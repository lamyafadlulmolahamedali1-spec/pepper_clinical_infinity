#!/usr/bin/env python3
"""
PEPPER IN CENTER - غرفة بدون طاولة في النص، Pepper في المنتصف
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

# ========== مجسم ملون (زي رسمة طفل) ==========
class ColoredPerson:
    def __init__(self, x, y, color, name=""):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.body_parts = []
        self.direction = random.choice([-0.02, 0.02])
        self.create_person()
    
    def create_person(self):
        """إنشاء مجسم ملون بأيدين ورجلين ورأس"""
        
        # الرأس (دائرة)
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=self.color)
        head_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=head, basePosition=[self.x, self.y, 0.9])
        self.body_parts.append(head_body)
        
        # الجسم (مستطيل)
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.18, 0.12, 0.35], rgbaColor=self.color)
        body_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=body, basePosition=[self.x, self.y, 0.55])
        self.body_parts.append(body_body)
        
        # الذراع الأيمن
        right_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.3], rgbaColor=self.color)
        right_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_arm, basePosition=[self.x + 0.22, self.y, 0.7])
        self.body_parts.append(right_arm_body)
        
        # الذراع الأيسر
        left_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.3], rgbaColor=self.color)
        left_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_arm, basePosition=[self.x - 0.22, self.y, 0.7])
        self.body_parts.append(left_arm_body)
        
        # الرجل اليمنى
        right_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.3], rgbaColor=self.color)
        right_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_leg, basePosition=[self.x + 0.1, self.y, 0.25])
        self.body_parts.append(right_leg_body)
        
        # الرجل اليسرى
        left_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.3], rgbaColor=self.color)
        left_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_leg, basePosition=[self.x - 0.1, self.y, 0.25])
        self.body_parts.append(left_leg_body)
        
        return self.body_parts
    
    def walk(self):
        """تحريك المجسم"""
        self.x += self.direction
        # تغيير الاتجاه عند الحدود
        if self.x > 3.5 or self.x < -3.5:
            self.direction = -self.direction
            self.x += self.direction
        
        for part in self.body_parts:
            pos, ori = p.getBasePositionAndOrientation(part)
            p.resetBasePositionAndOrientation(part, [self.x, self.y, pos[2]], ori)

# ========== إنشاء غرفة بدون طاولة في المنتصف ==========
def create_room():
    """إنشاء غرفة بجدران وأثاث جانبي - الطاولة في الجنبة"""
    
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # ===== الجدران الأربعة =====
    # جدار شمالي
    wall_north = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_north, basePosition=[0, -4.5, 1])
    
    # جدار جنوبي
    wall_south = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_south, basePosition=[0, 4.5, 1])
    
    # جدار شرقي
    wall_east = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_east, basePosition=[4.5, 0, 1])
    
    # جدار غربي
    wall_west = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_west, basePosition=[-4.5, 0, 1])
    
    # ===== طاولة في الجنب (يمين) =====
    table_top = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_top, basePosition=[3, 2.5, 0.55])
    
    # أرجل الطاولة
    for leg_x, leg_y in [(2.2, 2.2), (2.2, 2.8), (3.8, 2.2), (3.8, 2.8)]:
        leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.5], rgbaColor=[0.4, 0.2, 0.05, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=leg, basePosition=[leg_x, leg_y, 0.25])
    
    # ===== كراسي حول الطاولة الجانبية =====
    chair_positions = [(2.5, 1.8), (3.5, 1.8), (2.5, 3.2), (3.5, 3.2)]
    for cx, cy in chair_positions:
        seat = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.35, 0.35, 0.08], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat, basePosition=[cx, cy, 0.25])
        back = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.35, 0.35], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back, basePosition=[cx, cy - 0.3, 0.55])
    
    # ===== دولاب =====
    cabinet = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.7, 0.4, 1.2], rgbaColor=[0.4, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=cabinet, basePosition=[-3.2, -3, 0.6])
    
    # ===== مراية =====
    mirror = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.6, 0.05, 0.9], rgbaColor=[0.9, 0.9, 1, 0.7])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=mirror, basePosition=[0, -4.4, 1.2])
    
    # ===== بالونات =====
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1]]
    balloons = []
    for i in range(15):
        x = random.uniform(-3.5, 3.5)
        y = random.uniform(-3.5, 3.5)
        color = colors[i % len(colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon_body = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.8)])
        balloons.append(balloon_body)
    
    print("✅ غرفة جاهزة: الطاولة في الجنب، Pepper في المنتصف!")
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.7:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== تحريك المجسمات الملونة ==========
def move_colored_people(people):
    while True:
        for person in people:
            person.walk()
        time.sleep(0.05)

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
            self.pepper.setAngles("HeadYaw", 0.5, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", -0.5, 0.1)
            time.sleep(0.3)
            self.pepper.setAngles("HeadYaw", 0, 0.1)
        except:
            pass

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
                speak("Hello! I'm Pepper! I'm in the center of the room!")
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
                speak("I see a room with a table in the corner, chairs, a cabinet, a mirror, colorful balloons, and colorful people walking!")
            else:
                speak(f"You said: {cmd}")
        except KeyboardInterrupt:
            speak("Goodbye!")
            break

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER IN CENTER - Starting...")
print("="*60)

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة
balloons = create_room()

# إعداد الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# وضع Pepper في المنتصف (0,0)
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
print("✅ Pepper في المنتصف!")

# تهيئة الحركات
gestures = PepperGestures(pepper)

# إنشاء مجسمات ملونة تمشي
colors_list = [
    [1, 0.2, 0.2, 1],  # أحمر
    [0.2, 1, 0.2, 1],  # أخضر
    [0.2, 0.2, 1, 1],  # أزرق
    [1, 1, 0.2, 1],    # أصفر
    [1, 0.5, 0.2, 1],  # برتقالي
    [0.8, 0.2, 0.8, 1], # بنفسجي
]

colored_people = []
names = ["Red", "Green", "Blue", "Yellow", "Orange", "Purple"]

for i in range(6):
    x = random.uniform(-2.5, 2.5)
    y = random.uniform(-3, 3)
    person = ColoredPerson(x, y, colors_list[i], names[i])
    colored_people.append(person)
    print(f"✅ {names[i]} (مجسم ملون) يمشي في الغرفة!")

# تشغيل البالونات
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

# تشغيل المجسمات الملونة
people_thread = threading.Thread(target=move_colored_people, args=(colored_people,), daemon=True)
people_thread.start()

print("\n✅ الطاولة في الجنب (يمين)")
print("✅ Pepper في المنتصف!")
print("✅ 6 مجسمات ملونة تمشي في الغرفة!")
speak("Hello! I am Pepper! I am in the center of the room! Look at the colorful people walking around!")

# بدء التحكم
keyboard_control(pepper, gestures)

print("\n✅ Finished!")
