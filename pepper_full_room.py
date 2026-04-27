#!/usr/bin/env python3
"""
PEPPER FULL ROOM - غرفة كاملة مع مجسم بشري و Pepper
"""

import time
import math
import random
import threading
import pyttsx3
import pybullet as p
import pybullet_data
from qibullet import SimulationManager

# ========== الصوت ==========
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    print(f"🔊 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

# ========== إنشاء مجسم بشري كامل ==========
def create_human(x, y, color=[0.9, 0.7, 0.5, 1]):
    """إنشاء مجسم بشري بأيدين ورجلين ورأس"""
    
    body_parts = []
    
    # الرأس (دائرة)
    head = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=color)
    head_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=head, basePosition=[x, y, 1.0])
    body_parts.append(head_body)
    
    # الصدر والبطن (مستطيل كبير)
    torso = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.15, 0.4], rgbaColor=color)
    torso_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=torso, basePosition=[x, y, 0.65])
    body_parts.append(torso_body)
    
    # الذراع الأيمن (مستطيل طويل)
    right_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.35], rgbaColor=color)
    right_arm_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=right_arm, basePosition=[x + 0.25, y, 0.75])
    body_parts.append(right_arm_body)
    
    # الذراع الأيسر
    left_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.35], rgbaColor=color)
    left_arm_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=left_arm, basePosition=[x - 0.25, y, 0.75])
    body_parts.append(left_arm_body)
    
    # الرجل اليمنى (مستطيل)
    right_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.35], rgbaColor=color)
    right_leg_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=right_leg, basePosition=[x + 0.12, y, 0.3])
    body_parts.append(right_leg_body)
    
    # الرجل اليسرى
    left_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.35], rgbaColor=color)
    left_leg_body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=left_leg, basePosition=[x - 0.12, y, 0.3])
    body_parts.append(left_leg_body)
    
    return body_parts

# ========== إنشاء غرفة كاملة ==========
def create_full_room():
    """إنشاء غرفة بجدران وأثاث كامل"""
    
    # إضافة مسار PyBullet
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    
    # أرضية
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # ===== الجدران الأربعة =====
    # جدار شمالي (خلفي)
    wall_north = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.7, 0.6, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_north, basePosition=[0, -4.5, 1])
    
    # جدار جنوبي (أمامي)
    wall_south = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.7, 0.6, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_south, basePosition=[0, 4.5, 1])
    
    # جدار شرقي (يمين)
    wall_east = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.7, 0.6, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_east, basePosition=[4.5, 0, 1])
    
    # جدار غربي (يسار)
    wall_west = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.7, 0.6, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_west, basePosition=[-4.5, 0, 1])
    
    # ===== أثاث =====
    
    # طاولة
    table_top = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_top, basePosition=[0, 0, 0.55])
    
    # أرجل الطاولة
    for leg_x, leg_y in [(-0.7, -0.5), (-0.7, 0.5), (0.7, -0.5), (0.7, 0.5)]:
        leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.5], rgbaColor=[0.4, 0.2, 0.05, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg, basePosition=[leg_x, leg_y, 0.25])
    
    # كراسي (4 كراسي حول الطاولة)
    chair_positions = [(-1.5, -1.2), (1.5, -1.2), (-1.5, 1.2), (1.5, 1.2)]
    for cx, cy in chair_positions:
        # قاعدة الكرسي
        seat = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.4, 0.08], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat, basePosition=[cx, cy, 0.25])
        # ظهر الكرسي
        back = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.4, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back, basePosition=[cx, cy - 0.35, 0.55])
    
    # دولاب (خزانة)
    cabinet = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.8, 0.4, 1.2], rgbaColor=[0.4, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=cabinet, basePosition=[3, -3, 0.6])
    
    # مراية على الجدار
    mirror = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.6, 0.05, 0.9], rgbaColor=[0.9, 0.9, 1, 0.8])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=mirror, basePosition=[0, -4.4, 1.2])
    
    # ===== بالونات =====
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1]]
    balloons = []
    for i in range(15):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        color = colors[i % len(colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon_body = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.8)])
        balloons.append(balloon_body)
    
    # ===== أشخاص (مجسمات كاملة) =====
    human1 = create_human(-2, -2, [0.9, 0.7, 0.5, 1])  # شخص بلون بشرة
    human2 = create_human(2.5, 2, [0.8, 0.6, 0.4, 1])   # شخص تاني
    human3 = create_human(-2.5, 2.5, [0.95, 0.8, 0.6, 1]) # شخص تالت
    
    print("✅ غرفة كاملة: 4 جدران، طاولة، 4 كراسي، دولاب، مراية، 15 بالون، 3 أشخاص!")
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.8:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== حركات Pepper ==========
class PepperGestures:
    def __init__(self, pepper):
        self.pepper = pepper
    
    def wave(self):
        for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
            try:
                self.pepper.setAngles("RShoulderPitch", angle, 0.1)
                time.sleep(0.08)
            except:
                pass
    
    def dance(self):
        moves = [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]
        for l, r in moves:
            try:
                self.pepper.setAngles("LShoulderPitch", l, 0.1)
                self.pepper.setAngles("RShoulderPitch", r, 0.1)
                time.sleep(0.12)
            except:
                pass
    
    def move_head(self):
        try:
            self.pepper.setAngles("HeadYaw", 0.4, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", -0.4, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", 0, 0.1)
        except:
            pass

# ========== تحريك Pepper في الغرفة ==========
def move_pepper_in_room(pepper):
    """Pepper يتحرك في مسار دائري حول الغرفة"""
    t = 0
    while True:
        t += 0.02
        radius = 2.5
        x = radius * math.cos(t * 0.3)
        y = radius * math.sin(t * 0.4)
        try:
            # استخدام setPosition بدلاً من setTranslation
            pepper.setPosition([x, y, 0])
            # اتجاه الجسم
            angle = math.atan2(y, x)
            pepper.setOrientation([0, 0, angle])
        except:
            pass
        time.sleep(0.05)

# ========== التحكم ==========
def keyboard_control(pepper, gestures):
    print("\n" + "="*50)
    print("🎮 التحكم في Pepper:")
    print("   h = يقول Hello")
    print("   w = يلوح")
    print("   d = يرقص")
    print("   t = تعليم")
    print("   m = طبي")
    print("   v = يوصف الغرفة")
    print("   q = خروج")
    print("="*50 + "\n")
    
    while True:
        try:
            cmd = input("👤 Command: ").strip().lower()
            if cmd == 'q':
                speak("Goodbye!")
                break
            elif cmd == 'h':
                speak("Hello! I'm Pepper!")
                gestures.move_head()
            elif cmd == 'w':
                gestures.wave()
                speak("Hello!")
            elif cmd == 'd':
                gestures.dance()
                speak("Let's dance!")
            elif cmd == 't':
                speak("Let's learn! 1, 2, 3, 4, 5")
                for i in range(1, 6):
                    speak(str(i))
                    time.sleep(0.5)
            elif cmd == 'm':
                speak("Take a deep breath... in... and out...")
            elif cmd == 'v':
                speak("I see a beautiful room with 4 walls, a table, chairs, a cabinet, a mirror, balloons, and people!")
            else:
                speak(f"You said: {cmd}")
        except KeyboardInterrupt:
            speak("Goodbye!")
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER FULL ROOM - Starting...")
print("="*60)

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة
balloons = create_full_room()

# إعداد الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])

# تهيئة الحركات
gestures = PepperGestures(pepper)

# تشغيل البالونات
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

# تشغيل حركة Pepper
move_thread = threading.Thread(target=move_pepper_in_room, args=(pepper,), daemon=True)
move_thread.start()

print("\n✅ Pepper يتحرك في الغرفة!")
speak("Hello! I am Pepper! Welcome to my beautiful room!")

# بدء التحكم
keyboard_control(pepper, gestures)

print("\n✅ Finished!")
