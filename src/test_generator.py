#!/usr/bin/env python3
"""
Test data generator for SecureFaceID
Creates synthetic face images using OpenCV for testing purposes
"""

import cv2
import numpy as np
import os
from typing import List

class TestFaceGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_faces')
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_synthetic_face(self, width: int = 160, height: int = 160) -> np.ndarray:
        """Generate a simple synthetic face-like image"""
        # Create blank image
        face = np.zeros((height, width, 3), dtype=np.uint8)
        face.fill(200)  # Light gray background

        # Add simple face features
        center_x, center_y = width // 2, height // 2

        # Face outline (ellipse)
        cv2.ellipse(face, (center_x, center_y), (width//3, height//2.5), 0, 0, 360, (150, 100, 80), -1)

        # Eyes
        eye_color = (50, 50, 50)
        eye_size = (8, 6)
        cv2.ellipse(face, (center_x - 25, center_y - 20), eye_size, 0, 0, 360, eye_color, -1)
        cv2.ellipse(face, (center_x + 25, center_y - 20), eye_size, 0, 0, 360, eye_color, -1)

        # Eyebrows
        cv2.line(face, (center_x - 35, center_y - 35), (center_x - 15, center_y - 30), (30, 30, 30), 2)
        cv2.line(face, (center_x + 15, center_y - 30), (center_x + 35, center_y - 35), (30, 30, 30), 2)

        # Nose
        cv2.ellipse(face, (center_x, center_y + 5), (3, 8), 0, 0, 360, (120, 80, 60), -1)

        # Mouth
        cv2.ellipse(face, (center_x, center_y + 25), (15, 5), 0, 0, 360, (80, 50, 50), -1)

        # Add some random noise for realism
        noise = np.random.normal(0, 5, face.shape).astype(np.uint8)
        face = cv2.add(face, noise)

        return face

    def generate_test_dataset(self, num_persons: int = 5, images_per_person: int = 10):
        """Generate a test dataset with multiple persons"""
        print(f"Generating test dataset: {num_persons} persons, {images_per_person} images each")

        for person_id in range(1, num_persons + 1):
            person_dir = os.path.join(self.output_dir, f'person_{person_id:02d}')
            os.makedirs(person_dir, exist_ok=True)

            for img_id in range(1, images_per_person + 1):
                # Generate face with slight variations
                face = self.generate_synthetic_face()

                # Add random transformations for variety
                if img_id % 3 == 0:
                    # Slight rotation
                    angle = np.random.uniform(-10, 10)
                    h, w = face.shape[:2]
                    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
                    face = cv2.warpAffine(face, M, (w, h))

                elif img_id % 3 == 1:
                    # Brightness variation
                    alpha = np.random.uniform(0.7, 1.3)
                    face = cv2.convertScaleAbs(face, alpha=alpha, beta=0)

                # Save image
                filename = f'person_{person_id:02d}_{img_id:02d}.jpg'
                filepath = os.path.join(person_dir, filename)
                cv2.imwrite(filepath, face)

        print(f"Test dataset generated in: {self.output_dir}")
        return self.output_dir

    def generate_single_test_image(self, person_name: str = "TestPerson") -> str:
        """Generate a single test image for quick testing"""
        face = self.generate_synthetic_face()
        filepath = os.path.join(self.output_dir, f'{person_name}_test.jpg')
        cv2.imwrite(filepath, face)
        print(f"Test image saved: {filepath}")
        return filepath

if __name__ == "__main__":
    generator = TestFaceGenerator()

    # Generate small test dataset
    test_dir = generator.generate_test_dataset(num_persons=3, images_per_person=5)

    # Generate single test image
    single_test = generator.generate_single_test_image()

    print("\nTest data generation complete!")
    print(f"Dataset location: {test_dir}")
    print(f"Single test image: {single_test}")
