#!/usr/bin/env python3
"""
PEPPER FINAL WORKING - Pepper في المنتصف + أشخاص هندسيين
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

# ========== مجسم شخص بأشكال هندسية ==========
class GeometricPerson:
    def __init__(self, x, y, color, name=""):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.body_parts = []
        self.direction = random.choice([-0.015, 0.015])
        self.create_person()
    
    def create_person(self):
        # الرأس (دائرة)
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.13, rgbaColor=self.color)
        head_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=head, basePosition=[self.x, self.y, 0.95])
        self.body_parts.append(head_body)
        
        # الجسم (مستطيل)
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.14, 0.4], rgbaColor=self.color)
        body_body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=body, basePosition=[self.x, self.y, 0.6])
        self.body_parts.append(body_body)
        
        # الذراع الأيمن
        right_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=self.color)
        right_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_arm, basePosition=[self.x + 0.26, self.y, 0.72])
        self.body_parts.append(right_arm_body)
        
        # الذراع الأيسر
        left_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=self.color)
        left_arm_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_arm, basePosition=[self.x - 0.26, self.y, 0.72])
        self.body_parts.append(left_arm_body)
        
        # الرجل اليمنى
        right_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=self.color)
        right_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=right_leg, basePosition=[self.x + 0.12, self.y, 0.28])
        self.body_parts.append(right_leg_body)
        
        # الرجل اليسرى
        left_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=self.color)
        left_leg_body = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=left_leg, basePosition=[self.x - 0.12, self.y, 0.28])
        self.body_parts.append(left_leg_body)
    
    def walk(self):
        self.x += self.direction
        if self.x > 3.5 or self.x < -3.5:
            self.direction = -self.direction
            self.x += self.direction
        for part in self.body_parts:
            pos, ori = p.getBasePositionAndOrientation(part)
            p.resetBasePositionAndOrientation(part, [self.x, self.y, pos[2]], ori)

# ========== إنشاء غرفة ==========
def create_room():
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # جدران
    wall_north = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_north, basePosition=[0, -4.5, 1])
    
    wall_south = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_south, basePosition=[0, 4.5, 1])
    
    wall_east = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_east, basePosition=[4.5, 0, 1])
    
    wall_west = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_west, basePosition=[-4.5, 0, 1])
    
    # طاولة في الجنب
    table_top = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table_top, basePosition=[3, 2.5, 0.55])
    
    # كراسي
    chair_positions = [(2.5, 1.8), (3.5, 1.8), (2.5, 3.2), (3.5, 3.2)]
    for cx, cy in chair_positions:
        seat = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.35, 0.35, 0.08], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=seat, basePosition=[cx, cy, 0.25])
        back = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.35, 0.35], rgbaColor=[0.6, 0.4, 0.2, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=back, basePosition=[cx, cy - 0.3, 0.55])
    
    # بالونات
    colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1], [1,0.5,0,1], [0.8,0.2,0.8,1]]
    balloons = []
    for i in range(12):
        x = random.uniform(-3.5, 3.5)
        y = random.uniform(-3.5, 3.5)
        color = colors[i % len(colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        balloon_body = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.5)])
        balloons.append(balloon_body)
    
    return balloons

# ========== تحريك البالونات ==========
def animate_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.005
            if new_z > 1.5:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        p.stepSimulation()
        time.sleep(1/50.)

# ========== تحريك الأشخاص ==========
def move_people(people):
    while True:
        for person in people:
            person.walk()
        time.sleep(0.05)

# ========== الرئيسي ==========
print("="*60)
print("🤖 PEPPER IN CENTER WITH GEOMETRIC PEOPLE")
print("="*60)

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة
balloons = create_room()

# ضبط الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# إضافة Pepper في المنتصف
print("🤖 جاري تحميل Pepper...")
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
print("✅ Pepper في المنتصف!")

# إنشاء أشخاص هندسيين
colors_list = [[1,0.2,0.2,1], [0.2,1,0.2,1], [0.2,0.2,1,1], [1,1,0.2,1], [1,0.5,0.2,1], [0.8,0.2,0.8,1]]
people = []

for i in range(6):
    x = random.uniform(-3, 3)
    y = random.uniform(-3, 3)
    person = GeometricPerson(x, y, colors_list[i], f"Person{i+1}")
    people.append(person)
    print(f"✅ شخص {i+1} (دائرة + مستطيلات)")

# تشغيل الخيوط
balloon_thread = threading.Thread(target=animate_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

people_thread = threading.Thread(target=move_people, args=(people,), daemon=True)
people_thread.start()

print("\n" + "="*50)
print("📍 Pepper في المنتصف!")
print("📍 12 بالون طائر")
print("📍 6 أشخاص يمشون بأشكال هندسية")
print("="*50 + "\n")

speak("Hello! I am Pepper! I am in the center of the room!")

# حلقة رئيسية
try:
    while True:
        p.stepSimulation()
        time.sleep(1/60.)
except KeyboardInterrupt:
    print("\n👋 Goodbye!")
