"""Mistake review queue (the Leitner system).

A wrong answer puts the question in box 1. Each box has a waiting time before
the question comes back: box 1 = 1 day, box 2 = 3 days, box 3 = 7 days.
Answer it right and it moves up one box; wrong and it goes back to box 1.
Right in box 3 moves it to box 4: learned.

Spacing reviews out like this beats re-reading, because each review happens
just as the memory starts to fade.
"""
from datetime import date, timedelta

from services import common

WAIT_DAYS = {1: 1, 2: 3, 3: 7}
LEARNED = 4


def record(conn, student_id: int, question_id: int, correct: bool, on: date | None = None) -> None:
    """Update the queue after an answer. Call inside the caller's transaction."""
    on = on or common.today()
    row = conn.execute(
        "SELECT box FROM review_queue WHERE student_id = ? AND question_id = ?", (student_id, question_id)
    ).fetchone()
    if not correct:
        conn.execute(
            """INSERT INTO review_queue (student_id, question_id, box, due_on, last_reviewed_on, times_wrong)
               VALUES (?, ?, 1, ?, ?, 1)
               ON CONFLICT (student_id, question_id) DO UPDATE SET
                   box = 1, due_on = excluded.due_on, last_reviewed_on = excluded.last_reviewed_on,
                   times_wrong = times_wrong + 1""",
            (student_id, question_id, (on + timedelta(days=WAIT_DAYS[1])).isoformat(), on.isoformat()),
        )
    elif row is not None and row["box"] < LEARNED:
        box = row["box"] + 1
        due = on + timedelta(days=WAIT_DAYS.get(box, 0))
        conn.execute(
            """UPDATE review_queue SET box = ?, due_on = ?, last_reviewed_on = ?
               WHERE student_id = ? AND question_id = ?""",
            (box, due.isoformat(), on.isoformat(), student_id, question_id),
        )


def due(conn, student_id: int, on: date | None = None, limit: int = 20) -> list[int]:
    on = on or common.today()
    return [r[0] for r in conn.execute(
        """SELECT question_id FROM review_queue
           WHERE student_id = ? AND box < ? AND due_on <= ?
           ORDER BY box, due_on LIMIT ?""",
        (student_id, LEARNED, on.isoformat(), limit),
    )]


def summary(conn, student_id: int, on: date | None = None) -> dict:
    on = on or common.today()
    boxes = {b: 0 for b in (1, 2, 3, 4)}
    for r in conn.execute("SELECT box, COUNT(*) AS n FROM review_queue WHERE student_id = ? GROUP BY box",
                          (student_id,)):
        boxes[r["box"]] = r["n"]
    due_now = conn.execute(
        "SELECT COUNT(*) FROM review_queue WHERE student_id = ? AND box < ? AND due_on <= ?",
        (student_id, LEARNED, on.isoformat()),
    ).fetchone()[0]
    next_due = conn.execute(
        "SELECT MIN(due_on) FROM review_queue WHERE student_id = ? AND box < ? AND due_on > ?",
        (student_id, LEARNED, on.isoformat()),
    ).fetchone()[0]
    return {"boxes": boxes, "due": due_now, "next_due": next_due}
