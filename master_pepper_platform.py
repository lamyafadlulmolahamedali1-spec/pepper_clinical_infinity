import os
import time
import cv2
import threading
import multiprocessing
import pybullet as p
import pybullet_data
from deepface import DeepFace
import shared_state

# --- CONFIGURATION & ENV SETUP ---
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '' # Keep GPU free for PyBullet

PEPPER_URDF = "/home/lamya/pepper_duo/src/permanent_libs/qibullet/robot_data/pepper.urdf"

# --- VISION PROCESS (THE EYES) ---
def vision_submodule():
    print("🎭 Vision: Initializing DeepFace on Camera 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0) # Fallback to 0
        
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        try:
            # Analyze 9 emotions
            results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, detector_backend='opencv', silent=True)
            if results:
                raw = results[0]['emotion']
                # Derive Anxiety and Confusion
                raw['confusion'] = (raw['neutral'] * 0.4) + (raw['surprise'] * 0.6)
                raw['anxiety'] = (raw['fear'] * 0.7) + (raw['sad'] * 0.3)
                dom = max(raw, key=raw.get)
                
                # Write to shared nervous system
                shared_state.set_emotion(dom, raw[dom]/100, raw)
                
                # Overlay for the Live Monitor
                cv2.putText(frame, f"Empathy Engine: {dom.upper()}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        except: pass

        cv2.imshow("Therapist Monitor - Child's Emotions", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

# --- SIMULATION & THERAPY PROCESS (THE BRAIN & BODY) ---
def therapy_submodule():
    print("🚀 Simulation: Building Therapy Room...")
    physicsClient = p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    p.setGravity(0, 0, -9.81)
    
    try:
        pepper_id = p.loadURDF(PEPPER_URDF, [0, 0, 0], useFixedBase=True)
        print("✅ Pepper Avatar Loaded.")
    except:
        print("⚠️ URDF Path Error. Using Proxy.")
        pepper_id = p.loadURDF("sphere_small.urdf", [0, 0, 0.5])

    last_emotion = "neutral"
    
    responses = {
        "happy": "Your happiness makes me happy! High five!",
        "sad": "I am here for you. Want to tell me what is wrong?",
        "anxiety": "I feel you might be anxious. Let's do a calm breathing exercise.",
        "confusion": "It is okay to be confused. I can explain that again.",
        "angry": "It is okay to be frustrated. Let's count to ten.",
        "neutral": "I am ready to learn with you."
    }

    print("🏁 LIVE SESSION ACTIVE")
    while True:
        # Read from shared nervous system
        state = shared_state.get_emotion()
        current_emo = state['emotion']
        
        if current_emo != last_emotion and state['confidence'] > 0.4:
            msg = responses.get(current_emo, "I am observing your feelings.")
            print(f"\n[THERAPY LOG] Pepper detected: {current_emo.upper()}")
            print(f"🔊 Pepper says: {msg}")
            
            # Simple Animation: Move head/arms based on emotion
            if current_emo == "happy":
                p.setJointMotorControl2(pepper_id, 1, p.POSITION_CONTROL, targetPosition=0.2)
            elif current_emo == "sad":
                p.setJointMotorControl2(pepper_id, 1, p.POSITION_CONTROL, targetPosition=-0.2)
                
            last_emotion = current_emo
            
        p.stepSimulation()
        time.sleep(0.1)

# --- MAIN RUNNER ---
if __name__ == "__main__":
    # Create the two parallel worlds
    vision_p = multiprocessing.Process(target=vision_submodule)
    therapy_p = multiprocessing.Process(target=therapy_submodule)
    
    # Launch them
    vision_p.start()
    therapy_p.start()
    
    try:
        vision_p.join()
        therapy_p.join()
    except KeyboardInterrupt:
        print("\nShutting down Platform...")
        vision_p.terminate()
        therapy_p.terminate()
