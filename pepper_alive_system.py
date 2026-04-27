#!/usr/bin/env python3
"""
Pepper Alive System - بيبر حي ومتحرك
- يمشي بإستمرار
- يحرك يديه بشكل طبيعي
- يلفت ويتفاعل مع البالونات
- يرقص (رقصات متعددة)
- يستمع ويرد بالصوت
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

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== إعداد الاستماع ==========
recognizer = sr.Recognizer()
microphone = sr.Microphone()
try:
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print("🎤 Microphone ready!")
except:
    microphone = None

def listen():
    if microphone is None:
        return None
    try:
        with microphone as source:
            print("\n🎤 Listening...", end="", flush=True)
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
        text = recognizer.recognize_google(audio, language='en-US')
        print(f"\r   ✅ You said: {text}")
        return text.lower()
    except:
        print("\r   ❌ Could not understand", end="", flush=True)
        return None

# ========== بدء المحاكاة ==========
print("🤖 Starting Pepper Alive System...")

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

for i in range(15):
    x = random.uniform(-3.8, 3.8)
    y = random.uniform(-3.2, 3.2)
    z = random.uniform(0.3, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)
    balloon_positions.append([x, y, z, random.uniform(0.006, 0.018)])

print("🎈 15 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=8, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
head_pitch = 0
arm_angle = 0
arm_dir = 1
is_dancing = False

# ========== رقصات متعددة ==========
def dance_gangnam():
    global is_dancing
    is_dancing = True
    speak("Let's dance Gangnam Style!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.15)
        pepper.setAngles("RShoulderPitch", 1.2, 0.15)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0.2, 0.15)
        pepper.setAngles("RShoulderPitch", 0.2, 0.15)
        time.sleep(0.2)
    for _ in range(4):
        pepper.setAngles("HeadYaw", 0.8, 0.15)
        time.sleep(0.15)
        pepper.setAngles("HeadYaw", -0.8, 0.15)
        time.sleep(0.15)
    pepper.setAngles("HeadYaw", 0, 0.15)
    is_dancing = False

def dance_robot():
    global is_dancing
    is_dancing = True
    speak("Robot dance!")
    for _ in range(5):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.12)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.12)
    is_dancing = False

def dance_happy():
    global is_dancing
    is_dancing = True
    speak("Happy dance!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.3, 0.12)
        time.sleep(0.12)
        pepper.setAngles("LShoulderPitch", 0, 0.12)
        pepper.setAngles("RShoulderPitch", 1.3, 0.12)
        time.sleep(0.12)
        pepper.setAngles("RShoulderPitch", 0, 0.12)
    is_dancing = False

def dance_wave():
    global is_dancing
    is_dancing = True
    speak("Wave dance!")
    for _ in range(6):
        pepper.setAngles("LShoulderPitch", 1.1, 0.1)
        pepper.setAngles("RShoulderPitch", 0.3, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.3, 0.1)
        pepper.setAngles("RShoulderPitch", 1.1, 0.1)
        time.sleep(0.15)
    pepper.setAngles("LShoulderPitch", 0, 0.1)
    pepper.setAngles("RShoulderPitch", 0, 0.1)
    is_dancing = False

# ========== حركات طبيعية مستمرة ==========
def natural_arm_movement():
    """حركة يدين طبيعية مستمرة"""
    global arm_angle, arm_dir
    while True:
        if not is_dancing:
            arm_angle += 0.03 * arm_dir
            if arm_angle > 0.4:
                arm_angle = 0.4
                arm_dir = -1
            elif arm_angle < 0:
                arm_angle = 0
                arm_dir = 1
            try:
                pepper.setAngles("LShoulderPitch", arm_angle, 0.05)
                pepper.setAngles("RShoulderPitch", arm_angle, 0.05)
            except:
                pass
        time.sleep(0.04)

def natural_head_movement():
    """حركة رأس طبيعية مستمرة"""
    global head_yaw, head_pitch
    tt = 0
    while True:
        if not is_dancing:
            tt += 0.02
            head_yaw = math.sin(tt) * 0.4
            head_pitch = math.sin(tt * 0.7) * 0.15
            try:
                pepper.setAngles("HeadYaw", head_yaw, 0.05)
                pepper.setAngles("HeadPitch", head_pitch, 0.05)
            except:
                pass
        time.sleep(0.04)

# ========== حركة المشي السريعة ==========
def fast_walking():
    global robot_x, robot_y, t
    while True:
        if not is_dancing:
            t += 0.05
            robot_x = 3.5 * math.cos(t * 0.55)
            robot_y = 3.0 * math.sin(t * 0.7)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.03)

# ========== تتبع البالونات ==========
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
                head_yaw = head_yaw * 0.92 + target_yaw * 0.08
                try:
                    pepper.setAngles("HeadYaw", head_yaw, 0.08)
                except:
                    pass
        time.sleep(0.05)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for i, b in enumerate(balloons):
            new_z = balloon_positions[i][2] + balloon_positions[i][3]
            if new_z > 1.9:
                new_z = 0.2
                balloon_positions[i][0] = random.uniform(-3.8, 3.8)
                balloon_positions[i][1] = random.uniform(-3.2, 3.2)
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
speak("Hello! I am Pepper! I am alive! I walk around and wave my arms. Say dance, robot, happy, or wave to see me dance!")

print("\n" + "="*60)
print("🎤🔊🤖 PEPPER ALIVE SYSTEM")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Pepper moves arms naturally")
print("✅ Pepper looks at balloons")
print("✅ 4 different dances")
print("✅ Voice and text input")
print("✅ Voice response")
print("="*60)
print("\n🎭 DANCE COMMANDS:")
print("   'dance' - Gangnam Style")
print("   'robot' - Robot dance")
print("   'happy' - Happy dance")
print("   'wave' - Wave dance")
print("="*60 + "\n")

mode = "voice"

while True:
    try:
        if mode == "voice":
            user_input = listen()
            if user_input is None:
                continue
            
            if user_input in ['exit', 'quit', 'bye']:
                speak("Goodbye! See you later!")
                break
            elif user_input == 'dance':
                dance_gangnam()
            elif user_input == 'robot':
                dance_robot()
            elif user_input == 'happy':
                dance_happy()
            elif user_input == 'wave':
                dance_wave()
            elif user_input == 'text':
                mode = "text"
                print("📝 Switching to text mode. Type 'voice' to go back.")
            else:
                speak(f"You said: {user_input}")
        else:
            user_input = input("\n👶 You: ").strip().lower()
            
            if user_input == 'exit':
                speak("Goodbye!")
                break
            elif user_input == 'voice':
                mode = "voice"
                print("🎤 Switching to voice mode.")
            elif user_input == 'dance':
                dance_gangnam()
            elif user_input == 'robot':
                dance_robot()
            elif user_input == 'happy':
                dance_happy()
            elif user_input == 'wave':
                dance_wave()
            else:
                speak(f"You typed: {user_input}")
                
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
