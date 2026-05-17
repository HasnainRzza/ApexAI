import os
from datetime import timedelta

from flask import Flask, redirect, render_template, request, session, url_for

from quiz_system.auth import get_current_user
from quiz_system.config import BASE_DIR, SECRET_KEY, SESSION_COOKIE_NAME, SESSION_LIFETIME_DAYS
from quiz_system.database.seed import seed
from quiz_system.routes import register_blueprints

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static", template_folder=TEMPLATE_DIR)
    app.secret_key = SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=SESSION_LIFETIME_DAYS)
    app.config["SESSION_COOKIE_NAME"] = SESSION_COOKIE_NAME
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    register_blueprints(app)

    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "APEXAI Quiz Management"}

    def role_home(role):
        return {
            "admin": "admin_page",
            "lecturer": "lecturer_page",
            "student": "student_page",
        }.get(role, "login_page")

    @app.route("/")
    def index():
        user = get_current_user()
        if user:
            return redirect(url_for(role_home(user["role_name"])))
        return redirect(url_for("login_page"))

    @app.route("/login")
    def login_page():
        if request.args.get("logout"):
            session.clear()
        user = get_current_user()
        return render_template("login.html", current_user=user)

    @app.route("/logout")
    def logout_page():
        session.clear()
        return redirect(url_for("login_page"))

    @app.route("/admin")
    def admin_page():
        user = get_current_user()
        if not user or user["role_name"] != "admin":
            return redirect(url_for("login_page"))
        return render_template("admin.html", user=user)

    @app.route("/lecturer")
    def lecturer_page():
        user = get_current_user()
        if not user or user["role_name"] != "lecturer":
            return redirect(url_for("login_page"))
        return render_template("lecturer.html", user=user)

    @app.route("/student")
    def student_page():
        user = get_current_user()
        if not user or user["role_name"] != "student":
            return redirect(url_for("login_page"))
        return render_template("student.html", user=user)

    @app.route("/student/quiz/<int:quiz_id>")
    def take_quiz_page(quiz_id):
        user = get_current_user()
        if not user or user["role_name"] != "student":
            return redirect(url_for("login_page"))
        return render_template("take_quiz.html", user=user, quiz_id=quiz_id)

    return app


app = create_app()

if __name__ == "__main__":
    seed()
    print("[APEXAI Quiz] http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
