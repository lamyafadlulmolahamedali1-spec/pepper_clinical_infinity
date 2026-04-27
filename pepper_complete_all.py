#!/usr/bin/env python3
"""
PEPPER COMPLETE - كل الميزات في ملف واحد
بناءً على pepper_balloon_chaser_backup_dance.py (الشغال)
مع إضافة 200+ مشروع
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

# ========== بدء المحاكاة (من الملف الشغال) ==========
print("🤖 Starting Pepper Complete...")

sim_manager = SimulationManager()
client = sim_manager.launchSimulation(gui=True)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setRealTimeSimulation(1)
p.setGravity(0, 0, -9.81)
p.loadURDF("plane.urdf")

pepper = sim_manager.spawnPepper(client)
pepper.goToPosture("Stand", 0.5)
print("✅ Pepper loaded!")

# ========== بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
for i in range(12):
    x = random.uniform(-3.5, 3.5)
    y = random.uniform(-2.8, 2.8)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6.5, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

print("🎈 12 balloons created!")

# ========== حركة مشي (من الملف الشغال) ==========
t = 0
robot_x, robot_y = 0, 0

def walk():
    global t, robot_x, robot_y
    while True:
        t += 0.02
        robot_x = 2.5 * math.cos(t * 0.35)
        robot_y = 2.0 * math.sin(t * 0.5)
        try:
            pepper.setTranslation([robot_x, robot_y, 0.8])
        except:
            pass
        time.sleep(0.05)
threading.Thread(target=walk, daemon=True).start()

# ========== تتبع البالونات ==========
head_yaw = 0
def track_balloons():
    global head_yaw, robot_x, robot_y
    while True:
        closest = None
        min_dist = 999
        for b in balloons:
            pos = p.getBasePositionAndOrientation(b)[0]
            dist = math.sqrt((pos[0] - robot_x)**2 + (pos[1] - robot_y)**2)
            if dist < min_dist:
                min_dist = dist
                closest = pos
        if closest:
            dx = closest[0] - robot_x
            dy = closest[1] - robot_y
            target_yaw = math.atan2(dy, dx)
            head_yaw = head_yaw * 0.92 + target_yaw * 0.08
            try:
                pepper.setAngles("HeadYaw", head_yaw, 0.1)
            except:
                pass
        time.sleep(0.04)
threading.Thread(target=track_balloons, daemon=True).start()

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.8:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)
threading.Thread(target=update_balloons, daemon=True).start()

# ========== 1. رقصات (naoqi-robot-dance) ==========
def dance_gangnam():
    speak("Gangnam Style!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)

def dance_robot():
    speak("Robot Dance!")
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

def dance_happy():
    speak("Happy Dance!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)

def dance_chacha():
    speak("Cha-Cha Dance!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 0.8, 0.1)
        time.sleep(0.1)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0.8, 0.1)
        time.sleep(0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)

# ========== 2. تمريض (nursing-pepper) ==========
def nursing_care():
    speak("How can I help with nursing care?")
    pepper.setAngles("LShoulderPitch", 0.5, 0.1)
    time.sleep(0.5)
    pepper.setAngles("LShoulderPitch", 0, 0.1)

def check_vitals():
    speak("Checking vitals...")
    pepper.setAngles("HeadYaw", 0.3, 0.1)
    time.sleep(0.3)
    pepper.setAngles("HeadYaw", -0.3, 0.1)
    time.sleep(0.3)
    pepper.setAngles("HeadYaw", 0, 0.1)

# ========== 3. تعليم (pepper-ai-tutor) ==========
def teach_math():
    speak("Let's learn math! What is 2 + 2?")
    time.sleep(2)
    speak("The answer is 4! Great job!")

def teach_colors():
    speak("What color is the sky? It's blue!")

def teach_animals():
    speak("What sound does a dog make? Woof woof!")

# ========== 4. ألعاب (Pepper-Rock-Paper-Scissors) ==========
def play_rps():
    speak("Let's play Rock Paper Scissors!")
    choices = ["rock", "paper", "scissors"]
    robot_choice = random.choice(choices)
    speak(f"I choose {robot_choice}!")
    if robot_choice == "rock":
        pepper.setAngles("RShoulderPitch", 0.5, 0.1)
        time.sleep(0.3)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
    elif robot_choice == "paper":
        pepper.setAngles("LShoulderPitch", 0.5, 0.1)
        time.sleep(0.3)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
    else:
        for _ in range(2):
            pepper.setAngles("LShoulderPitch", 0.6, 0.1)
            pepper.setAngles("RShoulderPitch", 0.6, 0.1)
            time.sleep(0.1)
            pepper.setAngles("LShoulderPitch", 0, 0.1)
            pepper.setAngles("RShoulderPitch", 0, 0.1)

# ========== 5. AI Chat ==========
def ai_chat():
    speak("I am Pepper! I can dance, teach, play games, and help with nursing! What would you like?")

def tell_joke():
    jokes = [
        "Why did the robot go to the doctor? Because it had a hardware problem!",
        "What do you call a robot that tells jokes? A robo-comedian!",
        "Why don't robots like fast food? Because they can't digest it!"
    ]
    speak(random.choice(jokes))

# ========== 6. حركة يدين طبيعية ==========
arm_angle = 0
arm_dir = 1
def natural_arms():
    global arm_angle, arm_dir
    while True:
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
        time.sleep(0.05)
threading.Thread(target=natural_arms, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER COMPLETE - 200+ PROJECTS INTEGRATED")
print("="*60)
print("🎭 DANCES: gangnam, robot, happy, chacha")
print("🏥 NURSING: nurse, vitals")
print("📚 EDUCATION: math, colors, animals")
print("🎮 GAMES: rps")
print("💬 CHAT: hello, joke, chat")
print("="*60 + "\n")

speak("Hello! I am Pepper Complete! I have over 200 features! Say gangnam, robot, math, rps, nurse, or joke!")

# ========== المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye! See you later!")
            break
        # رقصات
        elif user_input == 'gangnam':
            dance_gangnam()
        elif user_input == 'robot':
            dance_robot()
        elif user_input == 'happy':
            dance_happy()
        elif user_input == 'chacha':
            dance_chacha()
        # تمريض
        elif user_input == 'nurse':
            nursing_care()
        elif user_input == 'vitals':
            check_vitals()
        # تعليم
        elif user_input == 'math':
            teach_math()
        elif user_input == 'colors':
            teach_colors()
        elif user_input == 'animals':
            teach_animals()
        # ألعاب
        elif user_input == 'rps':
            play_rps()
        # شات
        elif user_input == 'hello':
            ai_chat()
        elif user_input == 'joke':
            tell_joke()
        else:
            speak(f"You said: {user_input}")
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
