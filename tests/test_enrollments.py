import sqlite3

import pytest

from services import enrollments
from services.common import ValidationError


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
