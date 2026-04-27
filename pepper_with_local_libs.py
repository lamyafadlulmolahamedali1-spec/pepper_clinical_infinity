#!/usr/bin/env python3
"""
Pepper QiBullet - باستخدام المكتبات المحلية
"""

import sys
import os

# إضافة المكتبات المحلية إلى المسار
sys.path.insert(0, '/home/lamya/pepper_duo/src/local_libs')

import time
import random
import math
import threading
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3

# محاولة استيراد YOLO من المكتبات المحلية
try:
    from ultralytics import YOLO
    print("✅ YOLO loaded from local libs")
except:
    print("⚠️ YOLO not available, using fallback")
    YOLO = None

# محاولة استيراد deepface من المكتبات المحلية
try:
    import deepface
    print("✅ DeepFace loaded from local libs")
except:
    print("⚠️ DeepFace not available")

# محاولة استيراد mediapipe من المكتبات المحلية
try:
    import mediapipe as mp
    print("✅ MediaPipe loaded from local libs")
except:
    print("⚠️ MediaPipe not available")

# ========== إعداد الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== بدء qiBullet ==========
print("\n🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0], quaternion=[0, 0, 0, 1])

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

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

# ========== رقصات ==========
def gangnam_dance():
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)

def robot_dance():
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

def wave():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
        time.sleep(0.2)

# ========== حركة مشي ==========
t = 0
def walk():
    global t
    while True:
        t += 0.035
        x = 2.8 * math.cos(t * 0.45)
        y = 2.5 * math.sin(t * 0.6)
        try:
            pepper.setTranslation([x, y, 0.8])
        except:
            pass
        time.sleep(0.04)
threading.Thread(target=walk, daemon=True).start()

# تحديث البالونات
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
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER WITH LOCAL LIBRARIES")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Balloons float around")
print("✅ Commands: dance, robot, wave, hello, exit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can dance! Say dance, robot, or wave!")

while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye!")
            break
        elif user_input == 'dance':
            speak("Gangnam style!")
            gangnam_dance()
        elif user_input == 'robot':
            speak("Robot dance!")
            robot_dance()
        elif user_input == 'wave':
            speak("Waving!")
            wave()
        elif user_input == 'hello':
            speak("Hello! I am Pepper!")
        else:
            speak(f"You said: {user_input}")
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
