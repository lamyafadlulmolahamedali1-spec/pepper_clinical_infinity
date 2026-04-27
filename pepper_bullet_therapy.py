import time
import pybullet as p
import pyttsx3
from qibullet import SimulationManager

class PepperTherapySim:
    def __init__(self):
        # 1. Setup Simulation
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        
        # 2. Setup Voice (Comfort Conversation)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 145) # Calm speed
        
        # Move Pepper to a "Welcome" position
        self.pepper.goToPosture("Stand", 0.6)
        time.sleep(1)

    def say_and_move(self, text, animation="wave"):
        print(f"🤖 Pepper: {text}")
        
        # Perform animation based on conversation context
        if animation == "wave":
            self.pepper.setAngles("RHand", 1.0, 0.1)
            self.pepper.setAngles("RShoulderPitch", 0.3, 0.1)
        elif animation == "nod":
            self.pepper.setAngles("HeadPitch", 0.2, 0.1)
            
        self.engine.say(text)
        self.engine.runAndWait()
        
        # Reset posture
        self.pepper.goToPosture("Stand", 0.5)

    def start_conversation(self, child_name):
        # Initial greeting
        self.say_and_move(f"Hello {child_name}! I am so happy to see you today.", "wave")
        time.sleep(1)
        
        # Comfort & Therapy Questions
        self.say_and_move(f"How are you feeling today, {child_name}? I am here to play with you.", "nod")
        time.sleep(2)
        
        self.say_and_move("Look at my hands! Can you clap your hands with me?")
        
        # Keep simulation running
        print("Finalizing session... Press Ctrl+C to close.")
        try:
            while True:
                p.stepSimulation(self.client)
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    # Start the session for Ahmed
    session = PepperTherapySim()
    session.start_conversation("Ahmed")
