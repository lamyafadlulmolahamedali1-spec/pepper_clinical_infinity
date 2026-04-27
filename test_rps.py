#!/usr/bin/env python3
"""اختبار لعبة حجر ورقة مقص - من Pepper-Rock-Paper-Scissors"""
import time
import random
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

choices = ["rock", "paper", "scissors"]
speak("Let's play Rock Paper Scissors! Type your choice!")
print("Enter: rock, paper, or scissors")
player = input("You: ").lower()
if player in choices:
    robot = random.choice(choices)
    speak(f"I chose {robot}!")
    if player == robot:
        speak("It's a tie!")
    elif (player == "rock" and robot == "scissors") or \
         (player == "paper" and robot == "rock") or \
         (player == "scissors" and robot == "paper"):
        speak("You win!")
    else:
        speak("I win!")
else:
    speak("Invalid choice!")
print("✅ Test complete")
