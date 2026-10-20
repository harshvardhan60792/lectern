from datetime import date, timedelta

import pytest

from services import clock, enrollments, quizzes, review
from services.errors import ValidationError
from tests.conftest import TODAY, answer_all


def test_quiz_needs_enrollment(conn, world):
    with pytest.raises(ValidationError, match="Enroll"):
        quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"])


def test_quiz_scoring_and_progress(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    attempt = quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"], seed=1)
    assert len(attempt["questions"]) == 5
    result = answer_all(conn, attempt, [True, True, True, False, False])
    assert result["score"] == 60.0 and result["correct"] == 3
    row = conn.execute("SELECT status, best_score FROM module_progress WHERE student_id = ? AND module_id = ?",
                       (world["asha"], world["mods"]["Variables"])).fetchone()
    assert row["status"] == "completed" and row["best_score"] == 60.0  # pass mark is 60
    with pytest.raises(ValidationError, match="already submitted"):
        quizzes.submit(conn, attempt["attempt_id"], {})


def test_unanswered_counts_as_wrong(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    attempt = quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"])
    result = quizzes.submit(conn, attempt["attempt_id"], {q["id"]: None for q in attempt["questions"]})
    assert result["score"] == 0


def test_wrong_answers_enter_review_queue(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    attempt = quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"])
    answer_all(conn, attempt, False)
    s = review.summary(conn, world["asha"])
    assert s["boxes"][1] == 5
    assert s["due"] == 0 and s["next_due"] == (TODAY + timedelta(days=1)).isoformat()


def test_leitner_boxes():
    """Right answers move up a box with longer waits; a wrong answer goes back to box 1."""
    assert review.WAIT_DAYS == {1: 1, 2: 3, 3: 7}


def test_review_promotes_and_demotes(conn, world):
    sid, qid = world["asha"], conn.execute("SELECT id FROM questions LIMIT 1").fetchone()[0]
    day = date(2026, 10, 1)
    review.record(conn, sid, qid, False, day)
    box = lambda: conn.execute("SELECT box, due_on FROM review_queue WHERE question_id = ?", (qid,)).fetchone()  # noqa: E731
    assert tuple(box()) == (1, "2026-10-02")
    review.record(conn, sid, qid, True, date(2026, 10, 2))
    assert tuple(box()) == (2, "2026-10-05")
    review.record(conn, sid, qid, True, date(2026, 10, 5))
    assert tuple(box()) == (3, "2026-10-12")
    review.record(conn, sid, qid, False, date(2026, 10, 12))
    assert box()[0] == 1
    for d in (13, 16, 23):
        review.record(conn, sid, qid, True, date(2026, 10, d))
    assert box()[0] == review.LEARNED


def test_review_session_uses_due_items(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"]), False)
    with pytest.raises(ValidationError, match="Nothing is due"):
        quizzes.start_review(conn, world["asha"])
    clock.set_today(TODAY + timedelta(days=1))
    session = quizzes.start_review(conn, world["asha"])
    assert len(session["questions"]) == 5
    answer_all(conn, session, True)
    assert review.summary(conn, world["asha"])["boxes"][2] == 5


def test_finishing_every_module_issues_certificate(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    first = answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"]), True)
    assert first["certificate"] is None
    last = answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"]["Loops"]), True)
    assert last["certificate"]["code"].startswith("LEC-")
    status = conn.execute("SELECT status FROM enrollments WHERE student_id = ? AND course_id = ?",
                          (world["asha"], world["a"])).fetchone()[0]
    assert status == "completed"
    enrollments.enroll(conn, world["asha"], world["b"])  # prerequisite now met


def test_better_retake_is_recorded_in_audit_trail(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    mid = world["mods"]["Variables"]
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], mid), [True, True, False, False, False])
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], mid), True)
    audit = conn.execute("SELECT old_score, new_score FROM grade_audit").fetchall()
    assert [tuple(a) for a in audit] == [(40.0, 100.0)]


def test_question_validation(conn, world):
    mid = world["mods"]["Loops"]
    with pytest.raises(ValidationError, match="two answer options"):
        quizzes.save_question(conn, mid, "Q?", ["only one"], 0)
    with pytest.raises(ValidationError, match="same"):
        quizzes.save_question(conn, mid, "Q?", ["same", "Same"], 0)
    with pytest.raises(ValidationError, match="correct"):
        quizzes.save_question(conn, mid, "Q?", ["a", "b"], 5)


def test_skipped_questions_lower_the_score(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    attempt = quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"], seed=1)
    first = attempt["questions"][0]["id"]
    right = conn.execute("SELECT id FROM question_options WHERE question_id = ? AND is_correct = 1",
                         (first,)).fetchone()[0]
    result = quizzes.submit(conn, attempt["attempt_id"], {first: right})  # four questions left out
    assert result["score"] == 20.0 and result["total"] == 5


def test_answers_must_belong_to_the_quiz(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    attempt = quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"])
    other = conn.execute("SELECT id FROM questions WHERE module_id = ?", (world["mods"]["Loops"],)).fetchone()[0]
    with pytest.raises(ValidationError, match="isn't in this quiz"):
        quizzes.submit(conn, attempt["attempt_id"], {other: None})
