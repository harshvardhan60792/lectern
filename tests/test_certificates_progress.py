import sqlite3
from datetime import timedelta

import pytest

from services import certificates, clock, enrollments, progress, quizzes
from tests.conftest import TODAY, answer_all


@pytest.fixture
def certified(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    for m in ("Variables", "Loops"):
        result = answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"][m]), True)
    return result["certificate"]["code"]


def test_genuine_certificate_verifies(conn, certified):
    assert certificates.verify(conn, certified)["valid"]
    assert certificates.verify(conn, certified.lower())["valid"]


def test_edited_pdf_details_fail(conn, certified):
    for change in ({"student_name": "Someone Else"}, {"score": 99.0}, {"issued_on": "2020-01-01"},
                   {"course_title": "Rocket science"}):
        assert not certificates.verify(conn, certified, **change)["valid"]


def test_record_edited_in_database_fails(conn, certified):
    conn.execute("UPDATE certificates SET score = 100 WHERE code = ?", (certified,))
    conn.execute("UPDATE students SET display_name = 'Forged' WHERE id = (SELECT student_id FROM certificates)")
    assert not certificates.verify(conn, certified)["valid"]


def test_unknown_and_revoked(conn, certified):
    assert not certificates.verify(conn, "LEC-0000-0000")["valid"]
    certificates.revoke(conn, certified)
    assert "revoked" in certificates.verify(conn, certified)["reason"]


def test_database_refuses_certificate_for_unfinished_course(conn, world):
    enrollments.enroll(conn, world["ravi"], world["a"])
    with pytest.raises(sqlite3.IntegrityError, match="course not completed"):
        conn.execute("INSERT INTO certificates (code, student_id, course_id, issued_on, fingerprint) "
                     "VALUES ('X', ?, ?, '2026-01-01', 'x')", (world["ravi"], world["a"]))


def test_pdf_is_written(conn, certified, tmp_path):
    path = certificates.render_pdf(conn, certified, tmp_path / "c.pdf")
    assert path.read_bytes()[:4] == b"%PDF"


def test_mastery_weights_recent_answers(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    mid = world["mods"]["Variables"]
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], mid), False)
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], mid), True)
    tile = next(t for t in progress.mastery_map(conn, world["asha"], world["a"]) if t["module_id"] == mid)
    # 5 wrong then 5 right: well above the plain average of 50% because recent answers count more.
    assert tile["mastery"] > 75 and tile["basis"] == "10 answers"
    untouched = next(t for t in progress.mastery_map(conn, world["asha"], world["a"]) if t["title"] == "Loops")
    assert untouched["mastery"] is None


def test_streaks(conn, world):
    sid = world["asha"]
    for offset in (0, 1, 2, 5, 6):
        conn.execute("INSERT INTO activity_days VALUES (?, ?, ?, 1)",
                     (sid, world["a"], (TODAY - timedelta(days=offset)).isoformat()))
    s = progress.streaks(conn, sid)
    assert s["current"] == 3 and s["longest"] == 3 and s["active_days"] == 5


def test_pace_states(conn, world):
    sid = world["asha"]
    enrollments.enroll(conn, sid, world["a"])
    assert progress.pace(conn, sid, world["a"])["state"] == "starting"
    clock.set_today(TODAY + timedelta(days=10))
    assert progress.pace(conn, sid, world["a"])["state"] == "stalled"
    answer_all(conn, quizzes.start_quiz(conn, sid, world["mods"]["Variables"]), True)
    p = progress.pace(conn, sid, world["a"])
    assert p["state"] == "on_pace" and p["remaining"] == 1


def test_lesson_completion_counts(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    lesson = conn.execute("SELECT id FROM lessons WHERE module_id = ?", (world["mods"]["Loops"],)).fetchone()[0]
    progress.complete_lesson(conn, world["asha"], lesson)
    progress.complete_lesson(conn, world["asha"], lesson)  # twice is harmless
    assert progress.course_progress(conn, world["asha"], world["a"])["lessons_done"] == 1
