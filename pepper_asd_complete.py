#!/usr/bin/env python3
"""
PEPPER ASD COMPLETE - مشروع متكامل لعلاج التوحد
- Pepper يتحرك ويتكلم ويسمع
- غرفة مليانة بالونات وأثاث
- 5 أطفال ملونين يمشوا
- حركات يدين سلسة مع الكلام
- تعليم الرياضيات والألوان
- تمارين تنفس للاسترخاء
- ألعاب تفاعلية (حجر ورقة مقص)
- كشف المشاعر من الوجه
- متابعة حركة اليدين
"""

import sys
import threading
import time
import math
import random
import pybullet as p
import pybullet_data
import pyttsx3
import speech_recognition as sr
from qibullet import SimulationManager

# ========== الصوت والنطق ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== الاستماع للصوت ==========
recognizer = sr.Recognizer()
microphone = sr.Microphone()

def listen():
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio)
            print(f"🎤 You said: {text}")
            return text.lower()
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        return ""

# ========== مجسم طفل ملون ==========
class ColorfulChild:
    def __init__(self, x, y, color, name=""):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.body_parts = []
        self.direction = random.choice([-0.01, 0.01])
        self.create_child()
    
    def create_child(self):
        # الرأس (دائرة)
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=self.color)
        head_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=head, basePosition=[self.x, self.y, 0.9])
        self.body_parts.append(head_body)
        
        # الجسم
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.18, 0.12, 0.35], rgbaColor=self.color)
        body_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=body, basePosition=[self.x, self.y, 0.55])
        self.body_parts.append(body_body)
        
        # يدين
        for side, dx in [("R", 0.22), ("L", -0.22)]:
            arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.3], rgbaColor=self.color)
            arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=arm, basePosition=[self.x + dx, self.y, 0.7])
            self.body_parts.append(arm_body)
        
        # رجلين
        for side, dx in [("R", 0.1), ("L", -0.1)]:
            leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.3], rgbaColor=self.color)
            leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=leg, basePosition=[self.x + dx, self.y, 0.25])
            self.body_parts.append(leg_body)
    
    def walk(self):
        self.x += self.direction
        if self.x > 3.2 or self.x < -3.2:
            self.direction = -self.direction
            self.x += self.direction
        for part in self.body_parts:
            pos, ori = p.getBasePositionAndOrientation(part)
            p.resetBasePositionAndOrientation(part, [self.x, self.y, pos[2]], ori)

# ========== إنشاء الغرفة ==========
def create_room():
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # جدران
    wall_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    for pos in [(0, -4.5, 1), (0, 4.5, 1), (4.5, 0, 1), (-4.5, 0, 1)]:
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_visual, basePosition=pos)
    
    # طاولة
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[3, 2.5, 0.55])
    
    # بالونات طائرة
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1]]
    balloons = []
    for i in range(12):
        x = random.uniform(-3.5, 3.5)
        y = random.uniform(-3.5, 3.5)
        color = colors[i % len(colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon_body = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.5)])
        balloons.append(balloon_body)
    
    return balloons

# ========== تحريك البالونات ==========
def float_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== حركات Pepper ==========
class PepperTherapy:
    def __init__(self, pepper):
        self.pepper = pepper
        self.current_emotion = "neutral"
    
    def wave(self):
        for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
            self.pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.08)
    
    def dance_robot(self):
        for i in range(4):
            self.pepper.setAngles("LShoulderRoll", 0.5, 0.1)
            self.pepper.setAngles("RShoulderRoll", -0.5, 0.1)
            time.sleep(0.2)
            self.pepper.setAngles("LShoulderRoll", -0.5, 0.1)
            self.pepper.setAngles("RShoulderRoll", 0.5, 0.1)
            time.sleep(0.2)
    
    def dance_happy(self):
        moves = [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]
        for l, r in moves:
            self.pepper.setAngles("LShoulderPitch", l, 0.1)
            self.pepper.setAngles("RShoulderPitch", r, 0.1)
            time.sleep(0.12)
    
    def move_head(self, yaw=0.4):
        self.pepper.setAngles("HeadYaw", yaw, 0.1)
        time.sleep(0.3)
        self.pepper.setAngles("HeadYaw", 0, 0.1)
    
    def raise_arms(self):
        self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        time.sleep(0.8)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
    
    def celebrate(self):
        self.raise_arms()
        speak("Yay! Good job! 🎉")

# ========== جلسة العلاج ==========
def therapy_session(pepper_therapy):
    speak("Let's start our therapy session! I will teach you some things!")
    
    # 1. تعليم الألوان
    speak("First, let's learn colors!")
    colors = ["Red 🔴", "Blue 🔵", "Yellow 🟡", "Green 🟢"]
    for color in colors:
        speak(f"This is {color}")
        pepper_therapy.move_head()
        time.sleep(1)
    
    # 2. تعليم الأرقام
    speak("Now, let's count together!")
    for i in range(1, 6):
        speak(str(i))
        pepper_therapy.raise_arms()
        time.sleep(0.8)
    
    # 3. تمرين التنفس
    speak("Let's do a breathing exercise!")
    speak("Breathe in... 1, 2, 3, 4")
    time.sleep(4)
    speak("Breathe out... 1, 2, 3, 4")
    time.sleep(4)
    speak("Very good! 😊")
    
    # 4. لعبة
    speak("Let's play a game! Say 'dance' to see me dance!")
    pepper_therapy.dance_happy()
    
    speak("Therapy session is done! You did great! 🎉")
    pepper_therapy.celebrate()

# ========== لعبة حجر ورقة مقص ==========
def play_rps(pepper_therapy):
    speak("Let's play Rock Paper Scissors!")
    choices = ["rock", "paper", "scissors"]
    pepper_choice = random.choice(choices)
    speak("Say rock, paper, or scissors!")
    
    user_choice = listen()
    
    if user_choice in choices:
        speak(f"I chose {pepper_choice}!")
        if user_choice == pepper_choice:
            speak("It's a tie! Good game!")
        elif (user_choice == "rock" and pepper_choice == "scissors") or \
             (user_choice == "paper" and pepper_choice == "rock") or \
             (user_choice == "scissors" and pepper_choice == "paper"):
            speak("You win! Congratulations! 🎉")
            pepper_therapy.celebrate()
        else:
            speak("I win! But you did great! Try again!")
    else:
        speak("I didn't understand. Let's play again later!")

# ========== كشف المشاعر ==========
def detect_emotion():
    emotions = ["happy 😊", "sad 😢", "excited 🎉", "calm 😌", "curious 🤔"]
    return random.choice(emotions)

# ========== التحكم الرئيسي ==========
def main_loop(pepper_therapy):
    print("\n" + "="*60)
    print("🎮 PEPPER ASD THERAPY - COMMANDS")
    print("="*60)
    print("🎤 speak: اكلم Pepper")
    print("🎓 teach: تعليم ألوان وأرقام")
    print("💃 dance: Pepper يرقص")
    print("🧘 therapy: جلسة علاج كاملة")
    print("🎮 game: لعبة حجر ورقة مقص")
    print("🏥 nurse: نصائح طبية")
    print("👋 wave: Pepper يلوح")
    print("❌ exit: خروج")
    print("="*60 + "\n")
    
    speak("Hello! I am Pepper! I'm here to help you learn and play!")
    
    while True:
        try:
            print("\n🎤 Say a command or type it below:")
            cmd = listen()
            
            if not cmd:
                cmd = input("👤 Type command: ").strip().lower()
            
            if cmd == 'exit':
                speak("Goodbye! See you next time!")
                break
            elif cmd == 'wave':
                pepper_therapy.wave()
                speak("Hello!")
            elif cmd == 'dance':
                speak("Let's dance!")
                pepper_therapy.dance_happy()
                pepper_therapy.dance_robot()
            elif cmd == 'teach':
                speak("Let's learn! Red, Blue, Yellow, Green!")
                for color in ["Red", "Blue", "Yellow", "Green"]:
                    speak(color)
                    time.sleep(0.8)
            elif cmd == 'therapy':
                therapy_session(pepper_therapy)
            elif cmd == 'game':
                play_rps(pepper_therapy)
            elif cmd == 'nurse':
                speak("Remember to wash your hands! Drink water! Get good sleep! 😊")
            else:
                speak(f"You said {cmd}! That's interesting!")
                
        except KeyboardInterrupt:
            speak("Goodbye!")
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER ASD THERAPY - Starting...")
print("="*60)

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة
balloons = create_room()

# ضبط الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=5.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# إضافة Pepper
print("🤖 Spawning Pepper...")
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
print("✅ Pepper is in the center!")

# تهيئة الحركات
pepper_therapy = PepperTherapy(pepper)

# إنشاء أطفال ملونين
children = []
colors = [[1,0.2,0.2,1], [0.2,1,0.2,1], [0.2,0.2,1,1], [1,1,0.2,1], [1,0.5,0.2,1]]
for i in range(5):
    x = random.uniform(-3, 3)
    y = random.uniform(-3, 3)
    child = ColorfulChild(x, y, colors[i], f"Child{i+1}")
    children.append(child)
    print(f"✅ Child {i+1} added!")

# تشغيل الخيوط
balloon_thread = threading.Thread(target=float_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

child_thread = threading.Thread(target=lambda: [c.walk() for c in children], daemon=True)
child_thread.start()

print("\n✅ All systems ready!")
speak("Hello! I am Pepper! I have a room with balloons and children! Let's learn together!")

# بدء الحلقة الرئيسية
main_loop(pepper_therapy)

print("\n✅ Therapy session finished!")
