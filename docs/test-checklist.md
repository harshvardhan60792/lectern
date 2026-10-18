# Click-test checklist

Tick each line. If something breaks or looks wrong, write: *screen → what you did → what happened*.

## Sign in
- [ ] Wrong password shows "Wrong username or password" and clears the password box
- [ ] Right password opens the Overview
- [ ] The book on the sign-in screen turns its pages once
- [ ] Dark / Light button switches appearance; every screen stays readable
- [ ] Ctrl+K opens the jump-to palette; typing "rep" and Enter opens Reports
- [ ] Sign out returns to the sign-in screen

## Students
- [ ] Search "OU-11" shows matching students; clearing the box shows everyone again
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

## Courses
- [ ] Select DDD-2013J → About, Modules, Prerequisites, Insights tabs all open
- [ ] Insights shows the weekly activity chart and the scores chart
- [ ] New course with code `x` → error; with code `WEB-101` → created
- [ ] Add a module, rename it, move it up/down
- [ ] Add a lesson with a video link starting `ftp://` → error; with `https://` → saved
- [ ] Open a module (arrow), click a lesson → it opens to read
- [ ] PY-102 Prerequisites tab shows PY-101 and the course map
- [ ] Course cards lean slightly toward the mouse

## Enrollments
- [ ] Search a student, pick PY-102, Enroll → "Finish these first: Python programming I"
- [ ] Pick PY-101, Enroll → success; enrolling again → "Already enrolled"
- [ ] Drop → success; the student shows as withdrawn

## Learning (as a student or via Learner view)
- [ ] Browse courses: cards in the drawer lift on hover and pull out when clicked
- [ ] Continue opens the course; lessons open; "Mark as read and continue" moves on
- [ ] Watch the video opens the browser
- [ ] Take quiz → answer all → Submit → score and feedback appear
- [ ] Next day (or after wrong answers), "Start review" appears on the home page

## Question bank
- [ ] PY-101 → module → Bank lists questions; clicking one previews it; Show answer flips the card
- [ ] Draft from lessons → Draft questions → drafts appear; Save kept as drafts → message
- [ ] Maths skill builder → Health check → Run check → counts and table appear

## Reports, Ask the data, At-risk, Certificates
- [ ] Each Reports tab shows a chart or table; Save as CSV opens the exports folder
- [ ] Ask the data: each example button gives an answer and shows the SQL
- [ ] Ask "delete all students" → refused
- [ ] At-risk: change course and day → table and numbers update; selecting a row shows reasons
- [ ] Certificates: select one → Turn it over shows the fingerprint → Save PDF opens a PDF
- [ ] Verify with the right code → Genuine; add score 99 → Not valid
