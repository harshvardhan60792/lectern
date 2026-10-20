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
