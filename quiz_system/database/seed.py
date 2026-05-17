"""Seed roles, admin, sample lecturers, students, courses, and a demo quiz."""
import os

from werkzeug.security import generate_password_hash

from quiz_system.config import DB_PATH
from quiz_system.database.db import get_db, init_schema


def _schema_ok():
    if not os.path.exists(DB_PATH):
        return False
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        return "password_hash" in cols and "role_id" in cols
    except Exception:
        return False
    finally:
        conn.close()


def seed():
    if os.path.exists(DB_PATH) and not _schema_ok():
        os.remove(DB_PATH)
        print("[Quiz DB] Removed outdated database; recreating schema.")
    init_schema()
    with get_db() as conn:
        roles = [("admin",), ("lecturer",), ("student",)]
        conn.executemany("INSERT OR IGNORE INTO roles (name) VALUES (?)", roles)

        role_map = {
            r["name"]: r["id"]
            for r in conn.execute("SELECT id, name FROM roles").fetchall()
        }

        def upsert_user(email, password, role, first, last):
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email.lower(),)
            ).fetchone()
            if existing:
                return existing["id"]
            cur = conn.execute(
                """INSERT INTO users (email, password_hash, role_id, first_name, last_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    email.lower(),
                    generate_password_hash(password),
                    role_map[role],
                    first,
                    last,
                ),
            )
            return cur.lastrowid

        admin_id = upsert_user(
            "admin@apexai.edu", "Admin@123", "admin", "System", "Administrator"
        )

        lec_users = [
            ("lecturer1@apexai.edu", "Lecturer@123", "Ahmed", "Khan"),
            ("lecturer2@apexai.edu", "Lecturer@123", "Sara", "Malik"),
        ]
        lecturer_ids = []
        for email, pw, fn, ln in lec_users:
            uid = upsert_user(email, pw, "lecturer", fn, ln)
            row = conn.execute(
                "SELECT id FROM lecturers WHERE user_id = ?", (uid,)
            ).fetchone()
            if not row:
                cur = conn.execute(
                    "INSERT INTO lecturers (user_id, employee_code) VALUES (?, ?)",
                    (uid, f"LEC-{uid:04d}"),
                )
                lecturer_ids.append(cur.lastrowid)
            else:
                lecturer_ids.append(row["id"])

        semesters_data = [
            ("Fall 2025", 2025, "Fall"),
            ("Spring 2026", 2026, "Spring"),
        ]
        sem_ids = []
        for name, year, term in semesters_data:
            row = conn.execute(
                "SELECT id FROM semesters WHERE name = ? AND year = ?",
                (name, year),
            ).fetchone()
            if row:
                sem_ids.append(row["id"])
            else:
                cur = conn.execute(
                    "INSERT INTO semesters (name, year, term) VALUES (?, ?, ?)",
                    (name, year, term),
                )
                sem_ids.append(cur.lastrowid)

        courses_data = [
            ("CS101", "Programming Fundamentals", sem_ids[0]),
            ("CS201", "Data Structures", sem_ids[0]),
            ("CS301", "Database Systems", sem_ids[1]),
        ]
        course_ids = []
        for code, name, sem_id in courses_data:
            row = conn.execute(
                "SELECT id FROM courses WHERE code = ?", (code,)
            ).fetchone()
            if row:
                course_ids.append(row["id"])
            else:
                cur = conn.execute(
                    "INSERT INTO courses (code, name, semester_id) VALUES (?, ?, ?)",
                    (code, name, sem_id),
                )
                course_ids.append(cur.lastrowid)

        for lid, cid in [(lecturer_ids[0], course_ids[0]), (lecturer_ids[0], course_ids[1]), (lecturer_ids[1], course_ids[2])]:
            conn.execute(
                """INSERT OR IGNORE INTO course_lecturer_allocations (course_id, lecturer_id)
                   VALUES (?, ?)""",
                (cid, lid),
            )

        student_users = [
            ("student1@apexai.edu", "Student@123", "Ali", "Hassan"),
            ("student2@apexai.edu", "Student@123", "Fatima", "Shah"),
            ("student3@apexai.edu", "Student@123", "Usman", "Raza"),
        ]
        student_ids = []
        for email, pw, fn, ln in student_users:
            uid = upsert_user(email, pw, "student", fn, ln)
            row = conn.execute(
                "SELECT id FROM students WHERE user_id = ?", (uid,)
            ).fetchone()
            if not row:
                cur = conn.execute(
                    "INSERT INTO students (user_id, student_code) VALUES (?, ?)",
                    (uid, f"STD-{uid:04d}"),
                )
                student_ids.append(cur.lastrowid)
            else:
                student_ids.append(row["id"])

        for sid, cid in [
            (student_ids[0], course_ids[0]),
            (student_ids[0], course_ids[1]),
            (student_ids[1], course_ids[0]),
            (student_ids[2], course_ids[2]),
        ]:
            sem = conn.execute(
                "SELECT semester_id FROM courses WHERE id = ?", (cid,)
            ).fetchone()
            conn.execute(
                """INSERT OR IGNORE INTO student_enrollments
                   (student_id, course_id, semester_id) VALUES (?, ?, ?)""",
                (sid, cid, sem["semester_id"]),
            )

        from datetime import datetime, timedelta

        now = datetime.now()
        start = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        end = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        existing_quiz = conn.execute(
            "SELECT id FROM quizzes WHERE title = ?", ("Sample Programming Quiz",)
        ).fetchone()
        if not existing_quiz:
            cur = conn.execute(
                """INSERT INTO quizzes
                   (course_id, lecturer_id, title, start_time, end_time, duration_minutes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (course_ids[0], lecturer_ids[0], "Sample Programming Quiz", start, end, 15),
            )
            qz = cur.lastrowid
            q1 = conn.execute(
                "INSERT INTO questions (quiz_id, statement, sort_order) VALUES (?,?,0)",
                (qz, "What does HTML stand for?"),
            ).lastrowid
            opts = [
                ("Hyper Text Markup Language", 1),
                ("High Transfer Machine Language", 0),
                ("Home Tool Markup Language", 0),
                ("Hyperlink Text Model Language", 0),
            ]
            for i, (text, correct) in enumerate(opts):
                conn.execute(
                    "INSERT INTO question_options (question_id, option_text, is_correct, sort_order) VALUES (?,?,?,?)",
                    (q1, text, correct, i),
                )

        print("[Quiz DB] Seed complete.")
        print("  Admin:    admin@apexai.edu / Admin@123")
        print("  Lecturer: lecturer1@apexai.edu / Lecturer@123")
        print("  Student:  student1@apexai.edu / Student@123")


if __name__ == "__main__":
    seed()
