#!/usr/bin/env python3
"""اختبار ChatGPT - من pepperchat"""
import time
import requests
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

speak("ChatGPT test. Say something in the terminal!")
user = input("You: ")
speak(f"You said: {user}")
print("✅ Test complete")
