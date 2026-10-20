"""Reports and the question health check."""
import csv
import re
from pathlib import Path

from app.config import config


def overview(conn) -> dict:
    one = lambda sql, *p: conn.execute(sql, p).fetchone()[0]  # noqa: E731
    return {
        "students": one("SELECT COUNT(*) FROM students"),
        "students_by_source": {r[0]: r[1] for r in conn.execute(
            "SELECT source, COUNT(*) FROM students GROUP BY source")},
        "courses": one("SELECT COUNT(*) FROM courses WHERE archived = 0"),
        "enrollments": one("SELECT COUNT(*) FROM enrollments"),
        "active": one("SELECT COUNT(*) FROM enrollments WHERE status = 'active'"),
        "certificates": one("SELECT COUNT(*) FROM certificates WHERE revoked = 0"),
        "questions": one("SELECT COUNT(*) FROM questions WHERE status = 'live'"),
        "answers": one("SELECT COUNT(*) FROM responses"),
        "completion_rate": one(
            """SELECT ROUND(100.0 * SUM(status = 'completed') / NULLIF(SUM(status <> 'active'), 0), 1)
               FROM enrollments"""),
    }


def course_outcomes(conn, source: str | None = "oulad") -> list[dict]:
    where = "WHERE source = ?" if source else ""
    return [dict(r) for r in conn.execute(
        f"""SELECT course_id, code, title, enrolled, completed, failed, withdrawn, active, completion_rate
            FROM v_course_stats {where} ORDER BY code""",
        (source,) if source else (),
    )]


GROUPS = {
    "highest_education": "Education before the course",
    "imd_band": "Deprivation band of home area (IMD)",
    "age_band": "Age band",
    "disability": "Declared disability",
    "gender": "Gender",
}
EDUCATION_ORDER = ["No Formal quals", "Lower Than A Level", "A Level or Equivalent",
                   "HE Qualification", "Post Graduate Qualification"]


def outcomes_by(conn, field: str) -> list[dict]:
    """Pass / fail / withdraw rates by a student background field (OULAD only)."""
    if field not in GROUPS:
        raise ValueError("Unknown grouping.")
    rows = [dict(r) for r in conn.execute(
        f"""SELECT s.{field} AS grp,
                   COUNT(*) AS n,
                   ROUND(100.0 * SUM(e.status = 'completed') / COUNT(*), 1) AS passed,
                   ROUND(100.0 * SUM(e.status = 'failed') / COUNT(*), 1) AS failed,
                   ROUND(100.0 * SUM(e.status = 'withdrawn') / COUNT(*), 1) AS withdrawn
            FROM enrollments e JOIN students s ON s.id = e.student_id
            WHERE s.source = 'oulad' AND s.{field} IS NOT NULL
            GROUP BY s.{field}"""  # field is checked against GROUPS above
    )]
    if field == "highest_education":
        rows.sort(key=lambda r: EDUCATION_ORDER.index(r["grp"]) if r["grp"] in EDUCATION_ORDER else 99)
    else:
        rows.sort(key=lambda r: str(r["grp"]))
    return rows


def activity_by_outcome(conn) -> list[dict]:
    """Average number of active days and clicks for each final result (OULAD)."""
    return [dict(r) for r in conn.execute(
        """SELECT e.final_result AS result, COUNT(*) AS n,
                  ROUND(AVG(a.days), 1) AS avg_active_days, ROUND(AVG(a.clicks), 0) AS avg_clicks
           FROM enrollments e
           JOIN courses c ON c.id = e.course_id AND c.source = 'oulad'
           LEFT JOIN (SELECT student_id, course_id, COUNT(*) AS days, SUM(clicks) AS clicks
                      FROM activity_days GROUP BY student_id, course_id) a
                  ON a.student_id = e.student_id AND a.course_id = e.course_id
           GROUP BY e.final_result
           ORDER BY CASE e.final_result WHEN 'Distinction' THEN 0 WHEN 'Pass' THEN 1 WHEN 'Fail' THEN 2 ELSE 3 END"""
    )]


def weekly_activity(conn, course_id: int) -> list[dict]:
    """Clicks per course week, split by final result: shows when students drift away."""
    return [dict(r) for r in conn.execute(
        """SELECT CAST((julianday(a.day) - julianday(c.starts_on)) / 7 AS INTEGER) AS week,
                  e.final_result AS result,
                  ROUND(1.0 * SUM(a.clicks) / COUNT(DISTINCT a.student_id), 1) AS clicks_per_student
           FROM activity_days a
           JOIN courses c ON c.id = a.course_id
           JOIN enrollments e ON e.student_id = a.student_id AND e.course_id = a.course_id
           WHERE a.course_id = ? AND a.day >= c.starts_on
           GROUP BY week, e.final_result ORDER BY week""",
        (course_id,),
    )]


def monthly_enrollments(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM v_monthly_enrollments ORDER BY month")]


def score_distribution(conn, course_id: int) -> list[float]:
    return [r[0] for r in conn.execute(
        "SELECT weighted_score FROM v_enrollment_scores WHERE course_id = ? AND weighted_score IS NOT NULL",
        (course_id,),
    )]


def grade_audit(conn, limit: int = 200) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT g.changed_at, s.display_name AS student, m.title AS module, c.title AS course,
                  g.old_score, g.new_score, COALESCE(u.username, '(system)') AS changed_by
           FROM grade_audit g
           JOIN students s ON s.id = g.student_id
           JOIN modules m  ON m.id = g.module_id
           JOIN courses c  ON c.id = m.course_id
           LEFT JOIN users u ON u.id = g.changed_by
           ORDER BY g.id DESC LIMIT ?""",
        (limit,),
    )]


def export_csv(rows: list[dict], name: str) -> Path:
    config.exports_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9 _-]", "", name).strip() or "export"  # no folders, only a plain file name
    path = config.exports_dir / f"{safe}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return path


# Question health ---------------------------------------------------------------
#
# Item analysis, as used by exam boards:
#   difficulty p      = share of students who got the question right
#   discrimination D  = p among the strongest 27% of students − p among the weakest 27%
# A good question has p between about 0.2 and 0.9, and D above about 0.2: strong
# students get it right more often than weak ones. D near zero or negative means
# the question is confusing, or its answer key may be wrong.

MIN_ANSWERS = 30
GROUP_SHARE = 0.27


def question_health(conn, course_id: int, module_id: int | None = None, min_answers: int = MIN_ANSWERS) -> dict:
    # First answer of each student to each question: later attempts are practice.
    first: dict[tuple[int, int], int] = {}
    for r in conn.execute(
        """SELECT r.student_id, r.question_id, r.is_correct
           FROM responses r JOIN questions q ON q.id = r.question_id JOIN modules m ON m.id = q.module_id
           WHERE m.course_id = ?
           ORDER BY COALESCE(r.answered_at, ''), r.seq, r.id""",
        (course_id,),
    ):
        first.setdefault((r["student_id"], r["question_id"]), r["is_correct"])

    # Ability = share right across the whole course.
    totals: dict[int, list[int]] = {}
    by_question: dict[int, list[tuple[int, int]]] = {}
    for (student, question), ok in first.items():
        t = totals.setdefault(student, [0, 0])
        t[0] += ok
        t[1] += 1
        by_question.setdefault(question, []).append((student, ok))
    ability = {s: right / n for s, (right, n) in totals.items() if n >= 5}

    scope = {r[0]: dict(r) for r in conn.execute(
        f"""SELECT q.id, q.external_id, q.prompt, q.source, m.title AS module_title
            FROM questions q JOIN modules m ON m.id = q.module_id
            WHERE m.course_id = ? {'AND m.id = ?' if module_id else ''}""",
        (course_id, module_id) if module_id else (course_id,),
    )}

    items = []
    for qid, answers in by_question.items():
        if qid not in scope or len(answers) < min_answers:
            continue
        p = sum(ok for _, ok in answers) / len(answers)
        ranked = sorted((ability[s], ok) for s, ok in answers if s in ability)
        k = max(1, int(len(ranked) * GROUP_SHARE))
        d = None
        if len(ranked) >= 2 * k and len(ranked) >= 10:
            d = sum(ok for _, ok in ranked[-k:]) / k - sum(ok for _, ok in ranked[:k]) / k
        flag, advice = _verdict(p, d)
        q = scope[qid]
        items.append({
            "question_id": qid,
            "label": q["prompt"] or f"Problem {q['external_id']}",
            "module": q["module_title"],
            "answers": len(answers),
            "difficulty": round(p, 2),
            "discrimination": None if d is None else round(d, 2),
            "flag": flag,
            "advice": advice,
        })
    order = {"Check answer key": 0, "Doesn't separate": 1, "Too hard": 2, "Too easy": 3, "Healthy": 4}
    items.sort(key=lambda i: (order[i["flag"]], i["discrimination"] if i["discrimination"] is not None else 1))
    counts: dict[str, int] = {}
    for i in items:
        counts[i["flag"]] = counts.get(i["flag"], 0) + 1
    return {"items": items, "counts": counts, "students": len(totals), "min_answers": min_answers}


def _verdict(p: float, d: float | None) -> tuple[str, str]:
    if d is not None and d < -0.1:  # small negative values are just noise in small groups
        return "Check answer key", "Weaker students do better than stronger ones. The key or wording may be wrong."
    if d is not None and d < 0.2 and 0.2 <= p <= 0.9:
        return "Doesn't separate", "Strong and weak students score about the same. Reword or replace."
    if p < 0.2:
        return "Too hard", "Fewer than 1 in 5 get it right. Check it is taught before it is tested."
    if p > 0.9:
        return "Too easy", "Almost everyone gets it right. Fine as a warm-up, tells you little."
    return "Healthy", "Good spread of difficulty and separates strong from weak students."
