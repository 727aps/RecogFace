import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.spatial.distance import cosine, euclidean
from .face_trainer import FaceTrainer
from .utils import SecureFaceUtils

class FaceMatcher:
    def __init__(self, tolerance: float = 0.5):
        self.trainer = FaceTrainer()
        self.utils = SecureFaceUtils()
        self.tolerance = tolerance
        self.database = self.trainer.load_face_database()

    def set_tolerance(self, tolerance: float):
        """Update matching tolerance (0.4-0.6 recommended)"""
        self.tolerance = max(0.1, min(1.0, tolerance))
        self.utils.log_event("CONFIG", f"Matching tolerance set to {self.tolerance}")

    def calculate_similarity(self, encoding1: np.ndarray, encoding2: np.ndarray,
                           method: str = 'euclidean') -> float:
        """Calculate similarity between two face encodings"""
        if method == 'cosine':
            # Cosine similarity (higher is more similar)
            return 1 - cosine(encoding1, encoding2)
        else:
            # Euclidean distance (lower is more similar)
            return euclidean(encoding1, encoding2)

    def match_face(self, face_encoding: np.ndarray, method: str = 'hybrid') -> Tuple[Optional[Dict], float]:
        """
        Match face encoding against database
        Returns (person_data, confidence_score) or (None, 0.0)
        """
        if not self.database.get('persons'):
            return None, 0.0

        best_match = None
        best_confidence = 0.0

        for person in self.database['persons']:
            db_encoding = np.array(person['encoding'])

            # Primary matching with Euclidean distance
            euclidean_dist = self.calculate_similarity(face_encoding, db_encoding, 'euclidean')

            # Fallback to cosine similarity for verification
            cosine_sim = self.calculate_similarity(face_encoding, db_encoding, 'cosine')

            # Adaptive confidence calculation
            if euclidean_dist < self.tolerance:
                # Higher confidence for closer matches
                confidence = max(0, 1.0 - (euclidean_dist / self.tolerance))
                # Boost confidence if cosine similarity also indicates match
                if cosine_sim > 0.7:
                    confidence *= 1.2
                confidence = min(1.0, confidence)

                if confidence > best_confidence:
                    best_match = person
                    best_confidence = confidence

        # Quality-based confidence adjustment
        if best_match and best_confidence > 0:
            quality_factor = best_match.get('quality_score', 0.5)
            best_confidence *= quality_factor

        return best_match, best_confidence

    def match_multiple_faces(self, face_encodings: List[np.ndarray]) -> List[Tuple[Optional[Dict], float]]:
        """Match multiple faces in a single frame"""
        results = []
        for encoding in face_encodings:
            match, confidence = self.match_face(encoding)
            results.append((match, confidence))
        return results

    def adaptive_threshold_adjustment(self, image_variance: float) -> float:
        """Adjust matching threshold based on image quality"""
        # Lower threshold for higher quality images
        base_threshold = self.tolerance
        quality_factor = min(1.0, image_variance / 1000.0)  # Normalize variance
        adjusted_threshold = base_threshold * (0.8 + 0.4 * quality_factor)
        return adjusted_threshold

    def re_query_on_low_confidence(self, face_encoding: np.ndarray,
                                 low_confidence_threshold: float = 0.6) -> Tuple[Optional[Dict], float]:
        """Perform re-query with relaxed threshold for uncertain matches"""
        original_tolerance = self.tolerance
        relaxed_tolerance = original_tolerance * 1.5  # More permissive

        self.set_tolerance(relaxed_tolerance)
        match, confidence = self.match_face(face_encoding)
        self.set_tolerance(original_tolerance)  # Restore original

        if match and confidence >= low_confidence_threshold:
            return match, confidence
        return None, 0.0

    def batch_match_gallery(self, image_paths: List[str], output_dir: str) -> Dict[str, List]:
        """Batch process images for face matching and annotation"""
        import cv2
        import os
        from .face_detector import FaceDetector

        detector = FaceDetector()
        results = {'processed': 0, 'matches': 0, 'unknown': 0, 'errors': 0}

        os.makedirs(output_dir, exist_ok=True)

        for image_path in image_paths:
            try:
                image = cv2.imread(image_path)
                if image is None:
                    results['errors'] += 1
                    continue

                faces, encodings = detector.detect_and_encode(image)
                matches = self.match_multiple_faces(encodings)

                # Annotate image
                annotated_image = image.copy()
                match_details = []

                for i, ((match, confidence), (x, y, w, h)) in enumerate(zip(matches, faces)):
                    if match and confidence > 0.5:
                        color = (0, 255, 0)  # Green for known faces
                        label = f"{match['name']} ({confidence:.2f})"
                        results['matches'] += 1
                    else:
                        color = (0, 0, 255)  # Red for unknown faces
                        label = f"Unknown ({confidence:.2f})"
                        results['unknown'] += 1

                    # Draw bounding box and label
                    cv2.rectangle(annotated_image, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(annotated_image, label, (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                    match_details.append({
                        'face_id': i,
                        'bbox': [x, y, w, h],
                        'match': match['name'] if match else 'Unknown',
                        'confidence': confidence,
                        'person_id': match['id'] if match else None
                    })

                # Save annotated image
                filename = os.path.basename(image_path)
                output_path = os.path.join(output_dir, f"annotated_{filename}")
                cv2.imwrite(output_path, annotated_image)

                results['processed'] += 1

                # Log results for this image
                self.utils.log_event("GALLERY", f"Processed {filename}: {len(faces)} faces, {sum(1 for m in matches if m[0])} matches")

            except Exception as e:
                self.utils.log_event("ERROR", f"Failed to process {image_path}: {e}")
                results['errors'] += 1

        return results

    def get_matching_statistics(self) -> Dict:
        """Get statistics about matching performance"""
        data = self.trainer.load_face_database()
        persons = data.get('persons', [])

        stats = {
            'total_persons': len(persons),
            'avg_quality_score': np.mean([p.get('quality_score', 0) for p in persons]) if persons else 0,
            'database_integrity': self.trainer.validate_database_integrity(),
            'current_tolerance': self.tolerance
        }

        return stats

    def export_match_log(self, matches: List[Dict], filename: str):
        """Export matching results to CSV"""
        import pandas as pd

        df = pd.DataFrame(matches)
        df['timestamp'] = pd.Timestamp.now()
        df.to_csv(filename, index=False)

        self.utils.log_event("EXPORT", f"Match log exported to {filename}")

    def refresh_database(self):
        """Reload face database from disk"""
        self.database = self.trainer.load_face_database()
        self.utils.log_event("DATABASE", "Face database refreshed")
