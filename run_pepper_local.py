#!/usr/bin/env python3
"""
Pepper QiBullet - باستخدام المكتبات المنسوخة محلياً
"""

import sys
import os

# إضافة المكتبات المحلية إلى المسار
sys.path.insert(0, '/home/lamya/pepper_duo/src/all_libs')

# استيراد المكتبات
import time
import random
import math
import threading

# استيراد qibullet و pybullet
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# استيراد الصوت
import pyttsx3

print("✅ All libraries loaded successfully!")

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
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
for i in range(12):
    x = random.uniform(-4, 4)
    y = random.uniform(-3, 3)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)

print("🎈 12 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

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
    for _ in range(3):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)
        time.sleep(0.2)

def happy_dance():
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("LShoulderPitch", 0, 0.1)
        pepper.setAngles("RShoulderPitch", 1.0, 0.1)
        time.sleep(0.1)
        pepper.setAngles("RShoulderPitch", 0, 0.1)

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

print("\n" + "="*60)
print("🤖 PEPPER WITH LOCAL LIBRARIES")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Balloons float around")
print("✅ Natural arm movement")
print("✅ Commands: dance, robot, wave, happy, hello, exit")
print("="*60 + "\n")

speak("Hello! I am Pepper! I can dance! Say dance, robot, wave, or happy!")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("\n👶 You: ").strip().lower()
        
        if user_input == 'exit':
            speak("Goodbye! See you later!")
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
        elif user_input == 'happy':
            speak("Happy dance!")
            happy_dance()
        elif user_input == 'hello':
            speak("Hello! I am Pepper! Your robot friend!")
        else:
            speak(f"You said: {user_input}")
            
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
