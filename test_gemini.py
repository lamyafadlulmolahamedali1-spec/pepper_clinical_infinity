#!/usr/bin/env python3
"""اختبار Gemini AI - من Pepper-Gemini-Flash-2.5"""
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

speak("Gemini AI test (requires API key)")
print("Note: This requires a Gemini API key from Google AI Studio")
print("You can get one for free at: https://aistudio.google.com/")
print("Add your key to the code to enable")
print("✅ Test setup complete")
