# Lectern: project overview

Read this first. It explains what we built, how the pieces fit, the technical words you will hear at the review, and (in section 13) where each part lives in the code. Likely review questions are in [review-questions.md](review-questions.md).

---

## 1. The problem

Small institutes, coaching centres and tutors teach online but track students in WhatsApp groups and spreadsheets. That breaks down:

- Nobody knows exactly who finished which module or how they scored.
- Certificates are made by hand and can be faked by editing the PDF.
- Teachers write quizzes from scratch and never learn which questions were badly written.
- Students who are falling behind are noticed only after they have dropped out. In the Open University data we use, **31% of enrollments ended in withdrawal**.
- Students forget what they got wrong and repeat the same mistakes.

## 2. The solution in one line

**Lectern** is a desktop app that keeps courses, students, enrollments, progress, quizzes and certificates in one proper SQL database, and adds tools that help teachers teach and students remember. It all runs offline, on real data.

## 3. Who uses it

| Role | What they do |
|---|---|
| **Admin** | Everything an instructor does, plus manages accounts. |
| **Instructor** | Manages students and courses, builds quizzes, checks question quality, sees reports, at-risk students and the data. |
| **Student** | Reads lessons, takes quizzes, reviews mistakes, follows the coach's plan, downloads certificates. |

Staff can also open any added student's **learner view** to see exactly what that student sees.

---

## 4. The big picture: four layers

```
┌──────────────────────────────┐
│  Interface  webui/           │  React screens in a desktop window (pywebview)
│  Bridge     app/api.py       │  one entry point: call(method, data)
├──────────────────────────────┤
│  Services services/          │  the rules (plain Python functions)
│  Smart    smart/             │  rule engines + scikit-learn models
├──────────────────────────────┤
│  DB layer db/                │  opens connections, runs parameterised SQL
├──────────────────────────────┤
│  SQLite   data/lectern.db    │  one file holds everything
└──────────────────────────────┘
```

Each layer only talks to the one below it. This is **separation of concerns**: the interface never writes SQL, the database never knows about buttons, and the rules can be tested without opening a window (that's what the 109 tests do).

**Example: clicking "Enroll"** (`webui/src/screens/Enrollments.jsx`)
1. **Interface**: `onEnrollClicked()` sends `api('enroll', {student_id, course_id})` across the bridge.
1. **Bridge**: `Api.enroll` in `app/api.py` checks who is signed in and calls the service.
2. **Service**: `enrollments.enroll()` checks the course is open, the student exists, they aren't already enrolled, and they've finished the prerequisites.
3. **DB layer**: runs `INSERT INTO enrollments …` inside a transaction.
4. **Database**: a trigger checks prerequisites again before saving. If anything fails, nothing is saved.

---

## 5. Technology choices

| Part | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Required by the task. |
| Window | **pywebview** | A real desktop window started from Python, showing a web-built interface. Python stays in charge of everything behind it. |
| Interface | **React** + **Motion** | React builds the screens; Motion does the 3D tilt, flips, sliding sheets and the card drawer. Built once with Vite into `webui/dist`, so it runs offline. |
| Bridge | `app/api.py` | The only way the interface reaches Python: one `call(method, data)` that checks the role and returns JSON. |
| Database | **SQLite** | One file, nothing to install, fast. Standard SQL, so it could move to PostgreSQL. |
| No Django ORM | — | Django is a web framework. In a desktop app, writing SQL directly is simpler and shows more database skill. |
| Smart features | **Rule engines + scikit-learn** | Free, offline, explainable. No paid API, no language model. |
| PDFs | **pypdf** (reading), **reportlab** + **qrcode** (certificates) | |
| Charts | Hand-drawn SVG, animated with Motion | Stacked bars, lines, histograms, the isometric mastery skyline; every value also written as text. |
| Tests | **pytest** | 109 automatic checks, including the bridge's permissions. |

---

## 6. The data: all real

| Source | Becomes |
|---|---|
| **OULAD**, Open University (UK), 2013–14 | 22 courses, 28,785 students, 32,593 enrollments, 173,739 assessment scores, 1.8M study days (from 10.6M click rows), 15,385 certificates |
| **ASSISTments**, maths tutor, 2009–10 | 1 course, 102 skills, 18,209 problems, 275,458 answers |
| **OpenStax** *Introduction to Python Programming* | 2 courses, 15 chapters, 85 lessons with video links, 390 questions with the official answer key |
| **SciQ**, Allen Institute for AI | 6 short science courses (15 topics), 4 readings and 40 questions per topic |

Dataset students are anonymised (`Student 11391`). Their courses are historical and closed to new students. New students and courses are added in the app. Details and licences are in [database.md](database.md#data-sources).

---

## 7. The database

23 tables, 13 indexes, 3 views, 3 triggers. Diagram: [database.md](database.md).

| Table | Holds |
|---|---|
| `students`, `instructors`, `users` | People; `users` has login details with hashed passwords |
| `courses`, `prerequisites`, `modules`, `lessons`, `materials` | What is taught |
| `enrollments` | Who is in which course, and how it ended |
| `module_progress`, `lesson_progress`, `activity_days`, `material_use` | Progress and activity |
| `questions`, `question_options`, `quiz_attempts`, `responses` | Quizzes and every answer |
| `review_queue` | Mistakes waiting to be retried (Leitner boxes) |
| `certificates`, `grade_audit` | Certificates; every score change |
| `model_runs`, `app_session`, `meta` | Bookkeeping |

### Database ideas to explain

- **Primary key**: a unique ID per row. **Foreign key**: a column pointing at another table's row (`enrollments.student_id → students.id`). The database refuses broken links.
- **Normalisation (3NF)**: each fact stored once. A student's name lives only in `students`.
- **Many-to-many**: students ↔ courses through `enrollments`.
- **Constraints**: `CHECK (best_score BETWEEN 0 AND 100)`, `UNIQUE (student_id, course_id)`.
- **ON DELETE CASCADE**: removing a student removes their enrollments, answers and certificates automatically.
- **Index**: makes lookups like "all enrollments of course 12" fast.
- **View**: a saved query used like a table (`v_course_stats` gives enrolled, completed, withdrawn and completion rate per course).
- **Trigger**: SQL that runs by itself on an event. Ours: (1) log every score change to `grade_audit`, with who was signed in; (2) refuse an enrollment with unfinished prerequisites; (3) refuse a certificate for an unfinished course.
- **Transaction**: steps that succeed or fail together. Submitting a quiz saves the answers, the score, the review queue, the activity and maybe a certificate, all or nothing.
- **Parameterised query**: values go separately from the SQL (`WHERE id = ?`), which blocks **SQL injection**.

---

## 8. Features that make it different

**Mistake review queue (Leitner system).** A wrong answer goes into box 1 and comes back tomorrow. Right → next box (3 days, then 7 days, then "learned"). Wrong → back to box 1. Spaced reviews beat re-reading.

**Question health check (item analysis).** For each question with 30+ answers:
- *Difficulty p* = share who got it right.
- *Discrimination D* = share right among the top 27% of students minus the bottom 27%.
- Flags: too easy (p > 0.9), too hard (p < 0.2), doesn't separate (D < 0.2), check answer key (D < −0.1: weaker students do *better*).
On the real ASSISTments answers: 1,969 healthy, 101 too easy, 13 too hard, 391 don't separate, 66 to check.

**Mastery map.** One tile per module. Built from answers with an exponentially weighted average: the newest answer counts 30%, the one before 21%, and so on. Recent learning matters more than an old mistake.

**Study calendar and streaks.** A year of days, darker = more study, from `activity_days`.

**Prerequisites and course map.** Python II requires Python I. Checked in Python and by a trigger; loops (A needs B needs A) are refused with a recursive SQL query. The course map draws the graph.

**Tamper-evident certificates.** At issue time: SHA-256 hash of code + student + course + date + score. The PDF carries the code, the hash and a QR code. Verifying recomputes the hash; change any detail and it no longer matches.

**Pace forecast.** Modules finished in the last 14 days → modules per week → finish date.

**Grade audit trail.** The trigger above. Retake a quiz with a better score and a row appears in Reports → Grade changes.

---

## 9. Smart features: rules and machine learning

No paid API and no language model. Two kinds of "intelligence":
- **Rule engines**: hand-written, predictable, every output traceable to a rule.
- **Machine learning**: models that learn from data (scikit-learn), used where rules would be guesswork.

**At-risk prediction (logistic regression).** Predicts which students won't finish (withdraw or fail).
- *Features*, measured on day 30/60/90/120 of the course: days since last activity, activity in the last 2 weeks, active days, share of assessments handed in, average score, late registration, earlier attempts.
- *Honest test*: trained on 2013 students (44,914 snapshots), tested on 2014 students it never saw (59,254). **ROC AUC 0.79, precision 0.66, recall 0.62.** It gets better later in the course (day 120: accuracy 0.78).
- *Reasons*: weight × how unusual the student's value is shows what pushed their risk up, e.g. "Handed in 0 of 2 assessments due".
- In the app you pick a course and a day and see who would have been flagged, next to what really happened.

**Ask the data (rule-based parser).** English → SQL without AI writing SQL. It finds the intent (count / average / rate / top / list), the subject, filters (course code, typo-tolerant course names, result, region, gender, age, education, year, score limits), grouping and limit, then fills fixed SQL templates. Typed values are always parameters. Change words ("delete", "update", `;`, `DROP TABLE`) are refused. It runs on a read-only connection with a 200-row limit and shows the SQL it ran.

**Question drafter (TF-IDF + LSA).** Turns lesson text into multiple-choice drafts. TF-IDF finds key terms (frequent here, rare elsewhere). Definition sentences ("A tuple is …") become "Which term matches this description?"; other sentences become fill-in-the-blank. Wrong options are terms used in similar contexts, found with LSA (a term-by-sentence matrix compressed by truncated SVD). Every draft is reviewed before saving.

**SciQ topics (k-means).** 13,679 science questions with no labels, grouped into 15 topics by TF-IDF + LSA + k-means, each named by its three strongest words.

**Progress coach (rule engine).** Rules with a condition, a priority and a message: reviews due, inactive for 5+ days, weak module (mastery < 50%), stalled pace, one module left, rising or falling scores, quiz taken before reading. Top 3 notes are shown, plus a 7-day plan (reviews first, then weak modules, then the next lessons and quizzes).

**Recommender.** Content similarity (TF-IDF + cosine) blended with "students who took X also took Y" (item-item collaborative filtering), minus courses already taken. Each suggestion says why. For Open University courses, it also finds learning materials with the highest *lift*: pass rate of students who used them ÷ overall pass rate.

---

## 10. Design

### Direction

Lectern is a classroom and a reading room: chalkboard slate, a brass desk lamp, index cards in a card-catalog drawer, and a book open on a stand. The interface is built from those materials. Courses are index cards that slide out of a drawer, mastery is a small skyline of blocks, the sign-in screen is a book opening on a lectern. Data screens stay calm and legible; the three-dimensional, moving pieces live in a few places where they explain something (a drawer you pull from, a card you flip to check, a block that rises as you learn).

Not the cream-paper, serif, clay-accent look, and no blue or purple anywhere.

### Colour

| Token | Light (day) | Dark (chalkboard) | Role |
|---|---|---|---|
| `--slate` | `#1E2B24` | `#111A15` | Sidebar, dark panels |
| `--bg` | `#E3E7DC` | `#16201B` | App background (sage paper / board) |
| `--card` | `#F6F7F2` | `#1F2C25` | Index cards, panels |
| `--card-2` | `#EDF0E7` | `#26352D` | Inset areas, table stripes |
| `--line` | `#C9D0C2` | `#34463B` | Borders, rules |
| `--ink` | `#18201B` | `#E8ECE2` | Main text (chalk in dark) |
| `--ink-2` | `#4E5A52` | `#A9B4AA` | Secondary text |
| `--brass` | `#B8862B` | `#D4A445` | Primary action fill (ink text on it) |
| `--brass-ink` | `#7A5714` | `#E2BC6A` | Brass as text/links |
| `--green` | `#2E6B47` | `#7DBB91` | Good, passed |
| `--amber` | `#94600E` | `#E0A94E` | Warning |
| `--red` | `#AE3A2A` | `#EE8A78` | Errors, withdrawn (teacher's red pen) |

Contrast: ink on card 15.6:1; ink-2 on card 6.6:1; ink on brass 6.1:1; brass-ink on card 5.9:1. Colour never carries meaning alone: every status also has a word.

### Type

- **Literata** (a typeface made for long reading on screens): page titles, numbers that matter, lesson text, certificate.
- **Atkinson Hyperlegible** (designed for legibility by the Braille Institute): everything else: navigation, controls, tables, labels.
- Scale (px): 13 · 15 · 17 (body) · 22 · 30 · 44 · 64. Tables 15, tabular figures. Lesson text 19/1.7 in Literata, max 68ch.
- Sentence case everywhere. No all-caps labels.

### Space, shape, depth

- Spacing steps: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64.
- Radius by role: controls 8, index cards 6 (paper is barely rounded), sheets 14, pills full.
- Depth is physical: paper cards sit on the desk with a short, warm-tinted shadow `0 1px 0 rgba(30,43,36,.08), 0 8px 24px -12px rgba(30,43,36,.35)`. Lifted things cast longer shadows. Blur (`backdrop-filter`) only on floating layers: command palette, side sheets, toasts.

### Motion

- Springs for things you move: `stiffness 380, damping 32` (snappy) and `220/26` (drawers, sheets).
- Ease for things that appear: `cubic-bezier(.2,.8,.2,1)`, 180–320 ms.
- One orchestrated moment: the sign-in book opening. Other motion answers an action (hover a card, open a drawer, flip a card, answer a question).
- 3D: `perspective 1200px`; tilt at most 8°; nothing spins for decoration.
- `prefers-reduced-motion`: springs become instant, tilt and float switch off, flips become cross-fades.

### Signature pieces

1. **Book on a lectern** (sign-in): pages turn once on load.
2. **Card-catalog drawer** (course catalog): index cards stacked in 3D; hovering lifts one out, clicking slides it fully out.
3. **Mastery skyline**: isometric blocks, height = mastery, colour + label = state.
4. **Flip cards**: quiz feedback and certificates turn over to show the answer / the fingerprint.
5. **Sliding sheets**: student and course details slide in from the right over the list.

### Anti-patterns for this project

Cream + serif + clay accent; blue or purple; gradient washes; identical rounded cards with the same grey shadow everywhere; all-caps eyebrows; emoji icons; "→" on buttons; fade-up on every section.

## 11. Words you might be asked about

| Term | Simple meaning |
|---|---|
| CRUD | Create, Read, Update, Delete |
| ORM | A library mapping tables to objects (like Django ORM). We use SQL directly. |
| Schema / ER diagram | The table design / a picture of it |
| Hash vs encryption | A hash can't be reversed; encryption can be decrypted with a key |
| Salt | Random bytes added before hashing a password, so equal passwords get different hashes |
| scrypt | A deliberately slow password hash, so guessing is expensive |
| TF-IDF | How important a word is to one document compared with all others |
| Cosine similarity | How alike two lists of numbers are, 0 to 1 |
| LSA / truncated SVD | Squeezing a big word matrix into fewer dimensions so related words end up close |
| k-means | Groups points into k clusters around k centres |
| Logistic regression | Weighted features → probability between 0 and 1 |
| Train/test split | Learn on one part of the data, check on a part the model never saw |
| Precision / recall | Of those flagged, how many were right / of the real cases, how many were caught |
| React | A JavaScript library that builds screens from small reusable pieces (components) |
| pywebview | A Python library that opens a desktop window showing a web page and lets its JavaScript call Python |
| Bridge / API | The agreed list of calls between two programs; here, the interface asking Python for data |
| ROC AUC | Chance the model ranks a random non-finisher above a random finisher (0.5 = guessing, 1 = perfect) |

---

## 12. Honest limitations (say these at the review)

- One computer, not a multi-user web system. The interface is already web technology, so the next step is PostgreSQL behind a small web server.
- Dataset students have IDs, not names, and their courses are historical.
- Video is a link to the textbook's videos.
- Drafted questions need a human check; that's why the review step exists.
- Ask the data understands a set of question shapes, not any English.
- The at-risk model is right about two times in three when it flags someone. It is for deciding who to check on, never for judging a student.

---

## 13. Code tour: where everything lives

Use this to find your way around, or to answer "show me where that happens".

### Start-up

| What | Where |
|---|---|
| `python -m app` opens the window | `app/__main__.py`: pywebview window showing `webui/dist/index.html`, with `Bridge` as its JavaScript API |
| `python -m app --browser` | same interface in a browser, via the small local server in `app/__main__.py` (localhost only) |
| Settings from `.env` | `app/config.py` |
| Everything the interface can ask Python | `app/api.py` class `Api`: one method per action, `call()` checks roles and turns errors into messages |
| First run asks for an admin account | `webui/src/screens/SignIn.jsx` → `Api.setup_admin` |
| Sidebar, Ctrl+K palette, screen switching | `webui/src/App.jsx`, `webui/src/components/Shell.jsx` |

### Database

| What | Where |
|---|---|
| Every table, index, view and trigger | `db/schema.sql` |
| The only place connections are opened | `db/connection.py` `connect()`, `read_only()` |
| All-or-nothing changes | `db/connection.py` `transaction()` |
| Telling triggers who is signed in | `db/connection.py` `set_current_user()` + table `app_session` |
| `python -m db setup` | `db/__main__.py` `setup()` |

### Importing the datasets (`db/importers/`)

| File | Notes |
|---|---|
| `openstax.py` | Reads the PDF outline for chapters and sections, extracts text in layout mode so code keeps its indentation, pulls out "Concepts in practice" questions and matches the answer key at the back of the book. |
| `sciq.py` | Loads 13,679 questions; TF-IDF → LSA → k-means makes 15 topics, grouped into 6 short courses. |
| `assistments.py` | One row per answer (`order_id`), original problems only; skills become modules. |
| `oulad.py` | Courses, assessments, students, enrollments, scores. `_import_clicks()` streams 10.6M rows into a staging database on disk and lets SQLite add them up, so memory stays low. Issues certificates for Pass and Distinction. |

### Services (the rules)

| File | Key functions |
|---|---|
| `services/auth.py` | `hash_password` (scrypt + salt), `login`, `create_user`, `create_instructor` |
| `services/students.py` | `add`, `update`, `remove`, `search`; email check in `_clean` |
| `services/courses.py` | courses, modules (`move_module` swaps positions), lessons, prerequisites; `_would_loop` uses a recursive SQL query |
| `services/enrollments.py` | `enroll` (all the checks), `drop`, `check_completion` (completes the course and issues the certificate) |
| `services/quizzes.py` | `start_quiz` (unseen questions first), `submit` (the big transaction), `save_question` |
| `services/review.py` | Leitner boxes: `record`, `due`, `summary` |
| `services/progress.py` | `mastery_map` (weighted average), `calendar`, `streaks`, `pace` |
| `services/certificates.py` | `fingerprint` (SHA-256), `issue`, `verify`, `render_pdf` |
| `services/reports.py` | outcomes, engagement, score distribution, CSV export, `question_health` (item analysis) |
| `services/common.py` | `ValidationError` (a message the user can act on) and "today", fixed in tests |

### Smart features (`smart/`)

| File | Technique |
|---|---|
| `ask_data.py` | `parse()` finds intent, subject, filters, group, limit → `build()` fills SQL templates → `check_safe()` → runs on `read_only()` |
| `risk.py` | `_features()` (one SQL query per snapshot day), `train()` (2013 vs 2014 split), `predict()`, `_reasons()`, `nudge()` |
| `drafter.py` | `TermSpace` (LSA term vectors), `draft()` |
| `coach.py` | `_facts()` gathers data, `_rules()` the rule table, `notes()`, `week_plan()` |
| `recommender.py` | `recommend_courses()` (TF-IDF cosine + co-enrollment), `material_insights()` (lift) |
| `text.py` | sentence splitting, `key_terms()` (TF-IDF), `best_match()` (typo-tolerant), `looks_like_python()` |

### Interface (`webui/src/`)

| File | Screen |
|---|---|
| `screens/SignIn.jsx` | Sign-in and first run, with the book-on-a-lectern scene |
| `screens/Overview.jsx` | Totals, floating index cards, how OU courses ended, model card |
| `screens/Students.jsx` | Student list; profile sheet with courses, mastery skyline, study days, coach notes |
| `screens/Courses.jsx` | Course cards; course sheet with modules and lessons editor, prerequisites and course map, OU insights |
| `screens/Enrollments.jsx` | Enroll / drop (`onEnrollClicked`), who is in each course |
| `screens/Questions.jsx` | Question bank with flip-card preview, drafter, health check |
| `screens/Reports.jsx` | Outcomes by background, weekly engagement, scores, monthly enrollments, grade changes |
| `screens/Ask.jsx` | Ask the data, with the SQL shown |
| `screens/Risk.jsx` | At-risk students, gauge, reasons, suggested message |
| `screens/Certificates.jsx` | Certificate that flips to its fingerprint, PDF, verification |
| `screens/Accounts.jsx` | Sign-in accounts (admin only) |
| `screens/Learn.jsx` | Student home, course page, lesson reader, quiz deck and results |
| `screens/Catalog.jsx` | The card-catalog drawer of open courses |

Shared pieces:
- `lib/api.js`: the single function `api(method, data)` that reaches Python (pywebview in the window, `/api/...` in a browser), plus `useApi` to load a screen's data and reload it.
- `lib/format.js`: how numbers, dates and labels are written, and the shared motion settings.
- `components/ui.jsx`: buttons, fields, tables, sliding sheets, dialogs, tabs.
- `components/depth.jsx`: `TiltCard`, `FlipCard`, `Float`, the 3D pieces.
- `components/charts.jsx`: SVG charts. `components/learning.jsx`: mastery skyline, study calendar, coach notes, course map.
- `styles/tokens.css`: the fonts and every colour, size and spacing value, light and dark. `styles/components.css` and `styles/depth.css` style the pieces and the 3D parts.

### Tests (`tests/`)

`conftest.py` builds a small database by hand (two courses, three modules, two students) so 103 tests run in seconds without the datasets. `test_api.py` checks the bridge: roles, error messages, a full quiz flow. `test_real_data.py` adds 6 checks against the real database when it exists.
