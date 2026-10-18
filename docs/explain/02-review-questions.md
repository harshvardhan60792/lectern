# Likely review questions, with answers

Practise saying these in your own words. Short answers are better than long ones.

## The project

**What problem does it solve?**
Tutors and small institutes track students in spreadsheets and chats. Lectern keeps courses, enrollments, progress and certificates in one database, catches students who are drifting away before they drop out, and helps students fix their mistakes.

**Where does the data come from? Is it fake?**
No, it's all real and published: Open University (UK) course records, ASSISTments maths answers, the OpenStax Python textbook, and SciQ science questions. Nothing is generated. Dataset students are anonymised, which is why they show as IDs.

**Why a desktop app and not a website?**
The task asked for a Python GUI. A desktop app also means no server to run during the demo.

**Is it really a Python GUI if the screens are React?**
Yes: Python starts the program, opens the window (pywebview), owns the database and all the rules. The window draws its screens with web technology, the same way many desktop apps do (VS Code, Slack, Discord). Every action goes through one Python class, `Api` in `app/api.py`, which checks who is asking. We chose this because the brief asked for something that looks and feels finished, with 3D and motion, which Tkinter can't do well.

**How does a button reach the database?**
`onEnrollClicked` in `Enrollments.jsx` calls `api('enroll', …)` → pywebview passes it to `Api.call('enroll', …)` in Python → `Api.enroll` checks the role → `services/enrollments.enroll` checks the rules → SQL `INSERT` inside a transaction → the trigger checks prerequisites again.

**Why SQLite and not MySQL/PostgreSQL? Why not Django ORM?**
SQLite is a real SQL database in one file, so it needs no installation. The SQL is standard and would move to PostgreSQL for a multi-user web version. Django is a web framework; for a desktop app, writing SQL directly is simpler and shows the database work more clearly.

## Database

**Show me a many-to-many relationship.** Students and courses, through `enrollments`.

**What is normalisation here?** Each fact is stored once. A student's name is only in `students`; enrollments store the student's ID.

**What stops a student enrolling twice?** `UNIQUE (student_id, course_id)` on `enrollments`, and a check in `services/enrollments.py`.

**What's a trigger? Show one.** SQL that runs by itself on an event. `trg_grade_audit` copies every score change into `grade_audit`. `trg_enrollment_prerequisites` refuses an enrollment if prerequisites aren't completed, even if the Python code were skipped.

**What's a transaction? Where do you use one?** All-or-nothing changes. Submitting a quiz saves answers, score, review queue, activity and possibly a certificate in one transaction (`services/quizzes.py` `submit`).

**How do you prevent SQL injection?** Every value is passed as a parameter (`?`), never pasted into SQL text. Ask the data only fills fixed templates and runs read-only.

**How are passwords stored?** As scrypt hashes with a random salt. The password itself is never stored.

**How did you import 10.6 million rows without running out of memory?** Streamed the CSV into a staging SQLite file in batches, then let SQL add them up into one row per student per day (1.8M rows).

## Unique features

**How does the review queue work?** Leitner boxes. Wrong → box 1, back tomorrow. Right → next box, waiting 3, then 7 days, then learned. Wrong again → box 1.

**How do you know a quiz question is bad?** Item analysis. Difficulty = share right. Discrimination = share right in the top 27% minus the bottom 27%. If weaker students do better than stronger ones, the answer key may be wrong.

**How can you tell a certificate is fake?** Its SHA-256 fingerprint. We hash the code, name, course, date and score when issuing. Change any of them and the hash no longer matches.

**What does the mastery percentage mean?** A weighted average of the student's answers in that module, where newer answers count more (30% for the newest).

## Smart features

**Is there AI in it?** Yes, but no language model and no paid API. There are rule engines (ask the data, coach) and machine-learning models (at-risk logistic regression, k-means topics, TF-IDF/LSA for the drafter and recommender). All of it runs offline and every result can be explained.

**How does the at-risk model work?** Logistic regression on seven behaviour measures taken on a chosen day of the course: days since last activity, recent activity, active days, share of assessments handed in, average score, late registration, earlier attempts. It outputs a probability of not finishing.

**How good is it? How did you test it?** Trained on 2013 students, tested on 2014 students it never saw. ROC AUC 0.79, precision 0.66, recall 0.62, and it improves later in the course. In the app you can compare each prediction with what really happened.

**Why logistic regression and not something fancier?** It's accurate enough, fast, and explainable: each feature has a weight, so we can say *why* a student is flagged. That matters when the output is about a person.

**How does Ask the data work without AI writing SQL?** A rule-based parser finds the intent, subject, filters, grouping and limit, then fills a fixed SQL template. It can only ever produce a SELECT, refuses change words, and runs on a read-only connection.

**How does the drafter pick wrong options?** It looks for terms used in similar sentences elsewhere in the course, using LSA term vectors, so the options are plausible rather than random.

## Honest questions

**What doesn't work well?** Drafted distractors are sometimes weak (that's why every draft is reviewed). Ask the data only understands certain question shapes. The model flags some students who end up passing.

**What would you do next?** PostgreSQL and a web front end for many users; email reminders from the coach; retrain the model on the platform's own students once there are enough.

**What did you build yourself?** Answer honestly for your own part. Be ready to walk through `enroll()`, `submit()`, one trigger, and one smart feature line by line.
