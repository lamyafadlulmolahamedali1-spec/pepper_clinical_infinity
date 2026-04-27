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

class PepperMuseumDeluxe:
    def __init__(self):
        print("🚀 تشغيل Pepper في متحف العلماء الفاخر...")
        
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
        p.resetDebugVisualizerCamera(4.5, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # سرعة عالية
        self.speed = 0.6
        
        # تحميل العلماء
        self.scientists = self.load_scientists()
        
        # نافذة الصور
        self.create_image_window()
        
        self.current_index = 0
        self.last_update = time.time()
        self.text_id = None
        self.running = True
        self.speech_queue = queue.Queue()
        self.start_speech_worker()
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("Welcome to the scientist museum! Watch me move!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 1.0)
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

    def load_scientists(self):
        """تحميل العلماء مع صورهم"""
        scientists = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # قائمة العلماء
        data = [
            {
                'name': 'Albert Einstein',
                'key': 'einstein',
                'facts': ['E=mc²', 'Theory of Relativity', 'Nobel Prize 1921', 'German physicist', 'said: Imagination is important'],
                'color': [0.9, 0.8, 0.7]
            },
            {
                'name': 'Marie Curie',
                'key': 'marie_curie',
                'facts': ['Discovered Radium', 'Two Nobel Prizes', 'First woman professor', 'Died from radiation', 'Polish scientist'],
                'color': [0.8, 0.7, 0.9]
            },
            {
                'name': 'Isaac Newton',
                'key': 'newton',
                'facts': ['Laws of Motion', 'Gravity', 'Invented Calculus', 'English physicist', 'Apple story'],
                'color': [0.7, 0.9, 0.8]
            },
            {
                'name': 'Nikola Tesla',
                'key': 'tesla',
                'facts': ['AC Current', 'Tesla Coil', 'Wireless energy', 'Serbian inventor', '300 patents'],
                'color': [0.9, 0.9, 0.6]
            },
            {
                'name': 'Stephen Hawking',
                'key': 'hawking',
                'facts': ['Black Holes', 'A Brief History of Time', 'ALS', 'British cosmologist', 'Universe theories'],
                'color': [0.7, 0.7, 0.9]
            }
        ]
        
        for d in data:
            found = False
            for filename in os.listdir(images_dir):
                if d['key'] in filename.lower() and filename.endswith(('.jpg', '.png')):
                    img_path = os.path.join(images_dir, filename)
                    img = cv2.imread(img_path)
                    if img is not None:
                        img = cv2.resize(img, (400, 500))
                        d['image'] = img
                        scientists.append(d)
                        found = True
                        print(f"✅ Added: {d['name']}")
                        break
            if not found:
                # صورة افتراضية
                img = np.ones((500, 400, 3), dtype=np.uint8) * 200
                d['image'] = img
                scientists.append(d)
                print(f"⚠️ No image for {d['name']}, using default")
        
        return scientists

    def create_image_window(self):
        """إنشاء نافذة الصور"""
        cv2.namedWindow("Scientists Gallery", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientists Gallery", 1200, 600)
        cv2.moveWindow("Scientists Gallery", 800, 50)
        
        # إنشاء لوحة عرض لجميع العلماء
        self.gallery = np.ones((600, 1200, 3), dtype=np.uint8) * 255

    def update_gallery(self):
        """تحديث معرض الصور"""
        self.gallery[:] = 255
        x_pos = 50
        for i, s in enumerate(self.scientists):
            # نسخ الصورة
            img = s['image'].copy()
            h, w = img.shape[:2]
            
            # إطار أخضر للعالم الحالي
            if i == self.current_index:
                cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 8)
                # اسم العالم الحالي
                cv2.putText(img, f"★ {s['name']} ★", (20, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.rectangle(img, (5, 5), (w-5, h-5), (100, 100, 100), 2)
                cv2.putText(img, s['name'], (20, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            
            # وضع الصورة في المعرض
            self.gallery[50:50+h, x_pos:x_pos+w] = img
            x_pos += w + 20
        
        cv2.imshow("Scientists Gallery", self.gallery)
        cv2.waitKey(1)

    def show_text_over_pepper(self, text):
        """نص فوق Pepper"""
        pos = self.pepper.getPosition()
        if self.text_id is not None:
            p.removeUserDebugItem(self.text_id)
        self.text_id = p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 2.0],
            [0, 0, 0],
            textSize=1.8,
            lifeTime=2.5
        )

    def move_hands(self, style="wave"):
        """حركات اليدين المختلفة"""
        if style == "wave":
            # موجة
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                 [-0.5, 0.8], self.speed)
            self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                                 [1.3, -1.3], self.speed)
        elif style == "both":
            # كلتا اليدين
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                 [-0.3, 1.0], self.speed)
            self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                                 [1.2, -1.2], self.speed)
        elif style == "raise":
            # رفع اليدين
            self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                                 [-0.8, 1.2], self.speed)
        
        time.sleep(0.3)
        # إعادة اليدين لوضعية طبيعية
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                             [0.2, 1.57], 0.3)
        self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                             [1.2, -1.2], 0.3)

    def move_pepper(self):
        """حركة Pepper السريعة"""
        # مشي دائري
        self.pepper.move(0.35, 0, 0.25)
        
        # حركة اليدين
        if random.choice([True, False]):
            self.move_hands("wave")
        else:
            self.move_hands("both")
        
        # دوران الرأس
        self.pepper.setAngles(["HeadYaw"], [0.5], self.speed)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadYaw"], [-0.5], self.speed)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadYaw"], [0.0], self.speed)

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper في متحف العلماء - 5 صور + حركة سريعة + يدين")
        print("="*70 + "\n")
        
        self.speak("Welcome! Look at the gallery!")
        
        try:
            while self.running:
                # حركة سريعة
                self.move_pepper()
                
                # تحديث المعرض
                self.update_gallery()
                
                # كل ثانيتين نغير العالم
                if time.time() - self.last_update > 2:
                    s = self.scientists[self.current_index]
                    fact = random.choice(s['facts'])
                    
                    # نص فوق Pepper
                    self.show_text_over_pepper(f"{s['name']}: {fact}")
                    
                    # كلام
                    print(f"⚡ {s['name']}: {fact}")
                    self.speak(f"{s['name']} {fact}")
                    
                    self.current_index += 1
                    if self.current_index >= len(self.scientists):
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
    app = PepperMuseumDeluxe()
    app.run()
