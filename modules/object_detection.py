import threading
import time
from ultralytics import YOLO


class SharedObjectDetector:
    """
    A single YOLO model instance shared across ALL user sessions.
    All frame submissions go into a queue; a single worker thread processes
    them sequentially to avoid GPU/CPU contention. Results are stored per-user.
    """

    def __init__(self, config):
        cfg = config.get("object_detection", {})
        model_path  = cfg.get("model_path", "yolov8n.pt")
        self.conf   = cfg.get("confidence_threshold", 0.4)
        self.classes = cfg.get("suspicious_classes", ["cell phone", "book", "laptop", "remote"])

        self.model  = YOLO(model_path)
        self._lock  = threading.Lock()

        # Per-user latest frame and results keyed by sid
        self._frames  = {}   # sid -> frame
        self._results = {}   # sid -> {"detected": [...], "anomaly": bool}

        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def update_frame(self, sid, frame):
        with self._lock:
            self._frames[sid] = frame.copy()

    def get_results(self, sid):
        with self._lock:
            return self._results.get(sid, {"detected": [], "anomaly": False})

    def remove_user(self, sid):
        with self._lock:
            self._frames.pop(sid, None)
            self._results.pop(sid, None)

    def _loop(self):
        while self._running:
            with self._lock:
                items = list(self._frames.items())
                self._frames.clear()

            if not items:
                time.sleep(0.02)
                continue

            for sid, frame in items:
                try:
                    results = self.model(frame, verbose=False, conf=self.conf)
                    detected = []
                    is_anomaly = False
                    if results:
                        for box in results[0].boxes:
                            class_name = self.model.names[int(box.cls[0])]
                            if class_name in self.classes:
                                is_anomaly = True
                                detected.append({
                                    "class": class_name,
                                    "conf":  float(box.conf[0]),
                                    "bbox":  box.xyxy[0].cpu().numpy().astype(int).tolist()
                                })
                    with self._lock:
                        self._results[sid] = {"detected": detected, "anomaly": is_anomaly}
                except Exception as e:
                    print(f"[ObjectDetector] Error for {sid}: {e}")

    def stop(self):
        self._running = False
        self._thread.join(timeout=3)
