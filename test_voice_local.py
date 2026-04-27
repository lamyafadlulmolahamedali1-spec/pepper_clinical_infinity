#!/usr/bin/env python3
"""اختبار الصوت بدون نت - من robot-simulator-foundrylocal"""
import time
import speech_recognition as sr
import pyttsx3
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

engine = pyttsx3.init()
def speak(text): print(f"🔊 {text}"); engine.say(text); engine.runAndWait()

sim_manager = SimulationManager()
client_id = sim_manager.launchSimulation(gui=True)
pepper = sim_manager.spawnPepper(client_id)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.loadURDF("plane.urdf")
p.resetDebugVisualizerCamera(cameraDistance=4, cameraYaw=45, cameraPitch=-30)

recognizer = sr.Recognizer()
mic = sr.Microphone()

speak("Voice recognition test. Say something!")
try:
    with mic as source:
        print("🎤 Listening...")
        audio = recognizer.listen(source, timeout=5)
    text = recognizer.recognize_google(audio)
    speak(f"You said: {text}")
except:
    speak("Could not hear you")
print("✅ Test complete - Close window to exit")
