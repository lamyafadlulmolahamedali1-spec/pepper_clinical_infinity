import time
import requests
import pyttsx3
import threading
from qibullet import SimulationManager

class PepperInteractiveRobot:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        self.engine = pyttsx3.init()
        
        # Smooth Startup: Arms down, relaxed posture
        self.pepper.goToPosture("Stand", 0.6)
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], [1.5, 1.5], 0.1)

    def speak_and_move(self, text, is_correct):
        print(f"🤖 Pepper: {text}")
        
        if is_correct:
            self.pepper.setAngles("HeadPitch", -0.2, 0.05) # Look up happily
            self.pepper.setAngles(["RShoulderRoll", "LShoulderRoll"], [-0.3, 0.3], 0.05)
        else:
            self.pepper.setAngles("HeadPitch", 0.2, 0.05) # Look down supportively
            
        self.engine.say(text)
        self.engine.runAndWait()
        
        # Reset to relaxed arms and watching tablet
        self.pepper.setAngles(["RShoulderPitch", "LShoulderPitch"], [1.5, 1.5], 0.05)
        self.pepper.setAngles("HeadPitch", 0.3, 0.05)

    def check_dashboard(self):
        print("🔗 Pepper Bridge Active. Watching localhost:5009...")
        while True:
            try:
                r = requests.get('http://localhost:5009/get_pepper_status', timeout=0.5)
                if r.status_code == 200 and r.json().get('new_event'):
                    data = r.json()
                    self.speak_and_move(data['text'], data['status'] == 'correct')
            except: pass
            time.sleep(0.4)

    def walk_around(self):
        while True:
            self.pepper.moveTo(0.8, 0.2, 0, _async=True) # Move forward-right
            time.sleep(15)
            self.pepper.moveTo(-0.8, -0.2, 0, _async=True) # Move back
            time.sleep(15)

if __name__ == "__main__":
    bot = PepperInteractiveRobot()
    threading.Thread(target=bot.walk_around, daemon=True).start()
    bot.check_dashboard()
