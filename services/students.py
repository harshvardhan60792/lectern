"""Add, find, change and remove students."""
import re

from db import transaction
from services.errors import ValidationError

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SOURCES = {"oulad": "Open University", "assistments": "ASSISTments", "local": "Added here"}


def _clean(name: str, email: str | None) -> tuple[str, str | None]:
    name = " ".join(name.split())
    if not name:
        raise ValidationError("Name is required.")
    if len(name) > 80:
        raise ValidationError("Name is too long (80 characters max).")
    email = (email or "").strip().lower() or None
    if email and not EMAIL.match(email):
        raise ValidationError("That email address doesn't look right.")
    return name, email


def _check_email_free(conn, email: str | None, student_id: int | None = None) -> None:
    if email is None:
        return
    row = conn.execute("SELECT id FROM students WHERE email = ?", (email,)).fetchone()
    if row and row["id"] != student_id:
        raise ValidationError("Another student already uses this email.")


def add(conn, name: str, email: str | None = None, region: str | None = None,
        highest_education: str | None = None) -> int:
    name, email = _clean(name, email)
    _check_email_free(conn, email)
    with transaction(conn):
        cur = conn.execute(
            """INSERT INTO students (source, display_name, email, region, highest_education)
               VALUES ('local', ?, ?, ?, ?)""",
            (name, email, region or None, highest_education or None),
        )
    return cur.lastrowid


def update(conn, student_id: int, name: str, email: str | None = None, region: str | None = None,
           highest_education: str | None = None) -> None:
    name, email = _clean(name, email)
    _check_email_free(conn, email, student_id)
    with transaction(conn):
        conn.execute(
            """UPDATE students SET display_name = ?, email = ?, region = ?, highest_education = ?
               WHERE id = ?""",
            (name, email, region or None, highest_education or None, student_id),
        )


def remove(conn, student_id: int) -> None:
    """Deletes the student and, through ON DELETE CASCADE, their enrollments,
    progress, answers and certificates."""
    with transaction(conn):
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def get(conn, student_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def search(conn, text: str = "", source: str | None = None, limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    where, params = ["1 = 1"], []
    text = text.strip()
    if text:
        where.append("(s.display_name LIKE ? OR s.email LIKE ? OR s.external_id = ?)")
        params += [f"%{text}%", f"%{text}%", text]
    if source:
        where.append("s.source = ?")
        params.append(source)
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM students s WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT s.id, s.display_name, s.email, s.source, s.region, s.highest_education,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.student_id = s.id) AS courses
            FROM students s
            WHERE {clause}
            ORDER BY s.source = 'local' DESC, s.display_name
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def enrollments(conn, student_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT e.id, e.course_id, c.code, c.title, c.source, e.status, e.final_result,
                  e.enrolled_on, e.ended_on, v.weighted_score, v.avg_score, v.modules_done,
                  (SELECT COUNT(*) FROM modules m WHERE m.course_id = c.id) AS modules_total
           FROM enrollments e
           JOIN courses c ON c.id = e.course_id
           LEFT JOIN v_enrollment_scores v ON v.enrollment_id = e.id
           WHERE e.student_id = ?
           ORDER BY e.enrolled_on DESC, c.title""",
        (student_id,),
    )]
