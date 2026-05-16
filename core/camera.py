import cv2
import time

class CameraTracker:
    def __init__(self, config):
        camera_cfg = config.get("camera", {})
        self.source = camera_cfg.get("source", 0)
        self.width = camera_cfg.get("width", 640)
        self.height = camera_cfg.get("height", 480)
        self.fps = camera_cfg.get("fps", 30)
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera source {self.source}")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
    def read_frame(self):
        if not self.cap:
            return False, None
        return self.cap.read()

    def stop(self):
        if self.cap:
            self.cap.release()
            self.cap = None
