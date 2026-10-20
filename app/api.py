"""The bridge between the window's web UI and the Python services.

The UI calls one function, `call(method, payload)`. Every public method of
`Api` below is something the UI can ask for. Each returns plain data (dicts,
lists, numbers, strings) that travels to the UI as JSON.

Rules live in `services/` and `smart/`; this file only checks who is asking,
calls the right service, and shapes the answer for the screen.
"""
import inspect
import os
import sqlite3
import threading
import webbrowser
from dataclasses import asdict

from app.config import config
from db import connect, read_only, set_current_user
from services import (
    auth,
    certificates,
    common,
    courses,
    enrollments,
    progress,
    quizzes,
    reports,
    review,
    students,
)
from services.common import ValidationError
from services.enrollments import HISTORICAL
from smart import ask_data, coach, drafter, recommender, risk
from smart import text as tt


class Forbidden(ValidationError):
    pass


def signed_in(fn):
    fn.signed_in = True
    return fn


def staff_only(fn):
    fn.staff_only = True
    return fn


def admin_only(fn):
    fn.admin_only = True
    return fn


class Api:
    def __init__(self, db_path=None):
        self._local = threading.local()
        self._db_path = db_path  # None = the path from .env / the default
        self.session: auth.Session | None = None

    # Plumbing --------------------------------------------------------------------

    @property
    def conn(self):
        """One SQLite connection per thread (the window calls in from several threads)."""
        if getattr(self._local, "conn", None) is None:
            self._local.conn = connect(self._db_path)
        set_current_user(self._local.conn, self.session.user_id if self.session else None)
        return self._local.conn

    @property
    def reader(self):
        if getattr(self._local, "reader", None) is None:
            self._local.reader = read_only(self._db_path)
        return self._local.reader

    def call(self, method: str, payload: dict | None = None) -> dict:
        payload = payload or {}
        fn = getattr(self, method, None)
        if method.startswith("_") or method == "call" or not callable(fn):
            return {"ok": False, "error": f"Unknown action: {method}"}
        try:
            if getattr(fn, "signed_in", False) and self.session is None:
                raise Forbidden("Sign in first.")
            if getattr(fn, "staff_only", False) or getattr(fn, "admin_only", False):
                if self.session is None or not self.session.is_staff:
                    raise Forbidden("Only staff can do that.")
            if getattr(fn, "admin_only", False) and self.session.role != "admin":
                raise Forbidden("Only the admin can do that.")
            allowed = inspect.signature(fn).parameters
            return {"ok": True, "data": fn(**{k: v for k, v in payload.items() if k in allowed})}
        except (ValidationError, ask_data.NotUnderstood) as exc:
            return {"ok": False, "error": str(exc)}
        except (TypeError, ValueError):
            return {"ok": False, "error": "Some of the details are missing or in the wrong format."}
        except sqlite3.IntegrityError as exc:
            if "FOREIGN KEY" in str(exc):
                return {"ok": False, "error": "Something this refers to no longer exists. Refresh and try again."}
            return {"ok": False, "error": f"The database refused that: {exc}."}
        except Exception as exc:  # shown in the UI instead of failing silently
            return {"ok": False, "error": f"Something went wrong: {exc}"}

    def _need(self, table: str, row_id, what: str) -> None:
        """Refuse an action on something that was deleted (or never existed)."""
        if self.conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (row_id,)).fetchone() is None:
            raise ValidationError(f"That {what} no longer exists.")

    def _student_id(self, student_id: int | None) -> int:
        """Students act only as themselves; staff may act as an added (local) student."""
        if self.session is None:
            raise Forbidden("Sign in first.")
        if self.session.role == "student":
            return self.session.student_id
        if student_id is None:
            raise ValidationError("Choose a student.")
        self._need("students", int(student_id), "student")
        return int(student_id)

    # Session ---------------------------------------------------------------------

    def state(self):
        built = (self._db_path or config.db_path).exists()
        has_users = built and auth.has_users(self.conn)
        return {"db_ready": built, "has_users": has_users, "session": self._session_dict(),
                "today": common.today().isoformat()}

    def _session_dict(self):
        s = self.session
        if s is None:
            return None
        return {"user_id": s.user_id, "username": s.username, "role": s.role, "student_id": s.student_id,
                "display_name": s.display_name}

    def setup_admin(self, username: str, password: str, repeat: str):
        if auth.has_users(self.conn):
            raise Forbidden("An admin account already exists.")
        if password != repeat:
            raise ValidationError("The passwords don't match.")
        auth.create_user(self.conn, username, password, "admin")
        return self.login(username, password)

    def login(self, username: str, password: str):
        self.session = auth.login(self.conn, username, password)
        return self._session_dict()

    def logout(self):
        auth.logout(self.conn)
        self.session = None
        return True

    # Overview --------------------------------------------------------------------

    @staff_only
    def overview(self):
        run = risk.latest_run(self.conn)
        return {
            "totals": reports.overview(self.conn),
            "outcomes": reports.course_outcomes(self.conn, "oulad"),
            "activity": reports.activity_by_outcome(self.conn),
            "model": run,
        }

    # Students ------------------------------------------------------------------------

    @staff_only
    def students_search(self, text: str = "", source: str | None = None, offset: int = 0, limit: int = 60):
        rows, total = students.search(self.conn, text, source or None, limit, offset)
        return {"rows": rows, "total": total}

    @staff_only
    def student_profile(self, student_id: int):
        s = students.get(self.conn, student_id)
        if s is None:
            raise ValidationError("That student no longer exists.")
        enrolled = students.enrollments(self.conn, student_id)
        has_login = self.conn.execute("SELECT 1 FROM users WHERE student_id = ?", (student_id,)).fetchone() is not None
        first = enrolled[0]["course_id"] if enrolled else None
        return {
            "student": s,
            "has_login": has_login,
            "enrollments": enrolled,
            "mastery": progress.mastery_map(self.conn, student_id, first) if first else [],
            "mastery_course": first,
            "calendar": progress.calendar(self.conn, student_id),
            "streaks": progress.streaks(self.conn, student_id),
            "notes": [asdict(n) for n in coach.notes(self.conn, student_id, 4)],
        }

    @staff_only
    def student_mastery(self, student_id: int, course_id: int):
        self._need("students", student_id, "student")
        self._need("courses", course_id, "course")
        return progress.mastery_map(self.conn, student_id, course_id)

    def student_calendar(self, student_id: int | None = None, year: int | None = None):
        sid = self._student_id(student_id)
        return progress.calendar(self.conn, sid, int(year) if year else None)

    @staff_only
    def student_save(self, name: str, email: str = "", region: str = "", education: str = "",
                     student_id: int | None = None):
        if student_id:
            self._need("students", student_id, "student")
            students.update(self.conn, student_id, name, email, region, education)
            return student_id
        return students.add(self.conn, name, email, region, education)

    @staff_only
    def student_remove(self, student_id: int):
        self._need("students", student_id, "student")
        students.remove(self.conn, student_id)
        return True

    @staff_only
    def student_create_login(self, student_id: int, username: str, password: str):
        self._need("students", student_id, "student")
        auth.create_user(self.conn, username, password, "student", student_id=student_id)
        return True

    # Courses ---------------------------------------------------------------------------

    @staff_only
    def courses_search(self, text: str = "", source: str | None = None, archived: bool = False):
        rows = courses.search(self.conn, text, source or None, bool(archived))
        for r in rows:
            r["historical"] = r["source"] in HISTORICAL
        return rows

    @staff_only
    def course_detail(self, course_id: int):
        c = courses.get(self.conn, course_id)
        if c is None:
            raise ValidationError("That course no longer exists.")
        stats = next((r for r in courses.search(self.conn, include_archived=True) if r["id"] == course_id), {})
        return {
            "course": c | {"historical": c["source"] in HISTORICAL},
            "stats": stats,
            "modules": courses.modules(self.conn, course_id),
            "prerequisites": courses.prerequisites(self.conn, course_id),
            "instructors": courses.instructors(self.conn),
        }

    @staff_only
    def course_save(self, code: str, title: str, subject: str, description: str = "", pass_mark=50,
                    instructor_id: int | None = None, course_id: int | None = None):
        if course_id:
            self._need("courses", course_id, "course")
            courses.update(self.conn, course_id, code, title, subject, description, pass_mark, instructor_id)
            return course_id
        return courses.add(self.conn, code, title, subject, description, pass_mark, instructor_id)

    @staff_only
    def course_archive(self, course_id: int, archived: bool):
        self._need("courses", course_id, "course")
        courses.set_archived(self.conn, course_id, archived)
        return True

    @staff_only
    def course_remove(self, course_id: int):
        self._need("courses", course_id, "course")
        courses.remove(self.conn, course_id)
        return True

    @staff_only
    def module_add(self, course_id: int, title: str):
        self._need("courses", course_id, "course")
        return courses.add_module(self.conn, course_id, title)

    @staff_only
    def module_rename(self, module_id: int, title: str):
        self._need("modules", module_id, "module")
        courses.rename_module(self.conn, module_id, title)
        return True

    @staff_only
    def module_move(self, module_id: int, direction: int):
        self._need("modules", module_id, "module")
        courses.move_module(self.conn, module_id, direction)
        return True

    @staff_only
    def module_remove(self, module_id: int):
        self._need("modules", module_id, "module")
        courses.remove_module(self.conn, module_id)
        return True

    @staff_only
    def lessons(self, module_id: int):
        return courses.lessons(self.conn, module_id)

    @signed_in
    def lesson(self, lesson_id: int):
        lesson = courses.lesson(self.conn, lesson_id)
        if lesson is None:
            raise ValidationError("That lesson no longer exists.")
        lesson["blocks"] = _blocks(lesson["body"])
        return lesson

    @staff_only
    def lesson_save(self, module_id: int, title: str, body: str, video_url: str = "", lesson_id: int | None = None):
        self._need("modules", module_id, "module")
        return courses.save_lesson(self.conn, module_id, title, body, video_url, lesson_id)

    @staff_only
    def lesson_remove(self, lesson_id: int):
        self._need("lessons", lesson_id, "lesson")
        courses.remove_lesson(self.conn, lesson_id)
        return True

    @staff_only
    def prerequisite_add(self, course_id: int, requires_id: int):
        self._need("courses", course_id, "course")
        self._need("courses", requires_id, "course")
        courses.add_prerequisite(self.conn, course_id, requires_id)
        return True

    @staff_only
    def prerequisite_remove(self, course_id: int, requires_id: int):
        courses.remove_prerequisite(self.conn, course_id, requires_id)
        return True

    @staff_only
    def prerequisite_graph(self):
        nodes, edges = courses.prerequisite_graph(self.conn)
        return {"nodes": nodes, "edges": edges}

    @staff_only
    def course_insights(self, course_id: int):
        c = courses.get(self.conn, course_id)
        if c is None:
            raise ValidationError("That course no longer exists.")
        return {
            "weekly": reports.weekly_activity(self.conn, course_id),
            "scores": reports.score_distribution(self.conn, course_id),
            "pass_mark": c["pass_mark"],
            "materials": recommender.material_insights(self.conn, course_id),
        }

    # Enrollments ---------------------------------------------------------------------------

    def enroll(self, course_id: int, student_id: int | None = None):
        enrollments.enroll(self.conn, self._student_id(student_id), course_id)
        return True

    @staff_only
    def drop(self, student_id: int, course_id: int):
        enrollments.drop(self.conn, student_id, course_id)
        return True

    @staff_only
    def course_roster(self, course_id: int, status: str | None = None, text: str = "", offset: int = 0,
                      limit: int = 100):
        rows, total = enrollments.list_for_course(self.conn, course_id, status or None, text, limit, offset)
        return {"rows": rows, "total": total}

    # Questions ---------------------------------------------------------------------------

    @staff_only
    def question_bank(self, module_id: int, text: str = "", status: str | None = None, offset: int = 0,
                      limit: int = 80):
        rows, total = quizzes.bank(self.conn, module_id, status or None, text, limit, offset)
        return {"rows": rows, "total": total}

    @staff_only
    def question(self, question_id: int):
        self._need("questions", question_id, "question")
        return quizzes.question(self.conn, question_id)

    @staff_only
    def question_save(self, module_id: int, prompt: str, options: list, correct: int, explanation: str = "",
                      question_id: int | None = None, status: str = "live"):
        return quizzes.save_question(self.conn, module_id, prompt, options, int(correct), explanation,
                                     status=status, question_id=question_id)

    @staff_only
    def question_status(self, question_id: int, status: str):
        self._need("questions", question_id, "question")
        quizzes.set_status(self.conn, question_id, status)
        return True

    @staff_only
    def draft_questions(self, module_id: int, how_many: int = 8, text: str = ""):
        self._need("modules", module_id, "module")
        drafts = drafter.draft_for_module(self.conn, module_id, int(how_many), source_text=text.strip() or None)
        return [asdict(d) for d in drafts]

    @staff_only
    def save_drafts(self, module_id: int, drafts: list, status: str = "draft"):
        self._need("modules", module_id, "module")
        for d in drafts:
            source = d.get("sentence")
            quizzes.save_question(self.conn, module_id, d["prompt"], d["options"], int(d["correct"]),
                                  f"From the lesson: {source}" if source else "", source="drafted", status=status)
        return len(drafts)

    @staff_only
    def question_health(self, course_id: int, module_id: int | None = None):
        result = reports.question_health(self.conn, course_id, module_id)
        result["items"] = result["items"][:400]
        return result

    # Reports ---------------------------------------------------------------------------

    @staff_only
    def report(self, kind: str, field: str = "highest_education", course_id: int | None = None):
        if kind == "outcomes":
            return {"groups": reports.GROUPS, "rows": reports.outcomes_by(self.conn, field),
                    "courses": reports.course_outcomes(self.conn, None)}
        if kind == "engagement":
            return {"weekly": reports.weekly_activity(self.conn, course_id),
                    "by_result": reports.activity_by_outcome(self.conn)}
        if kind == "scores":
            self._need("courses", course_id, "course")
            return {"scores": reports.score_distribution(self.conn, course_id),
                    "pass_mark": courses.get(self.conn, course_id)["pass_mark"]}
        if kind == "trend":
            return reports.monthly_enrollments(self.conn)
        if kind == "audit":
            return reports.grade_audit(self.conn)
        raise ValidationError("Unknown report.")

    @staff_only
    def export_csv(self, name: str, rows: list):
        if not rows:
            raise ValidationError("Nothing to export.")
        path = reports.export_csv(rows, name)
        _open_path(path.parent)
        return str(path)

    # Ask the data ---------------------------------------------------------------------

    @staff_only
    def ask(self, question: str):
        result = ask_data.ask(question, self.conn, self.reader)
        result["rows"] = [list(r) for r in result["rows"]]
        return result

    @staff_only
    def ask_examples(self):
        return ask_data.EXAMPLES

    # At-risk ----------------------------------------------------------------------------

    @staff_only
    def risk_predict(self, course_id: int, day: int = 60):
        if int(day) not in (30, 60, 90, 120):
            raise ValidationError("Choose day 30, 60, 90 or 120.")
        preds = risk.predict(self.conn, course_id, int(day))
        for p in preds:
            p["nudge"] = risk.nudge(p) if p["level"] != "low" else None
            p.pop("_row", None)
        return {"predictions": preds[:600], "total": len(preds), "check": risk.check_against_outcomes(preds),
                "threshold": risk.THRESHOLD}

    @staff_only
    def model_run(self):
        return risk.latest_run(self.conn)

    @admin_only
    def model_retrain(self):
        result = risk.train(self.conn)
        return {k: v for k, v in result.items() if k != "details"}

    # Certificates --------------------------------------------------------------------------

    def certificates_list(self, text: str = "", offset: int = 0, limit: int = 80):
        if self.session and self.session.role == "student":
            rows = certificates.list_for_student(self.conn, self.session.student_id)
            return {"rows": [r | {"student": self.session.display_name} for r in rows], "total": len(rows)}
        if self.session is None or not self.session.is_staff:
            raise Forbidden("Sign in first.")
        rows, total = certificates.search(self.conn, text, limit, offset)
        return {"rows": rows, "total": total}

    def certificate_verify(self, code: str, student_name: str = "", course_title: str = "", issued_on: str = "",
                           score: str = ""):
        score_value = None
        if str(score).strip():
            try:
                score_value = float(str(score).strip().rstrip("%"))
            except ValueError:
                raise ValidationError("Score must be a number.") from None
        return certificates.verify(self.conn, code, student_name.strip() or None, course_title.strip() or None,
                                   issued_on.strip() or None, score_value)

    @signed_in
    def certificate_pdf(self, code: str):
        cert = certificates.details(self.conn, code)
        if cert is None:
            raise ValidationError("No certificate has this code.")
        if self.session and self.session.role == "student" and cert["student_id"] != self.session.student_id:
            raise Forbidden("That isn't your certificate.")
        path = certificates.render_pdf(self.conn, cert["code"], config.exports_dir / "certificates" / f"{cert['code']}.pdf")
        _open_path(path)
        return str(path)

    @admin_only
    def certificate_revoke(self, code: str):
        certificates.revoke(self.conn, code)
        return True

    # Accounts -------------------------------------------------------------------------------

    @admin_only
    def users(self):
        return auth.list_users(self.conn)

    @admin_only
    def instructor_add(self, name: str, email: str, username: str, password: str):
        auth.create_instructor(self.conn, name, email, username, password)
        return True

    def password_change(self, old: str, new: str, repeat: str):
        if self.session is None:
            raise Forbidden("Sign in first.")
        if new != repeat:
            raise ValidationError("The new passwords don't match.")
        auth.change_password(self.conn, self.session.user_id, old, new)
        return True

    # Learning (student side; staff can open an added student's view) -------------------------------

    def learn_home(self, student_id: int | None = None):
        sid = self._student_id(student_id)
        s = students.get(self.conn, sid)
        mine = students.enrollments(self.conn, sid)
        active = []
        for e in mine:
            if e["status"] == "active" and e["source"] not in HISTORICAL:
                active.append(e | {
                    "progress": progress.course_progress(self.conn, sid, e["course_id"]),
                    "pace": progress.pace(self.conn, sid, e["course_id"]),
                    "mastery": progress.mastery_map(self.conn, sid, e["course_id"]),
                })
        return {
            "student": s,
            "today": common.today().isoformat(),
            "streaks": progress.streaks(self.conn, sid),
            "review": review.summary(self.conn, sid),
            "active": active,
            "finished": len(mine) - len(active),
            "certificates": certificates.list_for_student(self.conn, sid),
            "notes": [asdict(n) for n in coach.notes(self.conn, sid, 3)],
            "plan": coach.week_plan(self.conn, sid),
            "recommendations": recommender.recommend_courses(self.conn, sid, 3),
            "calendar": progress.calendar(self.conn, sid),
        }

    def learn_course(self, course_id: int, student_id: int | None = None):
        sid = self._student_id(student_id)
        c = courses.get(self.conn, course_id)
        if c is None:
            raise ValidationError("That course no longer exists.")
        tiles = {t["module_id"]: t for t in progress.mastery_map(self.conn, sid, course_id)}
        mods = []
        for m in courses.modules(self.conn, course_id):
            done = progress.lessons_done(self.conn, sid, m["id"])
            mods.append(m | {"mastery": tiles.get(m["id"]), "lessons_list": [
                lesson | {"done": lesson["id"] in done} for lesson in courses.lessons(self.conn, m["id"])]})
        return {"course": c, "progress": progress.course_progress(self.conn, sid, course_id),
                "pace": progress.pace(self.conn, sid, course_id), "modules": mods}

    def lesson_complete(self, lesson_id: int, student_id: int | None = None):
        progress.complete_lesson(self.conn, self._student_id(student_id), lesson_id)
        return True

    def quiz_start(self, module_id: int, student_id: int | None = None):
        return quizzes.start_quiz(self.conn, self._student_id(student_id), module_id)

    def review_start(self, student_id: int | None = None):
        return quizzes.start_review(self.conn, self._student_id(student_id))

    def quiz_submit(self, attempt_id: int, answers: dict):
        attempt = self.conn.execute("SELECT student_id FROM quiz_attempts WHERE id = ?", (attempt_id,)).fetchone()
        if attempt is None:
            raise ValidationError("Unknown attempt.")
        self._student_id(attempt["student_id"])
        if self.session.role == "student" and attempt["student_id"] != self.session.student_id:
            raise Forbidden("That isn't your quiz.")
        return quizzes.submit(self.conn, attempt_id, {int(k): (int(v) if v else None) for k, v in answers.items()})

    def catalog(self, student_id: int | None = None):
        sid = self._student_id(student_id)
        mine = {r["course_id"]: r["status"] for r in self.conn.execute(
            "SELECT course_id, status FROM enrollments WHERE student_id = ?", (sid,))}
        out = []
        for c in courses.search(self.conn):
            if c["source"] in HISTORICAL:
                continue
            full = courses.get(self.conn, c["id"])
            out.append(c | {
                "description": full["description"], "attribution": full["attribution"], "pass_mark": full["pass_mark"],
                "status": mine.get(c["id"]),
                "requires": courses.prerequisites(self.conn, c["id"]),
                "missing": enrollments.missing_prerequisites(self.conn, sid, c["id"]),
                "lessons": self.conn.execute(
                    "SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id = l.module_id WHERE m.course_id = ?",
                    (c["id"],)).fetchone()[0],
                "questions": self.conn.execute(
                    "SELECT COUNT(*) FROM questions q JOIN modules m ON m.id = q.module_id "
                    "WHERE m.course_id = ? AND q.status = 'live'", (c["id"],)).fetchone()[0],
            })
        return out

    def open_url(self, url: str):
        if not str(url).startswith(("https://", "http://")):
            raise ValidationError("Only web links can be opened.")
        webbrowser.open(url)
        return True


def _blocks(body: str) -> list[dict]:
    """Split lesson text into prose paragraphs and code samples for the reader."""
    blocks: list[dict] = []
    in_code = False
    for line in body.split("\n"):
        code = tt.looks_like_python(line) or (in_code and line.startswith(" ") and line.strip() != "")
        if not line.strip():
            in_code = False
            continue
        stripped = line.strip()
        heading = (not code and len(stripped.split()) <= 6 and stripped[:1].isupper()
                   and not stripped.endswith((".", ",", ":", "?", "!", ")")) and not stripped.startswith("•"))
        kind = "code" if code else "heading" if heading else "text"
        if blocks and blocks[-1]["type"] == kind == "code":
            blocks[-1]["text"] += "\n" + line
        else:
            blocks.append({"type": kind, "text": line})
        in_code = code
    return blocks


def _open_path(path) -> None:
    try:
        os.startfile(path)  # Windows: open in Explorer / the PDF viewer
    except (AttributeError, OSError):
        pass

