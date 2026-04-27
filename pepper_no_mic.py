#!/usr/bin/env python3
"""
Pepper في غرفة مع أطفال - بدون ميكروفون (للتجربة)
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
from qibullet import SimulationManager
import pyttsx3

class PepperNoMic:
    def __init__(self):
        print("🚀 تشغيل Pepper بدون ميكروفون...")
        
        # الصوت (للخروج فقط)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # بناء غرفة بسيطة
        self.build_simple_room()
        
        # إنشاء Pepper
        self.create_pepper()
        
        # إنشاء أطفال بسيطين
        self.kids = []
        self.create_simple_kids()
        
        print("✅ Pepper جاهز!")
        self.speak("Hello! I'm Pepper!")

    def speak(self, text):
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()

    def build_simple_room(self):
        """غرفة بسيطة"""
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])

    def create_pepper(self):
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -2, 0.2], quaternion=[0, 0, 0, 1]
        )

    def create_simple_kids(self):
        """أطفال بسيطون (مكعبات)"""
        positions = [[1.5, 1.5, 0.2], [-1, 2, 0.2], [2, -2, 0.2]]
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1]]
        names = ["Emma", "Liam", "Sophia"]
        
        for pos, color, name in zip(positions, colors, names):
            # جسم الطفل (مكعب)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.4], rgbaColor=color)
            kid = p.createMultiBody(baseMass=1, baseVisualShapeIndex=vis_id, basePosition=pos)
            
            # رأس (كرة)
            head_pos = [pos[0], pos[1], pos[2] + 0.5]
            head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1,0.9,0.8,1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis, basePosition=head_pos)
            
            # اسم
            p.addUserDebugText(name, [pos[0], pos[1], pos[2] + 0.8], [0,0,0], textSize=1)
            
            self.kids.append(kid)

    def wave(self):
        for i in range(3):
            self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
            time.sleep(0.2)
            self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
            time.sleep(0.2)

    def show_text(self, text):
        pos = self.pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)

    def run(self):
        print("\n" + "="*60)
        print("🌟 PEPPER في الغرفة - بدون ميكروفون")
        print("="*60 + "\n")
        print("🔹 Pepper سيتحرك ويتكلم كل 5 ثواني")
        
        self.speak("I'm here with the children!")
        
        last_speak = time.time()
        
        try:
            while True:
                # حركة Pepper
                self.pepper.move(0.05, 0, 0.02)
                
                # كل 5 ثواني يتكلم
                if time.time() - last_speak > 5:
                    texts = [
                        "Hello children!",
                        "Let's play together!",
                        "I love this room!",
                        "You're all so wonderful!"
                    ]
                    text = random.choice(texts)
                    print(f"🤖 Pepper: {text}")
                    self.speak(text)
                    self.show_text(text)
                    self.wave()
                    last_speak = time.time()
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = PepperNoMic()
    pepper.run()
