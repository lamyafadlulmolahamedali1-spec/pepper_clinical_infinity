#!/usr/bin/env python3
"""
Pepper qiBullet Smart - مع صوت وذكاء اصطناعي
"""

import time
import random
import math
import threading
import pyttsx3
import requests
from qibullet import SimulationManager
import pybullet as p

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== AI Chat ==========
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

def get_ai_response(message):
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in short, simple English sentences."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post(CHAT_API, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    return f"You said: {message}"

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(
    client_id,
    translation=[0, 0, 0],
    quaternion=[0, 0, 0, 1],
    spawn_ground_plane=True
)
print("✅ Pepper loaded!")

# ========== بالونات ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1]]
balloons = []
for i in range(10):
    x = random.uniform(-3, 3)
    y = random.uniform(-2.5, 2.5)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%5])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, random.uniform(0.5,1.5)])
    balloons.append(ball)

p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0,0,0.8])

# ========== رقصة ==========
def dance():
    for _ in range(3):
        pepper.setAngles("LShoulderPitch", 1.2, 0.15)
        pepper.setAngles("RShoulderPitch", 1.2, 0.15)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0.2, 0.15)
        pepper.setAngles("RShoulderPitch", 0.2, 0.15)
        time.sleep(0.2)

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
        pepper.setAngles("LShoulderPitch", arm_angle, 0.05)
        pepper.setAngles("RShoulderPitch", arm_angle, 0.05)
        time.sleep(0.04)

# ========== حركة مشي ==========
t = 0
def walk():
    global t
    while True:
        t += 0.04
        x = 2.5 * math.cos(t * 0.45)
        y = 2.0 * math.sin(t * 0.6)
        pepper.setTranslation([x, y, 0.8])
        time.sleep(0.04)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.008
            if new_z > 1.6:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== بدء التشغيل ==========
threading.Thread(target=natural_arms, daemon=True).start()
threading.Thread(target=walk, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

time.sleep(2)
speak("Hello! I am Pepper! I am walking in qiBullet!")

print("\n" + "="*60)
print("🤖 PEPPER QIBULLET SMART")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Pepper moves arms naturally")
print("✅ Type 'dance' - Pepper dances")
print("✅ Type anything - AI chat")
print("✅ Type 'exit' - Quit")
print("="*60 + "\n")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        elif user_input == 'dance':
            speak("Let's dance!")
            dance()
        else:
            response = get_ai_response(user_input)
            speak(response)
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
