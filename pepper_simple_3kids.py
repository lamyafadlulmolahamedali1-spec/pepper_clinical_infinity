#!/usr/bin/env python3
"""
Pepper مع 3 أطفال فقط - نسخة بسيطة ومضمونة
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import math
from qibullet import SimulationManager
import pyttsx3

# ========== محرك الصوت ==========
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.lock = threading.Lock()
    
    def speak(self, text):
        def _speak():
            with self.lock:
                self.engine.say(text)
                self.engine.runAndWait()
        threading.Thread(target=_speak, daemon=True).start()

# ========== طفل Pepper (بدون حركة - ثابت) ==========
class PepperKid:
    def __init__(self, name, age, color, position, sim_manager, client):
        self.name = name
        self.age = age
        self.color = color
        self.position = position
        self.client = client
        
        # إنشاء Pepper كطفل
        self.pepper = sim_manager.spawnPepper(
            client, translation=position, quaternion=[0, 0, 0, 1]
        )
        
        # اسم الطفل
        p.addUserDebugText(f"{name} ({age})", 
                          [position[0], position[1], position[2] + 1.5],
                          [0, 0, 0], textSize=1.2)
        
        print(f"✅ طفل: {name}")

# ========== غرفة بسيطة ==========
class SimpleRoom:
    def __init__(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])
        
        # جدار خلفي
        wall_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.2, 3], 
                                        rgbaColor=[0.9, 0.8, 0.7, 1])
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, -5, 1.5])
        
        # جدار أمامي
        p.createMultiBody(baseVisualShapeIndex=wall_vis, basePosition=[0, 5, 1.5])

# ========== Pepper الرئيسي ==========
class MainPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper مع 3 أطفال...")
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # غرفة بسيطة
        self.room = SimpleRoom()
        
        # Pepper الرئيسي
        self.main_pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -2, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # 3 أطفال فقط
        self.kids = self.create_kids()
        
        # نقطة واحدة للتجوال (اختبار)
        self.target_point = [3, 2, 0.2]
        self.reached_target = False
        
        print("✅ Pepper جاهز!")
        self.voice.speak("Hello children!")

    def create_kids(self):
        # 3 أطفال فقط
        kids_data = [
            ("Emma", 4, [1, 0.5, 0.5, 1], [2, 2, 0.2]),
            ("Liam", 5, [0.5, 1, 0.5, 1], [-2, 2, 0.2]),
            ("Sophia", 3, [0.5, 0.5, 1, 1], [3, -2, 0.2])
        ]
        
        kids = []
        for name, age, color, pos in kids_data:
            kid = PepperKid(name, age, color, pos, self.sim_manager, self.client)
            kids.append(kid)
        
        return kids

    def move_towards(self, target):
        """تحريك Pepper نحو هدف"""
        current = self.main_pepper.getPosition()
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0.5:
            self.main_pepper.move(0.1 * dx / dist, 0, 0.05 * math.atan2(dy, dx))
            return False
        return True

    def talk_to_random_kid(self):
        """التحدث مع طفل عشوائي"""
        kid = random.choice(self.kids)
        texts = [
            f"Hi {kid.name}!",
            f"Hello {kid.name}!",
            f"{kid.name}, let's play!"
        ]
        text = random.choice(texts)
        print(f"🤖 Pepper: {text}")
        self.voice.speak(text)

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع 3 أطفال")
        print("="*70 + "\n")
        
        last_talk = time.time()
        
        try:
            while True:
                # Pepper يتحرك نحو الهدف
                if not self.reached_target:
                    self.reached_target = self.move_towards(self.target_point)
                else:
                    # إذا وصل، يتحرك لمكان آخر
                    self.target_point = [-3, -2, 0.2]
                    self.reached_target = self.move_towards(self.target_point)
                
                # يتكلم كل 5 ثواني
                if time.time() - last_talk > 5:
                    self.talk_to_random_kid()
                    last_talk = time.time()
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = MainPepper()
    pepper.run()
