#!/usr/bin/env python3
"""
PEPPER - PERMANENT VERSION
يستخدم فقط المكتبات المنسوخة محلياً (لا يحتاج أي تثبيت)
"""

import sys
import os

# ========== إضافة جميع المكتبات المحلية إلى المسار ==========
PROJECT_PATH = '/home/lamya/pepper_duo/src'
LIBS_PATH = os.path.join(PROJECT_PATH, 'permanent_libs')

# إضافة المسار أولاً
sys.path.insert(0, LIBS_PATH)
sys.path.insert(0, PROJECT_PATH)

print("="*60)
print("🤖 PEPPER - PERMANENT LIBRARIES VERSION")
print("="*60)
print(f"📁 Libraries path: {LIBS_PATH}")

# ========== استيراد جميع المكتبات ==========
print("\n📦 Loading libraries...")

try:
    from qibullet import SimulationManager
    print("   ✅ qibullet")
except Exception as e:
    print(f"   ❌ qibullet: {e}")

try:
    import pybullet as p
    import pybullet_data
    print("   ✅ pybullet")
except Exception as e:
    print(f"   ❌ pybullet: {e}")

try:
    import pyttsx3
    print("   ✅ pyttsx3")
except Exception as e:
    print(f"   ❌ pyttsx3: {e}")

try:
    import speech_recognition as sr
    print("   ✅ speech_recognition")
except Exception as e:
    print(f"   ⚠️ speech_recognition: {e}")

try:
    from ultralytics import YOLO
    print("   ✅ ultralytics/YOLO")
except Exception as e:
    print(f"   ⚠️ YOLO: {e}")

try:
    import deepface
    print("   ✅ deepface")
except Exception as e:
    print(f"   ⚠️ deepface: {e}")

try:
    import mediapipe as mp
    print("   ✅ mediapipe")
except Exception as e:
    print(f"   ⚠️ mediapipe: {e}")

try:
    import torch
    print("   ✅ torch")
except Exception as e:
    print(f"   ⚠️ torch: {e}")

import time
import random
import math
import threading

print("\n✅ All libraries loaded!")

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

# ========== رقصات ==========
def gangnam_dance():
    speak("Gangnam style!")
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1)
        time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1)
        time.sleep(0.15)

def robot_dance():
    speak("Robot dance!")
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

def wave():
    speak("Waving!")
    for _ in range(3):
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
print("✅ PEPPER IS READY!")
print("="*60)
print("📝 Commands: dance, robot, wave, hello, exit")
print("="*60 + "\n")

speak("Hello! I am Pepper! All libraries are permanent!")

while True:
    try:
        cmd = input("\n👶 You: ").strip().lower()
        if cmd == 'exit':
            speak("Goodbye!")
            break
        elif cmd == 'dance':
            gangnam_dance()
        elif cmd == 'robot':
            robot_dance()
        elif cmd == 'wave':
            wave()
        elif cmd == 'hello':
            speak("Hello! I am Pepper! Your permanent robot friend!")
        else:
            speak(f"You said: {cmd}")
    except KeyboardInterrupt:
        print("\n")
        speak("Goodbye!")
        break

print("\n✅ Done")
