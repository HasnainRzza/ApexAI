from datetime import timedelta

from flask import Blueprint, jsonify, request, session

from quiz_system.auth import get_current_user, login_user
from quiz_system.config import SESSION_LIFETIME_DAYS

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "")
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user, err = login_user(email, password)
    if err:
        return jsonify({"error": err}), 401

    session.permanent = True
    session["user_id"] = user["id"]
    session["role"] = user["role_name"]
    return jsonify({"user": user, "message": "Login successful."})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@auth_bp.route("/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": user})
