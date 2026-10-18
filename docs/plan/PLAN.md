# E-learning Platform Database — Build Plan

Python desktop app (pywebview window, React interface) + SQL backend + offline smart features (rule engines + scikit-learn ML). No paid API, no internet needed.
Phase 1 (PPT) due **15 Oct 2026**. Phase 2 (review) **21 Oct 2026**.

Working name: **Lectern** (change any time; it lives in one config value).

## Status (13 Oct 2026)

**Built and tested: T01–T32.** 100 tests pass; every screen checked in light and dark mode in the real desktop window.
**Left:** fill team names on the deck, T33 explain-back / teaching sessions, git (owner, last), M1–M5 (teammate).

Changes from the plan below, decided during the build:
- **Real data only, no generated seed data** (owner decision). T04 became four importers: OULAD, ASSISTments, OpenStax, SciQ. See `docs/data-sources.md`.
- Dataset students are anonymised IDs; their courses (2009–14) are historical and closed to new enrollments.
- Python course content and its 390 quiz questions come from the OpenStax textbook (with the official answer key), so the teammate no longer writes course text.
- At-risk model is trained on 2013 Open University students and tested on 2014 (AUC 0.79), instead of on synthetic data.
- No PostgreSQL switch: SQLite only, written in standard SQL; listed as a limitation and next step.
- Learning tasks were rewritten once everything existed (`LEARN.md`); worked answers are in `docs/learn/`.
- **Interface rebuilt (13 Oct)** as React + Motion inside a pywebview desktop window, for the 3D, sliding and floating pieces the owner asked for. New look (slate, brass, index cards; no blue or purple) in `DESIGN.md`. The CustomTkinter screens were removed.

## Ground rules

- One task = one session. Each task lists its output and a "done when" check.
- Tasks marked **[YOU]** are the owner's learning tasks (details in `LEARN.md`). Claude prepares the ground before them and reviews after, but does not write them.
- Tasks marked **[MATE]** are the 1st-year teammate's (details in `TEAMMATE.md`).
- Everything else is built by Claude. Each Claude task also writes a short note in `docs/explain/` (what it does, how it works, likely review questions).
- Stack: Python 3.11+, pywebview + React (Vite, Motion), SQLite (Postgres-compatible SQL), scikit-learn, numpy. No LLM, no API keys. Everything installs/lives on D drive.
- No Django. A desktop GUI over plain SQL is simpler and easier to explain.

## Who does what

| Who | Does |
|---|---|
| **Claude** | Architecture, hard code, AI features, most GUI screens, PPT build |
| **Owner [YOU]** | 7 learning tasks on core skills (run, git, SQL, errors, tests, reviewing AI code, tracing code) + review prep; commits after each Claude task |
| **Teammate [MATE]** | Problem-slide text, proofreading, screenshots, click-testing |

---

## What makes it unique

Most teams will ship CRUD screens plus a chatbot. These features are real, explainable, and rare in student projects. Each one is backed by something you can point to in the code or the database.

1. **Mistake review queue** — every wrong quiz answer goes into a Leitner box queue and comes back after 1, 3, then 7 days. Get it right and it moves up a box; wrong and it drops to box 1. (Spaced repetition, no AI needed.)
2. **Question health report** — for each quiz question, compute the *difficulty index* (share who got it right) and the *discrimination index* (top 27% vs bottom 27% of scorers). Flags questions that are too easy, too hard, or that strong students get wrong. Real teacher-side psychometrics.
3. **Mastery map** — per student, a grid of module tiles shaded by mastery (score + recency). One glance shows where they are weak.
4. **Study calendar** — year-view activity heatmap plus streak counter, built from the activity log.
5. **Prerequisites and course map** — courses unlock only after their prerequisites; a drawn graph shows the path.
6. **Tamper-evident certificates** — each PDF has a QR code with the certificate ID and a SHA-256 hash of (student, course, date, score). The verify screen recomputes the hash; any edited value fails.
7. **Pace forecast** — "at your current pace you finish on 3 Nov", from the last two weeks of progress.
8. **Grade history via SQL triggers** — every score change is copied to an audit table by a database trigger (old value, new value, who, when). Shows real DB skill, not just Python.
9. **Ask-your-data shows its SQL** — the English-question box shows the SQL it ran, so it doubles as a teaching tool.

### Smart features (rules + ML, fully offline)

No language model and no paid API. Every output can be explained line by line, which is a strength at the review: "no black box, no internet, student data never leaves the machine".

- **Question drafter** — module text in, multiple-choice questions out. TF-IDF picks the key terms; sentence patterns ("X is …", "X is used to …") become questions; cloze (fill-the-blank) for the rest; distractors are other key terms from the same course. Instructor edits before saving.
- **Progress coach** — a defined rule engine over scores, mastery map, review queue, pace and streak. Each rule has a condition, a priority and a message template. Output: top 3 notes + a 7-day study plan.
- **Ask the data** — a small English-question parser: intent (count / average / list / top / completion rate), subject (students, courses, quizzes…), filters (course name fuzzy-matched, "this month", "below 50"), grouping ("per course"), limit ("top 5"). Builds parameterised SQL from fixed templates, so it can only ever produce a safe `SELECT`. Shows the SQL; suggests example questions when it can't parse.
- **Recommender (ML)** — two signals combined: content similarity (TF-IDF + cosine over course descriptions) and "students who took X also took Y" (item-item collaborative filtering over the enrollment matrix). Rules filter out taken courses and unmet prerequisites. Each result says why.
- **At-risk prediction (ML)** — scikit-learn logistic regression trained on past enrollments (completed vs dropped). Features: days inactive, average score, progress rate, review backlog, streak. Coefficients explain the main reason ("12 days inactive"). Accuracy/precision/recall reported on a held-out split; retrain button.

### Database concepts on show (graders like these)

Normalised schema (3NF), foreign keys with cascade rules, indexes, views for reports, triggers for audit and certificate eligibility, transactions for enrollment + quiz submit, CHECK constraints.

---

## Making it not look AI-generated

**Visual design**
- One deliberate look: warm off-white "paper" background, deep ink text, a single accent colour (e.g. oxblood or forest green), serif headings + clean sans body. Proper dark theme from the same tokens.
- No gradients, no emoji, no sparkle icons, no "AI-powered" badges. AI features get plain labels: "Draft questions", "Coach notes", "Ask the data".
- Consistent spacing scale and one icon set. Charts styled to match (same fonts and colours, no default matplotlib look).
- Real empty states ("No enrollments yet — enroll a student from Courses").

**Words**
- Short, specific UI copy. No "Unlock your potential", no "seamless", no "delve".
- README and PPT written in plain first-person team voice, with honest limitations listed.
- Seed data looks real: mixed name origins, uneven scores, some dropped courses, some late starters.

**Code**
- Consistent naming, small functions, comments only where something is non-obvious.
- No giant generated files; modules split by feature.
- Git history: small commits with normal messages, made by the owner as work lands.

---

## Timeline (today 12 Oct)

| Days | Goal |
|---|---|
| 12–13 Oct | Phase 0 + Phase 1 |
| 13–14 Oct | Phase 2 (AI) + start Phase 3 |
| 14 Oct | **PPT gate:** login, courses, students, enrollments, one unique feature, one smart feature visible in the GUI |
| 15 Oct | PPT submitted |
| 15–20 Oct | Rest of GUI, unique features, tests, review prep |
| 21 Oct | Review |

---

## Phase 0 — Foundation

**T01 — Project scaffold**
Folder layout (`app/`, `db/`, `services/`, `smart/`, `gui/`, `tests/`, `docs/`), venv on D, `requirements.txt`, `.env.example`, config loader, `git init`.
*Done when:* `python -m app` starts and config loads.

**L1 [YOU] — Set up and run the project** (venv, install, `.env`, run).
**L2 [YOU] — Git basics** (status, diff, commit, restore; first commit).

**T02 — Schema + ER diagram**
`db/schema.sql`: users, students, instructors, courses, prerequisites, modules, lessons, enrollments, module_progress, activity_log, quizzes, questions, attempts, attempt_answers, review_queue, certificates, grade_audit, model_runs (ML training metrics). Constraints, indexes, views, triggers. ER diagram (Mermaid + PNG).
*Done when:* schema loads clean; diagram renders.

**T03 — DB layer**
Connection helper, init/reset command, parameterised queries only, transaction helper, Postgres switch in config.

**T04 — Seed data**
Realistic generator using `data/seed/` files from [MATE]. Uneven scores, some drop-outs, 90 days of activity history so the calendar and pace forecast have data.
*Done when:* `python -m app.db seed` gives a believable DB; rerunnable.

**L3 [YOU] — SQL on the real data** (SELECT, JOIN, GROUP BY in DB Browser).

## Phase 1 — Backend services

Plain functions over the DB layer, each with unit tests.

**T05 — Users & auth** — roles, scrypt password hashing, login, session.
**T06 — Courses, modules, lessons, prerequisites** — CRUD, ordering, video URL on lessons, unlock check.
**T07 — Students** — CRUD, search, filters, email validation.
**T08 — Enrollments** — enroll/drop/re-enroll in a transaction, prerequisite check, no duplicates.
**T09 — Progress & activity** — module completion, scores, video watched %, activity log, mastery calculation, pace forecast.
**T10 — Quizzes & attempts** — manual quiz builder, attempt, auto-grade, feeds progress and review queue.
**T11 — Mistake review queue** — Leitner boxes, due-today list, promote/demote.
**T12 — Certificates** — eligibility, ID + SHA-256 hash, PDF with QR code, verify function.
**T13 — Reports & question health** — performance, completion, trends via SQL views; difficulty and discrimination indexes; CSV export.

**L4 [YOU] — Read an error and fix it** (Claude prepares 3 broken scripts in `docs/learn/l4/`).
**L5 [YOU] — Run the tests, break one, undo with git.**

*Phase 1 done when:* a script runs a full student journey end to end from the shell.

## Phase 2 — Smart features (rules + ML)

**T14 — Text tools** — sentence splitting, keyword extraction (TF-IDF over all course text), fuzzy matching (difflib), shared by T15–T18.
**T15 — Question drafter** — pattern questions, cloze questions, distractor picking, quality filters (no duplicate answers, no trivial blanks), review step.
**T16 — Progress coach** — rule table (condition, priority, template), conflict handling, 7-day plan builder. Tests per rule.
**T17 — Ask the data** — tokenizer, intent/subject/filter/group/limit parser, SQL templates with parameters, read-only connection, row limit, "try asking…" suggestions. Test suite of ~40 questions plus hostile inputs.
**T18 — Recommender** — TF-IDF content similarity + item-item collaborative filtering, blended score, prerequisite filter, reason text.
**T19 — At-risk model** — feature builder, logistic regression training, held-out metrics, saved model file, per-student explanation from coefficients, retrain command.
*Seed data (T04) must carry a real, noisy pattern (inactivity and low scores raise drop-out odds) so the model learns something honest. Say at the review it is trained on synthetic data.*

**L6 [YOU] — Check an AI-written change before accepting it** (Claude leaves T17 uncommitted; you review the diff and try to break it).

## Phase 3 — GUI (CustomTkinter)

**T20 — Design system + app shell** — colour/type/spacing tokens, light + dark, sidebar, login, role menus, shared table/form/card widgets, chart style.
**T21 — Courses screen** — list, search, edit, modules/lessons, prerequisites.
**T22 — Students screen** — list, search, edit, profile.

**T23 — Enrollments screen.**

**L7 [YOU] — Trace one feature through the code** (Enroll button → handler → service → SQL → table).

**T24 — Student home** — my courses, progress, mastery map, study calendar, streak, pace forecast, recommendations, "due for review" count.
**T25 — Lesson, quiz, and review screens.**
**T26 — Instructor: draft-questions screen + question health table.**
**T27 — Reports & analytics** — styled charts, course map graph, exports.
**T28 — Smart screens** — coach notes, ask-the-data (with SQL shown), at-risk list with reasons and model metrics.
**T29 — Certificates** — list, PDF download, verify screen.

*Phase 3 done when:* every feature is reachable from the GUI without the console.

## Phase 4 — Delivery

**T30 — PPT (15 Oct)** — Problem, Solution, Unique Features, AI/ML features and how they work (rules + ML, offline), architecture/ER, screenshots. Uses [MATE]'s problem text and screenshots. Same visual style as the app.
**T31 — README + explain notes** — setup, features, honest limitations, one cheat sheet per module.
**T32 — Test pass** — full suite green; [MATE] runs the manual checklist; fix bugs.
**T33 — Demo script + review prep** — 5-minute click-through, likely Q&A, and a walkthrough session where you explain each module back.

---

## If time runs short

Cut in this order: video tracking → recommender collaborative-filtering half → course map graph → question drafter pattern questions (keep cloze) → dark theme.
Keep no matter what: core CRUD, review queue, question health, certificates with hash, question drafter (cloze), coach, ask the data, at-risk model.

## Risks

- **Ask the data can't parse a question** — it shows example questions it does understand; the demo script uses tested questions.
- **ML on synthetic data** — be upfront about it; show the metrics anyway.
- **Review grades understanding** — do the L tasks and read `docs/explain/` before the 21st.
- **PC memory pressure** — close other heavy apps when running tests; everything stays on D.
