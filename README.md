# 7777 — Smart Attendance Management System

This package is the **original project 1234** extended with the requested new features.
The original attendance, records, student dashboard, marks, results, documents,
registration and password-reset routes/templates were kept. The new functionality
is additive.

## Original core features kept
- Teacher/Admin login
- Student login
- Mark attendance with Present/Absent
- Duplicate attendance prevention
- Attendance records
- Student attendance dashboard
- Student bio-data
- Student password change
- Manage students
- Edit/delete students
- Dashboard statistics and class/month/year summaries
- Quarterly / Half-Yearly / Annual marks
- Results
- Portion / Blueprint PDF upload and viewing
- Forgot/reset password
- Teacher/Admin registration
- Responsive CSS/JavaScript

## Added features
- Multi-school system with isolated SQLite database per school
- Main login school selector
- Boss Admin who alone creates/manages school names
- Our School always exists
- Separate school data (students, teachers, attendance, marks, assignments, complaints, etc.)
- Teacher subject assignment
- Teacher class-teacher assignment
- Teacher-only subject-specific marks
- Written/external + internal marks (default 75 + 25)
- Assignments/projects and student file submission
- Student complaint system with teacher/admin recipient and status
- Complete student attendance history
- Shared event/festival/holiday calendar
- Admin announcements targeted to students, teachers, or both
- Profile photo upload
- Class timetables and common exam timetable
- Student OD requests with admin decision
- Protected student/teacher detail-change requests with admin approval
- Admin/teacher student-account creation with unique admission number
- Username/password editing with duplicate username checks
- Students can view Portion/Blueprint; only teachers/admins can upload

## Default accounts for Our School
- Boss Admin: `bossadmin` / `Boss@123`
- School Admin: `admin` / `Admin@123`
- Original Teacher: `teacher` / `Teacher@123`
- Added teachers: `teacher1` ... `teacher5` / `teacher@123`
- Students: admission number as initial username/password

## Run
```bash
pip install -r requirements.txt
python app.py
```

The application listens on `0.0.0.0:5004`.

## Important
The file `attendance.db` is the original school's existing database. Other schools
created by Boss Admin receive their own SQLite database under `school_data/`.
A student/teacher with the same name in another school is therefore a separate record.
