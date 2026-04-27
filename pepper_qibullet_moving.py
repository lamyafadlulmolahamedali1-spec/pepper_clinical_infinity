#!/usr/bin/env python3
"""
Pepper في qiBullet - يتحرك باستمرار في غرفة واسعة
مع كل الميزات من PyBullet
"""

import time
import random
import math
import threading
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== بدء qiBullet ==========
print("🤖 Starting Pepper in qiBullet...")

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)

# تحميل بيبر (بدون spawn_ground_plane عشان نضيف أرضية أكبر)
pepper = sim_manager.spawnPepper(
    client_id,
    translation=[0, 0, 0],
    quaternion=[0, 0, 0, 1]
)

# إضافة أرضية كبيرة
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.setGravity(0, 0, -9.81)

print("✅ Pepper loaded in qiBullet!")

# ========== إنشاء غرفة واسعة ==========
# أرضية أكبر
floor = p.createVisualShape(p.GEOM_BOX, halfExtents=[10, 10, 0.05], rgbaColor=[0.4, 0.4, 0.4, 1])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=floor, basePosition=[0, 0, -0.05])

# جدران شفافة لتحديد المساحة
wall_color = [0.8, 0.8, 0.9, 0.3]
wall = p.createVisualShape(p.GEOM_BOX, halfExtents=[10, 0.1, 2.5], rgbaColor=wall_color)
p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, -5.5, 1.2])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, 5.5, 1.2])
wall_side = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5.5, 2.5], rgbaColor=wall_color)
p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[-6, 0, 1.2])
p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[6, 0, 1.2])

print("🏠 Large room created!")

# ========== بالونات ملونة ==========
colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [1,0,1,1]]
balloons = []
balloon_positions = []

for i in range(15):
    x = random.uniform(-5, 5)
    y = random.uniform(-4, 4)
    z = random.uniform(0.5, 2)
    vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.13, rgbaColor=colors[i%6])
    ball = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis, basePosition=[x, y, z])
    balloons.append(ball)
    balloon_positions.append([x, y, z, random.uniform(0.006, 0.018)])

print("🎈 15 balloons created!")

# ========== كاميرا ==========
p.resetDebugVisualizerCamera(cameraDistance=10, cameraYaw=45, cameraPitch=-35, cameraTargetPosition=[0, 0, 0.8])

# ========== متغيرات الحركة ==========
robot_x, robot_y = 0, 0
t = 0
head_yaw = 0
arm_angle = 0
arm_dir = 1
is_dancing = False

# ========== رقصة ==========
def dance_gangnam():
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

# ========== حركة يدين طبيعية مستمرة ==========
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

# ========== حركة رأس طبيعية ==========
def natural_head():
    tt = 0
    while True:
        if not is_dancing:
            tt += 0.02
            yaw = math.sin(tt) * 0.3
            pitch = math.sin(tt * 0.7) * 0.1
            try:
                pepper.setAngles("HeadYaw", yaw, 0.05)
                pepper.setAngles("HeadPitch", pitch, 0.05)
            except:
                pass
        time.sleep(0.04)

# ========== حركة مشي سريعة ومستمرة (لافي في المساحة) ==========
def continuous_walking():
    global robot_x, robot_y, t
    while True:
        if not is_dancing:
            t += 0.045
            # مسار دائري واسع (يجوب كل الغرفة)
            robot_x = 4.5 * math.cos(t * 0.4)
            robot_y = 3.8 * math.sin(t * 0.55)
            try:
                pepper.setTranslation([robot_x, robot_y, 0.8])
            except:
                pass
        time.sleep(0.035)

# ========== تتبع البالونات بالرأس ==========
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

# ========== تحديث البالونات (تطير للأعلى) ==========
def update_balloons():
    while True:
        for i, b in enumerate(balloons):
            new_z = balloon_positions[i][2] + balloon_positions[i][3]
            if new_z > 2.2:
                new_z = 0.3
                balloon_positions[i][0] = random.uniform(-5, 5)
                balloon_positions[i][1] = random.uniform(-4, 4)
            balloon_positions[i][2] = new_z
            p.resetBasePositionAndOrientation(b, [balloon_positions[i][0], balloon_positions[i][1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/60.)

# ========== بدء التشغيل ==========
threading.Thread(target=natural_arms, daemon=True).start()
threading.Thread(target=natural_head, daemon=True).start()
threading.Thread(target=continuous_walking, daemon=True).start()
threading.Thread(target=track_balloons, daemon=True).start()
threading.Thread(target=update_balloons, daemon=True).start()

print("\n" + "="*60)
print("🤖 PEPPER IN QIBULLET - ALWAYS MOVING")
print("="*60)
print("✅ Pepper walks CONTINUOUSLY in a large room")
print("✅ Pepper moves arms naturally")
print("✅ Pepper looks at balloons")
print("✅ Balloons float up and down")
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
            dance_gangnam()
        elif user_input == 'hello':
            print("🤖 Pepper: Hello! I am Pepper! I love walking around!")
        else:
            print(f"🤖 Pepper: You said: {user_input}")
            
    except KeyboardInterrupt:
        print("\n🤖 Pepper: Goodbye!")
        break

print("\n✅ Done")
