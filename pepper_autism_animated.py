import time
import random
import math
import pybullet as p
from qibullet import SimulationManager

def create_custom_kid(client, pos, color):
    # إنشاء جسم (أسطوانة)، رأس (كرة)، وأطراف
    # الجسم
    body_v = p.createVisualShape(p.GEOM_CYLINDER, radius=0.15, length=0.5, rgbaColor=color, physicsClientId=client)
    body_c = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.15, height=0.5, physicsClientId=client)
    
    kid_id = p.createMultiBody(
        baseMass=1,
        baseCollisionShapeIndex=body_c,
        baseVisualShapeIndex=body_v,
        basePosition=pos,
        physicsClientId=client
    )
    
    # إضافة رأس كروي كـ "طفل"
    head_v = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[1, 0.8, 0.6, 1], physicsClientId=client)
    p.createMultiBody(baseMass=0.1, baseVisualShapeIndex=head_v, basePosition=[pos[0], pos[1], pos[2]+0.4], physicsClientId=client)
    
    return kid_id

def start_therapy_animated():
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🤖 Pepper: Custom Animated Humanoids Mode...")
    
    kids_data = []
    positions = [[2.0, 1.5, 0.3], [2.0, -1.5, 0.3], [3.5, 0.0, 0.3], [0.0, 3.0, 0.3]]
    colors = [[1, 0, 0, 1], [0, 0, 1, 1], [0, 1, 0, 1], [1, 1, 0, 1]]
    
    for i in range(4):
        k_id = create_custom_kid(client, positions[i], colors[i])
        kids_data.append(k_id)

    t = 0
    try:
        while True:
            t += 0.1
            
            # محاكاة حركة بسيطة (اهتزاز كأنهم يتحركون)
            for k_id in kids_data:
                pos, orn = p.getBasePositionAndOrientation(k_id, physicsClientId=client)
                # حركة خفيفة للأعلى والأسفل (تنفس/مشي خفيف)
                new_z = 0.3 + 0.02 * math.sin(t * 2)
                p.resetBasePositionAndOrientation(k_id, [pos[0], pos[1], new_z], orn, physicsClientId=client)

            # تحرك بيبر
            if int(t*10) % 150 == 0:
                target_kid = random.choice(kids_data)
                k_pos, _ = p.getBasePositionAndOrientation(target_kid, physicsClientId=client)
                pep_pos = pepper.getPosition()
                
                dx, dy = k_pos[0] - pep_pos[0], k_pos[1] - pep_pos[1]
                angle = math.atan2(dy, dx)
                
                print(f"🏃 Pepper is visiting a friend at {k_pos[0]:.1f}")
                pepper.moveTo(0, 0, angle, _async=False)
                pepper.moveTo(max(0, math.sqrt(dx**2 + dy**2) - 0.8), 0, 0, _async=False)
                
                # تفاعل (تحريك الرأس واليد)
                pepper.setAngles(["HeadPitch", "RShoulderPitch"], [-0.2, 0.5], 0.1)
                time.sleep(2)
                pepper.setAngles(["HeadPitch", "RShoulderPitch"], [0.1, 1.5], 0.1)
                time.sleep(2)

    except KeyboardInterrupt:
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    start_therapy_animated()
