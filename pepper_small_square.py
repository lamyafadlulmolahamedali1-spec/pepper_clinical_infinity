import time
from qibullet import SimulationManager

def small_square_move():
    sim_manager = SimulationManager()
    client = sim_manager.launchSimulation(gui=True)
    pepper = sim_manager.spawnPepper(client, spawn_ground_plane=True)

    print("🤖 Adjusting Pepper's posture...")
    # Move arms down to the body (0.0 or small angles)
    # LShoulderRoll/RShoulderRoll close to 0 pulls arms in
    pepper.setAngles(["LShoulderRoll", "RShoulderRoll", "LShoulderPitch", "RShoulderPitch"], 
                     [0.1, -0.1, 1.5, 1.5], 0.1)
    time.sleep(2.0)

    print("🚶 Starting 20cm Square Movement...")
    
    # 0.2 meters = 20 centimeters
    side_length = 0.2 
    turn_90 = 1.57 # 90 degrees in radians

    try:
        while True:
            for i in range(4):
                print(f"  Step {i+1}: Moving {side_length*100}cm forward")
                # Move forward
                pepper.moveTo(side_length, 0.0, 0.0, _async=False)
                time.sleep(0.5)
                
                print(f"  Step {i+1}: Turning 90 degrees")
                # Turn in place
                pepper.moveTo(0.0, 0.0, turn_90, _async=False)
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("🛑 Movement stopped.")
        sim_manager.stopSimulation(client)

if __name__ == "__main__":
    small_square_move()
