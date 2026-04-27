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

class PepperFinalOpenCV:
    def __init__(self):
        print("🚀 تشغيل Pepper مع OpenCV لعرض الصور...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.resetDebugVisualizerCamera(3.5, 50, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        self.reset_arms()
        
        # تحميل العلماء
        self.scientists = []
        self.load_scientists()
        
        # نافذة OpenKV
        cv2.namedWindow("Scientist Images", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Scientist Images", 800, 600)
        cv2.moveWindow("Scientist Images", 1000, 100)
        
        self.current_image_index = 0
        self.running = True
        self.speak("I am ready! Watch me recognize scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
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

    def reset_arms(self):
        self.pepper.setAngles(["LShoulderPitch"], [1.57], 0.1)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.1)
        self.pepper.setAngles(["LElbowRoll"], [-1.2], 0.1)
        self.pepper.setAngles(["RElbowRoll"], [1.2], 0.1)

    def load_scientists(self):
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        scientist_info = {
            'einstein': {
                'name': 'Albert Einstein',
                'facts': [
                    'developed the theory of relativity',
                    'won the Nobel Prize in Physics',
                    'had the famous equation E=mc²'
                ]
            },
            'marie_curie': {
                'name': 'Marie Curie',
                'facts': [
                    'discovered radium and polonium',
                    'first person to win two Nobel Prizes',
                    'died from radiation exposure'
                ]
            },
            'newton': {
                'name': 'Isaac Newton',
                'facts': [
                    'formulated the laws of motion',
                    'discovered gravity',
                    'invented calculus'
                ]
            },
            'tesla': {
                'name': 'Nikola Tesla',
                'facts': [
                    'invented alternating current',
                    'developed the Tesla coil',
                    'had over 300 patents'
                ]
            },
            'hawking': {
                'name': 'Stephen Hawking',
                'facts': [
                    'studied black holes',
                    'wrote A Brief History of Time',
                    'had ALS and used a speech synthesizer'
                ]
            }
        }
        
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                filepath = os.path.join(images_dir, filename)
                base_name = os.path.splitext(filename)[0].lower()
                
                # قراءة الصورة
                img = cv2.imread(filepath)
                if img is not None:
                    img = cv2.resize(img, (300, 400))
                    
                    # البحث عن المعلومات
                    for key, info in scientist_info.items():
                        if key in base_name:
                            self.scientists.append({
                                'name': info['name'],
                                'facts': info['facts'],
                                'image': img,
                                'filepath': filepath
                            })
                            print(f"✅ Added: {info['name']}")
                            break

    def display_current_image(self):
        if self.current_image_index < len(self.scientists):
            scientist = self.scientists[self.current_image_index]
            
            # عرض الصورة
            img_copy = scientist['image'].copy()
            
            # رسم مربع أخضر واسم
            cv2.rectangle(img_copy, (10, 10), (290, 390), (0, 255, 0), 3)
            cv2.putText(img_copy, scientist['name'], (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Scientist Images", img_copy)
            cv2.waitKey(1)
            
            return scientist
        return None

    def move_to_image(self):
        # تحريك Pepper تجاه الصورة (مكان افتراضي)
        current = self.pepper.getPosition()
        target = [2, 0, 0.5]
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        
        if abs(dx) > 0.1 or abs(dy) > 0.1:
            self.pepper.move(0.05 * dx, 0, 0.03 * dy)
            return False
        return True

    def wave(self):
        self.pepper.setAngles(["RShoulderPitch"], [-0.5], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        self.reset_arms()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper مع OpenCV - الصور في نافذة منفصلة")
        print("="*60 + "\n")
        
        recognized = [False] * len(self.scientists)
        current_scientist = None
        
        try:
            while self.running:
                # عرض الصورة الحالية
                if self.current_image_index < len(self.scientists):
                    current_scientist = self.display_current_image()
                    
                    # التحرك نحو الصورة
                    if self.move_to_image():
                        if not recognized[self.current_image_index]:
                            # التعرف على العالم
                            name = current_scientist['name']
                            fact = random.choice(current_scientist['facts'])
                            
                            print(f"\n🔍 Pepper: This is {name}!")
                            print(f"💬 {fact}")
                            
                            self.speak(f"This is {name}! {fact}")
                            self.wave()
                            
                            # كتابة المعلومة في المحاكي
                            pos = self.pepper.getPosition()
                            p.addUserDebugText(
                                f"{name}: {fact}",
                                [pos[0], pos[1], pos[2] + 1.5],
                                [0, 0, 0],
                                textSize=1.5,
                                lifeTime=3
                            )
                            
                            recognized[self.current_image_index] = True
                            time.sleep(3)
                        
                        self.current_image_index += 1
                else:
                    # إعادة التشغيل
                    print("\n🔄 جولة جديدة!")
                    self.current_image_index = 0
                    recognized = [False] * len(self.scientists)
                    self.speak("Let's look at them again!")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
        finally:
            cv2.destroyAllWindows()
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFinalOpenCV()
    app.run()
