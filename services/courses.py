"""Courses, their modules and lessons, and prerequisites."""
import re

from db import transaction
from services.common import ValidationError

SOURCES = {
    "openstax": "OpenStax textbook", "sciq": "SciQ questions", "assistments": "ASSISTments",
    "oulad": "Open University", "local": "Created here",
}
CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,19}$")


# Courses ---------------------------------------------------------------------

def search(conn, text: str = "", source: str | None = None, include_archived: bool = False) -> list[dict]:
    where, params = ["1 = 1"], []
    if text.strip():
        where.append("(c.title LIKE ? OR c.code LIKE ? OR c.subject LIKE ?)")
        params += [f"%{text.strip()}%"] * 3
    if source:
        where.append("c.source = ?")
        params.append(source)
    if not include_archived:
        where.append("c.archived = 0")
    rows = conn.execute(
        f"""SELECT c.id, c.code, c.title, c.subject, c.source, c.starts_on, c.archived,
                   v.enrolled, v.completed, v.withdrawn, v.failed, v.active, v.completion_rate,
                   (SELECT COUNT(*) FROM modules m WHERE m.course_id = c.id) AS modules
            FROM courses c
            JOIN v_course_stats v ON v.course_id = c.id
            WHERE {' AND '.join(where)}
            ORDER BY CASE c.source WHEN 'local' THEN 0 WHEN 'openstax' THEN 1 WHEN 'sciq' THEN 2
                                   WHEN 'assistments' THEN 3 ELSE 4 END, c.code""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def get(conn, course_id: int) -> dict | None:
    row = conn.execute(
        """SELECT c.*, i.name AS instructor_name FROM courses c
           LEFT JOIN instructors i ON i.id = c.instructor_id WHERE c.id = ?""",
        (course_id,),
    ).fetchone()
    return dict(row) if row else None


def _validate(code: str, title: str, subject: str, pass_mark) -> tuple[str, str, str, int]:
    code, title, subject = code.strip().upper(), " ".join(title.split()), " ".join(subject.split())
    if not CODE.match(code):
        raise ValidationError("Code: 2–20 capital letters, digits or dashes, e.g. WEB-101.")
    if not title:
        raise ValidationError("Title is required.")
    if not subject:
        raise ValidationError("Subject is required.")
    try:
        pass_mark = int(pass_mark)
    except (TypeError, ValueError):
        raise ValidationError("Pass mark must be a whole number.") from None
    if not 0 <= pass_mark <= 100:
        raise ValidationError("Pass mark must be between 0 and 100.")
    return code, title, subject, pass_mark


def add(conn, code: str, title: str, subject: str, description: str = "", pass_mark=50,
        instructor_id: int | None = None) -> int:
    code, title, subject, pass_mark = _validate(code, title, subject, pass_mark)
    if conn.execute("SELECT 1 FROM courses WHERE code = ?", (code,)).fetchone():
        raise ValidationError(f"A course with code {code} already exists.")
    with transaction(conn):
        cur = conn.execute(
            """INSERT INTO courses (code, title, subject, description, source, pass_mark, instructor_id)
               VALUES (?, ?, ?, ?, 'local', ?, ?)""",
            (code, title, subject, description.strip(), pass_mark, instructor_id),
        )
    return cur.lastrowid


def update(conn, course_id: int, code: str, title: str, subject: str, description: str, pass_mark,
           instructor_id: int | None = None) -> None:
    code, title, subject, pass_mark = _validate(code, title, subject, pass_mark)
    clash = conn.execute("SELECT id FROM courses WHERE code = ?", (code,)).fetchone()
    if clash and clash["id"] != course_id:
        raise ValidationError(f"A course with code {code} already exists.")
    with transaction(conn):
        conn.execute(
            """UPDATE courses SET code = ?, title = ?, subject = ?, description = ?, pass_mark = ?,
                                  instructor_id = ?
               WHERE id = ?""",
            (code, title, subject, description.strip(), pass_mark, instructor_id, course_id),
        )


def set_archived(conn, course_id: int, archived: bool) -> None:
    with transaction(conn):
        conn.execute("UPDATE courses SET archived = ? WHERE id = ?", (int(archived), course_id))


def remove(conn, course_id: int) -> None:
    n = conn.execute("SELECT COUNT(*) FROM enrollments WHERE course_id = ?", (course_id,)).fetchone()[0]
    if n:
        raise ValidationError(f"{n} students are enrolled. Archive the course instead of deleting it.")
    with transaction(conn):
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))


def instructors(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT id, name, email FROM instructors ORDER BY name")]


# Modules ---------------------------------------------------------------------

def modules(conn, course_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT m.*,
                  (SELECT COUNT(*) FROM lessons l WHERE l.module_id = m.id) AS lessons,
                  (SELECT COUNT(*) FROM questions q WHERE q.module_id = m.id AND q.status = 'live') AS questions
           FROM modules m WHERE m.course_id = ? ORDER BY m.position""",
        (course_id,),
    )]


def add_module(conn, course_id: int, title: str) -> int:
    title = " ".join(title.split())
    if not title:
        raise ValidationError("Module title is required.")
    with transaction(conn):
        pos = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM modules WHERE course_id = ?",
                           (course_id,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO modules (course_id, position, title, kind) VALUES (?, ?, ?, 'chapter')",
            (course_id, pos, title),
        )
    return cur.lastrowid


def rename_module(conn, module_id: int, title: str) -> None:
    title = " ".join(title.split())
    if not title:
        raise ValidationError("Module title is required.")
    with transaction(conn):
        conn.execute("UPDATE modules SET title = ? WHERE id = ?", (title, module_id))


def move_module(conn, module_id: int, direction: int) -> None:
    """Swap a module with its neighbour (direction -1 = up, +1 = down)."""
    m = conn.execute("SELECT course_id, position FROM modules WHERE id = ?", (module_id,)).fetchone()
    other = conn.execute(
        f"""SELECT id, position FROM modules WHERE course_id = ? AND position {'<' if direction < 0 else '>'} ?
            ORDER BY position {'DESC' if direction < 0 else 'ASC'} LIMIT 1""",
        (m["course_id"], m["position"]),
    ).fetchone()
    if other is None:
        return
    with transaction(conn):
        # Positions are UNIQUE per course, so park one at -1 while swapping.
        conn.execute("UPDATE modules SET position = -1 WHERE id = ?", (module_id,))
        conn.execute("UPDATE modules SET position = ? WHERE id = ?", (m["position"], other["id"]))
        conn.execute("UPDATE modules SET position = ? WHERE id = ?", (other["position"], module_id))


def remove_module(conn, module_id: int) -> None:
    with transaction(conn):
        conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))


# Lessons ---------------------------------------------------------------------

def lessons(conn, module_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, position, title, video_url, length(body) AS length FROM lessons WHERE module_id = ? ORDER BY position",
        (module_id,),
    )]


def lesson(conn, lesson_id: int) -> dict | None:
    row = conn.execute(
        """SELECT l.*, m.title AS module_title, m.course_id, c.title AS course_title, c.attribution
           FROM lessons l JOIN modules m ON m.id = l.module_id JOIN courses c ON c.id = m.course_id
           WHERE l.id = ?""",
        (lesson_id,),
    ).fetchone()
    return dict(row) if row else None


def save_lesson(conn, module_id: int, title: str, body: str, video_url: str = "", lesson_id: int | None = None) -> int:
    title = " ".join(title.split())
    if not title:
        raise ValidationError("Lesson title is required.")
    if not body.strip():
        raise ValidationError("Lesson text is required.")
    video_url = video_url.strip() or None
    if video_url and not video_url.startswith(("http://", "https://")):
        raise ValidationError("Video link must start with http:// or https://")
    with transaction(conn):
        if lesson_id:
            conn.execute("UPDATE lessons SET title = ?, body = ?, video_url = ? WHERE id = ?",
                         (title, body.strip(), video_url, lesson_id))
            return lesson_id
        pos = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM lessons WHERE module_id = ?",
                           (module_id,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO lessons (module_id, position, title, body, video_url) VALUES (?, ?, ?, ?, ?)",
            (module_id, pos, title, body.strip(), video_url),
        )
        return cur.lastrowid


def remove_lesson(conn, lesson_id: int) -> None:
    with transaction(conn):
        conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))


# Prerequisites -----------------------------------------------------------------

def prerequisites(conn, course_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT c.id, c.code, c.title FROM prerequisites p JOIN courses c ON c.id = p.requires_id
           WHERE p.course_id = ? ORDER BY c.code""",
        (course_id,),
    )]


def _would_loop(conn, course_id: int, requires_id: int) -> bool:
    """True if `requires_id` already (directly or indirectly) requires `course_id`."""
    row = conn.execute(
        """WITH RECURSIVE chain(id) AS (
               SELECT requires_id FROM prerequisites WHERE course_id = ?
               UNION
               SELECT p.requires_id FROM prerequisites p JOIN chain ON p.course_id = chain.id
           )
           SELECT 1 FROM chain WHERE id = ?""",
        (requires_id, course_id),
    ).fetchone()
    return row is not None


def add_prerequisite(conn, course_id: int, requires_id: int) -> None:
    if course_id == requires_id:
        raise ValidationError("A course can't require itself.")
    if _would_loop(conn, course_id, requires_id):
        raise ValidationError("That would make a loop: the other course already depends on this one.")
    with transaction(conn):
        conn.execute("INSERT OR IGNORE INTO prerequisites (course_id, requires_id) VALUES (?, ?)",
                     (course_id, requires_id))


def remove_prerequisite(conn, course_id: int, requires_id: int) -> None:
    with transaction(conn):
        conn.execute("DELETE FROM prerequisites WHERE course_id = ? AND requires_id = ?", (course_id, requires_id))


def prerequisite_graph(conn) -> tuple[list[dict], list[tuple[int, int]]]:
    """Courses that take part in any prerequisite, and the edges between them."""
    edges = [(r["requires_id"], r["course_id"]) for r in conn.execute("SELECT * FROM prerequisites")]
    ids = sorted({i for e in edges for i in e})
    if not ids:
        return [], []
    nodes = [dict(r) for r in conn.execute(
        f"SELECT id, code, title FROM courses WHERE id IN ({', '.join(map(str, ids))})")]
    return nodes, edges
