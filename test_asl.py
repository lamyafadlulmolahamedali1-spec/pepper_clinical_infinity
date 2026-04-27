#!/usr/bin/env python3
"""اختبار لغة الإشارة (ASL) - من مشروع shadow-hand-asl"""
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
p.resetDebugVisualizerCamera(cameraDistance=4, cameraYaw=45, cameraPitch=-30)

def asl_a():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 0.5, 0.1); time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1); time.sleep(0.2)

def asl_b():
    for _ in range(2):
        pepper.setAngles("RShoulderPitch", 0.5, 0.1); time.sleep(0.2)
        pepper.setAngles("RShoulderPitch", 0, 0.1); time.sleep(0.2)

speak("Testing ASL: Letter A")
asl_a()
time.sleep(1)
speak("Letter B")
asl_b()
speak("ASL test complete!")
time.sleep(2)
print("✅ Test complete - Close window to exit")
