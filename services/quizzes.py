"""Question bank, quizzes, grading.

A quiz is drawn from a module's question bank each time, so a student who
retakes it gets a fresh mix, with questions they haven't yet got right first.
"""
import random
from datetime import datetime

from db import transaction
from services import clock, enrollments, review
from services.errors import ValidationError

QUIZ_SIZE = 10


# Question bank -----------------------------------------------------------------

def bank(conn, module_id: int, status: str | None = "live", text: str = "", limit: int = 200,
         offset: int = 0) -> tuple[list[dict], int]:
    where, params = ["q.module_id = ?"], [module_id]
    if status:
        where.append("q.status = ?")
        params.append(status)
    if text.strip():
        where.append("q.prompt LIKE ?")
        params.append(f"%{text.strip()}%")
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM questions q WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT q.id, q.source, q.external_id, q.prompt, q.status,
                   (SELECT COUNT(*) FROM responses r WHERE r.question_id = q.id) AS answers,
                   (SELECT ROUND(100.0 * AVG(r.is_correct), 0) FROM responses r WHERE r.question_id = q.id) AS pct_correct
            FROM questions q WHERE {clause} ORDER BY q.id LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def question(conn, question_id: int) -> dict | None:
    row = conn.execute(
        """SELECT q.*, m.title AS module_title, m.course_id FROM questions q
           JOIN modules m ON m.id = q.module_id WHERE q.id = ?""",
        (question_id,),
    ).fetchone()
    if row is None:
        return None
    q = dict(row)
    q["options"] = [dict(o) for o in conn.execute(
        "SELECT id, position, text, is_correct FROM question_options WHERE question_id = ? ORDER BY position",
        (question_id,),
    )]
    return q


def save_question(conn, module_id: int, prompt: str, options: list[str], correct: int,
                  explanation: str = "", source: str = "manual", status: str = "live",
                  question_id: int | None = None) -> int:
    prompt = prompt.strip()
    options = [o.strip() for o in options if o.strip()]
    if not prompt:
        raise ValidationError("The question needs some text.")
    if len(options) < 2:
        raise ValidationError("Give at least two answer options.")
    if len({o.lower() for o in options}) != len(options):
        raise ValidationError("Two options are the same.")
    if not 0 <= correct < len(options):
        raise ValidationError("Mark which option is correct.")
    with transaction(conn):
        if question_id:
            conn.execute("UPDATE questions SET prompt = ?, explanation = ?, status = ? WHERE id = ?",
                         (prompt, explanation.strip() or None, status, question_id))
            conn.execute("DELETE FROM question_options WHERE question_id = ?", (question_id,))
        else:
            cur = conn.execute(
                "INSERT INTO questions (module_id, source, prompt, explanation, status) VALUES (?, ?, ?, ?, ?)",
                (module_id, source, prompt, explanation.strip() or None, status),
            )
            question_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO question_options (question_id, position, text, is_correct) VALUES (?, ?, ?, ?)",
            [(question_id, i + 1, text, int(i == correct)) for i, text in enumerate(options)],
        )
    return question_id


def set_status(conn, question_id: int, status: str) -> None:
    if status not in ("live", "draft", "retired"):
        raise ValidationError("Unknown status.")
    with transaction(conn):
        conn.execute("UPDATE questions SET status = ? WHERE id = ?", (status, question_id))


# Taking quizzes ----------------------------------------------------------------

def _load_questions(conn, ids: list[int]) -> list[dict]:
    out = []
    for qid in ids:
        q = conn.execute("SELECT id, prompt, module_id FROM questions WHERE id = ?", (qid,)).fetchone()
        opts = conn.execute(
            "SELECT id, text FROM question_options WHERE question_id = ? ORDER BY position", (qid,)
        ).fetchall()
        out.append({"id": q["id"], "prompt": q["prompt"], "module_id": q["module_id"],
                    "options": [dict(o) for o in opts]})
    return out


def _require_enrolled(conn, student_id: int, module_id: int) -> int:
    row = conn.execute(
        """SELECT e.status, m.course_id FROM modules m
           LEFT JOIN enrollments e ON e.course_id = m.course_id AND e.student_id = ?
           WHERE m.id = ?""",
        (student_id, module_id),
    ).fetchone()
    if row is None:
        raise ValidationError("That module doesn't exist.")
    if row["status"] not in ("active", "completed"):
        raise ValidationError("Enroll in the course before taking its quizzes.")
    return row["course_id"]


def start_quiz(conn, student_id: int, module_id: int, size: int = QUIZ_SIZE, seed: int | None = None) -> dict:
    _require_enrolled(conn, student_id, module_id)
    rows = conn.execute(
        """SELECT q.id,
                  EXISTS (SELECT 1 FROM responses r WHERE r.question_id = q.id AND r.student_id = ?
                          AND r.is_correct = 1) AS known
           FROM questions q
           WHERE q.module_id = ? AND q.status = 'live'
             AND EXISTS (SELECT 1 FROM question_options o WHERE o.question_id = q.id)""",
        (student_id, module_id),
    ).fetchall()
    if not rows:
        raise ValidationError("This module has no quiz questions yet.")
    rng = random.Random(seed)
    fresh = [r["id"] for r in rows if not r["known"]]
    known = [r["id"] for r in rows if r["known"]]
    rng.shuffle(fresh)
    rng.shuffle(known)
    chosen = (fresh + known)[:size]
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO quiz_attempts (student_id, module_id, kind, n_questions) VALUES (?, ?, 'quiz', ?)",
            (student_id, module_id, len(chosen)),
        )
    return {"attempt_id": cur.lastrowid, "kind": "quiz", "questions": _load_questions(conn, chosen)}


def start_review(conn, student_id: int) -> dict:
    ids = review.due(conn, student_id)
    if not ids:
        raise ValidationError("Nothing is due for review today.")
    module_id = conn.execute("SELECT module_id FROM questions WHERE id = ?", (ids[0],)).fetchone()[0]
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO quiz_attempts (student_id, module_id, kind, n_questions) VALUES (?, ?, 'review', ?)",
            (student_id, module_id, len(ids)),
        )
    return {"attempt_id": cur.lastrowid, "kind": "review", "questions": _load_questions(conn, ids)}


def submit(conn, attempt_id: int, answers: dict[int, int | None]) -> dict:
    """Grade an attempt. `answers` maps question id -> chosen option id (or None).

    In one transaction: store each answer, update the review queue, record the
    score on the module, log the day's activity and, if the course is now
    finished, complete it and issue the certificate.
    """
    attempt = conn.execute("SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if attempt is None:
        raise ValidationError("Unknown attempt.")
    if attempt["finished_at"]:
        raise ValidationError("This attempt was already submitted.")
    student_id = attempt["student_id"]
    today = clock.today()
    now = f"{today.isoformat()} {datetime.now():%H:%M:%S}"

    feedback, correct_count, modules_touched = [], 0, {}
    with transaction(conn):
        for qid, chosen in answers.items():
            q = conn.execute("SELECT module_id, explanation, prompt FROM questions WHERE id = ?", (qid,)).fetchone()
            right = conn.execute(
                "SELECT id, text FROM question_options WHERE question_id = ? AND is_correct = 1", (qid,)
            ).fetchone()
            ok = chosen is not None and right is not None and chosen == right["id"]
            correct_count += ok
            modules_touched.setdefault(q["module_id"], [0, 0])
            modules_touched[q["module_id"]][0] += ok
            modules_touched[q["module_id"]][1] += 1
            conn.execute(
                """INSERT INTO responses (student_id, question_id, attempt_id, chosen_option_id, is_correct, answered_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (student_id, qid, attempt_id, chosen, int(ok), now),
            )
            review.record(conn, student_id, qid, ok, today)
            feedback.append({"question_id": qid, "prompt": q["prompt"], "correct": ok,
                             "chosen_option_id": chosen, "right_answer": right["text"] if right else None,
                             "explanation": q["explanation"]})

        total = max(1, len(answers))
        score = round(100.0 * correct_count / total, 1)
        conn.execute("UPDATE quiz_attempts SET finished_at = ?, score = ? WHERE id = ?", (now, score, attempt_id))

        certificate = None
        if attempt["kind"] == "quiz":
            pass_mark = conn.execute(
                "SELECT c.pass_mark FROM modules m JOIN courses c ON c.id = m.course_id WHERE m.id = ?",
                (attempt["module_id"],),
            ).fetchone()[0]
            status = "completed" if score >= pass_mark else "in_progress"
            conn.execute(
                """INSERT INTO module_progress (student_id, module_id, status, best_score, last_score, completed_on)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (student_id, module_id) DO UPDATE SET
                       best_score = MAX(COALESCE(best_score, 0), excluded.best_score),
                       last_score = excluded.last_score,
                       status = CASE WHEN status = 'completed' THEN 'completed' ELSE excluded.status END,
                       completed_on = COALESCE(completed_on, excluded.completed_on),
                       updated_at = datetime('now', 'localtime')""",
                (student_id, attempt["module_id"], status, score, score,
                 today.isoformat() if status == "completed" else None),
            )
        course_id = conn.execute("SELECT course_id FROM modules WHERE id = ?", (attempt["module_id"],)).fetchone()[0]
        log_activity(conn, student_id, course_id, len(answers))
        if attempt["kind"] == "quiz":
            certificate = enrollments.check_completion(conn, student_id, course_id)

    return {"score": score, "correct": correct_count, "total": total, "feedback": feedback,
            "certificate": certificate, "kind": attempt["kind"]}


def log_activity(conn, student_id: int, course_id: int, amount: int = 1) -> None:
    conn.execute(
        """INSERT INTO activity_days (student_id, course_id, day, clicks) VALUES (?, ?, ?, ?)
           ON CONFLICT (student_id, course_id, day) DO UPDATE SET clicks = clicks + excluded.clicks""",
        (student_id, course_id, clock.today().isoformat(), amount),
    )


def history(conn, student_id: int, limit: int = 20) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT a.id, a.kind, a.finished_at, a.score, a.n_questions, m.title AS module_title, c.title AS course_title
           FROM quiz_attempts a JOIN modules m ON m.id = a.module_id JOIN courses c ON c.id = m.course_id
           WHERE a.student_id = ? AND a.finished_at IS NOT NULL
           ORDER BY a.finished_at DESC LIMIT ?""",
        (student_id, limit),
    )]
