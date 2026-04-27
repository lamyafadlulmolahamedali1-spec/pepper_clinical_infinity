import time
import cv2
import numpy as np
from qibullet import SimulationManager

class PepperWithTablet:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        
        # Create the virtual tablet window
        cv2.namedWindow("Pepper's Tablet", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Pepper's Tablet", 400, 300)

    def update_tablet(self, message, color=(255, 255, 255)):
        # Create a colored screen
        img = np.zeros((300, 400, 3), np.uint8)
        img[:] = color # Background color
        cv2.putText(img, message, (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
        cv2.imshow("Pepper's Tablet", img)
        cv2.waitKey(1)

    def therapy_interaction(self):
        # Pepper points to the tablet
        self.update_tablet("Loading Game...")
        self.pepper.setAngles("HeadPitch", 0.3, 0.1) # Pepper looks down at tablet
        time.sleep(2)
        
        self.update_tablet("CHOOSE A COLOR", color=(200, 255, 200))
        print("🤖 Pepper: Ahmed, look at my tablet and pick a color!")
        
        # Keep simulation alive
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    bot = PepperWithTablet()
    bot.therapy_interaction()
