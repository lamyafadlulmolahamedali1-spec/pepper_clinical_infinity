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

class PepperWithImagesLight:
    def __init__(self):
        print("🚀 تشغيل Pepper مع صور خفيفة...")
        
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
        p.resetDebugVisualizerCamera(4.0, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        self.reset_pose()
        
        # تحميل العلماء
        self.scientists = self.load_scientists_with_images()
        
        # نافذة الصور
        cv2.namedWindow("Scientist Portrait", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientist Portrait", 400, 500)
        cv2.moveWindow("Scientist Portrait", 1000, 100)
        
        self.current_index = 0
        self.last_image_time = time.time()
        self.running = True
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("Welcome! I will show you scientists.")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def reset_pose(self):
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.1], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.3, 1.2], 0.1)

    def wave(self):
        self.pepper.setAngles(["RShoulderPitch"], [-0.5], 0.3)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.3)
        self.reset_pose()

    def load_scientists_with_images(self):
        """تحميل العلماء مع صورهم الفعلية"""
        scientists = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        scientist_data = [
            {'name': 'Albert Einstein', 'key': 'einstein', 'facts': ['developed relativity', 'won Nobel Prize', 'E=mc²']},
            {'name': 'Marie Curie', 'key': 'marie_curie', 'facts': ['discovered radium', 'two Nobel Prizes', 'died from radiation']},
            {'name': 'Isaac Newton', 'key': 'newton', 'facts': ['laws of motion', 'gravity', 'calculus']},
            {'name': 'Nikola Tesla', 'key': 'tesla', 'facts': ['AC current', 'Tesla coil', '300 patents']},
            {'name': 'Stephen Hawking', 'key': 'hawking', 'facts': ['black holes', 'Brief History of Time', 'ALS']}
        ]
        
        for scientist in scientist_data:
            for filename in os.listdir(images_dir):
                if scientist['key'] in filename.lower() and filename.endswith(('.jpg', '.png')):
                    img_path = os.path.join(images_dir, filename)
                    img = cv2.imread(img_path)
                    if img is not None:
                        img = cv2.resize(img, (350, 450))
                        scientist['image'] = img
                        scientists.append(scientist)
                        break
            if 'image' not in scientist:
                # صورة افتراضية
                scientist['image'] = np.zeros((450, 350, 3), dtype=np.uint8)
                scientists.append(scientist)
        
        return scientists

    def show_current_image(self):
        """عرض صورة العالم الحالي"""
        if self.current_index < len(self.scientists):
            scientist = self.scientists[self.current_index]
            img = scientist['image'].copy()
            
            # إطار أخضر
            h, w = img.shape[:2]
            cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 3)
            
            # اسم العالم
            cv2.putText(img, scientist['name'], (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Scientist Portrait", img)
            cv2.waitKey(1)

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper مع صور العلماء")
        print("="*60 + "\n")
        
        self.speak("Look at the window to see the scientists!")
        
        try:
            while self.running:
                # عرض الصورة الحالية
                self.show_current_image()
                
                # التحدث عن العالم الحالي
                if time.time() - self.last_image_time > 5:
                    scientist = self.scientists[self.current_index]
                    fact = random.choice(scientist['facts'])
                    
                    speech = f"This is {scientist['name']}. {fact}"
                    print(f"💬 {speech}")
                    self.speak(speech)
                    
                    self.wave()
                    
                    self.current_index += 1
                    if self.current_index >= len(self.scientists):
                        self.current_index = 0
                        print("\n🔄 New round!")
                    
                    self.last_image_time = time.time()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperWithImagesLight()
    app.run()
