from functools import wraps

from flask import jsonify, session
from werkzeug.security import check_password_hash

from quiz_system.database.db import get_db


def login_user(email, password):
    with get_db() as conn:
        user = conn.execute(
            """SELECT u.*, r.name AS role_name
               FROM users u JOIN roles r ON u.role_id = r.id
               WHERE u.email = ? AND u.is_active = 1""",
            (email.strip().lower(),),
        ).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return None, "Invalid email or password."
        profile = _load_profile(conn, user)
        return profile, None


def _load_profile(conn, user):
    data = dict(user)
    data.pop("password_hash", None)
    if user["role_name"] == "lecturer":
        lec = conn.execute(
            "SELECT id, employee_code FROM lecturers WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        data["lecturer_id"] = lec["id"] if lec else None
    elif user["role_name"] == "student":
        st = conn.execute(
            "SELECT id, student_code FROM students WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        data["student_id"] = st["id"] if st else None
    return data


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with get_db() as conn:
        user = conn.execute(
            """SELECT u.*, r.name AS role_name
               FROM users u JOIN roles r ON u.role_id = r.id
               WHERE u.id = ? AND u.is_active = 1""",
            (uid,),
        ).fetchone()
        if not user:
            return None
        return _load_profile(conn, user)


def require_roles(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user["role_name"] not in roles:
                return jsonify({"error": "Forbidden"}), 403
            return fn(user, *args, **kwargs)

        return wrapper

    return decorator
