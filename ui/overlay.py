import cv2

class UIOverlay:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        
    def draw(self, frame, state_dict, score_dict, obj_results):
        h, w, _ = frame.shape
        
        # Draw detected objects
        for obj in obj_results.get("detected", []):
            x1, y1, x2, y2 = obj["bbox"]
            label = f"{obj['class']} {obj['conf']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, label, (x1, max(y1 - 10, 0)), self.font, 0.5, (0, 0, 255), 1)

        # Draw left dashboard background
        cv2.rectangle(frame, (0, 0), (280, 260), (0, 0, 0), -1) # Background
        # Opacity can be added using addWeighted if desired, but keeping it simple for CPU
        
        # Display Status Lines
        y_offset = 25
        line_spacing = 25
        
        def put_line(text, color=(255, 255, 255)):
            nonlocal y_offset
            cv2.putText(frame, text, (10, y_offset), self.font, 0.6, color, 1)
            y_offset += line_spacing

        # Anomaly Score
        score = score_dict["score"]
        severity = score_dict["severity"]
        score_color = (0, 255, 0)
        if severity == "Warning":
            score_color = (0, 255, 255)
        elif severity == "Critical" or severity == "CHEATING":
            score_color = (0, 0, 255)
            
        put_line(f"Anomaly Score: {score:.1f}", score_color)
        put_line(f"Severity: {severity}", score_color)
        
        if severity == "CHEATING":
            cv2.putText(frame, "!!! CHEATING DETECTED !!!", (w // 2 - 150, 50), self.font, 1.0, (0, 0, 255), 3)
        
        # State signals
        put_line(f"Face Present: {not state_dict['face_missing']}", (0, 255, 0) if not state_dict['face_missing'] else (0, 0, 255))
        put_line(f"Multi Face: {state_dict['multiple_faces']}", (0, 0, 255) if state_dict['multiple_faces'] else (0, 255, 0))
        
        pose_anom = state_dict['head_pose_anomaly']
        head_dir = state_dict.get('head_dir_text', 'HEAD_CENTER/HEAD_CENTER')
        put_line(f"Head: {head_dir}", (0, 0, 255) if pose_anom else (0, 255, 0))
        
        gaze_anom = state_dict['gaze_anomaly']
        gaze_dir = state_dict.get('gaze_dir_text', 'EYE_CENTER/EYE_CENTER')
        put_line(f"Gaze: {gaze_dir}", (0, 0, 255) if gaze_anom else (0, 255, 0))
        
        audio_anom = state_dict['audio_anomaly']
        put_line(f"Audio: {'Anomaly' if audio_anom else 'Normal'}", (0, 0, 255) if audio_anom else (0, 255, 0))
        
        obj_anom = state_dict['object_detected']
        put_line(f"Suspicious Obj: {'Yes' if obj_anom else 'No'}", (0, 0, 255) if obj_anom else (0, 255, 0))

        browser_anom = state_dict['browser_violation']
        put_line(f"Browser Violation: {'Yes' if browser_anom else 'No'}", (0, 0, 255) if browser_anom else (0, 255, 0))

        return frame
