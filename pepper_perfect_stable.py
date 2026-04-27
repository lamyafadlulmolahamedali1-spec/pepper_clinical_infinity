import time
import webbrowser
import pyttsx3
import threading
import random
from qibullet import SimulationManager

class PepperPerfectProject:
    def __init__(self):
        # 1. Voice for Support (Setup first to avoid GPU clash)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        
        # 2. Start Simulation (The GPU heavy part)
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        
        self.dashboard_url = "http://localhost:5009"

    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def delayed_browser_launch(self):
        """Wait for simulation to settle before opening the dashboard."""
        time.sleep(3) 
        print(f"🌐 Stability Guard: Launching Dashboard at {self.dashboard_url}")
        webbrowser.open_new(self.dashboard_url)

    def support_logic(self, child_name):
        self.pepper.goToPosture("Stand", 0.6)
        
        # Launch browser in background thread to avoid Segmentation Fault
        threading.Thread(target=self.delayed_browser_launch, daemon=True).start()
        
        self.speak(f"Hello {child_name}! Look at my tablet. We have so many fun games!")
        
        # Interaction Loop
        self.pepper.setAngles("HeadPitch", 0.3, 0.2) 
        self.speak("I am watching you play on my tablet. You are doing a wonderful job!")
        
        compliments = [
            "Great move! You are so smart.",
            "Wow! Look at that progress!",
            "I like how you are focusing on the game.",
            "You are a superstar!"
        ]
        
        try:
            for _ in range(5): # Encourage Ahmed for about 2 minutes
                time.sleep(15)
                # Small encouraging movement
                self.pepper.setAngles("RHand", 1.0, 0.2)
                self.speak(random.choice(compliments))
                self.pepper.setAngles("RHand", 0.0, 0.1)
        except KeyboardInterrupt:
            pass

    def finish(self):
        self.speak("That was a perfect game session. See you next time!")
        self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperPerfectProject()
    try:
        app.support_logic("Ahmed")
        app.finish()
    except Exception as e:
        print(f"Error caught: {e}")
        app.finish()
