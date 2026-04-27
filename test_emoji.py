#!/usr/bin/env python3
"""اختبار تحويل المشاعر لإيموجي - من pepper-emoji"""
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

emojis = {"happy": "😊", "sad": "😢", "angry": "😠", "surprised": "😲"}
speak("Emotion to emoji test!")
for emotion, emoji in emojis.items():
    speak(f"{emotion} {emoji}")
    time.sleep(1)
speak("Test complete!")
print("✅ Test complete")
