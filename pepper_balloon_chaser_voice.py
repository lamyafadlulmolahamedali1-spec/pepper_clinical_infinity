#!/usr/bin/env python3
"""
Pepper Balloon Chaser with Voice + Dance + Fast Movement
- بيبر يتحرك بسرعة في الغرفة
- يتكلم بصوت
- يرقص
- يتتبع البالونات
"""

import time
import random
import math
import threading
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    """جعل بيبر يتكلم بصوت"""
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== بدء المحاكاة ==========
print("🤖 Starting Pepper in PyBullet...")

sim_manager = SimulationManager()
client = sim_manager.launchSimulation(gui=True)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setRealTimeSimulation(1)
p.setGravity(0, 0, -9.81)

# Ground
p.loadURDF("plane.urdf")

# Spawn Pepper
pepper = sim_manager.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
print("✅ Pepper loaded!")

# ========== إنشاء البالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
balloon_positions = []

for i in range(12):
    x = random.uniform(-3.5, 3.5)
    y = random.uniform(-2.8, 2.8)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)
    balloon_positions.append([x, y, z, random.uniform(0.008, 0.02)])

print("🎈 12 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

print("✅ Room ready!")

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
is_dancing = False

# ========== رقصة جانجام ستايل ==========
def gangnam_dance():
    global is_dancing
    is_dancing = True
    print("💃 Pepper is dancing Gangnam Style!")
    speak("Let's dance!")
    
    for _ in range(3):
        pepper.setAngles("LShoulderPitch", 1.2, 0.15)
        pepper.setAngles("RShoulderPitch", 1.2, 0.15)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0.2, 0.15)
        pepper.setAngles("RShoulderPitch", 0.2, 0.15)
        time.sleep(0.2)
    
    for _ in range(3):
        pepper.setAngles("HeadYaw", 0.8, 0.15)
        time.sleep(0.15)
        pepper.setAngles("HeadYaw", -0.8, 0.15)
        time.sleep(0.15)
    
    pepper.setAngles("HeadYaw", 0, 0.15)
    is_dancing = False

# ========== حركة سريعة في الغرفة ==========
def fast_move():
    global robot_x, robot_y, t
    while True:
        if not is_dancing:
            t += 0.04  # سرعة عالية
            robot_x = 3.2 * math.cos(t * 0.6)
            robot_y = 2.8 * math.sin(t * 0.8)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.03)

# ========== تتبع البالونات بالرأس ==========
def track_balloons():
    global head_yaw
    while True:
        if not is_dancing:
            closest = None
            min_dist = 999
            for b in balloon_positions:
                dist = math.sqrt((b[0] - robot_x)**2 + (b[1] - robot_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest = b
            if closest:
                dx = closest[0] - robot_x
                dy = closest[1] - robot_y
                target_yaw = math.atan2(dy, dx)
                head_yaw = head_yaw * 0.9 + target_yaw * 0.1
                try:
                    pepper.setAngles("HeadYaw", head_yaw, 0.1)
                except:
                    pass
        time.sleep(0.04)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for i, b in enumerate(balloons):
            new_z = balloon_positions[i][2] + balloon_positions[i][3]
            if new_z > 1.9:
                new_z = 0.3
                balloon_positions[i][0] = random.uniform(-3.5, 3.5)
                balloon_positions[i][1] = random.uniform(-2.8, 2.8)
            balloon_positions[i][2] = new_z
            p.resetBasePositionAndOrientation(b, [balloon_positions[i][0], balloon_positions[i][1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== بدء التشغيل ==========
threading.Thread(target=fast_move, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

# ========== الترحيب بصوت ==========
time.sleep(2)
speak("Hello! I am Pepper! I am your friend!")

print("\n" + "="*50)
print("🤖 PEPPER BALLOON CHASER WITH VOICE")
print("="*50)
print("✅ Pepper moves FAST around the room")
print("✅ Pepper TALKS with voice")
print("✅ Type 'dance' - Pepper dances")
print("✅ Type 'hello' - Pepper says hello")
print("✅ Type 'exit' - Quit")
print("="*50 + "\n")

# ========== المحادثة ==========
while True:
    try:
        user = input("\n👶 You: ").strip().lower()
        
        if user == 'exit':
            speak("Goodbye! See you later!")
            break
        elif user == 'dance':
            gangnam_dance()
        elif user == 'hello':
            speak("Hello! I am Pepper! I am your friend!")
        else:
            print("🤖 Pepper: Say 'dance' to see me dance, or 'hello' for me to talk!")
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
