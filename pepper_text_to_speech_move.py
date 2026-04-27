#!/usr/bin/env python3
"""
Pepper Text-to-Speech + حركة مستمرة
- تكتب في التيرمينال
- بيبر يرد عليك بصوت
- بيبر يتحرك في كل الغرفة
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
p.loadURDF("plane.urdf")

pepper = sim_manager.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
print("✅ Pepper loaded!")

# ========== بالونات ملونة ==========
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

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
arm_angle = 0
arm_dir = 1

# ========== حركة يدين طبيعية مستمرة ==========
def natural_arm_movement():
    global arm_angle, arm_dir
    while True:
        arm_angle += 0.04 * arm_dir
        if arm_angle > 0.5:
            arm_angle = 0.5
            arm_dir = -1
        elif arm_angle < 0:
            arm_angle = 0
            arm_dir = 1
        try:
            pepper.setAngles("LShoulderPitch", arm_angle, 0.1)
            pepper.setAngles("RShoulderPitch", arm_angle, 0.1)
        except:
            pass
        time.sleep(0.05)

# ========== حركة رأس طبيعية ==========
def natural_head_movement():
    tt = 0
    while True:
        tt += 0.02
        yaw = math.sin(tt) * 0.4
        pitch = math.sin(tt * 0.7) * 0.15
        try:
            pepper.setAngles("HeadYaw", yaw, 0.1)
            pepper.setAngles("HeadPitch", pitch, 0.1)
        except:
            pass
        time.sleep(0.05)

# ========== حركة المشي السريعة ==========
def fast_walking():
    global robot_x, robot_y, t
    while True:
        t += 0.045
        robot_x = 3.2 * math.cos(t * 0.55)
        robot_y = 2.8 * math.sin(t * 0.7)
        try:
            pepper.setTranslation([robot_x, robot_y, 0.8])
        except:
            pass
        time.sleep(0.035)

# ========== تتبع البالونات بالرأس ==========
def track_balloons():
    global head_yaw
    while True:
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
            head_yaw = head_yaw * 0.92 + target_yaw * 0.08
            try:
                pepper.setAngles("HeadYaw", head_yaw, 0.1)
            except:
                pass
        time.sleep(0.05)

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
threading.Thread(target=natural_arm_movement, daemon=True).start()
threading.Thread(target=natural_head_movement, daemon=True).start()
threading.Thread(target=fast_walking, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

time.sleep(2)
speak("Hello! I am Pepper! I am walking around! Type anything and I will talk back!")

print("\n" + "="*60)
print("🤖 PEPPER TEXT-TO-SPEECH + MOVEMENT")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Pepper moves arms naturally")
print("✅ Pepper looks at balloons")
print("✅ Type anything - Pepper talks back")
print("✅ Type 'exit' to quit")
print("="*60 + "\n")

# ========== المحادثة بالكتابة ==========
while True:
    try:
        user_input = input("👶 You: ").strip()
        
        if user_input.lower() == 'exit':
            speak("Goodbye! See you later!")
            break
        
        if not user_input:
            continue
        
        # رد بسيط
        if user_input.lower() in ['hello', 'hi', 'hey']:
            speak("Hello! I am Pepper! How are you today?")
        elif user_input.lower() in ['how are you', 'how r u']:
            speak("I am great! Thank you for asking! I love walking around!")
        elif user_input.lower() in ['what is your name', 'whats your name']:
            speak("My name is Pepper! I am your robot friend!")
        else:
            speak(f"You said: {user_input}")
        
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
