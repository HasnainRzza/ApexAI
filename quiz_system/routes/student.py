from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from quiz_system.auth import require_roles
from quiz_system.database.db import get_db, rows_to_list
from quiz_system.services.quiz_service import (
    get_quiz_full,
    start_student_attempt,
    submit_attempt,
)
from quiz_system.validators import quiz_ended, quiz_is_active, quiz_not_started

student_bp = Blueprint("student", __name__)


@student_bp.route("/courses", methods=["GET"])
@require_roles("student")
def my_courses(user):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.*, s.name AS semester_name, e.enrolled_at
               FROM student_enrollments e
               JOIN courses c ON e.course_id = c.id
               JOIN semesters s ON c.semester_id = s.id
               WHERE e.student_id = ?
               ORDER BY c.code""",
            (user["student_id"],),
        ).fetchall()
        return jsonify(rows_to_list(rows))


@student_bp.route("/quizzes", methods=["GET"])
@require_roles("student")
def active_quizzes(user):
    sid = user["student_id"]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT q.id, q.title, q.start_time, q.end_time, q.duration_minutes,
                      c.code AS course_code, c.name AS course_name,
                      a.id AS attempt_id, a.status AS attempt_status, a.score
               FROM quizzes q
               JOIN courses c ON q.course_id = c.id
               JOIN student_enrollments e ON e.course_id = c.id AND e.student_id = ?
               LEFT JOIN quiz_attempts a ON a.quiz_id = q.id AND a.student_id = ?
               WHERE datetime(q.start_time) <= datetime('now', 'localtime')
                 AND datetime(q.end_time) >= datetime('now', 'localtime')
               ORDER BY q.start_time""",
            (sid, sid),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_active"] = True
            if d.get("attempt_status") in ("submitted", "auto_submitted"):
                d["already_submitted"] = True
            else:
                d["already_submitted"] = False
            result.append(d)
        return jsonify(result)


@student_bp.route("/quizzes/all", methods=["GET"])
@require_roles("student")
def all_quizzes(user):
    sid = user["student_id"]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT q.*, c.code AS course_code, c.name AS course_name,
                      a.status AS attempt_status, a.score
               FROM quizzes q
               JOIN courses c ON q.course_id = c.id
               JOIN student_enrollments e ON e.course_id = c.id AND e.student_id = ?
               LEFT JOIN quiz_attempts a ON a.quiz_id = q.id AND a.student_id = ?
               ORDER BY q.start_time DESC""",
            (sid, sid),
        ).fetchall()
        return jsonify(rows_to_list(rows))


@student_bp.route("/quizzes/<int:qid>", methods=["GET"])
@require_roles("student")
def quiz_detail(user, qid):
    sid = user["student_id"]
    with get_db() as conn:
        quiz = conn.execute(
            """SELECT q.* FROM quizzes q
               JOIN student_enrollments e ON e.course_id = q.course_id
               WHERE q.id = ? AND e.student_id = ?""",
            (qid, sid),
        ).fetchone()
        if not quiz:
            return jsonify({"error": "Quiz not found or not enrolled."}), 404
        quiz = dict(quiz)
        if quiz_not_started(quiz["start_time"]):
            return jsonify({"error": "Quiz has not started yet."}), 403
        if quiz_ended(quiz["end_time"]):
            attempt = conn.execute(
                """SELECT * FROM quiz_attempts
                   WHERE quiz_id=? AND student_id=?""",
                (qid, sid),
            ).fetchone()
            if attempt and attempt["status"] in ("submitted", "auto_submitted"):
                return jsonify({
                    "quiz": get_quiz_full(conn, qid, hide_correct=True),
                    "attempt": dict(attempt),
                    "readonly": True,
                })
            return jsonify({"error": "Quiz has ended."}), 403

        full = get_quiz_full(conn, qid, hide_correct=True)
        for q in full["questions"]:
            for o in q["options"]:
                o.pop("is_correct", None)
        return jsonify({"quiz": full})


@student_bp.route("/quizzes/<int:qid>/start", methods=["POST"])
@require_roles("student")
def start_quiz(user, qid):
    attempt, err = start_student_attempt(user["student_id"], qid)
    if err:
        return jsonify({"error": err}), 400
    with get_db() as conn:
        quiz = get_quiz_full(conn, qid, hide_correct=True)
        for q in quiz["questions"]:
            for o in q["options"]:
                o.pop("is_correct", None)
    started = datetime.fromisoformat(attempt["started_at"].replace("Z", ""))
    expires = started + timedelta(minutes=quiz["duration_minutes"])
    return jsonify({
        "attempt": dict(attempt),
        "quiz": quiz,
        "expires_at": expires.isoformat(),
    })


@student_bp.route("/attempts/<int:aid>/submit", methods=["POST"])
@require_roles("student")
def submit_quiz(user, aid):
    data = request.get_json() or {}
    result, err = submit_attempt(
        aid,
        user["student_id"],
        data.get("answers", []),
        auto=data.get("auto_submit", False),
    )
    if err:
        return jsonify({"error": err}), 400
    return jsonify(result)


@student_bp.route("/attempts/<int:aid>", methods=["GET"])
@require_roles("student")
def get_attempt(user, aid):
    with get_db() as conn:
        attempt = conn.execute(
            """SELECT a.*, q.title, q.duration_minutes
               FROM quiz_attempts a JOIN quizzes q ON a.quiz_id = q.id
               WHERE a.id = ? AND a.student_id = ?""",
            (aid, user["student_id"]),
        ).fetchone()
        if not attempt:
            return jsonify({"error": "Not found"}), 404
        return jsonify(dict(attempt))
