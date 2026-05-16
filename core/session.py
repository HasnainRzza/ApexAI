import threading
import time
import os
import cv2
import numpy as np
import base64

from modules.face_tracking import FaceTracker
from modules.head_pose import HeadPoseEstimator
from modules.gaze_estimation import GazeEstimator
from modules.temporal_engine import TemporalEngine
from core.database import create_exam_session, close_exam_session, log_anomaly_event


class UserSession:
    """
    Encapsulates the complete per-user proctoring state.
    Each connected student gets their own isolated instance of all AI modules.
    """

    def __init__(self, user_id, user_info, config, object_detector, sid):
        self.user_id = user_id
        self.user_info = user_info
        self.config = config
        self.sid = sid  # Socket.IO session ID

        # Per-user AI modules (each student gets independent state/smoothing)
        self.face_tracker   = FaceTracker(config)
        self.head_pose_est  = HeadPoseEstimator(config)
        self.gaze_est       = GazeEstimator(config)
        self.temporal_engine = TemporalEngine(config)

        # Shared YOLO detector (thread-safe singleton injected from app)
        self.object_detector = object_detector

        # Screenshot proof tracking (one per anomaly type per session)
        self.screenshots_taken = {
            "object_detected":  False,
            "browser_violation": False,
            "multiple_faces":   False,
            "face_missing":     False,
            "cheating":         False,
        }

        # Audio state (updated via process_audio_chunk)
        self._audio_lock   = threading.Lock()
        self._is_speech    = False
        self._audio_anomaly = False
        self._speech_start = None
        self._speech_threshold = config.get("audio_anomaly", {}).get("speech_threshold_seconds", 0.5)

        # Browser state
        self._browser_lock      = threading.Lock()
        self._browser_violation = False

        # Frame counter for object detection skip
        self._frame_count = 0
        self._obj_skip = config.get("object_detection", {}).get("frame_skip", 10)

        # Start timestamp for the 10-second grace period
        self.started_at = time.time()

        # Latest processed state (thread-safe read for emitting)
        self._state_lock  = threading.Lock()
        self.latest_state = {}
        self.latest_score = {}

        # Database exam session
        self.exam_session_id = create_exam_session(user_id)

        # Screenshots directory per user
        self.screenshot_dir = os.path.join("screenshots", self.exam_session_id)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Frame processing  (called from SocketIO event thread)
    # ------------------------------------------------------------------
    def process_frame(self, frame_bgr):
        """Run full detection pipeline on one BGR frame. Returns state dict."""
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # 1. Face Tracking
        face_state = self.face_tracker.process(frame_rgb)

        # 2. Head Pose & Gaze
        pose_state = {"pitch": 0, "dy": 0.0, "h_dir": "HEAD_CENTER", "v_dir": "HEAD_CENTER", "anomaly": False}
        gaze_state = {"h_ratio": 0.5, "direction": "EYE_CENTER/EYE_CENTER", "anomaly": False}

        if face_state["face_present"] and face_state["landmarks"]:
            pose_state = self.head_pose_est.estimate((h, w, 3), face_state["landmarks"])
            gaze_state = self.gaze_est.estimate((h, w, 3), face_state["landmarks"],
                                                head_pitch=pose_state.get("dy", 0.0))

        # 3. Object Detection (throttled)
        self._frame_count += 1
        if self._frame_count % self._obj_skip == 0:
            self.object_detector.update_frame(frame_bgr)
        obj_results = self.object_detector.get_results()

        # 4. Audio / Browser state (thread-safe reads)
        with self._audio_lock:
            audio_anomaly = self._audio_anomaly

        with self._browser_lock:
            browser_violation = self._browser_violation

        # 5. Aggregate
        h_dir = pose_state.get("h_dir", "HEAD_CENTER")
        v_dir = pose_state.get("v_dir", "HEAD_CENTER")
        gaze_parts = gaze_state.get("direction", "EYE_CENTER/EYE_CENTER").split("/")
        e_dir = gaze_parts[0] if gaze_parts else "EYE_CENTER"
        e_v   = gaze_parts[1] if len(gaze_parts) > 1 else "EYE_CENTER"

        current_state = {
            "face_missing":       not face_state["face_present"],
            "multiple_faces":     face_state["multiple_faces"],
            "head_pose_anomaly":  pose_state["anomaly"],
            "gaze_anomaly":       gaze_state["anomaly"],
            "head_dir_text":      f"{h_dir}/{v_dir}",
            "gaze_dir_text":      f"{e_dir}/{e_v}",
            "object_detected":    obj_results["anomaly"],
            "audio_anomaly":      audio_anomaly,
            "browser_violation":  browser_violation,
            "objects":            obj_results.get("detected", []),
        }

        # 6. Temporal engine
        score_dict = self.temporal_engine.update(current_state)

        # 7. Screenshot proof (after 10 s grace period)
        if time.time() - self.started_at > 10.0:
            self._maybe_screenshot(current_state, score_dict, frame_bgr)

        with self._state_lock:
            self.latest_state = current_state
            self.latest_score = score_dict

        return current_state, score_dict

    # ------------------------------------------------------------------
    # Audio chunk  (called from SocketIO audio_chunk event)
    # ------------------------------------------------------------------
    def process_audio_chunk(self, vad, pcm_bytes, sample_rate):
        try:
            is_active = vad.is_speech(pcm_bytes, sample_rate)
        except Exception:
            is_active = False

        with self._audio_lock:
            self._is_speech = is_active
            if is_active:
                if self._speech_start is None:
                    self._speech_start = time.time()
                elif time.time() - self._speech_start > self._speech_threshold:
                    self._audio_anomaly = True
            else:
                self._speech_start = None
                self._audio_anomaly = False

    # ------------------------------------------------------------------
    # Browser event  (called from SocketIO browser_event)
    # ------------------------------------------------------------------
    def set_browser_event(self, event_type):
        with self._browser_lock:
            if event_type in ("blur", "hidden", "fullscreen_exit"):
                self._browser_violation = True
            elif event_type in ("focus", "visible", "fullscreen_enter"):
                self._browser_violation = False

    def save_browser_screen(self, b64_frame):
        """Save the captured screen frame as evidence of browser violation."""
        try:
            # Only save once per session to prevent spam, or update to save multiple if needed.
            # Here we save it specifically as browser_screen.jpg
            path = os.path.join(self.screenshot_dir, "browser_screen.jpg")
            header, encoded = b64_frame.split(",", 1)
            data = base64.b64decode(encoded)
            with open(path, "wb") as f:
                f.write(data)
            
            # Explicitly log this as a browser violation proof
            log_anomaly_event(self.exam_session_id, "browser_violation", screenshot=path)
            self.screenshots_taken["browser_violation"] = True
            print(f"[ALERT] [{self.user_info['name']}] Screen capture saved: {path}")
        except Exception as e:
            print(f"[Session] Screen capture error: {e}")

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------
    def _maybe_screenshot(self, state, score, frame):
        for key in ("object_detected", "browser_violation", "multiple_faces", "face_missing"):
            if state.get(key) and not self.screenshots_taken[key]:
                path = os.path.join(self.screenshot_dir, f"{key}.jpg")
                cv2.imwrite(path, frame)
                self.screenshots_taken[key] = True
                log_anomaly_event(self.exam_session_id, key, screenshot=path)
                print(f"[ALERT] [{self.user_info['name']}] Screenshot: {path}")

        if score.get("is_cheating") and not self.screenshots_taken["cheating"]:
            path = os.path.join(self.screenshot_dir, "cheating_confirmed.jpg")
            cv2.imwrite(path, frame)
            self.screenshots_taken["cheating"] = True
            log_anomaly_event(self.exam_session_id, "cheating", screenshot=path)
            print(f"[ALERT] [{self.user_info['name']}] CHEATING confirmed — screenshot saved.")

    # ------------------------------------------------------------------
    # Cleanup on disconnect
    # ------------------------------------------------------------------
    def close(self):
        try:
            with self._state_lock:
                score = self.latest_score.get("score", 0)
                verdict = self.latest_score.get("severity", "Normal")
            close_exam_session(self.exam_session_id, score, verdict)
            self.face_tracker.close()
        except Exception as e:
            print(f"[Session] Close error: {e}")
