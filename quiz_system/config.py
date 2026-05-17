import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("QUIZ_DB_PATH", os.path.join(BASE_DIR, "apexai_quiz.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", "apexai-quiz-secret-key-change-in-production")
SESSION_COOKIE_NAME = "apexai_quiz_session"
SESSION_LIFETIME_DAYS = 7
