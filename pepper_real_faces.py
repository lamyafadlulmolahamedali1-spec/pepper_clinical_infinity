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

class PepperRealFaces:
    def __init__(self):
        print("🚀 تشغيل Pepper مع صور حقيقية للعلماء...")
        
        # الصوت
        self.init_voice()
        
        # محاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # نافذة حرة
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        p.resetDebugVisualizerCamera(3.5, 50, -30, [0, 0, 1])
        self.reset_pose()
        
        # تحميل صور العلماء الحقيقية
        self.load_scientist_images()
        
        # YOLO للتعرف (اختياري - نقدر نستخدم DeepFace بدله)
        # لكن بما إن الصور في المحاكي، هنستخدم DeepFace مباشرة
        
        self.running = True
        self.current_target = 0
        self.detected_faces = []
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("I am ready to recognize real faces of scientists!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def load_scientist_images(self):
        """تحميل صور العلماء الحقيقية"""
        self.scientists = []
        images_dir = os.path.expanduser("~/pepper_duo/data/known_faces/")
        
        # معلومات العلماء
        scientist_info = {
            'einstein': {'name': 'Albert Einstein', 'facts': ['developed relativity', 'won Nobel Prize', 'E=mc²']},
            'marie_curie': {'name': 'Marie Curie', 'facts': ['discovered radium', 'two Nobel Prizes', 'died from radiation']},
            'newton': {'name': 'Isaac Newton', 'facts': ['laws of motion', 'gravity', 'calculus']},
            'tesla': {'name': 'Nikola Tesla', 'facts': ['alternating current', 'Tesla coil', 'wireless energy']},
            'hawking': {'name': 'Stephen Hawking', 'facts': ['black holes', 'A Brief History of Time', 'ALS']}
        }
        
        positions = [
            [2, -1.5, 0.5],
            [2, 0, 0.5],
            [2, 1.5, 0.5],
            [2, 3, 0.5],
            [2, -3, 0.5]
        ]
        
        i = 0
        for filename in os.listdir(images_dir):
            if filename.endswith(('.jpg', '.png', '.jpeg')):
                # استخراج الاسم من الملف
                base_name = os.path.splitext(filename)[0].lower()
                
                # البحث عن المعلومات
                info = None
                for key, val in scientist_info.items():
                    if key in base_name:
                        info = val
                        break
                
                if info:
                    filepath = os.path.join(images_dir, filename)
                    
                    # إنشاء texture من الصورة
                    texture_id = p.loadTexture(filepath)
                    
                    scientist = {
                        'name': info['name'],
                        'facts': info['facts'],
                        'image': filepath,
                        'texture': texture_id,
                        'pos': positions[i % len(positions)]
                    }
                    self.scientists.append(scientist)
                    i += 1
        
        # عرض الصور في المحاكي
        self.display_real_images()

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
            
            # وضع اللوحة في المكان المحدد
            body_id = p.createMultiBody(
                baseMass=0,
                baseCollisionShapeIndex=col_id,
                baseVisualShapeIndex=vis_id,
                basePosition=s['pos']
            )
            
            # إطار أبيض حول الصورة (شكل برواز)
            frame_pos = [s['pos'][0], s['pos'][1], s['pos'][2]]
            p.addUserDebugLine(
                [frame_pos[0]-0.52, frame_pos[1], frame_pos[2]-0.72],
                [frame_pos[0]+0.52, frame_pos[1], frame_pos[2]+0.72],
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

    def look_at(self, target):
        dx = target[0] - self.pepper.getPosition()[0]
        self.pepper.setAngles(["HeadYaw"], [dx * 0.3], 0.1)

    def recognize_face(self, scientist):
        """يتعرف على الوجه باستخدام DeepFace"""
        try:
            # استخدام DeepFace للتحقق
            result = DeepFace.verify(
                img1_path=scientist['image'],
                img2_path=scientist['image'],  # مؤقت - هنا المفروض صورة من كاميرا Pepper
                enforce_detection=False
            )
            
            if result['verified']:
                # رسم مربع أخضر حول الصورة في المحاكي
                pos = scientist['pos']
                box_corners = [
                    [pos[0]-0.5, pos[1], pos[2]-0.7],
                    [pos[0]+0.5, pos[1], pos[2]-0.7],
                    [pos[0]+0.5, pos[1], pos[2]+0.7],
                    [pos[0]-0.5, pos[1], pos[2]+0.7]
                ]
                
                # رسم مربع أخضر
                for i in range(4):
                    p.addUserDebugLine(
                        box_corners[i],
                        box_corners[(i+1)%4],
                        [0, 1, 0], lineWidth=3, lifeTime=2
                    )
                
                # كتابة الاسم فوق الصورة
                text_pos = [pos[0], pos[1], pos[2] + 0.8]
                p.addUserDebugText(
                    scientist['name'],
                    text_pos,
                    [0, 1, 0], textSize=1.5, lifeTime=3
                )
                
                return True
        except:
            return False
        return False

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يتعرف على صور حقيقية للعلماء!")
        print("="*60 + "\n")
        
        last_move = time.time()
        recognized = [False] * len(self.scientists)
        
        try:
            while self.running:
                # حركة مستمرة
                if time.time() - last_move > 4:
                    self.look_at([2, 0, 0.5])
                    last_move = time.time()
                
                # التنقل بين العلماء
                if self.current_target < len(self.scientists):
                    target = self.scientists[self.current_target]
                    
                    # التحرك نحو العالم
                    if self.move_to_target(target['pos']):
                        if not recognized[self.current_target]:
                            print(f"\n🔍 Pepper يفحص {target['name']}...")
                            
                            # التعرف على الوجه
                            if self.recognize_face(target):
                                print(f"✅ تم التعرف على: {target['name']}")
                                fact = random.choice(target['facts'])
                                text = f"I see {target['name']}! He {fact}"
                                print(f"🤖 Pepper: {text}")
                                self.speak(text)
                                self.wave()
                                recognized[self.current_target] = True
                            else:
                                print(f"❌ لم أتعرف على {target['name']}")
                            
                            time.sleep(3)
                        
                        self.current_target += 1
                
                # إعادة التشغيل
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
    app = PepperRealFaces()
    app.run()
