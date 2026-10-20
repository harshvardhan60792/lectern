# Lectern: everything you need to make the Phase 1 PPT

Hi! This file has all the content for the slides. You don't need to understand the code. Copy the text, use the screenshots from the `screenshots` folder, and keep the design rules at the bottom.

**What the PPT must cover (from the club brief):** Problem, Solution, Unique Features, AI features and how they work.
**Due:** 15 Oct 2026. The final review is on 21 Oct, where each of us is asked about the project.

---

## 1. The project in one paragraph

**Lectern** is an e-learning platform database. It keeps everything about online courses in one proper SQL database: courses, modules, lessons, students, enrollments, progress, scores, quizzes, certificates and reports. It's a Python desktop app. All the data comes from real, published datasets, nothing made up. It also has smart features (an AI-style drop-out predictor, plain-English questions to the database, a question writer, a study coach and course suggestions). They are built from rules and machine learning, run offline, and use no paid AI service.

**One-line pitch:** *Courses, progress and certificates in one SQL database, built on real student data, with smart features that run offline.*

---

## 2. Slide-by-slide content

Fifteen slides is a good length. Each slide below has: **title**, **what goes on it**, **screenshot** (if any), and **what to say** (speaker notes).

### Slide 1: Cover
- Title: **Lectern**
- Subtitle: Courses, progress and certificates in one SQL database, built on real student data and smart features that run offline.
- Team name, member names
- Built with: Python · SQLite · pywebview + React · scikit-learn
- Screenshot (optional, as a background or on the side): `01-sign-in.png`
- Say: introduce the team and the idea. Stress two things: all data is real, and every smart feature runs offline with no paid API.

### Slide 2: The problem
- Title: **Online teaching is run from chats and spreadsheets, so students slip away unnoticed**
- Big number: **31%** of 32,593 Open University enrollments ended in withdrawal (2013–14, real data)
- Four problems:
  1. **Progress is guesswork.** Who finished what, and how they scored, lives in scattered sheets.
  2. **Drop-outs seen too late.** A student who stopped logging in is noticed only after they quit.
  3. **Weak questions survive.** Nobody checks which quiz questions are confusing or wrongly keyed.
  4. **Certificates are easy to fake.** A certificate made in a design tool can be edited by anyone.
- Say: tutors, coaching centres and small institutes teach online but track students in WhatsApp and Excel. The 31% is real: almost a third of enrollments in the dataset we use ended in withdrawal.

### Slide 3: The solution
- Title: **One database for courses, people, progress and proof**
- Text: Lectern is a Python desktop app over a real SQL database. Three roles see three views of the same data:
  - **Admin:** students, courses, accounts, reports
  - **Instructor:** lessons, quizzes, question checks, at-risk list
  - **Student:** lessons, quizzes, reviews, study plan, certificates
- Covers the brief: add/update/remove courses and students · enrollments · progress, scores and modules · certificates · reports
- Screenshot: `02-overview.png`
- Say: on the right is the real Overview screen: 33,003 students, 36,810 enrollments, and how each Open University course ended.

### Slide 4: Real data, nothing generated
- Title: **Four published datasets, each with its own job**

| Source | Size | Used for |
|---|---|---|
| Open University (OULAD) | 32,593 enrollments · 10.6 million clicks | Students, scores, activity, outcomes, the at-risk model |
| ASSISTments 2009–10 | 275,458 answers | Question health check, mastery |
| OpenStax *Introduction to Python* textbook | 85 lessons · 390 questions | Two Python courses, with the book's answer key |
| SciQ (Allen Institute for AI) | 13,679 questions | Six short science courses, topics found by clustering |

- Note: students in the datasets are anonymous, so they appear as IDs like **Student 11391**. Each dataset is used only for what it really contains.
- Say: all data is real and openly licensed. One command builds the whole 237 MB database from the downloaded files in about 80 seconds.

### Slide 5: How it is built
- Title: **Four layers, and the database guards itself**
- Layers (draw as a stack, top to bottom):
  1. **Screens:** React pages inside a Python desktop window (pywebview)
  2. **Rules and smart features:** Python (`services/`, `smart/`)
  3. **Database layer:** all SQL in one place, values passed as parameters
  4. **SQLite database:** one file, 237 MB
- Numbers: **23** tables · **13** indexes · **3** views · **3** triggers
- Points:
  - Normalised to third normal form: each fact stored once
  - Foreign keys, CHECK and UNIQUE rules
  - Transactions: a quiz submit saves everything or nothing
  - Triggers log every grade change and block enrollments with unfinished prerequisites
  - Every value passed as a parameter, so no SQL injection
- Say: each layer talks only to the one below. We chose SQLite because it's a real SQL database in one file with nothing to install. The SQL is standard, so it can move to PostgreSQL later. We didn't use the Django ORM because Django is for websites, and writing SQL ourselves shows the database work. The triggers mean the database itself refuses bad data, even if the Python code were bypassed.

### Slide 6: Unique features for students
- Title: **Learning that sticks, not just a progress bar**
  - **Mistake review queue:** wrong answers come back after 1, then 3, then 7 days (the Leitner system)
  - **Mastery skyline:** each module is a 3D block whose height shows skill; the newest answer counts 30%
  - **Study calendar:** a year of study days and streaks, from real daily activity
  - **Pace forecast:** "At your pace you finish around 1 Nov", from the last 14 days
  - **Course catalog drawer:** courses are index cards you pull out of a drawer
- Screenshot: `09-learner-home.png` (and `10-catalog.png` if there's room)
- Say: spaced reviews beat re-reading. Get a question wrong and it comes back tomorrow; get it right and the gap grows. The mastery score is a weighted average where recent answers count more, so one old mistake doesn't follow you forever.

### Slide 7: Unique features for teachers
- Title: **Questions you can trust, records nobody can quietly change**
  - **Question health check:** item analysis like exam boards use: how hard each question is, and whether strong students beat weak ones. On 2,540 real maths questions it flagged **66** whose answer key may be wrong.
  - **Tamper-evident certificates:** each certificate has a SHA-256 fingerprint of name, course, date and score. Change one character and verification fails. The PDF has a QR code.
  - **Grade audit trail:** a database trigger records every score change and who made it.
- Screenshot: `08-certificate.png` (or `05-question-flip.png`)
- Say: difficulty is the share who got a question right. Discrimination compares the top 27% of students with the bottom 27%. When weaker students do better than stronger ones, the answer key is probably wrong.

### Slide 8: AI features overview
- Title: **Smart, offline and explainable**
- Text: no paid API and no chatbot. Rule engines where the rules are clear, machine learning where rules would be guesswork. Every result can be traced to a rule or a weight, and student data never leaves the computer.
- Five features:

| Feature | How |
|---|---|
| At-risk prediction | Logistic regression (machine learning) |
| Ask the data | Rule-based English parser into safe SQL |
| Question drafter | TF-IDF + LSA (text machine learning) |
| Progress coach | Rule engine |
| Course recommender | Text similarity + "students who took X also took Y" |

- Say: this is a strength, not a shortcut. It's free, works without internet, keeps student data private, and we can explain every output, which matters when the output is about a person.

### Slide 9: AI feature 1: At-risk prediction (machine learning)
- Title: **Spotting students who will drop out, weeks ahead**
- How it works:
  1. On day 30, 60, 90 or 120 of a course, measure 7 behaviours: days since last activity, recent activity, number of active days, work handed in, average score, late registration, earlier attempts.
  2. A logistic regression model turns them into a chance of not finishing.
  3. Each feature's weight explains the reason, e.g. "Handed in 0 of 2 assessments due". The app also suggests a message the teacher can send.
- Results: **ROC AUC 0.79** · **precision 0.66** · **recall 0.62**
- Tested fairly: trained on 2013 students, tested on 2014 students it never saw (59,254 test cases).
- Screenshot: `07-at-risk.png`
- Say: AUC 0.79 means it ranks a non-finisher above a finisher 79% of the time. Precision 0.66: two in three students it flags really don't finish. Recall 0.62: it catches about six in ten. Because the data is historical, the app shows each prediction next to what actually happened.

### Slide 10: AI feature 2: Ask the data (rule engine)
- Title: **Ask the database in plain English, safely**
- Example: *"Withdrawal rate by region"*

| Step | Result |
|---|---|
| Intent | a rate: withdrawals |
| Subject | enrollments |
| Group by | region |
| Becomes | a fixed SQL SELECT template, values passed as parameters |

- Safety: it can only ever build a SELECT. "Delete", "update" and SQL like `; DROP TABLE` are refused, and it runs on a read-only database connection. It shows the SQL it ran.
- Screenshot: `06-ask-the-data.png`
- Say: letting an AI write SQL is risky because it could write DELETE. Our parser never writes free SQL. It finds the intent (count, average, rate, top, list), the subject, filters such as a course code, region, year or "below 40", even with typos in course names, then fills a ready-made template. It also shows the SQL, so it helps people learn SQL.

### Slide 11: AI features 3–5
- Title: **Drafting questions, coaching students, suggesting what's next**
  - **Question drafter (TF-IDF + LSA):** finds a lesson's key terms, turns definition sentences ("A tuple is …") into questions, and picks wrong options from terms used in similar sentences. A teacher reviews every draft before it's used.
  - **Progress coach (rule engine):** each rule has a condition, a priority and a message: reviews due, weak module, stalled pace, falling scores. It shows the top 3 notes and a 7-day plan.
  - **Recommender and topics (similarity + k-means):** course similarity plus "students who took X also took Y", always with a reason. k-means clustering sorted 13,679 unlabelled science questions into 15 topics.
- Say: the coach always gives the same advice for the same facts, because it's rules. The recommender always says why it suggests a course.

### Slide 12: The app
- Title: **A Python desktop app with one consistent look, light and dark**
- Three screenshots side by side: `11-quiz.png`, `10-catalog.png`, `04-course-insights.png`
  - Captions: Quizzes from the textbook's own questions · Course catalog: cards slide out of a drawer · Weekly activity: students who withdraw go quiet early
- Text: Python opens the window with pywebview; React and Motion draw the screens. Screens: students, courses, enrollments, question bank, reports, ask the data, at-risk students, certificates, accounts, and the student's own home, catalog, lessons and quizzes.
- Say: it has a light "paper" mode and a dark "chalkboard" mode. 3D is used where it means something: catalog cards in a drawer, flip cards for questions and certificates, and a 3D skill skyline.

### Slide 13: Proof it works
- Title: **Tested, measured, and rebuilt from scratch in 80 seconds**
- Four numbers:
  - **109** automated tests, all passing
  - **33,003** real students across 31 courses
  - **15,385** certificates, each with a fingerprint
  - **0** paid services or internet needed
- Points:
  - Tests cover every rule: double enrollment, prerequisites, scoring, the review queue, tampered certificates, refused SQL, and who is allowed to do what
  - The database triggers are tested directly, not only the Python checks
  - Six tests run on the real 237 MB database: data counts, model quality, every example question
- Say: the tests try things that should fail: enrolling twice, skipping a prerequisite, forging a certificate, typing DROP TABLE into Ask the data.

### Slide 14: Limits and next steps
- **Limits today:**
  - Runs on one computer, not a shared website
  - Videos are links to the textbook's videos
  - Ask the data understands a set of question shapes, not all English
  - When the model flags someone it's right about two times in three, so it's a prompt to check in, never a judgement
  - Dataset students are anonymous IDs from 2009–14
- **Next:**
  - PostgreSQL behind a small web server for many users
  - Email reminders when reviews come due
  - Retrain the model on Lectern's own students
  - A video player that records how much was watched
- Say: being honest about limits shows we understand the project.

### Slide 15: Thank you
- Title: **Thank you**
- Line: A real database, real data, and smart features you can explain line by line.
- Questions? · team name · member names
- If asked for a live demo, do it in this order: sign in → Overview → a student's profile → take a quiz as a student and get a question wrong → show it in the review queue → Ask the data: "Withdrawal rate by region" → At-risk students on DDD-2014J at day 60 → verify a certificate, then change its score and show it fails.

---

## 3. Design rules for the PPT

The app has its own look. Make the slides match it, so it looks like one project.

**Colours (use only these):**

| Name | Hex | Use |
|---|---|---|
| Slate (dark green-grey) | `#1E2B24` | Dark slides, title bars |
| Sage paper | `#E3E7DC` | Main slide background |
| Card | `#F6F7F2` | Boxes and cards on slides |
| Ink | `#18201B` | Main text |
| Ink 2 | `#4E5A52` | Secondary text |
| Brass | `#B8862B` | Accent: lines, highlights, big numbers on dark slides |
| Brass ink | `#7A5714` | Accent text on light backgrounds |
| Green | `#2E6B47` | Good / passed |
| Red | `#AE3A2A` | Bad / at risk |

**Fonts:** headings in **Literata** (a serif), body text in **Atkinson Hyperlegible**. Both are free on Google Fonts. If you can't install them, use Georgia for headings and Arial for body.

**Do:**
- One idea per slide, big text (body at least 24 pt)
- Use the real screenshots, not stock images
- Keep the numbers exactly as written here

**Don't:**
- No blue or purple anywhere
- No PowerPoint theme templates, gradients, clip art, or emoji
- Don't say we used Django. We didn't.
- Don't change the numbers or round them differently

---

## 4. Screenshots (in the `screenshots` folder)

| File | What it shows | Slide |
|---|---|---|
| `01-sign-in.png` | Sign-in screen with the book on a lectern | 1 |
| `02-overview.png` | Overview: totals and how courses ended | 3 |
| `03-student-profile.png` | A student's profile with mastery and calendar | spare |
| `04-course-insights.png` | Course insights charts | 12 |
| `05-question-flip.png` | Question bank, card flipped to show the answer | 7 or spare |
| `06-ask-the-data.png` | Ask the data with the SQL shown | 10 |
| `07-at-risk.png` | At-risk students with reasons | 9 |
| `08-certificate.png` | A certificate and the verify form | 7 |
| `09-learner-home.png` | Student home: streak, coach, plan, skyline | 6 |
| `10-catalog.png` | Course catalog drawer | 6 or 12 |
| `11-quiz.png` | A quiz question from the textbook | 12 |

---

## 5. Words you might be asked about

- **SQL database:** stores data in tables with rows and columns; you ask it questions in SQL.
- **SQLite:** a full SQL database stored in one file.
- **Table / row / column:** like a spreadsheet sheet / line / heading.
- **Foreign key:** a column that points to a row in another table (an enrollment points to a student and a course).
- **Trigger:** a rule inside the database that runs automatically when data changes.
- **Transaction:** a group of changes that all happen or none do.
- **Normalisation (3NF):** each fact is stored once, so it can't disagree with itself.
- **Logistic regression:** a simple machine-learning model that gives a probability and shows which inputs pushed it up or down.
- **ROC AUC / precision / recall:** how good the predictor is (see slide 9).
- **TF-IDF:** scores how important a word is in one lesson compared with all lessons.
- **k-means:** groups similar items together without being told the groups.
- **SHA-256:** turns text into a fixed code; change one letter and the code completely changes.
- **Leitner system:** flashcard method where cards you get right come back less often.
- **pywebview:** a Python library that opens a desktop window showing web pages.
