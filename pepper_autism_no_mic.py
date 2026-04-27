#!/usr/bin/env python3
"""
Pepper مع أطفال توحديين - بدون ميكروفون (للتجربة)
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

# ========== طفل Pepper ==========
class PepperKid:
    def __init__(self, name, age, personality, color, position, sim_manager, client):
        self.name = name
        self.age = age
        self.personality = personality
        self.color = color
        self.position = position
        self.sim_manager = sim_manager
        self.client = client
        
        # إنشاء Pepper كطفل
        self.pepper = sim_manager.spawnPepper(
            client, translation=position, quaternion=[0, 0, 0, 1]
        )
        
        print(f"✅ طفل Pepper: {name} ({age} yrs) - {personality}")

# ========== الغرفة ==========
class PlayRoom:
    def __init__(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.8, 0.8, 0.8, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])

# ========== Pepper الرئيسي ==========
class MainPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper مع أطفال توحديين...")
        
        # الصوت
        self.voice = VoiceEngine()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة
        self.room = PlayRoom()
        
        # Pepper الرئيسي
        self.main_pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -3, 0.2], quaternion=[0, 0, 0, 1]
        )
        
        # أطفال Pepper
        self.kids = self.create_kids()
        
        print("✅ Pepper جاهز!")
        self.voice.speak("Hello everyone! Let's play together!")

    def create_kids(self):
        kids_data = [
            ("Emma", 4, "happy", [1, 1, 0.8, 1], [2, 2, 0.2]),
            ("Liam", 5, "curious", [0.8, 1, 1, 1], [-2, 3, 0.2]),
            ("Sophia", 3, "shy", [1, 0.8, 1, 1], [3, -2, 0.2])
        ]
        
        kids = []
        for name, age, personality, color, pos in kids_data:
            kid = PepperKid(name, age, personality, color, pos, self.sim_manager, self.client)
            kids.append(kid)
        
        return kids

    def talk_to_kid(self, kid):
        """التحدث مع طفل"""
        texts = [
            f"Hi {kid.name}! How are you?",
            f"{kid.name}, let's play!",
            f"Hello {kid.name}!",
            f"{kid.name}, you're so cute!"
        ]
        text = random.choice(texts)
        print(f"🤖 Pepper: {text}")
        self.voice.speak(text)

    def run(self):
        print("\n" + "="*70)
        print("🌟 PEPPER مع أطفال توحديين")
        print("="*70 + "\n")
        
        last_interaction = time.time()
        
        try:
            while True:
                if time.time() - last_interaction > 5:
                    kid = random.choice(self.kids)
                    self.talk_to_kid(kid)
                    last_interaction = time.time()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = MainPepper()
    pepper.run()
