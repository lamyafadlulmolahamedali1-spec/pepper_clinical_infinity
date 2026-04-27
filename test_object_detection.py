#!/usr/bin/env python3
"""اختبار كشف أشياء - من Integrated_Robot_Project"""
import time
import cv2
from ultralytics import YOLO
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

model = YOLO('yolov8n.pt')
cap = cv2.VideoCapture(0)
speak("Object detection test. Looking for objects...")
for _ in range(30):
    ret, frame = cap.read()
    if ret:
        results = model(frame, verbose=False)
        objects = []
        for r in results:
            if r.boxes:
                for box in r.boxes:
                    objects.append(model.names[int(box.cls[0])])
        if objects:
            speak(f"I see: {', '.join(set(objects)[:3])}")
            break
    time.sleep(0.1)
cap.release()
cv2.destroyAllWindows()
print("✅ Test complete")
