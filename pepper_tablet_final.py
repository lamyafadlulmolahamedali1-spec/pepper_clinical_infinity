import time
import cv2
import numpy as np
import os
import pyttsx3
import urllib.request
from qibullet import SimulationManager

class PepperTherapyExpert:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        self.engine = pyttsx3.init()
        
        # Tablet Setup
        cv2.namedWindow("Pepper's Tablet", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Pepper's Tablet", 500, 400)
        cv2.moveWindow("Pepper's Tablet", 100, 100)

    def download_image(self, item):
        """Downloads a real photo if it's missing."""
        path = os.path.expanduser(f"~/pepper_duo/src/{item}.jpg")
        if not os.path.exists(path):
            print(f"🌐 Downloading a real photo of a {item}...")
            urls = {
                "cat": "https://p0.pikist.com/download/91/319/604/cat-animal-pet-kitten-cute-feline.jpg",
                "car": "https://p0.pikist.com/download/535/196/1023/car-red-car-vehicle-auto.jpg"
            }
            try:
                urllib.request.urlretrieve(urls.get(item), path)
            except:
                print("Failed to download. Using flashcard instead.")
        return path

    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def show_tablet(self, item_name=None, color=None):
        if item_name:
            path = self.download_image(item_name.lower())
            if os.path.exists(path):
                img = cv2.imread(path)
                img = cv2.resize(img, (500, 400))
            else:
                img = np.zeros((400, 500, 3), np.uint8)
                cv2.putText(img, item_name, (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
        elif color:
            img = np.zeros((400, 500, 3), np.uint8)
            img[:] = color # Fill with BGR color
            
        cv2.imshow("Pepper's Tablet", img)
        cv2.waitKey(500)

    def run_therapy(self, child_name):
        self.pepper.goToPosture("Stand", 0.6)
        
        # Part 1: Real Photo Test
        self.speak(f"Hello {child_name}! Look at my tablet. What animal is this?")
        self.show_tablet(item_name="cat")
        time.sleep(3)
        self.speak("That is right! It is a cat. Meow!")

        # Part 2: Color Test
        self.speak("Now Ahmed, let's play the color game. What color is this?")
        self.show_tablet(color=(0, 0, 255)) # Red in BGR
        time.sleep(3)
        self.speak("Great! That was Red. You are so smart!")
        
        self.show_tablet(color=(0, 255, 0)) # Green in BGR
        self.speak("And what about this one?")
        time.sleep(3)
        self.speak("Yes! It is Green!")

        self.speak("I am very proud of you today.")
        self.pepper.goToPosture("StandZero", 0.5)

if __name__ == "__main__":
    app = PepperTherapyExpert()
    try:
        app.run_therapy("Ahmed")
        print("Session finished. Press Ctrl+C to close.")
        while True: time.sleep(1)
    except KeyboardInterrupt:
        app.sim_manager.stopSimulation(app.client)
        cv2.destroyAllWindows()
