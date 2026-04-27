import time
import pybullet as p
import pybullet_data
import threading
import random
import cv2
import numpy as np
import os
import math
from qibullet import SimulationManager
import pyttsx3
import queue
from ultralytics import YOLO

class PepperYoloFixed:
    def __init__(self):
        print("🚀 تشغيل Pepper مع YOLO (نسخة مثبتة)...")
        
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
        
        # إعدادات
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
        
        # تحميل الصور (بنفس الحجم)
        self.images = self.load_images()
        
        # نوافذ العرض
        cv2.namedWindow("YOLO Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("YOLO Detection", 800, 600)
        cv2.moveWindow("YOLO Detection", 1000, 100)
        
        cv2.namedWindow("Scientists Gallery", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientists Gallery", 1200, 500)
        cv2.moveWindow("Scientists Gallery", 100, 100)
        
        self.current_index = 0
        self.last_update = time.time()
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ تم تحميل {len(self.images)} صورة")
        self.speak("I will detect scientists with YOLO!")

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
        """تحميل الصور وتوحيد أحجامها"""
        images = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # حجم موحد للجميع
        IMG_HEIGHT = 450
        IMG_WIDTH = 350
        
        scientist_names = {
            'einstein': 'Albert Einstein',
            'marie_curie': 'Marie Curie',
            'newton': 'Isaac Newton',
            'tesla': 'Nikola Tesla',
            'hawking': 'Stephen Hawking'
        }
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                filepath = os.path.join(images_dir, filename)
                img = cv2.imread(filepath)
                if img is not None:
                    # توحيد الحجم
                    img = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))
                    
                    # تحديد اسم العالم
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
        """الكشف عن الصورة باستخدام YOLO"""
        results = self.yolo(img)[0]
        
        # رسم النتائج
        img_copy = img.copy()
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf[0].item()
            cls = int(box.cls[0].item())
            label = self.yolo.names[cls]
            
            # رسم المربع
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(img_copy, f"{label} {conf:.2f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return img_copy, results

    def show_gallery(self):
        """عرض معرض الصور"""
        if len(self.images) == 0:
            return
            
        h, w = self.images[0]['image'].shape[:2]
        gallery = np.ones((h + 100, 1200, 3), dtype=np.uint8) * 255
        x_pos = 20
        
        for i, img_data in enumerate(self.images):
            img = img_data['image'].copy()
            
            # إطار للصورة الحالية
            if i == self.current_index:
                cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 5)
                cv2.putText(img, f"★ {img_data['name']} ★", (20, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(img, img_data['name'], (20, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            
            gallery[20:20+h, x_pos:x_pos+w] = img
            x_pos += w + 20
        
        cv2.imshow("Scientists Gallery", gallery)
        cv2.waitKey(1)

    def detect_current_image(self):
        """كشف الصورة الحالية بـ YOLO"""
        if self.current_index < len(self.images):
            img_data = self.images[self.current_index]
            detected_img, results = self.detect_with_yolo(img_data['image'].copy())
            
            # إضافة الاسم
            cv2.putText(detected_img, f"Detected: {img_data['name']}", 
                       (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            cv2.imshow("YOLO Detection", detected_img)
            cv2.waitKey(1)
            
            return results
        return None

    def move_pepper(self):
        """حركة Pepper"""
        # مشي بطيء
        self.pepper.move(0.1, 0, 0.05)
        
        # حركة يدين
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                             [-0.3, 1.0], 0.3)
        self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                             [1.2, -1.2], 0.3)

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع YOLO - جميع الصور بنفس الحجم")
        print("="*70 + "\n")
        
        self.speak("Watch YOLO detect scientists!")
        
        try:
            while self.running:
                # حركة Pepper
                self.move_pepper()
                
                # تحديث المعرض
                self.show_gallery()
                
                # كشف الصورة الحالية
                self.detect_current_image()
                
                # كل 4 ثواني ننتقل للصورة التالية
                if time.time() - self.last_update > 4:
                    if self.current_index < len(self.images):
                        img_data = self.images[self.current_index]
                        
                        # كلام
                        speech = f"This is {img_data['name']}"
                        print(f"🔍 {speech}")
                        self.speak(speech)
                        
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
    app = PepperYoloFixed()
    app.run()
