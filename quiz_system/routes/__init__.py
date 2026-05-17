from flask import Blueprint

from quiz_system.routes.admin import admin_bp
from quiz_system.routes.auth_routes import auth_bp
from quiz_system.routes.lecturer import lecturer_bp
from quiz_system.routes.student import student_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(lecturer_bp, url_prefix="/api/lecturer")
    app.register_blueprint(student_bp, url_prefix="/api/student")
