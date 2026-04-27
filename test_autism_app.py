#!/usr/bin/env python3
"""اختبار تطبيق التوحد - من PepperForAutism"""
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

questions = [
    "Does the child make eye contact?",
    "Does the child respond to their name?",
    "Does the child play with others?"
]
speak("Autism screening test. Answer yes or no in terminal.")
score = 0
for q in questions:
    speak(q)
    answer = input(f"{q} (yes/no): ").lower()
    if answer == 'yes':
        score += 1
if score >= 2:
    speak("Moderate indicators. Consider professional screening.")
else:
    speak("Low indicators. Continue monitoring.")
print("✅ Test complete")
