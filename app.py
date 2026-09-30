from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

import sqlite3
import os
import secrets
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename

from pathlib import Path
from datetime import datetime, timedelta

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ==========================================================
# APP SETTINGS
# ==========================================================

app = Flask(__name__)

# Local runs keep a per-process key. On Vercel a stable key is required
# or every cold start logs everyone out. Override with SECRET_KEY.
app.secret_key = os.environ.get("SECRET_KEY") or (
    "attenzyra-hosted-session" if os.environ.get("VERCEL") else secrets.token_hex(32)
)

BASE_FOLDER = Path(__file__).resolve().parent
DATABASE_FILE = BASE_FOLDER / "attendance.db"

# Vercel can read the project but cannot write beside it. When VERCEL is set,
# copy the existing databases and static files to /tmp and write only there.
# `python app.py` on a normal machine does not enter this branch.
if os.environ.get("VERCEL"):
    import shutil

    _bundle_folder = BASE_FOLDER
    BASE_FOLDER = Path("/tmp/attenzyra")
    if not (BASE_FOLDER / ".ready").exists():
        if BASE_FOLDER.exists():
            shutil.rmtree(BASE_FOLDER, ignore_errors=True)
        BASE_FOLDER.mkdir(parents=True, exist_ok=True)
        for _db_name in ("attendance.db", "schools_master.db"):
            _src = _bundle_folder / _db_name
            if _src.exists():
                shutil.copy2(_src, BASE_FOLDER / _db_name)
        _schools = _bundle_folder / "school_data"
        if _schools.exists():
            shutil.copytree(_schools, BASE_FOLDER / "school_data")
        else:
            (BASE_FOLDER / "school_data").mkdir(parents=True, exist_ok=True)
        _static = _bundle_folder / "static"
        if _static.exists():
            shutil.copytree(_static, BASE_FOLDER / "static")
        (BASE_FOLDER / ".ready").write_text("1", encoding="utf-8")
    DATABASE_FILE = BASE_FOLDER / "attendance.db"
    app.static_folder = str((BASE_FOLDER / "static").resolve())
CLASSES = [
    "Class LKG A", "Class LKG B", "Class LKG C",
    "Class LKG D", "Class LKG E", "Class LKG F",

    "Class UKG A", "Class UKG B", "Class UKG C",
    "Class UKG D", "Class UKG E", "Class UKG F",

    "Class 1 A", "Class 1 B", "Class 1 C", "Class 1 D",
    "Class 2 A", "Class 2 B", "Class 2 C", "Class 2 D",
    "Class 3 A", "Class 3 B", "Class 3 C", "Class 3 D",
    "Class 4 A", "Class 4 B", "Class 4 C", "Class 4 D",
    "Class 5 A", "Class 5 B", "Class 5 C", "Class 5 D",
    "Class 6 A", "Class 6 B", "Class 6 C", "Class 6 D",
    "Class 7 A", "Class 7 B", "Class 7 C", "Class 7 D",
    "Class 8 A", "Class 8 B", "Class 8 C", "Class 8 D",
    "Class 9 A", "Class 9 B", "Class 9 C", "Class 9 D",
    "Class 10 A", "Class 10 B", "Class 10 C", "Class 10 D",
    "Class 11 A", "Class 11 B", "Class 11 C", "Class 11 D",
    "Class 12 A", "Class 12 B", "Class 12 C", "Class 12 D",
]


# ==========================================================
# DEFAULT STUDENTS
# ==========================================================

DEFAULT_STUDENTS = {

    "1001": {
        "name": "Srinivasan",
        "class_name": "Class 12 C"
    },

    "1002": {
        "name": "Rupesh",
        "class_name": "Class 12 C"
    },

    "1003": {
        "name": "Gokul",
        "class_name": "Class 12 C"
    },

    "1004": {
        "name": "Hamsini",
        "class_name": "Class 12 C"
    },

    "1005": {
        "name": "Harshitha",
        "class_name": "Class 12 C"
    },

    "1006": {
        "name": "Srinidhi",
        "class_name": "Class 12 C"
    },

    "1007": {
        "name": "Joshitha",
        "class_name": "Class 12 C"
    },

    "1008": {
        "name": "Abinaya",
        "class_name": "Class 12 C"
    }
}


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_db_connection():

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================================
# DATABASE SETUP
# ==========================================================

def setup_database(seed_default_data=True):

    connection = get_db_connection()

    cursor = connection.cursor()


    # ======================================================
    # USERS
    # ======================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL
        )
    """)


    # ======================================================
    # STUDENTS
    # ======================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            admission_no TEXT PRIMARY KEY,

            name TEXT NOT NULL,

            class_name TEXT DEFAULT 'Unassigned',

            password TEXT,

            roll_no TEXT,

            blood_group TEXT,

            mother_phone TEXT,

            father_phone TEXT,

            mother_email TEXT,

            father_email TEXT,

            address TEXT
        )
    """)


    # ======================================================
    # SAFE DATABASE MIGRATION
    #
    # This prevents old attendance.db files from breaking.
    # ======================================================

    existing_columns = cursor.execute(
        "PRAGMA table_info(students)"
    ).fetchall()

    existing_names = {
        column["name"]
        for column in existing_columns
    }


    required_columns = {

        "class_name": "TEXT DEFAULT 'Unassigned'",

        "password": "TEXT",

        "roll_no": "TEXT",

        "blood_group": "TEXT",

        "mother_phone": "TEXT",

        "father_phone": "TEXT",

        "mother_email": "TEXT",

        "father_email": "TEXT",

        "address": "TEXT"
    }


    for column_name, column_type in required_columns.items():

        if column_name not in existing_names:

            cursor.execute(
                f"""
                ALTER TABLE students
                ADD COLUMN {column_name}
                {column_type}
                """
            )


    # ======================================================
    # ATTENDANCE
    # ======================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            time TEXT NOT NULL,

            admission_no TEXT NOT NULL,

            student_name TEXT NOT NULL,

            status TEXT NOT NULL,

            UNIQUE(date, admission_no)
        )
    """)


    # ======================================================
    # DEFAULT ADMIN / TEACHER + STUDENTS
    # ======================================================
    # Existing school databases keep their original starter data.
    # Newly created schools are schema-only and start empty.
    # ======================================================

    if seed_default_data:
        users = [
            ("teacher", generate_password_hash("Teacher@123"), "teacher"),
            ("admin", generate_password_hash("Admin@123"), "admin")
        ]

        for username, password, role in users:
            existing = cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO users (username, password, role)
                    VALUES (?, ?, ?)
                    """,
                    (username, password, role)
                )

        student_count = cursor.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        if student_count == 0:
            for admission_no, student in DEFAULT_STUDENTS.items():
                cursor.execute(
                    """
                    INSERT INTO students
                    (admission_no, name, class_name, password)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        admission_no,
                        student["name"],
                        student["class_name"],
                        generate_password_hash(admission_no)
                    )
                )
        else:
            old_students = cursor.execute(
                "SELECT admission_no FROM students WHERE password IS NULL"
            ).fetchall()
            for student in old_students:
                cursor.execute(
                    "UPDATE students SET password = ? WHERE admission_no = ?",
                    (generate_password_hash(student["admission_no"]), student["admission_no"])
                )

    connection.commit()

    connection.close()



# ==========================================================
# EXTRA FEATURES DATABASE SETUP
# ==========================================================

def setup_extra_database():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Add contact details without breaking existing databases.
    migrations = {
        "users": {
            "email": "TEXT",
        },
        "students": {
            "email": "TEXT",
            "phone": "TEXT",
        },
    }

    for table, columns in migrations.items():
        existing = {
            row["name"]
            for row in cursor.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
                )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_no TEXT NOT NULL,
            exam_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            marks REAL NOT NULL,
            max_marks REAL NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL,
            UNIQUE(admission_no, exam_type, subject)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            uploaded_by TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT NOT NULL,
            account_key TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def send_password_reset_email(recipient, reset_url):
    """Send a reset email when SMTP settings are configured."""
    smtp_host = os.environ.get("ATTENDORA_SMTP_HOST")
    smtp_port = int(os.environ.get("ATTENDORA_SMTP_PORT", "587"))
    smtp_user = os.environ.get("ATTENDORA_SMTP_USER")
    smtp_password = os.environ.get("ATTENDORA_SMTP_PASSWORD")
    smtp_from = os.environ.get("ATTENDORA_SMTP_FROM", smtp_user or "")

    if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
        return False

    message = EmailMessage()
    message["Subject"] = "ATTENZYRA Password Reset"
    message["From"] = smtp_from
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your ATTENZYRA account.\n\n"
        f"Use this link within 30 minutes:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

    return True


def build_reset_url(token):
    return url_for("reset_password", token=token, _external=True)


# Initialize both the original and enhanced database structures.
# Safe to run repeatedly because all setup operations are idempotent.
setup_database()
setup_extra_database()


# ==========================================================
# AUTHENTICATION HELPERS
# ==========================================================

def login_required():

    return "user_id" in session


def admin_required():

    return (
        login_required()
        and session.get("role") == "admin"
    )


def teacher_or_admin_required():

    return (
        login_required()
        and session.get("role")
        in ["teacher", "admin"]
    )


def student_required():

    return (
        login_required()
        and session.get("role") == "student"
    )


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():

    if not login_required():

        return redirect(
            url_for("login")
        )


    if session.get("role") == "student":

        return redirect(
            url_for("student_dashboard")
        )


    return redirect(
        url_for("dashboard")
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if login_required():

        if session.get("role") == "student":

            return redirect(
                url_for("student_dashboard")
            )

        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        connection = get_db_connection()


        # ==================================================
        # ADMIN / TEACHER
        # ==================================================

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username.lower(),)
        ).fetchone()


        if user and check_password_hash(
            user["password"],
            password
        ):

            connection.close()

            session.clear()

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["role"] = user["role"]


            flash(
                f"Welcome, {user['role'].title()}!",
                "success"
            )


            return redirect(
                url_for("dashboard")
            )


        # ==================================================
        # STUDENT
        # ==================================================

        student = connection.execute(
            """
            SELECT *
            FROM students
            WHERE admission_no = ?
            """,
            (username,)
        ).fetchone()


        connection.close()


        if student and student["password"]:

            if check_password_hash(
                student["password"],
                password
            ):

                session.clear()

                session["user_id"] = student[
                    "admission_no"
                ]

                session["username"] = student[
                    "admission_no"
                ]

                session["role"] = "student"

                session["admission_no"] = student[
                    "admission_no"
                ]


                flash(
                    f"Welcome, {student['name']}!",
                    "success"
                )


                return redirect(
                    url_for("student_dashboard")
                )


        flash(
            "Invalid username or password.",
            "error"
        )


    return render_template(
        "login.html"
    )


# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ==========================================================
# TEACHER / ADMIN DASHBOARD
# ==========================================================

@app.route("/dashboard")
def dashboard():

    if not teacher_or_admin_required():

        if student_required():

            return redirect(
                url_for("student_dashboard")
            )

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    today = datetime.now().strftime(
        "%d-%m-%Y"
    )


    selected_class = request.args.get(
        "class_name",
        ""
    ).strip()


    # ======================================================
    # STATISTICS
    # ======================================================

    if selected_class:

        total_students = connection.execute(
            """
            SELECT COUNT(*)
            FROM students
            WHERE class_name = ?
            """,
            (selected_class,)
        ).fetchone()[0]


        recorded_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance a

            INNER JOIN students s
            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]


        present = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance a

            INNER JOIN students s
            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND a.status = 'Present'

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]


        absent = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance a

            INNER JOIN students s
            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND a.status = 'Absent'

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]

    else:

        total_students = connection.execute(
            """
            SELECT COUNT(*)
            FROM students
            """
        ).fetchone()[0]


        recorded_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?
            """,
            (today,)
        ).fetchone()[0]


        present = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?

            AND status = 'Present'
            """,
            (today,)
        ).fetchone()[0]


        absent = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?

            AND status = 'Absent'
            """,
            (today,)
        ).fetchone()[0]


    # ======================================================
    # CLASS LIST
    # ======================================================

    classes = connection.execute(
        """
        SELECT
            class_name,
            COUNT(*) AS student_count

        FROM students

        GROUP BY class_name

        ORDER BY class_name
        """
    ).fetchall()


    class_names = CLASSES


    # ======================================================
    # TODAY CLASS SUMMARY
    # ======================================================

    class_summary = connection.execute(
        """
        SELECT

            s.class_name,

            COUNT(
                DISTINCT s.admission_no
            ) AS total_students,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Present'
                    THEN a.admission_no
                END
            ) AS present,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Absent'
                    THEN a.admission_no
                END
            ) AS absent,

            COUNT(
                DISTINCT a.admission_no
            ) AS recorded

        FROM students s

        LEFT JOIN attendance a

        ON s.admission_no = a.admission_no

        AND a.date = ?

        GROUP BY s.class_name

        ORDER BY s.class_name
        """,
        (today,)
    ).fetchall()


    connection.close()


    return render_template(
        "dashboard.html",

        total_students=total_students,

        recorded_today=recorded_today,

        present=present,

        absent=absent,

        today=today,

        class_names=class_names,

        classes=classes,

        class_summary=class_summary,

        selected_class=selected_class
    )


# ==========================================================
# STUDENT DASHBOARD
# ==========================================================

@app.route("/student-dashboard")
def student_dashboard():

    if not student_required():

        return redirect(
            url_for("login")
        )


    admission_no = session.get(
        "admission_no"
    )


    connection = get_db_connection()


    student = connection.execute(
        """
        SELECT *
        FROM students
        WHERE admission_no = ?
        """,
        (admission_no,)
    ).fetchone()


    if student is None:

        connection.close()

        session.clear()

        flash(
            "Student account not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    total_days = connection.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE admission_no = ?
        """,
        (admission_no,)
    ).fetchone()[0]


    present_days = connection.execute(
        """
        SELECT COUNT(*)
        FROM attendance

        WHERE admission_no = ?

        AND status = 'Present'
        """,
        (admission_no,)
    ).fetchone()[0]


    absent_days = connection.execute(
        """
        SELECT COUNT(*)
        FROM attendance

        WHERE admission_no = ?

        AND status = 'Absent'
        """,
        (admission_no,)
    ).fetchone()[0]


    if total_days > 0:

        attendance_percentage = round(
            (
                present_days
                / total_days
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0


    records = connection.execute(
        """
        SELECT *
        FROM attendance

        WHERE admission_no = ?

        ORDER BY id DESC
        """,
        (admission_no,)
    ).fetchall()


    connection.close()


    return render_template(
        "student_dashboard.html",

        student=student,

        total_days=total_days,

        present_days=present_days,

        absent_days=absent_days,

        attendance_percentage=attendance_percentage,

        records=records
    )


# ==========================================================
# STUDENT BIO DATA
# ==========================================================

@app.route(
    "/student-biodata",
    methods=["GET", "POST"]
)
def student_biodata():

    if not student_required():

        return redirect(
            url_for("login")
        )


    admission_no = session.get(
        "admission_no"
    )


    connection = get_db_connection()


    student = connection.execute(
        """
        SELECT *
        FROM students
        WHERE admission_no = ?
        """,
        (admission_no,)
    ).fetchone()


    if student is None:

        connection.close()

        flash(
            "Student record not found.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )


    if request.method == "POST":

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        blood_group = request.form.get(
            "blood_group",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        mother_phone = request.form.get(
            "mother_phone",
            ""
        ).strip()

        father_phone = request.form.get(
            "father_phone",
            ""
        ).strip()

        mother_email = request.form.get(
            "mother_email",
            ""
        ).strip()

        father_email = request.form.get(
            "father_email",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()


        if not name:

            connection.close()

            flash(
                "Student name is required.",
                "error"
            )

            return redirect(
                url_for("student_biodata")
            )


        connection.execute(
            """
            UPDATE students

            SET

                roll_no = ?,

                name = ?,

                blood_group = ?,

                email = ?,

                phone = ?,

                mother_phone = ?,

                father_phone = ?,

                mother_email = ?,

                father_email = ?,

                address = ?

            WHERE admission_no = ?
            """,
            (
                roll_no,
                name,
                blood_group,
                email,
                phone,
                mother_phone,
                father_phone,
                mother_email,
                father_email,
                address,
                admission_no
            )
        )


        connection.commit()

        connection.close()


        flash(
            "Your bio-data has been saved successfully.",
            "success"
        )


        return redirect(
            url_for("student_biodata")
        )


    connection.close()


    return render_template(
        "student_biodata.html",
        student=student
    )


# ==========================================================
# STUDENT CHANGE PASSWORD
# ==========================================================

@app.route(
    "/student-change-password",
    methods=["GET", "POST"]
)
def student_change_password():

    if not student_required():

        return redirect(
            url_for("login")
        )


    admission_no = session.get(
        "admission_no"
    )


    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        if not current_password or not new_password:

            flash(
                "All password fields are required.",
                "error"
            )

            return redirect(
                url_for("student_change_password")
            )


        if new_password != confirm_password:

            flash(
                "New passwords do not match.",
                "error"
            )

            return redirect(
                url_for("student_change_password")
            )


        if len(new_password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("student_change_password")
            )


        connection = get_db_connection()


        student = connection.execute(
            """
            SELECT password
            FROM students
            WHERE admission_no = ?
            """,
            (admission_no,)
        ).fetchone()


        if (
            not student
            or not student["password"]
            or not check_password_hash(
                student["password"],
                current_password
            )
        ):

            connection.close()

            flash(
                "Current password is incorrect.",
                "error"
            )

            return redirect(
                url_for("student_change_password")
            )


        connection.execute(
            """
            UPDATE students

            SET password = ?

            WHERE admission_no = ?
            """,
            (
                generate_password_hash(
                    new_password
                ),
                admission_no
            )
        )


        connection.commit()

        connection.close()


        flash(
            "Password changed successfully.",
            "success"
        )


        return redirect(
            url_for("student_dashboard")
        )


    return render_template(
        "student_change_password.html"
    )


# ==========================================================
# MARK ATTENDANCE
# ==========================================================

@app.route(
    "/mark-attendance",
    methods=["GET", "POST"]
)
def mark_attendance():

    if not teacher_or_admin_required():

        if student_required():

            return redirect(
                url_for("student_dashboard")
            )

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    today = datetime.now().strftime(
        "%d-%m-%Y"
    )


    selected_class = request.args.get(
        "class_name",
        ""
    ).strip()


    if selected_class:

        students = connection.execute(
            """
            SELECT *
            FROM students

            WHERE class_name = ?

            ORDER BY admission_no
            """,
            (selected_class,)
        ).fetchall()

    else:

        students = connection.execute(
            """
            SELECT *
            FROM students

            ORDER BY class_name, admission_no
            """
        ).fetchall()


    recorded = connection.execute(
        """
        SELECT admission_no
        FROM attendance
        WHERE date = ?
        """,
        (today,)
    ).fetchall()


    recorded_numbers = {
        row["admission_no"]
        for row in recorded
    }


    remaining_students = [

        student

        for student in students

        if student["admission_no"]
        not in recorded_numbers
    ]


    if request.method == "POST":

        if not remaining_students:

            connection.close()

            flash(
                "Attendance has already been recorded for every student today.",
                "error"
            )

            return redirect(
                url_for(
                    "mark_attendance",
                    class_name=selected_class
                )
            )


        absent_students = request.form.getlist(
            "absent_students"
        )


        valid_numbers = {
            student["admission_no"]
            for student in remaining_students
        }


        invalid_students = [

            number

            for number in absent_students

            if number not in valid_numbers
        ]


        if invalid_students:

            connection.close()

            flash(
                "Invalid student selection detected.",
                "error"
            )

            return redirect(
                url_for(
                    "mark_attendance",
                    class_name=selected_class
                )
            )


        now = datetime.now()

        date = now.strftime(
            "%d-%m-%Y"
        )

        time = now.strftime(
            "%I:%M:%S %p"
        )


        try:

            for student in remaining_students:

                admission_no = student[
                    "admission_no"
                ]

                name = student[
                    "name"
                ]


                if admission_no in absent_students:

                    status = "Absent"

                else:

                    status = "Present"


                connection.execute(
                    """
                    INSERT INTO attendance
                    (
                        date,
                        time,
                        admission_no,
                        student_name,
                        status
                    )

                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        date,
                        time,
                        admission_no,
                        name,
                        status
                    )
                )


            connection.commit()


            present_count = (
                len(remaining_students)
                - len(absent_students)
            )


            connection.close()


            flash(
                f"Attendance saved successfully! "
                f"Present: {present_count} | "
                f"Absent: {len(absent_students)}",
                "success"
            )


            return redirect(
                url_for(
                    "dashboard",
                    class_name=selected_class
                )
            )


        except sqlite3.IntegrityError:

            connection.rollback()

            connection.close()


            flash(
                "Duplicate attendance was prevented.",
                "error"
            )


            return redirect(
                url_for(
                    "dashboard",
                    class_name=selected_class
                )
            )


    class_rows = connection.execute(
        """
        SELECT DISTINCT class_name
        FROM students
        WHERE TRIM(class_name) <> ''
        ORDER BY class_name
        """
    ).fetchall()

    class_names = CLASSES


    connection.close()


    return render_template(
        "mark_attendance.html",

        students=remaining_students,

        today=today,

        selected_class=selected_class,

        class_names=class_names
    )


# ==========================================================
# ATTENDANCE RECORDS
# ==========================================================

@app.route("/attendance-records")
def attendance_records():

    if not teacher_or_admin_required():

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    selected_date = request.args.get(
        "date"
    )


    selected_class = request.args.get(
        "class_name",
        ""
    ).strip()


    search = request.args.get(
        "search",
        ""
    ).strip()


    query = """
        SELECT

            a.*,

            s.class_name,

            s.roll_no

        FROM attendance a

        LEFT JOIN students s

        ON a.admission_no = s.admission_no

        WHERE 1 = 1
    """


    parameters = []


    if selected_date:

        query += """
            AND a.date = ?
        """

        parameters.append(
            selected_date
        )


    if selected_class:

        query += """
            AND s.class_name = ?
        """

        parameters.append(
            selected_class
        )


    if search:

        query += """
            AND
            (
                a.admission_no LIKE ?

                OR a.student_name LIKE ?

                OR s.roll_no LIKE ?
            )
        """

        parameters.extend(
            [
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ]
        )


    query += """
        ORDER BY a.id DESC
    """


    records = connection.execute(
        query,
        parameters
    ).fetchall()


    classes = connection.execute(
        """
        SELECT DISTINCT class_name
        FROM students
        ORDER BY class_name
        """
    ).fetchall()


    class_names = CLASSES


    connection.close()


    return render_template(
        "attendance_records.html",

        records=records,

        selected_date=selected_date,

        selected_class=selected_class,

        search=search,

        class_names=class_names
    )


# ==========================================================
# MANAGE STUDENTS
# ==========================================================

@app.route(
    "/manage-students",
    methods=["GET", "POST"]
)
def manage_students():

    if not admin_required():

        flash(
            "Only the admin can manage students.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )


    connection = get_db_connection()


    if request.method == "POST":

        admission_no = request.form.get(
            "admission_no",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        ).strip()

        blood_group = request.form.get("blood_group", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()


        if (
            not admission_no
            or not name
            or not class_name
        ):

            connection.close()

            flash(
                "Admission number, student name and class are required.",
                "error"
            )

            return redirect(
                url_for("manage_students")
            )


        try:

            connection.execute(
                """
                INSERT INTO students
                (
                    admission_no,
                    name,
                    class_name,
                    password,
                    blood_group,
                    email,
                    phone,
                    address
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    admission_no,
                    name,
                    class_name,
                    generate_password_hash(
                        admission_no
                    ),
                    blood_group,
                    email,
                    phone,
                    address
                )
            )


            connection.commit()


            flash(
                "Student added successfully. "
                "Initial password is the admission number.",
                "success"
            )


        except sqlite3.IntegrityError:

            flash(
                "Admission number already exists.",
                "error"
            )


        connection.close()


        return redirect(
            url_for("manage_students")
        )


    students = connection.execute(
        """
        SELECT

            admission_no,

            name,

            class_name,

            roll_no,

            blood_group,

            mother_phone,

            father_phone,

            mother_email,

            father_email,

            address

        FROM students

        ORDER BY class_name, admission_no
        """
    ).fetchall()


    connection.close()


    return render_template(
        "manage_students.html",
        students=students
    )


# ==========================================================
# EDIT STUDENT
# ==========================================================

@app.route(
    "/edit-student/<admission_no>",
    methods=["POST"]
)
def edit_student(admission_no):

    if not admin_required():

        return jsonify(
            {
                "success": False,
                "message": "Unauthorized"
            }
        ), 403


    name = request.form.get(
        "name",
        ""
    ).strip()


    class_name = request.form.get(
        "class_name",
        ""
    ).strip()


    if not name or not class_name:

        return jsonify(
            {
                "success": False,
                "message":
                    "Student name and class cannot be empty."
            }
        )


    connection = get_db_connection()


    connection.execute(
        """
        UPDATE students

        SET

            name = ?,

            class_name = ?

        WHERE admission_no = ?
        """,
        (
            name,
            class_name,
            admission_no
        )
    )


    connection.commit()

    connection.close()


    return jsonify(
        {
            "success": True,
            "message":
                "Student updated successfully."
        }
    )


# ==========================================================
# DELETE STUDENT
# ==========================================================

@app.route(
    "/delete-student/<admission_no>",
    methods=["POST"]
)
def delete_student(admission_no):

    if not admin_required():

        return jsonify(
            {
                "success": False,
                "message": "Unauthorized"
            }
        ), 403


    connection = get_db_connection()


    student = connection.execute(
        """
        SELECT *
        FROM students
        WHERE admission_no = ?
        """,
        (admission_no,)
    ).fetchone()


    if student is None:

        connection.close()

        return jsonify(
            {
                "success": False,
                "message": "Student not found."
            }
        )


    connection.execute(
        """
        DELETE FROM students
        WHERE admission_no = ?
        """,
        (admission_no,)
    )


    connection.commit()

    connection.close()


    return jsonify(
        {
            "success": True,
            "message":
                "Student deleted successfully."
        }
    )


# ==========================================================
# DASHBOARD SUMMARY API
# ==========================================================

@app.route("/api/dashboard-summary")
def dashboard_summary():

    if not teacher_or_admin_required():

        return jsonify(
            {
                "error": "Unauthorized"
            }
        ), 401


    connection = get_db_connection()


    today = datetime.now().strftime(
        "%d-%m-%Y"
    )


    selected_class = request.args.get(
        "class_name",
        ""
    ).strip()


    if selected_class:

        total_students = connection.execute(
            """
            SELECT COUNT(*)
            FROM students
            WHERE class_name = ?
            """,
            (selected_class,)
        ).fetchone()[0]


        recorded_today = connection.execute(
            """
            SELECT COUNT(*)

            FROM attendance a

            INNER JOIN students s

            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]


        present = connection.execute(
            """
            SELECT COUNT(*)

            FROM attendance a

            INNER JOIN students s

            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND a.status = 'Present'

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]


        absent = connection.execute(
            """
            SELECT COUNT(*)

            FROM attendance a

            INNER JOIN students s

            ON a.admission_no = s.admission_no

            WHERE a.date = ?

            AND a.status = 'Absent'

            AND s.class_name = ?
            """,
            (
                today,
                selected_class
            )
        ).fetchone()[0]

    else:

        total_students = connection.execute(
            """
            SELECT COUNT(*)
            FROM students
            """
        ).fetchone()[0]


        recorded_today = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?
            """,
            (today,)
        ).fetchone()[0]


        present = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?

            AND status = 'Present'
            """,
            (today,)
        ).fetchone()[0]


        absent = connection.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE date = ?

            AND status = 'Absent'
            """,
            (today,)
        ).fetchone()[0]


    connection.close()


    return jsonify(
        {
            "total_students":
                total_students,

            "recorded_today":
                recorded_today,

            "present":
                present,

            "absent":
                absent,

            "date":
                today,

            "class_name":
                selected_class
        }
    )


# ==========================================================
# CLASS-WISE SUMMARY API
# ==========================================================

@app.route("/api/class-wise-summary")
def class_wise_summary():

    if not teacher_or_admin_required():

        return jsonify(
            {
                "error": "Unauthorized"
            }
        ), 401


    connection = get_db_connection()


    today = datetime.now().strftime(
        "%d-%m-%Y"
    )


    rows = connection.execute(
        """
        SELECT

            s.class_name,

            COUNT(
                DISTINCT s.admission_no
            ) AS total_students,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Present'
                    THEN a.admission_no
                END
            ) AS present,

            COUNT(
                DISTINCT CASE
                    WHEN a.status = 'Absent'
                    THEN a.admission_no
                END
            ) AS absent,

            COUNT(
                DISTINCT a.admission_no
            ) AS recorded

        FROM students s

        LEFT JOIN attendance a

        ON s.admission_no = a.admission_no

        AND a.date = ?

        GROUP BY s.class_name

        ORDER BY s.class_name
        """,
        (today,)
    ).fetchall()


    connection.close()


    data = []


    for row in rows:

        total = row["total_students"] or 0

        present = row["present"] or 0


        percentage = (

            round(
                (present / total) * 100,
                2
            )

            if total > 0

            else 0
        )


        data.append(
            {
                "class_name":
                    row["class_name"],

                "total_students":
                    total,

                "recorded":
                    row["recorded"] or 0,

                "present":
                    present,

                "absent":
                    row["absent"] or 0,

                "percentage":
                    percentage
            }
        )


    return jsonify(data)


# ==========================================================
# MONTHLY CLASS ATTENDANCE
# ==========================================================

@app.route("/api/monthly-class-attendance")
def monthly_class_attendance():

    if not teacher_or_admin_required():

        return jsonify(
            {
                "error": "Unauthorized"
            }
        ), 401


    connection = get_db_connection()


    current_month = datetime.now().strftime(
        "%m-%Y"
    )


    classes = connection.execute(
        """
        SELECT DISTINCT class_name
        FROM students
        ORDER BY class_name
        """
    ).fetchall()


    labels = []

    percentages = []


    for row in classes:

        class_name = row["class_name"]


        result = connection.execute(
            """
            SELECT

                COUNT(a.id)
                AS total_records,

                SUM(
                    CASE
                        WHEN a.status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                )
                AS present_records

            FROM attendance a

            INNER JOIN students s

            ON a.admission_no = s.admission_no

            WHERE s.class_name = ?

            AND substr(a.date, 4, 7) = ?
            """,
            (
                class_name,
                current_month
            )
        ).fetchone()


        total_records = (
            result["total_records"] or 0
        )

        present_records = (
            result["present_records"] or 0
        )


        percentage = (

            round(
                (
                    present_records
                    / total_records
                ) * 100,
                2
            )

            if total_records > 0

            else 0
        )


        labels.append(class_name)

        percentages.append(percentage)


    connection.close()


    return jsonify(
        {
            "labels":
                labels,

            "data":
                percentages,

            "period":
                current_month
        }
    )


# ==========================================================
# YEARLY CLASS ATTENDANCE
# ==========================================================

@app.route("/api/yearly-class-attendance")
def yearly_class_attendance():

    if not teacher_or_admin_required():

        return jsonify(
            {
                "error": "Unauthorized"
            }
        ), 401


    connection = get_db_connection()


    current_year = datetime.now().strftime(
        "%Y"
    )


    classes = connection.execute(
        """
        SELECT DISTINCT class_name
        FROM students
        ORDER BY class_name
        """
    ).fetchall()


    labels = []

    percentages = []


    for row in classes:

        class_name = row["class_name"]


        result = connection.execute(
            """
            SELECT

                COUNT(a.id)
                AS total_records,

                SUM(
                    CASE
                        WHEN a.status = 'Present'
                        THEN 1
                        ELSE 0
                    END
                )
                AS present_records

            FROM attendance a

            INNER JOIN students s

            ON a.admission_no = s.admission_no

            WHERE s.class_name = ?

            AND substr(a.date, 7, 4) = ?
            """,
            (
                class_name,
                current_year
            )
        ).fetchone()


        total_records = (
            result["total_records"] or 0
        )

        present_records = (
            result["present_records"] or 0
        )


        percentage = (

            round(
                (
                    present_records
                    / total_records
                ) * 100,
                2
            )

            if total_records > 0

            else 0
        )


        labels.append(class_name)

        percentages.append(percentage)


    connection.close()


    return jsonify(
        {
            "labels":
                labels,

            "data":
                percentages,

            "period":
                current_year
        }
    )



# ==========================================================
# ACCOUNT REGISTRATION
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "").strip().lower()

        if role not in ["teacher", "admin"]:
            flash("Please select Teacher or Admin.", "error")
            return redirect(url_for("register"))

        if not username or not email or len(password) < 6:
            flash("Username, email and a password of at least 6 characters are required.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        connection = get_db_connection()
        try:
            connection.execute(
                """
                INSERT INTO users (username, password, role, email)
                VALUES (?, ?, ?, ?)
                """,
                (username, generate_password_hash(password), role, email)
            )
            connection.commit()
            flash("Account created successfully. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "error")
            return redirect(url_for("register"))
        finally:
            connection.close()

    return render_template("register.html")


# ==========================================================
# FORGOT / RESET PASSWORD
# ==========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        connection = get_db_connection()
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        # Students can use admission number or their saved email.
        student = None if user else connection.execute(
            "SELECT * FROM students WHERE admission_no = ? OR lower(email) = ?",
            (username, username)
        ).fetchone()

        email = user["email"] if user else (student["email"] if student else None)

        if not email:
            connection.close()
            flash("No account with a registered email was found.", "error")
            return redirect(url_for("forgot_password"))

        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(minutes=30)).isoformat()
        user_type = "user" if user else "student"
        account_key = str(user["id"]) if user else student["admission_no"]

        connection.execute("DELETE FROM password_resets WHERE account_key = ?", (account_key,))
        connection.execute(
            """
            INSERT INTO password_resets (user_type, account_key, token, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_type, account_key, token, expires)
        )
        connection.commit()
        connection.close()

        reset_url = build_reset_url(token)
        try:
            sent = send_password_reset_email(email, reset_url)
        except Exception:
            sent = False

        if sent:
            flash("A password reset link has been sent to your registered email.", "success")
        else:
            # Useful for local/demo installations until SMTP is configured.
            flash(
                "SMTP is not configured. For local testing use this reset link: "
                + reset_url,
                "error"
            )
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    connection = get_db_connection()
    reset = connection.execute(
        "SELECT * FROM password_resets WHERE token = ?", (token,)
    ).fetchone()

    if not reset or datetime.fromisoformat(reset["expires_at"]) < datetime.now():
        connection.close()
        flash("This password reset link is invalid or expired.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            connection.close()
            return redirect(url_for("reset_password", token=token))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            connection.close()
            return redirect(url_for("reset_password", token=token))

        if reset["user_type"] == "user":
            connection.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (generate_password_hash(password), reset["account_key"])
            )
        else:
            connection.execute(
                "UPDATE students SET password = ? WHERE admission_no = ?",
                (generate_password_hash(password), reset["account_key"])
            )

        connection.execute("DELETE FROM password_resets WHERE token = ?", (token,))
        connection.commit()
        connection.close()
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("login"))

    connection.close()
    return render_template("reset_password.html")


# ==========================================================
# MARKS / EXAM RESULTS
# ==========================================================

EXAM_TYPES = ["Quarterly", "Half Yearly", "Annual"]


@app.route("/marks", methods=["GET", "POST"])
def marks():

    if not teacher_or_admin_required():
        return redirect(url_for("login"))

    connection = get_db_connection()

    if request.method == "POST":
        admission_no = request.form.get("admission_no", "").strip()
        exam_type = request.form.get("exam_type", "").strip()
        subject = request.form.get("subject", "").strip()
        marks_value = request.form.get("marks", "").strip()
        max_marks = request.form.get("max_marks", "100").strip()

        if exam_type not in EXAM_TYPES or not admission_no or not subject:
            flash("Student, exam type and subject are required.", "error")
        else:
            try:
                mark_value = float(marks_value)
                max_value = float(max_marks)
                if max_value <= 0 or mark_value < 0 or mark_value > max_value:
                    raise ValueError

                connection.execute(
                    """
                    INSERT INTO marks
                    (admission_no, exam_type, subject, marks, max_marks, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(admission_no, exam_type, subject)
                    DO UPDATE SET marks=excluded.marks,
                                  max_marks=excluded.max_marks,
                                  created_at=excluded.created_at
                    """,
                    (
                        admission_no, exam_type, subject,
                        mark_value, max_value, datetime.now().isoformat()
                    )
                )
                connection.commit()
                flash("Marks saved successfully.", "success")
            except ValueError:
                flash("Enter valid marks between 0 and the maximum marks.", "error")

        connection.close()
        return redirect(url_for("marks"))

    students = connection.execute(
        "SELECT admission_no, name, class_name FROM students ORDER BY class_name, admission_no"
    ).fetchall()
    records = connection.execute(
        """
        SELECT m.*, s.name, s.class_name
        FROM marks m
        JOIN students s ON s.admission_no = m.admission_no
        ORDER BY m.id DESC
        """
    ).fetchall()
    connection.close()

    return render_template(
        "marks.html",
        students=students,
        records=records,
        exam_types=EXAM_TYPES
    )


@app.route("/results")
def results():

    if student_required():
        admission_no = session.get("admission_no")
    elif teacher_or_admin_required():
        admission_no = request.args.get("admission_no", "").strip()
    else:
        return redirect(url_for("login"))

    connection = get_db_connection()
    student = connection.execute(
        "SELECT admission_no, name, class_name FROM students WHERE admission_no = ?",
        (admission_no,)
    ).fetchone()

    if not student:
        connection.close()
        flash("Student record not found.", "error")
        return redirect(url_for("home"))

    rows = connection.execute(
        """
        SELECT * FROM marks
        WHERE admission_no = ?
        ORDER BY
            CASE exam_type
                WHEN 'Quarterly' THEN 1
                WHEN 'Half Yearly' THEN 2
                WHEN 'Annual' THEN 3
                ELSE 4
            END,
            subject
        """,
        (admission_no,)
    ).fetchall()
    connection.close()

    grouped = {exam: [] for exam in EXAM_TYPES}
    for row in rows:
        grouped.setdefault(row["exam_type"], []).append(row)

    summaries = {}
    for exam, items in grouped.items():
        total = sum(float(x["marks"]) for x in items)
        maximum = sum(float(x["max_marks"]) for x in items)
        percentage = round((total / maximum) * 100, 2) if maximum else 0
        summaries[exam] = {
            "total": total,
            "maximum": maximum,
            "percentage": percentage
        }

    return render_template(
        "results.html",
        student=student,
        grouped=grouped,
        summaries=summaries,
        exam_types=EXAM_TYPES
    )


# ==========================================================
# PORTION / BLUEPRINT PDF DOCUMENTS
# ==========================================================

ALLOWED_PDF_EXTENSIONS = {".pdf"}


@app.route("/documents", methods=["GET", "POST"])
def documents():

    if not login_required():
        return redirect(url_for("login"))

    upload_root = BASE_FOLDER / "static" / "uploads"
    (upload_root / "portion").mkdir(parents=True, exist_ok=True)
    (upload_root / "blueprint").mkdir(parents=True, exist_ok=True)

    connection = get_db_connection()

    if request.method == "POST":
        if not teacher_or_admin_required():
            connection.close()
            flash("Only teachers and admins can upload documents.", "error")
            return redirect(url_for("documents"))

        category = request.form.get("category", "").strip().lower()
        title = request.form.get("title", "").strip()
        file = request.files.get("file")

        if category not in ["portion", "blueprint"] or not title or not file:
            connection.close()
            flash("Title, category and PDF file are required.", "error")
            return redirect(url_for("documents"))

        original_name = secure_filename(file.filename or "")
        if Path(original_name).suffix.lower() not in ALLOWED_PDF_EXTENSIONS:
            connection.close()
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("documents"))

        stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{original_name}"
        destination = upload_root / category / stored_name
        file.save(destination)

        connection.execute(
            """
            INSERT INTO documents (title, category, filename, uploaded_at, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title, category, stored_name,
                datetime.now().isoformat(),
                session.get("username", "")
            )
        )
        connection.commit()
        connection.close()

        flash(f"{category.title()} PDF uploaded successfully.", "success")
        return redirect(url_for("documents"))

    records = connection.execute(
        "SELECT * FROM documents ORDER BY id DESC"
    ).fetchall()
    connection.close()

    return render_template("documents.html", documents=records)


@app.route("/documents/<int:document_id>")
def download_document(document_id):

    if not login_required():
        return redirect(url_for("login"))

    connection = get_db_connection()
    document = connection.execute(
        "SELECT * FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    connection.close()

    if not document:
        flash("Document not found.", "error")
        return redirect(url_for("documents"))

    from flask import send_from_directory
    return send_from_directory(
        BASE_FOLDER / "static" / "uploads" / document["category"],
        document["filename"],
        as_attachment=False
    )




# ==========================================================
# 7777 ADD-ON FEATURES
# The original attendance system above is intentionally kept.
# These additions extend it without replacing its core routes.
# ==========================================================
import re
import uuid
from flask import g, send_from_directory, has_request_context

_CORE_GET_DB_CONNECTION = get_db_connection
MASTER_DATABASE_FILE = BASE_FOLDER / "schools_master.db"
SCHOOL_DATA_FOLDER = BASE_FOLDER / "school_data"
SCHOOL_DATA_FOLDER.mkdir(parents=True, exist_ok=True)


def _master_connection():
    c = sqlite3.connect(MASTER_DATABASE_FILE)
    c.row_factory = sqlite3.Row
    return c


def _slugify_school(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "school"


def _school_db_path(slug):
    if slug == "our-school":
        return DATABASE_FILE
    return SCHOOL_DATA_FOLDER / f"{slug}.db"


def _setup_master_database():
    c = _master_connection()
    c.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            db_file TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS boss_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    if not c.execute("SELECT 1 FROM boss_admin LIMIT 1").fetchone():
        c.execute(
            "INSERT INTO boss_admin(username,password) VALUES(?,?)",
            ("bossadmin", generate_password_hash("Boss@123"))
        )
    if not c.execute("SELECT 1 FROM schools LIMIT 1").fetchone():
        c.execute(
            "INSERT INTO schools(name,slug,db_file,created_at) VALUES(?,?,?,?)",
            ("Our School", "our-school", str(DATABASE_FILE), datetime.now().isoformat())
        )
    c.commit()
    c.close()


def _initialize_school_database(path):
    global DATABASE_FILE
    old_path = DATABASE_FILE
    try:
        DATABASE_FILE = Path(path)
        _CORE_GET_DB_CONNECTION()
        # A newly created school gets the same schema/features, but no
        # students, teachers, or starter admin data from the original school.
        setup_database(seed_default_data=False)
        setup_extra_database()
    finally:
        DATABASE_FILE = old_path
    _ensure_feature_schema_for_path(Path(path))


def _ensure_feature_schema_for_path(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row

    migrations = {
        "users": {
            "full_name": "TEXT DEFAULT ''",
            "subject": "TEXT DEFAULT ''",
            "class_teacher": "TEXT DEFAULT ''",
            "photo": "TEXT DEFAULT ''",
            "email": "TEXT DEFAULT ''",
        },
        "students": {
            "login_username": "TEXT DEFAULT ''",
            "photo": "TEXT DEFAULT ''",
        },
    }
    for table, cols in migrations.items():
        existing = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, typ in cols.items():
            if name not in existing:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")

    tables = {
        "subjects": """
            CREATE TABLE IF NOT EXISTS subjects(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """,
        "assignments": """
            CREATE TABLE IF NOT EXISTS assignments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                subject TEXT,
                class_name TEXT,
                due_date TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """,
        "assignment_submissions": """
            CREATE TABLE IF NOT EXISTS assignment_submissions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                admission_no TEXT NOT NULL,
                filename TEXT,
                original_filename TEXT,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                UNIQUE(assignment_id, admission_no)
            )
        """,
        "complaints": """
            CREATE TABLE IF NOT EXISTS complaints(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT NOT NULL,
                recipient_type TEXT NOT NULL,
                recipient_username TEXT,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                action_taken TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
        "calendar_events": """
            CREATE TABLE IF NOT EXISTS calendar_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """,
        "announcements": """
            CREATE TABLE IF NOT EXISTS announcements(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                target TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """,
        "timetables": """
            CREATE TABLE IF NOT EXISTS timetables(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                day_name TEXT NOT NULL,
                period_no INTEGER NOT NULL,
                subject TEXT NOT NULL,
                teacher TEXT DEFAULT '',
                start_time TEXT DEFAULT '',
                end_time TEXT DEFAULT ''
            )
        """,
        "exam_timetables": """
            CREATE TABLE IF NOT EXISTS exam_timetables(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                subject TEXT NOT NULL,
                start_time TEXT DEFAULT '',
                end_time TEXT DEFAULT ''
            )
        """,
        "subject_marks": """
            CREATE TABLE IF NOT EXISTS subject_marks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT NOT NULL,
                exam_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                written_marks REAL NOT NULL DEFAULT 0,
                written_max REAL NOT NULL DEFAULT 75,
                internal_marks REAL NOT NULL DEFAULT 0,
                internal_max REAL NOT NULL DEFAULT 25,
                teacher_username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(admission_no, exam_type, subject)
            )
        """,
        "od_requests": """
            CREATE TABLE IF NOT EXISTS od_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_no TEXT NOT NULL,
                request_date TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                action_by TEXT DEFAULT '',
                action_at TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """,
        "change_requests": """
            CREATE TABLE IF NOT EXISTS change_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_type TEXT NOT NULL,
                requester_key TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                reason TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending',
                action_by TEXT DEFAULT '',
                action_at TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """,
        "profile_photos": """
            CREATE TABLE IF NOT EXISTS profile_photos(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_type TEXT NOT NULL,
                account_key TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
        """,
    }
    for sql in tables.values():
        c.execute(sql)

    defaults = [
        ("Mathematics",), ("Physics",), ("Chemistry",),
        ("English",), ("Computer Science",)
    ]
    for (name,) in defaults:
        c.execute(
            "INSERT OR IGNORE INTO subjects(name,created_at) VALUES(?,?)",
            (name, datetime.now().isoformat())
        )

    # Keep legacy starter teacher metadata only for the original Our School database.
    if Path(path).resolve() == DATABASE_FILE.resolve():
        teacher_defaults = [
            ("teacher1", "Teacher 1", "Mathematics", "Class 11 A"),
            ("teacher2", "Teacher 2", "Physics", "Class 11 B"),
            ("teacher3", "Teacher 3", "Chemistry", "Class 12 C"),
            ("teacher4", "Teacher 4", "English", "Class 12 D"),
            ("teacher5", "Teacher 5", "Computer Science", ""),
        ]
        for username, full_name, subject, class_teacher in teacher_defaults:
            row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            if not row:
                c.execute(
                    """INSERT INTO users(username,password,role,full_name,subject,class_teacher)
                       VALUES(?,?,?,?,?,?)""",
                    (username, generate_password_hash("teacher@123"), "teacher",
                     full_name, subject, class_teacher)
                )
            else:
                c.execute(
                    """UPDATE users SET full_name=COALESCE(NULLIF(full_name,''),?),
                       subject=COALESCE(NULLIF(subject,''),?),
                       class_teacher=COALESCE(NULLIF(class_teacher,''),?)
                       WHERE username=?""",
                    (full_name, subject, class_teacher, username)
                )

    # Students initially use admission number as login username.
    c.execute("UPDATE students SET login_username=admission_no WHERE COALESCE(login_username,'')=''")
    c.commit()
    c.close()


_setup_master_database()


# ----------------------------------------------------------
# Multi-school database routing.
# Existing core routes continue to call get_db_connection().
# Outside a request they still use the original database.
# ----------------------------------------------------------
def get_db_connection():
    if not has_request_context():
        return _CORE_GET_DB_CONNECTION()

    slug = session.get("school_id")
    if not slug:
        return _CORE_GET_DB_CONNECTION()

    master = _master_connection()
    school = master.execute(
        "SELECT * FROM schools WHERE slug=? AND active=1", (slug,)
    ).fetchone()
    master.close()
    if not school:
        return _CORE_GET_DB_CONNECTION()

    path = Path(school["db_file"])
    if not path.is_absolute():
        path = BASE_FOLDER / path
    # A school database path may have been created on another computer.
    # If that old absolute path no longer exists, use this project's
    # standard school database location without touching the database data.
    if not path.exists():
        path = _school_db_path(slug)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def _current_school_name():
    slug = session.get("school_id", "our-school")
    c = _master_connection()
    row = c.execute("SELECT name FROM schools WHERE slug=?", (slug,)).fetchone()
    c.close()
    return row["name"] if row else "Our School"


def _feature_setup_current_db():
    path = _school_db_path(session.get("school_id", "our-school"))
    if not path.exists():
        _initialize_school_database(path)
    _ensure_feature_schema_for_path(path)


@app.context_processor
def inject_7777_context():
    try:
        c = _master_connection()
        schools = c.execute(
            "SELECT name,slug FROM schools WHERE active=1 ORDER BY id"
        ).fetchall()
        c.close()
    except Exception:
        schools = []
    return {
        "school_list": schools,
        "current_school_name": _current_school_name(),
    }


@app.before_request
def prepare_7777_request():
    # A selected school is available to the original login route before
    # it performs its normal user lookup.
    if request.path == "/login" and request.method == "POST":
        slug = request.form.get("school_slug", "our-school").strip()
        c = _master_connection()
        school = c.execute(
            "SELECT slug FROM schools WHERE slug=? AND active=1", (slug,)
        ).fetchone()
        c.close()
        if school:
            session["school_id"] = slug
            g.login_school_slug = slug

        # Boss Admin is kept outside school databases.
        if request.form.get("account_type") == "boss":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            c = _master_connection()
            boss = c.execute(
                "SELECT * FROM boss_admin WHERE username=?", (username,)
            ).fetchone()
            c.close()
            if boss and check_password_hash(boss["password"], password):
                session.clear()
                session["user_id"] = f"boss:{boss['id']}"
                session["username"] = boss["username"]
                session["role"] = "boss"
                session["school_id"] = "master"
                return redirect(url_for("boss_dashboard"))
            flash("Invalid Boss Admin username or password.", "error")
            return redirect(url_for("login"))

        # Support editable student usernames without touching the original
        # student/admission-number identity.
        username = request.form.get("username", "").strip()
        if username:
            c = get_db_connection()
            row = c.execute(
                "SELECT admission_no FROM students WHERE login_username=?",
                (username,)
            ).fetchone()
            c.close()
            if row:
                form = request.form.copy()
                form["username"] = row["admission_no"]
                request.form = form

    if request.path not in ["/login", "/logout"] and session.get("role") != "boss":
        if session.get("school_id") not in [None, "", "master"]:
            _feature_setup_current_db()


@app.after_request
def restore_7777_school_session(response):
    slug = getattr(g, "login_school_slug", None)
    if slug and session.get("role") in ["student", "teacher", "admin"]:
        session["school_id"] = slug
    return response


# ----------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------
def _teacher_row():
    if session.get("role") != "teacher":
        return None
    c = get_db_connection()
    row = c.execute(
        "SELECT * FROM users WHERE username=?", (session.get("username",""),)
    ).fetchone()
    c.close()
    return row


def _admin_or_teacher():
    return session.get("role") in ["admin", "teacher"]


def _save_upload(file_obj, folder):
    if not file_obj or not file_obj.filename:
        return None, None
    safe = secure_filename(file_obj.filename)
    if not safe:
        return None, None
    target_dir = BASE_FOLDER / "static" / "uploads" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe}"
    file_obj.save(target_dir / stored)
    return stored, safe


def _recipient_teacher_for_student(admission_no):
    c = get_db_connection()
    student = c.execute(
        "SELECT class_name FROM students WHERE admission_no=?", (admission_no,)
    ).fetchone()
    if not student:
        c.close()
        return None
    row = c.execute(
        "SELECT username FROM users WHERE role='teacher' AND class_teacher=? LIMIT 1",
        (student["class_name"],)
    ).fetchone()
    c.close()
    return row["username"] if row else None


# ==========================================================
# FEATURE HUB
# ==========================================================
@app.route("/features")
def features_hub():
    if not login_required():
        return redirect(url_for("login"))
    return render_template("features.html")


# ==========================================================
# STUDENT ATTENDANCE HISTORY
# ==========================================================
@app.route("/attendance-history")
def attendance_history():
    if not student_required():
        return redirect(url_for("login"))
    admission_no = session.get("admission_no")
    c = get_db_connection()
    rows = c.execute(
        "SELECT date,time,status FROM attendance WHERE admission_no=? ORDER BY id DESC",
        (admission_no,)
    ).fetchall()
    c.close()
    return render_template("attendance_history.html", records=rows)


# ==========================================================
# SUBJECT-SPECIFIC + INTERNAL/EXTERNAL MARKS
# ==========================================================
@app.route("/subject-marks", methods=["GET","POST"])
def subject_marks():
    if not _admin_or_teacher():
        return redirect(url_for("login"))

    c = get_db_connection()
    _ensure_targeted_schema(c)
    teacher = _teacher_row()
    allowed_subject = teacher["subject"].strip() if teacher else ""
    allowed_assignments = c.execute("SELECT class_name,subject FROM teacher_assignments WHERE username=? ORDER BY class_name,subject", (session.get("username",""),)).fetchall() if session.get("role") == "teacher" else []

    if request.method == "POST":
        admission_no = request.form.get("admission_no","").strip()
        subject = request.form.get("subject","").strip()
        exam_type = request.form.get("exam_type","Quarterly").strip()
        try:
            written = float(request.form.get("written_marks","0"))
            internal = float(request.form.get("internal_marks","0"))
            wmax = float(request.form.get("written_max","75"))
            imax = float(request.form.get("internal_max","25"))
        except ValueError:
            c.close()
            flash("Enter valid numeric marks.", "error")
            return redirect(url_for("subject_marks"))

        student_row = c.execute("SELECT class_name FROM students WHERE admission_no=?", (admission_no,)).fetchone()
        if session.get("role") == "teacher" and (not student_row or not c.execute("SELECT 1 FROM teacher_assignments WHERE username=? AND class_name=? AND subject=?", (session.get("username",""), student_row["class_name"], subject)).fetchone()):
            c.close()
            flash("You can enter marks only for your assigned subject in the student's class.", "error")
            return redirect(url_for("subject_marks"))

        if not admission_no or not subject or written < 0 or internal < 0 or wmax <= 0 or imax <= 0 or written > wmax or internal > imax:
            c.close()
            flash("Check the student, subject and mark ranges.", "error")
            return redirect(url_for("subject_marks"))

        c.execute("""
            INSERT INTO subject_marks
            (admission_no,exam_type,subject,written_marks,written_max,internal_marks,internal_max,teacher_username,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(admission_no,exam_type,subject)
            DO UPDATE SET written_marks=excluded.written_marks,
                          written_max=excluded.written_max,
                          internal_marks=excluded.internal_marks,
                          internal_max=excluded.internal_max,
                          teacher_username=excluded.teacher_username,
                          created_at=excluded.created_at
        """, (admission_no,exam_type,subject,written,wmax,internal,imax,session.get("username",""),datetime.now().isoformat()))
        c.commit()
        c.close()
        flash("Subject marks saved successfully.", "success")
        return redirect(url_for("subject_marks"))

    if session.get("role") == "teacher":
        students = c.execute("""SELECT DISTINCT s.admission_no,s.name,s.class_name FROM students s JOIN teacher_assignments ta ON ta.class_name=s.class_name WHERE ta.username=? ORDER BY s.class_name,s.admission_no""", (session.get("username",""),)).fetchall()
        subjects = c.execute("SELECT DISTINCT subject AS name FROM teacher_assignments WHERE username=? ORDER BY subject", (session.get("username",""),)).fetchall()
        rows = c.execute("""SELECT sm.*,s.name,s.class_name FROM subject_marks sm JOIN students s ON s.admission_no=sm.admission_no WHERE sm.teacher_username=? ORDER BY sm.id DESC""", (session.get("username",""),)).fetchall()
    else:
        students = c.execute("SELECT admission_no,name,class_name FROM students ORDER BY class_name,admission_no").fetchall()
        subjects = c.execute("SELECT name FROM subjects ORDER BY name").fetchall()
        rows = c.execute("""SELECT sm.*,s.name,s.class_name FROM subject_marks sm JOIN students s ON s.admission_no=sm.admission_no ORDER BY sm.id DESC""").fetchall()
    c.close()
    return render_template("subject_marks.html", students=students, subjects=subjects,
                           records=rows, allowed_subject=allowed_subject,
                           exam_types=EXAM_TYPES)


# Enforce class-teacher attendance scope while leaving the original
# attendance implementation untouched.
@app.before_request
def enforce_class_teacher_attendance_scope():
    # Superseded by enforce_strict_class_teacher_scope below; kept as a no-op
    # so the original route structure is not removed.
    return None


# Enforce the original /marks route for teachers too.
@app.before_request
def enforce_original_marks_subject():
    # Multi-subject validation is handled by enforce_teacher_subject_marks_scope.
    return None



# ==========================================================
# ASSIGNMENTS / PROJECTS
# ==========================================================
@app.route("/assignments", methods=["GET","POST"])
def assignments():
    if not login_required():
        return redirect(url_for("login"))
    c = get_db_connection()

    if request.method == "POST":
        if session.get("role") != "teacher":
            c.close()
            flash("Only teachers can create and assign assignments/projects.", "error")
            return redirect(url_for("assignments"))
        title = request.form.get("title","").strip()
        description = request.form.get("description","").strip()
        subject = request.form.get("subject","").strip()
        class_name = request.form.get("class_name","").strip()
        due_date = request.form.get("due_date","").strip()
        teacher = _teacher_row()
        if not title:
            c.close()
            flash("Assignment title is required.", "error")
            return redirect(url_for("assignments"))
        if teacher and teacher["subject"] and subject != teacher["subject"]:
            c.close()
            flash("You can assign only your own subject.", "error")
            return redirect(url_for("assignments"))
        c.execute("""
            INSERT INTO assignments(title,description,subject,class_name,due_date,created_by,created_at)
            VALUES(?,?,?,?,?,?,?)
        """,(title,description,subject,class_name,due_date,session.get("username",""),datetime.now().isoformat()))
        c.commit()
        c.close()
        flash("Assignment/project assigned successfully.", "success")
        return redirect(url_for("assignments"))

    if session.get("role") == "student":
        admission_no = session.get("admission_no")
        student = c.execute("SELECT class_name FROM students WHERE admission_no=?",(admission_no,)).fetchone()
        class_name = student["class_name"] if student else ""
        rows = c.execute("""
            SELECT a.*,s.status,s.filename,s.original_filename,s.submitted_at
            FROM assignments a
            LEFT JOIN assignment_submissions s
              ON s.assignment_id=a.id AND s.admission_no=?
            WHERE (a.class_name='' OR a.class_name=?)
            ORDER BY a.due_date IS NULL,a.due_date,a.id DESC
        """,(admission_no,class_name)).fetchall()
    else:
        rows = c.execute("SELECT * FROM assignments ORDER BY id DESC").fetchall()
    subjects = c.execute("SELECT name FROM subjects ORDER BY name").fetchall()
    classes = c.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    c.close()
    return render_template("assignments.html", assignments=rows, subjects=subjects,
                           classes=classes)


@app.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
def submit_assignment(assignment_id):
    if not student_required():
        return redirect(url_for("login"))
    file_obj = request.files.get("file")
    stored, original = _save_upload(file_obj, "assignments")
    if not stored:
        flash("Please attach the completed assignment/project file.", "error")
        return redirect(url_for("assignments"))
    c = get_db_connection()
    a = c.execute("SELECT * FROM assignments WHERE id=?",(assignment_id,)).fetchone()
    if not a:
        c.close()
        flash("Assignment not found.", "error")
        return redirect(url_for("assignments"))
    admission_no = session.get("admission_no")
    student = c.execute("SELECT class_name FROM students WHERE admission_no=?",(admission_no,)).fetchone()
    if a["class_name"] and student and a["class_name"] != student["class_name"]:
        c.close()
        flash("This assignment is not assigned to your class.", "error")
        return redirect(url_for("assignments"))
    c.execute("""
        INSERT INTO assignment_submissions(assignment_id,admission_no,filename,original_filename,submitted_at,status)
        VALUES(?,?,?,?,?,'Submitted')
        ON CONFLICT(assignment_id,admission_no)
        DO UPDATE SET filename=excluded.filename,original_filename=excluded.original_filename,
                      submitted_at=excluded.submitted_at,status='Submitted'
    """,(assignment_id,admission_no,stored,original,datetime.now().isoformat()))
    c.commit(); c.close()
    flash("Assignment submitted successfully.", "success")
    return redirect(url_for("assignments"))


# ==========================================================
# COMPLAINTS
# ==========================================================
@app.route("/complaints", methods=["GET","POST"])
def complaints():
    if not login_required():
        return redirect(url_for("login"))
    c = get_db_connection()

    if request.method == "POST" and session.get("role") == "student":
        recipient = request.form.get("recipient_type","").strip().lower()
        subject = request.form.get("subject","").strip()
        message = request.form.get("message","").strip()
        if recipient not in ["teacher","admin"] or not subject or not message:
            c.close()
            flash("Recipient, subject and complaint message are required.", "error")
            return redirect(url_for("complaints"))
        recipient_username = _recipient_teacher_for_student(session.get("admission_no")) if recipient=="teacher" else None
        if recipient=="teacher" and not recipient_username:
            c.close()
            flash("No class teacher is assigned to your class yet.", "error")
            return redirect(url_for("complaints"))
        c.execute("""
            INSERT INTO complaints(admission_no,recipient_type,recipient_username,subject,message,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)
        """,(session.get("admission_no"),recipient,recipient_username,subject,message,
             datetime.now().isoformat(),datetime.now().isoformat()))
        c.commit(); c.close()
        flash("Complaint submitted successfully.", "success")
        return redirect(url_for("complaints"))

    role = session.get("role")
    if role == "student":
        rows = c.execute("""
            SELECT c.*,u.full_name AS teacher_name
            FROM complaints c LEFT JOIN users u ON u.username=c.recipient_username
            WHERE c.admission_no=? ORDER BY c.id DESC
        """,(session.get("admission_no"),)).fetchall()
    elif role == "admin":
        rows = c.execute("""
            SELECT c.*,s.name,s.class_name
            FROM complaints c JOIN students s ON s.admission_no=c.admission_no
            ORDER BY c.id DESC
        """).fetchall()
    elif role == "teacher":
        rows = c.execute("""
            SELECT c.*,s.name,s.class_name
            FROM complaints c JOIN students s ON s.admission_no=c.admission_no
            WHERE c.recipient_type='teacher' AND c.recipient_username=?
            ORDER BY c.id DESC
        """,(session.get("username"),)).fetchall()
    else:
        rows=[]
    c.close()
    return render_template("complaints.html", complaints=rows)


@app.route("/complaints/<int:complaint_id>/update", methods=["POST"])
def update_complaint(complaint_id):
    if session.get("role") not in ["admin","teacher"]:
        return redirect(url_for("login"))
    status = request.form.get("status","Pending").strip()
    action = request.form.get("action_taken","").strip()
    if status not in ["Pending","Action Taken","Resolved"]:
        status="Pending"
    c=get_db_connection()
    row=c.execute("SELECT * FROM complaints WHERE id=?",(complaint_id,)).fetchone()
    if not row:
        c.close(); flash("Complaint not found.","error"); return redirect(url_for("complaints"))
    if session.get("role")=="teacher" and row["recipient_username"]!=session.get("username"):
        c.close(); flash("You can update only complaints sent to you.","error"); return redirect(url_for("complaints"))
    c.execute("UPDATE complaints SET status=?,action_taken=?,updated_at=? WHERE id=?",
              (status,action,datetime.now().isoformat(),complaint_id))
    c.commit(); c.close()
    flash("Complaint status updated.","success")
    return redirect(url_for("complaints"))


# ==========================================================
# CALENDAR
# ==========================================================
@app.route("/calendar", methods=["GET","POST"])
def calendar():
    if not login_required():
        return redirect(url_for("login"))
    c=get_db_connection()
    if request.method=="POST":
        if session.get("role")!="admin":
            c.close(); flash("Only admin can manage calendar events.","error"); return redirect(url_for("calendar"))
        title=request.form.get("title","").strip()
        event_date=request.form.get("event_date","").strip()
        category=request.form.get("category","").strip()
        description=request.form.get("description","").strip()
        if not title or not event_date or category not in ["Event","Festival","Holiday"]:
            c.close(); flash("Enter title, date and valid category.","error"); return redirect(url_for("calendar"))
        c.execute("""INSERT INTO calendar_events(title,event_date,category,description,created_by,created_at)
                     VALUES(?,?,?,?,?,?)""",(title,event_date,category,description,session.get("username",""),datetime.now().isoformat()))
        c.commit(); c.close(); flash("Calendar event added.","success"); return redirect(url_for("calendar"))
    rows=c.execute("SELECT * FROM calendar_events ORDER BY event_date,id").fetchall()
    c.close()
    return render_template("calendar.html", events=rows)


# ==========================================================
# ANNOUNCEMENTS
# ==========================================================
@app.route("/announcements", methods=["GET","POST"])
def announcements():
    if not login_required():
        return redirect(url_for("login"))
    c=get_db_connection()
    if request.method=="POST":
        if session.get("role")!="admin":
            c.close(); flash("Only admin can create announcements.","error"); return redirect(url_for("announcements"))
        title=request.form.get("title","").strip()
        message=request.form.get("message","").strip()
        target=request.form.get("target","").strip()
        if not title or not message or target not in ["students","teachers","both"]:
            c.close(); flash("Enter title, message and target.","error"); return redirect(url_for("announcements"))
        c.execute("""INSERT INTO announcements(title,message,target,created_by,created_at)
                     VALUES(?,?,?,?,?)""",(title,message,target,session.get("username",""),datetime.now().isoformat()))
        c.commit(); c.close(); flash("Announcement published.","success"); return redirect(url_for("announcements"))
    role=session.get("role")
    target="students" if role=="student" else "teachers" if role=="teacher" else "both"
    rows=c.execute("""SELECT * FROM announcements
                      WHERE target=? OR target='both' ORDER BY id DESC""",(target,)).fetchall()
    c.close()
    return render_template("announcements.html", announcements=rows)


# ==========================================================
# TIMETABLES
# ==========================================================
@app.route("/timetable", methods=["GET","POST"])
def timetable():
    if not login_required():
        return redirect(url_for("login"))
    c=get_db_connection()
    if request.method=="POST":
        if session.get("role")!="admin":
            c.close(); flash("Only admin can manage timetables.","error"); return redirect(url_for("timetable"))
        kind=request.form.get("kind","class")
        if kind=="exam":
            c.execute("""INSERT INTO exam_timetables(exam_name,exam_date,subject,start_time,end_time)
                         VALUES(?,?,?,?,?)""",(request.form.get("exam_name","").strip(),
                         request.form.get("exam_date","").strip(),request.form.get("subject","").strip(),
                         request.form.get("start_time",""),request.form.get("end_time","")))
        else:
            c.execute("""INSERT INTO timetables(class_name,day_name,period_no,subject,teacher,start_time,end_time)
                         VALUES(?,?,?,?,?,?,?)""",(request.form.get("class_name","").strip(),
                         request.form.get("day_name","").strip(),int(request.form.get("period_no","1")),
                         request.form.get("subject","").strip(),request.form.get("teacher","").strip(),
                         request.form.get("start_time",""),request.form.get("end_time","")))
        c.commit(); c.close(); flash("Timetable saved.","success"); return redirect(url_for("timetable"))
    classes=c.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    class_rows=c.execute("SELECT * FROM timetables ORDER BY class_name,day_name,period_no").fetchall()
    exam_rows=c.execute("SELECT * FROM exam_timetables ORDER BY exam_date,start_time").fetchall()
    teachers=c.execute("SELECT username,full_name,subject FROM users WHERE role='teacher' ORDER BY username").fetchall()
    subjects=c.execute("SELECT name FROM subjects ORDER BY name").fetchall()
    c.close()
    return render_template("timetable.html", class_rows=class_rows, exam_rows=exam_rows,
                           classes=classes, teachers=teachers, subjects=subjects)


# ==========================================================
# OD REQUESTS / ADMIN OD ATTENDANCE RECORD
# ==========================================================
def _od_attendance_date(request_date):
    """Convert the OD form date (YYYY-MM-DD) to the attendance date format."""
    try:
        return datetime.strptime(request_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except (TypeError, ValueError):
        return None


@app.route("/od", methods=["GET", "POST"])
def od():
    if not login_required():
        return redirect(url_for("login"))

    c = get_db_connection()

    # Students can only submit their own OD request.
    if request.method == "POST" and session.get("role") == "student":
        request_date = request.form.get("request_date", "").strip()
        reason = request.form.get("reason", "").strip()
        attendance_date = _od_attendance_date(request_date)

        if not request_date or not reason or not attendance_date:
            c.close()
            flash("Please enter a valid OD date and reason.", "error")
            return redirect(url_for("od"))

        # Do not create another active request for the same student/date.
        existing = c.execute(
            """SELECT status FROM od_requests
               WHERE admission_no=? AND request_date=?
                 AND status IN ('Pending','Accepted')
               LIMIT 1""",
            (session.get("admission_no"), request_date)
        ).fetchone()
        if existing:
            c.close()
            flash("An OD request already exists for this date.", "error")
            return redirect(url_for("od"))

        c.execute(
            """INSERT INTO od_requests(admission_no,request_date,reason,status,created_at)
               VALUES(?,?,?,?,?)""",
            (session.get("admission_no"), request_date, reason, "Pending", datetime.now().isoformat())
        )
        c.commit()
        c.close()
        flash("OD request submitted. Status: Pending.", "success")
        return redirect(url_for("od"))

    if session.get("role") == "student":
        rows = c.execute(
            """SELECT o.*, s.name, s.class_name
               FROM od_requests o
               LEFT JOIN students s ON s.admission_no=o.admission_no
               WHERE o.admission_no=? ORDER BY o.id DESC""",
            (session.get("admission_no"),)
        ).fetchall()
    elif session.get("role") == "admin":
        rows = c.execute(
            """SELECT o.*, s.name, s.class_name
               FROM od_requests o
               LEFT JOIN students s ON s.admission_no=o.admission_no
               ORDER BY o.request_date DESC, o.id DESC"""
        ).fetchall()
    else:
        c.close()
        return redirect(url_for("login"))

    c.close()
    return render_template("od.html", requests=rows)


@app.route("/od-records")
def od_records():
    """Admin-only complete OD request/attendance record."""
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    c = get_db_connection()
    rows = c.execute(
        """SELECT o.id, o.admission_no, s.name, s.class_name,
                  o.request_date, o.reason, o.status, o.action_by,
                  o.action_at, o.created_at,
                  a.date AS attendance_date, a.time AS attendance_time,
                  a.status AS attendance_status
           FROM od_requests o
           LEFT JOIN students s ON s.admission_no=o.admission_no
           LEFT JOIN attendance a
             ON a.admission_no=o.admission_no
            AND a.date=?
           ORDER BY o.request_date DESC, o.id DESC""",
        # Attendance stores dates as DD-MM-YYYY while OD requests use the
        # browser's YYYY-MM-DD value. The join below is therefore replaced
        # in Python after retrieval so existing attendance data is untouched.
        ("__NO_DIRECT_MATCH__",)
    ).fetchall()

    # Re-read attendance by admission number and converted OD date. This
    # keeps the existing attendance table and its date format unchanged.
    attendance_by_key = {}
    attendance_rows = c.execute(
        "SELECT admission_no,date,time,status FROM attendance"
    ).fetchall()
    for a in attendance_rows:
        attendance_by_key[(a["admission_no"], a["date"])] = a

    enriched = []
    for r in rows:
        item = dict(r)
        attendance_date = _od_attendance_date(item.get("request_date"))
        a = attendance_by_key.get((item.get("admission_no"), attendance_date))
        item["attendance_date"] = a["date"] if a else ""
        item["attendance_time"] = a["time"] if a else ""
        item["attendance_status"] = a["status"] if a else "Not marked"
        enriched.append(item)

    c.close()
    return render_template("od_records.html", records=enriched)


@app.route("/od/<int:request_id>/decision", methods=["POST"])
def od_decision(request_id):
    # Only the Admin can accept or deny an OD request.
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    status = request.form.get("status", "").strip()
    if status not in ["Accepted", "Denied"]:
        flash("Choose either Accept or Deny for the OD request.", "error")
        return redirect(url_for("od"))

    c = get_db_connection()
    request_row = c.execute(
        """SELECT o.*, s.name, s.class_name
           FROM od_requests o
           LEFT JOIN students s ON s.admission_no=o.admission_no
           WHERE o.id=?""",
        (request_id,)
    ).fetchone()

    if not request_row:
        c.close()
        flash("OD request not found.", "error")
        return redirect(url_for("od"))

    # Once the Admin has made a decision, it cannot be changed accidentally.
    if request_row["status"] != "Pending":
        c.close()
        flash(f"This OD request is already {request_row['status']}.", "error")
        return redirect(url_for("od"))

    action_at = datetime.now().isoformat()
    c.execute(
        """UPDATE od_requests
           SET status=?, action_by=?, action_at=?
           WHERE id=? AND status='Pending'""",
        (status, session.get("username", ""), action_at, request_id)
    )

    if status == "Accepted":
        attendance_date = _od_attendance_date(request_row["request_date"])
        if not attendance_date:
            c.rollback()
            c.close()
            flash("The OD request contains an invalid date, so attendance was not changed.", "error")
            return redirect(url_for("od"))

        student_name = request_row["name"] or request_row["admission_no"]
        attendance_time = datetime.now().strftime("%I:%M:%S %p")

        # Mark the approved OD date as attendance status OD. If attendance for
        # that date already exists, update that single student's record rather
        # than creating a duplicate (the table has UNIQUE(date, admission_no)).
        c.execute(
            """INSERT INTO attendance(date,time,admission_no,student_name,status)
               VALUES(?,?,?,?,?)
               ON CONFLICT(date, admission_no) DO UPDATE SET
                   time=excluded.time,
                   student_name=excluded.student_name,
                   status='OD'""",
            (attendance_date, attendance_time, request_row["admission_no"], student_name, "OD")
        )

    c.commit()
    c.close()

    if status == "Accepted":
        flash("OD accepted. Attendance has been automatically marked as OD for the requested date.", "success")
    else:
        flash("OD request denied. The student will see the status as Denied.", "success")
    return redirect(url_for("od"))


# ==========================================================
# DETAIL CHANGE REQUESTS
# ==========================================================
@app.route("/change-requests", methods=["GET","POST"])
def change_requests():
    if not login_required():
        return redirect(url_for("login"))
    c=get_db_connection()
    role=session.get("role")
    if request.method=="POST" and role in ["student","teacher"]:
        field=request.form.get("field_name","").strip()
        new_value=request.form.get("new_value","").strip()
        reason=request.form.get("reason","").strip()
        if not field or not new_value:
            c.close(); flash("Field and requested value are required.","error"); return redirect(url_for("change_requests"))
        key=session.get("admission_no") if role=="student" else session.get("username")
        table="students" if role=="student" else "users"
        keycol="admission_no" if role=="student" else "username"
        allowed_student={"name","class_name","roll_no","blood_group","email","phone","address",
                         "mother_phone","father_phone","mother_email","father_email"}
        allowed_user={"full_name","email","subject","class_teacher"}
        if field not in (allowed_student if role=="student" else allowed_user):
            c.close()
            flash("That detail cannot be changed through a request.", "error")
            return redirect(url_for("change_requests"))
        row=c.execute(f"SELECT * FROM {table} WHERE {keycol}=?",(key,)).fetchone()
        old=str(row[field]) if row and field in row.keys() else ""
        c.execute("""INSERT INTO change_requests(requester_type,requester_key,field_name,old_value,new_value,reason,created_at)
                     VALUES(?,?,?,?,?,?,?)""",(role,key,field,old,new_value,reason,datetime.now().isoformat()))
        c.commit(); c.close(); flash("Change request sent to admin.","success"); return redirect(url_for("change_requests"))
    if role=="admin":
        rows=c.execute("SELECT * FROM change_requests ORDER BY id DESC").fetchall()
    else:
        key=session.get("admission_no") if role=="student" else session.get("username")
        rows=c.execute("SELECT * FROM change_requests WHERE requester_key=? ORDER BY id DESC",(key,)).fetchall()
    c.close()
    return render_template("change_requests.html", requests=rows)


@app.route("/change-requests/<int:request_id>/decision", methods=["POST"])
def change_request_decision(request_id):
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    status=request.form.get("status","Denied")
    if status not in ["Accepted","Denied"]:
        status="Denied"
    c=get_db_connection()
    row=c.execute("SELECT * FROM change_requests WHERE id=?",(request_id,)).fetchone()
    if row:
        c.execute("""UPDATE change_requests SET status=?,action_by=?,action_at=? WHERE id=?""",
                  (status,session.get("username",""),datetime.now().isoformat(),request_id))
        # Apply safe profile fields after admin approval.
        if status=="Accepted":
            allowed_student={"name","class_name","roll_no","blood_group","email","phone","address",
                             "mother_phone","father_phone","mother_email","father_email"}
            allowed_user={"full_name","email","subject","class_teacher"}
            allowed=allowed_student if row["requester_type"]=="student" else allowed_user
            if row["field_name"] in allowed:
                table="students" if row["requester_type"]=="student" else "users"
                keycol="admission_no" if row["requester_type"]=="student" else "username"
                c.execute(f"UPDATE {table} SET {row['field_name']}=? WHERE {keycol}=?",
                          (row["new_value"],row["requester_key"]))
        c.commit()
    c.close(); flash(f"Change request {status}.","success"); return redirect(url_for("change_requests"))


# ==========================================================
# PROFILE PHOTO + ACCOUNT SETTINGS
# ==========================================================
@app.route("/profile", methods=["GET","POST"])
def profile():
    if not login_required():
        return redirect(url_for("login"))
    c=get_db_connection()
    role=session.get("role")
    if request.method=="POST":
        file_obj=request.files.get("photo")
        stored,_=_save_upload(file_obj,"profiles")
        if stored:
            key=session.get("admission_no") if role=="student" else session.get("username")
            if role=="student":
                c.execute("UPDATE students SET photo=? WHERE admission_no=?",(stored,key))
            else:
                c.execute("UPDATE users SET photo=? WHERE username=?",(stored,key))
            c.execute("""INSERT INTO profile_photos(account_type,account_key,filename,uploaded_at)
                         VALUES(?,?,?,?)
                         ON CONFLICT(account_key) DO UPDATE SET
                         account_type=excluded.account_type,filename=excluded.filename,
                         uploaded_at=excluded.uploaded_at""",
                      (role,key,stored,datetime.now().isoformat()))
            c.commit()
            flash("Profile photo updated.","success")
        else:
            flash("Please choose an image file.","error")
        c.close(); return redirect(url_for("profile"))
    key=session.get("admission_no") if role=="student" else session.get("username")
    table="students" if role=="student" else "users"
    keycol="admission_no" if role=="student" else "username"
    row=c.execute(f"SELECT * FROM {table} WHERE {keycol}=?",(key,)).fetchone()
    c.close()
    return render_template("profile.html", profile=row, role=role)


@app.route("/account-settings", methods=["GET","POST"])
def account_settings():
    """Allow the currently logged-in account to change only its own
    username and/or password. No approval request is required for this.
    Works for students, teachers, school admins, and Boss Admin.
    """
    if not login_required():
        return redirect(url_for("login"))

    role = session.get("role")

    # Boss Admin lives in the master database, not a school database.
    if role == "boss":
        c = _master_connection()
        key = session.get("username", "")
        if request.method == "POST":
            new_username = request.form.get("username", "").strip()
            new_password = request.form.get("password", "")

            if not new_username:
                c.close()
                flash("Username cannot be empty.", "error")
                return redirect(url_for("account_settings"))

            if new_username != key:
                exists = c.execute(
                    "SELECT id FROM boss_admin WHERE username=? AND username<>?",
                    (new_username, key)
                ).fetchone()
                if exists:
                    c.close()
                    flash("Username already exists.", "error")
                    return redirect(url_for("account_settings"))
                c.execute(
                    "UPDATE boss_admin SET username=? WHERE username=?",
                    (new_username, key)
                )
                session["username"] = new_username
                key = new_username

            if new_password:
                c.execute(
                    "UPDATE boss_admin SET password=? WHERE username=?",
                    (generate_password_hash(new_password), key)
                )

            c.commit()
            c.close()
            flash("Your username/password has been updated.", "success")
            return redirect(url_for("account_settings"))

        c.close()
        return render_template("account_settings.html", role=role, username=key)

    c = get_db_connection()
    key = session.get("admission_no") if role == "student" else session.get("username")

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "")

        if not new_username:
            c.close()
            flash("Username cannot be empty.", "error")
            return redirect(url_for("account_settings"))

        if role == "student":
            exists = c.execute(
                "SELECT admission_no FROM students WHERE login_username=? AND admission_no<>?",
                (new_username, key)
            ).fetchone()
            if exists:
                c.close()
                flash("Username already exists in this school.", "error")
                return redirect(url_for("account_settings"))

            c.execute(
                "UPDATE students SET login_username=? WHERE admission_no=?",
                (new_username, key)
            )
            session["username"] = new_username

            if new_password:
                c.execute(
                    "UPDATE students SET password=? WHERE admission_no=?",
                    (generate_password_hash(new_password), key)
                )
        else:
            if new_username != key:
                exists = c.execute(
                    "SELECT id FROM users WHERE username=? AND username<>?",
                    (new_username, key)
                ).fetchone()
                if exists:
                    c.close()
                    flash("Username already exists in this school.", "error")
                    return redirect(url_for("account_settings"))

                c.execute(
                    "UPDATE users SET username=? WHERE username=?",
                    (new_username, key)
                )
                session["username"] = new_username
                key = new_username

            if new_password:
                c.execute(
                    "UPDATE users SET password=? WHERE username=?",
                    (generate_password_hash(new_password), key)
                )

        c.commit()
        c.close()
        flash("Your username/password has been updated.", "success")
        return redirect(url_for("account_settings"))

    # Show the current login username, not the student's permanent admission ID.
    if role == "student":
        row = c.execute(
            "SELECT login_username FROM students WHERE admission_no=?",
            (key,)
        ).fetchone()
        display_username = row["login_username"] if row and row["login_username"] else key
    else:
        display_username = key

    c.close()
    return render_template("account_settings.html", role=role, username=display_username)


# ==========================================================
# TEACHERS / SUBJECTS MANAGEMENT
# ==========================================================
@app.route("/teachers")
def teachers():
    if not _admin_or_teacher():
        return redirect(url_for("login"))
    c=get_db_connection()
    if session.get("role")=="admin":
        rows=c.execute("SELECT * FROM users WHERE role='teacher' ORDER BY username").fetchall()
    else:
        rows=c.execute("SELECT * FROM users WHERE username=?",(session.get("username"),)).fetchall()
    c.close()
    return render_template("teachers.html", teachers=rows)


@app.route("/subjects", methods=["GET","POST"])
def subjects():
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    c=get_db_connection()
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if name:
            try:
                c.execute("INSERT INTO subjects(name,created_at) VALUES(?,?)",(name,datetime.now().isoformat()))
                c.commit(); flash("Subject added.","success")
            except sqlite3.IntegrityError:
                flash("Subject already exists.","error")
        return redirect(url_for("subjects"))
    rows=c.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    teachers=c.execute("SELECT username,full_name,subject,class_teacher FROM users WHERE role='teacher' ORDER BY username").fetchall()
    c.close()
    return render_template("subjects.html", subjects=rows, teachers=teachers)


@app.route("/subjects/assign", methods=["POST"])
def assign_subject():
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    username=request.form.get("username","").strip()
    subject=request.form.get("subject","").strip()
    class_teacher=request.form.get("class_teacher","").strip()
    c=get_db_connection()
    c.execute("UPDATE users SET subject=?,class_teacher=? WHERE username=? AND role='teacher'",
              (subject,class_teacher,username))
    c.commit(); c.close(); flash("Teacher assignment updated.","success"); return redirect(url_for("subjects"))


# ==========================================================
# CREATE STUDENT ACCOUNT FOR TEACHER + ADMIN
# ==========================================================
@app.route("/create-student", methods=["GET","POST"])
def create_student():
    if session.get("role") not in ["admin","teacher"]:
        return redirect(url_for("login"))
    c=get_db_connection()
    if request.method=="POST":
        admission=request.form.get("admission_no","").strip()
        name=request.form.get("name","").strip()
        class_name=request.form.get("class_name","").strip()
        if not admission or not name or not class_name:
            c.close(); flash("Admission number, name and class are required.","error"); return redirect(url_for("create_student"))
        if c.execute("SELECT 1 FROM students WHERE admission_no=?",(admission,)).fetchone():
            c.close(); flash("Admission number already exists.","error"); return redirect(url_for("create_student"))
        c.execute("""INSERT INTO students(admission_no,name,class_name,password,login_username)
                     VALUES(?,?,?,?,?)""",(admission,name,class_name,generate_password_hash(admission),admission))
        c.commit(); c.close()
        flash("Student account created. Initial username and password are the admission number.","success")
        return redirect(url_for("create_student"))
    c.close()
    return render_template("create_student.html")


# ==========================================================
# BOSS ADMIN / SCHOOL MANAGEMENT
# ==========================================================
@app.route("/boss")
def boss_dashboard():
    if session.get("role")!="boss":
        return redirect(url_for("login"))
    c=_master_connection()
    rows=c.execute("SELECT * FROM schools ORDER BY id").fetchall()
    selected_slug=request.args.get("school", "").strip()
    selected_school=None
    if selected_slug:
        selected_school=c.execute(
            "SELECT * FROM schools WHERE slug=? AND active=1", (selected_slug,)
        ).fetchone()
    c.close()
    return render_template("boss.html", schools=rows, selected_school=selected_school)


@app.route("/boss/create-school", methods=["POST"])
def boss_create_school():
    if session.get("role")!="boss":
        return redirect(url_for("login"))
    name=request.form.get("name","").strip()
    if not name:
        flash("School name is required.","error")
        return redirect(url_for("boss_dashboard"))
    c=_master_connection()
    if c.execute("SELECT 1 FROM schools WHERE name=?",(name,)).fetchone():
        c.close(); flash("A school with that exact name already exists. Use a different school name.","error"); return redirect(url_for("boss_dashboard"))
    slug=_unique_school_slug(name, c)
    path=_school_db_path(slug)
    # Never reuse another school's database file.
    if Path(path).exists():
        slug=_unique_school_slug(f"{name}-{uuid.uuid4().hex[:6]}", c)
        path=_school_db_path(slug)
    c.execute("""INSERT INTO schools(name,slug,db_file,created_at) VALUES(?,?,?,?)""",
              (name,slug,str(path),datetime.now().isoformat()))
    c.commit(); c.close()
    _initialize_school_database(path)
    _ensure_admin_account(path, name)
    flash(f"{name} created with a separate database. Default Admin ID: admin / Admin@123 (change it after first login).","success")
    # Keep the newly created school selected so Boss Admin creates accounts
    # in this school instead of silently falling back to the previous one.
    return redirect(url_for("boss_dashboard", school=slug))


@app.route("/boss/toggle-school/<int:school_id>", methods=["POST"])
def boss_toggle_school(school_id):
    if session.get("role")!="boss":
        return redirect(url_for("login"))
    c=_master_connection()
    c.execute("UPDATE schools SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=? AND slug<>'our-school'",
              (school_id,))
    c.commit(); c.close(); return redirect(url_for("boss_dashboard"))


@app.route("/boss/switch-school/<slug>")
def boss_switch_school(slug):
    if session.get("role")!="boss":
        return redirect(url_for("login"))
    c=_master_connection()
    row=c.execute("SELECT * FROM schools WHERE slug=? AND active=1",(slug,)).fetchone()
    c.close()
    if not row:
        flash("School not found.","error"); return redirect(url_for("boss_dashboard"))
    path = Path(row["db_file"])
    if not path.is_absolute(): path = BASE_FOLDER / path
    _initialize_school_database(path)
    _ensure_admin_account(path, row["name"])
    session.clear()
    session["school_id"]=slug
    session["role"]="admin"
    session["username"]="admin"
    session["user_id"]="boss-switched"
    return redirect(url_for("dashboard"))


# Initialize all current-school feature tables when the module is loaded.
# This is additive and makes the project safe for both `python app.py`
# and WSGI servers such as Gunicorn.
try:
    setup_database()
    setup_extra_database()
    _ensure_feature_schema_for_path(DATABASE_FILE)
except Exception as _7777_init_error:
    print("7777 feature initialization warning:", _7777_init_error)



# ==========================================================
# BOSS ADMIN — TEACHER / STUDENT ACCOUNT MANAGEMENT
# ==========================================================
# Boss Admin is the central authority. School users cannot use these routes.

@app.route("/boss/create-teacher", methods=["POST"])
def boss_create_teacher():
    if session.get("role") != "boss":
        return redirect(url_for("login"))

    school_slug = request.form.get("school_slug", "").strip()
    username = request.form.get("username", "").strip().lower()
    full_name = request.form.get("full_name", "").strip()
    password = request.form.get("password", "").strip() or "Teacher@123"
    subject = request.form.get("subject", "").strip()
    class_teacher = request.form.get("class_teacher", "").strip()
    email = request.form.get("email", "").strip()

    if not school_slug or not username or not full_name:
        flash("School, teacher username and teacher name are required.", "error")
        return redirect(url_for("boss_dashboard"))

    master = _master_connection()
    school = master.execute(
        "SELECT * FROM schools WHERE slug=? AND active=1", (school_slug,)
    ).fetchone()
    master.close()
    if not school:
        flash("Selected school was not found.", "error")
        return redirect(url_for("boss_dashboard"))

    path = Path(school["db_file"])
    if not path.is_absolute():
        path = BASE_FOLDER / path
    _initialize_school_database(path)

    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        c.execute("""
            INSERT INTO users(username,password,role,full_name,subject,class_teacher,email)
            VALUES(?,?,?,?,?,?,?)
        """, (username, generate_password_hash(password), "teacher", full_name,
              subject, class_teacher, email))
        c.commit()
        flash(f"Teacher account '{username}' created in {school['name']}.", "success")
    except sqlite3.IntegrityError:
        flash("That username already exists in the selected school.", "error")
    finally:
        c.close()
    return redirect(url_for("boss_dashboard"))


@app.route("/boss/create-student", methods=["POST"])
def boss_create_student():
    if session.get("role") != "boss":
        return redirect(url_for("login"))

    school_slug = request.form.get("school_slug", "").strip()
    admission_no = request.form.get("admission_no", "").strip()
    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip() or "Unassigned"
    roll_no = request.form.get("roll_no", "").strip()
    password = request.form.get("password", "").strip() or admission_no
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    if not school_slug or not admission_no or not name:
        flash("School, admission number and student name are required.", "error")
        return redirect(url_for("boss_dashboard"))

    master = _master_connection()
    school = master.execute(
        "SELECT * FROM schools WHERE slug=? AND active=1", (school_slug,)
    ).fetchone()
    master.close()
    if not school:
        flash("Selected school was not found.", "error")
        return redirect(url_for("boss_dashboard"))

    path = Path(school["db_file"])
    if not path.is_absolute():
        path = BASE_FOLDER / path
    _initialize_school_database(path)

    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        # Admission number is the protected student identity and must be unique.
        if c.execute("SELECT 1 FROM students WHERE admission_no=?", (admission_no,)).fetchone():
            flash("That admission number already exists in the selected school.", "error")
            return redirect(url_for("boss_dashboard"))
        # Editable username is also unique inside this school.
        if c.execute("SELECT 1 FROM students WHERE login_username=?", (admission_no,)).fetchone():
            flash("That student username already exists in the selected school.", "error")
            return redirect(url_for("boss_dashboard"))
        c.execute("""
            INSERT INTO students(admission_no,name,class_name,password,roll_no,email,phone,login_username)
            VALUES(?,?,?,?,?,?,?,?)
        """, (admission_no, name, class_name, generate_password_hash(password),
              roll_no, email, phone, admission_no))
        c.commit()
        flash(f"Student ID '{admission_no}' created in {school['name']}.", "success")
    finally:
        c.close()
    return redirect(url_for("boss_dashboard"))


@app.before_request
def boss_controls_registration_and_school_creation():
    # Account creation is controlled by Boss Admin. Existing core pages remain available.
    if request.path == "/register" and session.get("role") != "boss":
        flash("Teacher/Admin account creation is controlled by Boss Admin.", "error")
        return redirect(url_for("login"))


# ==========================================================
# TARGETED BUG FIXES + ADDITIVE TEACHER/SUBSTITUTION FEATURES
# The existing core routes remain intact; these hooks only add
# permissions, account tools, and timetable workflows.
# ==========================================================

def _selected_school_record(slug=None, active_only=True):
    slug = (slug or session.get("school_id") or "").strip()
    if not slug or slug == "master":
        return None
    c = _master_connection()
    sql = "SELECT * FROM schools WHERE slug=?"
    if active_only:
        sql += " AND active=1"
    row = c.execute(sql, (slug,)).fetchone()
    c.close()
    return row


def _school_connection_by_slug(slug):
    row = _selected_school_record(slug)
    if not row:
        return None
    path = Path(row["db_file"])
    if not path.is_absolute():
        path = BASE_FOLDER / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _initialize_school_database(path)
    _ensure_feature_schema_for_path(path)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def _class_teacher_name():
    if session.get("role") != "teacher":
        return ""
    c = get_db_connection()
    row = c.execute("SELECT class_teacher FROM users WHERE username=?", (session.get("username", ""),)).fetchone()
    c.close()
    return (row["class_teacher"] or "").strip() if row else ""


def _teacher_assignments(username=None):
    username = username or session.get("username", "")
    c = get_db_connection()
    rows = c.execute("""
        SELECT class_name, subject, is_class_teacher
        FROM teacher_assignments
        WHERE username=?
        ORDER BY class_name, subject
    """, (username,)).fetchall()
    c.close()
    return rows


def _teacher_has_subject_class(subject, class_name, username=None):
    username = username or session.get("username", "")
    c = get_db_connection()
    row = c.execute("""
        SELECT 1 FROM teacher_assignments
        WHERE username=? AND class_name=? AND subject=?
    """, (username, class_name, subject)).fetchone()
    c.close()
    return bool(row)


def _teacher_is_class_teacher(class_name, username=None):
    username = username or session.get("username", "")
    c = get_db_connection()
    row = c.execute("""
        SELECT 1 FROM teacher_assignments
        WHERE username=? AND class_name=? AND is_class_teacher=1
    """, (username, class_name)).fetchone()
    c.close()
    if row:
        return True
    # Preserve the original single class-teacher field for existing data.
    if username == session.get("username"):
        return _class_teacher_name() == class_name
    return False


def _ensure_admin_account(path, school_name=""):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT NOT NULL)""")
    row = c.execute("SELECT id FROM users WHERE username='admin' AND role='admin'").fetchone()
    if not row:
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                  ("admin", generate_password_hash("Admin@123"), "admin"))
    c.commit(); c.close()


# Re-define only the school path helper so every school gets a collision-proof DB.
# Existing Our School keeps its original database for backward compatibility.
def _school_db_path(slug):
    if slug == "our-school":
        return DATABASE_FILE
    safe = re.sub(r"[^a-z0-9_-]+", "-", slug.lower()).strip("-") or "school"
    return SCHOOL_DATA_FOLDER / f"{safe}.db"


# Fix multi-school creation: unique slug/path even when names normalize to the same slug.
def _unique_school_slug(name, master_conn):
    base = _slugify_school(name)
    slug = base
    n = 2
    while master_conn.execute("SELECT 1 FROM schools WHERE slug=?", (slug,)).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


@app.route("/boss/create-admin", methods=["POST"])
def boss_create_admin_account():
    if session.get("role") != "boss":
        return redirect(url_for("login"))
    school_slug = request.form.get("school_slug", "").strip()
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip() or "Admin@123"
    school = _selected_school_record(school_slug)
    if not school or not username:
        flash("Select a valid school and enter an admin username.", "error")
        return redirect(url_for("boss_dashboard", school=school_slug))
    path = Path(school["db_file"])
    if not path.is_absolute(): path = BASE_FOLDER / path
    _initialize_school_database(path)
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row
    try:
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                  (username, generate_password_hash(password), "admin"))
        c.commit(); flash(f"Admin ID '{username}' created in {school['name']}.", "success")
    except sqlite3.IntegrityError:
        flash("That username already exists in the selected school.", "error")
    finally: c.close()
    return redirect(url_for("boss_dashboard", school=school_slug))


@app.route("/admin/create-teacher", methods=["POST"])
def admin_create_teacher_account():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    username = request.form.get("username", "").strip().lower()
    full_name = request.form.get("full_name", "").strip()
    password = request.form.get("password", "").strip() or "Teacher@123"
    email = request.form.get("email", "").strip()
    if not username or not full_name:
        flash("Teacher username and name are required.", "error")
        return redirect(url_for("teachers"))
    c = get_db_connection()
    try:
        c.execute("INSERT INTO users(username,password,role,full_name,email) VALUES(?,?,?,?,?)",
                  (username, generate_password_hash(password), "teacher", full_name, email))
        c.commit(); flash(f"Teacher ID '{username}' created successfully.", "success")
    except sqlite3.IntegrityError:
        flash("That teacher username already exists in this school.", "error")
    finally: c.close()
    return redirect(url_for("teachers"))


# Login-page self creation for separate Teacher and Student IDs.
@app.route("/login/create-teacher", methods=["GET", "POST"])
def login_create_teacher():
    if request.method == "POST":
        school_slug = request.form.get("school_slug", "").strip()
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        email = request.form.get("email", "").strip()
        if not _selected_school_record(school_slug) or not username or not name or len(password) < 6 or password != confirm:
            flash("Choose a school and enter valid teacher details; password must be at least 6 characters and match confirmation.", "error")
            return redirect(url_for("login_create_teacher"))
        c = _school_connection_by_slug(school_slug)
        try:
            c.execute("INSERT INTO users(username,password,role,full_name,email) VALUES(?,?,?,?,?)",
                      (username, generate_password_hash(password), "teacher", name, email))
            c.commit(); flash("Teacher ID created. You can now log in.", "success")
        except sqlite3.IntegrityError:
            flash("That Teacher username already exists in this school.", "error")
        finally: c.close()
        return redirect(url_for("login"))
    return render_template("login_create_account.html", account_type="Teacher")


@app.route("/login/create-student", methods=["GET", "POST"])
def login_create_student():
    if request.method == "POST":
        school_slug = request.form.get("school_slug", "").strip()
        admission = request.form.get("admission_no", "").strip()
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        class_name = request.form.get("class_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        school = _selected_school_record(school_slug)
        if not school or not admission or not username or not name or not class_name or len(password) < 6 or password != confirm:
            flash("Choose a school and complete all student details; password must be at least 6 characters and match confirmation.", "error")
            return redirect(url_for("login_create_student"))
        c = _school_connection_by_slug(school_slug)
        try:
            if c.execute("SELECT 1 FROM students WHERE admission_no=? OR login_username=?", (admission, username)).fetchone():
                flash("Admission number or Student username already exists in this school.", "error")
                return redirect(url_for("login_create_student"))
            c.execute("INSERT INTO students(admission_no,name,class_name,password,login_username) VALUES(?,?,?,?,?)",
                      (admission, name, class_name, generate_password_hash(password), username))
            c.commit(); flash("Student ID created. You can now log in.", "success")
        finally: c.close()
        return redirect(url_for("login"))
    return render_template("login_create_account.html", account_type="Student")


# Stronger no-cache headers stop old login pages/form data from being reused by the browser.
@app.after_request
def no_cache_login_pages(response):
    if request.path == "/login" or request.path.startswith("/login/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Ensure the login GET always starts from a clean authenticated session.
@app.before_request
def clear_stale_login_session():
    if request.path == "/login" and request.method == "GET" and session.get("role"):
        session.clear()


# Class-teacher-only attendance and class details.
@app.before_request
def enforce_strict_class_teacher_scope():
    if session.get("role") != "teacher":
        return None
    if request.path not in ["/mark-attendance", "/attendance-records", "/dashboard"]:
        return None
    c=get_db_connection(); _ensure_targeted_schema(c)
    assigned_rows=c.execute("SELECT DISTINCT class_name FROM teacher_assignments WHERE username=? AND is_class_teacher=1 ORDER BY class_name", (session.get("username",""),)).fetchall()
    assigned_classes=[r["class_name"] for r in assigned_rows if r["class_name"]]
    c.close()
    if not assigned_classes:
        legacy=_class_teacher_name()
        assigned_classes=[legacy] if legacy else []
    if not assigned_classes:
        flash("Only an assigned class teacher can access class attendance.", "error")
        return redirect(url_for("features_hub"))
    requested=request.args.get("class_name", "").strip()
    if requested and requested not in assigned_classes:
        flash("You can access attendance and class details only for your assigned class.", "error")
        requested=assigned_classes[0]
    if not requested:
        requested=assigned_classes[0]
    # Only redirect when the class was missing or invalid. If the requested
    # class is already valid, let the original route continue normally.
    # This prevents the old redirect loop on Mark Attendance and Records.
    original_requested = request.args.get("class_name", "").strip()
    if request.path == "/attendance-records" and original_requested != requested:
        return redirect(url_for("attendance_records", class_name=requested))
    if request.path == "/mark-attendance" and original_requested != requested:
        return redirect(url_for("mark_attendance", class_name=requested))
    if request.path == "/dashboard" and not request.args.get("class_name"):
        return redirect(url_for("dashboard", class_name=requested))
    if request.args.get("class_name", "").strip() not in assigned_classes:
        if request.path == "/dashboard":
            return redirect(url_for("dashboard", class_name=requested))
        if request.path == "/mark-attendance":
            return redirect(url_for("mark_attendance", class_name=requested))
        return redirect(url_for("attendance_records", class_name=requested))
    return None


# Prevent teachers from using the original Marks screen for students outside their subjects/classes.
@app.before_request
def enforce_teacher_subject_marks_scope():
    if session.get("role") != "teacher" or request.path not in ["/marks", "/subject-marks"]:
        return None
    if request.path == "/marks" and request.method == "GET":
        return redirect(url_for("subject_marks"))
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        admission = request.form.get("admission_no", "").strip()
        c = get_db_connection()
        student = c.execute("SELECT class_name FROM students WHERE admission_no=?", (admission,)).fetchone()
        c.close()
        if not student or not _teacher_has_subject_class(subject, student["class_name"]):
            flash("You can enter marks only for a subject and class assigned to you.", "error")
            return redirect(url_for(request.endpoint))
    return None


# Additive schema for multi-subject teachers, substitutions, exchanges and self-registration.
def _ensure_targeted_schema(c):
    c.execute("""CREATE TABLE IF NOT EXISTS teacher_assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        class_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        is_class_teacher INTEGER NOT NULL DEFAULT 0,
        UNIQUE(username,class_name,subject)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS substitution_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL, period_no INTEGER NOT NULL, day_name TEXT NOT NULL,
        subject TEXT NOT NULL, absent_teacher TEXT NOT NULL, substitute_teacher TEXT NOT NULL,
        start_time TEXT DEFAULT '', end_time TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'Pending',
        message TEXT DEFAULT '', created_at TEXT NOT NULL, responded_at TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS period_exchange_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester TEXT NOT NULL, target_teacher TEXT NOT NULL,
        class_name TEXT NOT NULL, period_no INTEGER NOT NULL, day_name TEXT NOT NULL,
        requested_subject TEXT NOT NULL, offered_period_no INTEGER, offered_day_name TEXT DEFAULT '',
        message TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'Pending',
        created_at TEXT NOT NULL, responded_at TEXT DEFAULT ''
    )""")
    # Migrate the original single-subject/class-teacher fields into the new assignment table.
    legacy = c.execute("SELECT username,subject,class_teacher FROM users WHERE role='teacher'").fetchall()
    for r in legacy:
        subject = (r["subject"] or "").strip()
        class_name = (r["class_teacher"] or "").strip()
        if subject and class_name:
            c.execute("INSERT OR IGNORE INTO teacher_assignments(username,class_name,subject,is_class_teacher) VALUES(?,?,?,1)", (r["username"],class_name,subject))


@app.before_request
def targeted_schema_bootstrap():
    if session.get("role") in ["admin", "teacher", "student"] and session.get("school_id") not in [None, "", "master"]:
        c = get_db_connection(); _ensure_targeted_schema(c); c.commit(); c.close()


@app.context_processor
def targeted_menu_context():
    assignments = []
    substitutions = []
    exchanges = []
    accepted_substitutions = []
    if session.get("role") in ["teacher", "admin", "student"] and session.get("school_id") not in [None, "", "master"]:
        try:
            c = get_db_connection(); _ensure_targeted_schema(c)
            accepted_substitutions = c.execute("SELECT * FROM substitution_requests WHERE status='Accepted' ORDER BY day_name,period_no,id DESC").fetchall()
            if session.get("role") == "teacher":
                assignments = c.execute("SELECT * FROM teacher_assignments WHERE username=? ORDER BY class_name,subject", (session.get("username", ""),)).fetchall()
                substitutions = c.execute("SELECT * FROM substitution_requests WHERE substitute_teacher=? ORDER BY id DESC LIMIT 10", (session.get("username", ""),)).fetchall()
                exchanges = c.execute("SELECT * FROM period_exchange_requests WHERE target_teacher=? OR requester=? ORDER BY id DESC LIMIT 10", (session.get("username", ""), session.get("username", ""))).fetchall()
            c.close()
        except Exception:
            pass
    return {"teacher_assignments_menu": assignments, "substitution_menu": substitutions, "exchange_menu": exchanges, "accepted_substitutions": accepted_substitutions}


@app.route("/subject-students")
def subject_students():
    if session.get("role") not in ["teacher", "admin"]:
        return redirect(url_for("login"))
    c=get_db_connection(); _ensure_targeted_schema(c)
    if session.get("role") == "teacher":
        rows=c.execute("""SELECT DISTINCT s.admission_no,s.name,s.class_name,s.roll_no,s.email,s.phone,ta.subject
                          FROM students s JOIN teacher_assignments ta ON ta.class_name=s.class_name
                          WHERE ta.username=? ORDER BY s.class_name,ta.subject,s.admission_no""", (session.get("username",""),)).fetchall()
    else:
        rows=c.execute("""SELECT s.admission_no,s.name,s.class_name,s.roll_no,s.email,s.phone,
                               COALESCE((SELECT GROUP_CONCAT(DISTINCT ta.subject) FROM teacher_assignments ta WHERE ta.class_name=s.class_name),'') AS subject
                        FROM students s ORDER BY s.class_name,s.admission_no""").fetchall()
    c.close(); return render_template("subject_students.html", rows=rows)


@app.route("/teacher-schedule")
def teacher_schedule():
    if session.get("role") not in ["teacher", "admin"]:
        return redirect(url_for("login"))
    c = get_db_connection(); _ensure_targeted_schema(c)
    username = request.args.get("teacher", "").strip() if session.get("role") == "admin" else session.get("username", "")
    if session.get("role") == "admin" and not username:
        username = session.get("username", "")
    assignments = c.execute("SELECT * FROM teacher_assignments WHERE username=? ORDER BY class_name,subject", (username,)).fetchall()
    rows = c.execute("""
        SELECT t.* FROM timetables t
        WHERE t.teacher=?
        ORDER BY CASE t.day_name WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END, t.period_no
    """, (username,)).fetchall()
    # Also match by assigned subject/class when old timetable rows contain a teacher display name.
    if not rows and assignments:
        pairs = [(a["class_name"], a["subject"]) for a in assignments]
        rows = c.execute("SELECT * FROM timetables ORDER BY class_name,period_no").fetchall()
        rows = [r for r in rows if (r["class_name"], r["subject"]) in pairs]
    c.close()
    return render_template("teacher_schedule.html", teacher=username, assignments=assignments, rows=rows)


@app.route("/substitutions", methods=["GET", "POST"])
def substitutions():
    if session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))
    c = get_db_connection(); _ensure_targeted_schema(c)
    if request.method == "POST":
        action = request.form.get("action", "")
        rid = request.form.get("request_id", "")
        if action in ["accept", "deny"] and rid and session.get("role") == "teacher":
            status = "Accepted" if action == "accept" else "Denied"
            c.execute("UPDATE substitution_requests SET status=?,responded_at=? WHERE id=? AND substitute_teacher=?",
                      (status, datetime.now().isoformat(), rid, session.get("username", "")))
            c.commit(); flash(f"Substitution {status.lower()}.", "success")
        elif session.get("role") == "admin" and action == "create":
            fields = (request.form.get("class_name", "").strip(), int(request.form.get("period_no", "1")), request.form.get("day_name", "").strip(), request.form.get("subject", "").strip(), request.form.get("absent_teacher", "").strip(), request.form.get("substitute_teacher", "").strip(), request.form.get("start_time", ""), request.form.get("end_time", ""), request.form.get("message", "").strip(), datetime.now().isoformat())
            if all([fields[0], fields[2], fields[3], fields[4], fields[5]]):
                c.execute("""INSERT INTO substitution_requests(class_name,period_no,day_name,subject,absent_teacher,substitute_teacher,start_time,end_time,message,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""", fields)
                c.commit(); flash("Substitution offer sent to the selected teacher.", "success")
        c.close(); return redirect(url_for("substitutions"))
    if session.get("role") == "admin":
        rows = c.execute("SELECT * FROM substitution_requests ORDER BY id DESC").fetchall()
        teachers = c.execute("SELECT username,full_name FROM users WHERE role='teacher' ORDER BY username").fetchall()
    else:
        rows = c.execute("SELECT * FROM substitution_requests WHERE substitute_teacher=? OR absent_teacher=? ORDER BY id DESC", (session.get("username", ""), session.get("username", ""))).fetchall()
        teachers = []
    classes = c.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    c.close(); return render_template("substitutions.html", rows=rows, teachers=teachers, classes=classes)


@app.route("/period-exchange", methods=["GET", "POST"])
def period_exchange():
    if session.get("role") != "teacher":
        return redirect(url_for("login"))
    c = get_db_connection(); _ensure_targeted_schema(c)
    if request.method == "POST":
        action = request.form.get("action", "create")
        rid = request.form.get("request_id", "")
        if action in ["accept", "deny"] and rid:
            status = "Accepted" if action == "accept" else "Denied"
            c.execute("UPDATE period_exchange_requests SET status=?,responded_at=? WHERE id=? AND target_teacher=?", (status,datetime.now().isoformat(),rid,session.get("username", "")))
            c.commit(); flash(f"Exchange request {status.lower()}.", "success")
        else:
            target = request.form.get("target_teacher", "").strip()
            class_name = request.form.get("class_name", "").strip()
            subject = request.form.get("requested_subject", "").strip()
            if target and class_name and subject and target != session.get("username"):
                c.execute("""INSERT INTO period_exchange_requests(requester,target_teacher,class_name,period_no,day_name,requested_subject,offered_period_no,offered_day_name,message,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                          (session.get("username",""),target,class_name,int(request.form.get("period_no","1")),request.form.get("day_name", "").strip(),subject,int(request.form.get("offered_period_no","1")),request.form.get("offered_day_name", "").strip(),request.form.get("message", "").strip(),datetime.now().isoformat()))
                c.commit(); flash("Period exchange request sent.", "success")
        c.close(); return redirect(url_for("period_exchange"))
    incoming = c.execute("SELECT * FROM period_exchange_requests WHERE target_teacher=? ORDER BY id DESC", (session.get("username", ""),)).fetchall()
    outgoing = c.execute("SELECT * FROM period_exchange_requests WHERE requester=? ORDER BY id DESC", (session.get("username", ""),)).fetchall()
    teachers = c.execute("SELECT username,full_name FROM users WHERE role='teacher' AND username<>? ORDER BY username", (session.get("username", ""),)).fetchall()
    classes = c.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    c.close(); return render_template("period_exchange.html", incoming=incoming, outgoing=outgoing, teachers=teachers, classes=classes)


# Admin assignment UI: one teacher may have any number of subject/class rows.
@app.route("/teacher-assignments")
def teacher_assignments_page():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    c=get_db_connection(); _ensure_targeted_schema(c)
    rows=c.execute("SELECT ta.*,u.full_name FROM teacher_assignments ta LEFT JOIN users u ON u.username=ta.username ORDER BY ta.username,ta.class_name,ta.subject").fetchall()
    teachers=c.execute("SELECT username,full_name FROM users WHERE role='teacher' ORDER BY username").fetchall()
    subjects=c.execute("SELECT name FROM subjects ORDER BY name").fetchall()
    classes=c.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name").fetchall()
    c.close(); return render_template("teacher_assignments.html", rows=rows, teachers=teachers, subjects=subjects, classes=classes)


@app.route("/teacher-assignments/add", methods=["POST"])
def add_teacher_assignment():
    if session.get("role") != "admin": return redirect(url_for("login"))
    username=request.form.get("username", "").strip(); subject=request.form.get("subject", "").strip(); class_name=request.form.get("class_name", "").strip(); is_ct=1 if request.form.get("is_class_teacher") else 0
    c=get_db_connection(); _ensure_targeted_schema(c)
    if not username or not subject or not class_name:
        c.close(); flash("Teacher, subject and class are required.", "error"); return redirect(url_for("teacher_assignments_page"))
    if is_ct:
        c.execute("UPDATE teacher_assignments SET is_class_teacher=0 WHERE class_name=?", (class_name,))
        c.execute("UPDATE users SET class_teacher=? WHERE username=? AND role='teacher'", (class_name,username))
    try:
        c.execute("INSERT INTO teacher_assignments(username,class_name,subject,is_class_teacher) VALUES(?,?,?,?)", (username,class_name,subject,is_ct)); c.commit(); flash("Teacher assignment added.", "success")
    except sqlite3.IntegrityError:
        flash("That teacher is already assigned to this subject/class.", "error")
    c.close(); return redirect(url_for("teacher_assignments_page"))


@app.route("/teacher-assignments/delete/<int:assignment_id>", methods=["POST"])
def delete_teacher_assignment(assignment_id):
    if session.get("role") != "admin": return redirect(url_for("login"))
    c=get_db_connection(); _ensure_targeted_schema(c); c.execute("DELETE FROM teacher_assignments WHERE id=?", (assignment_id,)); c.commit(); c.close(); flash("Teacher assignment removed.", "success"); return redirect(url_for("teacher_assignments_page"))

# ==========================================================
# START APPLICATION
# ==========================================================

if __name__ == "__main__":

    setup_database()
    setup_extra_database()

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5004
    )