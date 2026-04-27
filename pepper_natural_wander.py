import time
import random
from qibullet import SimulationManager

def natural_wander():
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🤖 Pepper is now in 'Explorer Mode'...")
    
    SAFE_ZONE = 3.0

    try:
        while True:
            distance = random.uniform(0.5, 1.5)
            theta = random.uniform(-0.78, 0.78)

            print(f"🚶 Wandering: {distance:.2f}m with a {theta:.2f} rad turn")
            pepper.moveTo(distance, 0.0, theta, _async=False)
            
            time.sleep(random.uniform(1.0, 3.0))

            # --- THE FIX IS HERE ---
            # We just take the whole position vector [x, y, z]
            pos = pepper.getPosition() 
            x, y = pos[0], pos[1] 
            
            if abs(x) > SAFE_ZONE or abs(y) > SAFE_ZONE:
                print(f"⚠️ Edge reached at ({x:.1f}, {y:.1f})! Returning to center...")
                pepper.moveTo(-x, -y, 3.14, _async=False) 

    except KeyboardInterrupt:
        print("🛑 Simulation stopped.")
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    natural_wander()
