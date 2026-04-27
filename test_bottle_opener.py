#!/usr/bin/env python3
"""اختبار تحكم بالصوت - من Bottle-Opener"""
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

def wave():
    for _ in range(2):
        pepper.setAngles("LShoulderPitch", 1.2, 0.1); time.sleep(0.2)
        pepper.setAngles("LShoulderPitch", 0, 0.1); time.sleep(0.2)

speak("Say 'wave' to make me wave")
recognizer = sr.Recognizer()
mic = sr.Microphone()

try:
    with mic as source:
        print("🎤 Listening...")
        audio = recognizer.listen(source, timeout=5)
    text = recognizer.recognize_google(audio).lower()
    if 'wave' in text:
        wave()
        speak("Waving!")
except:
    speak("Command not recognized")
print("✅ Test complete")
