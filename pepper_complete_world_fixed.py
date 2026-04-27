#!/usr/bin/env python3
"""
PEPPER COMPLETE WORLD FIXED - بيبر في عالم متكامل
"""

import time
import math
import random
import threading
import pyttsx3
import pybullet as p
import pybullet_data

# ========== الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)

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
        }
        for key in responses:
            if key in message.lower():
                return responses[key]
        return f"That's interesting! Tell me more!"

# ========== qiBullet setup ==========
from qibullet import SimulationManager

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

# ========== إنشاء الغرفة بدون plane.urdf ==========
def create_room():
    """إنشاء غرفة مليانة بالأشياء - بدون ملفات خارجية"""
    
    # إضافة مسار PyBullet data
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    
    # أرضية (plane.urdf موجود في pybullet_data)
    try:
        plane = p.loadURDF("plane.urdf")
    except:
        # بديل: إنشاء أرضية يدوياً
        plane_collision = p.createCollisionShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1])
        plane_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], rgbaColor=[0.5, 0.5, 0.5, 1])
        plane = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=plane_collision, baseVisualShapeIndex=plane_visual, basePosition=[0, 0, -0.1])
    
    p.setGravity(0, 0, -9.81)
    
    # جدران الغرفة (أعمدة بسيطة)
    wall_positions = [(-4, -4), (-4, 4), (4, -4), (4, 4)]
    for x, y in wall_positions:
        wall_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 1.5], rgbaColor=[0.7, 0.7, 0.8, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_visual, basePosition=[x, y, 0.8])
    
    # كراسي (مكعبات)
    chairs = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
    for x, y in chairs:
        chair_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_visual, basePosition=[x, y, 0.2])
    
    # طاولة في المنتصف
    table_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.8, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_visual, basePosition=[0, 0, 0.3])
    
    # كتب على الطاولة
    for i in range(3):
        book_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.15, 0.1, 0.03], rgbaColor=[0.2, 0.5, 0.8, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=book_visual, basePosition=[-0.3 + i*0.3, 0, 0.5])
    
    # بالونات
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1]]
    balloons = []
    for i in range(10):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        color = colors[i % len(colors)]
        balloon_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=color)
        balloon = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon_visual, basePosition=[x, y, random.uniform(0.5, 1.5)])
        balloons.append(balloon)
    
    # أشخاص بسيطين (مكعبات ملونة)
    people_positions = [(-1, -2.5), (2, 2.5), (-2.5, 1.5)]
    for x, y in people_positions:
        # جسم
        body_visual = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.6], rgbaColor=[0.9, 0.7, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=body_visual, basePosition=[x, y, 0.4])
        # رأس
        head_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[0.9, 0.7, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=head_visual, basePosition=[x, y, 0.85])
    
    print("✅ غرفة كاملة: بالونات، كراسي، كتب، طاولة، ناس!")
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== تحريك بيبر في الغرفة ==========
def move_pepper_continuously(pepper, gestures):
    t = 0
    while True:
        t += 0.03
        radius = 2.5
        x = radius * math.cos(t * 0.4)
        y = radius * math.sin(t * 0.5)
        try:
            pepper.setTranslation([x, y, 0.8])
            angle = math.atan2(y, x)
            pepper.setOrientation([0, 0, angle])
        except:
            pass
        gestures.move_head_naturally()
        time.sleep(0.05)

# ========== الرد على الأوامر ==========
def command_listener(gestures):
    commands = {
        "wave": lambda: gestures.wave(),
        "dance": lambda: gestures.dance(),
        "hello": lambda: (gestures.wave(), speak("Hello! Nice to see you!")),
    }
    
    print("\n🎤 الأوامر المتاحة:")
    print("   hello, wave, dance, teach, medical, vision, exit\n")
    
    while True:
        try:
            cmd = input("👤 You: ").strip().lower()
            if cmd in commands:
                commands[cmd]()
            elif cmd == 'teach':
                speak("Let's learn numbers! 1, 2, 3, 4, 5")
                for i in range(1, 6):
                    speak(str(i))
                    time.sleep(0.5)
            elif cmd == 'medical':
                speak("Take a deep breath... in... and out...")
                time.sleep(2)
                speak("You're doing great!")
            elif cmd == 'vision':
                speak("I see a beautiful room with balloons, chairs, books, and people!")
            elif cmd == 'exit':
                speak("Goodbye!")
                break
            else:
                response = get_ai_response(cmd)
                speak(response)
        except KeyboardInterrupt:
            speak("Goodbye!")
            break
        except:
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER COMPLETE WORLD - Starting...")
print("="*60)

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])

# إعداد الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=5, cameraYaw=50, cameraPitch=-25, cameraTargetPosition=[0,0,0.8])

# إنشاء الغرفة
balloons = create_room()

# تهيئة الحركات
gestures = Gestures(pepper)

print("\n✅ Pepper في غرفة مليانة بالونات، كراسي، كتب، وناس!")
print("✅ Pepper بيدور ويتحرك في الغرفة!\n")

speak("Hello everyone! I'm Pepper! Welcome to my room!")

# تشغيل الخيوط
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

movement_thread = threading.Thread(target=move_pepper_continuously, args=(pepper, gestures), daemon=True)
movement_thread.start()

# بدء الاستماع
command_listener(gestures)

print("\n✅ Finished!")
