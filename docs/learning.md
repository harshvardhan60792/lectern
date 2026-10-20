# Learning tasks

Seven tasks covering the basics every developer needs:
running a project, git, SQL, reading errors, tests, reviewing code, and tracing a feature through the code.

The app is built, so every task is ready now. Do them in order.

How it works:
1. Follow the steps exactly. If something doesn't match what you see, stop and note what you see.
2. When done, compare your work with the worked answers further down.

**Where to type commands:** unless a step says otherwise, use the **VS Code terminal**: open VS Code, *File → Open Folder…*, pick
`D:\study\claude projects\elearning-platform`, then *Terminal → New Terminal* (it opens PowerShell).
The prompt should end with `elearning-platform>`. If it doesn't, run:

```powershell
cd "D:\study\claude projects\elearning-platform"
```

---

## L1 — Set up and run the project  *(~25 min)*

**Why it matters:** every project you ever touch starts here. If you can't run it, you can't show it.

A `.venv` folder already exists from when the app was built. You'll delete it and make your own, which is exactly what you'd do on a new computer.

1. Check which Pythons are installed:
   ```powershell
   py -0
   ```
   You should see 3.12 in the list. We use 3.12 because every library we need supports it.
2. Delete the old virtual environment:
   ```powershell
   Remove-Item -Recurse -Force .venv
   ```
3. Create a new one with Python 3.12:
   ```powershell
   py -3.12 -m venv .venv
   ```
4. Activate it:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   The prompt now starts with `(.venv)`.
   If you get *"running scripts is disabled on this system"*, skip activating and write `.\.venv\Scripts\python` instead of `python` in every command below.
5. Keep the pip download cache on D (C is nearly full):
   ```powershell
   $env:PIP_CACHE_DIR = "D:\cache\pip"
   ```
6. Install the packages listed in `requirements.txt`:
   ```powershell
   python -m pip install -r requirements.txt
   ```
7. Create your settings file from the example, then open `.env` in VS Code and read it:
   ```powershell
   Copy-Item .env.example .env
   ```
8. Run the tests. The last line should say `109 passed`:
   ```powershell
   python -m pytest
   ```
9. Start the app. A window opens with a book on a lectern; the first time, it asks you to create the admin account. Pick a username and a password you'll remember.
   ```powershell
   python -m app
   ```
   The screens are already built (`webui\dist`). You only need Node.js if you change them (see README).

The database (`data\lectern.db`) is already built. On a new computer you'd download the datasets and run `python -m db setup` first (see Part 2 of `docs\database.md`).

**Check yourself:** What is a venv for? What breaks if you skip step 6? Why do settings and secrets go in `.env` and not in the code?

---

## L2 — Git basics  *(~30 min)*

**Why it matters:** git is your undo button and your proof of work. At the review, the history shows what you did.

The project is already in git and on GitHub: https://github.com/harshvardhan60792/lectern. You'll practise the everyday loop: look, change, check, commit, push.

1. Check git knows who you are:
   ```powershell
   git config --global user.name
   git config --global user.email
   ```
   If either prints nothing, set it (use the email on your GitHub account):
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
2. Get anything your teammate pushed, then see the history. Each line is one commit, newest first:
   ```powershell
   git pull
   git log --oneline
   ```
3. Open `.gitignore` and read it. It keeps out `.env`, the 237 MB database, the downloaded datasets and `webui\node_modules`, which are too big and can be rebuilt. Run `git status`: it should say "nothing to commit". `.env` and `data/` never appear.
4. Practise undo. Open `README.md`, type a junk line anywhere, save. Then:
   ```powershell
   git status
   git diff
   ```
   `git diff` shows exactly what changed (green = added). Throw the change away:
   ```powershell
   git restore README.md
   ```
   The junk line is gone.
5. Make a real commit. Open `docs\learning.md`, go to the click-test checklist at the end, tick one line you have tested (`- [ ]` becomes `- [x]`), save. Then:
   ```powershell
   git add docs\learning.md
   git commit -m "Tick sign-in checks in the test checklist"
   git push
   ```
   Open the GitHub page: your commit is at the top of the history.

**Habit from now on:** before you commit, run `git status` and `git diff --stat`, look at what changed, then commit with a short message saying what changed, e.g. `Fix email check on student form`.

---

## L3 — SQL on the real data  *(~45 min)*

**Why it matters:** this is a database project. Graders will ask you to explain queries.

1. Install **DB Browser for SQLite** from sqlitebrowser.org. In the installer, set the folder to `D:\Programs\DB Browser for SQLite`.
2. **Close Lectern first** (an open app can lock the database).
3. In DB Browser: *Open Database Read Only* (the arrow next to *Open Database*) → pick `D:\study\claude projects\elearning-platform\data\lectern.db`. Read-only means you can't break anything.
4. Click **Database Structure**. Open `docs\database.md` in VS Code next to it (press **Ctrl+Shift+V** to see the diagram). Find how `students`, `enrollments` and `courses` link.
5. Click **Execute SQL**. Type this and press **Ctrl+Enter**:
   ```sql
   SELECT display_name, region, highest_education FROM students LIMIT 10;
   ```
6. Now write these yourself. Use a hint only if you're stuck for 10 minutes.
   1. All courses, sorted by title. *(ORDER BY)*
   2. How many students there are. *(COUNT)*
   3. How many students come from each `source`. *(GROUP BY)*
   4. Names of students who withdrew from course `DDD-2013J`. *(JOIN students → enrollments → courses, WHERE c.code = … AND e.status = 'withdrawn')*
   5. Number of enrollments per course, biggest first. *(GROUP BY, ORDER BY … DESC)*
   6. The 5 highest assessment scores in `DDD-2013J`, with the student's name. *(JOIN module_progress → modules → courses, and → students; LIMIT 5)*
7. Save each working query in a new file `docs\learn\l3-queries.sql`, with a comment line above each one saying what it does (`-- how many students per source`).

---

## L4 — Read an error and fix it  *(~30 min)*

**Why it matters:** the skill you'll use most. Every program breaks sometimes, and you need to read the error before you can ask a good question.

`docs\learn\broken.py` holds three small scripts that crash. Run them one at a time. For each one:

1. Run it:
   ```powershell
   python docs\learn\broken.py 1
   ```
2. Read the error **from the bottom up**:
   - The **last line** is the error type and message.
   - The lines above show the path. Find the lowest line that points to a file in **this project** (not inside Python itself). It gives the file name and line number.
3. In VS Code, open that file, press **Ctrl+G**, type the line number, press Enter.
4. Fix it, save, run again until it prints a result.
5. In a new file `docs\learn\l4-notes.md`, write for each script: the error message, the file and line, what was wrong, what you changed.

Then run it with `2`, then `3`. Script 2's error even suggests the fix; notice that.

---

## L5 — Run the tests, break one, undo  *(~20 min)*

**Why it matters:** tests tell you whether a change broke something, so you don't have to click through the whole app.

1. Run all tests:
   ```powershell
   python -m pytest
   ```
   Last line: `109 passed`.
2. Break something on purpose. Open `services\enrollments.py` and find these three lines inside `enroll` (search with **Ctrl+F** for `Finish these first`):
   ```python
       missing = missing_prerequisites(conn, student_id, course_id)
       if missing:
           raise ValidationError("Finish these first: " + ", ".join(missing) + ".")
   ```
   Put `# ` at the start of **all three** lines. Save. The app no longer checks prerequisites in Python.
3. Run only the enrollment tests:
   ```powershell
   python -m pytest tests\test_enrollments.py
   ```
   `test_prerequisite_blocks_enrollment` now fails with `Regex pattern did not match`. Scroll up in the output to see what message it got instead: *"Prerequisite not completed."*
   That message comes from the **database trigger** `trg_enrollment_prerequisites` in `db\schema.sql`. Even with the Python check gone, the database still refused the enrollment. The test fails only because the friendly message changed. The Python check is for a helpful message; the database is the last line of defence.
4. Undo with git:
   ```powershell
   git restore services\enrollments.py
   ```
5. Run the tests again. All pass.
6. Write 3–4 lines in `docs\learn\l5-notes.md`: which test failed, why, and what still stopped the enrollment without the Python check.

---

## L6 — Review code before trusting it  *(~30 min)*

**Why it matters:** never trust code you haven't looked at, especially code that touches data safety.

The "Ask the data" feature takes typed English and runs SQL on the database. You'll check it can't be used to damage data.

1. Open `smart\ask_data.py`. Read the docstring at the top (the text in triple quotes).
2. Find the function `parse` (**Ctrl+Shift+O** lists all functions). Read its first six lines.
3. Find `check_safe` and `ask` near the bottom.
4. Answer in a new file `docs\learn\l6-review.md`:
   - What two checks in `parse` refuse dangerous questions before anything else happens?
   - Can the code ever build SQL that isn't a `SELECT`? Which line in `check_safe` would stop it if it did?
   - In `ask`, which connection runs the SQL, and why does that make it safe even if every other check failed? (Look at `read_only` in `db\connection.py`.)
5. Start the app, sign in, open **Ask the data**, and try to break it. Type each and note what happens:
   - `delete all students`
   - `show students; drop table courses`
   - `update every score to 100`
   - `how many students withdrew from DDD-2013J` *(this one should work)*
6. If anything harmful got through, write it down. If not, commit your notes:
   ```powershell
   git add docs\learn
   git commit -m "Review ask-the-data safety"
   ```

---

## L7 — Trace one feature through the code  *(~40 min)*

**Why it matters:** at the review someone will point at a button and ask "what happens when I click this?" This is how you find out.

Feature to trace: **enrolling a student in a course**. It crosses from the screen (JavaScript) into Python.

1. In VS Code press **Ctrl+Shift+F** and search for `onEnrollClicked`. Open `webui\src\screens\Enrollments.jsx`.
2. Read `onEnrollClicked`. It calls `api('enroll', { student_id, course_id })`. Find where the button uses it (search the same file for `onClick={onEnrollClicked}`).
3. Open `webui\src\lib\api.js`. See how `api` sends the call: in the desktop window through `window.pywebview.api.call`, in a browser through `/api/enroll`.
4. Open `app\api.py`. Find `def call` (it checks the method exists and the role is allowed) and then `def enroll`. Note `_student_id`: a student can only enroll themselves.
5. In `enroll`, click `enrollments.enroll` and press **F12**. You're in `services\enrollments.py`. List every check it makes before saving (there are six). Find the SQL `INSERT`. Is it inside a transaction?
6. Open `db\schema.sql` and find `trg_enrollment_prerequisites`. What does it do that the Python code also does?
7. Prove it: in the app, add a student on **Students**, enroll them in *Python programming I* on **Enrollments**. Close the app. In DB Browser (read-only) → **Browse Data** → `enrollments` → scroll to the bottom. Find the new row.
8. Write `docs\learn\l7-trace.md`, about 8–12 lines:
   button → `onEnrollClicked` → `api()` → pywebview → `Api.call` → `Api.enroll` → `services.enrollments.enroll` → checks → SQL → table → trigger.

## Before the review (21 Oct)

- Read `docs\explain\00-project-overview.md`, `01-code-tour.md` and `02-review-questions.md`.
- Practise explaining each part out loud, then answer the questions in `docs/review-questions.md`.
- Be ready to answer: why SQLite and no Django, where the data comes from, how the review queue works, how certificate verification works, how the at-risk model was tested, how Ask the data stays safe.

---

## Worked answers

These are the answers for L1 and L3–L7 above, done so you can read them. Try each task yourself first if you can. Reading the answer after you've been stuck for ten minutes teaches more than reading it first.
L2 (git) is yours, last, as you decided.

---

### L1 — Set up and run

What was done: a virtual environment in `.venv` with Python 3.12, the packages from `requirements.txt`, the database built with `python -m db setup`, and the interface built into `webui/dist`. `python -m app` opens the window.

**What is a venv for?** It's a private folder of packages for this one project. Without it, every project on the computer shares one set of packages, and upgrading a library for one project can break another. With it, Lectern always has exactly the versions in `requirements.txt`.

**What breaks if you skip installing the packages?** The first `import` of a missing package fails, for example `ModuleNotFoundError: No module named 'webview'`, and nothing starts.

**Why do settings and secrets go in `.env`?** Code is shared (git, screenshots, the review). Settings differ per computer, and secrets must never be shared. `.env` stays on your computer and `.gitignore` keeps it out of git. The code reads it in `app/config.py`.

---

### L3 — SQL on the real data

All six queries, with comments, are in [`learn/l3-queries.sql`](learn/l3-queries.sql). Each was run against the real database. Results to expect:

| Query | Result |
|---|---|
| 1. Courses by title | 31 rows |
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

### L4 — Read an error and fix it

| Script | Last line of the error | Where | What was wrong | Fix |
|---|---|---|---|---|
| `broken.py 1` | `sqlite3.OperationalError: no such column: emial` | the `conn.execute(...)` line | typo in the column name inside the SQL | `emial` → `email` |
| `broken.py 2` | `AttributeError: module 'services.students' has no attribute 'serch'. Did you mean: 'search'?` | the `students.serch(...)` line | typo in the function name; Python even suggests the fix | `serch` → `search` |
| `broken.py 3` | `TypeError: can only concatenate str (not "float") to str` | the `print(...)` line | adding text and a number with `+` | `str(round(average, 1))`, or an f-string: `print(f"Average score: {average:.1f}%")` |

After fixing, script 3 prints `Average score: 69.6%`.

The habit: **read the last line first** (what went wrong), then go up to the lowest line that's in *your* file (where). The lines in between are Python's own files: skip them.

The scripts were left broken on purpose so you can still practise on them.

---

### L5 — Run the tests, break one, undo

With the three prerequisite lines commented out in `services/enrollments.py`:

- **Failed test**: `tests/test_enrollments.py::test_prerequisite_blocks_enrollment`, with `AssertionError: Regex pattern did not match`.
- **Why**: the test expects the message *"Finish these first: Python one."* It got *"Prerequisite not completed."* instead.
- **What still stopped the enrollment**: the database trigger `trg_enrollment_prerequisites` in `db/schema.sql`. SQLite refused the `INSERT` itself, and `enroll` turned that refusal into a message.
- **Lesson**: the Python check is there to give a friendly message. The trigger is the safety net that works even if the Python is wrong or bypassed. That's "defence in depth".

`git restore services/enrollments.py` puts the file back as it was in the last commit.

---

### L6 — Review code before trusting it

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

### L7 — Trace one feature through the code

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


---

## Teammate tasks

Small, clear jobs. None need programming. Each takes under an hour.
Ask if anything is unclear; don't guess.

### Before 15 Oct (PPT)

**M1: Problem slide text**
Write 4–5 short bullet points on the problem: why do small institutes and online tutors struggle to track students, progress and certificates? Use real-life examples (WhatsApp groups, Excel sheets, Canva certificates, students silently dropping out). Plain English. Send it to the owner.

**M2: Proofread the slides**
When the owner shares the deck, read every slide. Note typos, unclear sentences, and anything you don't understand (if you don't get it, the judges won't either).

### 15–21 Oct (review)

**M3: Screenshots**
Once the app runs on the owner's laptop, take clear screenshots of: sign-in, Overview, Students (with someone selected), a course's Insights tab, Question bank → Health check, Ask the data (with an answer), At-risk students, a quiz, a certificate. Name them `01-signin.png`, `02-overview.png`, and so on.

**M4: Click-test**
Follow the click-test checklist at the end of this file with the owner's laptop. Click every button, try wrong inputs (empty fields, wrong password, a bad email). Write each problem as: *screen → what you did → what happened*.

**M5: Learn one screen**
Pick **Students** or **Courses**. Be able to answer, in your own words: "What does this screen do and how would a teacher use it?" That's enough for your part of the review; nobody expects you to explain the code.

### Not for the teammate

Database design, Python code, SQL, the machine-learning parts. The owner handles those.

---

## Click-test checklist

Tick each line. If something breaks or looks wrong, write: *screen → what you did → what happened*.

### Sign in
- [ ] Wrong password shows "Wrong username or password" and clears the password box
- [ ] Right password opens the Overview
- [ ] The book on the sign-in screen turns its pages once
- [ ] Dark / Light button switches appearance; every screen stays readable
- [ ] Ctrl+K opens the jump-to palette; typing "rep" and Enter opens Reports
- [ ] Sign out returns to the sign-in screen

### Students
- [ ] Search "11391" shows matching students; clearing the box shows everyone again
- [ ] Source filter "Added here" shows only students added in the app
- [ ] Next / Previous page through the list
- [ ] Add student with an empty name → error message, dialog stays open
- [ ] Add student with email `abc` → error message
- [ ] Add a real student → appears in the list and opens on the right
- [ ] Edit that student's region → saved
- [ ] Create login for that student → message confirms the username
- [ ] Learner view opens their home page
- [ ] Mastery tab shows the block skyline; Study days shows the calendar
- [ ] Remove asks for confirmation; Cancel keeps the student

### Courses
- [ ] Select DDD-2013J → About, Modules, Prerequisites, Insights tabs all open
- [ ] Insights shows the weekly activity chart and the scores chart
- [ ] New course with code `x` → error; with code `WEB-101` → created
- [ ] Add a module, rename it, move it up/down
- [ ] Add a lesson with a video link starting `ftp://` → error; with `https://` → saved
- [ ] Open a module (arrow), click a lesson → it opens to read
- [ ] PY-102 Prerequisites tab shows PY-101 and the course map
- [ ] Course cards lean slightly toward the mouse

### Enrollments
- [ ] Search a student, pick PY-102, Enroll → "Finish these first: Python programming I"
- [ ] Pick PY-101, Enroll → success; enrolling again → "Already enrolled"
- [ ] Drop → success; the student shows as withdrawn

### Learning (as a student or via Learner view)
- [ ] Browse courses: cards in the drawer lift on hover and pull out when clicked
- [ ] Continue opens the course; lessons open; "Mark as read and continue" moves on
- [ ] Watch the video opens the browser
- [ ] Take quiz → answer all → Submit → score and feedback appear
- [ ] Next day (or after wrong answers), "Start review" appears on the home page

### Question bank
- [ ] PY-101 → module → Bank lists questions; clicking one previews it; Show answer flips the card
- [ ] Draft from lessons → Draft questions → drafts appear; Save kept as drafts → message
- [ ] Maths skill builder → Health check → Run check → counts and table appear

### Reports, Ask the data, At-risk, Certificates
- [ ] Each Reports tab shows a chart or table; Save as CSV opens the exports folder
- [ ] Ask the data: each example button gives an answer and shows the SQL
- [ ] Ask "delete all students" → refused
- [ ] At-risk: change course and day → table and numbers update; selecting a row shows reasons
- [ ] Certificates: select one → Turn it over shows the fingerprint → Save PDF opens a PDF
- [ ] Verify with the right code → Genuine; add score 99 → Not valid
