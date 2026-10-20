"""Ask the data, question drafter, coach and recommender."""
import pytest

from db import read_only
from services import enrollments, quizzes
from smart import ask_data, coach, drafter, recommender
from tests.conftest import LESSON_TEXT, answer_all

# Ask the data -------------------------------------------------------------------

WORKING = [
    "How many students are there?",
    "How many students withdrew?",
    "list students",
    "show courses",
    "Average score per course",
    "Top 5 students by score",
    "Completion rate by course",
    "Withdrawal rate per course",
    "How many certificates were issued in 2026?",
    "How many enrollments per course",
    "Number of questions per module",
    "Average accuracy by module",
    "students with a score below 40",
    "how many students with a score above 50",
    "Courses with the highest completion rate",
    "Total clicks by month",
    "How many enrollments in pyhton one",
    "enrollments this month",
]


@pytest.fixture
def asked(conn, db_path, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"]), [True, False] * 3)
    reader = read_only(db_path)
    yield lambda q: ask_data.ask(q, conn, reader)
    reader.close()


@pytest.mark.parametrize("question", WORKING)
def test_questions_run(asked, question):
    result = asked(question)
    assert result["sql"].lstrip().upper().startswith("SELECT")
    assert result["understood"]


def test_answers_are_right(asked, world):
    assert asked("How many students are there?")["rows"] == [(2,)]
    assert asked("How many enrollments in pyhton one")["rows"] == [(1,)]
    rows = dict((r[0], r[1]) for r in asked("Average score per course")["rows"])
    assert rows == {"PY-1": 60.0}


@pytest.mark.parametrize("question", [
    "delete all students",
    "DROP TABLE students",
    "show students; drop table courses",
    "update every score to 100",
    "students -- comment",
    "insert a student called Bob",
])
def test_changes_are_refused(asked, question):
    with pytest.raises(ask_data.NotUnderstood):
        asked(question)


def test_typed_values_are_parameters_not_sql(asked):
    result = asked("how many students in o'brien course")
    assert "o'brien" not in result["sql"].lower()


def test_gibberish_is_not_understood(asked):
    with pytest.raises(ask_data.NotUnderstood):
        asked("hello there")


def test_read_only_connection_cannot_write(asked, db_path):
    reader = read_only(db_path)
    with pytest.raises(Exception):
        reader.execute("DELETE FROM students")


def test_safety_check_rejects_non_select():
    for bad in ("DELETE FROM students", "SELECT 1; DROP TABLE x", "PRAGMA writable_schema = 1"):
        with pytest.raises(ask_data.NotUnderstood):
            ask_data.check_safe(bad)


# Drafter ------------------------------------------------------------------------

def test_drafter_makes_valid_questions():
    corpus = [LESSON_TEXT["Loops"], LESSON_TEXT["Lists"]] * 3
    drafts = drafter.draft(LESSON_TEXT["Variables"] + " " + LESSON_TEXT["Lists"], corpus, how_many=5)
    assert drafts
    for d in drafts:
        assert len(d.options) == 4 and len(set(d.options)) == 4
        assert d.options[d.correct] == d.term
        assert d.term.lower() not in d.prompt.lower().replace("_____", "")


def test_drafter_needs_enough_text():
    assert drafter.draft("Too short.", ["Also short."]) == []


# Coach and recommender --------------------------------------------------------------

def test_coach_with_no_courses_recommends_one(conn, world):
    notes = coach.notes(conn, world["asha"])
    assert notes[0].rule == "no-courses" and "Python one" in notes[0].text


def test_coach_flags_weak_module_and_due_reviews(conn, world):
    from datetime import timedelta

    from services import common
    from tests.conftest import TODAY
    enrollments.enroll(conn, world["asha"], world["a"])
    answer_all(conn, quizzes.start_quiz(conn, world["asha"], world["mods"]["Variables"]), False)
    common.set_today(TODAY + timedelta(days=1))
    rules = {n.rule for n in coach.notes(conn, world["asha"], limit=0)}
    assert {"reviews-due", "weak-module"} <= rules
    plan = coach.week_plan(conn, world["asha"])
    assert len(plan) == 7 and plan[0]["tasks"][0].startswith("Review 5")


def test_recommender_respects_prerequisites(conn, world):
    enrollments.enroll(conn, world["asha"], world["a"])
    recs = recommender.recommend_courses(conn, world["asha"])
    assert recs and recs[0]["code"] == "PY-2" and recs[0]["locked"]
    assert "Unlocks after Python one" in recs[0]["reason"]
