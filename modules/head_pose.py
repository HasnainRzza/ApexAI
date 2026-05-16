import cv2
import numpy as np

class HeadPoseEstimator:
    def __init__(self, config):
        cfg = config.get("head_pose", {})
        self.dx_thresh_left = -0.25
        self.dx_thresh_right = 0.25
        self.dy_thresh_up = -0.18
        self.dy_thresh_down = 0.18
        
    def _pt(self, lm, i, w, h):
        return np.array([lm[i].x * w, lm[i].y * h])

    def estimate(self, image_shape, face_landmarks):
        h, w, _ = image_shape
        lm = face_landmarks.landmark
        
        nose = self._pt(lm, 1, w, h)
        left_eye = self._pt(lm, 33, w, h)
        right_eye = self._pt(lm, 263, w, h)
        
        center = (left_eye + right_eye) / 2
        dx = nose[0] - center[0]
        dy = nose[1] - center[1]

        face_width = np.linalg.norm(right_eye - left_eye) + 1e-6

        dx /= face_width
        dy /= face_width

        if dx < self.dx_thresh_left:
            h_dir = "HEAD_LEFT"
        elif dx > self.dx_thresh_right:
            h_dir = "HEAD_RIGHT"
        else:
            h_dir = "HEAD_CENTER"

        if dy < self.dy_thresh_up:
            v_dir = "HEAD_UP"
        elif dy > self.dy_thresh_down:
            v_dir = "HEAD_DOWN"
        else:
            v_dir = "HEAD_CENTER"

        anomaly = (h_dir != "HEAD_CENTER" or v_dir != "HEAD_CENTER")
        
        return {
            "h_dir": h_dir,
            "v_dir": v_dir,
            "dx": dx,
            "dy": dy,
            "pitch": dy, 
            "yaw": dx,   
            "roll": 0,
            "anomaly": anomaly
        }
