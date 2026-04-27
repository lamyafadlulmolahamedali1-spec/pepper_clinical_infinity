#!/usr/bin/env python3
"""اختبار المعلم AI - من pepper-ai-tutor"""
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

lessons = {"math": ["What is 2+2?", "What is 5-3?"]}
speak("AI Tutor test! Let's learn math!")
speak(lessons["math"][0])
time.sleep(2)
speak("The answer is 4! Good job!")
speak("Test complete!")
print("✅ Test complete")
