#!/usr/bin/env python3
import os, threading, time, cv2, json
import pybullet as p
import pybullet_data
from flask import Flask, jsonify
import google.generativeai as genai
from deepface import DeepFace

# --- CONFIGURATION ---
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)

# Shared State
ST = {
    "name": "User", 
    "emotion": "neutral", 
    "status": "Initializing",
    "score": 0,
    "active": True
}

# --- MODULE 1: AI BRAIN ---
class TherapyBrain:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.chat = self.model.start_chat()
    def talk(self, text):
        response = self.chat.send_message(f"Child says: {text}. Respond as a kind robot therapist.")
        return response.text

# --- MODULE 2: VISION ENGINE ---
def vision_loop():
    cap = cv2.VideoCapture(0)
    while ST["active"]:
        ret, frame = cap.read()
        if ret:
            try:
                # Optimized DeepFace call for your GPU
                res = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
                ST["emotion"] = res[0]['dominant_emotion']
            except: pass
            cv2.putText(frame, f"Emotion: {ST['emotion']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Omni-Pepper Vision", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()
    cv2.destroyAllWindows()

# --- MODULE 3: SIMULATION ---
def sim_loop():
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    p.loadURDF("plane.urdf")
    # Load Pepper (Ensure the path to your Pepper URDF is correct)
    # robot = p.loadURDF("pepper.urdf", [0, 0, 0]) 
    ST["status"] = "Simulation Active"
    while ST["active"]:
        p.stepSimulation()
        time.sleep(1./240.)

# --- MODULE 4: DASHBOARD ---
app = Flask(__name__)
@app.route('/status')
def get_status(): return jsonify(ST)

def run_dash():
    app.run(port=5009, host='0.0.0.0', debug=False, use_reloader=False)

# --- EXECUTION ---
if __name__ == "__main__":
    print("🤖 STARTING OMNI-PEPPER ULTIMATE...")
    
    threads = [
        threading.Thread(target=vision_loop),
        threading.Thread(target=sim_loop),
        threading.Thread(target=run_dash)
    ]
    
    for t in threads: t.start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        ST["active"] = False
        print("\nStopping System...")
