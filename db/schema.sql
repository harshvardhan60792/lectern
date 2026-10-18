-- Lectern database schema (SQLite).
-- Dates are stored as ISO text 'YYYY-MM-DD'; timestamps as 'YYYY-MM-DD HH:MM:SS'.

PRAGMA foreign_keys = ON;

-------------------------------------------------------------------------------
-- People
-------------------------------------------------------------------------------

CREATE TABLE instructors (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Students come from three places: the OULAD and ASSISTments datasets
-- (anonymised, so they have an ID instead of a name) and people added in the app.
CREATE TABLE students (
    id                 INTEGER PRIMARY KEY,
    source             TEXT NOT NULL CHECK (source IN ('oulad', 'assistments', 'local')),
    external_id        TEXT,
    display_name       TEXT NOT NULL,
    email              TEXT UNIQUE,
    gender             TEXT,
    region             TEXT,
    highest_education  TEXT,
    age_band           TEXT,
    imd_band           TEXT,
    disability         TEXT,
    created_at         TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source, external_id)
);

CREATE TABLE users (
    id             INTEGER PRIMARY KEY,
    username       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('admin', 'instructor', 'student')),
    student_id     INTEGER REFERENCES students(id) ON DELETE CASCADE,
    instructor_id  INTEGER REFERENCES instructors(id) ON DELETE CASCADE,
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    last_login_at  TEXT,
    CHECK ((role = 'student') = (student_id IS NOT NULL)),
    CHECK ((role = 'instructor') = (instructor_id IS NOT NULL))
);

-------------------------------------------------------------------------------
-- Courses and their content
-------------------------------------------------------------------------------

CREATE TABLE courses (
    id             INTEGER PRIMARY KEY,
    code           TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    subject        TEXT NOT NULL,
    description    TEXT NOT NULL DEFAULT '',
    source         TEXT NOT NULL CHECK (source IN ('oulad', 'assistments', 'openstax', 'sciq', 'local')),
    starts_on      TEXT,
    length_days    INTEGER CHECK (length_days > 0),
    pass_mark      INTEGER NOT NULL DEFAULT 40 CHECK (pass_mark BETWEEN 0 AND 100),
    instructor_id  INTEGER REFERENCES instructors(id) ON DELETE SET NULL,
    attribution    TEXT,
    archived       INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE prerequisites (
    course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    requires_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, requires_id),
    CHECK (course_id <> requires_id)
);

-- A module is one unit of a course: a book chapter, an assessment (OULAD),
-- a maths skill (ASSISTments) or a topic cluster (SciQ).
CREATE TABLE modules (
    id           INTEGER PRIMARY KEY,
    course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    title        TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('chapter', 'assessment', 'skill', 'topic')),
    external_id  TEXT,
    weight       REAL CHECK (weight >= 0),
    due_day      INTEGER,
    UNIQUE (course_id, position)
);

CREATE TABLE lessons (
    id           INTEGER PRIMARY KEY,
    module_id    INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    video_url    TEXT,
    source_page  INTEGER,
    UNIQUE (module_id, position)
);

-- Online learning materials of OULAD courses (the "VLE" in the dataset).
CREATE TABLE materials (
    id             INTEGER PRIMARY KEY,
    course_id      INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    external_id    TEXT NOT NULL,
    activity_type  TEXT NOT NULL,
    week_from      INTEGER,
    week_to        INTEGER,
    UNIQUE (course_id, external_id)
);

-------------------------------------------------------------------------------
-- Enrollment and progress
-------------------------------------------------------------------------------

CREATE TABLE enrollments (
    id               INTEGER PRIMARY KEY,
    student_id       INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id        INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_on      TEXT,
    status           TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'completed', 'failed', 'withdrawn')),
    ended_on         TEXT,
    final_result     TEXT,
    prev_attempts    INTEGER NOT NULL DEFAULT 0 CHECK (prev_attempts >= 0),
    studied_credits  INTEGER,
    UNIQUE (student_id, course_id)
);

CREATE TABLE module_progress (
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    module_id     INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    status        TEXT NOT NULL DEFAULT 'in_progress'
                  CHECK (status IN ('in_progress', 'completed')),
    best_score    REAL CHECK (best_score BETWEEN 0 AND 100),
    last_score    REAL CHECK (last_score BETWEEN 0 AND 100),
    completed_on  TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (student_id, module_id)
) WITHOUT ROWID;

CREATE TABLE lesson_progress (
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    completed_on  TEXT,
    watched_pct   INTEGER NOT NULL DEFAULT 0 CHECK (watched_pct BETWEEN 0 AND 100),
    PRIMARY KEY (student_id, lesson_id)
) WITHOUT ROWID;

-- One row per student, course and day with any study activity.
-- For OULAD this is the sum of clicks on the learning platform that day.
CREATE TABLE activity_days (
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    day         TEXT NOT NULL,
    clicks      INTEGER NOT NULL CHECK (clicks >= 0),
    PRIMARY KEY (student_id, course_id, day)
) WITHOUT ROWID;

CREATE TABLE material_use (
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    material_id  INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    clicks       INTEGER NOT NULL CHECK (clicks >= 0),
    first_day    TEXT,
    last_day     TEXT,
    PRIMARY KEY (student_id, material_id)
) WITHOUT ROWID;

-------------------------------------------------------------------------------
-- Questions, quizzes and answers
-------------------------------------------------------------------------------

CREATE TABLE questions (
    id           INTEGER PRIMARY KEY,
    module_id    INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    source       TEXT NOT NULL CHECK (source IN ('openstax', 'sciq', 'assistments', 'drafted', 'manual')),
    external_id  TEXT,
    prompt       TEXT,
    explanation  TEXT,
    support      TEXT,
    status       TEXT NOT NULL DEFAULT 'live' CHECK (status IN ('live', 'draft', 'retired')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source, external_id)
);

CREATE TABLE question_options (
    id           INTEGER PRIMARY KEY,
    question_id  INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    text         TEXT NOT NULL,
    is_correct   INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    UNIQUE (question_id, position)
);

CREATE TABLE quiz_attempts (
    id           INTEGER PRIMARY KEY,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    module_id    INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL DEFAULT 'quiz' CHECK (kind IN ('quiz', 'review')),
    started_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    finished_at  TEXT,
    score        REAL CHECK (score BETWEEN 0 AND 100),
    n_questions  INTEGER NOT NULL CHECK (n_questions > 0)
);

-- Every answer to every question. ASSISTments rows have no date, only an
-- order number (seq) inside the original log.
CREATE TABLE responses (
    id                INTEGER PRIMARY KEY,
    student_id        INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    question_id       INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    attempt_id        INTEGER REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    chosen_option_id  INTEGER REFERENCES question_options(id) ON DELETE SET NULL,
    is_correct        INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    answered_at       TEXT,
    seq               INTEGER,
    attempt_count     INTEGER,
    hint_count        INTEGER
);

-- Leitner boxes: 1 = due tomorrow, 2 = in 3 days, 3 = in 7 days, 4 = learned.
CREATE TABLE review_queue (
    student_id        INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    question_id       INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    box               INTEGER NOT NULL DEFAULT 1 CHECK (box BETWEEN 1 AND 4),
    due_on            TEXT NOT NULL,
    last_reviewed_on  TEXT,
    times_wrong       INTEGER NOT NULL DEFAULT 1 CHECK (times_wrong >= 0),
    PRIMARY KEY (student_id, question_id)
) WITHOUT ROWID;

-------------------------------------------------------------------------------
-- Certificates, audit, ML bookkeeping
-------------------------------------------------------------------------------

CREATE TABLE certificates (
    id           INTEGER PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    issued_on    TEXT NOT NULL,
    score        REAL CHECK (score BETWEEN 0 AND 100),
    grade        TEXT,
    fingerprint  TEXT NOT NULL,
    revoked      INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0, 1)),
    UNIQUE (student_id, course_id)
);

CREATE TABLE grade_audit (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL,
    module_id   INTEGER NOT NULL,
    old_score   REAL,
    new_score   REAL,
    changed_by  INTEGER,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Holds the logged-in user so triggers can record who made a change.
CREATE TABLE app_session (
    id       INTEGER PRIMARY KEY CHECK (id = 1),
    user_id  INTEGER
);
INSERT INTO app_session (id, user_id) VALUES (1, NULL);

CREATE TABLE model_runs (
    id          INTEGER PRIMARY KEY,
    model       TEXT NOT NULL,
    trained_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    n_train     INTEGER NOT NULL,
    n_test      INTEGER NOT NULL,
    accuracy    REAL,
    precision   REAL,
    recall      REAL,
    roc_auc     REAL,
    details     TEXT
);

CREATE TABLE meta (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

-------------------------------------------------------------------------------
-- Indexes
-------------------------------------------------------------------------------

CREATE INDEX idx_students_name        ON students (display_name);
CREATE INDEX idx_enrollments_course   ON enrollments (course_id, status);
CREATE INDEX idx_modules_course       ON modules (course_id);
CREATE INDEX idx_lessons_module       ON lessons (module_id);
CREATE INDEX idx_questions_module     ON questions (module_id, status);
CREATE INDEX idx_options_question     ON question_options (question_id);
CREATE INDEX idx_responses_question   ON responses (question_id);
CREATE INDEX idx_responses_student    ON responses (student_id, seq);
CREATE INDEX idx_progress_module      ON module_progress (module_id);
CREATE INDEX idx_activity_course_day  ON activity_days (course_id, day);
CREATE INDEX idx_material_use_mat     ON material_use (material_id);
CREATE INDEX idx_review_due           ON review_queue (student_id, due_on);
CREATE INDEX idx_certificates_course  ON certificates (course_id);

-------------------------------------------------------------------------------
-- Triggers
-------------------------------------------------------------------------------

-- Record every score change with who made it.
CREATE TRIGGER trg_grade_audit
AFTER UPDATE OF best_score ON module_progress
WHEN OLD.best_score IS NOT NEW.best_score
BEGIN
    INSERT INTO grade_audit (student_id, module_id, old_score, new_score, changed_by)
    VALUES (NEW.student_id, NEW.module_id, OLD.best_score, NEW.best_score,
            (SELECT user_id FROM app_session WHERE id = 1));
END;

-- The database itself refuses an enrollment whose prerequisites are not completed.
CREATE TRIGGER trg_enrollment_prerequisites
BEFORE INSERT ON enrollments
WHEN EXISTS (
    SELECT 1 FROM prerequisites p
    WHERE p.course_id = NEW.course_id
      AND NOT EXISTS (
          SELECT 1 FROM enrollments e
          WHERE e.student_id = NEW.student_id
            AND e.course_id = p.requires_id
            AND e.status = 'completed')
)
BEGIN
    SELECT RAISE(ABORT, 'prerequisite not completed');
END;

-- A certificate can only exist for a completed enrollment.
CREATE TRIGGER trg_certificate_requires_completion
BEFORE INSERT ON certificates
WHEN NOT EXISTS (
    SELECT 1 FROM enrollments e
    WHERE e.student_id = NEW.student_id
      AND e.course_id = NEW.course_id
      AND e.status = 'completed'
)
BEGIN
    SELECT RAISE(ABORT, 'course not completed');
END;

-------------------------------------------------------------------------------
-- Views used by reports
-------------------------------------------------------------------------------

CREATE VIEW v_course_stats AS
SELECT c.id                                              AS course_id,
       c.code,
       c.title,
       c.source,
       COUNT(e.id)                                       AS enrolled,
       SUM(e.status = 'completed')                       AS completed,
       SUM(e.status = 'failed')                          AS failed,
       SUM(e.status = 'withdrawn')                       AS withdrawn,
       SUM(e.status = 'active')                          AS active,
       ROUND(100.0 * SUM(e.status = 'completed')
             / NULLIF(SUM(e.status <> 'active'), 0), 1)  AS completion_rate
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.id
GROUP BY c.id;

CREATE VIEW v_enrollment_scores AS
SELECT e.id          AS enrollment_id,
       e.student_id,
       e.course_id,
       e.status,
       COUNT(mp.module_id)                        AS modules_done,
       ROUND(AVG(mp.best_score), 1)               AS avg_score,
       -- weighted by the assessments actually taken; plain average when those carry no weight
       ROUND(COALESCE(SUM(mp.best_score * m.weight)
                      / NULLIF(SUM(CASE WHEN mp.best_score IS NOT NULL THEN m.weight END), 0),
                      AVG(mp.best_score)), 1)    AS weighted_score
FROM enrollments e
LEFT JOIN modules m          ON m.course_id = e.course_id
LEFT JOIN module_progress mp ON mp.module_id = m.id AND mp.student_id = e.student_id
GROUP BY e.id;

CREATE VIEW v_monthly_enrollments AS
SELECT substr(enrolled_on, 1, 7) AS month,
       COUNT(*)                  AS enrollments
FROM enrollments
WHERE enrolled_on IS NOT NULL
GROUP BY month;
