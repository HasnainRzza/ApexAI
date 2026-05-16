import cv2
import time
import sys
import os

from core.config_loader import load_config
from core.camera import CameraTracker
from modules.face_tracking import FaceTracker
from modules.head_pose import HeadPoseEstimator
from modules.gaze_estimation import GazeEstimator
from modules.object_detection import ObjectDetector
from modules.audio_anomaly import AudioMonitor
from modules.browser_monitor import BrowserMonitor
from modules.temporal_engine import TemporalEngine
from ui.overlay import UIOverlay

def main():
    print("[INFO] Loading configuration...")
    try:
        config = load_config("config.yaml")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print("[INFO] Initializing modules...")
    camera = CameraTracker(config)
    face_tracker = FaceTracker(config)
    head_pose_est = HeadPoseEstimator(config)
    gaze_est = GazeEstimator(config)
    object_detector = ObjectDetector(config)
    audio_monitor = AudioMonitor(config)
    browser_monitor = BrowserMonitor(config)
    temporal_engine = TemporalEngine(config)
    overlay = UIOverlay()

    print("[INFO] Starting background threads...")
    object_detector.start()
    audio_monitor.start()
    browser_monitor.start()

    print("[INFO] Opening camera...")
    camera.start()

    print("[INFO] System ready. Press 'q' to quit.")
    
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        
    screenshots_taken = {
        "object_detected": False,
        "browser_violation": False,
        "multiple_faces": False,
        "face_missing": False,
        "cheating": False
    }
    
    frame_count = 0
    obj_detect_skip = config.get("object_detection", {}).get("frame_skip", 10)
    
    system_start_time = time.time()

    try:
        while True:
            ret, frame = camera.read_frame()
            if not ret:
                print("[WARNING] Could not read from camera. Retrying...")
                time.sleep(0.1)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape

            # 1. Face Tracking
            face_state = face_tracker.process(frame_rgb)
            
            # 2. Head Pose & 3. Gaze
            pose_state = {"pitch": 0, "yaw": 0, "roll": 0, "dy": 0.0, "anomaly": False}
            gaze_state = {"h_ratio": 0, "v_ratio": 0, "direction": "Unknown", "anomaly": False}
            
            if face_state["face_present"] and face_state["landmarks"] is not None:
                pose_state = head_pose_est.estimate((h, w, 3), face_state["landmarks"])
                head_pitch = pose_state.get("dy", 0.0)
                gaze_state = gaze_est.estimate((h, w, 3), face_state["landmarks"], head_pitch=head_pitch)

            # 4. Object Detection (Update frame)
            frame_count += 1
            if frame_count % obj_detect_skip == 0:
                object_detector.update_frame(frame)
            obj_results = object_detector.get_results()

            # 5. Audio Monitor
            audio_results = audio_monitor.get_results()

            # 6. Browser Monitor
            browser_results = browser_monitor.get_results()

            # Aggregate States
            h_dir = pose_state.get("h_dir", "HEAD_CENTER")
            v_dir = pose_state.get("v_dir", "HEAD_CENTER")
            gaze_dir_split = gaze_state.get("direction", "EYE_CENTER/EYE_CENTER").split('/')
            e_dir = gaze_dir_split[0] if len(gaze_dir_split) > 0 else "EYE_CENTER"
            e_v = gaze_dir_split[1] if len(gaze_dir_split) > 1 else "EYE_CENTER"

            current_state = {
                "face_missing": not face_state["face_present"],
                "multiple_faces": face_state["multiple_faces"],
                "head_pose_anomaly": pose_state["anomaly"],
                "gaze_anomaly": gaze_state["anomaly"],
                "head_dir_text": f"{h_dir}/{v_dir}",
                "gaze_dir_text": f"{e_dir}/{e_v}",
                "object_detected": obj_results["anomaly"],
                "audio_anomaly": audio_results["anomaly"],
                "browser_violation": browser_results["browser_violation"]
            }

            # 7. Temporal Engine
            score_dict = temporal_engine.update(current_state)

            # 8. UI Overlay
            display_frame = overlay.draw(frame, current_state, score_dict, obj_results)

            # Wait 10 seconds before activating screenshot mechanism
            if time.time() - system_start_time > 10.0:
                # Take ONE proof screenshot per allowed anomaly type
                for key in ["object_detected", "browser_violation", "multiple_faces", "face_missing"]:
                    if current_state.get(key, False) and not screenshots_taken[key]:
                        filename = f"screenshots/{key}_{int(time.time())}.jpg"
                        cv2.imwrite(filename, display_frame)
                        print(f"[ALERT] Proof captured for {key}: {filename}")
                        screenshots_taken[key] = True

                if score_dict.get("is_cheating") and not screenshots_taken["cheating"]:
                    filename = f"screenshots/cheating_confirmed_{int(time.time())}.jpg"
                    cv2.imwrite(filename, display_frame)
                    print(f"[ALERT] Proof captured for CHEATING: {filename}")
                    screenshots_taken["cheating"] = True

            cv2.imshow("ApexAI Proctoring Dashboard", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("[INFO] Interrupted by user.")
    except Exception as e:
        print(f"[ERROR] Main loop error: {e}")
    finally:
        print("[INFO] Shutting down...")
        camera.stop()
        face_tracker.close()
        object_detector.stop()
        audio_monitor.stop()
        browser_monitor.stop()
        cv2.destroyAllWindows()
        print("[INFO] Shutdown complete.")

if __name__ == "__main__":
    main()
