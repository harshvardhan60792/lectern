# Code tour: where everything lives

Use this to find your way around, or to answer "show me where that happens".

## Start-up

| What | Where |
|---|---|
| `python -m app` opens the window | `app/__main__.py`: pywebview window showing `webui/dist/index.html`, with `Bridge` as its JavaScript API |
| `python -m app --browser` | same interface in a browser, via `app/server.py` (localhost only) |
| Settings from `.env` | `app/config.py` |
| Everything the interface can ask Python | `app/api.py` class `Api`: one method per action, `call()` checks roles and turns errors into messages |
| First run asks for an admin account | `webui/src/screens/SignIn.jsx` → `Api.setup_admin` |
| Sidebar, Ctrl+K palette, screen switching | `webui/src/App.jsx`, `webui/src/components/Shell.jsx` |

## Database

| What | Where |
|---|---|
| Every table, index, view and trigger | `db/schema.sql` |
| The only place connections are opened | `db/connection.py` `connect()`, `read_only()` |
| All-or-nothing changes | `db/connection.py` `transaction()` |
| Telling triggers who is signed in | `db/connection.py` `set_current_user()` + table `app_session` |
| `python -m db setup` | `db/__main__.py` `setup()` |

## Importing the datasets (`db/importers/`)

| File | Notes |
|---|---|
| `openstax.py` | Reads the PDF outline for chapters and sections, extracts text in layout mode so code keeps its indentation, pulls out "Concepts in practice" questions and matches the answer key at the back of the book. |
| `sciq.py` | Loads 13,679 questions; TF-IDF → LSA → k-means makes 15 topics. |
| `assistments.py` | One row per answer (`order_id`), original problems only; skills become modules. |
| `oulad.py` | Courses, assessments, students, enrollments, scores. `_import_clicks()` streams 10.6M rows into a staging database on disk and lets SQLite add them up, so memory stays low. Issues certificates for Pass and Distinction. |

## Services (the rules)

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
| `services/clock.py` | "today", fixed in tests |

## Smart features (`smart/`)

| File | Technique |
|---|---|
| `ask_data.py` | `parse()` finds intent, subject, filters, group, limit → `build()` fills SQL templates → `check_safe()` → runs on `read_only()` |
| `risk.py` | `_features()` (one SQL query per snapshot day), `train()` (2013 vs 2014 split), `predict()`, `_reasons()`, `nudge()` |
| `drafter.py` | `TermSpace` (LSA term vectors), `draft()` |
| `coach.py` | `_facts()` gathers data, `_rules()` the rule table, `notes()`, `week_plan()` |
| `recommender.py` | `recommend_courses()` (TF-IDF cosine + co-enrollment), `material_insights()` (lift) |
| `text.py` | sentence splitting, `key_terms()` (TF-IDF), `best_match()` (typo-tolerant), `looks_like_python()` |

## Interface (`webui/src/`)

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
- `lib/api.js`: the single function `api(method, data)` that reaches Python (pywebview in the window, `/api/...` in a browser).
- `lib/useApi.js`: load data for a screen and reload it.
- `components/ui.jsx`: buttons, fields, tables, sliding sheets, dialogs, tabs.
- `components/depth.jsx`: `TiltCard`, `FlipCard`, `Float`, the 3D pieces.
- `components/charts.jsx`: SVG charts. `components/learning.jsx`: mastery skyline, study calendar, coach notes, course map.
- `styles/tokens.css`: every colour, size and spacing value, light and dark.

## Tests (`tests/`)

`conftest.py` builds a small database by hand (two courses, three modules, two students) so 94 tests run in seconds without the datasets. `test_api.py` checks the bridge: roles, error messages, a full quiz flow. `test_real_data.py` adds 6 checks against the real database when it exists.
