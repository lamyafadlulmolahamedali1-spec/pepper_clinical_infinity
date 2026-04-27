#!/usr/bin/env python3
"""
أبسط اختبار لـ Pepper - فقط Pepper
"""

import time
import pybullet as p
from qibullet import SimulationManager

print("="*50)
print("اختبار Pepper - بدون مجسمات أو أثاث")
print("="*50)

# تشغيل PyBullet
p.connect(p.GUI)
p.setGravity(0, 0, -9.81)
p.resetDebugVisualizerCamera(cameraDistance=3, cameraYaw=0, cameraPitch=-20, cameraTargetPosition=[0, 0, 0.8])

# تشغيل qiBullet
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)

# محاولة إضافة Pepper
print("\nجاري تحميل Pepper...")
try:
    pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
    print("✅ Pepper تم تحميله بنجاح!")
    print("📍 Pepper في المنتصف")
    
    # اختبار حركة الرأس
    print("\nاختبار حركة الرأس...")
    pepper.setAngles("HeadYaw", 0.5, 0.1)
    time.sleep(1)
    pepper.setAngles("HeadYaw", -0.5, 0.1)
    time.sleep(1)
    pepper.setAngles("HeadYaw", 0, 0.1)
    print("✅ Pepper يحرك رأسه!")
    
except Exception as e:
    print(f"❌ خطأ: {e}")
    print("\nمشكلة في تحميل Pepper")

print("\n✅ Pepper شغال. أغلق النافذة للخروج.\n")

# حلقة التشغيل
while True:
    p.stepSimulation()
    time.sleep(1/60.)
