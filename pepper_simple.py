#!/usr/bin/env python3
"""
Pepper فقط - أبسط كود ممكن
"""

import time
import pybullet as p
from qibullet import SimulationManager

print("="*50)
print("جاري تشغيل Pepper...")
print("="*50)

# تشغيل PyBullet
physics_client = p.connect(p.GUI)
p.setGravity(0, 0, -9.81)
p.loadURDF("plane.urdf")

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# إضافة Pepper
print("تحميل Pepper...")
pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])

# ضبط الكاميرا
p.resetDebugVisualizerCamera(cameraDistance=3, cameraYaw=0, cameraPitch=-20, cameraTargetPosition=[0, 0, 0.8])

print("✅ Pepper موجود في المنتصف!")
print("📌 أغلق النافذة للخروج\n")

# حركة بسيطة للتأكد
pepper.setAngles("HeadYaw", 0.5, 0.1)
time.sleep(0.5)
pepper.setAngles("HeadYaw", -0.5, 0.1)
time.sleep(0.5)
pepper.setAngles("HeadYaw", 0, 0.1)
print("✅ Pepper يحرك رأسه!")

# حلقة التشغيل
while True:
    p.stepSimulation()
    time.sleep(1/60.)
