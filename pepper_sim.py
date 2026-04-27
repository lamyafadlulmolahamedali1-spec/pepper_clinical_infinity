import pybullet as p
import pybullet_data
import time
import os

def start_sim():
    physicsClient = p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    planeId = p.loadURDF("plane.urdf")
    
    print("🤖 محاكي بيبر يعمل الآن.. الروبوت جاهز للتفاعل")
    # ملاحظة: سنستخدم مكعب كبديل لبيبر إذا لم يتوفر ملف URDF الخاص به حالياً
    pepperId = p.loadURDF("r2d2.urdf", [0, 0, 1]) 
    
    while True:
        p.stepSimulation()
        time.sleep(1./240.)

if __name__ == "__main__":
    start_sim()
