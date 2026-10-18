# Learning tasks: worked answers

These are the answers for L1 and L3–L7 in `docs/plan/LEARN.md`, done so you can read them. Try each task yourself first if you can. Reading the answer after you've been stuck for ten minutes teaches more than reading it first.
L2 (git) is yours, last, as you decided.

---

## L1 — Set up and run

What was done: a virtual environment in `.venv` with Python 3.12, the packages from `requirements.txt`, the database built with `python -m db setup`, and the interface built into `webui/dist`. `python -m app` opens the window.

**What is a venv for?** It's a private folder of packages for this one project. Without it, every project on the computer shares one set of packages, and upgrading a library for one project can break another. With it, Lectern always has exactly the versions in `requirements.txt`.

**What breaks if you skip installing the packages?** The first `import` of a missing package fails, for example `ModuleNotFoundError: No module named 'webview'`, and nothing starts.

**Why do settings and secrets go in `.env`?** Code is shared (git, screenshots, the review). Settings differ per computer, and secrets must never be shared. `.env` stays on your computer and `.gitignore` keeps it out of git. The code reads it in `app/config.py`.

---

## L3 — SQL on the real data

All six queries, with comments, are in [`l3-queries.sql`](l3-queries.sql). Each was run against the real database. Results to expect:

| Query | Result |
|---|---|
| 1. Courses by title | 26 rows |
| 2. Count students | 33,002 (more if you've added some) |
| 3. Students per source | Open University 28,785 · ASSISTments 4,217 |
| 4. Withdrew from DDD-2013J | 681 students |
| 5. Enrollments per course | ASSISTments 4,217 at the top, then CCC-2014J with 2,498 |
| 6. Top 5 scores in DDD-2013J | five 100s on TMAs |

Things to be able to say:
- **JOIN** follows a foreign key from one table to another. Query 4 goes students → enrollments → courses.
- **GROUP BY** turns many rows into one row per group, and **COUNT/AVG/SUM** run once per group.
- **LEFT JOIN** (query 5) keeps rows with no match. A course with no enrollments still appears, with 0.
- Real data is messy. In query 4 some withdrawals have no enrolment date, and some ended before the course started (they unregistered early). The app shows these as they are rather than inventing values.

---

## L4 — Read an error and fix it

| Script | Last line of the error | Where | What was wrong | Fix |
|---|---|---|---|---|
| `broken_1.py` | `sqlite3.OperationalError: no such column: emial` | the `conn.execute(...)` line | typo in the column name inside the SQL | `emial` → `email` |
| `broken_2.py` | `AttributeError: module 'services.students' has no attribute 'serch'. Did you mean: 'search'?` | the `students.serch(...)` line | typo in the function name; Python even suggests the fix | `serch` → `search` |
| `broken_3.py` | `TypeError: can only concatenate str (not "float") to str` | the `print(...)` line | adding text and a number with `+` | `str(round(average, 1))`, or an f-string: `print(f"Average score: {average:.1f}%")` |

After fixing, script 3 prints `Average score: 69.6%`.

The habit: **read the last line first** (what went wrong), then go up to the lowest line that's in *your* file (where). The lines in between are Python's own files: skip them.

The scripts were left broken on purpose so you can still practise on them.

---

## L5 — Run the tests, break one, undo

With the three prerequisite lines commented out in `services/enrollments.py`:

- **Failed test**: `tests/test_enrollments.py::test_prerequisite_blocks_enrollment`, with `AssertionError: Regex pattern did not match`.
- **Why**: the test expects the message *"Finish these first: Python one."* It got *"Prerequisite not completed."* instead.
- **What still stopped the enrollment**: the database trigger `trg_enrollment_prerequisites` in `db/schema.sql`. SQLite refused the `INSERT` itself, and `enroll` turned that refusal into a message.
- **Lesson**: the Python check is there to give a friendly message. The trigger is the safety net that works even if the Python is wrong or bypassed. That's "defence in depth".

`git restore services/enrollments.py` puts the file back (once you've made your first commit, L2).

---

## L6 — Check AI-written code before trusting it

Reviewing `smart/ask_data.py`:

**What two checks in `parse` refuse dangerous questions first?**
1. Anything that looks like SQL is refused: a `;`, `--`, or words like `DROP TABLE` / `DELETE FROM`. Message: *"That looks like SQL. Ask in plain English instead…"*
2. Questions that start with a change word (*delete, remove, drop, update, insert, change, set, add, create, alter, modify, erase, wipe, truncate*) are refused. Message: *"This box only reads data…"*

**Can it build SQL that isn't a SELECT?** No. `build()` only ever fills in templates that begin with `SELECT`, and the typed words never become SQL text: they're either matched to a fixed piece (like `GROUP BY c.code`) or passed as `?` parameters. Even so, `check_safe()` runs before every query and refuses anything not starting with `SELECT`, anything containing `;`, and any of `INSERT UPDATE DELETE DROP ALTER CREATE REPLACE ATTACH DETACH PRAGMA VACUUM`.

**Why is the read-only connection the last guarantee?** `ask()` runs the query on `read_only()` from `db/connection.py`, which opens the file with `mode=ro` and sets `PRAGMA query_only = ON`. SQLite itself refuses any write on that connection, so even a bug in every check above couldn't change data. There's a test for this: `test_read_only_connection_cannot_write`.

**Trying to break it in the app:**

| Typed | Result |
|---|---|
| `delete all students` | Refused: "This box only reads data. It can't add, change or delete anything." |
| `show students; drop table courses` | Refused: "That looks like SQL…" |
| `update every score to 100` | Refused, same as the first |
| `how many students withdrew from DDD-2013J` | Works: 681 |

Nothing harmful got through.

---

## L7 — Trace one feature through the code

Enrolling a student, from the button to the database:

1. **Button** — `webui/src/screens/Enrollments.jsx`, the *Enroll* button: `onClick={onEnrollClicked}`.
2. **Handler** — `onEnrollClicked` calls `api('enroll', { student_id, course_id })`, then shows a toast and reloads the list.
3. **Into Python** — `webui/src/lib/api.js`: in the desktop window, `window.pywebview.api.call('enroll', …)`. pywebview runs Python's `Bridge.call` (`app/__main__.py`).
4. **Gatekeeper** — `Api.call` in `app/api.py` checks the method exists and isn't private, and turns any error into a message for the screen.
5. **Who's asking** — `Api.enroll` uses `_student_id`: a signed-in student can only enroll themselves; staff can enroll anyone.
6. **The rules** — `services/enrollments.py` `enroll` checks, in order: the course exists · it isn't a historical dataset course · it isn't archived · the student exists · the prerequisites are completed · they aren't already enrolled (or re-enrolls someone who withdrew).
7. **SQL** — `INSERT INTO enrollments (student_id, course_id, enrolled_on, status) VALUES (?, ?, ?, 'active')`, inside `transaction()`, so it's all or nothing.
8. **Database guard** — before the row is saved, trigger `trg_enrollment_prerequisites` checks the prerequisites again and raises *"prerequisite not completed"* if they're missing.
9. **Table** — the new row appears at the bottom of `enrollments` in DB Browser.
