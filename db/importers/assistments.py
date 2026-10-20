"""Import the ASSISTments 2009–2010 skill-builder log.

Source: ASSISTments (Worcester Polytechnic Institute), "2009-2010 ASSISTment
Skill Builder Data", mirror https://doi.org/10.6084/m9.figshare.25309000.
Free for research and education with citation.

Each row is one student answering one maths problem. Rows are repeated once
per skill a problem is tagged with, so we keep one row per order_id. We keep
only "original" problems (not the scaffolding sub-steps). The log has no dates,
only an order number, which we keep as `seq`.
"""
import csv
import sqlite3
from pathlib import Path

from db import transaction

ATTRIBUTION = "Data: ASSISTments 2009–2010 Skill Builder dataset (WPI), used with citation."


def run(conn: sqlite3.Connection, raw_dir: Path, log=print) -> None:
    path = raw_dir / "assistments" / "skill_builder_data.csv"
    log("ASSISTments: reading log")

    problem_skill: dict[str, tuple[int, str]] = {}
    answers: dict[str, tuple] = {}
    with open(path, newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            if r["original"] != "1":
                continue
            skill_id = int(r["skill_id"]) if r["skill_id"] not in ("", "NA") else 10**9
            skill = r["skill_name"].strip() or "Unlabelled skill"
            current = problem_skill.get(r["problem_id"])
            if current is None or skill_id < current[0]:
                problem_skill[r["problem_id"]] = (skill_id, skill)
            if r["order_id"] not in answers:
                answers[r["order_id"]] = (
                    r["user_id"], r["problem_id"], 1 if r["correct"] == "1" else 0,
                    int(r["order_id"]), int(r["attempt_count"] or 0), int(r["hint_count"] or 0),
                )

    with transaction(conn):
        log("ASSISTments: course and skills")
        cur = conn.execute(
            """INSERT INTO courses (code, title, subject, description, source, attribution)
               VALUES ('ASSIST-0910', 'Maths skill builder 2009–10', 'Mathematics', ?, 'assistments', ?)""",
            ("Middle-school maths practice, 2009–10 school year. Each module is one skill.",
             ATTRIBUTION),
        )
        course_id = cur.lastrowid

        skills = sorted({skill for _, skill in problem_skill.values()}, key=lambda s: (s == "Unlabelled skill", s))
        module_ids = {}
        for pos, skill in enumerate(skills, start=1):
            cur = conn.execute(
                "INSERT INTO modules (course_id, position, title, kind) VALUES (?, ?, ?, 'skill')",
                (course_id, pos, skill),
            )
            module_ids[skill] = cur.lastrowid

        log(f"ASSISTments: {len(problem_skill):,} problems")
        question_ids = {}
        for problem_id, (_, skill) in problem_skill.items():
            cur = conn.execute(
                """INSERT INTO questions (module_id, source, external_id, prompt)
                   VALUES (?, 'assistments', ?, NULL)""",
                (module_ids[skill], problem_id),
            )
            question_ids[problem_id] = cur.lastrowid

        log("ASSISTments: students")
        student_ids = {}
        for user in sorted({a[0] for a in answers.values()}, key=int):
            cur = conn.execute(
                "INSERT INTO students (source, external_id, display_name) VALUES ('assistments', ?, ?)",
                (user, f"Student {user}"),
            )
            student_ids[user] = cur.lastrowid
        conn.executemany(
            "INSERT INTO enrollments (student_id, course_id, status) VALUES (?, ?, 'active')",
            [(sid, course_id) for sid in student_ids.values()],
        )

        log(f"ASSISTments: {len(answers):,} answers")
        conn.executemany(
            """INSERT INTO responses (student_id, question_id, is_correct, seq, attempt_count, hint_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (student_ids[u], question_ids[p], ok, seq, attempts, hints)
                for u, p, ok, seq, attempts, hints in answers.values()
            ],
        )
