#!/usr/bin/env python3
"""
PEPPER SIMPLE MOVE - بيبر يتحرك ويتفاعل في غرفة من PyBullet
"""

import time
import math
import random
import threading
import pyttsx3
import pybullet as p
import pybullet_data
from qibullet import SimulationManager

# ========== الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== المحادثة ==========
def get_response(message):
    responses = {
        "hello": "Hello! Nice to meet you!",
        "hi": "Hi there! Welcome to my room!",
        "how are you": "I'm doing great, thank you!",
        "wave": "Waving at you! 👋",
        "dance": "Let's dance! 🕺",
        "what is your name": "I'm Pepper, your robot friend!",
        "what do you see": "I see a beautiful room with balloons and furniture!",
    }
    msg = message.lower()
    for key in responses:
        if key in msg:
            return responses[key]
    return "That's interesting! Tell me more!"

# ========== تحريك Pepper ==========
def move_pepper(pepper):
    """حركة بسيطة ومستمرة لـ Pepper"""
    t = 0
    while True:
        t += 0.05
        # حركة دائرية بسيطة
        x = 2.0 * math.cos(t * 0.5)
        y = 2.0 * math.sin(t * 0.3)
        try:
            pepper.setTranslation([x, y, 0.8])
            # اتجاه الجسم
            angle = math.atan2(y, x)
            pepper.setOrientation([0, 0, angle])
        except Exception as e:
            print(f"Move error: {e}")
        time.sleep(0.05)

# ========== إنشاء غرفة في PyBullet ==========
def create_pybullet_room():
    """إنشاء غرفة مباشرة في PyBullet"""
    
    # إضافة مسار PyBullet
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    
    # أرضية
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # بالونات (كرات طائرة)
    balloons = []
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
    
    for i in range(8):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        color = colors[i % len(colors)]
        sphere = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=sphere, basePosition=[x, y, random.uniform(0.5, 1.5)])
        balloons.append(balloon)
    
    # كراسي
    chairs = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
    for x, y in chairs:
        box = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.3, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=box, basePosition=[x, y, 0.2])
    
    # طاولة
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.8, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[0, 0, 0.3])
    
    # أشخاص (بسيطين)
    people = [(-1, -2), (2, 1.5)]
    for x, y in people:
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.6], rgbaColor=[0.9, 0.7, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=body, basePosition=[x, y, 0.4])
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[0.9, 0.7, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=head, basePosition=[x, y, 0.85])
    
    print("✅ PyBullet: غرفة جاهزة!")
    return balloons

# ========== تحريك البالونات ==========
def float_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.5:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== التحكم من لوحة المفاتيح ==========
def keyboard_control(pepper, gestures):
    print("\n" + "="*50)
    print("🎮 التحكم في Pepper:")
    print("   w = مشي للأمام")
    print("   s = مشي للخلف")
    print("   a = لف يسار")
    print("   d = لف يمين")
    print("   space = يلوح")
    print("   q = رقص")
    print("   t = تعليم")
    print("   m = طبي")
    print("   v = رؤية")
    print("   esc = خروج")
    print("="*50 + "\n")
    
    import keyboard
    
    speed = 0.05
    angle_speed = 0.1
    
    while True:
        try:
            if keyboard.is_pressed('w'):
                pepper.setTranslationOffset([speed, 0, 0])
            elif keyboard.is_pressed('s'):
                pepper.setTranslationOffset([-speed, 0, 0])
            elif keyboard.is_pressed('a'):
                pepper.setOrientationOffset([0, 0, angle_speed])
            elif keyboard.is_pressed('d'):
                pepper.setOrientationOffset([0, 0, -angle_speed])
            elif keyboard.is_pressed('space'):
                gestures.wave()
                speak("Hello!")
                time.sleep(0.5)
            elif keyboard.is_pressed('q'):
                gestures.dance()
                speak("Let's dance!")
            elif keyboard.is_pressed('t'):
                speak("Let's learn numbers! 1, 2, 3, 4, 5")
                for i in range(1, 6):
                    speak(str(i))
                    time.sleep(0.5)
            elif keyboard.is_pressed('m'):
                speak("Take a deep breath... in... and out...")
            elif keyboard.is_pressed('v'):
                speak("I see a room with balloons, chairs, and people!")
            elif keyboard.is_pressed('esc'):
                speak("Goodbye!")
                break
            time.sleep(0.05)
        except:
            break

# ========== حركات Pepper ==========
class Gestures:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def wave(self):
        for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
            self.pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.08)
    
    def dance(self):
        moves = [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]
        for l, r in moves:
            self.pepper.setAngles("LShoulderPitch", l, 0.1)
            self.pepper.setAngles("RShoulderPitch", r, 0.1)
            time.sleep(0.12)
        self.pepper.setAngles("LShoulderPitch", 0, 0.1)
        self.pepper.setAngles("RShoulderPitch", 0, 0.1)

# ========== الرئيسي ==========
print("="*60)
print("🤖 STARTING PEPPER IN PYTHON + QIBULLET")
print("="*60)

# 1. تشغيل PyBullet في نافذة منفصلة
print("📦 Loading PyBullet room...")
p.connect(p.GUI)
balloons = create_pybullet_room()

# 2. تشغيل qiBullet في نفس النافذة
print("🤖 Loading Pepper in qiBullet...")
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)  # GUI false عشان نستخدم PyBullet GUI
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])

# إعداد الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# 3. تهيئة الحركات
gestures = Gestures(pepper)

# 4. بدء تشغيل البالونات
balloon_thread = threading.Thread(target=float_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

# 5. بدء حركة Pepper المستمرة
move_thread = threading.Thread(target=move_pepper, args=(pepper,), daemon=True)
move_thread.start()

print("\n✅ Pepper is alive and moving!")
speak("Hello! I am Pepper! I am moving in my room!")

# 6. التحكم
keyboard_control(pepper, gestures)

print("\n✅ Finished!")
