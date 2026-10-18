"""Shared test setup: a small database built by hand, so tests run in seconds and
don't need the downloaded datasets."""
from datetime import date
from pathlib import Path

import pytest

from db import connect, init_schema
from services import clock, courses, quizzes, students

TODAY = date(2026, 10, 1)

LESSON_TEXT = {
    "Variables": (
        "A variable is a name that refers to a value stored in memory. "
        "The assignment operator stores a value in a variable. "
        "A variable name can contain letters, digits and underscores but cannot start with a digit. "
        "Python is case sensitive, so total and Total are different variables. "
        "A keyword is a reserved word that cannot be used as a variable name."
    ),
    "Loops": (
        "A loop repeats a block of code. A while loop runs as long as its condition is true. "
        "A for loop iterates over the elements of a container such as a list. "
        "A break statement exits the loop immediately. "
        "A continue statement skips to the next iteration of the loop. "
        "A nested loop is a loop inside the body of another loop."
    ),
    "Lists": (
        "A list is an ordered collection of values written inside square brackets. "
        "Each element of a list has an index that starts at zero. "
        "The append method adds an element to the end of a list. "
        "A list is mutable, so its elements can be changed after it is created. "
        "Slicing returns a new list that contains part of the original list."
    ),
}


@pytest.fixture(autouse=True)
def fixed_today():
    clock.set_today(TODAY)
    yield
    clock.set_today(None)


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    init_schema(c)
    yield c
    c.close()


def make_question(conn, module_id: int, n: int) -> int:
    return quizzes.save_question(conn, module_id, f"Question {n}?", [f"right {n}", f"wrong a{n}", f"wrong b{n}"], 0)


@pytest.fixture
def world(conn):
    """Two courses (B requires A), three modules with lessons and 5 questions each, two students."""
    a = courses.add(conn, "PY-1", "Python one", "Computer Science", "Variables and loops", pass_mark=60)
    b = courses.add(conn, "PY-2", "Python two", "Computer Science", "Lists and more", pass_mark=60)
    courses.add_prerequisite(conn, b, a)
    mods = {}
    for course_id, titles in ((a, ["Variables", "Loops"]), (b, ["Lists"])):
        for title in titles:
            mid = courses.add_module(conn, course_id, title)
            courses.save_lesson(conn, mid, f"About {title.lower()}", LESSON_TEXT[title])
            for n in range(5):
                make_question(conn, mid, n + 10 * mid)
            mods[title] = mid
    asha = students.add(conn, "Asha Verma", "asha@example.com")
    ravi = students.add(conn, "Ravi Kumar", "ravi@example.com")
    return {"a": a, "b": b, "mods": mods, "asha": asha, "ravi": ravi}


def answer_all(conn, attempt: dict, right: bool | list[bool]) -> dict:
    """Answer every question in an attempt right (True) or wrong (False)."""
    answers = {}
    for i, q in enumerate(attempt["questions"]):
        ok = right if isinstance(right, bool) else right[i]
        opt = conn.execute("SELECT id FROM question_options WHERE question_id = ? AND is_correct = ?",
                           (q["id"], int(ok))).fetchone()[0]
        answers[q["id"]] = opt
    return quizzes.submit(conn, attempt["attempt_id"], answers)
