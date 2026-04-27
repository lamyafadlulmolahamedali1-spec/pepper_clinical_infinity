#!/usr/bin/env python3
"""
Pepper في غرفة عصرية مع أطفال - نسخة بدون OpenCV GUI
"""

import time
import pybullet as p
import pybullet_data
import threading
import random
import queue
import numpy as np
import os
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr

# الذكاء الاصطناعي
try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI غير مثبت")

# ========== الطفل الذكي ==========
class SmartKid:
    def __init__(self, name, age, color, position):
        self.name = name
        self.age = age
        self.color = color
        self.position = position
        self.body_id = None
        self.head_id = None
        
    def create_in_sim(self):
        # جسم الطفل
        col_id = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.2, height=0.8)
        vis_id = p.createVisualShape(p.GEOM_CYLINDER, radius=0.2, length=0.8, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=3, baseCollisionShapeIndex=col_id,
                                         baseVisualShapeIndex=vis_id, 
                                         basePosition=self.position)
        
        # رأس الطفل
        head_pos = [self.position[0], self.position[1], self.position[2] + 0.4]
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.9, 0.8, 1])
        self.head_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_vis,
                                        basePosition=head_pos)
        
        # اسم الطفل
        p.addUserDebugText(f"{self.name} ({self.age}y)", 
                          [self.position[0], self.position[1], self.position[2] + 0.8],
                          [0, 0, 0], textSize=1.2)

# ========== الغرفة ==========
class ModernRoom:
    def __init__(self):
        # أرضية
        floor_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], 
                                        rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseVisualShapeIndex=floor_vis, basePosition=[0, 0, 0])

# ========== Pepper الذكي ==========
class SmartPepper:
    def __init__(self):
        print("🚀 تشغيل Pepper الذكي...")
        
        # الصوت
        self.init_voice()
        
        # الميكروفون
        self.init_microphone()
        
        # المحاكي
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # الغرفة
        self.room = ModernRoom()
        
        # إنشاء Pepper
        self.create_pepper()
        
        # إنشاء الأطفال
        self.kids = []
        self.create_kids()
        
        # متغيرات التشغيل
        self.running = True
        self.speech_queue = queue.Queue()
        
        # بدء الاستماع
        self.start_listening()
        
        print("✅ Pepper جاهز!")
        self.speak("Hello everyone! I'm Pepper!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
    
    def init_microphone(self):
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("🔄 معايرة الميكروفون...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ الميكروفون جاهز")
        except:
            print("⚠️ مشكلة في الميكروفون")
            self.microphone = None
    
    def create_pepper(self):
        self.pepper = self.sim_manager.spawnPepper(
            self.client, translation=[-3, -2, 0.2], quaternion=[0, 0, 0, 1]
        )
    
    def create_kids(self):
        kids_data = [
            ("Emma", 4, [1.5, 1.5, 0.2], [1, 0.8, 0.8, 1]),
            ("Liam", 5, [-1, 2, 0.2], [0.8, 1, 0.8, 1]),
            ("Sophia", 3, [2, -2, 0.2], [0.8, 0.8, 1, 1]),
            ("Noah", 6, [-2, -1, 0.2], [1, 1, 0.8, 1])
        ]
        
        for name, age, pos, color in kids_data:
            kid = SmartKid(name, age, color, pos)
            kid.create_in_sim()
            self.kids.append(kid)
            print(f"✅ طفل: {name}")
    
    def start_listening(self):
        def listen_loop():
            if not self.microphone:
                return
            while self.running:
                try:
                    with self.microphone as source:
                        print("\n🎤 استماع...")
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio)
                    print(f"📝 أنت: {text}")
                    self.speech_queue.put(text)
                except:
                    pass
                time.sleep(0.1)
        
        threading.Thread(target=listen_loop, daemon=True).start()
    
    def speak(self, text):
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()
    
    def show_text(self, text):
        pos = self.pepper.getPosition()
        p.addUserDebugText(text, [pos[0], pos[1], pos[2] + 2.0], [0,0,0], textSize=1.2, lifeTime=3)
    
    def wave(self):
        for i in range(2):
            try:
                self.pepper.setAngles(["RShoulderPitch"], [-0.7], 0.5)
                time.sleep(0.2)
                self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.5)
                time.sleep(0.2)
            except:
                pass
    
    def get_response(self, text):
        text_lower = text.lower()
        if "hello" in text_lower or "hi" in text_lower:
            return "Hello! Nice to meet you!"
        elif "name" in text_lower:
            names = ", ".join([k.name for k in self.kids])
            return f"I'm Pepper! I'm with {names}"
        elif "play" in text_lower:
            return "Let's play together!"
        elif "how are you" in text_lower:
            return "I'm great! The children are wonderful!"
        else:
            return random.choice(["That's interesting!", "Tell me more!", "Really?", "Wow!"])
    
    def process_speech(self, text):
        response = self.get_response(text)
        print(f"🤖 Pepper: {response}")
        self.speak(response)
        self.show_text(response)
        self.wave()
    
    def run(self):
        print("\n" + "="*60)
        print("🌟 PEPPER في الغرفة مع الأطفال")
        print("="*60 + "\n")
        print("🎤 تحدث الآن - Pepper سيسمعك\n")
        
        self.speak("I can hear you! Talk to me!")
        
        try:
            while self.running:
                if not self.speech_queue.empty():
                    text = self.speech_queue.get()
                    self.process_speech(text)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    pepper = SmartPepper()
    pepper.run()
