#!/usr/bin/env python3
"""
Pepper Balloon Chaser - النسخة المتطورة
- بيبر في غرفة مع أثاث وشخصيات (يوسف، أحمد)
- 15 بالونة ملونة تطير
- مشاريع AI مفعلة محلياً
- يوتيوب، صور، أغاني
"""

import time
import threading
import random
import math
import requests
import webbrowser
import urllib.parse
import speech_recognition as sr
import pyttsx3
import queue
import os
import subprocess
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== المشاريع المحلية ==========
LOCAL_PROJECTS = {
    "شات": {"url": "http://localhost:3000", "desc": "واجهة محادثة ذكاء اصطناعي"},
    "كويز": {"url": "http://localhost:5001", "desc": "ألعاب اختبارات تعليمية"},
    "صوت": {"url": "http://localhost:5003", "desc": "دردشة صوتية"},
    "يوتيوب": {"url": "http://localhost:5004", "desc": "تحدث مع فيديوهات يوتيوب"},
    "رسم": {"url": "http://localhost:5005", "desc": "رسم بالذكاء الاصطناعي"},
    "توحد": {"url": "http://localhost:5006", "desc": "دعم الأطفال المصابين بالتوحد"},
}

# ========== فئة الصوت ==========
class VoiceHandler:
    def __init__(self):
        self.engine = None
        self.recognizer = None
        self.microphone = None
        self.has_mic = False
        
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 140)
            print("✅ الصوت جاهز")
        except:
            print("⚠️ مشكلة في الصوت")
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self.has_mic = True
            print("✅ الميكروفون جاهز")
        except:
            print("⚠️ لا يوجد ميكروفون")
    
    def speak(self, text):
        print(f"\n🤖 بيبر: {text}")
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except:
                pass
    
    def listen(self):
        if not self.has_mic:
            return None
        try:
            with self.microphone as source:
                print("\n🎤 أسمعك...", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio, language="ar-SA")
            print(f"\r✅ قلت: {text}")
            return text.lower()
        except:
            print("\r❌ لم أفهم", end="", flush=True)
            return None

# ========== بيبر الروبوت ==========
class PepperRobot:
    def __init__(self):
        print("🤖 جاري تشغيل بيبر...")
        self.running = True
        self.t = 0
        self.characters = []
        
        try:
            self.sim = SimulationManager()
            self.client = self.sim.launchSimulation(gui=True)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.setRealTimeSimulation(1)
            p.setGravity(0, 0, -9.81)
            p.loadURDF("plane.urdf")
            
            # أثاث
            table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.5, 0.3], rgbaColor=[0.6, 0.4, 0.2, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_vis, basePosition=[1.5, 1.2, 0.3])
            
            chair_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.4], rgbaColor=[0.5, 0.3, 0.1, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_vis, basePosition=[1.5, 1.8, 0.2])
            
            shelf_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[1.0, 0.2, 0.8], rgbaColor=[0.4, 0.2, 0.1, 1])
            p.createMultiBody(baseMass=0, baseVisualShapeIndex=shelf_vis, basePosition=[-1.8, -1.5, 0.4])
            
            # شخصيات: يوسف (أزرق)، أحمد (أخضر)
            yusuf_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[0.2, 0.4, 0.8, 1])
            yusuf = p.createMultiBody(baseMass=0, baseVisualShapeIndex=yusuf_vis, basePosition=[2.0, -1.0, 0.2])
            
            ahmed_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[0.2, 0.7, 0.3, 1])
            ahmed = p.createMultiBody(baseMass=0, baseVisualShapeIndex=ahmed_vis, basePosition=[2.2, -1.4, 0.2])
            
            self.characters = [yusuf, ahmed]
            
            # بيبر
            self.pepper = self.sim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand", 0.5)
            time.sleep(0.5)
            
            # بالونات
            colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1], 
                      [1, 1, 0.2, 1], [1, 0.5, 0.2, 1], [0.8, 0.2, 0.8, 1]]
            self.balloons = []
            for i in range(15):
                x = random.uniform(-3, 3)
                y = random.uniform(-2.5, 2.5)
                vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
                ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5, 1.6)])
                self.balloons.append(ball)
            
            p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-28, cameraTargetPosition=[0, 0, 0.8])
            
            print("✅ بيبر جاهز! معه 15 بالونة ويوسف وأحمد في الغرفة!")
            threading.Thread(target=self._animate, daemon=True).start()
            
        except Exception as e:
            print(f"⚠️ مشكلة: {e}")
    
    def _animate(self):
        while self.running:
            try:
                self.t += 0.02
                x = 2.2 * math.cos(self.t * 0.35)
                y = 1.8 * math.sin(self.t * 0.45)
                self.pepper.setTranslation([x, y, 0.85])
                
                for i, char in enumerate(self.characters):
                    char_x = 2.0 + 0.1 * math.sin(self.t * 0.8 + i)
                    p.resetBasePositionAndOrientation(char, [char_x, -1.2, 0.2], [0, 0, 0, 1])
                
                for b in self.balloons:
                    pos, _ = p.getBasePositionAndOrientation(b)
                    new_z = pos[2] + 0.008
                    if new_z > 1.7:
                        new_z = 0.45
                    p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0, 0, 0, 1])
                
                p.stepSimulation()
                time.sleep(0.05)
            except:
                pass
    
    def dance(self):
        try:
            for _ in range(4):
                for angle in [0.5, 1.0, 0.5, 0]:
                    self.pepper.setAngles("LShoulderPitch", angle, 0.15)
                    self.pepper.setAngles("RShoulderPitch", angle, 0.15)
                    time.sleep(0.12)
        except:
            pass
    
    def wave(self):
        try:
            for _ in range(3):
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.25)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.25)
        except:
            pass
    
    def stop(self):
        self.running = False

# ========== وظائف مساعدة ==========
def search_youtube(query):
    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")

def search_images(query):
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}&tbm=isch")

def play_song(song):
    webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(song + ' اغنية')}")

# ========== AI ==========
def get_ai_response(msg):
    try:
        data = {"model": "openai", "messages": [{"role": "user", "content": msg}]}
        r = requests.post("https://text.pollinations.ai/v1/chat/completions", json=data, timeout=5)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"][:200]
    except:
        pass
    return random.choice(["جميل! أخبرني المزيد 😊", "أنا معك! ماذا تريد أن تفعل؟ 🌟", "عندي مشاريع كثيرة! قول 'عندك شنو' عشان تشوفهم 💡"])

# ========== البرنامج الرئيسي ==========
def main():
    print("\n" + "="*70)
    print("🤖 PEPPER BALLOON CHASER - النسخة المتطورة")
    print("="*70)
    print("🎈 بيبر في غرفة مع يوسف وأحمد و15 بالونة!")
    print("📦 مشاريع محلية: شات، كويز، صوت، يوتيوب، رسم، توحد")
    print("\n🎯 الأوامر:")
    print("   • 'ارقص' - بيبر يرقص")
    print("   • 'سلم' - بيبر يسلم")
    print("   • 'عندك شنو' - عرض المشاريع")
    print("   • 'افتح [اسم]' - تشغيل مشروع")
    print("   • 'كيف [شيء]' - فيديو تعليمي")
    print("   • 'صور [شيء]' - صور من Google")
    print("   • 'شغل [أغنية]' - تشغيل أغنية")
    print("   • 'مع السلامة' - خروج")
    print("="*70 + "\n")
    
    voice = VoiceHandler()
    robot = PepperRobot()
    input_queue = queue.Queue()
    
    def text_input():
        while True:
            try:
                text = input("💬 أنت: ")
                if text:
                    input_queue.put(text)
            except:
                pass
    
    threading.Thread(target=text_input, daemon=True).start()
    
    time.sleep(2)
    voice.speak("مرحباً! أنا بيبر! معي يوسف وأحمد في الغرفة!")
    voice.speak("عندي 15 بالونة تطير وعندي مشاريع كثيرة!")
    
    running = True
    while running:
        cmd = None
        try:
            cmd = input_queue.get_nowait().lower()
        except:
            pass
        
        if not cmd:
            cmd = voice.listen()
        
        if cmd:
            if cmd in ["مع السلامة", "باي", "خروج"]:
                voice.speak("مع السلامة! أراك قريباً!")
                running = False
            
            elif "ارقص" in cmd:
                voice.speak("هيا نرقص!")
                robot.dance()
            
            elif "سلم" in cmd:
                voice.speak("أهلاً وسهلاً!")
                robot.wave()
            
            elif cmd in ["عندك شنو", "المشاريع"]:
                print("\n📦 المشاريع المتوفرة:")
                for name, proj in LOCAL_PROJECTS.items():
                    print(f"   • {name}: {proj['desc']}")
                voice.speak(f"عندي {len(LOCAL_PROJECTS)} مشروع!")
            
            elif "افتح " in cmd:
                name = cmd.split("افتح ")[-1].strip()
                if name in LOCAL_PROJECTS:
                    webbrowser.open(LOCAL_PROJECTS[name]["url"])
                    voice.speak(f"فتحت {name}!")
                else:
                    webbrowser.open(f"https://github.com/search?q={name}")
                    voice.speak(f"بحثت عن {name}")
            
            elif "كيف " in cmd:
                topic = cmd.split("كيف ")[-1].strip()
                search_youtube(f"{topic} تعليمي")
                voice.speak(f"فتحت فيديو عن {topic}")
            
            elif "صور " in cmd:
                topic = cmd.split("صور ")[-1].strip()
                search_images(topic)
                voice.speak(f"فتحت صور عن {topic}")
            
            elif "شغل " in cmd:
                song = cmd.split("شغل ")[-1].strip()
                play_song(song)
                voice.speak(f"شغلت {song}")
            
            else:
                response = get_ai_response(cmd)
                voice.speak(response)
        
        time.sleep(0.1)
    
    robot.stop()
    print("\n✅ تم الإغلاق")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 مع السلامة!")
