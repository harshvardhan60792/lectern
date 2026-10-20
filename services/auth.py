"""Accounts and login.

Passwords are never stored. We store a scrypt hash: a slow, salted one-way
function, so even someone with the database file cannot read passwords back,
and two people with the same password get different hashes.
"""
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from db import set_current_user, transaction
from services.common import ValidationError

_N, _R, _P = 2**14, 8, 1
MIN_PASSWORD = 8


@dataclass(frozen=True)
class Session:
    user_id: int
    username: str
    role: str
    student_id: int | None
    instructor_id: int | None
    display_name: str

    @property
    def is_staff(self) -> bool:
        return self.role in ("admin", "instructor")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    return hmac.compare_digest(candidate.hex(), digest)


_DUMMY_HASH = hash_password(secrets.token_hex(8))


def has_users(conn) -> bool:
    return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


def _check_new_account(conn, username: str, password: str) -> str:
    username = username.strip()
    if len(username) < 3:
        raise ValidationError("Username needs at least 3 characters.")
    if not username.replace("_", "").replace(".", "").isalnum():
        raise ValidationError("Username can use letters, numbers, dots and underscores only.")
    if len(password) < MIN_PASSWORD:
        raise ValidationError(f"Password needs at least {MIN_PASSWORD} characters.")
    if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        raise ValidationError("That username is taken.")
    return username


def create_user(conn, username: str, password: str, role: str,
                student_id: int | None = None, instructor_id: int | None = None) -> int:
    username = _check_new_account(conn, username, password)
    if student_id is not None and conn.execute("SELECT 1 FROM users WHERE student_id = ?", (student_id,)).fetchone():
        raise ValidationError("This student already has a login.")
    with transaction(conn):
        cur = conn.execute(
            """INSERT INTO users (username, password_hash, role, student_id, instructor_id)
               VALUES (?, ?, ?, ?, ?)""",
            (username, hash_password(password), role, student_id, instructor_id),
        )
    return cur.lastrowid


def create_instructor(conn, name: str, email: str, username: str, password: str) -> int:
    name = name.strip()
    if not name:
        raise ValidationError("Name is required.")
    _check_new_account(conn, username, password)
    with transaction(conn):
        cur = conn.execute("INSERT INTO instructors (name, email) VALUES (?, ?)", (name, email.strip() or None))
        conn.execute(
            """INSERT INTO users (username, password_hash, role, instructor_id)
               VALUES (?, ?, 'instructor', ?)""",
            (username.strip(), hash_password(password), cur.lastrowid),
        )
    return cur.lastrowid


def login(conn, username: str, password: str) -> Session:
    row = conn.execute(
        """SELECT u.*, COALESCE(s.display_name, i.name, u.username) AS display_name
           FROM users u
           LEFT JOIN students s    ON s.id = u.student_id
           LEFT JOIN instructors i ON i.id = u.instructor_id
           WHERE u.username = ?""",
        (username.strip(),),
    ).fetchone()
    # Same message and the same slow hash check either way, so neither the words on
    # screen nor the time it takes reveal which usernames exist.
    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(password, stored) or row is None:
        raise ValidationError("Wrong username or password.")
    conn.execute("UPDATE users SET last_login_at = datetime('now', 'localtime') WHERE id = ?", (row["id"],))
    set_current_user(conn, row["id"])
    return Session(row["id"], row["username"], row["role"], row["student_id"], row["instructor_id"],
                   row["display_name"])


def logout(conn) -> None:
    set_current_user(conn, None)


def change_password(conn, user_id: int, old: str, new: str) -> None:
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None or not verify_password(old, row["password_hash"]):
        raise ValidationError("Current password is wrong.")
    if len(new) < MIN_PASSWORD:
        raise ValidationError(f"Password needs at least {MIN_PASSWORD} characters.")
    with transaction(conn):
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), user_id))


def reset_password(conn, user_id: int, new: str) -> None:
    """For the admin, when someone forgets their password."""
    if len(new) < MIN_PASSWORD:
        raise ValidationError(f"Password needs at least {MIN_PASSWORD} characters.")
    with transaction(conn):
        cur = conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), user_id))
    if cur.rowcount == 0:
        raise ValidationError("That account no longer exists.")


def remove_user(conn, user_id: int) -> None:
    """Removes the sign-in only. The student or instructor record stays."""
    with transaction(conn):
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount == 0:
        raise ValidationError("That account no longer exists.")


def list_users(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT u.id, u.username, u.role, u.last_login_at,
                  COALESCE(s.display_name, i.name, '') AS name
           FROM users u
           LEFT JOIN students s    ON s.id = u.student_id
           LEFT JOIN instructors i ON i.id = u.instructor_id
           ORDER BY u.role, u.username""")]
