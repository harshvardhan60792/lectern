"""Import the Open University Learning Analytics Dataset (OULAD).

Source: Kuzilek, J., Hlosta, M. & Zdrahal, Z. Open University Learning Analytics
dataset. Sci Data 4, 170171 (2017). https://doi.org/10.1038/sdata.2017.171
Licence: CC BY 4.0.

All OULAD dates are "days since the module-presentation started". The dataset
only says presentations start in February ("B") or October ("J"), so we place
day 0 on the 1st of that month. That is the one assumption in this import.
"""
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from db import transaction
from services.certificates import certificate_code, fingerprint

# Module domains as published in the OULAD paper (Table 1).
DOMAINS = {
    "AAA": "Social Sciences", "BBB": "Social Sciences", "GGG": "Social Sciences",
    "CCC": "STEM", "DDD": "STEM", "EEE": "STEM", "FFF": "STEM",
}
STATUS = {"Pass": "completed", "Distinction": "completed", "Fail": "failed", "Withdrawn": "withdrawn"}
ATTRIBUTION = "Data: Open University Learning Analytics Dataset (Kuzilek et al., 2017), CC BY 4.0."


def term_start(presentation: str) -> date:
    year, term = int(presentation[:4]), presentation[4]
    return date(year, 2 if term == "B" else 10, 1)


def term_label(presentation: str) -> str:
    return f"{'Feb' if presentation[4] == 'B' else 'Oct'} {presentation[:4]}"


def _day(start: date, offset: str | int | None) -> str | None:
    if offset in (None, "", "?"):
        return None
    return (start + timedelta(days=int(float(offset)))).isoformat()


def _rows(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def run(conn: sqlite3.Connection, raw_dir: Path, stage_dir: Path, log=print) -> None:
    src = raw_dir / "oulad"

    with transaction(conn):
        # Courses: one per module-presentation, e.g. AAA-2013J
        log("OULAD: courses")
        courses = {}
        for r in _rows(src / "courses.csv"):
            mod, pres = r["code_module"], r["code_presentation"]
            start = term_start(pres)
            code = f"{mod}-{pres}"
            title = f"{DOMAINS[mod]} module {mod} · {term_label(pres)}"
            desc = (f"{DOMAINS[mod]} module {mod}, {term_label(pres)} run, "
                    f"{r['module_presentation_length']} days long.")
            cur = conn.execute(
                """INSERT INTO courses (code, title, subject, description, source, starts_on, length_days, attribution)
                   VALUES (?, ?, ?, ?, 'oulad', ?, ?, ?)""",
                (code, title, DOMAINS[mod], desc, start.isoformat(), int(r["module_presentation_length"]), ATTRIBUTION),
            )
            courses[(mod, pres)] = {"id": cur.lastrowid, "start": start, "length": int(r["module_presentation_length"])}

        # Assessments become the modules of each course, in date order.
        log("OULAD: assessments")
        by_course: dict[tuple, list] = {}
        for r in _rows(src / "assessments.csv"):
            by_course.setdefault((r["code_module"], r["code_presentation"]), []).append(r)
        assessment_module = {}
        for key, items in by_course.items():
            course = courses[key]
            items.sort(key=lambda a: (int(a["date"]) if a["date"] not in ("", "?") else course["length"]))
            counts: dict[str, int] = {}
            for pos, a in enumerate(items, start=1):
                kind = a["assessment_type"]
                counts[kind] = counts.get(kind, 0) + 1
                title = "Final exam" if kind == "Exam" else f"{kind} {counts[kind]}"
                due = int(a["date"]) if a["date"] not in ("", "?") else course["length"]
                cur = conn.execute(
                    """INSERT INTO modules (course_id, position, title, kind, external_id, weight, due_day)
                       VALUES (?, ?, ?, 'assessment', ?, ?, ?)""",
                    (course["id"], pos, title, a["id_assessment"], float(a["weight"]), due),
                )
                assessment_module[a["id_assessment"]] = (cur.lastrowid, course)

        log("OULAD: learning materials")
        conn.executemany(
            """INSERT INTO materials (course_id, external_id, activity_type, week_from, week_to)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (courses[(r["code_module"], r["code_presentation"])]["id"], r["id_site"], r["activity_type"],
                 None if r["week_from"] in ("", "?") else int(r["week_from"]),
                 None if r["week_to"] in ("", "?") else int(r["week_to"]))
                for r in _rows(src / "vle.csv")
            ],
        )

        log("OULAD: students")
        info = list(_rows(src / "studentInfo.csv"))
        student_ids: dict[str, int] = {}
        for r in info:
            ext = r["id_student"]
            if ext in student_ids:
                continue
            cur = conn.execute(
                """INSERT INTO students (source, external_id, display_name, gender, region,
                                         highest_education, age_band, imd_band, disability)
                   VALUES ('oulad', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ext, f"Student {ext}", r["gender"], r["region"], r["highest_education"], r["age_band"],
                 None if r["imd_band"] in ("", "?") else r["imd_band"], r["disability"]),
            )
            student_ids[ext] = cur.lastrowid

        log("OULAD: enrollments")
        registration = {
            (r["code_module"], r["code_presentation"], r["id_student"]): r
            for r in _rows(src / "studentRegistration.csv")
        }
        enrollment_rows = []
        for r in info:
            key = (r["code_module"], r["code_presentation"])
            course = courses[key]
            reg = registration.get((*key, r["id_student"]), {})
            status = STATUS[r["final_result"]]
            if status == "withdrawn":
                ended = _day(course["start"], reg.get("date_unregistration"))
            else:
                ended = _day(course["start"], course["length"])
            enrollment_rows.append((
                student_ids[r["id_student"]], course["id"], _day(course["start"], reg.get("date_registration")),
                status, ended, r["final_result"], int(r["num_of_prev_attempts"]), int(r["studied_credits"]),
            ))
        conn.executemany(
            """INSERT INTO enrollments (student_id, course_id, enrolled_on, status, ended_on, final_result,
                                        prev_attempts, studied_credits)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            enrollment_rows,
        )

        log("OULAD: assessment scores")
        progress = []
        for r in _rows(src / "studentAssessment.csv"):
            if r["score"] in ("", "?") or r["id_assessment"] not in assessment_module:
                continue
            module_id, course = assessment_module[r["id_assessment"]]
            score = min(100.0, max(0.0, float(r["score"])))
            progress.append((student_ids[r["id_student"]], module_id, score, score,
                             _day(course["start"], r["date_submitted"])))
        conn.executemany(
            """INSERT OR IGNORE INTO module_progress (student_id, module_id, status, best_score, last_score, completed_on)
               VALUES (?, ?, 'completed', ?, ?, ?)""",
            progress,
        )

    _import_clicks(conn, src, stage_dir, log)

    with transaction(conn):
        log("OULAD: certificates for passed enrollments")
        rows = conn.execute(
            """SELECT e.student_id, e.course_id, e.ended_on, e.final_result, s.display_name, c.title,
                      -- Same rule as services.certificates.course_score: weighted average, or a plain
                      -- average when the assessments taken carry no weight (some OU modules weight TMAs 0).
                      (SELECT ROUND(COALESCE(SUM(mp.best_score * m.weight) / NULLIF(SUM(m.weight), 0),
                                             AVG(mp.best_score)), 1)
                       FROM modules m JOIN module_progress mp
                         ON mp.module_id = m.id AND mp.student_id = e.student_id
                       WHERE m.course_id = e.course_id) AS score
               FROM enrollments e
               JOIN students s ON s.id = e.student_id
               JOIN courses c  ON c.id = e.course_id
               WHERE c.source = 'oulad' AND e.status = 'completed'"""
        ).fetchall()
        certs = []
        for r in rows:
            code = certificate_code(r["student_id"], r["course_id"])
            fp = fingerprint(code, r["display_name"], r["title"], r["ended_on"], r["score"])
            certs.append((code, r["student_id"], r["course_id"], r["ended_on"], r["score"], r["final_result"], fp))
        conn.executemany(
            """INSERT INTO certificates (code, student_id, course_id, issued_on, score, grade, fingerprint)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            certs,
        )


def _import_clicks(conn: sqlite3.Connection, src: Path, stage_dir: Path, log) -> None:
    """studentVle.csv has 10.6 million rows. Stream it into a staging database on
    disk, then let SQLite aggregate it to one row per student per day, so memory
    use stays small."""
    stage_dir.mkdir(parents=True, exist_ok=True)
    stage_path = stage_dir / "oulad_vle.db"
    if stage_path.exists():
        stage_path.unlink()
    stage = sqlite3.connect(stage_path)
    stage.execute("PRAGMA journal_mode = OFF")
    stage.execute("PRAGMA synchronous = OFF")
    stage.execute(
        "CREATE TABLE vle (module TEXT, pres TEXT, student TEXT, site TEXT, day INTEGER, clicks INTEGER)"
    )

    log("OULAD: staging 10.6M click rows (takes a minute or two)")
    batch = []
    with open(src / "studentVle.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for i, row in enumerate(reader, start=1):
            batch.append(row)
            if len(batch) == 200_000:
                stage.executemany("INSERT INTO vle VALUES (?, ?, ?, ?, ?, ?)", batch)
                batch.clear()
            if i % 2_000_000 == 0:
                log(f"  {i:,} rows")
        if batch:
            stage.executemany("INSERT INTO vle VALUES (?, ?, ?, ?, ?, ?)", batch)
    stage.commit()
    stage.close()

    conn.execute("ATTACH DATABASE ? AS stage", (str(stage_path),))
    try:
        with transaction(conn):
            log("OULAD: daily activity")
            conn.execute(
                """INSERT INTO activity_days (student_id, course_id, day, clicks)
                   SELECT s.id, c.id, date(c.starts_on, printf('%+d days', v.day)), SUM(v.clicks)
                   FROM stage.vle v
                   JOIN courses c  ON c.code = v.module || '-' || v.pres
                   JOIN students s ON s.source = 'oulad' AND s.external_id = v.student
                   GROUP BY s.id, c.id, v.day"""
            )
            log("OULAD: material use")
            conn.execute(
                """INSERT INTO material_use (student_id, material_id, clicks, first_day, last_day)
                   SELECT s.id, m.id, SUM(v.clicks),
                          date(c.starts_on, printf('%+d days', MIN(v.day))),
                          date(c.starts_on, printf('%+d days', MAX(v.day)))
                   FROM stage.vle v
                   JOIN courses c   ON c.code = v.module || '-' || v.pres
                   JOIN materials m ON m.course_id = c.id AND m.external_id = v.site
                   JOIN students s  ON s.source = 'oulad' AND s.external_id = v.student
                   GROUP BY s.id, m.id"""
            )
    finally:
        conn.execute("DETACH DATABASE stage")
    stage_path.unlink(missing_ok=True)
