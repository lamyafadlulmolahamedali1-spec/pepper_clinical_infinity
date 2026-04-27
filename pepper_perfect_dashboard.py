import time
import webbrowser
import pyttsx3
import threading
from qibullet import SimulationManager

class PepperPerfectProject:
    def __init__(self):
        # 1. Start Simulation
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        
        # 2. Voice for Support
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 155)
        
        # 3. Game Dashboard URL
        self.dashboard_url = "http://localhost:5009"

    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def open_tablet_dashboard(self):
        """Opens the game dashboard in a browser window to act as the tablet."""
        print(f"🌐 Launching Tablet Dashboard at {self.dashboard_url}")
        webbrowser.open_new(self.dashboard_url)

    def support_logic(self, child_name):
        # Initial Greeting
        self.pepper.goToPosture("Stand", 0.6)
        self.speak(f"Hello {child_name}! Look at my tablet. We have so many fun games to play!")
        
        # Open the dashboard
        self.open_tablet_dashboard()
        
        # Interaction Loop
        self.pepper.setAngles("HeadPitch", 0.3, 0.2) # Pepper looks at the "tablet"
        self.speak("I am watching you play. You are doing a wonderful job!")
        
        # Random compliments every 15 seconds to keep the child motivated
        compliments = [
            "Great move! You are so smart.",
            "Wow! Look at that progress!",
            "I like how you are focusing on the game.",
            "You are a superstar!"
        ]
        
        try:
            for i in range(3): # Run for 3 rounds of play
                time.sleep(15)
                self.pepper.setAngles("RHand", 1.0, 0.1) # Hand gesture
                self.speak(random.choice(compliments))
                self.pepper.setAngles("RHand", 0.0, 0.1)
        except KeyboardInterrupt:
            pass

    def finish(self):
        self.speak("That was a perfect game session. See you next time!")
        self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    import random
    app = PepperPerfectProject()
    try:
        app.support_logic("Ahmed")
        app.finish()
    except Exception as e:
        print(f"Error: {e}")
        app.finish()
