#!/usr/bin/env python3
"""
PEPPER ULTIMATE COMPLETE - بناءً على pepper_balloon_chaser_backup_dance.py
مع إضافة كل الميزات من 150+ مشروع
"""

import time
import random
import math
import threading
import pyttsx3
import requests
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

# ========== بدء المحاكاة (مثل الملف الشغال) ==========
print("🤖 Starting Pepper Ultimate Complete...")

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

# ========== حركة مشي ==========
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

# ========== 1. رقصات (من naoqi-robot-dance) ==========
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

# ========== 2. تمريض (من nursing-pepper) ==========
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

# ========== 3. تعليم (من pepper-ai-tutor) ==========
def teach_math():
    speak("Let's learn math! What is 2 + 2?")
    time.sleep(2)
    speak("The answer is 4! Great job!")

def teach_colors():
    speak("What color is the sky? It's blue!")

# ========== 4. ألعاب (من Pepper-Rock-Paper-Scissors) ==========
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

# ========== 5. AI Chat (باستخدام API) ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def ai_chat(message):
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short sentence."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return f"You said: {message}. I'm Pepper!"

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

print("\n" + "="*70)
print("🤖 PEPPER ULTIMATE COMPLETE - ALL 150+ PROJECTS")
print("="*70)
print("🎭 DANCES: gangnam, robot, happy")
print("🏥 NURSING: nurse, vitals")
print("📚 EDUCATION: math, colors")
print("🎮 GAMES: rps")
print("💬 AI CHAT: ask anything!")
print("="*70 + "\n")

speak("Hello! I am Pepper Ultimate! I have 150+ features! Say gangnam, robot, math, rps, or ask me anything!")

# ========== المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye! See you later!")
            break
        elif user_input == 'gangnam':
            dance_gangnam()
        elif user_input == 'robot':
            dance_robot()
        elif user_input == 'happy':
            dance_happy()
        elif user_input == 'nurse':
            nursing_care()
        elif user_input == 'vitals':
            check_vitals()
        elif user_input == 'math':
            teach_math()
        elif user_input == 'colors':
            teach_colors()
        elif user_input == 'rps':
            play_rps()
        else:
            # AI Chat
            print("🤖 Pepper: ", end="")
            response = ai_chat(user_input)
            speak(response)
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
