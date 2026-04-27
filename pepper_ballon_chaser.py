import pybullet as p
import pybullet_data
import time
import math

def run_ballon_chaser():
    # الاتصال بالمحاكي
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    
    # تحميل الأرضية والروبوت (كبديل لبيبر في المحاكاة السريعة)
    p.loadURDF("plane.urdf")
    robot_id = p.loadURDF("r2d2.urdf", [0, 0, 0.5])
    
    # إنشاء "البالونة" (كرة حمراء صغيرة)
    ballon_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0, 0, 1])
    ballon_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=ballon_visual, basePosition=[2, 2, 1])

    print("🎈 نظام مطاردة البالونات نشط! بيبر يراقب الهدف...")

    t = 0
    while True:
        p.stepSimulation()
        
        # تحريك البالونة بشكل دائري (كأنها تطير)
        target_x = 2 * math.cos(t)
        target_y = 2 * math.sin(t)
        p.resetBasePositionAndOrientation(ballon_id, [target_x, target_y, 1], [0,0,0,1])
        
        # جعل الروبوت "ينظر" باتجاه البالونة (محاكاة المطاردة)
        pos, _ = p.getBasePositionAndOrientation(robot_id)
        # منطق بسيط للتحرك نحو الهدف
        new_x = pos[0] + (target_x - pos[0]) * 0.01
        new_y = pos[1] + (target_y - pos[1]) * 0.01
        p.resetBasePositionAndOrientation(robot_id, [new_x, new_y, 0.5], [0,0,0,1])
        
        t += 0.01
        time.sleep(1./240.)

if __name__ == "__main__":
    run_ballon_chaser()
