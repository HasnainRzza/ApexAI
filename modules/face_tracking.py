import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class MockLandmarkList:
    def __init__(self, landmarks):
        self.landmark = landmarks

class FaceTracker:
    def __init__(self, config):
        cfg = config.get("face_tracking", {})
        self.min_detection_confidence = cfg.get("min_detection_confidence", 0.5)
        self.min_tracking_confidence = cfg.get("min_tracking_confidence", 0.5)
        self.max_faces = cfg.get("max_faces", 1)
        
        base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=self.max_faces,
            min_face_detection_confidence=self.min_detection_confidence,
            min_face_presence_confidence=self.min_tracking_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
        
    def process(self, frame_rgb):
        """
        Process the RGB frame and return a dict of face tracking states.
        """
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = self.face_landmarker.detect(mp_image)
        
        state = {
            "face_present": False,
            "multiple_faces": False,
            "num_faces": 0,
            "landmarks": None # Return landmarks for the primary face
        }
        
        if results.face_landmarks and len(results.face_landmarks) > 0:
            state["num_faces"] = len(results.face_landmarks)
            state["face_present"] = state["num_faces"] > 0
            state["multiple_faces"] = state["num_faces"] > 1
            # We'll use the first detected face's landmarks for pose/gaze
            # Wrap it in MockLandmarkList to keep compatibility with existing code
            state["landmarks"] = MockLandmarkList(results.face_landmarks[0])
            
        return state
        
    def close(self):
        self.face_landmarker.close()
