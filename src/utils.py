import os
import json
import logging
import hashlib
import numpy as np
from datetime import datetime
from cryptography.fernet import Fernet
from plyer import notification
import winsound
from deepface import DeepFace
import cv2

class SecureFaceUtils:
    def __init__(self):
        self.setup_logging()
        self.key = self.get_or_create_key()

    def setup_logging(self):
        """Initialize logging system"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f'secureface_{datetime.now().strftime("%Y%m%d")}.log')

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

    def get_or_create_key(self):
        """Generate or load encryption key"""
        key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'encryption.key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    def encrypt_data(self, data):
        """Encrypt data using Fernet"""
        f = Fernet(self.key)
        json_data = json.dumps(data, cls=NumpyEncoder)
        return f.encrypt(json_data.encode()).decode()

    def decrypt_data(self, encrypted_data):
        """Decrypt data using Fernet"""
        f = Fernet(self.key)
        decrypted = f.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())

    def hash_encoding(self, encoding):
        """Create hash of face encoding for verification"""
        encoding_str = ','.join([str(x) for x in encoding])
        return hashlib.sha256(encoding_str.encode()).hexdigest()

    def log_event(self, event_type, details):
        """Log security and recognition events"""
        logging.info(f"{event_type}: {details}")

    def show_alert(self, title, message, sound=True):
        """Show system notification and play sound"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="SecureFaceID",
                timeout=5
            )
            if sound:
                winsound.Beep(800, 500)  # Frequency 800Hz, duration 500ms
        except Exception as e:
            logging.warning(f"Alert notification failed: {e}")

    def estimate_age_gender(self, face_image):
        """Estimate age and gender using DeepFace"""
        try:
            analysis = DeepFace.analyze(face_image, actions=['age', 'gender'], enforce_detection=False)
            if isinstance(analysis, list) and len(analysis) > 0:
                result = analysis[0]
                return {
                    'age': int(result.get('age', 0)),
                    'gender': result.get('dominant_gender', 'unknown'),
                    'gender_confidence': result.get('gender', {}).get(result.get('dominant_gender', ''), 0)
                }
        except Exception as e:
            logging.warning(f"Age/gender estimation failed: {e}")
        return {'age': 0, 'gender': 'unknown', 'gender_confidence': 0}

    def anonymize_image(self, image, faces):
        """Apply privacy-preserving anonymization to detected faces"""
        anonymized = image.copy()
        for (x, y, w, h) in faces:
            # Apply Gaussian blur to face region
            face_roi = anonymized[y:y+h, x:x+w]
            blurred = cv2.GaussianBlur(face_roi, (99, 99), 30)
            anonymized[y:y+h, x:x+w] = blurred
        return anonymized

    def validate_consent(self):
        """Check if user has provided consent for face processing"""
        consent_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_consent.json')
        if os.path.exists(consent_file):
            with open(consent_file, 'r') as f:
                consent = json.load(f)
                return consent.get('consented', False) and consent.get('timestamp', '')
        return False

    def record_consent(self, consented=True):
        """Record user's consent decision"""
        consent_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_consent.json')
        consent_data = {
            'consented': consented,
            'timestamp': datetime.now().isoformat(),
            'privacy_notice': 'Face data is processed locally and encrypted. No data is transmitted externally.'
        }
        with open(consent_file, 'w') as f:
            json.dump(consent_data, f, indent=2)

    def create_backup(self, data, backup_path=None):
        """Create encrypted backup of face data"""
        if backup_path is None:
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f'face_data_backup_{timestamp}.enc')

        encrypted_data = self.encrypt_data(data)
        with open(backup_path, 'w') as f:
            f.write(encrypted_data)

        self.log_event("BACKUP", f"Face data backed up to {backup_path}")
        return backup_path

    def calculate_image_variance(self, image):
        """Calculate image variance for adaptive threshold adjustment"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.var(gray.astype(np.float32))


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy arrays"""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
