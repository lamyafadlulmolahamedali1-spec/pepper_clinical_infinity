#!/usr/bin/env python3
"""
Pepper Balloon Chaser - نسخة qiBullet
- بيبر يتحرك في الغرفة
- بالونات تطير
- يتبع البالونات برأسه
"""

import sys
import time
import random
import math
import threading
from qibullet import SimulationManager
import pybullet as p

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

# تحميل بيبر
pepper = sim_manager.spawnPepper(
    client_id,
    translation=[0, 0, 0],
    quaternion=[0, 0, 0, 1],
    spawn_ground_plane=True
)
print("✅ Pepper loaded in qiBullet!")

# ========== إنشاء بالونات (في PyBullet) ==========
# ملاحظة: qiBullet يستخدم PyBullet للفيزياء، فالبالونات ننشئها بنفس الطريقة
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
balloon_positions = []

for i in range(12):
    x = random.uniform(-3.5, 3.5)
    y = random.uniform(-2.8, 2.8)
    z = random.uniform(0.5, 1.8)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)
    balloon_positions.append([x, y, z, random.uniform(0.008, 0.02)])

print("🎈 12 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
is_dancing = False

# ========== رقصة ==========
def gangnam_dance():
    global is_dancing
    is_dancing = True
    print("💃 Pepper is dancing!")
    
    for _ in range(3):
        pepper.setAngles("LShoulderPitch", 1.2, 0.15)
        pepper.setAngles("RShoulderPitch", 1.2, 0.15)
        time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0.2, 0.15)
        pepper.setAngles("RShoulderPitch", 0.2, 0.15)
        time.sleep(0.2)
    
    for _ in range(3):
        pepper.setAngles("HeadYaw", 0.8, 0.15)
        time.sleep(0.15)
        pepper.setAngles("HeadYaw", -0.8, 0.15)
        time.sleep(0.15)
    
    pepper.setAngles("HeadYaw", 0, 0.15)
    is_dancing = False

# ========== حركة يدين طبيعية ==========
arm_angle = 0
arm_dir = 1

def natural_arms():
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

# ========== حركة مشي ==========
def fast_walking():
    global robot_x, robot_y, t
    while True:
        if not is_dancing:
            t += 0.045
            robot_x = 3.2 * math.cos(t * 0.55)
            robot_y = 2.8 * math.sin(t * 0.7)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.035)

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
                    pepper.setAngles("HeadYaw", head_yaw, 0.1)
                except:
                    pass
        time.sleep(0.05)

# ========== تحديث البالونات ==========
def update_balloons():
    while True:
        for i, b in enumerate(balloons):
            new_z = balloon_positions[i][2] + balloon_positions[i][3]
            if new_z > 1.9:
                new_z = 0.3
                balloon_positions[i][0] = random.uniform(-3.5, 3.5)
                balloon_positions[i][1] = random.uniform(-2.8, 2.8)
            balloon_positions[i][2] = new_z
            p.resetBasePositionAndOrientation(b, [balloon_positions[i][0], balloon_positions[i][1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== بدء التشغيل ==========
threading.Thread(target=natural_arms, daemon=True).start()
threading.Thread(target=fast_walking, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER IN QIBULLET + BALLOONS")
print("="*60)
print("✅ Pepper walks continuously")
print("✅ Pepper moves arms naturally")
print("✅ Pepper looks at balloons")
print("✅ Type 'dance' - Pepper dances")
print("✅ Type 'exit' - Quit")
print("="*60 + "\n")

# ========== المحادثة ==========
while True:
    try:
        user_input = input("👶 You: ").strip().lower()
        
        if user_input == 'exit':
            print("🤖 Pepper: Goodbye!")
            break
        elif user_input == 'dance':
            gangnam_dance()
        elif user_input == 'hello':
            print("🤖 Pepper: Hello! I am Pepper!")
        else:
            print(f"🤖 Pepper: You said: {user_input}")
            
    except KeyboardInterrupt:
        print("\n🤖 Pepper: Goodbye!")
        break

print("\n✅ Done")
