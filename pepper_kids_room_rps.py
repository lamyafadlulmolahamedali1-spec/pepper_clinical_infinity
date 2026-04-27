import time
import random
import math
import pybullet as p
import pyttsx3
from qibullet import SimulationManager

# إعداد الصوت بالعربي (إذا كان النظام يدعمه) أو إنجليزي واضح
engine = pyttsx3.init()
engine.setProperty('rate', 145)

def create_animated_kid(client, pos):
    """بناء طفل بمفاصل متحركة للعب - تم تصحيح الوسائط"""
    # 1. الجسم الأساسي (استخدام height بدلاً من length)
    v_torso = p.createVisualShape(p.GEOM_CAPSULE, radius=0.15, length=0.4, rgbaColor=[0.2, 0.6, 1, 1])
    c_torso = p.createCollisionShape(p.GEOM_CAPSULE, radius=0.15, height=0.4) 
    kid_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=c_torso, 
                                baseVisualShapeIndex=v_torso, basePosition=pos)
    
    # 2. الرأس
    v_head = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=[1, 0.8, 0.6, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_head, basePosition=[pos[0], pos[1], pos[2]+0.4])
    
    # 3. الذراع
    v_arm = p.createVisualShape(p.GEOM_CYLINDER, radius=0.04, length=0.3, rgbaColor=[1, 0.8, 0.6, 1])
    arm_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_arm, 
                               basePosition=[pos[0]-0.25, pos[1], pos[2]+0.2],
                               baseOrientation=p.getQuaternionFromEuler([0, 1.57, 0]))
    return kid_id, arm_id

def start_play_session():
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🏠 Playroom is ready!")
    # طاولة اللعب
    v_table = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.5, 0.3], rgbaColor=[0.8, 0.4, 0.1, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_table, basePosition=[1.0, 0, 0.3])

    kid_body, kid_arm = create_animated_kid(client, [1.6, 0, 0.5])

    try:
        while True:
            msg = "يلا نلعب! واحد.. اثنين.. ثلاثة"
            print(f"🤖 Pepper: {msg}")
            engine.say("Let's play! One.. Two.. Three!")
            engine.runAndWait()
            
            # حركة العد المشتركة
            for i in range(3):
                pepper.setAngles("RElbowRoll", 1.5, 0.2)
                p.resetBasePositionAndOrientation(kid_arm, [1.35, 0, 0.8], p.getQuaternionFromEuler([0, 1.57, 0]))
                time.sleep(0.5)
                
                pepper.setAngles("RElbowRoll", 0.5, 0.2)
                p.resetBasePositionAndOrientation(kid_arm, [1.35, 0, 0.7], p.getQuaternionFromEuler([0, 1.57, 0]))
                time.sleep(0.5)

            choices = ["ROCK", "PAPER", "SCISSORS"]
            p_choice = random.choice(choices)
            k_choice = random.choice(choices)

            # استجابة بيبر
            if p_choice == "PAPER":
                pepper.setAngles("RHand", 1.0, 0.2)
            else:
                pepper.setAngles("RHand", 0.0, 0.2)

            print(f"🤖 Pepper: {p_choice} | 👶 Kid: {k_choice}")
            time.sleep(4)

    except KeyboardInterrupt:
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    start_play_session()
