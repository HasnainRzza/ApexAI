from flask import Blueprint, jsonify, request

from quiz_system.auth import require_roles
from quiz_system.database.db import get_db, rows_to_list
from quiz_system.services.quiz_service import (
    create_quiz_with_questions,
    get_quiz_full,
    lecturer_assigned_to_course,
)
from quiz_system.validators import normalize_datetime_str, validate_quiz_times, validate_questions

lecturer_bp = Blueprint("lecturer", __name__)


@lecturer_bp.route("/courses", methods=["GET"])
@require_roles("lecturer")
def my_courses(user):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.*, s.name AS semester_name
               FROM courses c
               JOIN course_lecturer_allocations a ON a.course_id = c.id
               JOIN semesters s ON c.semester_id = s.id
               WHERE a.lecturer_id = ?
               ORDER BY c.code""",
            (user["lecturer_id"],),
        ).fetchall()
        return jsonify(rows_to_list(rows))


@lecturer_bp.route("/quizzes", methods=["GET", "POST"])
@require_roles("lecturer")
def quizzes(user):
    lid = user["lecturer_id"]
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute(
                """SELECT q.*, c.code AS course_code, c.name AS course_name
                   FROM quizzes q JOIN courses c ON q.course_id = c.id
                   WHERE q.lecturer_id = ? ORDER BY q.start_time DESC""",
                (lid,),
            ).fetchall()
            return jsonify(rows_to_list(rows))

    data = request.get_json() or {}
    _, _, err = validate_quiz_times(data.get("start_time"), data.get("end_time"))
    if err:
        return jsonify({"error": err}), 400
    if not (data.get("title") or "").strip():
        return jsonify({"error": "Title is required."}), 400
    try:
        dur = int(data.get("duration_minutes", 0))
        if dur <= 0:
            return jsonify({"error": "Duration must be positive."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid duration."}), 400

    quiz_id, err = create_quiz_with_questions(lid, data)
    if err:
        return jsonify({"error": err}), 400
    with get_db() as conn:
        quiz = get_quiz_full(conn, quiz_id)
    return jsonify(quiz), 201


@lecturer_bp.route("/quizzes/<int:qid>", methods=["GET", "PUT", "DELETE"])
@require_roles("lecturer")
def quiz_detail(user, qid):
    lid = user["lecturer_id"]
    if request.method == "GET":
        with get_db() as conn:
            quiz = conn.execute(
                "SELECT * FROM quizzes WHERE id=? AND lecturer_id=?", (qid, lid)
            ).fetchone()
            if not quiz:
                return jsonify({"error": "Not found"}), 404
            return jsonify(get_quiz_full(conn, qid))

    if request.method == "DELETE":
        with get_db() as conn:
            quiz = conn.execute(
                "SELECT id FROM quizzes WHERE id=? AND lecturer_id=?", (qid, lid)
            ).fetchone()
            if not quiz:
                return jsonify({"error": "Not found"}), 404
            conn.execute("DELETE FROM quizzes WHERE id=?", (qid,))
        return jsonify({"message": "Quiz deleted."})

    data = request.get_json() or {}
    _, _, err = validate_quiz_times(data.get("start_time"), data.get("end_time"))
    if err:
        return jsonify({"error": err}), 400
    q_err = validate_questions(data.get("questions", []))
    if q_err:
        return jsonify({"error": q_err}), 400

    with get_db() as conn:
        quiz = conn.execute(
            "SELECT * FROM quizzes WHERE id=? AND lecturer_id=?", (qid, lid)
        ).fetchone()
        if not quiz:
            return jsonify({"error": "Not found"}), 404
        if not lecturer_assigned_to_course(conn, lid, data.get("course_id", quiz["course_id"])):
            return jsonify({"error": "Not assigned to course."}), 403

        conn.execute(
            """UPDATE quizzes SET course_id=?, title=?, start_time=?, end_time=?,
               duration_minutes=?, allow_multiple_attempts=?, updated_at=datetime('now')
               WHERE id=?""",
            (
                data.get("course_id", quiz["course_id"]),
                data.get("title", quiz["title"]).strip(),
                normalize_datetime_str(data.get("start_time", quiz["start_time"])),
                normalize_datetime_str(data.get("end_time", quiz["end_time"])),
                int(data.get("duration_minutes", quiz["duration_minutes"])),
                1 if data.get("allow_multiple_attempts") else 0,
                qid,
            ),
        )
        conn.execute("DELETE FROM questions WHERE quiz_id=?", (qid,))
        from quiz_system.services.quiz_service import _insert_questions

        _insert_questions(conn, qid, data["questions"])
        return jsonify(get_quiz_full(conn, qid))


@lecturer_bp.route("/quizzes/<int:qid>/submissions", methods=["GET"])
@require_roles("lecturer")
def quiz_submissions(user, qid):
    lid = user["lecturer_id"]
    with get_db() as conn:
        quiz = conn.execute(
            "SELECT id FROM quizzes WHERE id=? AND lecturer_id=?", (qid, lid)
        ).fetchone()
        if not quiz:
            return jsonify({"error": "Not found"}), 404
        rows = conn.execute(
            """SELECT a.*, u.first_name, u.last_name, u.email
               FROM quiz_attempts a
               JOIN students s ON a.student_id = s.id
               JOIN users u ON s.user_id = u.id
               WHERE a.quiz_id = ? AND a.status IN ('submitted', 'auto_submitted')
               ORDER BY a.submitted_at DESC""",
            (qid,),
        ).fetchall()
        return jsonify(rows_to_list(rows))
