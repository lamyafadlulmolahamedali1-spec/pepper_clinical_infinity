import time
from qibullet import SimulationManager

def move_in_line():
    # 1. Setup Simulation
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🤖 Pepper is ready to walk the line!")
    
    try:
        while True:
            # Move Forward 1.0 meter
            print("🚀 Moving Forward...")
            pepper.moveTo(1.0, 0.0, 0.0, _async=False)
            time.sleep(1)
            
            # Move Backward 1.0 meter (returning to 0)
            print("🔙 Moving Backward...")
            pepper.moveTo(-1.0, 0.0, 0.0, _async=False)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("🛑 Movement stopped by user.")
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    move_in_line()
