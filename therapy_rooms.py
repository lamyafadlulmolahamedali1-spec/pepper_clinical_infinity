import cv2
import threading
import time
import random
import os
from datetime import datetime
import pyttsx3

# Load existing libraries
try:
    from deepface import DeepFace
    print("✅ DeepFace Loaded from local computer!")
except:
    print("⚠️ DeepFace not found in local path.")

try:
    import mediapipe as mp
    print("✅ MediaPipe Loaded!")
except:
    print("⚠️ MediaPipe not found.")

class PepperTherapy:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.cap = cv2.VideoCapture(0)
        self.running = True
        print("🤖 Pepper System Initialized...")

    def say(self, text):
        print(f"🔊 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def start_session(self, name, severity):
        self.say(f"Hello {name}! I am ready for our {severity} session.")
        # Simple loop to show the camera works with your local OpenCV
        while self.running:
            ret, frame = self.cap.read()
            if not ret: break
            cv2.putText(frame, f"Session: {name}", (10, 30), 1, 1, (0, 255, 0), 2)
            cv2.imshow("Therapy View", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    child_name = sys.argv[1] if len(sys.argv) > 1 else "Ahmed"
    level = sys.argv[2] if len(sys.argv) > 2 else "moderate"
    
    app = PepperTherapy()
    app.start_session(child_name, level)
