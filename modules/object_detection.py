import cv2
import threading
import time
from ultralytics import YOLO

class ObjectDetector:
    def __init__(self, config):
        cfg = config.get("object_detection", {})
        model_path = cfg.get("model_path", "yolov8n.pt")
        self.conf_thresh = cfg.get("confidence_threshold", 0.4)
        self.suspicious_classes = cfg.get("suspicious_classes", ["cell phone", "book", "laptop", "remote"])
        
        # We load the model. Ultralytics automatically downloads the model if not present.
        self.model = YOLO(model_path)
        
        self.running = True
        self.current_frame = None
        self.latest_results = []
        self.anomaly = False
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        
    def start(self):
        self.thread.start()
        
    def update_frame(self, frame):
        """
        Pass the latest frame to the detector.
        """
        with self.lock:
            # Copy to avoid concurrent modification issues if needed
            self.current_frame = frame.copy() if frame is not None else None
            
    def get_results(self):
        with self.lock:
            return {
                "detected": self.latest_results,
                "anomaly": self.anomaly
            }
            
    def _process_loop(self):
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.current_frame is not None:
                    frame_to_process = self.current_frame
                    self.current_frame = None # Consume the frame
            
            if frame_to_process is not None:
                # Run inference
                results = self.model(frame_to_process, verbose=False, conf=self.conf_thresh)
                detected_suspicious = []
                is_anomaly = False
                
                if results and len(results) > 0:
                    result = results[0]
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]
                        conf = float(box.conf[0])
                        
                        if class_name in self.suspicious_classes:
                            is_anomaly = True
                            detected_suspicious.append({
                                "class": class_name,
                                "conf": conf,
                                "bbox": box.xyxy[0].cpu().numpy().astype(int).tolist()
                            })
                            
                with self.lock:
                    self.latest_results = detected_suspicious
                    self.anomaly = is_anomaly
            else:
                time.sleep(0.01) # Avoid tight loop if no frame
                
    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
