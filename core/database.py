import sqlite3
import os
import uuid
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'apexai.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema and seed predefined users."""
    conn = get_db()
    c = conn.cursor()

    # Classes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id   TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            semester INTEGER NOT NULL
        )
    ''')

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'student',
            class_id   TEXT REFERENCES classes(id)
        )
    ''')

    # Exam sessions table (one row per proctoring run)
    c.execute('''
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id          TEXT PRIMARY KEY,
            user_id     TEXT REFERENCES users(id),
            started_at  TEXT NOT NULL,
            ended_at    TEXT,
            final_score REAL DEFAULT 0,
            verdict     TEXT DEFAULT 'Normal'
        )
    ''')

    # Anomaly events table
    c.execute('''
        CREATE TABLE IF NOT EXISTS anomaly_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT REFERENCES exam_sessions(id),
            event_type  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            screenshot  TEXT
        )
    ''')

    conn.commit()

    # ----- Seed classes -----
    classes = [
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'cs-sem1-prog')),   'Programming Fundamentals', 'Programming',     1),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'cs-sem1-math')),   'Calculus I',               'Mathematics',      1),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'cs-sem2-oop')),    'Object Oriented Programming','OOP',            2),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'cs-sem3-ds')),     'Data Structures',          'Data Structures',  3),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'cs-sem4-ai')),     'Artificial Intelligence',  'AI',               4),
    ]
    c.executemany('INSERT OR IGNORE INTO classes VALUES (?,?,?,?)', classes)

    # ----- Seed users -----
    def pw(plain): return hashlib.sha256(plain.encode()).hexdigest()

    sem1_prog_id = classes[0][0]
    sem1_math_id = classes[1][0]
    sem2_oop_id  = classes[2][0]
    sem3_ds_id   = classes[3][0]
    sem4_ai_id   = classes[4][0]

    users = [
        # Admins
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'admin-001')),  'Dr. Ahmed Khan',    'admin@apexai.edu',    pw('admin123'),   'admin',   None),

        # Semester 1 – Programming
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s1-001')), 'Ali Hassan',        'ali.s1@apexai.edu',   pw('pass1234'),   'student', sem1_prog_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s1-002')), 'Sara Malik',        'sara.s1@apexai.edu',  pw('pass1234'),   'student', sem1_prog_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s1-003')), 'Usman Raza',        'usman.s1@apexai.edu', pw('pass1234'),   'student', sem1_prog_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s1-004')), 'Ayesha Noor',       'ayesha.s1@apexai.edu',pw('pass1234'),   'student', sem1_prog_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s1-005')), 'Bilal Ahmed',       'bilal.s1@apexai.edu', pw('pass1234'),   'student', sem1_prog_id),

        # Semester 1 – Math
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-m1-001')), 'Hira Khan',         'hira.m1@apexai.edu',  pw('pass1234'),   'student', sem1_math_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-m1-002')), 'Zain Ali',          'zain.m1@apexai.edu',  pw('pass1234'),   'student', sem1_math_id),

        # Semester 2 – OOP
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s2-001')), 'Fatima Shah',       'fatima.s2@apexai.edu',pw('pass1234'),   'student', sem2_oop_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s2-002')), 'Hamza Butt',        'hamza.s2@apexai.edu', pw('pass1234'),   'student', sem2_oop_id),

        # Semester 3 – DS
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s3-001')), 'Amna Qureshi',      'amna.s3@apexai.edu',  pw('pass1234'),   'student', sem3_ds_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s3-002')), 'Saad Tariq',        'saad.s3@apexai.edu',  pw('pass1234'),   'student', sem3_ds_id),

        # Semester 4 – AI
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s4-001')), 'Nadia Iqbal',       'nadia.s4@apexai.edu', pw('pass1234'),   'student', sem4_ai_id),
        (str(uuid.uuid5(uuid.NAMESPACE_DNS, 'std-s4-002')), 'Omar Farooq',       'omar.s4@apexai.edu',  pw('pass1234'),   'student', sem4_ai_id),
    ]
    c.executemany('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', users)

    conn.commit()
    conn.close()
    print("[DB] Database initialized and seeded.")

def get_user_by_email(email):
    conn = get_db()
    row = conn.execute(
        '''SELECT u.*, c.name AS class_name, c.course, c.semester
           FROM users u LEFT JOIN classes c ON u.class_id = c.id
           WHERE u.email = ?''', (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        '''SELECT u.*, c.name AS class_name, c.course, c.semester
           FROM users u LEFT JOIN classes c ON u.class_id = c.id
           WHERE u.id = ?''', (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def create_exam_session(user_id):
    import datetime
    session_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute('INSERT INTO exam_sessions VALUES (?,?,?,?,?,?)',
                 (session_id, user_id, now, None, 0.0, 'Normal'))
    conn.commit()
    conn.close()
    return session_id

def close_exam_session(session_id, final_score, verdict):
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute('UPDATE exam_sessions SET ended_at=?, final_score=?, verdict=? WHERE id=?',
                 (now, final_score, verdict, session_id))
    conn.commit()
    conn.close()

def log_anomaly_event(session_id, event_type, screenshot=None):
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute('INSERT INTO anomaly_events (session_id, event_type, timestamp, screenshot) VALUES (?,?,?,?)',
                 (session_id, event_type, now, screenshot))
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = get_db()
    rows = conn.execute(
        '''SELECT es.*, u.name AS user_name, u.email,
                  c.name AS class_name, c.course, c.semester
           FROM exam_sessions es
           JOIN users u ON es.user_id = u.id
           LEFT JOIN classes c ON u.class_id = c.id
           ORDER BY es.started_at DESC'''
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_session_events(session_id):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM anomaly_events WHERE session_id=? ORDER BY timestamp',
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
