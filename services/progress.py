"""Progress, mastery, study calendar, streaks and pace."""
from datetime import date, timedelta

from db import transaction
from services import clock
from services.errors import ValidationError
from services.quizzes import log_activity

# Weight of the newest answer in the mastery average (exponentially weighted).
# 0.3 means the latest answer counts for 30%, the one before for 21%, and so on.
MASTERY_ALPHA = 0.3


def course_progress(conn, student_id: int, course_id: int) -> dict:
    row = conn.execute(
        """SELECT
             (SELECT COUNT(*) FROM modules WHERE course_id = :c) AS modules_total,
             (SELECT COUNT(*) FROM module_progress mp JOIN modules m ON m.id = mp.module_id
              WHERE m.course_id = :c AND mp.student_id = :s AND mp.status = 'completed') AS modules_done,
             (SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id = l.module_id WHERE m.course_id = :c) AS lessons_total,
             (SELECT COUNT(*) FROM lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id
              JOIN modules m ON m.id = l.module_id
              WHERE m.course_id = :c AND lp.student_id = :s AND lp.completed_on IS NOT NULL) AS lessons_done""",
        {"c": course_id, "s": student_id},
    ).fetchone()
    p = dict(row)
    p["percent"] = round(100 * p["modules_done"] / p["modules_total"]) if p["modules_total"] else 0
    return p


def complete_lesson(conn, student_id: int, lesson_id: int, watched_pct: int = 0) -> None:
    row = conn.execute(
        """SELECT m.course_id, e.status FROM lessons l JOIN modules m ON m.id = l.module_id
           LEFT JOIN enrollments e ON e.course_id = m.course_id AND e.student_id = ?
           WHERE l.id = ?""", (student_id, lesson_id),
    ).fetchone()
    if row is None:
        raise ValidationError("That lesson no longer exists.")
    if row["status"] not in ("active", "completed"):
        raise ValidationError("Enroll in the course before marking its lessons as read.")
    course_id = row["course_id"]
    with transaction(conn):
        conn.execute(
            """INSERT INTO lesson_progress (student_id, lesson_id, completed_on, watched_pct) VALUES (?, ?, ?, ?)
               ON CONFLICT (student_id, lesson_id) DO UPDATE SET
                   completed_on = COALESCE(completed_on, excluded.completed_on),
                   watched_pct = MAX(watched_pct, excluded.watched_pct)""",
            (student_id, lesson_id, clock.today().isoformat(), max(0, min(100, watched_pct))),
        )
        log_activity(conn, student_id, course_id, 1)


def lessons_done(conn, student_id: int, module_id: int) -> set[int]:
    return {r[0] for r in conn.execute(
        """SELECT lp.lesson_id FROM lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id
           WHERE lp.student_id = ? AND l.module_id = ? AND lp.completed_on IS NOT NULL""",
        (student_id, module_id),
    )}


def _ewma(values: list[int]) -> float:
    level = float(values[0])
    for v in values[1:]:
        level = MASTERY_ALPHA * v + (1 - MASTERY_ALPHA) * level
    return level


def mastery_map(conn, student_id: int, course_id: int) -> list[dict]:
    """One tile per module: 0–100, or None when there is nothing to judge yet.

    From answers when there are any (recent answers count more), otherwise from
    the module's best score (OULAD assessments).
    """
    answers: dict[int, list[int]] = {}
    for r in conn.execute(
        """SELECT q.module_id, r.is_correct FROM responses r
           JOIN questions q ON q.id = r.question_id
           JOIN modules m ON m.id = q.module_id
           WHERE r.student_id = ? AND m.course_id = ?
           ORDER BY COALESCE(r.answered_at, ''), r.seq, r.id""",
        (student_id, course_id),
    ):
        answers.setdefault(r["module_id"], []).append(r["is_correct"])

    tiles = []
    for m in conn.execute(
        """SELECT m.id, m.title, m.position, mp.best_score, mp.status
           FROM modules m LEFT JOIN module_progress mp ON mp.module_id = m.id AND mp.student_id = ?
           WHERE m.course_id = ? ORDER BY m.position""",
        (student_id, course_id),
    ):
        seen = answers.get(m["id"])
        if seen:
            value, basis = round(100 * _ewma(seen)), f"{len(seen)} answers"
        elif m["best_score"] is not None:
            value, basis = round(m["best_score"]), "best score"
        else:
            value, basis = None, "not started"
        tiles.append({"module_id": m["id"], "title": m["title"], "mastery": value, "basis": basis,
                      "completed": m["status"] == "completed"})
    return tiles


def calendar(conn, student_id: int, year: int | None = None) -> dict:
    """Activity per day for one year, summed over all courses."""
    if year is None:
        last = conn.execute("SELECT MAX(day) FROM activity_days WHERE student_id = ?", (student_id,)).fetchone()[0]
        year = int(last[:4]) if last else clock.today().year
    days = {r["day"]: r["clicks"] for r in conn.execute(
        """SELECT day, SUM(clicks) AS clicks FROM activity_days
           WHERE student_id = ? AND day BETWEEN ? AND ? GROUP BY day""",
        (student_id, f"{year}-01-01", f"{year}-12-31"),
    )}
    years = [int(r[0]) for r in conn.execute(
        "SELECT DISTINCT substr(day, 1, 4) FROM activity_days WHERE student_id = ? ORDER BY 1", (student_id,))]
    return {"year": year, "days": days, "years": years or [year]}


def streaks(conn, student_id: int, as_of: date | None = None) -> dict:
    """Current streak (consecutive active days up to `as_of`) and the longest ever.

    For dataset students `as_of` defaults to their last active day, since their
    activity is historical.
    """
    days = sorted({date.fromisoformat(r[0]) for r in conn.execute(
        "SELECT DISTINCT day FROM activity_days WHERE student_id = ?", (student_id,))})
    if not days:
        return {"current": 0, "longest": 0, "last_active": None, "active_days": 0}
    longest = run = 1
    for a, b in zip(days, days[1:]):
        run = run + 1 if (b - a).days == 1 else 1
        longest = max(longest, run)

    source = conn.execute("SELECT source FROM students WHERE id = ?", (student_id,)).fetchone()[0]
    ref = as_of or (clock.today() if source == "local" else days[-1])
    active = set(days)
    if ref not in active:
        ref -= timedelta(days=1)  # today isn't over yet; a streak survives until tomorrow
    current = 0
    while ref in active:
        current += 1
        ref -= timedelta(days=1)
    return {"current": current, "longest": longest, "last_active": days[-1].isoformat(), "active_days": len(days)}


def pace(conn, student_id: int, course_id: int, window_days: int = 14) -> dict:
    """Finish-date forecast from modules completed in the last `window_days`."""
    enrollment = conn.execute(
        "SELECT status, enrolled_on, ended_on, final_result FROM enrollments WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    ).fetchone()
    progress = course_progress(conn, student_id, course_id)
    remaining = progress["modules_total"] - progress["modules_done"]
    if enrollment is None:
        return {"state": "not_enrolled", "text": "Not enrolled."}
    if enrollment["status"] != "active":
        ended = enrollment["ended_on"] or "unknown date"
        return {"state": "ended", "text": f"Ended {ended}: {enrollment['final_result'] or enrollment['status']}."}
    if remaining == 0:
        return {"state": "done", "text": "All modules done."}

    today = clock.today()
    since = (today - timedelta(days=window_days)).isoformat()
    recent = conn.execute(
        """SELECT COUNT(*) FROM module_progress mp JOIN modules m ON m.id = mp.module_id
           WHERE m.course_id = ? AND mp.student_id = ? AND mp.status = 'completed' AND mp.completed_on > ?""",
        (course_id, student_id, since),
    ).fetchone()[0]
    started = enrollment["enrolled_on"]
    if recent == 0 and started and (today - date.fromisoformat(started)).days < 7:
        return {"state": "starting", "remaining": remaining,
                "text": "Just started. Finish a first module to get a finish-date forecast."}
    if recent == 0:
        return {"state": "stalled", "remaining": remaining,
                "text": f"No modules finished in the last {window_days} days. {remaining} to go."}
    per_day = recent / window_days
    finish = today + timedelta(days=round(remaining / per_day))
    return {"state": "on_pace", "remaining": remaining, "per_week": round(per_day * 7, 1),
            "finish_on": finish.isoformat(),
            "text": f"At your current pace ({per_day * 7:.1f} modules a week) you finish around {finish:%d %b %Y}."}
