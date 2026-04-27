import time
import pybullet as p
import pybullet_data
import threading
import random
import cv2
import numpy as np
import os
from qibullet import SimulationManager
import pyttsx3
import queue
from ultralytics import YOLO

class PepperYoloEnhanced:
    def __init__(self):
        print("🚀 تشغيل Pepper مع YOLO المحسن...")
        
        # تحميل YOLO
        print("📦 تحميل YOLO...")
        self.yolo = YOLO('yolov8n.pt')
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.resetDebugVisualizerCamera(4.5, 50, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # تحميل الصور
        self.images = self.load_images()
        
        # نوافذ
        cv2.namedWindow("YOLO Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLO Detection", 800, 600)
        cv2.moveWindow("YOLO Detection", 1000, 100)
        
        self.current_index = 0
        self.last_update = time.time()
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ تم تحميل {len(self.images)} صورة")
        self.speak("I will detect objects with YOLO!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text):
        self.speech_queue.put(text)

    def start_speech_worker(self):
        def worker():
            while self.running:
                try:
                    text = self.speech_queue.get(timeout=0.5)
                    self.engine.say(text)
                    self.engine.runAndWait()
                except queue.Empty:
                    continue
        threading.Thread(target=worker, daemon=True).start()

    def load_images(self):
        """تحميل الصور"""
        images = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        scientist_names = {
            'einstein': 'Albert Einstein',
            'marie_curie': 'Marie Curie',
            'newton': 'Isaac Newton',
            'tesla': 'Nikola Tesla',
            'hawking': 'Stephen Hawking'
        }
        
        IMG_HEIGHT = 450
        IMG_WIDTH = 350
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                filepath = os.path.join(images_dir, filename)
                img = cv2.imread(filepath)
                if img is not None:
                    img = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))
                    
                    name = "Unknown"
                    for key, fullname in scientist_names.items():
                        if key in filename.lower():
                            name = fullname
                            break
                    
                    images.append({
                        'name': name,
                        'image': img,
                        'filepath': filepath
                    })
                    print(f"✅ Added: {name}")
        
        return images

    def detect_with_yolo(self, img):
        """كشف الصورة بـ YOLO"""
        results = self.yolo(img)[0]
        detections = []
        img_copy = img.copy()
        
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0].item()
            cls = int(box.cls[0].item())
            label = self.yolo.names[cls]
            detections.append(label)
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(img_copy, f"{label} {conf:.2f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return img_copy, detections, results

    def show_text_over_pepper(self, text):
        """نص فوق Pepper"""
        pos = self.pepper.getPosition()
        if self.text_id is not None:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 2.2],
            [0, 0, 0],
            textSize=1.8,
            lifeTime=3
        )

    def show_text_below_pepper(self, text):
        """نص تحت Pepper"""
        pos = self.pepper.getPosition()
        self.text_id = p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] - 0.5],
            [0, 0, 255],
            textSize=1.5,
            lifeTime=3
        )

    def move_hands(self):
        """حركة يدين"""
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                             [-0.4, 1.0], 0.3)
        self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                             [1.3, -1.3], 0.3)

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع YOLO - كائنات إضافية ونص فوق وتحت")
        print("="*70 + "\n")
        
        self.speak("Watch YOLO detect many objects!")
        
        try:
            while self.running:
                # حركة Pepper
                self.pepper.move(0.15, 0, 0.1)
                self.move_hands()
                
                # كشف الصورة الحالية
                if self.current_index < len(self.images):
                    img_data = self.images[self.current_index]
                    detected_img, detections, results = self.detect_with_yolo(img_data['image'].copy())
                    
                    # إضافة اسم العالم
                    cv2.putText(detected_img, f"★ {img_data['name']} ★", 
                               (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # عرض الكائنات المكتشفة
                    y_pos = 100
                    for i, det in enumerate(detections[:5]):  # أول 5 فقط
                        cv2.putText(detected_img, f"{i+1}. {det}", 
                                   (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        y_pos += 30
                    
                    cv2.imshow("YOLO Detection", detected_img)
                    cv2.waitKey(1)
                    
                    # كل 4 ثواني نتكلم
                    if time.time() - self.last_update > 4:
                        # نص فوق Pepper
                        self.show_text_over_pepper(f"{img_data['name']}")
                        
                        # كلام مع الكائنات
                        if len(detections) > 0:
                            objects = ', '.join(detections[:3])
                            speech = f"{img_data['name']} with {objects}"
                        else:
                            speech = f"This is {img_data['name']}"
                        
                        print(f"🔍 {speech}")
                        self.speak(speech)
                        
                        # نص تحت Pepper مع الكائنات
                        if len(detections) > 0:
                            self.show_text_below_pepper(f"Detected: {objects}")
                        
                        self.current_index += 1
                        if self.current_index >= len(self.images):
                            self.current_index = 0
                            print("\n🔥 New round!")
                        
                        self.last_update = time.time()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperYoloEnhanced()
    app.run()
