import time
import random
import math
import pybullet as p
from qibullet import SimulationManager

def start_therapy_session():
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🤖 Pepper: Starting Human Interaction Mode...")
    
    # 1. Gentle Posture (Arms down, head looking forward)
    pepper.setAngles(["LShoulderPitch", "RShoulderPitch", "HeadPitch"], [1.5, 1.5, 0.1], 0.1)
    
    # 2. Spawn "Kids" as Human Capsules (Tall cylinders with rounded tops)
    kids = []
    # Fixed positions to keep them "away from each other"
    positions = [[2.5, 2.0, 0.6], [2.5, -2.0, 0.6], [4.5, 0.5, 0.6], [1.0, 3.5, 0.6]]
    colors = [[1, 0.5, 0.5, 1], [0.5, 1, 0.5, 1], [0.5, 0.5, 1, 1], [1, 1, 0.5, 1]]
    
    for i in range(len(positions)):
        # Create a CAPSULE (Height 1.2m, Radius 0.25m - like a small child)
        visual_id = p.createVisualShape(
            shapeType=p.GEOM_CAPSULE, 
            radius=0.25, 
            length=1.0, 
            rgbaColor=colors[i],
            physicsClientId=client)
        
        kid_id = p.createMultiBody(
            baseVisualShapeIndex=visual_id,
            basePosition=positions[i],
            physicsClientId=client)
        kids.append(kid_id)

    print("👤 4 Human-shaped friends are ready and spread out!")

    try:
        while True:
            # SHUFFLE the list so he visits everyone once in a random order
            random.shuffle(kids)
            
            for target_kid in kids:
                kid_pos, _ = p.getBasePositionAndOrientation(target_kid, physicsClientId=client)
                pep_pos = pepper.getPosition()
                
                dx = kid_pos[0] - pep_pos[0]
                dy = kid_pos[1] - pep_pos[1]
                angle_to_kid = math.atan2(dy, dx)
                
                # Stop 0.9 meters away (Safe, respectful distance)
                approach_dist = math.sqrt(dx**2 + dy**2) - 0.9
                
                print(f"👋 Moving to friend at {kid_pos[0], kid_pos[1]}...")
                
                # 1. Turn to face them first (Natural behavior)
                pepper.moveTo(0, 0, angle_to_kid, _async=False)
                # 2. Walk forward
                pepper.moveTo(max(0, approach_dist), 0, 0, _async=False)
                
                # Interaction
                print("✨ Pepper: 'Hello! I am happy to spend time with you.'")
                # Small "looking around" head movement
                pepper.setAngles("HeadYaw", 0.3, 0.05)
                time.sleep(1.5)
                pepper.setAngles("HeadYaw", -0.3, 0.05)
                time.sleep(1.5)
                pepper.setAngles("HeadYaw", 0.0, 0.05)
                
                time.sleep(4) # Quiet time in front of them
                
                # Back away a tiny bit to avoid "kicking" them on the turn
                pepper.moveTo(-0.3, 0, 0, _async=False)

            print("✅ All friends visited! Starting the next round...")

    except KeyboardInterrupt:
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    start_therapy_session()
