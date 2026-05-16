import time

class TemporalEngine:
    def __init__(self, config):
        cfg = config.get("temporal_engine", {})
        self.window_size = cfg.get("window_size_seconds", 10)
        self.decay_rate = cfg.get("score_decay_rate", 0.95)
        self.weights = cfg.get("weights", {
            "face_missing": 10,
            "multiple_faces": 20,
            "head_pose_anomaly": 5,
            "gaze_anomaly": 5,
            "object_detected": 15,
            "audio_anomaly": 5,
            "browser_violation": 25
        })
        self.thresh_warning = cfg.get("threshold_warning", 50)
        self.thresh_critical = cfg.get("threshold_critical", 80)
        
        self.history = []
        self.current_score = 0.0
        
    def update(self, state_dict):
        """
        state_dict:
        {
            "face_missing": bool,
            "multiple_faces": bool,
            "head_pose_anomaly": bool,
            "gaze_anomaly": bool,
            "object_detected": bool,
            "audio_anomaly": bool,
            "browser_violation": bool
        }
        """
        now = time.time()
        self.history.append((now, state_dict))
        
        # Remove old events
        self.history = [item for item in self.history if now - item[0] <= self.window_size]
        
        # Calculate instant score for the current frame
        instant_score = 0
        for key, active in state_dict.items():
            if active:
                instant_score += self.weights.get(key, 0)
                
        # Apply decay to previous score and add instant score
        self.current_score = (self.current_score * self.decay_rate) + (instant_score * (1.0 - self.decay_rate))
        
        # Alternatively, for a simple sliding window sum:
        # sliding_score = 0
        # for ts, states in self.history:
        #     for key, active in states.items():
        #         if active: sliding_score += self.weights.get(key, 0)
        # self.current_score = min(100, sliding_score / (len(self.history) + 1e-5)) # normalize
        
        # Keep score bounded
        self.current_score = min(100.0, max(0.0, self.current_score))
        
        # Check if score crosses 35
        if self.current_score > 35.0 and not hasattr(self, 'was_above_35'):
            self.was_above_35 = False
            self.above_35_count = getattr(self, 'above_35_count', 0)
            self.is_cheating = getattr(self, 'is_cheating', False)
            
        if hasattr(self, 'was_above_35'):
            if self.current_score > 35.0 and not self.was_above_35:
                self.above_35_count += 1
                self.was_above_35 = True
            elif self.current_score <= 35.0:
                self.was_above_35 = False
                
            if self.above_35_count >= 2:
                self.is_cheating = True
        
        severity = "Normal"
        if getattr(self, 'is_cheating', False):
            severity = "CHEATING"
        elif self.current_score >= self.thresh_critical:
            severity = "Critical"
        elif self.current_score >= self.thresh_warning:
            severity = "Warning"
            
        return {
            "score": self.current_score,
            "severity": severity,
            "is_cheating": getattr(self, 'is_cheating', False)
        }
