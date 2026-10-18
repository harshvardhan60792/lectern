# Entity–relationship diagram

The main tables and how they link. Crow's-foot notation: `||--o{` reads "one … to zero or many".
Bookkeeping tables (`app_session`, `model_runs`, `meta`) are left out.

```mermaid
erDiagram
    STUDENTS ||--o{ ENROLLMENTS : "enrolls in"
    COURSES ||--o{ ENROLLMENTS : "has"
    COURSES ||--o{ MODULES : "is split into"
    COURSES ||--o{ PREREQUISITES : "requires"
    COURSES ||--o{ MATERIALS : "offers"
    INSTRUCTORS |o--o{ COURSES : "teaches"
    MODULES ||--o{ LESSONS : "contains"
    MODULES ||--o{ QUESTIONS : "has bank of"
    QUESTIONS ||--o{ QUESTION_OPTIONS : "offers"
    STUDENTS ||--o{ MODULE_PROGRESS : "scores in"
    MODULES ||--o{ MODULE_PROGRESS : ""
    STUDENTS ||--o{ LESSON_PROGRESS : "reads"
    LESSONS ||--o{ LESSON_PROGRESS : ""
    STUDENTS ||--o{ QUIZ_ATTEMPTS : "takes"
    QUIZ_ATTEMPTS ||--o{ RESPONSES : "contains"
    STUDENTS ||--o{ RESPONSES : "gives"
    QUESTIONS ||--o{ RESPONSES : "answered in"
    STUDENTS ||--o{ REVIEW_QUEUE : "reviews"
    QUESTIONS ||--o{ REVIEW_QUEUE : ""
    STUDENTS ||--o{ ACTIVITY_DAYS : "studies on"
    STUDENTS ||--o{ MATERIAL_USE : "opens"
    MATERIALS ||--o{ MATERIAL_USE : ""
    STUDENTS ||--o{ CERTIFICATES : "earns"
    COURSES ||--o{ CERTIFICATES : "awards"
    STUDENTS |o--o| USERS : "signs in as"
    INSTRUCTORS |o--o| USERS : "signs in as"
    MODULE_PROGRESS ||--o{ GRADE_AUDIT : "changes logged by trigger"

    STUDENTS {
        int id PK
        text source "oulad | assistments | local"
        text external_id "ID in the dataset"
        text display_name
        text email UK
        text region
        text highest_education
    }
    COURSES {
        int id PK
        text code UK
        text title
        text source
        text starts_on
        int pass_mark "0-100"
    }
    ENROLLMENTS {
        int id PK
        int student_id FK
        int course_id FK
        text status "active | completed | failed | withdrawn"
        text final_result
    }
    MODULES {
        int id PK
        int course_id FK
        int position
        text kind "chapter | assessment | skill | topic"
        real weight
    }
    QUESTIONS {
        int id PK
        int module_id FK
        text source
        text prompt
        text status "live | draft | retired"
    }
    RESPONSES {
        int id PK
        int student_id FK
        int question_id FK
        int attempt_id FK
        int is_correct "0 or 1"
    }
    REVIEW_QUEUE {
        int student_id PK
        int question_id PK
        int box "1-4 Leitner box"
        text due_on
    }
    CERTIFICATES {
        int id PK
        text code UK
        int student_id FK
        int course_id FK
        text fingerprint "SHA-256"
        int revoked
    }
    ACTIVITY_DAYS {
        int student_id PK
        int course_id PK
        text day PK
        int clicks
    }
```

## Why it is shaped like this

- **Enrollments** sit between students and courses because the relationship is many-to-many (a student takes many courses; a course has many students). `UNIQUE (student_id, course_id)` stops double enrollment.
- **Module progress** and **review queue** use two-column primary keys: one row per student per module, one row per student per question.
- **Activity days** stores one row per student, course and day rather than 10.6 million raw clicks: the importer adds them up, so reports stay fast.
- **Question options** are a separate table, not columns `option_a … option_d`, so a question can have two to five options without empty columns.
- **Grade audit** is written only by a trigger, so no part of the app can change a score without leaving a record.
