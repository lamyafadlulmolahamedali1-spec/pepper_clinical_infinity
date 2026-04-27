#!/usr/bin/env python3
"""
PEPPER MASTER - كل المشاريع في PyBullet واحد
يجمع: رقصات، تمريض، معالج، تعليم، ألعاب، صوت، كاميرا
"""

import time
import random
import math
import threading
import webbrowser
import urllib.parse
import pyttsx3
import speech_recognition as sr
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import cv2
from ultralytics import YOLO
from deepface import DeepFace

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
mic = sr.Microphone()
try:
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print("🎤 Microphone ready!")
except:
    mic = None

def listen():
    if mic is None:
        return None
    try:
        with mic as source:
            print("\n🎤 Listening...", end="", flush=True)
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
        text = recognizer.recognize_google(audio, language='en-US')
        print(f"\r   ✅ You said: {text}")
        return text.lower()
    except:
        print("\r   ❌ Could not understand", end="", flush=True)
        return None

# ========== بدء PyBullet ==========
print("🤖 Starting Pepper Master in PyBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)
p.setRealTimeSimulation(1)

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

# ========== رقصات متعددة (من naoqi-robot-dance) ==========
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

# ========== حركات تمريض (من nursing-pepper) ==========
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

# ========== معالج (من pepper-ai-tutor) ==========
def teach_math():
    speak("Let's learn math! What is 2 + 2?")
    time.sleep(2)
    speak("The answer is 4! Great job!")

def teach_colors():
    speak("What color is the sky? It's blue!")

# ========== ألعاب (من Pepper-Rock-Paper-Scissors) ==========
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

# ========== كاميرا YOLO (كشف أشياء) ==========
def start_camera():
    speak("Starting camera for object detection...")
    cap = cv2.VideoCapture(0)
    model = YOLO('yolov8n.pt')
    for _ in range(30):
        ret, frame = cap.read()
        if ret:
            results = model(frame, verbose=False)
            for r in results:
                if r.boxes:
                    for box in r.boxes:
                        name = model.names[int(box.cls[0])]
                        speak(f"I see {name}")
                        break
            break
    cap.release()
    cv2.destroyAllWindows()

# ========== حركة مشي مستمرة ==========
t = 0
def walk():
    global t
    while True:
        t += 0.04
        x = 3.5 * math.cos(t * 0.5)
        y = 3.0 * math.sin(t * 0.7)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.04)
threading.Thread(target=walk, daemon=True).start()

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.9:
                new_z = 0.3
                new_x = random.uniform(-4, 4)
                new_y = random.uniform(-3, 3)
                p.resetBasePositionAndOrientation(b, [new_x, new_y, new_z], [0,0,0,1])
            else:
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

print("\n" + "="*70)
print("🤖 PEPPER MASTER - ALL PROJECTS IN PYBULLET")
print("="*70)
print("🎭 DANCES: gangnam, robot, happy, chacha")
print("🏥 NURSING: nurse, vitals")
print("📚 EDUCATION: math, colors")
print("🎮 GAMES: rps")
print("📷 CAMERA: camera")
print("🎤 VOICE: speak, listen")
print("="*70 + "\n")

speak("Hello! I am Pepper Master! I have all features! Say gangnam, robot, math, rps, or camera!")

mode = "text"

while True:
    try:
        if mode == "voice":
            cmd = listen()
            if cmd is None:
                continue
        else:
            cmd = input("\n👶 You: ").strip().lower()
        
        if cmd == 'exit':
            speak("Goodbye!")
            break
        elif cmd == 'voice':
            mode = "voice"
            speak("Voice mode activated!")
            continue
        elif cmd == 'text':
            mode = "text"
            speak("Text mode activated!")
            continue
        elif cmd == 'gangnam':
            dance_gangnam()
        elif cmd == 'robot':
            dance_robot()
        elif cmd == 'happy':
            dance_happy()
        elif cmd == 'chacha':
            dance_chacha()
        elif cmd == 'nurse':
            nursing_care()
        elif cmd == 'vitals':
            check_vitals()
        elif cmd == 'math':
            teach_math()
        elif cmd == 'colors':
            teach_colors()
        elif cmd == 'rps':
            play_rps()
        elif cmd == 'camera':
            start_camera()
        elif cmd == 'hello':
            speak("Hello! I am Pepper Master!")
        else:
            speak(f"You said: {cmd}")
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
