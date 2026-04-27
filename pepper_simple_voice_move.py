#!/usr/bin/env python3
"""
Pepper Simple - بيتحرك، بيرقص، بيتكلم، ويسمع
"""

import time
import random
import math
import threading
import speech_recognition as sr
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== الصوت ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            print("🔊 صوت بيبر جاهز!")
        except:
            print("⚠️ الصوت مش شغال")
    
    def speak(self, text):
        print(f"🤖 بيبر: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass

# ========== الاستماع ==========
class Listener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 الميكروفون جاهز!")
        except:
            print("⚠️ الميكروفون مش شغال")
            self.mic = None
    
    def listen(self):
        if not self.mic:
            return None
        try:
            with self.mic as source:
                print("\n🎤 اسمع...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio, language='en-US')
            print(f"\r   ✅ سمعت: '{text}'")
            return text.lower()
        except:
            print("\r   ❌ ما سمعت شي", end="", flush=True)
            return None

# ========== بيبر في PyBullet ==========
class PepperRobot:
    def __init__(self):
        print("🤖 تشغيل بيبر...")
        self.sim = SimulationManager()
        self.client = self.sim.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.loadURDF("plane.urdf")
        
        self.pepper = self.sim.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        print("✅ بيبر جاهز!")
        
        # بالونات
        colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
        self.balloons = []
        for i in range(10):
            x = random.uniform(-3, 3)
            y = random.uniform(-2.5, 2.5)
            vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
            ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
            self.balloons.append(ball)
        
        p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])
        
        self.running = True
        self.is_dancing = False
        self.t = 0
        
        threading.Thread(target=self._walk, daemon=True).start()
        threading.Thread(target=self._update_balloons, daemon=True).start()
    
    def _walk(self):
        while self.running:
            if not self.is_dancing:
                self.t += 0.02
                x = 2.5 * math.cos(self.t * 0.35)
                y = 2.0 * math.sin(self.t * 0.5)
                try:
                    self.pepper.setTranslation([x, y, 0.8])
                except:
                    pass
            time.sleep(0.05)
    
    def _update_balloons(self):
        while self.running:
            for b in self.balloons:
                pos, _ = p.getBasePositionAndOrientation(b)
                new_z = pos[2] + 0.008
                if new_z > 1.6:
                    new_z = 0.3
                p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
            p.stepSimulation()
            time.sleep(1/60.)
    
    def dance(self):
        self.is_dancing = True
        for _ in range(3):
            for angle in [0.5, 1.0, 0.5, 0]:
                try:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.1)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                    time.sleep(0.15)
                except:
                    pass
        try:
            self.pepper.setAngles("LShoulderPitch", 0, 0.2)
            self.pepper.setAngles("RShoulderPitch", 0, 0.2)
        except:
            pass
        self.is_dancing = False
    
    def wave(self):
        for _ in range(2):
            try:
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.3)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.3)
            except:
                pass
    
    def move_forward(self):
        try:
            pos = self.pepper.getPosition()
            self.pepper.setTranslation([pos[0] + 0.4, pos[1], pos[2]])
        except:
            pass
    
    def stop(self):
        self.running = False

# ========== الرئيسي ==========
def main():
    print("\n" + "="*50)
    print("🤖 PEPPER - يتحرك، يرقص، يتكلم، ويسمع")
    print("="*50)
    print("قل: dance, wave, walk, hello, goodbye")
    print("="*50 + "\n")
    
    # تشغيل بيبر
    pepper = PepperRobot()
    time.sleep(2)
    
    # الصوت
    voice = Voice()
    listener = Listener()
    
    voice.speak("Hello! I'm Pepper! I can dance, wave, and walk! Say dance to see me dance!")
    
    while True:
        try:
            text = listener.listen()
            
            if text is None:
                continue
            
            if "goodbye" in text or "exit" in text:
                voice.speak("Goodbye! It was nice talking with you!")
                break
            
            if "dance" in text:
                voice.speak("Let's dance!")
                pepper.dance()
                continue
            
            if "wave" in text:
                voice.speak("Waving hello!")
                pepper.wave()
                continue
            
            if "walk" in text:
                voice.speak("Walking forward!")
                pepper.move_forward()
                continue
            
            if "hello" in text:
                voice.speak("Hello! How are you today?")
                continue
            
            voice.speak("I can dance, wave, or walk. What would you like?")
            
        except KeyboardInterrupt:
            voice.speak("Goodbye!")
            break
    
    pepper.stop()
    print("\n✅ تم الإغلاق")

if __name__ == "__main__":
    main()
