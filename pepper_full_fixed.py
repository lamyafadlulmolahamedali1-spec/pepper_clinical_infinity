#!/usr/bin/env python3
"""
Pepper في غرفة كاملة - نسخة تعمل 100%
"""

import time
import random
import threading
import pybullet as p
import pybullet_data
from qibullet import SimulationManager

# ========== مجسم شخص ==========
class SimplePerson:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.direction = random.choice([-0.01, 0.01])
        
        # الرأس (دائرة)
        head = p.createVisualShape(p.GEOM_SPHERE, radius=0.13, rgbaColor=color)
        self.head = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=head, basePosition=[x, y, 0.95])
        
        # الجسم (مستطيل)
        body = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.2, 0.14, 0.4], rgbaColor=color)
        self.body = p.createMultiBody(baseMass=0.3, baseVisualShapeIndex=body, basePosition=[x, y, 0.6])
        
        # الذراع الأيمن
        r_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=color)
        self.r_arm = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=r_arm, basePosition=[x + 0.26, y, 0.72])
        
        # الذراع الأيسر
        l_arm = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.07, 0.07, 0.32], rgbaColor=color)
        self.l_arm = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=l_arm, basePosition=[x - 0.26, y, 0.72])
        
        # الرجل اليمنى
        r_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=color)
        self.r_leg = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=r_leg, basePosition=[x + 0.12, y, 0.28])
        
        # الرجل اليسرى
        l_leg = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.09, 0.09, 0.32], rgbaColor=color)
        self.l_leg = p.createMultiBody(baseMass=0.2, baseVisualShapeIndex=l_leg, basePosition=[x - 0.12, y, 0.28])
    
    def walk(self):
        self.x += self.direction
        if self.x > 3.5 or self.x < -3.5:
            self.direction = -self.direction
            self.x += self.direction
        
        for obj in [self.head, self.body, self.r_arm, self.l_arm, self.r_leg, self.l_leg]:
            pos, ori = p.getBasePositionAndOrientation(obj)
            p.resetBasePositionAndOrientation(obj, [self.x, self.y, pos[2]], ori)

# ========== إنشاء الغرفة ==========
def create_room():
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    # جدران
    colors = [[0.8, 0.75, 0.7, 1]]
    
    # جدار شمالي
    wall = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, -4.5, 1])
    
    # جدار جنوبي
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, 4.5, 1])
    
    # جدار شرقي
    wall_e = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 5, 2], rgbaColor=[0.8, 0.75, 0.7, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_e, basePosition=[4.5, 0, 1])
    
    # جدار غربي
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_e, basePosition=[-4.5, 0, 1])
    
    # طاولة
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.1], rgbaColor=[0.5, 0.3, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[3, 2.5, 0.55])
    
    # كراسي
    chair_seat = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.35, 0.35, 0.08], rgbaColor=[0.6, 0.4, 0.2, 1])
    chair_back = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.35, 0.35], rgbaColor=[0.6, 0.4, 0.2, 1])
    
    for cx, cy in [(2.5, 1.8), (3.5, 1.8), (2.5, 3.2), (3.5, 3.2)]:
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_seat, basePosition=[cx, cy, 0.25])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=chair_back, basePosition=[cx, cy - 0.3, 0.55])
    
    # بالونات
    balloon_colors = [[1,0,0,1], [0,1,0,1], [0,0,1,1], [1,1,0,1]]
    balloons = []
    for i in range(10):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        color = balloon_colors[i % len(balloon_colors)]
        balloon = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=color)
        b = p.createMultiBody(baseMass=0.05, baseVisualShapeIndex=balloon, basePosition=[x, y, random.uniform(0.5, 1.3)])
        balloons.append(b)
    
    return balloons

# ========== تحريك البالونات ==========
def float_balloons(balloons):
    while True:
        for b in balloons:
            pos, _ = p.getBasePositionAndOrientation(b)
            new_z = pos[2] + 0.003
            if new_z > 1.3:
                new_z = 0.3
            p.resetBasePositionAndOrientation(b, [pos[0], pos[1], new_z], [0,0,0,1])
        time.sleep(1/50.)

# ========== حركات Pepper ==========
def dance(pepper):
    for l, r in [(0.5, 0.3), (1.0, 0.5), (1.2, 0.8), (0.8, 0.5), (0.3, 0.2), (0, 0)]:
        pepper.setAngles("LShoulderPitch", l, 0.1)
        pepper.setAngles("RShoulderPitch", r, 0.1)
        time.sleep(0.12)

def wave(pepper):
    for angle in [0.3, 0.6, 0.9, 0.6, 0.3, 0]:
        pepper.setAngles("RShoulderPitch", angle, 0.1)
        time.sleep(0.08)

# ========== الرئيسي ==========
print("="*50)
print("🤖 تشغيل Pepper في الغرفة")
print("="*50)

# إغلاق أي اتصال سابق
try:
    p.disconnect()
except:
    pass

# تشغيل PyBullet
p.connect(p.GUI)

# إنشاء الغرفة
balloons = create_room()

# ضبط الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=6, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# إضافة Pepper
print("تحميل Pepper...")
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
print("✅ Pepper في المنتصف!")

# إنشاء أشخاص
people_colors = [[1,0.2,0.2,1], [0.2,1,0.2,1], [0.2,0.2,1,1], [1,1,0.2,1]]
people = []
for i in range(4):
    x = random.uniform(-3, 3)
    y = random.uniform(-3, 3)
    people.append(SimplePerson(x, y, people_colors[i]))

# تشغيل الخيوط
balloon_thread = threading.Thread(target=float_balloons, args=(balloons,), daemon=True)
balloon_thread.start()

print("\n✅ Pepper في المنتصف!")
print("✅ 10 بالونات")
print("✅ 4 أشخاص يمشون\n")

# حلقة المحاكاة
while True:
    p.stepSimulation()
    # تحريك الأشخاص
    for person in people:
        person.walk()
    time.sleep(1/60.)
