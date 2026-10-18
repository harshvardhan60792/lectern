# Your learning tasks

Seven tasks covering the basics everyone needs, even when AI writes most of the code:
running a project, git, SQL, reading errors, tests, checking AI-written code, and tracing a feature through the code.

The app is built, so every task is ready now. Do them in order.

How it works:
1. Follow the steps exactly. If something doesn't match what you see, stop and paste what you see to Claude.
2. When done, say **"review L#"**. Claude checks your work and explains anything that went wrong.

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
8. Run the tests. The last line should say `100 passed`:
   ```powershell
   python -m pytest
   ```
9. Start the app. A window opens with a book on a lectern; the first time, it asks you to create the admin account. Pick a username and a password you'll remember.
   ```powershell
   python -m app
   ```
   The screens are already built (`webui\dist`). You only need Node.js if you change them (see README).

The database (`data\lectern.db`) is already built. On a new computer you'd download the datasets and run `python -m db setup` first (see `docs\data-sources.md`).

**Check yourself:** What is a venv for? What breaks if you skip step 6? Why do settings and secrets go in `.env` and not in the code?

---

## L2 — Git basics  *(~30 min)*

**Why it matters:** git is your undo button and your proof of work. At the review, the history shows what you did.

The folder is already a git repository with nothing committed yet. You make the first commit.

1. Check git knows who you are:
   ```powershell
   git config --global user.name
   git config --global user.email
   ```
   If either prints nothing, set it:
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
2. See what git sees:
   ```powershell
   git status
   ```
   Red = not saved in git yet.
3. Open `.gitignore` and read it. It keeps out `.env`, the 237 MB database, the downloaded datasets and `webui\node_modules`, which are too big and can be rebuilt. Run `git status` again and confirm that `.env` and `data/` are **not** listed. If they are, stop and tell Claude.
4. Stage everything and commit:
   ```powershell
   git add .
   git commit -m "Lectern: e-learning platform on real data"
   ```
5. See the history:
   ```powershell
   git log --oneline
   ```
6. Practise undo. Open `README.md`, type a junk line anywhere, save. Then:
   ```powershell
   git diff
   ```
   This shows exactly what changed (green = added). Throw the change away:
   ```powershell
   git restore README.md
   ```
   The junk line is gone.

**Habit from now on:** before you commit, run `git status` and `git diff --stat`, look at what changed, then commit with a short message saying what changed, e.g. `Fix email check on student form`.

---

## L3 — SQL on the real data  *(~45 min)*

**Why it matters:** this is a database project. Graders will ask you to explain queries.

1. Install **DB Browser for SQLite** from sqlitebrowser.org. In the installer, set the folder to `D:\Programs\DB Browser for SQLite`.
2. **Close Lectern first** (an open app can lock the database).
3. In DB Browser: *Open Database Read Only* (the arrow next to *Open Database*) → pick `D:\study\claude projects\elearning-platform\data\lectern.db`. Read-only means you can't break anything.
4. Click **Database Structure**. Open `docs\er-diagram.md` in VS Code next to it (press **Ctrl+Shift+V** to see the diagram). Find how `students`, `enrollments` and `courses` link.
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

**Why it matters:** the skill you'll use most. AI code breaks too, and you need to read the error before you can ask a good question.

There are three broken scripts in `docs\learn\l4\`. For each one:

1. Run it:
   ```powershell
   python docs\learn\l4\broken_1.py
   ```
2. Read the error **from the bottom up**:
   - The **last line** is the error type and message.
   - The lines above show the path. Find the lowest line that points to a file in **this project** (not inside Python itself). It gives the file name and line number.
3. In VS Code, open that file, press **Ctrl+G**, type the line number, press Enter.
4. Fix it, save, run again until it prints a result.
5. In a new file `docs\learn\l4-notes.md`, write for each script: the error message, the file and line, what was wrong, what you changed.

Then do `broken_2.py` and `broken_3.py`. Script 2's error even suggests the fix; notice that.

---

## L5 — Run the tests, break one, undo  *(~20 min)*

**Why it matters:** tests tell you whether a change broke something, so you don't have to click through the whole app.

1. Run all tests:
   ```powershell
   python -m pytest
   ```
   Last line: `100 passed`.
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

## L6 — Check AI-written code before trusting it  *(~30 min)*

**Why it matters:** the most important habit when building with AI. Never trust code you haven't looked at, especially code that touches data safety.

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
6. If anything harmful got through, write it down and tell Claude. If not, commit your notes:
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
- Say "explain-back session" to Claude: you walk through each part, Claude asks review-style questions.
- Be ready to answer: why SQLite and no Django, where the data comes from, how the review queue works, how certificate verification works, how the at-risk model was tested, how Ask the data stays safe.
