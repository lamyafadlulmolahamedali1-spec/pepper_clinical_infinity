import time
import pybullet as p
import pybullet_data
from qibullet import SimulationManager

print("🚀 اختبار qiBullet...")
sim_manager = SimulationManager()
client = sim_manager.launchSimulation(gui=True)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")

print("✅ إذا رأيت نافذة المحاكاة، qiBullet يعمل!")
print("⏳ انتظر 10 ثواني...")
time.sleep(10)

sim_manager.stopSimulation(client)
print("👋 انتهى")
