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

class PepperFacesFixed:
    def __init__(self):
        print("🚀 تشغيل Pepper مع صور العلماء...")
        
        self.init_voice()
        
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        p.resetDebugVisualizerCamera(3.5, 50, -30, [0, 0, 1])
        self.reset_pose()
        
        self.load_scientists()
        self.create_image_frames()
        
        self.running = True
        self.current_target = 0
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am ready to recognize scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def load_scientists(self):
        self.scientists = [
            {
                'name': 'Albert Einstein',
                'file': 'einstein.jpg',
                'facts': ['developed relativity', 'won Nobel Prize', 'E=mc²'],
                'pos': [2, -1.5, 0.5],
                'color': [0.9, 0.8, 0.7]
            },
            {
                'name': 'Marie Curie',
                'file': 'marie_curie.jpg',
                'facts': ['discovered radium', 'two Nobel Prizes', 'died from radiation'],
                'pos': [2, 0, 0.5],
                'color': [0.8, 0.7, 0.9]
            },
            {
                'name': 'Isaac Newton',
                'file': 'newton.jpg',
                'facts': ['laws of motion', 'gravity', 'calculus'],
                'pos': [2, 1.5, 0.5],
                'color': [0.7, 0.9, 0.8]
            },
            {
                'name': 'Nikola Tesla',
                'file': 'tesla.jpg',
                'facts': ['alternating current', 'Tesla coil', 'wireless energy'],
                'pos': [2, 3, 0.5],
                'color': [0.9, 0.9, 0.6]
            },
            {
                'name': 'Stephen Hawking',
                'file': 'hawking.jpg',
                'facts': ['black holes', 'A Brief History of Time', 'ALS'],
                'pos': [2, -3, 0.5],
                'color': [0.7, 0.7, 0.9]
            }
        ]
        
        # نتحقق من وجود الصور
        self.image_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        for s in self.scientists:
            img_path = os.path.join(self.image_dir, s['file'])
            if not os.path.exists(img_path):
                print(f"⚠️ صورة {s['file']} غير موجودة")

    def create_image_frames(self):
        """إنشاء إطارات للصور بلون يمثل كل عالم"""
        for i, s in enumerate(self.scientists):
            # إطار الصورة
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.5, 0.1, 0.7])
            vis_id = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[0.5, 0.1, 0.7],
                rgbaColor=[*s['color'], 1.0]
            )
            
            p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=col_id,
                baseVisualShapeIndex=vis_id,
                basePosition=s['pos']
            )
            
            # إطار أبيض
            pos = s['pos']
            corners = [
                [pos[0]-0.5, pos[1], pos[2]-0.7],
                [pos[0]+0.5, pos[1], pos[2]-0.7],
                [pos[0]+0.5, pos[1], pos[2]+0.7],
                [pos[0]-0.5, pos[1], pos[2]+0.7]
            ]
            
            for j in range(4):
                p.addUserDebugLine(
                    corners[j],
                    corners[(j+1)%4],
                    [1, 1, 1], lineWidth=2, lifeTime=0
                )
            
            # اسم العالم
            text_pos = [pos[0], pos[1], pos[2] + 0.8]
            p.addUserDebugText(s['name'], text_pos, [1, 1, 1], textSize=1.2, lifeTime=0)

    def reset_pose(self):
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def move_to_target(self, target_pos):
        current = self.pepper.getPosition()
        dx = target_pos[0] - current[0]
        dy = target_pos[1] - current[1]
        
        if abs(dx) > 0.3 or abs(dy) > 0.3:
            self.pepper.move(0.1 * dx, 0, 0.05 * dy)
            return False
        return True

    def wave(self):
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.3)
        self.reset_pose()

    def draw_green_box(self, pos):
        """رسم مربع أخضر حول الصورة"""
        corners = [
            [pos[0]-0.5, pos[1], pos[2]-0.7],
            [pos[0]+0.5, pos[1], pos[2]-0.7],
            [pos[0]+0.5, pos[1], pos[2]+0.7],
            [pos[0]-0.5, pos[1], pos[2]+0.7]
        ]
        
        for i in range(4):
            p.addUserDebugLine(
                corners[i],
                corners[(i+1)%4],
                [0, 1, 0], lineWidth=4, lifeTime=3
            )

    def recognize_and_speak(self, scientist):
        """يتعرف على العالم ويتحدث عنه"""
        fact = random.choice(scientist['facts'])
        text = f"I see {scientist['name']}! He {fact}"
        print(f"🤖 Pepper: {text}")
        self.speak(text)
        self.wave()
        
        # رسم المربع الأخضر
        self.draw_green_box(scientist['pos'])
        
        # كتابة الاسم فوق الصورة
        text_pos = [scientist['pos'][0], scientist['pos'][1], scientist['pos'][2] + 0.9]
        p.addUserDebugText(scientist['name'], text_pos, [0, 1, 0], textSize=1.5, lifeTime=3)

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يتعرف على العلماء!")
        print("="*60 + "\n")
        
        last_move = time.time()
        recognized = [False] * len(self.scientists)
        
        try:
            while self.running:
                if time.time() - last_move > 4:
                    self.pepper.setAngles(["HeadYaw"], [0.3], 0.1)
                    last_move = time.time()
                
                if self.current_target < len(self.scientists):
                    target = self.scientists[self.current_target]
                    
                    if self.move_to_target(target['pos']):
                        if not recognized[self.current_target]:
                            print(f"\n🎯 Pepper وصل إلى {target['name']}")
                            self.recognize_and_speak(target)
                            recognized[self.current_target] = True
                            time.sleep(3)
                        
                        self.current_target += 1
                
                if self.current_target >= len(self.scientists):
                    print("\n🔄 جولة جديدة!")
                    self.current_target = 0
                    recognized = [False] * len(self.scientists)
                    self.speak("Let me look at them again!")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFacesFixed()
    app.run()
