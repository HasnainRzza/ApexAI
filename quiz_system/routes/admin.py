from werkzeug.security import generate_password_hash

from flask import Blueprint, jsonify, request

from quiz_system.auth import require_roles
from quiz_system.database.db import get_db, rows_to_list
from quiz_system.validators import validate_email

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard", methods=["GET"])
@require_roles("admin")
def dashboard(user):
    with get_db() as conn:
        stats = {
            "total_students": conn.execute(
                "SELECT COUNT(*) AS c FROM students"
            ).fetchone()["c"],
            "total_lecturers": conn.execute(
                "SELECT COUNT(*) AS c FROM lecturers"
            ).fetchone()["c"],
            "total_courses": conn.execute(
                "SELECT COUNT(*) AS c FROM courses"
            ).fetchone()["c"],
            "total_quizzes": conn.execute(
                "SELECT COUNT(*) AS c FROM quizzes"
            ).fetchone()["c"],
            "active_quizzes": conn.execute(
                """SELECT COUNT(*) AS c FROM quizzes
                   WHERE datetime(start_time) <= datetime('now', 'localtime')
                     AND datetime(end_time) >= datetime('now', 'localtime')"""
            ).fetchone()["c"],
        }
    return jsonify(stats)


@admin_bp.route("/semesters", methods=["GET", "POST"])
@require_roles("admin")
def semesters(user):
    if request.method == "GET":
        with get_db() as conn:
            return jsonify(rows_to_list(conn.execute("SELECT * FROM semesters ORDER BY year DESC").fetchall()))
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    year = data.get("year")
    if not name or not year:
        return jsonify({"error": "Name and year are required."}), 400
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO semesters (name, year, term) VALUES (?, ?, ?)",
                (name, int(year), data.get("term")),
            )
            row = conn.execute("SELECT * FROM semesters WHERE id = ?", (cur.lastrowid,)).fetchone()
            return jsonify(dict(row)), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400


@admin_bp.route("/semesters/<int:sid>", methods=["PUT", "DELETE"])
@require_roles("admin")
def semester_detail(user, sid):
    if request.method == "DELETE":
        with get_db() as conn:
            conn.execute("DELETE FROM semesters WHERE id = ?", (sid,))
        return jsonify({"message": "Deleted."})
    data = request.get_json() or {}
    with get_db() as conn:
        conn.execute(
            "UPDATE semesters SET name=?, year=?, term=?, is_active=? WHERE id=?",
            (data.get("name"), data.get("year"), data.get("term"), data.get("is_active", 1), sid),
        )
        row = conn.execute("SELECT * FROM semesters WHERE id = ?", (sid,)).fetchone()
    return jsonify(dict(row))


@admin_bp.route("/courses", methods=["GET", "POST"])
@require_roles("admin")
def courses(user):
    if request.method == "GET":
        q = request.args.get("q", "").strip()
        with get_db() as conn:
            if q:
                rows = conn.execute(
                    """SELECT c.*, s.name AS semester_name FROM courses c
                       JOIN semesters s ON c.semester_id = s.id
                       WHERE c.name LIKE ? OR c.code LIKE ?
                       ORDER BY c.code""",
                    (f"%{q}%", f"%{q}%"),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT c.*, s.name AS semester_name FROM courses c
                       JOIN semesters s ON c.semester_id = s.id ORDER BY c.code"""
                ).fetchall()
            return jsonify(rows_to_list(rows))

    data = request.get_json() or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    semester_id = data.get("semester_id")
    if not code or not name or not semester_id:
        return jsonify({"error": "Code, name, and semester are required."}), 400
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO courses (code, name, description, semester_id) VALUES (?,?,?,?)",
                (code, name, data.get("description"), semester_id),
            )
            row = conn.execute(
                """SELECT c.*, s.name AS semester_name FROM courses c
                   JOIN semesters s ON c.semester_id = s.id WHERE c.id = ?""",
                (cur.lastrowid,),
            ).fetchone()
            return jsonify(dict(row)), 201
        except Exception as e:
            return jsonify({"error": "Course code must be unique." if "UNIQUE" in str(e) else str(e)}), 400


@admin_bp.route("/courses/<int:cid>", methods=["PUT", "DELETE"])
@require_roles("admin")
def course_detail(user, cid):
    if request.method == "DELETE":
        with get_db() as conn:
            conn.execute("DELETE FROM courses WHERE id = ?", (cid,))
        return jsonify({"message": "Course and related data removed."})
    data = request.get_json() or {}
    with get_db() as conn:
        conn.execute(
            "UPDATE courses SET code=?, name=?, description=?, semester_id=? WHERE id=?",
            (data.get("code"), data.get("name"), data.get("description"), data.get("semester_id"), cid),
        )
        row = conn.execute(
            """SELECT c.*, s.name AS semester_name FROM courses c
               JOIN semesters s ON c.semester_id = s.id WHERE c.id = ?""",
            (cid,),
        ).fetchone()
    return jsonify(dict(row))


@admin_bp.route("/lecturers", methods=["GET", "POST"])
@require_roles("admin")
def lecturers(user):
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute(
                """SELECT l.id, l.employee_code, u.id AS user_id, u.email,
                          u.first_name, u.last_name, u.is_active
                   FROM lecturers l JOIN users u ON l.user_id = u.id
                   ORDER BY u.last_name"""
            ).fetchall()
            return jsonify(rows_to_list(rows))

    data = request.get_json() or {}
    email, err = validate_email(data.get("email"))
    if err:
        return jsonify({"error": err}), 400
    password = data.get("password") or "Lecturer@123"
    fn = (data.get("first_name") or "").strip()
    ln = (data.get("last_name") or "").strip()
    if not fn or not ln:
        return jsonify({"error": "First and last name required."}), 400

    with get_db() as conn:
        role_id = conn.execute("SELECT id FROM roles WHERE name='lecturer'").fetchone()["id"]
        try:
            cur = conn.execute(
                """INSERT INTO users (email, password_hash, role_id, first_name, last_name)
                   VALUES (?,?,?,?,?)""",
                (email, generate_password_hash(password), role_id, fn, ln),
            )
            uid = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO lecturers (user_id, employee_code) VALUES (?,?)",
                (uid, data.get("employee_code") or f"LEC-{uid:04d}"),
            )
            return jsonify({
                "id": cur2.lastrowid,
                "email": email,
                "password": password,
                "first_name": fn,
                "last_name": ln,
            }), 201
        except Exception as e:
            return jsonify({"error": "Email already exists." if "UNIQUE" in str(e) else str(e)}), 400


@admin_bp.route("/lecturers/<int:lid>", methods=["PUT", "DELETE"])
@require_roles("admin")
def lecturer_detail(user, lid):
    if request.method == "DELETE":
        with get_db() as conn:
            lec = conn.execute("SELECT user_id FROM lecturers WHERE id=?", (lid,)).fetchone()
            if lec:
                conn.execute("DELETE FROM lecturers WHERE id=?", (lid,))
                conn.execute("DELETE FROM users WHERE id=?", (lec["user_id"],))
        return jsonify({"message": "Lecturer removed."})
    data = request.get_json() or {}
    with get_db() as conn:
        lec = conn.execute("SELECT user_id FROM lecturers WHERE id=?", (lid,)).fetchone()
        if not lec:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE users SET first_name=?, last_name=?, is_active=? WHERE id=?",
            (data.get("first_name"), data.get("last_name"), data.get("is_active", 1), lec["user_id"]),
        )
    return jsonify({"message": "Updated."})


@admin_bp.route("/students", methods=["GET", "POST"])
@require_roles("admin")
def students(user):
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute(
                """SELECT s.id, s.student_code, u.id AS user_id, u.email,
                          u.first_name, u.last_name, u.is_active
                   FROM students s JOIN users u ON s.user_id = u.id
                   ORDER BY u.last_name"""
            ).fetchall()
            return jsonify(rows_to_list(rows))

    data = request.get_json() or {}
    email, err = validate_email(data.get("email"))
    if err:
        return jsonify({"error": err}), 400
    password = data.get("password") or "Student@123"
    fn = (data.get("first_name") or "").strip()
    ln = (data.get("last_name") or "").strip()
    if not fn or not ln:
        return jsonify({"error": "First and last name required."}), 400

    with get_db() as conn:
        role_id = conn.execute("SELECT id FROM roles WHERE name='student'").fetchone()["id"]
        try:
            cur = conn.execute(
                """INSERT INTO users (email, password_hash, role_id, first_name, last_name)
                   VALUES (?,?,?,?,?)""",
                (email, generate_password_hash(password), role_id, fn, ln),
            )
            uid = cur.lastrowid
            cur2 = conn.execute(
                "INSERT INTO students (user_id, student_code) VALUES (?,?)",
                (uid, data.get("student_code") or f"STD-{uid:04d}"),
            )
            return jsonify({
                "id": cur2.lastrowid,
                "email": email,
                "password": password,
                "first_name": fn,
                "last_name": ln,
            }), 201
        except Exception as e:
            return jsonify({"error": "Email already exists." if "UNIQUE" in str(e) else str(e)}), 400


@admin_bp.route("/students/<int:sid>", methods=["PUT", "DELETE"])
@require_roles("admin")
def student_detail(user, sid):
    if request.method == "DELETE":
        with get_db() as conn:
            st = conn.execute("SELECT user_id FROM students WHERE id=?", (sid,)).fetchone()
            if st:
                conn.execute("DELETE FROM students WHERE id=?", (sid,))
                conn.execute("DELETE FROM users WHERE id=?", (st["user_id"],))
        return jsonify({"message": "Student removed."})
    data = request.get_json() or {}
    with get_db() as conn:
        st = conn.execute("SELECT user_id FROM students WHERE id=?", (sid,)).fetchone()
        if not st:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE users SET first_name=?, last_name=?, is_active=? WHERE id=?",
            (data.get("first_name"), data.get("last_name"), data.get("is_active", 1), st["user_id"]),
        )
    return jsonify({"message": "Updated."})


@admin_bp.route("/allocations", methods=["GET", "POST", "DELETE"])
@require_roles("admin")
def allocations(user):
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute(
                """SELECT a.id, a.course_id, a.lecturer_id,
                          c.code, c.name AS course_name,
                          u.first_name || ' ' || u.last_name AS lecturer_name
                   FROM course_lecturer_allocations a
                   JOIN courses c ON a.course_id = c.id
                   JOIN lecturers l ON a.lecturer_id = l.id
                   JOIN users u ON l.user_id = u.id"""
            ).fetchall()
            return jsonify(rows_to_list(rows))

    if request.method == "DELETE":
        alloc_id = request.args.get("id")
        if not alloc_id:
            return jsonify({"error": "Allocation id required."}), 400
        with get_db() as conn:
            conn.execute("DELETE FROM course_lecturer_allocations WHERE id=?", (alloc_id,))
        return jsonify({"message": "Allocation removed."})

    data = request.get_json() or {}
    course_id = data.get("course_id")
    lecturer_id = data.get("lecturer_id")
    if not course_id or not lecturer_id:
        return jsonify({"error": "course_id and lecturer_id required."}), 400
    with get_db() as conn:
        dup = conn.execute(
            """SELECT 1 FROM course_lecturer_allocations
               WHERE course_id=? AND lecturer_id=?""",
            (course_id, lecturer_id),
        ).fetchone()
        if dup:
            return jsonify({"error": "Lecturer already assigned to this course."}), 400
        try:
            cur = conn.execute(
                "INSERT INTO course_lecturer_allocations (course_id, lecturer_id) VALUES (?,?)",
                (course_id, lecturer_id),
            )
            return jsonify({"id": cur.lastrowid}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400


@admin_bp.route("/enrollments", methods=["GET", "POST", "DELETE"])
@require_roles("admin")
def enrollments(user):
    if request.method == "GET":
        course_id = request.args.get("course_id")
        with get_db() as conn:
            sql = """SELECT e.id, e.student_id, e.course_id, e.semester_id,
                            u.first_name || ' ' || u.last_name AS student_name,
                            u.email, c.code AS course_code, c.name AS course_name
                     FROM student_enrollments e
                     JOIN students s ON e.student_id = s.id
                     JOIN users u ON s.user_id = u.id
                     JOIN courses c ON e.course_id = c.id"""
            if course_id:
                rows = conn.execute(sql + " WHERE e.course_id=?", (course_id,)).fetchall()
            else:
                rows = conn.execute(sql).fetchall()
            return jsonify(rows_to_list(rows))

    if request.method == "DELETE":
        eid = request.args.get("id")
        with get_db() as conn:
            conn.execute("DELETE FROM student_enrollments WHERE id=?", (eid,))
        return jsonify({"message": "Enrollment removed."})

    data = request.get_json() or {}
    student_id = data.get("student_id")
    course_id = data.get("course_id")
    semester_id = data.get("semester_id")
    if not all([student_id, course_id, semester_id]):
        return jsonify({"error": "student_id, course_id, semester_id required."}), 400
    with get_db() as conn:
        dup = conn.execute(
            "SELECT 1 FROM student_enrollments WHERE student_id=? AND course_id=?",
            (student_id, course_id),
        ).fetchone()
        if dup:
            return jsonify({"error": "Student already enrolled in this course."}), 400
        cur = conn.execute(
            "INSERT INTO student_enrollments (student_id, course_id, semester_id) VALUES (?,?,?)",
            (student_id, course_id, semester_id),
        )
        return jsonify({"id": cur.lastrowid}), 201


@admin_bp.route("/quizzes", methods=["GET"])
@require_roles("admin")
def all_quizzes(user):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT q.*, c.code AS course_code, c.name AS course_name,
                      u.first_name || ' ' || u.last_name AS lecturer_name
               FROM quizzes q
               JOIN courses c ON q.course_id = c.id
               JOIN lecturers l ON q.lecturer_id = l.id
               JOIN users u ON l.user_id = u.id
               ORDER BY q.created_at DESC"""
        ).fetchall()
        return jsonify(rows_to_list(rows))


@admin_bp.route("/courses/<int:cid>/students", methods=["GET"])
@require_roles("admin")
def course_students(user, cid):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.first_name, u.last_name, u.email, s.student_code, e.enrolled_at
               FROM student_enrollments e
               JOIN students s ON e.student_id = s.id
               JOIN users u ON s.user_id = u.id
               WHERE e.course_id = ?""",
            (cid,),
        ).fetchall()
        return jsonify(rows_to_list(rows))
