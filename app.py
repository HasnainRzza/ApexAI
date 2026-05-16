import os
import base64
import hashlib
import numpy as np
import cv2
try:
    import webrtcvad
except ImportError:
    import webrtcvad_wheels as webrtcvad

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, disconnect

from core.config_loader import load_config
from core.database import init_db, get_user_by_email, get_user_by_id, get_all_sessions, get_session_events
from core.session import UserSession
from modules.object_detection import SharedObjectDetector

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'apexai-super-secret-key-2024')

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading',
                    max_http_buffer_size=5 * 1024 * 1024)  # 5MB for frames

# ---------------------------------------------------------------------------
# Global shared resources (loaded once, shared across all users)
# ---------------------------------------------------------------------------
config = load_config(os.path.join(BASE_DIR, 'config.yaml'))
object_detector = SharedObjectDetector(config)

# VAD is stateless between calls — safe to share
vad = webrtcvad.Vad(config.get("audio_anomaly", {}).get("vad_aggressiveness", 1))
SAMPLE_RATE = config.get("audio_anomaly", {}).get("sample_rate", 16000)

# Per-connected-user sessions: { socket_sid -> UserSession }
active_sessions: dict[str, UserSession] = {}

# ---------------------------------------------------------------------------
# Helper – wrap ObjectDetector to match UserSession interface
# ---------------------------------------------------------------------------
class _SidAdapter:
    """Adapts the shared detector to the per-user interface expected by UserSession."""
    def __init__(self, detector, sid):
        self._d   = detector
        self._sid = sid

    def update_frame(self, frame):
        self._d.update_frame(self._sid, frame)

    def get_results(self):
        return self._d.get_results(self._sid)


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    if user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('exam.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        pw_hash  = hashlib.sha256(password.encode()).hexdigest()

        user = get_user_by_email(email)
        if user and user['password'] == pw_hash:
            session['user_id'] = user['id']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        error = "Invalid email or password."
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
def admin_dashboard():
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user_by_id(session['user_id'])
    if not user or user['role'] != 'admin':
        return redirect(url_for('index'))
    sessions = get_all_sessions()
    return render_template('admin.html', admin=user, sessions=sessions)


@app.route('/admin/session/<session_id>')
def session_detail(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    admin = get_user_by_id(session['user_id'])
    if not admin or admin['role'] != 'admin':
        return redirect(url_for('index'))
    events = get_session_events(session_id)
    return render_template('session_detail.html', session_id=session_id, events=events, admin=admin)


@app.route('/screenshots/<path:filename>')
def screenshot(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'screenshots'), filename)


# ---------------------------------------------------------------------------
# Socket.IO events
# ---------------------------------------------------------------------------
@socketio.on('connect')
def on_connect():
    if 'user_id' not in session:
        disconnect()
        return

    user = get_user_by_id(session['user_id'])
    if not user:
        disconnect()
        return

    # Admins monitor via HTTP dashboard — no proctoring session needed
    if user['role'] == 'admin':
        return

    sid = request.sid
    adapter = _SidAdapter(object_detector, sid)
    user_session = UserSession(user['id'], user, config, adapter, sid)
    active_sessions[sid] = user_session

    print(f"[Connect] {user['name']} ({sid})")
    emit('connected', {
        'user':  user['name'],
        'class': user.get('class_name', ''),
        'course': user.get('course', ''),
        'semester': user.get('semester', ''),
        'exam_session': user_session.exam_session_id
    })


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    if sid in active_sessions:
        us = active_sessions.pop(sid)
        user_name = us.user_info.get('name', 'Unknown')
        us.close()
        object_detector.remove_user(sid)
        print(f"[Disconnect] {user_name} ({sid})")


@socketio.on('video_frame')
def on_video_frame(data):
    sid = request.sid
    us = active_sessions.get(sid)
    if not us:
        return

    try:
        # data['frame'] = 'data:image/jpeg;base64,...'
        b64 = data['frame'].split(',', 1)[-1]
        jpg  = base64.b64decode(b64)
        arr  = np.frombuffer(jpg, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        state, score = us.process_frame(frame)

        emit('state_update', {
            'score':    round(score.get('score', 0), 1),
            'severity': score.get('severity', 'Normal'),
            'is_cheating': score.get('is_cheating', False),
            'face_missing':      state['face_missing'],
            'multiple_faces':    state['multiple_faces'],
            'head_dir':          state['head_dir_text'],
            'gaze_dir':          state['gaze_dir_text'],
            'head_anomaly':      state['head_pose_anomaly'],
            'gaze_anomaly':      state['gaze_anomaly'],
            'object_detected':   state['object_detected'],
            'objects':           state.get('objects', []),
            'audio_anomaly':     state['audio_anomaly'],
            'browser_violation': state['browser_violation'],
        })

    except Exception as e:
        print(f"[video_frame] Error for {sid}: {e}")


@socketio.on('audio_chunk')
def on_audio_chunk(data):
    sid = request.sid
    us = active_sessions.get(sid)
    if not us:
        return
    try:
        pcm = bytes(data['pcm'])   # Int16 PCM bytes from browser
        us.process_audio_chunk(vad, pcm, SAMPLE_RATE)
    except Exception as e:
        print(f"[audio_chunk] Error for {sid}: {e}")


@socketio.on('browser_event')
def on_browser_event(data):
    sid = request.sid
    us = active_sessions.get(sid)
    if us:
        print(f"[Browser Event] {us.user_info['name']} -> {data.get('type')}")
        us.set_browser_event(data.get('type', ''))

@socketio.on('browser_screen_capture')
def on_browser_screen_capture(data):
    sid = request.sid
    us = active_sessions.get(sid)
    if us and 'frame' in data:
        us.save_browser_screen(data['frame'])


# ---------------------------------------------------------------------------
# API – admin endpoints (JSON)
# ---------------------------------------------------------------------------
@app.route('/api/sessions')
def api_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    admin = get_user_by_id(session['user_id'])
    if not admin or admin['role'] != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    return jsonify(get_all_sessions())


@app.route('/api/active_users')
def api_active_users():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    admin = get_user_by_id(session['user_id'])
    if not admin or admin['role'] != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    return jsonify([{
        'name':   s.user_info['name'],
        'email':  s.user_info['email'],
        'score':  round(s.latest_score.get('score', 0), 1),
        'severity': s.latest_score.get('severity', 'Normal'),
        'session_id': s.exam_session_id,
    } for s in active_sessions.values()])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    os.makedirs('screenshots', exist_ok=True)
    init_db()
    print("[INFO] Starting ApexAI Flask server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
