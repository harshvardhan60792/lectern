# Lectern explained simply

Read this before the review. It assumes you know nothing about the project. It covers what the app is, how the pieces talk to each other, how SQL is used, where everything lives, and how to run it.

---

## 1. What is Lectern?

Lectern is an **e-learning platform that runs on your own computer** (a desktop app, not a website). Think of a small version of Coursera or Moodle:

- **Admins and instructors** add students, create courses, write quiz questions, see reports, and spot students who might drop out.
- **Students** sign in, join courses, read lessons, take quizzes, and get a **PDF certificate** when they finish a course.

The heart of the project is a **SQL database**. Every screen in the app is just a friendly way of reading from or writing to that database.

All the data is **real and public**: past university records (Open University, UK), real maths-practice answers (ASSISTments), a real Python textbook (OpenStax) and real science questions (SciQ). Nothing is made up.

---

## 2. The big picture: four layers

```
 ┌──────────────────────────────────────────────┐
 │ 1. INTERFACE  (what you see)                 │  webui/   React (JavaScript)
 │    buttons, tables, forms, charts            │
 └───────────────────┬──────────────────────────┘
                     │  api("enroll", {course_id: 5})
 ┌───────────────────▼──────────────────────────┐
 │ 2. BRIDGE  (the doorman)                     │  app/api.py   Python
 │    who is asking? are they allowed?          │
 └───────────────────┬──────────────────────────┘
                     │  enrollments.enroll(conn, student, course)
 ┌───────────────────▼──────────────────────────┐
 │ 3. SERVICES  (the rules)                     │  services/, smart/   Python
 │    "you must finish Python I first"          │
 └───────────────────┬──────────────────────────┘
                     │  INSERT INTO enrollments ...
 ┌───────────────────▼──────────────────────────┐
 │ 4. DATABASE  (the memory)                    │  data/lectern.db   SQLite
 │    tables, keys, triggers, views             │  db/schema.sql
 └──────────────────────────────────────────────┘
```

A simple way to say it: **the interface asks, the bridge checks, the services decide, the database remembers.**

Why split it like this? Each layer has one job. If you want to change how something looks, you only touch layer 1. If you want to change a rule, you only touch layer 3. The database rules (layer 4) protect the data even if the Python code has a bug.

---

## 3. What we used, and why

| Tool | What it is | Why we used it |
|---|---|---|
| **Python** | Programming language | Runs everything behind the screen |
| **SQLite** | A SQL database stored in one file | No server to install; the whole database is `data/lectern.db` |
| **pywebview** | Opens a desktop window that shows a web page | Lets us build the interface with web tools but ship a desktop app |
| **React** (JavaScript) | Library for building interfaces | Screens are made of reusable pieces (tables, cards, dialogs) |
| **Vite** | Build tool | Turns the React code into plain files in `webui/dist/` that the window loads |
| **Motion** | Animation library | The sliding, flipping and 3D effects |
| **scikit-learn** | Machine-learning library | At-risk prediction and the question drafter |
| **reportlab** + **qrcode** | PDF and QR-code makers | Certificates |
| **pytest** | Testing tool | 109 automatic tests check the app still works |

Everything works **offline**. No internet connection, no paid service, no AI chatbot inside the app.

---

## 4. Where everything is (folder map)

```
elearning-platform/
├── app/                 START-UP AND BRIDGE
│   ├── __main__.py      opens the window (python -m app)
│   ├── api.py           every action the interface can ask for, plus permission checks
│   └── config.py        reads settings (where the database file is)
│
├── db/                  THE DATABASE
│   ├── schema.sql       ★ all tables, keys, triggers, views, indexes (read this one)
│   ├── connection.py    the only place that opens the database
│   ├── __main__.py      python -m db setup / stats / reset
│   └── importers/       one file per dataset: reads CSV/PDF/JSON, fills the tables
│
├── services/            THE RULES (plain Python + SQL)
│   ├── auth.py          sign-in, passwords, accounts
│   ├── students.py      add / edit / search students
│   ├── courses.py       courses, modules, lessons, prerequisites
│   ├── enrollments.py   join, leave, finish a course
│   ├── progress.py      lessons read, mastery, study calendar
│   ├── quizzes.py       question bank, quizzes, marking
│   ├── review.py        mistake review (wrong answers come back later)
│   ├── certificates.py  issue, verify, make the PDF
│   ├── reports.py       pass rates, drop-outs, CSV export
│   └── common.py        today's date, the "user-fixable error" type
│
├── smart/               SMART FEATURES (rules + machine learning)
│   ├── risk.py          who might drop out
│   ├── ask_data.py      English question → SQL
│   ├── drafter.py       makes quiz questions from lesson text
│   ├── coach.py         study tips and a 7-day plan
│   ├── recommender.py   "you might like this course"
│   └── text.py          shared text helpers
│
├── webui/               THE INTERFACE
│   ├── src/screens/     one file per screen (Students.jsx, Courses.jsx, Learn.jsx…)
│   ├── src/components/  shared pieces (tables, dialogs, charts, sidebar)
│   ├── src/lib/api.js   the one function screens use to talk to Python
│   └── dist/            the built interface the window actually loads
│
├── tests/               109 automatic tests
├── data/lectern.db      THE DATABASE FILE (not on GitHub, too big)
├── data/raw/            downloaded datasets (not on GitHub)
└── docs/                documentation
```

If the reviewer asks "where is X?", most answers are one of: **`db/schema.sql`** (structure), **`services/`** (rules), **`app/api.py`** (permissions), **`webui/src/screens/`** (screens).

---

## 5. How to run it

Open the **VS Code terminal**, make sure you are in the **`elearning-platform`** folder, then:

**Start the app** (the normal way):
```bash
.venv\Scripts\python -m app
```
The first time, it asks you to create the admin account (choose any username and password).

**Run all the tests** (should say `109 passed`):
```bash
.venv\Scripts\python -m pytest
```

**See how many rows each table has:**
```bash
.venv\Scripts\python -m db stats
```

**Rebuild the database from scratch** (only if needed; takes a few minutes; the four datasets must be in `data/raw/`):
```bash
.venv\Scripts\python -m db reset
```
```bash
.venv\Scripts\python -m db setup
```

**Open the app in a normal browser instead of a window** (handy for showing on a projector):
```bash
.venv\Scripts\python -m app --browser
```

**Look inside the database yourself:** install the free app **DB Browser for SQLite**, then open `data/lectern.db`. You can see every table and run SQL by hand. Some ready-made practice queries are in `docs/learn/l3-queries.sql`.

---

## 6. How SQL works in this project

### 6.1 What SQLite is

A database is an organised store of data in **tables** (like spreadsheets: rows and columns). **SQL** is the language for asking the database to store or fetch data:

```sql
SELECT display_name FROM students WHERE region = 'Scotland';   -- read
INSERT INTO enrollments (student_id, course_id) VALUES (12, 5); -- add
UPDATE enrollments SET status = 'withdrawn' WHERE id = 40;      -- change
DELETE FROM courses WHERE id = 9;                                -- remove
```

Most databases (MySQL, PostgreSQL) run as a separate server program. **SQLite** is different: the whole database is **one file** (`data/lectern.db`), and Python opens it directly with its built-in `sqlite3` module. Nothing extra to install, which suits a desktop app.

### 6.2 Where the SQL lives

1. **`db/schema.sql`** defines the structure: 23 tables, 3 triggers, 3 views, 13 indexes. It runs once when the database is built.
2. **`services/*.py`** and **`smart/*.py`** contain the everyday SQL (`SELECT`, `INSERT`, `UPDATE`) written directly inside Python strings. We **did not use an ORM** (a tool that writes SQL for you) on purpose, so every query is visible and explainable.
3. **`db/connection.py`** is the **only** place that opens the database.

### 6.3 The tables (grouped)

The database has 23 tables. You don't need to memorise them; know the groups:

| Group | Tables | What they hold |
|---|---|---|
| **People** | `students`, `instructors`, `users` | Who exists. `users` holds sign-in accounts with a role: admin, instructor or student |
| **Courses** | `courses`, `modules`, `lessons`, `prerequisites`, `materials` | A course has modules; a module has lessons. `prerequisites` says "course B needs course A first" |
| **Enrollment and progress** | `enrollments`, `module_progress`, `lesson_progress`, `activity_days`, `material_use` | Who is in which course, their scores, which lessons they read, which days they studied |
| **Quizzes** | `questions`, `question_options`, `quiz_attempts`, `responses`, `review_queue` | Questions and their choices, each quiz taken, every single answer, and wrong answers waiting to be retried |
| **Certificates and records** | `certificates`, `grade_audit` | Issued certificates; a log of every score change |
| **Housekeeping** | `app_session`, `model_runs`, `meta` | Who is signed in right now (for the audit log), results of training the at-risk model, build date |

How the main tables connect:

```
 students ──< enrollments >── courses ──< modules ──< lessons
    │                                        │
    │                                        └──< questions ──< question_options
    │                                                  │
    └──────────────< responses >───────────────────────┘
    │
    └──< certificates >── courses

  ──<  means "one to many": one course has many modules,
       one student has many enrollments, and so on.
```

`enrollments` is the classic **many-to-many** link: one student can take many courses, and one course has many students. The `enrollments` table sits in the middle and has one row per (student, course) pair.

### 6.4 Rules the database enforces by itself

This is the most important part to explain. Even if the Python code had a bug, the **database refuses bad data**. That is done with:

**Primary keys:** every row has a unique `id`.
```sql
id INTEGER PRIMARY KEY
```

**Foreign keys:** a column that must point at a real row in another table. You can't enroll student 999 if student 999 doesn't exist.
```sql
student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE
```
`ON DELETE CASCADE` means: if a student is deleted, their enrollments, answers and certificates are deleted too, so nothing is left pointing at nothing.

**UNIQUE:** no duplicates.
```sql
UNIQUE (student_id, course_id)   -- a student can't be enrolled twice in one course
```

**CHECK:** only sensible values.
```sql
pass_mark INTEGER CHECK (pass_mark BETWEEN 0 AND 100)
status TEXT CHECK (status IN ('active', 'completed', 'failed', 'withdrawn'))
```

**NOT NULL:** the value must be given.

### 6.5 Triggers (automatic actions inside the database)

A **trigger** is SQL that runs automatically when something happens to a table. We have three, all in `db/schema.sql`:

1. **`trg_enrollment_prerequisites`**: *before* a new enrollment is saved, it checks the student has completed every required course. If not, the database stops it with `prerequisite not completed`. The Python code checks this too, but the trigger is the last line of defence.
2. **`trg_certificate_requires_completion`**: a certificate can't be saved unless the enrollment is `completed`.
3. **`trg_grade_audit`**: *after* a score changes, it writes a row into `grade_audit` with the old score, the new score, and who was signed in. That is a tamper-proof history of grades.

### 6.6 Views (saved queries)

A **view** is a query saved under a name, which you can then use like a table. We have three, for the reports:

- `v_course_stats`: for each course, how many enrolled, completed, failed, withdrew, and the completion rate.
- `v_enrollment_scores`: each enrollment's average and weighted score.
- `v_monthly_enrollments`: enrollments per month.

### 6.7 Indexes (speed)

An **index** is like the index at the back of a book: it lets the database jump straight to matching rows instead of reading every row. There are over 275,000 answers and 1.8 million activity rows, so without indexes some screens would be slow. Example:
```sql
CREATE INDEX idx_enrollments_course ON enrollments (course_id, status);
```

### 6.8 Transactions (all or nothing)

When a student submits a quiz, several things must happen together: save each answer, update the score, update the review list, maybe mark the course complete, maybe issue a certificate. If one step failed halfway, the data would be half-updated.

A **transaction** makes the steps all succeed together or all be undone. In `db/connection.py`:
```python
with transaction(conn):        # BEGIN
    ...several INSERTs and UPDATEs...
                               # COMMIT if all worked, ROLLBACK if anything failed
```

### 6.9 Safety: parameters, never pasted text

Every value from the user goes into SQL as a **parameter** (`?`), never glued into the SQL text:
```python
conn.execute("SELECT * FROM students WHERE id = ?", (student_id,))   # safe
```
This blocks **SQL injection**, where someone types SQL into a search box to trick the database. "Ask the data" goes further: it uses a **read-only** connection, so it physically can't change anything.

Two other settings in `db/connection.py`:
- `PRAGMA foreign_keys = ON`: SQLite only enforces foreign keys when this is on.
- `PRAGMA journal_mode = WAL`: lets reading and writing happen at the same time without blocking.

---

## 7. What happens when you click a button (one full example)

**A student clicks "Enroll" on the Python programming II card.**

1. **Interface** (`webui/src/screens/Catalog.jsx`) calls
   `api('enroll', { student_id: sid, course_id: c.id })`.
2. **`webui/src/lib/api.js`** sends that to Python through pywebview's bridge (`window.pywebview.api.call`).
3. **Bridge** (`app/api.py`, `Api.call`) checks whether someone is signed in and whether they are allowed. A student can only enroll **themselves**.
4. **Service** (`services/enrollments.py`, `enroll`) checks the rules:
   - does the course exist, and is it open (not archived, not a past course)?
   - are the prerequisites done? (Python I must be completed)
   - is the student already enrolled?
5. **SQL**, inside a transaction:
   ```sql
   INSERT INTO enrollments (student_id, course_id, enrolled_on, status)
   VALUES (?, ?, ?, 'active');
   ```
   The **trigger** checks the prerequisites again inside the database.
6. The answer goes back as `{"ok": true, "data": ...}` or `{"ok": false, "error": "Finish these first: Python programming I."}`, and the screen shows it.

Every button in the app follows this same path.

---

## 8. The main journeys

### Signing in
- Passwords are **never stored**. We store a **scrypt hash**: a one-way scramble with a random "salt". On sign-in, we hash what was typed and compare. (`services/auth.py`)
- Three roles: **admin** (everything, including accounts), **instructor** (staff screens), **student** (own courses only). The permission markers `@signed_in`, `@staff_only` and `@admin_only` are in `app/api.py`.

### Learning, quiz, certificate
1. The student enrolls, then reads lessons (`lesson_progress` gets a row).
2. The student takes a module quiz: `quiz_attempts` gets a row, and each answer goes into `responses`.
3. **Marking** (`services/quizzes.py`, `submit`): compare each chosen option with the one marked `is_correct = 1`. Skipped questions count as wrong.
4. The best score goes into `module_progress` (and the audit trigger logs any change).
5. Wrong answers go into `review_queue` and come back after **1, then 3, then 7 days** (the Leitner method).
6. When every module is passed, `check_completion` in `services/enrollments.py` marks the enrollment `completed` and **issues a certificate**.
7. **Certificate:** a code like `LEC-F62A-F4CE`, plus a **SHA-256 fingerprint** of the name, course, date and score. If someone edits the PDF, the fingerprint no longer matches, so "Verify" says it is not genuine. The PDF is made with reportlab and has a QR code.

---

## 9. Where the data came from

`python -m db setup` runs four importers in `db/importers/`. Each one reads a downloaded file and fills the tables:

| Importer | Reads | Becomes |
|---|---|---|
| `openstax.py` | The *Introduction to Python Programming* PDF | Python programming I and II: lessons, videos, 390 questions |
| `sciq.py` | 13,679 science questions | 5 short science courses (Chemistry, Physics, Earth science, Biology I and II) |
| `assistments.py` | 275,458 real student answers to maths questions | A maths practice course, used for the question health check |
| `oulad.py` | Open University records: 32,593 enrollments, 10.6 million click rows | 22 past course runs, their students, scores and outcomes; trains the at-risk model |

That is why there are **about 33,000 students**: they are real (anonymised) students from these datasets. They show up as `Student 11391` because the datasets hide real names. The past course runs are **closed**: you can study their reports, but nobody new can join them. New students and courses are added inside the app.

The courses a student can actually take are the 7 open ones: Python I and II, and the 5 science courses.

---

## 10. The smart features, simply

No chatbot and no internet. Each one is either rules or classic machine learning, and each can be explained in a sentence:

- **At-risk students** (`smart/risk.py`): **logistic regression**, a model that learns how much each factor raises or lowers the chance of dropping out. Factors: days since last active, recent activity, assignments handed in, average score, late registration, previous attempts. Trained on 2013 students and tested on 2014 students it never saw, it scores **ROC AUC 0.79** (0.5 = guessing, 1.0 = perfect). Each prediction shows its reasons.
- **Ask the data** (`smart/ask_data.py`): turns English like *"Pass rate by education level"* into SQL using **fixed rules** (find the intent, the subject, the filters, the grouping). It shows you the SQL it built and runs it read-only.
- **Question drafter** (`smart/drafter.py`): picks the key terms in a lesson with **TF-IDF** (words that are common in this text but rare elsewhere), blanks one out, and uses related terms as wrong choices. A teacher checks each draft before saving.
- **Question health check**: for each question, **difficulty** = the share of students who got it right, and **discrimination** = whether strong students get it right more than weak ones. A question that strong students get wrong probably has the wrong answer marked.
- **Coach** (`smart/coach.py`): if-then rules that read your own scores and write study tips and a 7-day plan.
- **Recommender** (`smart/recommender.py`): suggests courses that are similar in content, plus "students who took X also took Y".

---

## 11. Tests

`tests/` has **109 automatic tests**. They build a small throwaway database, do real actions (enroll, take a quiz, issue a certificate, try to cheat) and check the results. Examples:
- enrolling without a prerequisite is refused;
- skipped quiz questions count as wrong;
- an edited certificate fails verification;
- a student can't act as another student.

Run them with `.venv\Scripts\python -m pytest` (see section 5).

---

## 12. Short answers for likely reviewer questions

**Q: Where is the database?**
`data/lectern.db`, a single SQLite file. Its structure is in `db/schema.sql`.

**Q: Why SQLite, not MySQL?**
It's a desktop app for one computer. SQLite needs no server and keeps the whole database in one file, yet still supports keys, triggers, views, indexes and transactions.

**Q: How do you stop bad data?**
In two places: the Python rules in `services/`, and the database's own rules (foreign keys, UNIQUE, CHECK, triggers). The database is the last line of defence.

**Q: Show a trigger.**
Open `db/schema.sql` and scroll to `trg_enrollment_prerequisites`. Or try enrolling in Python II without finishing Python I.

**Q: How do you avoid SQL injection?**
Every value goes in as a `?` parameter. "Ask the data" also uses a read-only connection.

**Q: Normalisation?**
Each fact is stored once. For example, a course title lives only in `courses`; other tables store `course_id` and join to it. Question choices are their own table (`question_options`) rather than columns like `option1`, `option2`.

**Q: How are passwords stored?**
As scrypt hashes with a random salt, never as the password itself.

**Q: Are 33,000 students real?**
Yes: real anonymised students from the Open University and ASSISTments datasets.

**Q: What would you improve?**
- Multi-user over a network would need a server database such as PostgreSQL.
- The dataset students have no names, because the data is anonymised.
- "Ask the data" only understands the question patterns it has rules for.

More questions with fuller answers: [review-questions.md](review-questions.md). Full table-by-table detail: [database.md](database.md).
