import numpy as np
import cv2
import os
from typing import Dict, List, Optional
from .face_detector import FaceDetector
from .utils import SecureFaceUtils
import json

class FaceTrainer:
    def __init__(self):
        self.detector = FaceDetector()
        self.utils = SecureFaceUtils()
        self.data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'face_data.json')

    def augment_face(self, face_image: np.ndarray) -> List[np.ndarray]:
        """Apply data augmentation techniques to improve robustness"""
        augmented_faces = [face_image]  # Include original

        # Flip horizontally
        augmented_faces.append(cv2.flip(face_image, 1))

        # Add slight rotations
        for angle in [-10, 10]:
            h, w = face_image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(face_image, rotation_matrix, (w, h))
            augmented_faces.append(rotated)

        # Add brightness variations
        for alpha in [0.8, 1.2]:
            adjusted = cv2.convertScaleAbs(face_image, alpha=alpha, beta=0)
            augmented_faces.append(adjusted)

        return augmented_faces

    def capture_training_frames(self, person_name: str, person_id: str, num_frames: int = 15) -> Optional[Dict]:
        """Capture multiple frames for robust training"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.utils.log_event("ERROR", "Could not open webcam for training")
            return None

        collected_encodings = []
        frame_count = 0

        self.utils.log_event("TRAINING", f"Starting capture for {person_name} ({person_id})")

        while frame_count < num_frames:
            ret, frame = cap.read()
            if not ret:
                break

            faces, encodings = self.detector.detect_and_encode(frame)

            if len(faces) == 1 and len(encodings) == 1:
                # Enhance and augment the face
                enhanced_face = self.detector.enhance_face_image(frame, faces[0])
                augmented_faces = self.augment_face(enhanced_face)

                # Get encodings for all augmented versions
                for aug_face in augmented_faces:
                    _, aug_encodings = self.detector.detect_and_encode(aug_face)
                    if aug_encodings:
                        collected_encodings.append(aug_encodings[0])

                frame_count += 1
                self.utils.log_event("TRAINING", f"Captured frame {frame_count}/{num_frames}")

                # Show progress on frame
                cv2.putText(frame, f"Capturing: {frame_count}/{num_frames}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Training Capture", frame)

                if cv2.waitKey(100) & 0xFF == ord('q'):
                    break
            else:
                cv2.putText(frame, "Position face in center",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Training Capture", frame)
                cv2.waitKey(100)

        cap.release()
        cv2.destroyAllWindows()

        if len(collected_encodings) < num_frames:
            self.utils.log_event("ERROR", f"Insufficient training data: {len(collected_encodings)}/{num_frames}")
            return None

        # Average encodings for robustness
        avg_encoding = np.mean(collected_encodings, axis=0)

        # Calculate encoding variance for quality assessment
        encoding_variance = np.var(collected_encodings, axis=0)
        quality_score = 1.0 / (1.0 + np.mean(encoding_variance))

        person_data = {
            'id': person_id,
            'name': person_name,
            'encoding': avg_encoding,
            'quality_score': float(quality_score),
            'training_frames': len(collected_encodings),
            'created_at': self.utils._get_timestamp(),
            'encoding_hash': self.utils.hash_encoding(avg_encoding)
        }

        self.utils.log_event("TRAINING", f"Completed training for {person_name} with quality score: {quality_score:.3f}")
        return person_data

    def load_face_database(self) -> Dict:
        """Load encrypted face database"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    encrypted_data = f.read()
                return self.utils.decrypt_data(encrypted_data)
            except Exception as e:
                self.utils.log_event("ERROR", f"Failed to load face database: {e}")
        return {'persons': []}

    def save_face_database(self, data: Dict):
        """Save encrypted face database"""
        try:
            encrypted_data = self.utils.encrypt_data(data)
            with open(self.data_file, 'w') as f:
                f.write(encrypted_data)

            # Create backup
            self.utils.create_backup(data)

            self.utils.log_event("DATABASE", f"Saved {len(data.get('persons', []))} face records")
        except Exception as e:
            self.utils.log_event("ERROR", f"Failed to save face database: {e}")

    def add_person(self, person_name: str, person_id: str) -> bool:
        """Add new person to database"""
        # Check if person_id already exists
        data = self.load_face_database()
        for person in data.get('persons', []):
            if person['id'] == person_id:
                self.utils.log_event("ERROR", f"Person ID {person_id} already exists")
                return False

        person_data = self.capture_training_frames(person_name, person_id)
        if person_data:
            data['persons'].append(person_data)
            self.save_face_database(data)
            return True
        return False

    def update_person(self, person_id: str, new_name: Optional[str] = None) -> bool:
        """Update existing person data"""
        data = self.load_face_database()
        for person in data.get('persons', []):
            if person['id'] == person_id:
                if new_name:
                    person['name'] = new_name
                # Re-capture encoding if needed
                if new_name:
                    person_data = self.capture_training_frames(new_name, person_id)
                    if person_data:
                        person.update(person_data)
                self.save_face_database(data)
                return True
        return False

    def remove_person(self, person_id: str) -> bool:
        """Remove person from database"""
        data = self.load_face_database()
        original_count = len(data.get('persons', []))
        data['persons'] = [p for p in data['persons'] if p['id'] != person_id]

        if len(data['persons']) < original_count:
            self.save_face_database(data)
            self.utils.log_event("DATABASE", f"Removed person {person_id}")
            return True
        return False

    def get_person_encoding(self, person_id: str) -> Optional[np.ndarray]:
        """Retrieve face encoding for a person"""
        data = self.load_face_database()
        for person in data.get('persons', []):
            if person['id'] == person_id:
                return np.array(person['encoding'])
        return None

    def list_persons(self) -> List[Dict]:
        """List all registered persons"""
        data = self.load_face_database()
        return data.get('persons', [])

    def validate_database_integrity(self) -> bool:
        """Validate database integrity using hashes"""
        data = self.load_face_database()
        for person in data.get('persons', []):
            expected_hash = self.utils.hash_encoding(np.array(person['encoding']))
            if person.get('encoding_hash') != expected_hash:
                self.utils.log_event("ERROR", f"Database integrity check failed for person {person['id']}")
                return False
        return True
