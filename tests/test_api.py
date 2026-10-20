"""The bridge the window's UI talks to: permissions, error handling, the main flows."""
import json

import pytest

from app.api import Api
from services import auth


@pytest.fixture
def api(conn, db_path, world):
    auth.create_user(conn, "admin", "long-enough-1", "admin")
    a = Api(db_path)
    return a


def ok(result):
    assert result["ok"], result.get("error")
    json.dumps(result, default=str)  # everything must travel as JSON
    return result["data"]


def test_unknown_and_private_methods_are_refused(api):
    assert not api.call("does_not_exist")["ok"]
    assert not api.call("_student_id", {"student_id": 1})["ok"]
    assert not api.call("call", {"method": "state"})["ok"]


def test_staff_screens_need_sign_in(api):
    assert api.call("overview") == {"ok": False, "error": "Only staff can do that."}
    ok(api.call("login", {"username": "admin", "password": "long-enough-1"}))
    assert ok(api.call("overview"))["totals"]["students"] == 2


def test_wrong_password_message(api):
    r = api.call("login", {"username": "admin", "password": "nope-nope-nope"})
    assert r == {"ok": False, "error": "Wrong username or password."}


def test_first_run_setup_only_once(conn, db_path):
    a = Api(db_path)
    assert ok(a.call("state"))["has_users"] is False
    ok(a.call("setup_admin", {"username": "boss", "password": "long-enough-1", "repeat": "long-enough-1"}))
    assert not a.call("setup_admin", {"username": "boss2", "password": "long-enough-1", "repeat": "long-enough-1"})["ok"]


def test_students_only_act_as_themselves(api, conn, world):
    auth.create_user(conn, "asha", "long-enough-1", "student", student_id=world["asha"])
    ok(api.call("login", {"username": "asha", "password": "long-enough-1"}))
    # Asking for Ravi's home still returns Asha's.
    assert ok(api.call("learn_home", {"student_id": world["ravi"]}))["student"]["id"] == world["asha"]
    assert not api.call("students_search")["ok"]
    assert not api.call("model_retrain")["ok"]


def test_instructor_is_not_admin(api, conn):
    auth.create_instructor(conn, "Meera", "", "meera", "long-enough-1")
    ok(api.call("login", {"username": "meera", "password": "long-enough-1"}))
    ok(api.call("students_search"))
    assert api.call("users") == {"ok": False, "error": "Only the admin can do that."}


def test_learning_flow_through_the_bridge(api, world):
    ok(api.call("login", {"username": "admin", "password": "long-enough-1"}))
    sid = world["asha"]
    ok(api.call("enroll", {"student_id": sid, "course_id": world["a"]}))
    attempt = ok(api.call("quiz_start", {"student_id": sid, "module_id": world["mods"]["Variables"]}))
    answers = {str(q["id"]): q["options"][0]["id"] for q in attempt["questions"]}  # option 0 is right in the test bank
    result = ok(api.call("quiz_submit", {"attempt_id": attempt["attempt_id"], "answers": answers}))
    assert result["score"] == 100.0
    home = ok(api.call("learn_home", {"student_id": sid}))
    assert home["active"][0]["progress"]["modules_done"] == 1
    lesson = ok(api.call("lesson", {"lesson_id": 1}))
    assert {b["type"] for b in lesson["blocks"]} <= {"text", "code", "heading"}


def test_service_errors_come_back_as_messages(api, world):
    ok(api.call("login", {"username": "admin", "password": "long-enough-1"}))
    r = api.call("enroll", {"student_id": world["asha"], "course_id": world["b"]})
    assert r == {"ok": False, "error": "Finish these first: Python one."}


def test_ask_the_data_through_the_bridge(api):
    ok(api.call("login", {"username": "admin", "password": "long-enough-1"}))
    assert ok(api.call("ask", {"question": "How many students are there?"}))["rows"] == [[2]]
    assert not api.call("ask", {"question": "delete all students"})["ok"]


def test_lessons_and_pdfs_need_sign_in(api, conn):
    lesson = conn.execute("SELECT id FROM lessons LIMIT 1").fetchone()[0]
    assert api.call("lesson", {"lesson_id": lesson}) == {"ok": False, "error": "Sign in first."}
    assert api.call("certificate_pdf", {"code": "LEC-0000-0000"}) == {"ok": False, "error": "Sign in first."}
    assert api.call("courses_search")["error"] == "Only staff can do that."


def test_missing_items_and_bad_input_get_clear_messages(api):
    ok(api.call("login", {"username": "admin", "password": "long-enough-1"}))
    assert api.call("module_rename", {"module_id": 999, "title": "x"})["error"] == "That module no longer exists."
    assert api.call("course_remove", {"course_id": 999})["error"] == "That course no longer exists."
    assert api.call("learn_home", {"student_id": 999})["error"] == "That student no longer exists."
    assert api.call("certificate_revoke", {"code": "LEC-NOPE"})["error"] == "No certificate has this code."
    assert api.call("risk_predict", {"course_id": 1, "day": 45})["error"] == "Choose day 30, 60, 90 or 120."
    assert "wrong format" in api.call("student_calendar", {"student_id": 1, "year": "soon"})["error"]


def test_csv_export_stays_in_its_folder(tmp_path, monkeypatch):
    from services import reports
    monkeypatch.setattr(reports, "config", type("C", (), {"exports_dir": tmp_path / "exports"}))
    path = reports.export_csv([{"a": 1}], "../../outside")
    assert path.parent == tmp_path / "exports" and path.name == "outside.csv"
