#!/usr/bin/env python3
"""
PEPPER COMPLETE WORLD - بيبر في عالم متكامل
- غرفة مليانة بالونات، كراسي، كتب، ناس
- بيبر بيدور ويتحرك
- كل المهارات: حركات، رقص، تعليم، طبي، محادثة، رؤية
"""

import time
import math
import random
import threading
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== المحادثة ==========
import json
import urllib.request
import urllib.parse

def get_ai_response(message):
    try:
        url = f"https://api.popcat.xyz/chat?msg={urllib.parse.quote(message)}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("response", "That's interesting! Tell me more! 😊")
    except:
        responses = {
            "hello": "Hello! I'm Pepper! Welcome to my room!",
            "how are you": "I'm so happy to see you!",
            "dance": "Let's dance together! 🕺",
            "teach": "I love teaching! What would you like to learn?",
            "medical": "I can help you relax and breathe.",
        }
        for key in responses:
            if key in message.lower():
                return responses[key]
        return f"That's interesting about {message}! Tell me more!"

# ========== حركات سلسة ==========
class Gestures:
    def __init__(self, pepper):
        self.pepper = pepper
        self.current_angle = 0
    
    def wave(self):
        for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
            self.pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.08)
    
    def raise_arms(self):
        self.pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        self.pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        time.sleep(0.8)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
    
    def dance(self):
        moves = [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]
        for l, r in moves:
            self.pepper.setAngles("LShoulderPitch", l, 0.1)
            self.pepper.setAngles("RShoulderPitch", r, 0.1)
            time.sleep(0.12)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)
    
    def move_head_naturally(self):
        yaw = math.sin(time.time() * 0.8) * 0.3
        self.pepper.setAngles("HeadYaw", yaw, 0.05)

# ========== إنشاء الغرفة الكاملة ==========
def create_room():
    """إنشاء غرفة مليانة بالأشياء"""
    
    # أرضية
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # جدران الغرفة
    wall_positions = [
        (-4, 0, 1), (4, 0, 1),   # جدران جانبية
        (0, -4, 1), (0, 4, 1),   # جدران أمامية وخلفية
    ]
    for x, y, z in wall_positions:
        wall = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_BOX, halfExtents=[0.1, 4, 1.5], rgbaColor=[0.7, 0.7, 0.8, 1]
            ),
            baseCollisionShapeIndex=p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[0.1, 4, 1.5]
            ),
            basePosition=[x, y, z]
        )
    
    # كراسي
    chairs = [(-2, -2, 0.3), (2, -2, 0.3), (-2, 2, 0.3), (2, 2, 0.3)]
    for x, y, z in chairs:
        chair = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.5], rgbaColor=[0.6, 0.4, 0.2, 1]
            ),
            basePosition=[x, y, z]
        )
    
    # طاولة في المنتصف
    table = p.createMultiBody(
        baseMass=0,
        baseVisualShapeIndex=p.createVisualShape(
            p.GEOM_BOX, halfExtents=[0.8, 0.8, 0.4], rgbaColor=[0.5, 0.3, 0.1, 1]
        ),
        basePosition=[0, 0, 0.4]
    )
    
    # كتب على الطاولة
    for i in range(3):
        book = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_BOX, halfExtents=[0.15, 0.1, 0.03], rgbaColor=[0.2, 0.5, 0.8, 1]
            ),
            basePosition=[-0.3 + i*0.3, 0, 0.65]
        )
    
    # بالونات (10 بالونات بألوان مختلفة)
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1], [0.2,0.8,0.8,1]]
    balloons = []
    for i in range(12):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        color = colors[i % len(colors)]
        balloon = p.createMultiBody(
            baseMass=0.1,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_SPHERE, radius=0.12, rgbaColor=color
            ),
            basePosition=[x, y, random.uniform(0.5, 1.8)]
        )
        balloons.append(balloon)
    
    # أشخاص (أشكال بشرية بسيطة)
    people_positions = [(-1, -2.5, 0), (2, 2.5, 0), (-2.5, 1.5, 0)]
    for x, y, z in people_positions:
        # جسم الشخص
        body = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_CAPSULE, radius=0.2, length=0.8, rgbaColor=[0.9, 0.7, 0.5, 1]
            ),
            basePosition=[x, y, 0.6]
        )
        # رأس الشخص
        head = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=p.createVisualShape(
                p.GEOM_SPHERE, radius=0.15, rgbaColor=[0.9, 0.7, 0.5, 1]
            ),
            basePosition=[x, y, 1.0]
        )
    
    print("✅ غرفة كاملة: بالونات، كراسي، كتب، طاولة، ناس!")
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.8:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== تحريك بيبر في الغرفة ==========
def move_pepper_continuously(pepper, gestures):
    t = 0
    while True:
        t += 0.03
        # مسار دائري حول الغرفة
        radius = 2.5
        x = radius * math.cos(t * 0.4)
        y = radius * math.sin(t * 0.5)
        try:
            pepper.setTranslation([x, y, 0.8])
            # اتجاه الجسم (يواجه اتجاه الحركة)
            angle = math.atan2(y, x)
            pepper.setOrientation([0, 0, angle])
        except:
            pass
        gestures.move_head_naturally()
        time.sleep(0.05)

# ========== الرد على الأوامر الصوتية (محاكاة) ==========
def command_listener(gestures):
    commands = {
        "wave": lambda: gestures.wave(),
        "dance": lambda: gestures.dance(),
        "hello": lambda: (gestures.wave(), speak("Hello! Nice to see you!")),
        "hi": lambda: (gestures.wave(), speak("Hi there! Welcome to my room!")),
    }
    
    print("\n🎤 قائمة الأوامر:")
    print("   type 'hello', 'wave', 'dance', 'teach', 'medical', 'vision'")
    
    while True:
        try:
            cmd = input("\n👤 Command: ").strip().lower()
            if cmd in commands:
                commands[cmd]()
            elif cmd == 'teach':
                speak("Let's learn! Say numbers, colors, or letters")
                topic = input("👤 Topic: ").strip().lower()
                if 'number' in topic:
                    for i in range(1, 6):
                        speak(str(i))
                        time.sleep(0.5)
                elif 'color' in topic:
                    for color in ["Red", "Blue", "Yellow", "Green"]:
                        speak(color)
                        time.sleep(0.8)
                elif 'letter' in topic:
                    for letter in ["A", "B", "C", "D"]:
                        speak(f"Letter {letter}")
                        time.sleep(0.5)
            elif cmd == 'medical':
                speak("Let's breathe together. Breathe in... and out...")
                time.sleep(2)
                speak("You're doing great!")
            elif cmd == 'vision':
                speak("I see a beautiful room with balloons, chairs, books, and people!")
            elif cmd == 'exit':
                speak("Goodbye! See you later!")
                break
            else:
                response = get_ai_response(cmd)
                speak(response)
        except:
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER COMPLETE WORLD - Starting...")
print("="*60)

# تشغيل المحاكاة
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])

# إعداد الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# إنشاء الغرفة
balloons = create_room()

# تهيئة الحركات
gestures = Gestures(pepper)

print("\n" + "="*60)
print("✅ Pepper في غرفة مليانة بالونات، كراسي، كتب، وناس!")
print("✅ Pepper بيدور ويتحرك في الغرفة!")
print("✅ كل المشاريع شغالة: تعليم، طبي، محادثة، حركات، رقص!")
print("="*60 + "\n")

speak("Hello everyone! I'm Pepper! Welcome to my colorful room! Look at all the balloons! 🎈")

# تشغيل الخيوط (threads)
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

movement_thread = threading.Thread(target=move_pepper_continuously, args=(pepper, gestures), daemon=True)
movement_thread.start()

# بدء الاستماع للأوامر
command_listener(gestures)

print("\n✅ Pepper Complete World finished!")
