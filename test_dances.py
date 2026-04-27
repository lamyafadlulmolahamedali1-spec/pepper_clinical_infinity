#!/usr/bin/env python3
"""اختبار الرقصات - من naoqi-robot-dance"""
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

def gangnam():
    for _ in range(4):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1); time.sleep(0.15)
        pepper.setAngles("LShoulderPitch", 0.2, 0.1); time.sleep(0.15)
        pepper.setAngles("RShoulderPitch", 1.2, 0.1); time.sleep(0.15)
        pepper.setAngles("RShoulderPitch", 0.2, 0.1); time.sleep(0.15)

def robot():
    for _ in range(3):
        for angle in [0.5, 1.0, 0.5, 0]:
            pepper.setAngles("LShoulderPitch", angle, 0.1)
            pepper.setAngles("RShoulderPitch", angle, 0.1)
            time.sleep(0.15)

speak("Testing Gangnam Style dance!")
gangnam()
speak("Testing Robot dance!")
robot()
speak("Dance test complete!")
print("✅ Test complete")
