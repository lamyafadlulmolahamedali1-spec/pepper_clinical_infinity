#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL - CLEAN VERSION (No Qt)                        ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  ✅ NO Qt - pure OpenCV windows (no threading errors)          ║
║  ✅ Local responses (no API key needed)                        ║
║  ✅ MediaPipe pose + hand tracking                             ║
║  ✅ 3-star mastery system                                      ║
║  ✅ Flask tablet interface                                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import cv2
import time
import threading
import numpy as np
import subprocess
import os
import json
from datetime import datetime

# Audio
import pyttsx3
import speech_recognition as sr

# MediaPipe
import mediapipe as mp

# Flask
from flask import Flask, render_template_string, jsonify, request

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import warnings
warnings.filterwarnings('ignore')

class ClinicalTherapist:
    def __init__(self):
        print("\n" + "="*70)
        print("🤖 PEPPER CLINICAL SYSTEM - CLEAN VERSION")
        print("Commander: Lamya | Omdurman Islamic University")
        print("="*70 + "\n")
        
        # State
        self.child_name = None
        self.current_task = "greeting"
        self.task_mastery = {
            "clap": 0,
            "wave": 0,
            "raise_arms": 0,
            "touch_nose": 0
        }
        self.session_active = True
        self.session_data = []
        
        # Tasks with visual modeling
        self.tasks = {
            "greeting": {
                "name": "Welcome",
                "instruction": "Hello! I'm Pepper. What's your name?",
                "type": "verbal",
                "required": 1
            },
            "clap": {
                "name": "Clap Hands",
                "instruction": "Watch me! 👏 Now you try! Clap 3 times",
                "type": "motor",
                "required": 3,
                "success": "Great clapping! ⭐",
                "visual_model": "🤲     👏     🤲",
                "joint_check": "wrists_distance < 0.1"
            },
            "wave": {
                "name": "Wave Hello",
                "instruction": "Wave your hand like this! 👋 Do it 3 times",
                "type": "motor",
                "required": 3,
                "success": "Wonderful waving! ⭐⭐",
                "visual_model": "👋     🌊     👋",
                "joint_check": "wrist_above_shoulder"
            },
            "raise_arms": {
                "name": "Reach High",
                "instruction": "Raise both arms up! 🙌 Do it 2 times",
                "type": "motor",
                "required": 2,
                "success": "You're so strong! ⭐⭐⭐",
                "visual_model": "🙌     ⬆️     🙌",
                "joint_check": "both_wrists_above_shoulders"
            },
            "touch_nose": {
                "name": "Touch Nose",
                "instruction": "Touch your nose with your finger! 👆 Do it 2 times",
                "type": "motor",
                "required": 2,
                "success": "Perfect! You're amazing! 🎉",
                "visual_model": "👉👃     👆     👉👃",
                "joint_check": "hand_near_face"
            },
            "completion": {
                "name": "Congratulations!",
                "instruction": "You completed all exercises! 🎉",
                "type": "celebration",
                "required": 0
            }
        }
        
        # Movement detection
        self.last_detection = {}
        self.detection_cooldown = 1.2
        
        # Initialize
        self.init_speech()
        self.init_mediapipe()
        self.init_camera()
        self.init_flask()
        
        print("\n✅ All systems ready!")
        print("📱 Tablet: http://localhost:5007")
        print("⌨️  Controls: q=Quit | s=Skip | r=Reset task")
        print("="*70 + "\n")
    
    def init_speech(self):
        """Initialize speech"""
        try:
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 150)
            self.tts.setProperty('volume', 0.9)
            print("✅ Voice ready")
        except:
            self.tts = None
        
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.mic = sr.Microphone()
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Listening ready (energy=300)")
        except:
            self.recognizer = None
    
    def init_mediapipe(self):
        """Initialize MediaPipe"""
        try:
            self.mp_pose = mp.solutions.pose
            self.mp_hands = mp.solutions.hands
            self.mp_face = mp.solutions.face_mesh
            
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.hands = self.mp_hands.Hands(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.face = self.mp_face.FaceMesh(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.mp_drawing = mp.solutions.drawing_utils
            print("✅ MediaPipe ready (pose + hands + face)")
        except Exception as e:
            print(f"⚠️ MediaPipe error: {e}")
            self.pose = None
    
    def init_camera(self):
        """Initialize camera"""
        self.camera = None
        for idx in [0, 1, 2]:
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    self.camera = cap
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"✅ Camera ready (index {idx})")
                    break
                cap.release()
            except:
                continue
        
        if not self.camera:
            print("⚠️ No camera found")
    
    def init_flask(self):
        """Initialize Flask tablet interface"""
        app = Flask(__name__)
        
        @app.route('/')
        def tablet():
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Pepper Clinical System</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        * { margin: 0; padding: 0; box-sizing: border-box; }
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                            min-height: 100vh;
                            padding: 20px;
                        }
                        .container {
                            max-width: 740px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 30px;
                            overflow: hidden;
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        }
                        .header {
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }
                        .header h1 { font-size: 1.8em; margin-bottom: 5px; }
                        .pepper-icon { font-size: 3em; margin: 10px 0; }
                        .task-area {
                            padding: 30px;
                            background: #f8f9fa;
                        }
                        .visual-model {
                            background: #2d3748;
                            color: white;
                            padding: 30px;
                            border-radius: 20px;
                            text-align: center;
                            font-size: 3em;
                            margin: 20px 0;
                            font-family: monospace;
                        }
                        .instruction {
                            font-size: 1.3em;
                            text-align: center;
                            padding: 20px;
                            background: white;
                            border-radius: 15px;
                            margin: 15px 0;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }
                        .stars {
                            text-align: center;
                            font-size: 2em;
                            margin: 15px 0;
                        }
                        .progress-bar {
                            background: #e0e0e0;
                            border-radius: 25px;
                            height: 40px;
                            overflow: hidden;
                            margin: 20px 0;
                        }
                        .progress-fill {
                            background: linear-gradient(90deg, #4caf50, #8bc34a);
                            height: 100%;
                            transition: width 0.5s ease;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                        }
                        .status {
                            text-align: center;
                            padding: 15px;
                            border-radius: 15px;
                            margin: 15px 0;
                            font-weight: bold;
                        }
                        .status.success { background: #4caf50; color: white; }
                        .status.info { background: #2196f3; color: white; }
                        .status.warning { background: #ff9800; color: white; }
                        .joint-data {
                            background: #f5f5f5;
                            padding: 15px;
                            border-radius: 10px;
                            margin: 15px 0;
                            font-size: 0.9em;
                            font-family: monospace;
                        }
                        @keyframes pulse {
                            0%, 100% { transform: scale(1); }
                            50% { transform: scale(1.05); }
                        }
                        .celebration {
                            animation: pulse 0.5s ease-in-out;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="pepper-icon">🤖</div>
                            <h1>Pepper Clinical System</h1>
                            <p>AI-Powered Therapy Assistant</p>
                        </div>
                        <div class="task-area">
                            <div class="visual-model" id="visualModel">🎯</div>
                            <div class="instruction" id="instruction">Loading...</div>
                            <div class="stars" id="stars">⭐️⭐️⭐️</div>
                            <div class="progress-bar">
                                <div class="progress-fill" id="progress" style="width: 0%">0%</div>
                            </div>
                            <div class="status info" id="status">🌟 Ready to begin!</div>
                            <div class="joint-data" id="jointData">Joint angles: waiting...</div>
                        </div>
                    </div>
                    <script>
                        function update() {
                            fetch('/api/status')
                                .then(r => r.json())
                                .then(d => {
                                    document.getElementById('visualModel').innerHTML = d.visual_model || '🎯';
                                    document.getElementById('instruction').innerHTML = d.instruction;
                                    document.getElementById('stars').innerHTML = d.stars;
                                    document.getElementById('progress').style.width = d.progress + '%';
                                    document.getElementById('progress').innerHTML = Math.round(d.progress) + '%';
                                    document.getElementById('status').innerHTML = d.status;
                                    document.getElementById('jointData').innerHTML = d.joint_data;
                                    
                                    if (d.celebration) {
                                        const statusDiv = document.getElementById('status');
                                        statusDiv.classList.add('celebration');
                                        setTimeout(() => statusDiv.classList.remove('celebration'), 500);
                                    }
                                });
                        }
                        update();
                        setInterval(update, 500);
                    </script>
                </body>
                </html>
            ''')
        
        @app.route('/api/status')
        def status():
            total_tasks = 4  # clap, wave, raise_arms, touch_nose
            completed = sum(1 for task in ['clap', 'wave', 'raise_arms', 'touch_nose'] 
                          if self.task_mastery.get(task, 0) >= self.tasks.get(task, {}).get('required', 1))
            progress = (completed / total_tasks) * 100 if total_tasks > 0 else 0
            
            current_required = self.tasks.get(self.current_task, {}).get('required', 1)
            current_progress = self.task_mastery.get(self.current_task, 0)
            
            stars = "⭐" * min(current_progress, 3) + "☆" * (3 - min(current_progress, 3))
            
            return jsonify({
                'visual_model': self.tasks.get(self.current_task, {}).get('visual_model', '🎯'),
                'instruction': self.tasks.get(self.current_task, {}).get('instruction', ''),
                'stars': stars,
                'progress': progress,
                'status': f"{self.task_mastery.get(self.current_task, 0)}/{current_required} completed",
                'celebration': current_progress > 0 and current_progress % current_required == 0,
                'joint_data': f"Task: {self.current_task} | Progress: {current_progress}/{current_required}"
            })
        
        def run_flask():
            app.run(host='0.0.0.0', port=5007, debug=False, use_reloader=False)
        
        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Tablet UI: http://localhost:5007")
    
    def speak(self, text):
        """Speak text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🤖 Pepper: {text}")
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                pass
    
    def listen(self, timeout=5):
        """Listen for speech"""
        if not self.recognizer:
            return None
        
        try:
            with self.mic as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio)
            print(f"🗣️ Heard: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except:
            return None
    
    def detect_movement(self, frame):
        """Detect movements using MediaPipe"""
        if not self.pose or frame is None:
            return None
        
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pose_results = self.pose.process(rgb)
            hands_results = self.hands.process(rgb)
            
            movement = None
            current_time = time.time()
            
            if pose_results.pose_landmarks:
                # Draw pose landmarks
                self.mp_drawing.draw_landmarks(
                    frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                
                lm = pose_results.pose_landmarks.landmark
                
                # Get landmarks
                left_wrist = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
                right_wrist = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                left_shoulder = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                nose = lm[self.mp_pose.PoseLandmark.NOSE]
                
                # Calculate distances
                wrists_dist = np.sqrt((left_wrist.x - right_wrist.x)**2 + 
                                     (left_wrist.y - right_wrist.y)**2)
                
                # Detect clap
                if wrists_dist < 0.08:
                    if current_time - self.last_detection.get('clap', 0) > self.detection_cooldown:
                        self.last_detection['clap'] = current_time
                        movement = "clap"
                
                # Detect wave
                elif (left_wrist.y < left_shoulder.y - 0.15 or 
                      right_wrist.y < right_shoulder.y - 0.15):
                    if current_time - self.last_detection.get('wave', 0) > self.detection_cooldown:
                        self.last_detection['wave'] = current_time
                        movement = "wave"
                
                # Detect arms up
                elif (left_wrist.y < left_shoulder.y - 0.12 and 
                      right_wrist.y < right_shoulder.y - 0.12):
                    if current_time - self.last_detection.get('raise_arms', 0) > self.detection_cooldown:
                        self.last_detection['raise_arms'] = current_time
                        movement = "raise_arms"
                
                # Detect touch nose (hand near face)
                if hands_results.multi_hand_landmarks and not movement:
                    for hand in hands_results.multi_hand_landmarks:
                        wrist = hand.landmark[self.mp_hands.HandLandmark.WRIST]
                        distance_to_nose = np.sqrt((wrist.x - nose.x)**2 + (wrist.y - nose.y)**2)
                        
                        if distance_to_nose < 0.15:
                            if current_time - self.last_detection.get('touch_nose', 0) > self.detection_cooldown:
                                self.last_detection['touch_nose'] = current_time
                                movement = "touch_nose"
                            break
                
                # Draw hand landmarks
                if hands_results.multi_hand_landmarks:
                    for hand in hands_results.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(
                            frame, hand, self.mp_hands.HAND_CONNECTIONS)
            
            return movement
            
        except Exception as e:
            return None
    
    def complete_task(self, movement):
        """Process task completion"""
        if self.current_task in ["greeting", "completion"]:
            return False
        
        if movement == self.current_task:
            current = self.task_mastery.get(self.current_task, 0)
            required = self.tasks[self.current_task].get("required", 1)
            
            if current < required:
                self.task_mastery[self.current_task] = current + 1
                self.session_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'task': self.current_task,
                    'attempt': current + 1,
                    'success': True
                })
                
                remaining = required - (current + 1)
                
                if remaining > 0:
                    self.speak(f"Good! {remaining} more to go!")
                else:
                    # Task mastered
                    self.speak(self.tasks[self.current_task]["success"])
                    return True
        
        return False
    
    def next_task(self):
        """Move to next task"""
        task_order = ["greeting", "clap", "wave", "raise_arms", "touch_nose", "completion"]
        try:
            current_idx = task_order.index(self.current_task)
            
            # Check if current task is mastered
            if self.current_task != "greeting" and self.current_task != "completion":
                required = self.tasks[self.current_task].get("required", 1)
                if self.task_mastery.get(self.current_task, 0) < required:
                    print(f"⚠️ Need to master {self.current_task} first ({self.task_mastery.get(self.current_task, 0)}/{required})")
                    return False
            
            if current_idx + 1 < len(task_order):
                self.current_task = task_order[current_idx + 1]
                if self.current_task != "completion":
                    self.speak(self.tasks[self.current_task]["instruction"])
                    # Show visual model
                    time.sleep(1)
                    self.speak(f"Look at the screen! {self.tasks[self.current_task]['visual_model']}")
                else:
                    total_mastered = sum(1 for task in ['clap', 'wave', 'raise_arms', 'touch_nose'] 
                                       if self.task_mastery.get(task, 0) >= self.tasks.get(task, {}).get('required', 1))
                    self.speak(f"Congratulations! You mastered {total_mastered} out of 4 exercises! {self.tasks[self.current_task]['instruction']}")
                    self.session_active = False
                return True
        except ValueError:
            pass
        return False
    
    def run_greeting(self):
        """Handle greeting and name capture"""
        self.speak("Hello! I'm Pepper. What's your name?")
        
        for attempt in range(3):
            name = self.listen(timeout=5)
            if name and len(name) > 1 and len(name) < 30:
                # Filter out invalid responses
                invalid = ['what', 'your', 'name', 'pepper', 'robot', 'hello', 'hi']
                if name.lower() not in invalid:
                    self.child_name = name.title()
                    self.speak(f"Nice to meet you, {self.child_name}! Let's start our exercises!")
                    self.next_task()
                    return
        
        self.child_name = "Champion"
        self.speak("Okay, I'll call you Champion! Let's begin!")
        self.next_task()
    
    def run(self):
        """Main loop"""
        self.run_greeting()
        
        while self.session_active:
            frame = None
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    # Detect movement
                    movement = self.detect_movement(frame)
                    if movement:
                        if self.complete_task(movement):
                            if not self.next_task():
                                break
                    
                    # Add overlay
                    task_name = self.tasks[self.current_task]["name"]
                    progress = self.task_mastery.get(self.current_task, 0)
                    required = self.tasks[self.current_task].get("required", 1)
                    
                    cv2.putText(frame, f"Task: {task_name}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Progress: {progress}/{required}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    if self.child_name:
                        cv2.putText(frame, f"Child: {self.child_name}", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    cv2.imshow("Pepper Clinical System - Live View", frame)
            
            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("\n👋 Session ended by user")
                break
            elif key == ord('s'):
                print("⏭️ Skipping current task...")
                self.next_task()
            elif key == ord('r'):
                print("🔄 Resetting current task...")
                self.task_mastery[self.current_task] = 0
            
            time.sleep(0.03)
        
        # Cleanup
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        
        # Save session report
        report = {
            'child_name': self.child_name,
            'date': datetime.now().isoformat(),
            'mastery': self.task_mastery,
            'sessions': self.session_data
        }
        
        with open(f"session_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*70)
        print(f"🎉 SESSION COMPLETE - {self.child_name}")
        print("="*70)
        for task, mastered in self.task_mastery.items():
            required = self.tasks.get(task, {}).get('required', 1)
            stars = "⭐" * min(mastered, 3)
            print(f"  {task:12} : {stars} ({mastered}/{required})")
        print("="*70)
        print(f"📄 Report saved: session_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print("🌟 Keep practicing! Stay healthy and happy!")
        print("="*70 + "\n")

if __name__ == "__main__":
    # Kill existing processes
    for port in [5001, 5007, 5009]:
        try:
            subprocess.run(['fuser', '-k', f'{port}/tcp'], stderr=subprocess.DEVNULL, timeout=1)
        except:
            pass
    time.sleep(1)
    
    # Run therapist
    therapist = ClinicalTherapist()
    therapist.run()
