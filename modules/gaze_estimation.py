import numpy as np
from collections import deque
import time

class GazeEstimator:
    def __init__(self, config):
        cfg = config.get("gaze_estimation", {})
        
        self.smoothing = cfg.get("gaze_smoothing_frames", 5)
        self.gaze_buffer = deque(maxlen=self.smoothing)
        self.pitch_buffer = deque(maxlen=self.smoothing)

        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        self.out_of_center_start = None

    def _pt(self, lm, i, w, h):
        return np.array([lm[i].x * w, lm[i].y * h])

    def _iris_center(self, lm, ids, w, h):
        return np.mean([self._pt(lm, i, w, h) for i in ids], axis=0)

    def _eye_ratio(self, iris, left, right):
        return np.dot((iris - left), (right - left)) / (np.linalg.norm(right - left)**2 + 1e-6)

    def estimate(self, image_shape, face_landmarks, head_pitch=0.0):
        h, w, _ = image_shape
        lm = face_landmarks.landmark
        
        left_iris = self._iris_center(lm, self.LEFT_IRIS, w, h)
        right_iris = self._iris_center(lm, self.RIGHT_IRIS, w, h)

        left_l = self._pt(lm, 33, w, h)
        left_r = self._pt(lm, 133, w, h)

        right_l = self._pt(lm, 362, w, h)
        right_r = self._pt(lm, 263, w, h)

        l_g = self._eye_ratio(left_iris, left_l, left_r)
        r_g = self._eye_ratio(right_iris, right_l, right_r)

        raw_gaze = (l_g + r_g) / 2
        
        self.gaze_buffer.append(raw_gaze)
        self.pitch_buffer.append(head_pitch)
        
        gaze = np.mean(self.gaze_buffer)
        pitch = np.mean(self.pitch_buffer)

        if gaze < 0.40:
            e_dir = "EYE_RIGHT"
        elif gaze > 0.60:
            e_dir = "EYE_LEFT"
        else:
            e_dir = "EYE_CENTER"

        if pitch < -0.15:
            e_v = "EYE_UP"
        elif pitch > 0.20:
            e_v = "EYE_DOWN"
        else:
            e_v = "EYE_CENTER"

        is_centered = (e_dir == "EYE_CENTER" and e_v == "EYE_CENTER")
        
        if is_centered:
            self.out_of_center_start = None
            anomaly = False
        else:
            if self.out_of_center_start is None:
                self.out_of_center_start = time.time()
                
            if time.time() - self.out_of_center_start > 5.0:
                anomaly = True
            else:
                anomaly = False

        direction = f"{e_dir}/{e_v}"

        return {
            "h_ratio": gaze,
            "v_ratio": pitch,
            "direction": direction,
            "anomaly": anomaly
        }
