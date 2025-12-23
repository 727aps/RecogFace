import cv2
import face_recognition
import numpy as np
from typing import List, Tuple, Optional
import os

class FaceDetector:
    def __init__(self):
        self.face_net = None
        self.load_dnn_model()

    def load_dnn_model(self):
        """Load OpenCV DNN face detection model for improved accuracy"""
        try:
            model_path = os.path.join(os.path.dirname(__file__), 'models')
            os.makedirs(model_path, exist_ok=True)

            config_file = os.path.join(model_path, 'deploy.prototxt')
            model_file = os.path.join(model_path, 'res10_300x300_ssd_iter_140000.caffemodel')

            # Download models if they don't exist (simplified - in real implementation would use requests)
            if not os.path.exists(config_file) or not os.path.exists(model_file):
                # For demo purposes, we'll fall back to face_recognition only
                # In production, you'd download the models
                self.face_net = None
            else:
                self.face_net = cv2.dnn.readNetFromCaffe(config_file, model_file)

        except Exception as e:
            print(f"DNN model loading failed, using face_recognition only: {e}")
            self.face_net = None

    def detect_faces_hybrid(self, image: np.ndarray, confidence_threshold: float = 0.5) -> List[Tuple[int, int, int, int]]:
        """
        Hybrid face detection using OpenCV DNN + face_recognition
        Returns list of (x, y, w, h) bounding boxes
        """
        faces = []

        # Try DNN detection first for better accuracy
        if self.face_net is not None:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                           (300, 300), (104.0, 177.0, 123.0))
                self.face_net.setInput(blob)
                detections = self.face_net.forward()

                h, w = image.shape[:2]
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    if confidence > confidence_threshold:
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (x1, y1, x2, y2) = box.astype(int)
                        faces.append((x1, y1, x2 - x1, y2 - y1))
            except Exception as e:
                print(f"DNN detection failed: {e}")

        # Fall back to face_recognition if DNN fails or finds no faces
        if not faces:
            face_locations = face_recognition.face_locations(image, model="hog")
            for (top, right, bottom, left) in face_locations:
                faces.append((left, top, right - left, bottom - top))

        return faces

    def get_face_encodings(self, image: np.ndarray, face_locations: List[Tuple]) -> List[np.ndarray]:
        """Extract 128D face encodings using face_recognition"""
        encodings = []
        try:
            # Convert to RGB for face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Convert our (x,y,w,h) format to face_recognition (top,right,bottom,left) format
            face_recognition_locations = []
            for (x, y, w, h) in face_locations:
                face_recognition_locations.append((y, x + w, y + h, x))

            face_encodings = face_recognition.face_encodings(rgb_image, face_recognition_locations)
            encodings = face_encodings

        except Exception as e:
            print(f"Face encoding extraction failed: {e}")

        return encodings

    def detect_and_encode(self, image: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[np.ndarray]]:
        """Combined detection and encoding pipeline"""
        faces = self.detect_faces_hybrid(image)
        encodings = self.get_face_encodings(image, faces)
        return faces, encodings

    def get_face_landmarks(self, image: np.ndarray, face_location: Tuple[int, int, int, int]) -> Optional[dict]:
        """Extract facial landmarks for additional analysis"""
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            x, y, w, h = face_location
            face_recognition_location = (y, x + w, y + h, x)

            landmarks_list = face_recognition.face_landmarks(rgb_image, [face_recognition_location])
            if landmarks_list:
                return landmarks_list[0]
        except Exception as e:
            print(f"Landmark extraction failed: {e}")
        return None

    def enhance_face_image(self, image: np.ndarray, face_location: Tuple[int, int, int, int]) -> np.ndarray:
        """Apply image enhancement to improve recognition accuracy"""
        x, y, w, h = face_location
        face_roi = image[y:y+h, x:x+w].copy()

        # Apply histogram equalization for better contrast
        if len(face_roi.shape) == 3:
            ycrcb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
            face_roi = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

        # Apply mild sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        face_roi = cv2.filter2D(face_roi, -1, kernel)

        return face_roi
