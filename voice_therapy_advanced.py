import time, random, cv2, pyttsx3
import pybullet as p
import speech_recognition as sr
from deepface import DeepFace
from qibullet import SimulationManager

class PepperSuperAI:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 800
        self.cap = cv2.VideoCapture(0)
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        self.setup_scene()

    def setup_scene(self):
        v_table = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.4, 0.6, 0.3], rgbaColor=[0.5, 0.3, 0.1, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_table, basePosition=[1.0, 0, 0.3])
        v_shirt = p.createVisualShape(p.GEOM_CAPSULE, radius=0.15, length=0.3, rgbaColor=[0, 0.4, 0.8, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_shirt, basePosition=[1.6, 0, 0.5])
        v_head = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=[1, 0.8, 0.6, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=v_head, basePosition=[1.6, 0, 0.9])
    def speak(self, text):
        print(f"🤖 Pepper: {text}"); self.engine.say(text); self.engine.runAndWait()

    def run_session(self):
        self.speak("System Active. I can see and hear you now.")
        while True:
            ret, frame = self.cap.read()
            if ret:
                try:
                    res = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                    if res[0]['dominant_emotion'] == "happy":
                        self.pepper.setAngles("RShoulderPitch", -0.5, 0.2)
                except: pass
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"👤 You: {text}")
                    if "play" in text: self.speak("Let's play!")
                    elif "bye" in text: break
                    else: self.speak("I am listening.")
                except: pass
            time.sleep(0.1)

if __name__ == "__main__":
    app = PepperSuperAI()
    app.run_session()
