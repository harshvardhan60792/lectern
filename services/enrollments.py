"""Enrolling, dropping and completing courses."""
import sqlite3

from db import transaction
from services import certificates, common
from services.common import ValidationError

# Courses imported from OULAD (2013–14) and ASSISTments (2009–10) are records of
# what happened, not courses anyone can join today.
HISTORICAL = ("oulad", "assistments")


def missing_prerequisites(conn, student_id: int, course_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT c.title FROM prerequisites p JOIN courses c ON c.id = p.requires_id
           WHERE p.course_id = ?
             AND NOT EXISTS (SELECT 1 FROM enrollments e
                             WHERE e.student_id = ? AND e.course_id = p.requires_id AND e.status = 'completed')""",
        (course_id, student_id),
    ).fetchall()
    return [r["title"] for r in rows]


def enroll(conn, student_id: int, course_id: int) -> int:
    """Enroll a student, or re-enroll one who withdrew. Returns the enrollment id."""
    course = conn.execute("SELECT title, archived, source FROM courses WHERE id = ?", (course_id,)).fetchone()
    if course is None:
        raise ValidationError("That course doesn't exist.")
    if course["source"] in HISTORICAL:
        raise ValidationError("This is a historical dataset course and is closed to new students.")
    if course["archived"]:
        raise ValidationError("This course is archived and closed to new students.")
    if conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        raise ValidationError("That student doesn't exist.")

    missing = missing_prerequisites(conn, student_id, course_id)
    if missing:
        raise ValidationError("Finish these first: " + ", ".join(missing) + ".")

    existing = conn.execute(
        "SELECT id, status FROM enrollments WHERE student_id = ? AND course_id = ?", (student_id, course_id)
    ).fetchone()
    today = common.today().isoformat()
    with transaction(conn):
        if existing:
            if existing["status"] in ("active", "completed"):
                raise ValidationError(f"Already enrolled in {course['title']}.")
            conn.execute(
                """UPDATE enrollments SET status = 'active', enrolled_on = ?, ended_on = NULL, final_result = NULL,
                                          prev_attempts = prev_attempts + 1
                   WHERE id = ?""",
                (today, existing["id"]),
            )
            return existing["id"]
        try:
            cur = conn.execute(
                "INSERT INTO enrollments (student_id, course_id, enrolled_on, status) VALUES (?, ?, ?, 'active')",
                (student_id, course_id, today),
            )
        except sqlite3.IntegrityError as exc:  # the database trigger is the last line of defence
            raise ValidationError(str(exc).capitalize() + ".") from None
        return cur.lastrowid


def drop(conn, student_id: int, course_id: int) -> None:
    with transaction(conn):
        cur = conn.execute(
            """UPDATE enrollments SET status = 'withdrawn', ended_on = ?, final_result = 'Withdrawn'
               WHERE student_id = ? AND course_id = ? AND status = 'active'""",
            (common.today().isoformat(), student_id, course_id),
        )
    if cur.rowcount == 0:
        raise ValidationError("Only an active enrollment can be dropped.")


def list_for_course(conn, course_id: int, status: str | None = None, text: str = "",
                    limit: int = 200, offset: int = 0) -> tuple[list[dict], int]:
    where, params = ["e.course_id = ?"], [course_id]
    if status:
        where.append("e.status = ?")
        params.append(status)
    if text.strip():
        where.append("s.display_name LIKE ?")
        params.append(f"%{text.strip()}%")
    clause = " AND ".join(where)
    total = conn.execute(
        f"SELECT COUNT(*) FROM enrollments e JOIN students s ON s.id = e.student_id WHERE {clause}", params
    ).fetchone()[0]
    rows = conn.execute(
        f"""SELECT e.id, e.student_id, s.display_name, s.source, e.status, e.final_result,
                   e.enrolled_on, e.ended_on,
                   (SELECT COUNT(*) FROM module_progress mp JOIN modules m ON m.id = mp.module_id
                    WHERE m.course_id = e.course_id AND mp.student_id = e.student_id
                      AND mp.status = 'completed') AS modules_done,
                   (SELECT ROUND(AVG(mp.best_score), 1) FROM module_progress mp JOIN modules m ON m.id = mp.module_id
                    WHERE m.course_id = e.course_id AND mp.student_id = e.student_id) AS avg_score
            FROM enrollments e JOIN students s ON s.id = e.student_id
            WHERE {clause}
            ORDER BY e.status = 'active' DESC, s.display_name
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def check_completion(conn, student_id: int, course_id: int) -> dict | None:
    """If every module is passed, mark the enrollment completed and issue the
    certificate. Call inside the caller's transaction. Returns the certificate
    when one was issued."""
    row = conn.execute(
        """SELECT c.pass_mark,
                  (SELECT COUNT(*) FROM modules m WHERE m.course_id = c.id
                     AND EXISTS (SELECT 1 FROM questions q WHERE q.module_id = m.id AND q.status = 'live')) AS needed,
                  (SELECT COUNT(*) FROM modules m JOIN module_progress mp ON mp.module_id = m.id
                   WHERE m.course_id = c.id AND mp.student_id = ? AND mp.status = 'completed'
                     AND EXISTS (SELECT 1 FROM questions q WHERE q.module_id = m.id AND q.status = 'live')) AS done,
                  e.status
           FROM courses c JOIN enrollments e ON e.course_id = c.id AND e.student_id = ?
           WHERE c.id = ?""",
        (student_id, student_id, course_id),
    ).fetchone()
    if row is None or row["status"] != "active" or row["needed"] == 0 or row["done"] < row["needed"]:
        return None
    today = common.today().isoformat()
    conn.execute(
        """UPDATE enrollments SET status = 'completed', ended_on = ?, final_result = 'Pass'
           WHERE student_id = ? AND course_id = ?""",
        (today, student_id, course_id),
    )
    return certificates.issue(conn, student_id, course_id, today, grade="Pass")
