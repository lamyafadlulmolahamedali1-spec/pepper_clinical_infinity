#!/usr/bin/env python3
"""
Pepper Balloon Chaser - بيبر يمشي باستمرار + كل الميزات
"""

import time
import random
import math
import threading
import webbrowser
import urllib.parse
import requests
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== AI Chat API ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def ai_chat(message):
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short, simple sentence in ENGLISH. Be kind and encouraging."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return f"That's interesting! Tell me more! 😊"

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== بدء المحاكاة ==========
print("🤖 Starting Pepper...")

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

# ========== حركة مشي مستمرة (في thread منفصل) ==========
walking = True
robot_x, robot_y = 0, 0
t = 0

def continuous_walk():
    global t, robot_x, robot_y, walking
    while True:
        if walking:
            t += 0.02
            robot_x = 2.5 * math.cos(t * 0.35)
            robot_y = 2.0 * math.sin(t * 0.5)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.05)

# بدء المشي في thread منفصل
threading.Thread(target=continuous_walk, daemon=True).start()

# ========== تتبع البالونات بالرأس ==========
head_yaw = 0
def track_balloons():
    global head_yaw, robot_x, robot_y
    while True:
        if walking:
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

# ========== حركة يدين طبيعية ==========
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

# ========== رقصات ==========
def dance_gangnam():
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)

def dance_robot():
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

def dance_happy():
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)

def wave():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
        time.sleep(0.2)

# ========== تمريض ==========
def nursing_care():
    pepper.setAngles("LShoulderPitch", 0.5, 0.1)
    time.sleep(0.5)
    pepper.setAngles("LShoulderPitch", 0, 0.1)

def check_vitals():
    pepper.setAngles("HeadYaw", 0.3, 0.1)
    time.sleep(0.3)
    pepper.setAngles("HeadYaw", -0.3, 0.1)
    time.sleep(0.3)
    pepper.setAngles("HeadYaw", 0, 0.1)

# ========== تعليم ==========
def teach_math():
    time.sleep(2)

def teach_colors():
    time.sleep(1)

# ========== ألعاب ==========
def play_rps():
    choices = ["rock", "paper", "scissors"]
    robot_choice = random.choice(choices)
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

# ========== ألعاب خارجية ==========
def open_games():
    webbrowser.open("http://localhost:5001")
    speak("Opening your ASD games dashboard!")

def open_video(topic):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(topic + ' cartoon for kids')}"
    webbrowser.open(url)
    speak(f"Opening video about {topic}!")

def open_picture(topic):
    url = f"https://image.pollinations.ai/prompt/{topic.replace(' ', '%20')}"
    webbrowser.open(url)
    speak(f"Opening picture of {topic}!")

print("\n" + "="*70)
print("🤖 PEPPER - WALKING CONTINUOUSLY + ALL FEATURES")
print("="*70)
print("✅ Pepper walks NON-STOP while doing everything!")
print("🎭 DANCES: dance, gangnam, robot, happy, wave")
print("🏥 NURSING: nurse, vitals")
print("📚 EDUCATION: math, colors")
print("🎮 GAMES: rps")
print("🎯 OTHER: game, how to [topic], picture [topic]")
print("💬 AI CHAT: ask anything!")
print("="*70 + "\n")

speak("Hello! I'm Pepper! I walk continuously! Say dance, robot, nurse, math, rps, or ask me anything!")

# ========== المحادثة الرئيسية ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye! See you later!")
            break
        
        # رقصات
        if user_input in ['dance', 'gangnam']:
            speak("Gangnam Style!")
            dance_gangnam()
        elif user_input == 'robot':
            speak("Robot Dance!")
            dance_robot()
        elif user_input == 'happy':
            speak("Happy Dance!")
            dance_happy()
        elif user_input == 'wave':
            speak("Waving!")
            wave()
        
        # تمريض
        elif user_input == 'nurse':
            speak("How can I help with nursing care?")
            nursing_care()
        elif user_input == 'vitals':
            speak("Checking vitals...")
            check_vitals()
        
        # تعليم
        elif user_input == 'math':
            speak("Let's learn math! What is 2 + 2?")
            teach_math()
            speak("The answer is 4! Great job!")
        elif user_input == 'colors':
            speak("What color is the sky? It's blue!")
            teach_colors()
        
        # ألعاب
        elif user_input == 'rps':
            speak("Let's play Rock Paper Scissors!")
            play_rps()
        
        # ألعاب خارجية
        elif user_input in ['game', 'games']:
            open_games()
        elif user_input.startswith('how to '):
            topic = user_input[7:]
            open_video(topic)
        elif user_input.startswith('picture '):
            topic = user_input[8:]
            open_picture(topic)
        
        # AI Chat (أي شيء آخر)
        else:
            print("🤖 Pepper: ", end="")
            response = ai_chat(user_input)
            speak(response)
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
