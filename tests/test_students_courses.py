"""Students, courses and enrollments: the records and the rules around them."""
import sqlite3

import pytest

from services import courses, enrollments, students
from services.common import ValidationError


@pytest.mark.parametrize("name, email, message", [
    ("", None, "Name is required"),
    ("   ", None, "Name is required"),
    ("Asha", "not-an-email", "doesn't look right"),
    ("Asha", "asha@nowhere", "doesn't look right"),
])
def test_student_validation(conn, name, email, message):
    with pytest.raises(ValidationError, match=message):
        students.add(conn, name, email)


def test_student_email_must_be_unique(conn, world):
    with pytest.raises(ValidationError, match="already uses"):
        students.add(conn, "Someone Else", "ASHA@example.com")


def test_student_search_and_update(conn, world):
    rows, total = students.search(conn, "ravi")
    assert total == 1 and rows[0]["display_name"] == "Ravi Kumar"
    students.update(conn, world["ravi"], "Ravi K.", "ravi.k@example.com")
    assert students.get(conn, world["ravi"])["email"] == "ravi.k@example.com"


def test_removing_a_student_removes_their_records(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    students.remove(conn, world["asha"])
    left = conn.execute("SELECT COUNT(*) FROM enrollments WHERE student_id = ?", (world["asha"],)).fetchone()[0]
    assert left == 0  # ON DELETE CASCADE


@pytest.mark.parametrize("code", ["x", "has space", "lower-ok?", "A" * 25])
def test_course_code_rules(conn, code):
    with pytest.raises(ValidationError, match="Code"):
        courses.add(conn, code, "Title", "Subject")


def test_course_code_unique(conn, world):
    with pytest.raises(ValidationError, match="already exists"):
        courses.add(conn, "py-1", "Again", "Subject")


def test_module_reorder(conn, world):
    mods = courses.modules(conn, world["a"])
    courses.move_module(conn, mods[1]["id"], -1)
    assert [m["title"] for m in courses.modules(conn, world["a"])] == ["Loops", "Variables"]


def test_prerequisite_loop_is_refused(conn, world):
    with pytest.raises(ValidationError, match="loop"):
        courses.add_prerequisite(conn, world["a"], world["b"])
    with pytest.raises(ValidationError, match="itself"):
        courses.add_prerequisite(conn, world["a"], world["a"])


def test_course_with_students_cannot_be_deleted(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    with pytest.raises(ValidationError, match="Archive"):
        courses.remove(conn, world["a"])


def test_lesson_needs_text_and_valid_link(conn, world):
    mid = world["mods"]["Loops"]
    with pytest.raises(ValidationError):
        courses.save_lesson(conn, mid, "Title", "")
    with pytest.raises(ValidationError, match="http"):
        courses.save_lesson(conn, mid, "Title", "Body", "ftp://video")


def test_enroll_and_list(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    rows, total = enrollments.list_for_course(conn, world["a"])
    assert total == 1 and rows[0]["status"] == "active"


def test_cannot_enroll_twice(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    with pytest.raises(ValidationError, match="Already enrolled"):
        enrollments.enroll(conn, world["asha"], world["a"])


def test_prerequisite_blocks_enrollment(conn, world):
    with pytest.raises(ValidationError, match="Finish these first: Python one"):
        enrollments.enroll(conn, world["asha"], world["b"])


def test_database_trigger_also_blocks_missing_prerequisite(conn, world):
    """Even if the Python check were skipped, the database refuses."""
    with pytest.raises(sqlite3.IntegrityError, match="prerequisite not completed"):
        conn.execute("INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, 'active')",
                     (world["asha"], world["b"]))


def test_drop_and_reenroll(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    enrollments.drop(conn, world["asha"], world["a"])
    status = conn.execute("SELECT status FROM enrollments WHERE student_id = ? AND course_id = ?",
                          (world["asha"], world["a"])).fetchone()[0]
    assert status == "withdrawn"
    with pytest.raises(ValidationError):
        enrollments.drop(conn, world["asha"], world["a"])
    enrollments.enroll(conn, world["asha"], world["a"])
    row = conn.execute("SELECT status, prev_attempts FROM enrollments WHERE student_id = ? AND course_id = ?",
                       (world["asha"], world["a"])).fetchone()
    assert row["status"] == "active" and row["prev_attempts"] == 1


def test_historical_courses_are_closed(conn, world):
    conn.execute("UPDATE courses SET source = 'oulad' WHERE id = ?", (world["a"],))
    with pytest.raises(ValidationError, match="historical"):
        enrollments.enroll(conn, world["asha"], world["a"])


def test_archived_course_is_closed(conn, world):
    conn.execute("UPDATE courses SET archived = 1 WHERE id = ?", (world["a"],))
    with pytest.raises(ValidationError, match="archived"):
        enrollments.enroll(conn, world["asha"], world["a"])
