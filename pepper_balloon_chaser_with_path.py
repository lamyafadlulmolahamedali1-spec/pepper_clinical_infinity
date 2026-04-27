#!/usr/bin/env python3
"""
Pepper Balloon Chaser - مع حركة في مسار محدد
بيبر يمشي في خط دائري مستمر + بالونات + رقصات + AI Chat
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

# ========== بدء المحاكاة ==========
print("🤖 Starting Pepper with Path Movement...")

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
    x = random.uniform(-4, 4)
    y = random.uniform(-3, 3)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

print("🎈 12 balloons created!")

# ========== مسار حركة بيبر (خط دائري محدد) ==========
# النقاط التي سيمشي فيها بيبر (مسار محدد)
path_points = [
    [2.5, 1.5], [3.0, 0.5], [2.5, -0.5], [1.5, -1.5],
    [0.5, -2.0], [-0.5, -2.0], [-1.5, -1.5], [-2.5, -0.5],
    [-3.0, 0.5], [-2.5, 1.5], [-1.5, 2.0], [0, 2.0],
    [1.5, 2.0], [2.5, 1.5]  # يعود للنقطة الأولى
]

current_point_index = 0
robot_x, robot_y = path_points[0]
is_moving = True
is_talking = False

def move_on_path():
    global current_point_index, robot_x, robot_y, is_moving
    while True:
        if is_moving and not is_talking:
            # الوصول إلى النقطة الحالية
            target_x, target_y = path_points[current_point_index]
            dx = target_x - robot_x
            dy = target_y - robot_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < 0.05:
                # انتقل إلى النقطة التالية
                current_point_index = (current_point_index + 1) % len(path_points)
            else:
                # تحرك نحو النقطة
                step = min(0.05, distance)
                robot_x += (dx / distance) * step
                robot_y += (dy / distance) * step
                try:
                    pepper.setTranslation([robot_x, robot_y, 0.8])
                except:
                    pass
        time.sleep(0.03)

# بدء حركة المسار
threading.Thread(target=move_on_path, daemon=True).start()

# ========== تتبع البالونات بالرأس ==========
head_yaw = 0
def track_balloons():
    global head_yaw, robot_x, robot_y
    while True:
        if not is_talking:
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
        if not is_talking:
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
    global is_talking
    is_talking = True
    speak("Gangnam Style!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)
    is_talking = False

def dance_robot():
    global is_talking
    is_talking = True
    speak("Robot Dance!")
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)
    is_talking = False

def dance_happy():
    global is_talking
    is_talking = True
    speak("Happy Dance!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
    is_talking = False

# ========== تمريض ==========
def nursing_care():
    global is_talking
    is_talking = True
    speak("How can I help with nursing care?")
    pepper.setAngles("LShoulderPitch", 0.5, 0.1)
    time.sleep(0.5)
    pepper.setAngles("LShoulderPitch", 0, 0.1)
    is_talking = False

# ========== تعليم ==========
def teach_math():
    global is_talking
    is_talking = True
    speak("Let's learn math! What is 2 + 2?")
    time.sleep(2)
    speak("The answer is 4! Great job!")
    is_talking = False

# ========== ألعاب ==========
def play_rps():
    global is_talking
    is_talking = True
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
    is_talking = False

# ========== AI Chat ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def ai_chat(message):
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short sentence in ENGLISH."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return f"You said: {message}. I'm Pepper!"

print("\n" + "="*70)
print("🤖 PEPPER WITH PATH MOVEMENT")
print("="*70)
print("✅ Pepper moves on a FIXED PATH continuously!")
print("✅ Path has 14 points (walks in a circle)")
print("🎭 Commands: gangnam, robot, happy, nurse, math, rps")
print("💬 AI Chat: ask anything!")
print("="*70 + "\n")

speak("Hello! I am Pepper! I am walking on a path! Say gangnam, robot, math, or ask me anything!")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        elif user_input == 'gangnam':
            dance_gangnam()
        elif user_input == 'robot':
            dance_robot()
        elif user_input == 'happy':
            dance_happy()
        elif user_input == 'nurse':
            nursing_care()
        elif user_input == 'math':
            teach_math()
        elif user_input == 'rps':
            play_rps()
        else:
            print("🤖 Pepper: ", end="")
            response = ai_chat(user_input)
            speak(response)
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
