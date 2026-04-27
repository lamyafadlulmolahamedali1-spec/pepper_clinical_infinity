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
import speech_recognition as sr
import tempfile

class PepperFinalSolution:
    def __init__(self):
        print("🚀 تشغيل Pepper مع صور حقيقية وصوت ونص عريض...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات النافذة
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        
        # Pepper واحد
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        p.resetDebugVisualizerCamera(3.5, 50, -30, [0, 0, 1])
        self.reset_pose()
        
        # تحميل العلماء
        self.scientists = []
        self.load_scientists()
        
        # عرض الصور الحقيقية
        self.display_real_images()
        
        self.running = True
        self.current_target = 0
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am ready! Look at the real faces of scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        print("✅ الصوت جاهز")

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def load_scientists(self):
        """تحميل صور العلماء الحقيقية مع معلوماتهم"""
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # مواقع العلماء في المحاكي (مصفوفة)
        positions = [
            [2, -2, 0.5],
            [2, 0, 0.5],
            [2, 2, 0.5],
            [2, -3.5, 0.5],
            [2, 3.5, 0.5],
            [2, -5, 0.5],
            [2, 5, 0.5],
            [2, -6.5, 0.5],
            [2, 6.5, 0.5]
        ]
        
        # معلومات العلماء (حقائق)
        scientist_info = {
            'einstein': {
                'name': 'Albert Einstein',
                'facts': [
                    'developed the theory of relativity',
                    'won the Nobel Prize in Physics in 1921',
                    'his famous equation is E = mc²',
                    'said: Imagination is more important than knowledge',
                    'escaped Nazi Germany to the USA'
                ]
            },
            'marie_curie': {
                'name': 'Marie Curie',
                'facts': [
                    'discovered radium and polonium',
                    'first person to win two Nobel Prizes',
                    'died from radiation exposure',
                    'was the first female professor at Sorbonne',
                    'her notebooks are still radioactive'
                ]
            },
            'newton': {
                'name': 'Isaac Newton',
                'facts': [
                    'formulated the laws of motion',
                    'discovered gravity when an apple fell',
                    'invented calculus',
                    'was president of the Royal Society',
                    'built the first reflecting telescope'
                ]
            },
            'tesla': {
                'name': 'Nikola Tesla',
                'facts': [
                    'invented alternating current',
                    'developed the Tesla coil',
                    'had over 300 patents',
                    'dreamed of wireless electricity',
                    'spoke 8 languages'
                ]
            },
            'hawking': {
                'name': 'Stephen Hawking',
                'facts': [
                    'studied black holes and cosmology',
                    'wrote A Brief History of Time',
                    'had ALS and used a speech synthesizer',
                    'believed aliens might exist',
                    'said: Intelligence is the ability to adapt'
                ]
            },
            'galileo': {
                'name': 'Galileo Galilei',
                'facts': [
                    'improved the telescope',
                    'discovered Jupiter\'s moons',
                    'supported heliocentrism',
                    'was tried by the Inquisition',
                    'said: And yet it moves'
                ]
            },
            'ada': {
                'name': 'Ada Lovelace',
                'facts': [
                    'first computer programmer',
                    'worked on Charles Babbage\'s engine',
                    'wrote the first algorithm',
                    'daughter of poet Lord Byron',
                    'saw potential in computers beyond math'
                ]
            },
            'turing': {
                'name': 'Alan Turing',
                'facts': [
                    'father of computer science',
                    'cracked the Enigma code',
                    'helped win World War II',
                    'created the Turing test',
                    'was persecuted for being gay'
                ]
            },
            'curie': {
                'name': 'Marie Curie',
                'facts': [
                    'already listed above'
                ]
            }
        }
        
        i = 0
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                filepath = os.path.join(images_dir, filename)
                base_name = os.path.splitext(filename)[0].lower()
                
                # البحث عن المعلومات
                info = None
                for key, val in scientist_info.items():
                    if key in base_name:
                        info = val
                        break
                
                if info:
                    # تحميل الصورة كـ texture
                    texture_id = p.loadTexture(filepath)
                    
                    self.scientists.append({
                        'name': info['name'],
                        'facts': info['facts'],
                        'image': filepath,
                        'texture': texture_id,
                        'pos': positions[i % len(positions)]
                    })
                    i += 1

    def display_real_images(self):
        """عرض الصور الحقيقية في المحاكي"""
        for s in self.scientists:
            # إنشاء لوحة لعرض الصورة
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.5, 0.05, 0.7])
            
            # استخدام texture الصورة
            vis_id = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[0.5, 0.05, 0.7],
                rgbaColor=[1, 1, 1, 1],
                textureUniqueId=s['texture']
            )
            
            # وضع الصورة في المكان
            p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=col_id,
                baseVisualShapeIndex=vis_id,
                basePosition=s['pos']
            )
            
            # إطار أبيض حول الصورة
            pos = s['pos']
            corners = [
                [pos[0]-0.52, pos[1], pos[2]-0.72],
                [pos[0]+0.52, pos[1], pos[2]-0.72],
                [pos[0]+0.52, pos[1], pos[2]+0.72],
                [pos[0]-0.52, pos[1], pos[2]+0.72]
            ]
            for i in range(4):
                p.addUserDebugLine(
                    corners[i], corners[(i+1)%4],
                    [1, 1, 1], lineWidth=2, lifeTime=0
                )

    def reset_pose(self):
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def move_to_target(self, target_pos):
        current = self.pepper.getPosition()
        dx = target_pos[0] - current[0]
        dy = target_pos[1] - current[1]
        
        if abs(dx) > 0.2 or abs(dy) > 0.2:
            self.pepper.move(0.1 * dx, 0, 0.05 * dy)
            return False
        return True

    def wave(self):
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.3)
        self.reset_pose()

    def look_at(self, target):
        dx = target[0] - self.pepper.getPosition()[0]
        self.pepper.setAngles(["HeadYaw"], [dx * 0.3], 0.1)

    def draw_recognition(self, scientist):
        """رسم مربع أخضر وكتابة اسم العالم بالأسود العريض"""
        pos = scientist['pos']
        
        # رسم مربع أخضر حول الصورة
        corners = [
            [pos[0]-0.55, pos[1], pos[2]-0.75],
            [pos[0]+0.55, pos[1], pos[2]-0.75],
            [pos[0]+0.55, pos[1], pos[2]+0.75],
            [pos[0]-0.55, pos[1], pos[2]+0.75]
        ]
        for i in range(4):
            p.addUserDebugLine(
                corners[i], corners[(i+1)%4],
                [0, 1, 0], lineWidth=4, lifeTime=5
            )
        
        # كتابة اسم العالم بالأسود العريض فوق الصورة
        text_pos = [pos[0], pos[1], pos[2] + 0.9]
        p.addUserDebugText(
            scientist['name'],
            text_pos,
            [0, 0, 0],  # لون أسود
            textSize=2.0,  # حجم كبير
            lifeTime=5
        )

    def draw_fact(self, scientist, fact):
        """كتابة المعلومة بالأسود العريض فوق Pepper"""
        pepper_pos = self.pepper.getPosition()
        text_pos = [pepper_pos[0], pepper_pos[1], pepper_pos[2] + 1.5]
        
        # المعلومة كاملة
        full_text = f"{scientist['name']}: {fact}"
        
        p.addUserDebugText(
            full_text,
            text_pos,
            [0, 0, 0],  # أسود
            textSize=1.8,
            lifeTime=4
        )

    def run(self):
        print("\n" + "="*70)
        print("🌟 Pepper مع صور حقيقية وصوت ونص عريض")
        print("="*70 + "\n")
        
        last_move = time.time()
        recognized = [False] * len(self.scientists)
        current_fact_index = 0
        
        try:
            while self.running:
                # حركة كل 3 ثواني
                if time.time() - last_move > 3:
                    self.look_at([2, 0, 0.5])
                    last_move = time.time()
                
                # التنقل بين العلماء
                if self.current_target < len(self.scientists):
                    target = self.scientists[self.current_target]
                    
                    if self.move_to_target(target['pos']):
                        if not recognized[self.current_target]:
                            print(f"\n🔍 Pepper: {target['name']}")
                            
                            # رسم المربع الأخضر والاسم
                            self.draw_recognition(target)
                            
                            # اختيار حقيقة عشوائية
                            fact = random.choice(target['facts'])
                            full_text = f"This is {target['name']}! He {fact}"
                            
                            # طباعة في التيرمينال
                            print(f"💬 {full_text}")
                            
                            # نطق بالصوت
                            self.speak(full_text)
                            
                            # كتابة المعلومة فوق Pepper
                            self.draw_fact(target, fact)
                            
                            # حركة يد
                            self.wave()
                            
                            recognized[self.current_target] = True
                            time.sleep(4)
                        
                        self.current_target += 1
                
                # إعادة التشغيل
                if self.current_target >= len(self.scientists):
                    print("\n🔄 جولة جديدة!")
                    self.current_target = 0
                    recognized = [False] * len(self.scientists)
                    self.speak("Let's look at them again!")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFinalSolution()
    app.run()
