import time
import cv2
import numpy as np
import os
import pyttsx3
from qibullet import SimulationManager

class PepperTherapyPro:
    def __init__(self):
        # 1. Start Simulation & Voice
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        self.engine = pyttsx3.init()
        
        # 2. Setup Tablet Window
        cv2.namedWindow("Pepper's Tablet", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Pepper's Tablet", 500, 400)
        # Move it to the side so it doesn't cover PyBullet
        cv2.moveWindow("Pepper's Tablet", 100, 100)

    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def show_on_tablet(self, item_name, color=(255, 255, 255)):
        """Displays an image from disk OR a generated flashcard."""
        img_path = f"~/pepper_duo/src/{item_name.lower()}.jpg"
        full_path = os.path.expanduser(img_path)

        if os.path.exists(full_path):
            img = cv2.imread(full_path)
            img = cv2.resize(img, (500, 400))
        else:
            # Generate a nice Flashcard if no image is found
            img = np.zeros((400, 500, 3), np.uint8)
            img[:] = color
            cv2.putText(img, item_name.upper(), (130, 220), 
                        cv2.FONT_HERSHEY_DUPLEX, 2.5, (0, 0, 0), 4)
            cv2.rectangle(img, (20, 20), (480, 380), (0,0,0), 5) # Border

        cv2.imshow("Pepper's Tablet", img)
        cv2.waitKey(500) # Small delay to ensure it renders

    def run_session(self, child_name):
        # Step 1: Greeting
        self.pepper.goToPosture("Stand", 0.6)
        self.speak(f"Hello {child_name}! Look at my tablet. I have a surprise!")
        
        # Step 2: Show "CAR"
        self.pepper.setAngles("HeadPitch", 0.3, 0.2) # Look at tablet
        self.show_on_tablet("CAR", color=(150, 200, 255)) # Light Blue
        self.speak("Can you see the car? Vroom vroom!")
        time.sleep(2)

        # Step 3: Show "CAT"
        self.show_on_tablet("CAT", color=(200, 255, 200)) # Light Green
        self.speak("And look! A little cat. Meow!")
        time.sleep(2)

        self.speak(f"You are doing a great job, {child_name}!")
        self.pepper.goToPosture("StandZero", 0.5)

if __name__ == "__main__":
    app = PepperTherapyPro()
    try:
        app.run_session("Ahmed")
        print("Session Active. Press Ctrl+C in terminal to exit.")
        while True: time.sleep(1)
    except KeyboardInterrupt:
        app.sim_manager.stopSimulation(app.client)
        cv2.destroyAllWindows()
