"""Progress coach: a rule engine that writes study notes and a 7-day plan.

Each rule has a condition, a priority (1 = most urgent) and a message. All rules
are checked against the student's facts; the ones that match are sorted by
priority, notes about the same module are merged, and the top ones shown.
Nothing is generated at random: the same facts always give the same advice,
and every note can be traced back to the rule that wrote it.
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta

from services import common, progress, review
from smart.recommender import OPEN_SOURCES, recommend_courses


@dataclass
class Note:
    rule: str
    priority: int
    text: str
    module_id: int | None = None


# Facts -----------------------------------------------------------------------

def _facts(conn, student_id: int) -> dict:
    today = common.today()
    student = dict(conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())
    enrollments = [dict(r) for r in conn.execute(
        """SELECT e.course_id, e.status, e.final_result, e.ended_on, c.title, c.source, c.pass_mark
           FROM enrollments e JOIN courses c ON c.id = e.course_id WHERE e.student_id = ?""",
        (student_id,),
    )]
    active = [e for e in enrollments if e["status"] == "active" and e["source"] in OPEN_SOURCES]
    for e in active:
        e["progress"] = progress.course_progress(conn, student_id, e["course_id"])
        e["pace"] = progress.pace(conn, student_id, e["course_id"])
        e["mastery"] = progress.mastery_map(conn, student_id, e["course_id"])
        e["next_lessons"] = [dict(r) for r in conn.execute(
            """SELECT l.id, l.title, m.id AS module_id, m.title AS module_title
               FROM lessons l JOIN modules m ON m.id = l.module_id
               WHERE m.course_id = ?
                 AND NOT EXISTS (SELECT 1 FROM lesson_progress lp
                                 WHERE lp.lesson_id = l.id AND lp.student_id = ? AND lp.completed_on IS NOT NULL)
               ORDER BY m.position, l.position LIMIT 12""",
            (e["course_id"], student_id),
        )]
    scores = [r["score"] for r in conn.execute(
        """SELECT score FROM quiz_attempts WHERE student_id = ? AND kind = 'quiz' AND finished_at IS NOT NULL
           ORDER BY finished_at DESC LIMIT 3""",
        (student_id,),
    )][::-1]
    last = conn.execute("SELECT MAX(day) FROM activity_days WHERE student_id = ?", (student_id,)).fetchone()[0]
    return {
        "today": today,
        "student": student,
        "historical": student["source"] != "local",
        "enrollments": enrollments,
        "active": active,
        "review": review.summary(conn, student_id, today),
        "streak": progress.streaks(conn, student_id),
        "days_inactive": (today - date.fromisoformat(last)).days if last else None,
        "recent_scores": scores,
    }


# Rules -----------------------------------------------------------------------

def _rules(f: dict, conn, student_id: int) -> list[Note]:
    notes: list[Note] = []
    add = notes.append
    due = f["review"]["due"]

    if due:
        minutes = max(2, math.ceil(due * 0.5))
        add(Note("reviews-due", 1 if due >= 5 else 2,
                 f"You have {due} mistake{'s' if due != 1 else ''} due for review. "
                 f"Clearing them takes about {minutes} minutes and is the fastest way to lift your scores."))

    if f["active"] and f["days_inactive"] is not None and f["days_inactive"] >= 5:
        add(Note("inactive", 1, f"It's been {f['days_inactive']} days since you last studied. "
                                f"One short lesson today gets you moving again."))

    for e in f["active"]:
        for tile in e["mastery"]:
            if tile["mastery"] is not None and tile["mastery"] < 50 and tile["basis"].endswith("answers") \
                    and int(tile["basis"].split()[0]) >= 3:
                add(Note("weak-module", 1, f"Your mastery of {tile['title']} ({e['title']}) is "
                                           f"{tile['mastery']}%. Reread it, then retake the quiz.", tile["module_id"]))
        pace = e["pace"]
        if pace["state"] == "stalled":
            add(Note("stalled", 2, f"{e['title']}: {pace['text']}"))
        elif pace["state"] == "on_pace":
            add(Note("on-pace", 3, f"{e['title']}: {pace['text']}"))
        remaining = e["progress"]["modules_total"] - e["progress"]["modules_done"]
        if remaining == 1:
            add(Note("one-left", 2, f"One module left in {e['title']}. Pass its quiz to earn the certificate."))
        unread_by_module: dict[int, int] = {}
        for lesson in e["next_lessons"]:
            unread_by_module[lesson["module_id"]] = unread_by_module.get(lesson["module_id"], 0) + 1
        for tile in e["mastery"]:
            unread = unread_by_module.get(tile["module_id"], 0)
            if unread and tile["mastery"] is not None and tile["mastery"] < e["pass_mark"]:
                add(Note("quiz-before-reading", 2,
                         f"You tried the {tile['title']} quiz with {unread} lesson{'s' if unread > 1 else ''} "
                         f"still unread. Read {'them' if unread > 1 else 'it'} first.", tile["module_id"]))

    s = f["recent_scores"]
    if len(s) == 3 and s[0] < s[1] < s[2]:
        add(Note("rising", 3, f"Your last three quiz scores went up: {s[0]:.0f}% → {s[1]:.0f}% → {s[2]:.0f}%."))
    elif len(s) == 3 and s[0] > s[1] > s[2]:
        add(Note("falling", 2, f"Your quiz scores slipped: {s[0]:.0f}% → {s[1]:.0f}% → {s[2]:.0f}%. "
                               f"Slow down and reread before the next one."))

    if not f["historical"] and f["streak"]["current"] >= 3:
        add(Note("streak", 3, f"{f['streak']['current']}-day study streak. Keep it going."))

    if not f["active"] and not f["historical"]:
        recs = recommend_courses(conn, student_id, 1)
        tail = f" Try {recs[0]['title']}: {recs[0]['reason']}" if recs else ""
        add(Note("no-courses", 2, "You're not enrolled in any open course right now." + tail))

    if f["historical"]:
        notes.extend(_historical_notes(conn, student_id, f))
    return notes


def _historical_notes(conn, student_id: int, f: dict) -> list[Note]:
    """For dataset students, the coach reads their record instead of planning ahead."""
    out = []
    for e in f["enrollments"]:
        if e["source"] != "oulad":
            continue
        days = conn.execute(
            "SELECT COUNT(*) FROM activity_days WHERE student_id = ? AND course_id = ?",
            (student_id, e["course_id"]),
        ).fetchone()[0]
        typical = conn.execute(
            """SELECT AVG(n) FROM (SELECT COUNT(*) AS n FROM activity_days a
               JOIN enrollments x ON x.student_id = a.student_id AND x.course_id = a.course_id
               WHERE a.course_id = ? AND x.status = 'completed' GROUP BY a.student_id)""",
            (e["course_id"],),
        ).fetchone()[0] or 0
        if e["status"] == "withdrawn":
            out.append(Note("record-withdrew", 1,
                            f"Withdrew from {e['title']} after {days} active days. Students who passed it "
                            f"were active on {typical:.0f} days on average."))
        elif e["status"] == "failed":
            weakest = conn.execute(
                """SELECT m.title, mp.best_score FROM module_progress mp JOIN modules m ON m.id = mp.module_id
                   WHERE mp.student_id = ? AND m.course_id = ? ORDER BY mp.best_score LIMIT 1""",
                (student_id, e["course_id"]),
            ).fetchone()
            extra = f" Weakest assessment: {weakest['title']} ({weakest['best_score']:.0f}%)." if weakest else ""
            out.append(Note("record-failed", 1, f"Did not pass {e['title']} ({days} active days).{extra}"))
        else:
            out.append(Note("record-passed", 3, f"{e['final_result']} in {e['title']} with {days} active days "
                                                f"(passers averaged {typical:.0f})."))
    return out


def notes(conn, student_id: int, limit: int = 3) -> list[Note]:
    f = _facts(conn, student_id)
    found = sorted(_rules(f, conn, student_id), key=lambda n: n.priority)
    picked, seen_modules = [], set()
    for n in found:
        if n.module_id and n.module_id in seen_modules:
            continue
        if n.module_id:
            seen_modules.add(n.module_id)
        picked.append(n)
    return picked[:limit] if limit else picked


# Plan ------------------------------------------------------------------------

def week_plan(conn, student_id: int, per_day: int = 3) -> list[dict]:
    """Seven days of concrete tasks: due reviews first, then weak modules, then the
    next unread lessons, with a quiz once a module's lessons are read."""
    f = _facts(conn, student_id)
    today = f["today"]
    days = [{"date": today + timedelta(days=i), "tasks": []} for i in range(7)]

    def put(day_index: int, task: str) -> bool:
        for d in days[day_index:]:
            if len(d["tasks"]) < per_day:
                d["tasks"].append(task)
                return True
        return False

    if f["review"]["due"]:
        put(0, f"Review {f['review']['due']} due mistakes")
    if f["review"]["next_due"]:
        next_due = date.fromisoformat(f["review"]["next_due"])
        if (next_due - today).days < 7:
            put((next_due - today).days, "Review mistakes that come due today")

    slot = 0
    for e in f["active"]:
        for tile in e["mastery"]:
            if tile["mastery"] is not None and tile["mastery"] < 50 and tile["basis"].endswith("answers"):
                put(min(slot, 6), f"Reread {tile['title']} and retake its quiz ({e['title']})")
                slot += 1

    lessons = [lesson for e in f["active"] for lesson in e["next_lessons"]]
    day = 0
    for i, lesson in enumerate(lessons):
        if not put(day, f"Read {lesson['title']}"):
            break
        nxt = lessons[i + 1] if i + 1 < len(lessons) else None
        if nxt is None or nxt["module_id"] != lesson["module_id"]:
            put(day, f"Take the {lesson['module_title']} quiz")
        if len(days[day]["tasks"]) >= per_day - 1:
            day = min(day + 1, 6)
    return [{"date": d["date"].isoformat(), "weekday": d["date"].strftime("%a"), "tasks": d["tasks"]} for d in days]
