import pytest

from services import auth
from services.common import ValidationError


def test_password_is_hashed_and_salted():
    a, b = auth.hash_password("correct horse"), auth.hash_password("correct horse")
    assert a != b  # different salt each time
    assert "correct horse" not in a
    assert auth.verify_password("correct horse", a)
    assert not auth.verify_password("wrong horse", a)


def test_login(conn):
    auth.create_user(conn, "admin", "long-enough-1", "admin")
    session = auth.login(conn, "ADMIN", "long-enough-1")  # usernames ignore case
    assert session.role == "admin" and session.is_staff
    with pytest.raises(ValidationError, match="Wrong username or password"):
        auth.login(conn, "admin", "nope-nope-nope")
    with pytest.raises(ValidationError, match="Wrong username or password"):
        auth.login(conn, "nobody", "long-enough-1")


@pytest.mark.parametrize("username, password, message", [
    ("ab", "long-enough-1", "at least 3"),
    ("bad name", "long-enough-1", "letters, numbers"),
    ("okname", "short", "at least 8"),
])
def test_new_account_rules(conn, username, password, message):
    with pytest.raises(ValidationError, match=message):
        auth.create_user(conn, username, password, "admin")


def test_username_taken(conn):
    auth.create_user(conn, "admin", "long-enough-1", "admin")
    with pytest.raises(ValidationError, match="taken"):
        auth.create_user(conn, "Admin", "long-enough-2", "admin")


def test_student_login_needs_student(conn, world):
    auth.create_user(conn, "asha", "long-enough-1", "student", student_id=world["asha"])
    assert auth.login(conn, "asha", "long-enough-1").student_id == world["asha"]


def test_change_password(conn):
    uid = auth.create_user(conn, "admin", "long-enough-1", "admin")
    with pytest.raises(ValidationError):
        auth.change_password(conn, uid, "wrong-old-pw", "new-password-1")
    auth.change_password(conn, uid, "long-enough-1", "new-password-1")
    assert auth.login(conn, "admin", "new-password-1")


def test_a_student_gets_one_login(conn, world):
    auth.create_user(conn, "asha", "long-enough-1", "student", student_id=world["asha"])
    with pytest.raises(ValidationError, match="already has a login"):
        auth.create_user(conn, "asha2", "long-enough-1", "student", student_id=world["asha"])
