-- L3: SQL on the real data. Run these in DB Browser for SQLite (Execute SQL tab, Ctrl+Enter).
-- Each one builds on the one before.

-- 1. All courses, sorted by title.
--    ORDER BY sorts the rows. ASC (A to Z) is the default.
SELECT code, title, subject
FROM courses
ORDER BY title;

-- 2. How many students there are.
--    COUNT(*) counts rows. One row comes back: 33,002 (plus anyone added in the app).
SELECT COUNT(*) AS students
FROM students;

-- 3. How many students come from each source.
--    GROUP BY makes one group per distinct value. COUNT runs once per group.
SELECT source, COUNT(*) AS students
FROM students
GROUP BY source
ORDER BY students DESC;

-- 4. Students who withdrew from course DDD-2013J.
--    Three tables joined through their keys: students.id = enrollments.student_id,
--    enrollments.course_id = courses.id. The WHERE keeps one course and one status.
SELECT s.display_name, e.enrolled_on, e.ended_on
FROM students s
JOIN enrollments e ON e.student_id = s.id
JOIN courses c     ON c.id = e.course_id
WHERE c.code = 'DDD-2013J'
  AND e.status = 'withdrawn'
ORDER BY e.ended_on;

-- 5. Number of enrollments per course, biggest first.
SELECT c.code, c.title, COUNT(e.id) AS enrollments
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.id   -- LEFT JOIN keeps courses with no enrollments (count 0)
GROUP BY c.id
ORDER BY enrollments DESC;

-- 6. The 5 highest assessment scores in DDD-2013J, with the student's name.
--    module_progress holds each student's score per module (for OU courses a module is an assessment).
SELECT s.display_name, m.title AS assessment, mp.best_score
FROM module_progress mp
JOIN modules m  ON m.id = mp.module_id
JOIN courses c  ON c.id = m.course_id
JOIN students s ON s.id = mp.student_id
WHERE c.code = 'DDD-2013J'
ORDER BY mp.best_score DESC, s.display_name
LIMIT 5;

-- Bonus: the same pass rate the app's "Ask the data" shows, written by hand.
SELECT s.highest_education,
       COUNT(*) AS enrollments,
       ROUND(100.0 * SUM(e.status = 'completed') / COUNT(*), 1) AS pass_rate
FROM enrollments e
JOIN students s ON s.id = e.student_id
WHERE s.source = 'oulad'
GROUP BY s.highest_education
ORDER BY pass_rate DESC;
