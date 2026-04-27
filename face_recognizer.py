import cv2
import numpy as np
import os
import tempfile

# استيراد DeepFace مع معالجة الخطأ
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("⚠️ DeepFace not available, using fallback mode")

class FaceRecognizer:
    def __init__(self, known_faces_dir='/app/data/known_faces/'):
        self.known_faces_dir = known_faces_dir
        self.known_faces = []
        self.known_names = []
        self.deepface_available = DEEPFACE_AVAILABLE
        
        if os.path.exists(known_faces_dir):
            for filename in os.listdir(known_faces_dir):
                if filename.endswith(('.jpg', '.png', '.jpeg')):
                    path = os.path.join(known_faces_dir, filename)
                    if os.path.getsize(path) > 1000:
                        name = os.path.splitext(filename)[0]
                        self.known_names.append(name)
                        self.known_faces.append(path)
                        print(f"✅ Added face: {name}")
                    else:
                        print(f"⚠️ Skipping empty file: {filename}")
        
        if self.deepface_available:
            print(f"✅ DeepFace initialized with {len(self.known_names)} known faces")
        else:
            print(f"⚠️ Running without DeepFace. Face recognition disabled.")
        
    def recognize(self, image):
        if not self.deepface_available or len(self.known_faces) == 0:
            return []
            
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        temp_path = temp_file.name
        cv2.imwrite(temp_path, image)
        
        faces = []
        try:
            # استخراج الوجوه
            detected_faces = DeepFace.extract_faces(
                img_path=temp_path, 
                detector_backend='opencv', 
                enforce_detection=False
            )
            
            if len(detected_faces) > 0:
                # مقارنة مع الوجوه المعروفة
                for idx, known_face_path in enumerate(self.known_faces):
                    try:
                        result = DeepFace.verify(
                            img1_path=temp_path, 
                            img2_path=known_face_path,
                            model_name='Facenet',
                            detector_backend='opencv',
                            enforce_detection=False
                        )
                        if result['verified']:
                            name = self.known_names[idx]
                            face_area = detected_faces[0]['area']
                            x = int(face_area['x'])
                            y = int(face_area['y'])
                            w = int(face_area['w'])
                            h = int(face_area['h'])
                            faces.append((name, (x, y, x+w, y+h)))
                            print(f"✅ Recognized: {name}")
                            break
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"DeepFace error: {e}")
        finally:
            os.unlink(temp_path)
            
        return faces
