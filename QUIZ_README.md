# APEXAI Quiz Management System

Role-based quiz platform for **Admin**, **Lecturer**, and **Student** users. Built with **Python Flask** (API + pages) and **vanilla HTML, CSS, and JavaScript** — no React, Node.js, or npm required.

## Features

- Secure password hashing (Werkzeug)
- Role-based access control on routes and APIs
- Admin: manage courses, semesters, users, allocations, enrollments, view all quizzes
- Lecturer: create MCQ quizzes for assigned courses only, view submissions
- Student: attempt active quizzes with countdown timer and auto-submit on timeout
- Normalized SQLite schema with foreign keys and cascade rules

## Quick start

### 1. Python environment

```bash
cd ApexAI
python -m venv .venv_quiz
.venv_quiz\Scripts\activate
pip install -r quiz_requirements.txt
```

### 2. Run the server

```bash
python run_quiz.py
```

Open **http://localhost:5001** in your browser.

### 3. Demo accounts

| Role     | Email                   | Password      |
|----------|-------------------------|---------------|
| Admin    | admin@apexai.edu        | Admin@123     |
| Lecturer | lecturer1@apexai.edu    | Lecturer@123  |
| Student  | student1@apexai.edu     | Student@123   |

## Project structure

```
ApexAI/
  run_quiz.py                 # Entry point
  quiz_requirements.txt       # Python dependencies
  apexai_quiz.db              # SQLite database (created on first run)
  quiz_system/
    app.py                    # Flask app + page routes
    auth.py                   # Session auth helpers
    validators.py             # Business rule validation
    database/
      schema.sql
      db.py
      seed.py
    routes/                   # REST API (admin, lecturer, student, auth)
    services/
    static/
      css/app.css
      js/api.js, ui.js, admin.js, lecturer.js, student.js, take_quiz.js
    templates/
      login.html, admin.html, lecturer.html, student.html, take_quiz.html
```

## Reset database

Delete `apexai_quiz.db` and run `python run_quiz.py` again to re-seed.

## Notes

- The proctoring system (`app.py` on port 5000) is separate from this quiz app (port 5001).
- Sessions persist via Flask signed cookies (7 days by default).
