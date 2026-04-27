#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PEPPER CLINICAL INTEGRATED - Your Existing Code + New Features ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  ✅ Your original Qt + PyBullet + MediaPipe setup              ║
║  ✅ ADDED: Touch-activated speech recording                    ║
║  ✅ ADDED: Visual drawings for exercises                       ║
║  ✅ ADDED: Kids tap screen → record → imitate drawing          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import cv2
import time
import threading
import numpy as np
import subprocess
import sys
import os
import json
import random
import base64
from datetime import datetime
from collections import defaultdict
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Audio/Speech
import pyttsx3
import speech_recognition as sr

# MediaPipe
import mediapipe as mp

# Flask for tablet
from flask import Flask, render_template_string, jsonify, request

# PyQt for your original UI (keep your existing imports)
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QImage, QPixmap

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# ============================================
# NEW: Visual Exercise Generator
# ============================================
class VisualExerciseGenerator:
    """Generates visual drawings for exercises"""
    
    @staticmethod
    def create_visual_drawing(exercise_type, movement):
        """Create a drawing/silhouette for the exercise"""
        img = Image.new('RGBA', (400, 400), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = 200, 200
        
        # Draw based on movement type
        if movement == 'clap':
            draw.ellipse([center_x-30, center_y-80, center_x+30, center_y-20], outline='black', width=3)
            draw.line([center_x, center_y-20, center_x, center_y+60], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x-30, center_y+100], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x+30, center_y+100], fill='black', width=3)
            draw.line([center_x-40, center_y, center_x-20, center_y+20], fill='black', width=4)
            draw.line([center_x+40, center_y, center_x+20, center_y+20], fill='black', width=4)
            
        elif movement == 'wave':
            draw.ellipse([center_x-30, center_y-80, center_x+30, center_y-20], outline='black', width=3)
            draw.line([center_x, center_y-20, center_x, center_y+60], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x-30, center_y+100], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x+30, center_y+100], fill='black', width=3)
            draw.line([center_x-40, center_y-10, center_x-60, center_y-30], fill='black', width=4)
            draw.line([center_x-60, center_y-30, center_x-55, center_y-40], fill='black', width=3)
            
        elif movement == 'raise_arms':
            draw.ellipse([center_x-30, center_y-80, center_x+30, center_y-20], outline='black', width=3)
            draw.line([center_x, center_y-20, center_x, center_y+60], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x-30, center_y+100], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x+30, center_y+100], fill='black', width=3)
            draw.line([center_x-40, center_y-10, center_x-50, center_y-60], fill='black', width=4)
            draw.line([center_x+40, center_y-10, center_x+50, center_y-60], fill='black', width=4)
            
        else:
            # Generic figure
            draw.ellipse([center_x-30, center_y-80, center_x+30, center_y-20], outline='black', width=3)
            draw.line([center_x, center_y-20, center_x, center_y+60], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x-30, center_y+100], fill='black', width=3)
            draw.line([center_x, center_y+60, center_x+30, center_y+100], fill='black', width=3)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

# ============================================
# NEW: Touch-Activated Speech Recorder
# ============================================
class TouchSpeechRecorder:
    """High-sensitivity touch-to-record speech recognition"""
    
    def __init__(self):
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = None
        self.recognized_text = None
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 200  # High sensitivity
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        try:
            self.mic = sr.Microphone()
            with self.mic as source:
                print("🎤 Calibrating high-sensitivity microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"✅ Touch recorder ready (threshold: {self.recognizer.energy_threshold})")
        except:
            print("⚠️ Microphone not available")
            self.mic = None
    
    def start_recording(self):
        """Start recording with high sensitivity"""
        if not self.mic:
            return
        self.is_recording = True
        self.audio_data = None
        self.recognized_text = None
        
        def record():
            try:
                with self.mic as source:
                    print("🎙️ Recording started (touch mode)...")
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=8)
                    self.audio_data = audio
                    print("🎙️ Recording stopped")
            except Exception as e:
                print(f"Recording error: {e}")
            finally:
                self.is_recording = False
        
        self.recording_thread = threading.Thread(target=record)
        self.recording_thread.start()
    
    def stop_recording_and_recognize(self):
        """Stop recording and recognize speech"""
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2)
        
        if self.audio_data:
            try:
                text = self.recognizer.recognize_google(self.audio_data)
                self.recognized_text = text
                print(f"✅ Recognized: {text}")
                return text
            except sr.UnknownValueError:
                print("❌ Could not understand")
                return None
            except Exception as e:
                print(f"❌ Recognition error: {e}")
                return None
        return None

# ============================================
# YOUR ORIGINAL PEPPER CLASS (MODIFIED)
# ============================================
class PepperClinicalIntegrated:
    def __init__(self):
        print("\n" + "="*80)
        print("🤖 PEPPER CLINICAL INTEGRATED - WITH VISUAL EXERCISES")
        print("Commander: Lamya | Omdurman Islamic University")
        print("="*80 + "\n")
        
        # Keep ALL your original state variables
        self.child_name = None
        self.current_task = "greeting"
        self.task_progress = {"clap": 0, "wave": 0, "raise_arms": 0}
        self.session_active = True
        
        # NEW: Visual exercises
        self.visual_exercises = self.generate_visual_exercises()
        self.current_visual_index = 0
        self.current_repetition = 0
        
        # NEW: Touch recorder
        self.touch_recorder = TouchSpeechRecorder()
        
        # Your original tasks
        self.tasks = {
            "greeting": {
                "name": "Welcome",
                "instruction": "Hello! I'm Pepper. What's your name?",
                "type": "verbal"
            },
            "clap": {
                "name": "Clap Hands",
                "instruction": "Watch the drawing and CLAP your hands! 👏",
                "type": "motor",
                "required": 3,
                "movement": "clap"
            },
            "wave": {
                "name": "Wave Hello",
                "instruction": "Watch the drawing and WAVE your hand! 👋",
                "type": "motor",
                "required": 3,
                "movement": "wave"
            },
            "raise_arms": {
                "name": "Raise Arms",
                "instruction": "Watch the drawing and RAISE both arms! 🙌",
                "type": "motor",
                "required": 3,
                "movement": "raise_arms"
            },
            "completion": {
                "name": "Congratulations!",
                "instruction": "You completed all exercises! 🎉",
                "type": "celebration"
            }
        }
        
        # Movement detection (your original)
        self.last_detection = {}
        self.detection_cooldown = 1.2
        
        # Initialize ALL your original systems
        self.init_speech()
        self.init_mediapipe()
        self.init_camera()
        self.init_flask_integrated()  # MODIFIED: Now includes touch UI
        self.init_qt()  # Keep your Qt setup
        
        print("\n✅ ALL SYSTEMS INTEGRATED!")
        print("📱 Tablet (with touch recording): http://localhost:5007")
        print("🎨 Visual drawings for every exercise")
        print("👆 Kids tap button to speak")
        print("="*80 + "\n")
    
    def generate_visual_exercises(self):
        """Generate visual drawings for exercises"""
        exercises = []
        movements = ['clap', 'wave', 'raise_arms']
        
        for movement in movements:
            visual_drawing = VisualExerciseGenerator.create_visual_drawing('motor', movement)
            exercises.append({
                'movement': movement,
                'visual_drawing': visual_drawing
            })
        return exercises
    
    # ============================================
    # YOUR ORIGINAL INIT METHODS (KEEP AS IS)
    # ============================================
    def init_speech(self):
        """Initialize speech - YOUR ORIGINAL CODE"""
        try:
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 150)
            self.tts.setProperty('volume', 0.9)
            print("✅ TTS ready")
        except:
            self.tts = None
        
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.mic = sr.Microphone()
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Speech recognition ready")
        except:
            self.recognizer = None
    
    def init_mediapipe(self):
        """Initialize MediaPipe - YOUR ORIGINAL CODE"""
        try:
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.mp_drawing = mp.solutions.drawing_utils
            print("✅ MediaPipe ready")
        except:
            self.pose = None
    
    def init_camera(self):
        """Initialize camera - YOUR ORIGINAL CODE"""
        self.camera = None
        for idx in [0, 1, 2]:
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    self.camera = cap
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    print(f"✅ Camera ready")
                    break
                cap.release()
            except:
                continue
    
    def init_qt(self):
        """Initialize Qt - YOUR ORIGINAL CODE"""
        try:
            self.app = QApplication.instance()
            if not self.app:
                self.app = QApplication(sys.argv)
            print("✅ Qt ready")
        except:
            print("⚠️ Qt not available")
    
    # ============================================
    # MODIFIED: Flask with Touch Recording UI
    # ============================================
    def init_flask_integrated(self):
        """Initialize Flask with touch recording UI"""
        app = Flask(__name__)
        
        @app.route('/')
        def tablet():
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Pepper Clinical - Touch to Speak</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
                    <style>
                        * { margin: 0; padding: 0; box-sizing: border-box; }
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                            min-height: 100vh;
                            padding: 20px;
                            touch-action: manipulation;
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
                        .stats {
                            display: flex;
                            justify-content: space-around;
                            padding: 15px;
                            background: #f8f9fa;
                            flex-wrap: wrap;
                        }
                        .stat-card {
                            text-align: center;
                            padding: 10px;
                        }
                        .stat-value {
                            font-size: 1.5em;
                            font-weight: bold;
                            color: #667eea;
                        }
                        .visual-area {
                            padding: 30px;
                            text-align: center;
                        }
                        .drawing-canvas {
                            background: #f0f0f0;
                            border-radius: 20px;
                            padding: 20px;
                            margin: 20px 0;
                            min-height: 300px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }
                        .drawing-canvas img {
                            max-width: 100%;
                            height: auto;
                            border-radius: 10px;
                        }
                        .instruction {
                            font-size: 1.2em;
                            text-align: center;
                            padding: 15px;
                            background: #e3f2fd;
                            border-radius: 15px;
                            margin: 15px 0;
                        }
                        .record-button {
                            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
                            border: none;
                            color: white;
                            padding: 25px;
                            border-radius: 60px;
                            font-size: 1.5em;
                            cursor: pointer;
                            width: 100%;
                            margin: 15px 0;
                            transition: all 0.3s ease;
                            touch-action: manipulation;
                            user-select: none;
                        }
                        .record-button:active {
                            transform: scale(0.95);
                        }
                        .record-button.recording {
                            background: linear-gradient(135deg, #ff4757, #ff6b81);
                            animation: pulse 0.5s infinite;
                        }
                        .feedback {
                            text-align: center;
                            padding: 15px;
                            border-radius: 15px;
                            margin: 10px 0;
                            font-weight: bold;
                        }
                        .feedback.success {
                            background: #4caf50;
                            color: white;
                        }
                        .progress-bar {
                            background: #e0e0e0;
                            border-radius: 25px;
                            height: 30px;
                            overflow: hidden;
                            margin: 15px 0;
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
                        @keyframes pulse {
                            0%, 100% { transform: scale(1); }
                            50% { transform: scale(1.02); }
                        }
                        .badge {
                            display: inline-block;
                            padding: 5px 15px;
                            border-radius: 20px;
                            font-size: 0.9em;
                            margin: 5px;
                            background: #ff9800;
                            color: white;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🤖 Pepper Clinical</h1>
                            <p>👆 Touch & Hold to Speak • 🎨 Watch & Imitate</p>
                        </div>
                        <div class="stats">
                            <div class="stat-card"><div class="stat-value" id="score">0</div><div>⭐ Score</div></div>
                            <div class="stat-card"><div class="stat-value" id="streak">0</div><div>🔥 Streak</div></div>
                            <div class="stat-card"><div class="stat-value" id="progress">0%</div><div>✅ Progress</div></div>
                        </div>
                        <div class="visual-area">
                            <div class="drawing-canvas">
                                <img id="visualDrawing" src="" alt="Exercise visual">
                            </div>
                            <div class="instruction" id="instruction">Loading...</div>
                            <div class="progress-bar">
                                <div class="progress-fill" id="progressFill" style="width: 0%">0%</div>
                            </div>
                            <button class="record-button" id="recordBtn">
                                🎤 TAP & HOLD TO SPEAK
                            </button>
                            <div class="feedback" id="feedback"></div>
                            <div id="badge"></div>
                        </div>
                    </div>
                    
                    <script>
                        let isRecording = false;
                        const recordBtn = document.getElementById('recordBtn');
                        const feedback = document.getElementById('feedback');
                        
                        function startRecording() {
                            if (isRecording) return;
                            isRecording = true;
                            recordBtn.classList.add('recording');
                            recordBtn.innerHTML = '🎙️ RECORDING... RELEASE TO STOP';
                            feedback.innerHTML = '🔴 Recording... Speak clearly!';
                            fetch('/api/start_recording', { method: 'POST' });
                        }
                        
                        function stopRecording() {
                            if (!isRecording) return;
                            isRecording = false;
                            recordBtn.classList.remove('recording');
                            recordBtn.innerHTML = '🎤 TAP & HOLD TO SPEAK';
                            feedback.innerHTML = '⏳ Processing...';
                            
                            fetch('/api/stop_recording', { method: 'POST' })
                                .then(r => r.json())
                                .then(data => {
                                    if (data.text) {
                                        feedback.innerHTML = '✅ Heard: "' + data.text + '"';
                                        feedback.className = 'feedback success';
                                        setTimeout(() => {
                                            feedback.innerHTML = '';
                                            feedback.className = 'feedback';
                                        }, 2000);
                                    } else if (data.error) {
                                        feedback.innerHTML = '❌ ' + data.error;
                                        setTimeout(() => {
                                            if (feedback.innerHTML.includes('❌')) feedback.innerHTML = '';
                                        }, 2000);
                                    }
                                });
                        }
                        
                        recordBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); });
                        recordBtn.addEventListener('touchend', (e) => { e.preventDefault(); stopRecording(); });
                        recordBtn.addEventListener('mousedown', startRecording);
                        recordBtn.addEventListener('mouseup', stopRecording);
                        
                        function updateUI() {
                            fetch('/api/status')
                                .then(r => r.json())
                                .then(d => {
                                    document.getElementById('visualDrawing').src = d.visual_drawing;
                                    document.getElementById('instruction').innerHTML = d.instruction;
                                    document.getElementById('score').innerHTML = d.score;
                                    document.getElementById('streak').innerHTML = d.streak;
                                    document.getElementById('progress').innerHTML = d.progress + '%';
                                    document.getElementById('progressFill').style.width = d.progress + '%';
                                    document.getElementById('progressFill').innerHTML = Math.round(d.progress) + '%';
                                    document.getElementById('badge').innerHTML = `<span class="badge">🎯 ${d.repetitions}/${d.total_repetitions}</span>`;
                                });
                        }
                        updateUI();
                        setInterval(updateUI, 500);
                    </script>
                </body>
                </html>
            ''')
        
        @app.route('/api/start_recording', methods=['POST'])
        def start_recording():
            self.touch_recorder.start_recording()
            return jsonify({'status': 'recording'})
        
        @app.route('/api/stop_recording', methods=['POST'])
        def stop_recording():
            text = self.touch_recorder.stop_recording_and_recognize()
            if text:
                self.process_touch_speech(text)
                return jsonify({'text': text})
            return jsonify({'error': 'Could not understand. Try again!'})
        
        @app.route('/api/status')
        def status():
            # Get current visual drawing
            visual_drawing = ""
            current_repetition = 0
            total_repetitions = 1
            
            for ex in self.visual_exercises:
                if ex['movement'] == self.current_task:
                    visual_drawing = ex['visual_drawing']
                    total_repetitions = self.tasks.get(self.current_task, {}).get('required', 1)
                    current_repetition = self.task_progress.get(self.current_task, 0)
                    break
            
            total_tasks = 3
            completed = sum(1 for task in ['clap', 'wave', 'raise_arms'] 
                          if self.task_progress.get(task, 0) >= self.tasks.get(task, {}).get('required', 1))
            progress = (completed / total_tasks) * 100 if total_tasks > 0 else 0
            
            return jsonify({
                'visual_drawing': visual_drawing,
                'instruction': self.tasks.get(self.current_task, {}).get('instruction', ''),
                'score': sum(self.task_progress.values()) * 10,
                'streak': 0,
                'progress': progress,
                'repetitions': current_repetition,
                'total_repetitions': total_repetitions
            })
        
        def run_flask():
            app.run(host='0.0.0.0', port=5007, debug=False, use_reloader=False)
        
        threading.Thread(target=run_flask, daemon=True).start()
        print("✅ Tablet with touch recording: http://localhost:5007")
    
    # ============================================
    # NEW: Process touch speech
    # ============================================
    def process_touch_speech(self, text):
        """Process speech from touch recording"""
        print(f"📝 Touch speech received: {text}")
        
        if self.current_task == "greeting":
            if text and len(text) > 1:
                self.child_name = text.title()
                self.speak(f"Nice to meet you, {self.child_name}! Let's begin!")
                self.next_task()
    
    # ============================================
    # YOUR ORIGINAL METHODS (KEEP AS IS)
    # ============================================
    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                pass
    
    def detect_movement(self, frame):
        """Your original movement detection"""
        if not self.pose or self.current_task not in ['clap', 'wave', 'raise_arms']:
            return None
        
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)
            
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                lm = results.pose_landmarks.landmark
                current_time = time.time()
                
                if self.current_task == 'clap':
                    left_wrist = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                    dist = np.sqrt((left_wrist.x - right_wrist.x)**2 + (left_wrist.y - right_wrist.y)**2)
                    if dist < 0.08 and current_time - self.last_detection.get('clap', 0) > self.detection_cooldown:
                        self.last_detection['clap'] = current_time
                        return 'clap'
                
                elif self.current_task == 'wave':
                    left_shoulder = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    left_wrist = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                    if (left_wrist.y < left_shoulder.y - 0.15 or right_wrist.y < right_shoulder.y - 0.15):
                        if current_time - self.last_detection.get('wave', 0) > self.detection_cooldown:
                            self.last_detection['wave'] = current_time
                            return 'wave'
                
                elif self.current_task == 'raise_arms':
                    left_shoulder = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    left_wrist = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
                    if (left_wrist.y < left_shoulder.y - 0.12 and right_wrist.y < right_shoulder.y - 0.12):
                        if current_time - self.last_detection.get('raise_arms', 0) > self.detection_cooldown:
                            self.last_detection['raise_arms'] = current_time
                            return 'raise_arms'
            
            return None
        except:
            return None
    
    def complete_task(self, movement):
        """Your original task completion"""
        if self.current_task in ["greeting", "completion"]:
            return False
        
        if movement == self.current_task:
            current = self.task_progress.get(self.current_task, 0)
            required = self.tasks[self.current_task].get("required", 1)
            
            if current < required:
                self.task_progress[self.current_task] = current + 1
                remaining = required - (current + 1)
                
                if remaining > 0:
                    self.speak(f"Good! {remaining} more to go!")
                else:
                    self.speak(self.tasks[self.current_task]["instruction"].replace("Watch the drawing and ", "") + " Great job! 🌟")
                    return True
        return False
    
    def next_task(self):
        """Your original next task"""
        task_order = ["greeting", "clap", "wave", "raise_arms", "completion"]
        try:
            current_idx = task_order.index(self.current_task)
            if current_idx + 1 < len(task_order):
                self.current_task = task_order[current_idx + 1]
                if self.current_task != "completion":
                    self.speak(self.tasks[self.current_task]["instruction"])
                else:
                    self.speak("Congratulations! You completed all exercises! 🎉")
                    self.session_active = False
                return True
        except:
            pass
        return False
    
    def run_greeting(self):
        """Your original greeting - now uses touch recording"""
        self.speak("Hello! I'm Pepper. What's your name?")
        self.speak("Tap the big button on the tablet and say your name!")
        
        # Wait for name via touch recording (handled by Flask callbacks)
        timeout = 30
        start_time = time.time()
        while not self.child_name and time.time() - start_time < timeout:
            time.sleep(1)
        
        if not self.child_name:
            self.child_name = "Friend"
            self.speak("Okay, I'll call you Friend! Let's begin!")
            self.next_task()
    
    def run(self):
        """Your original main loop"""
        # Start greeting in a separate thread to allow Flask to handle touch
        greeting_thread = threading.Thread(target=self.run_greeting)
        greeting_thread.start()
        
        # Main loop
        while self.session_active:
            frame = None
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    movement = self.detect_movement(frame)
                    if movement:
                        if self.complete_task(movement):
                            if not self.next_task():
                                break
                    
                    # Add overlay
                    cv2.putText(frame, f"Task: {self.tasks.get(self.current_task, {}).get('name', '')}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Progress: {self.task_progress.get(self.current_task, 0)}/{self.tasks.get(self.current_task, {}).get('required', 1)}", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    cv2.imshow("Pepper Clinical - Watch & Imitate", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord('s'):
                self.next_task()
            
            time.sleep(0.03)
        
        # Cleanup
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        print(f"\n🎉 Great job, {self.child_name}! Session complete!")

# ============================================
# MAIN ENTRY POINT
# ============================================
if __name__ == "__main__":
    # Kill existing processes
    for port in [5001, 5007, 5009]:
        try:
            subprocess.run(['fuser', '-k', f'{port}/tcp'], stderr=subprocess.DEVNULL, timeout=1)
        except:
            pass
    time.sleep(1)
    
    # Install Pillow if needed
    try:
        from PIL import Image
    except:
        subprocess.run(['pip', 'install', 'Pillow', '-q'], stderr=subprocess.DEVNULL)
    
    # Run integrated therapist
    therapist = PepperClinicalIntegrated()
    therapist.run()
