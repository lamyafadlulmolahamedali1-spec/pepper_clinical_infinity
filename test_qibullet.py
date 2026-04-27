#!/usr/bin/env python3
"""
اختبار qiBullet - بيبر في غرفة بسيطة
"""

import sys
import time
from qibullet import SimulationManager

print("🤖 Testing qiBullet with Pepper...")

simulation_manager = SimulationManager()

# تشغيل المحاكاة
client_id = simulation_manager.launchSimulation(gui=True)

# تحميل بيبر مع أرضية
pepper = simulation_manager.spawnPepper(
    client_id,
    translation=[0, 0, 0],
    quaternion=[0, 0, 0, 1],
    spawn_ground_plane=True
)

print("✅ Pepper loaded in qiBullet!")
print("📌 Close the window to exit")

# تحريك بيبر (اختبار)
pepper.setAngles("HeadYaw", 0.5, 0.5)
time.sleep(1)
pepper.setAngles("HeadYaw", -0.5, 0.5)
time.sleep(1)
pepper.setAngles("HeadYaw", 0, 0.5)

# انتظار المستخدم
if sys.version_info[0] >= 3:
    input("Press Enter to exit")
else:
    raw_input("Press Enter to exit")

simulation_manager.stopSimulation(client_id)
print("✅ Done")
