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

class PepperSmoothTour:
    def __init__(self):
        print("🚀 تشغيل Pepper في جولة سلسة...")
        
        # الصوت
        self.init_voice()
        
        # محاكي خفيف
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات خفيفة
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1)
        p.resetDebugVisualizerCamera(4.0, 60, -30, [0, 0, 1])
        
        # Pepper
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-3, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضعية البداية
        self.reset_pose()
        
        # تحميل العلماء
        self.scientists = self.load_scientists()
        
        # متغيرات الحركة
        self.walk_direction = 1  # 1 = يمين, -1 = يسار
        self.last_wave_time = time.time()
        self.last_speech_time = time.time()
        self.current_scientist_index = 0
        
        self.running = True
        
        print(f"✅ تم تحميل {len(self.scientists)} عالم")
        self.speak("Welcome! I will walk and talk about scientists.")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)
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

    def reset_pose(self):
        """وضعية طبيعية"""
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.1], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.3, 1.2], 0.1)

    def wave_right(self):
        """موجة باليمين"""
        self.pepper.setAngles(["RShoulderPitch"], [-0.5], 0.3)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [0.3], 0.3)
        self.reset_pose()

    def wave_left(self):
        """موجة باليسار"""
        self.pepper.setAngles(["LShoulderPitch"], [0.8], 0.3)
        time.sleep(0.2)
        self.pepper.setAngles(["LShoulderPitch"], [1.57], 0.3)
        self.reset_pose()

    def wave_both(self):
        """موجة باليدين"""
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], [-0.5, 0.8], 0.3)
        time.sleep(0.3)
        self.reset_pose()

    def look_left(self):
        """ينظر لليسار"""
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.2)
        time.sleep(0.2)

    def look_right(self):
        """ينظر لليمين"""
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.2)
        time.sleep(0.2)

    def look_center(self):
        """ينظر للوسط"""
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.2)

    def walk_continuous(self):
        """المشي المستمر"""
        # المشي في اتجاه دائري
        self.pepper.move(0.15, 0, 0.1 * self.walk_direction)
        
        # تغيير الاتجاه كل 10 ثواني
        if random.random() < 0.01:
            self.walk_direction *= -1

    def load_scientists(self):
        """تحميل العلماء مع معلوماتهم"""
        scientists = [
            {
                'name': 'Albert Einstein',
                'facts': [
                    'developed the theory of relativity',
                    'won the Nobel Prize in Physics',
                    'had the famous equation E=mc²',
                    'said: Imagination is more important than knowledge'
                ]
            },
            {
                'name': 'Marie Curie',
                'facts': [
                    'discovered radium and polonium',
                    'first person to win two Nobel Prizes',
                    'died from radiation exposure',
                    'was the first female professor at Sorbonne'
                ]
            },
            {
                'name': 'Isaac Newton',
                'facts': [
                    'formulated the laws of motion',
                    'discovered gravity',
                    'invented calculus',
                    'built the first reflecting telescope'
                ]
            },
            {
                'name': 'Nikola Tesla',
                'facts': [
                    'invented alternating current',
                    'developed the Tesla coil',
                    'had over 300 patents',
                    'dreamed of wireless electricity'
                ]
            },
            {
                'name': 'Stephen Hawking',
                'facts': [
                    'studied black holes',
                    'wrote A Brief History of Time',
                    'had ALS and used a speech synthesizer',
                    'believed aliens might exist'
                ]
            }
        ]
        return scientists

    def show_text_above(self, text, duration=3):
        """عرض نص فوق Pepper"""
        pos = self.pepper.getPosition()
        p.addUserDebugText(
            text,
            [pos[0], pos[1], pos[2] + 1.8],
            [0, 0, 0],
            textSize=1.5,
            lifeTime=duration
        )

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يجول ويتكلم عن العلماء")
        print("="*60 + "\n")
        
        self.speak("Hello! I will walk and talk about famous scientists.")
        
        try:
            while self.running:
                # 1. المشي المستمر
                self.walk_continuous()
                
                # 2. حركات الرأس المستمرة
                if random.random() < 0.02:
                    if random.choice([True, False]):
                        self.look_left()
                    else:
                        self.look_right()
                    time.sleep(0.5)
                    self.look_center()
                
                # 3. التحدث عن عالم كل 8 ثواني
                current_time = time.time()
                if current_time - self.last_speech_time > 8:
                    scientist = self.scientists[self.current_scientist_index]
                    fact = random.choice(scientist['facts'])
                    
                    # الكلام
                    speech = f"This is {scientist['name']}. {fact}"
                    print(f"💬 {speech}")
                    self.speak(speech)
                    
                    # نص فوق Pepper
                    self.show_text_above(f"{scientist['name']}: {fact[:30]}...", 4)
                    
                    self.current_scientist_index += 1
                    if self.current_scientist_index >= len(self.scientists):
                        self.current_scientist_index = 0
                    
                    self.last_speech_time = current_time
                
                # 4. حركات اليدين كل 5 ثواني
                if current_time - self.last_wave_time > 5:
                    if random.choice([True, False]):
                        self.wave_right()
                    else:
                        self.wave_left()
                    self.last_wave_time = current_time
                
                time.sleep(0.05)  # تحديث سريع لحركة سلسة
                
        except KeyboardInterrupt:
            print("\n\n👋 إيقاف Pepper...")
            self.speak("Goodbye! It was nice walking with you!")
        finally:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperSmoothTour()
    app.run()
