#!/usr/bin/env python3
"""
تشخيص مشكلة Pepper
"""

import pybullet as p
from qibullet import SimulationManager

print("="*50)
print("تشخيص مشكلة Pepper")
print("="*50)

# 1. فتح PyBullet
print("\n1. فتح PyBullet...")
p.connect(p.GUI)
print("   ✅ PyBullet مفتوح")

# 2. إضافة أرضية
print("\n2. إضافة أرضية...")
p.loadURDF("plane.urdf")
print("   ✅ أرضية مضافة")

# 3. تشغيل qiBullet
print("\n3. تشغيل qiBullet...")
sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=False)
print(f"   ✅ qiBullet شغال (client_id: {client_id})")

# 4. محاولة spawn Pepper
print("\n4. محاولة spawn Pepper...")
try:
    pepper = sim_manager.spawnPepper(client_id, translation=[0, 0, 0])
    print("   ✅ Pepper spawned!")
    print(f"   📍 Pepper position: {pepper.getPosition()}")
except Exception as e:
    print(f"   ❌ خطأ في spawn: {e}")

# 5. قائمة بالـ models المتاحة
print("\n5. التحقق من models...")
try:
    print("   ✅ QiBullet يعمل")
except:
    print("   ❌ مشكلة")

print("\n" + "="*50)
print("إذا ظهرت نافذة PyBullet ولا يوجد Pepper، أغلقها وجرب:")
print("pip uninstall qibullet && pip install qibullet")
print("="*50)

while True:
    p.stepSimulation()
