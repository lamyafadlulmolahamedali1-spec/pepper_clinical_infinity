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
from deepface import DeepFace
import tempfile

class PepperWithImages:
    def __init__(self):
        print("🚀 تشغيل Pepper مع التعرف على صور العلماء...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات نافذة حرة
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        
        # Pepper واحد
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[0, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # ضبط الكاميرا على Pepper
        p.resetDebugVisualizerCamera(3.0, 50, -30, [0, 0, 1])
        
        # وضعية البداية
        self.reset_pose()
        
        # تحميل العلماء
        self.load_scientists()
        
        # عرض الصور في المحاكي
        self.display_scientist_images()
        
        self.running = True
        self.current_target = 0
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am ready to recognize famous scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
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
        """تحميل معلومات العلماء"""
        self.scientists = [
            {
                'name': 'Albert Einstein',
                'image': 'einstein.jpg',
                'facts': [
                    'developed the theory of relativity',
                    'won the Nobel Prize in Physics',
                    'said: imagination is more important than knowledge'
                ],
                'pos': [2, -1, 0.5]
            },
            {
                'name': 'Marie Curie',
                'image': 'marie_curie.jpg',
                'facts': [
                    'discovered radium and polonium',
                    'first person to win two Nobel Prizes',
                    'died from radiation exposure'
                ],
                'pos': [2, 1, 0.5]
            },
            {
                'name': 'Isaac Newton',
                'image': 'newton.jpg',
                'facts': [
                    'formulated the laws of motion',
                    'discovered gravity',
                    'invented calculus'
                ],
                'pos': [2, -2.5, 0.5]
            },
            {
                'name': 'Nikola Tesla',
                'image': 'tesla.jpg',
                'facts': [
                    'invented alternating current',
                    'developed the Tesla coil',
                    'was a visionary inventor'
                ],
                'pos': [2, 2.5, 0.5]
            },
            {
                'name': 'Stephen Hawking',
                'image': 'hawking.jpg',
                'facts': [
                    'studied black holes',
                    'wrote A Brief History of Time',
                    'had ALS and communicated via computer'
                ],
                'pos': [2, -4, 0.5]
            }
        ]

    def display_scientist_images(self):
        """عرض صور العلماء في المحاكي كـ 2D textures"""
        for i, s in enumerate(self.scientists):
            # إنشاء صورة افتراضية (مستطيل)
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.5, 0.01, 0.7])
            
            # لون مختلف لكل عالم
            colors = [
                [0.9, 0.8, 0.7, 1],  # Einstein
                [0.8, 0.7, 0.9, 1],  # Curie
                [0.7, 0.9, 0.8, 1],  # Newton
                [0.9, 0.9, 0.6, 1],  # Tesla
                [0.7, 0.7, 0.9, 1]   # Hawking
            ]
            
            vis_id = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[0.5, 0.01, 0.7],
                rgbaColor=colors[i % len(colors)]
            )
            
            # وضع الصورة في المكان المحدد
            p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=col_id,
                baseVisualShapeIndex=vis_id,
                basePosition=s['pos']
            )
            
            # إضافة اسم العالم فوق الصورة
            text_pos = [s['pos'][0], s['pos'][1], s['pos'][2] + 0.8]
            p.addUserDebugText(s['name'], text_pos, [0, 0, 0], textSize=1.5, lifeTime=0)

    def reset_pose(self):
        """وضعية وقوف طبيعية"""
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def move_to_scientist(self, target_pos):
        """تحريك Pepper نحو العالم"""
        current_pos = self.pepper.getPosition()
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        
        if abs(dx) > 0.2 or abs(dy) > 0.2:
            self.pepper.move(0.1 * dx, 0, 0.05 * dy)
            return False
        return True

    def wave(self):
        """يلوح بيده"""
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.3)
        self.reset_pose()

    def look_at(self, target_pos):
        """يدير رأسه نحو الهدف"""
        dx = target_pos[0] - self.pepper.getPosition()[0]
        self.pepper.setAngles(["HeadYaw"], [dx * 0.5], 0.1)

    def recognize_scientist(self, scientist_name):
        """يتعرف على العالم ويتحدث عنه"""
        for s in self.scientists:
            if s['name'].lower() in scientist_name.lower():
                fact = random.choice(s['facts'])
                text = f"I recognize {s['name']}! He {fact}"
                print(f"🤖 Pepper: {text}")
                self.speak(text)
                self.wave()
                return True
        return False

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يتعرف على صور العلماء في المحاكي!")
        print("="*60 + "\n")
        
        last_move_time = time.time()
        recognized = [False] * len(self.scientists)
        
        try:
            while self.running:
                current_time = time.time()
                
                # حركة كل 5 ثواني
                if current_time - last_move_time > 5:
                    self.look_at([2, 0, 0.5])
                    last_move_time = current_time
                
                # التنقل بين العلماء والتعرف عليهم
                if self.current_target < len(self.scientists):
                    target = self.scientists[self.current_target]
                    
                    # التحرك نحو العالم
                    if self.move_to_scientist(target['pos']):
                        # وصل للعالم
                        if not recognized[self.current_target]:
                            print(f"\n🎯 Pepper وصل إلى {target['name']}")
                            self.recognize_scientist(target['name'])
                            recognized[self.current_target] = True
                            time.sleep(3)
                        
                        self.current_target += 1
                
                # إعادة التشغيل إذا خلص الكل
                if self.current_target >= len(self.scientists):
                    print("\n🔄 إعادة جولة جديدة!")
                    self.current_target = 0
                    recognized = [False] * len(self.scientists)
                    self.speak("Starting a new tour!")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperWithImages()
    app.run()
