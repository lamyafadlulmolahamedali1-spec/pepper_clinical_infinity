#!/usr/bin/env python3
"""اختبار حركات مع الكلام - من GPT-Pepper"""
import time
from qibullet import SimulationManager
import pybullet as p
import pybullet_data
import pyttsx3

engine = pyttsx3.init()
def speak(text): print(f"🔊 {text}"); engine.say(text); engine.runAndWait()

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)
pepper = sim_manager.spawnPepper(client_id)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")

def speak_with_gesture(text):
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.0, 0.1); time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0, 0.1); time.sleep(0.15)
    speak(text)

speak_with_gesture("Hello! I am Pepper with gestures!")
time.sleep(1)
speak("Test complete!")
print("✅ Test complete")
