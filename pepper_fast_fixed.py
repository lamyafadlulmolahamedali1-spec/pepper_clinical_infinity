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

class PepperFastFixed:
    def __init__(self):
        print("🚀 تشغيل Pepper السريع (نسخة مثبتة)...")
        
        self.init_voice()
        
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.resetDebugVisualizerCamera(4.0, 60, -30, [0, 0, 1])
        
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        self.speed = 0.5
        self.scientists = self.load_scientists()
        self.text_id = None  #初始化
        
        cv2.namedWindow("Scientist", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientist", 400, 500)
        cv2.moveWindow("Scientist", 1000, 100)
        
        self.current_index = 0
        self.last_update = time.time()
        self.running = True
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am fast! Watch me go!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
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

    def load_scientists(self):
        scientists = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        data = [
            {'name': 'Albert Einstein', 'key': 'einstein', 'facts': ['E=mc²', 'Relativity', 'Nobel Prize']},
            {'name': 'Marie Curie', 'key': 'marie_curie', 'facts': ['Radium', 'Two Nobels', 'Radioactivity']},
            {'name': 'Isaac Newton', 'key': 'newton', 'facts': ['Gravity', 'Laws of Motion', 'Calculus']},
            {'name': 'Nikola Tesla', 'key': 'tesla', 'facts': ['AC Current', 'Tesla Coil', 'Wireless']},
            {'name': 'Stephen Hawking', 'key': 'hawking', 'facts': ['Black Holes', 'Time', 'ALS']}
        ]
        
        for d in data:
            found = False
            for f in os.listdir(images_dir):
                if d['key'] in f.lower() and f.endswith(('.jpg', '.png')):
                    img = cv2.imread(os.path.join(images_dir, f))
                    if img is not None:
                        d['image'] = cv2.resize(img, (350, 450))
                        scientists.append(d)
                        found = True
                        break
            if not found:
                d['image'] = np.zeros((450, 350, 3), dtype=np.uint8)
                scientists.append(d)
        
        return scientists

    def show_image(self):
        s = self.scientists[self.current_index]
        img = s['image'].copy()
        h, w = img.shape[:2]
        cv2.rectangle(img, (5, 5), (w-5, h-5), (0, 255, 0), 3)
        cv2.putText(img, s['name'], (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        fact = random.choice(s['facts'])
        cv2.putText(img, fact, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Scientist", img)
        cv2.waitKey(1)
        return fact

    def show_text_over_pepper(self, text, color=[0,0,0]):
        """نص فوق Pepper"""
        pos = self.pepper.getPosition()
        # حذف القديم إذا موجود
        if self.text_id is not None:
            p.removeUserDebugItem(self.text_id)
        # إضافة جديد
        self.text_id = p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 1.8],
            color,
            textSize=1.5,
            lifeTime=2.5
        )

    def move_pepper_fast(self):
        """حركة سريعة جداً"""
        # مشي سريع مع دوران
        self.pepper.move(0.4, 0, 0.3)
        
        # حركة يدين سريعة
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], 
                             [-0.4, 0.9], self.speed)
        self.pepper.setAngles(["RElbowRoll", "LElbowRoll"], 
                             [1.3, -1.3], self.speed)
        
        # دوران رأس
        self.pepper.setAngles(["HeadYaw"], [0.7], self.speed)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadYaw"], [-0.7], self.speed)

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper سريع مع نص فوري!")
        print("="*60 + "\n")
        
        self.speak("Watch me move super fast!")
        
        try:
            while self.running:
                # حركة سريعة جداً
                self.move_pepper_fast()
                
                # كل 1.5 ثانية نغير العالم
                if time.time() - self.last_update > 1.5:
                    s = self.scientists[self.current_index]
                    fact = self.show_image()
                    
                    # نص فوق Pepper فوراً
                    self.show_text_over_pepper(f"{s['name']}: {fact}")
                    
                    # كلام
                    print(f"⚡ {s['name']}: {fact}")
                    self.speak(f"{s['name']} {fact}")
                    
                    self.current_index += 1
                    if self.current_index >= len(self.scientists):
                        self.current_index = 0
                        print("\n🔥 Faster round!")
                    
                    self.last_update = time.time()
                
                # حركة إضافية للخلف
                self.pepper.move(-0.2, 0, -0.2)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFastFixed()
    app.run()
