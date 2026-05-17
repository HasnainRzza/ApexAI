from datetime import datetime, timedelta

from quiz_system.database.db import get_db
from quiz_system.validators import normalize_datetime_str, now_local, validate_questions


def lecturer_assigned_to_course(conn, lecturer_id, course_id):
    row = conn.execute(
        """SELECT 1 FROM course_lecturer_allocations
           WHERE lecturer_id = ? AND course_id = ?""",
        (lecturer_id, course_id),
    ).fetchone()
    return row is not None


def student_enrolled_in_course(conn, student_id, course_id):
    row = conn.execute(
        """SELECT 1 FROM student_enrollments
           WHERE student_id = ? AND course_id = ?""",
        (student_id, course_id),
    ).fetchone()
    return row is not None


def create_quiz_with_questions(lecturer_id, data):
    err = validate_questions(data.get("questions", []))
    if err:
        return None, err

    with get_db() as conn:
        course_id = data["course_id"]
        if not lecturer_assigned_to_course(conn, lecturer_id, course_id):
            return None, "You are not assigned to this course."

        cur = conn.execute(
            """INSERT INTO quizzes
               (course_id, lecturer_id, title, start_time, end_time,
                duration_minutes, allow_multiple_attempts)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                course_id,
                lecturer_id,
                data["title"].strip(),
                normalize_datetime_str(data["start_time"]),
                normalize_datetime_str(data["end_time"]),
                int(data["duration_minutes"]),
                1 if data.get("allow_multiple_attempts") else 0,
            ),
        )
        quiz_id = cur.lastrowid
        _insert_questions(conn, quiz_id, data["questions"])
        return quiz_id, None


def _insert_questions(conn, quiz_id, questions):
    for i, q in enumerate(questions):
        cur = conn.execute(
            "INSERT INTO questions (quiz_id, statement, sort_order) VALUES (?, ?, ?)",
            (quiz_id, q["statement"].strip(), i),
        )
        qid = cur.lastrowid
        for j, opt in enumerate(q["options"]):
            text = (opt.get("text") or opt.get("option_text") or "").strip()
            conn.execute(
                """INSERT INTO question_options
                   (question_id, option_text, is_correct, sort_order)
                   VALUES (?, ?, ?, ?)""",
                (qid, text, 1 if opt.get("is_correct") else 0, j),
            )


def get_quiz_full(conn, quiz_id, hide_correct=False):
    quiz = conn.execute(
        """SELECT q.*, c.name AS course_name, c.code AS course_code
           FROM quizzes q JOIN courses c ON q.course_id = c.id
           WHERE q.id = ?""",
        (quiz_id,),
    ).fetchone()
    if not quiz:
        return None
    quiz = dict(quiz)
    questions = conn.execute(
        "SELECT * FROM questions WHERE quiz_id = ? ORDER BY sort_order",
        (quiz_id,),
    ).fetchall()
    result_q = []
    for q in questions:
        qd = dict(q)
        opts = conn.execute(
            "SELECT id, option_text, sort_order"
            + ("" if hide_correct else ", is_correct")
            + " FROM question_options WHERE question_id = ? ORDER BY sort_order",
            (q["id"],),
        ).fetchall()
        qd["options"] = [dict(o) for o in opts]
        result_q.append(qd)
    quiz["questions"] = result_q
    return quiz


def score_attempt(conn, attempt_id):
    answers = conn.execute(
        """SELECT qa.*, qo.is_correct AS option_correct
           FROM quiz_answers qa
           LEFT JOIN question_options qo ON qa.selected_option_id = qo.id
           WHERE qa.attempt_id = ?""",
        (attempt_id,),
    ).fetchall()
    correct = sum(1 for a in answers if a["option_correct"])
    total = conn.execute(
        """SELECT COUNT(*) AS cnt FROM questions q
           JOIN quiz_attempts a ON a.quiz_id = q.quiz_id
           WHERE a.id = ?""",
        (attempt_id,),
    ).fetchone()["cnt"]
    score = (correct / total * 100) if total else 0
    conn.execute(
        """UPDATE quiz_attempts SET score = ?, max_score = 100,
           status = 'submitted', submitted_at = ?
           WHERE id = ?""",
        (round(score, 2), now_local().strftime("%Y-%m-%d %H:%M:%S"), attempt_id),
    )
    return round(score, 2), total


def start_student_attempt(student_id, quiz_id):
    with get_db() as conn:
        quiz = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
        if not quiz:
            return None, "Quiz not found."
        if not student_enrolled_in_course(conn, student_id, quiz["course_id"]):
            return None, "You are not enrolled in this course."

        from quiz_system.validators import quiz_ended, quiz_not_started, quiz_is_active

        if quiz_not_started(quiz["start_time"]):
            return None, "Quiz has not started yet."
        if quiz_ended(quiz["end_time"]):
            return None, "Quiz has ended."
        if not quiz_is_active(quiz["start_time"], quiz["end_time"]):
            return None, "Quiz is not currently active."

        existing = conn.execute(
            """SELECT * FROM quiz_attempts
               WHERE quiz_id = ? AND student_id = ?""",
            (quiz_id, student_id),
        ).fetchone()
        if existing:
            if existing["status"] != "in_progress":
                if not quiz["allow_multiple_attempts"]:
                    return None, "You have already submitted this quiz."
            else:
                return dict(existing), None

        if existing and quiz["allow_multiple_attempts"]:
            pass
        elif existing:
            return dict(existing), None

        now = now_local().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """INSERT INTO quiz_attempts (quiz_id, student_id, started_at, status)
               VALUES (?, ?, ?, 'in_progress')""",
            (quiz_id, student_id, now),
        )
        attempt_id = cur.lastrowid
        questions = conn.execute(
            "SELECT id FROM questions WHERE quiz_id = ?", (quiz_id,)
        ).fetchall()
        for q in questions:
            conn.execute(
                "INSERT INTO quiz_answers (attempt_id, question_id) VALUES (?, ?)",
                (attempt_id, q["id"]),
            )
        return conn.execute(
            "SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)
        ).fetchone(), None


def submit_attempt(attempt_id, student_id, answers, auto=False):
    with get_db() as conn:
        attempt = conn.execute(
            "SELECT * FROM quiz_attempts WHERE id = ? AND student_id = ?",
            (attempt_id, student_id),
        ).fetchone()
        if not attempt:
            return None, "Attempt not found."
        if attempt["status"] != "in_progress":
            return None, "Quiz already submitted."

        quiz = conn.execute(
            "SELECT * FROM quizzes WHERE id = ?", (attempt["quiz_id"],)
        ).fetchone()
        from quiz_system.validators import quiz_ended

        if quiz_ended(quiz["end_time"]) and not auto:
            pass

        for ans in answers or []:
            qid = ans.get("question_id")
            oid = ans.get("selected_option_id")
            opt = conn.execute(
                "SELECT is_correct FROM question_options WHERE id = ? AND question_id = ?",
                (oid, qid),
            ).fetchone()
            conn.execute(
                """UPDATE quiz_answers SET selected_option_id = ?, is_correct = ?
                   WHERE attempt_id = ? AND question_id = ?""",
                (oid, 1 if opt and opt["is_correct"] else 0, attempt_id, qid),
            )

        status = "auto_submitted" if auto else "submitted"
        score, _ = score_attempt(conn, attempt_id)
        conn.execute(
            "UPDATE quiz_attempts SET status = ? WHERE id = ?",
            (status, attempt_id),
        )
        return {"score": score, "status": status}, None
