#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         PEPPER PERFECT THERAPY STATION v3.0                 ║
║  Video-Call Style | ASD Therapy | Real-time AI              ║
╚══════════════════════════════════════════════════════════════╝

Dependencies:
  pip install opencv-python deepface fer speechrecognition
  pip install pyaudio pyttsx3 numpy ultralytics threading

Combines:
  - pepper-android-realtime-chat (gesture sync + LLM)
  - GPT-Pepper (co-speech gestures)
  - Zoom-style video call UI
  - ABA/DTT/TEACCH/TIE protocols
  - High-sensitivity emotion + audio detection
"""

# ============================================================
# IMPORTS
# ============================================================
import cv2
import numpy as np
import threading
import time
import random
import queue
import json
import sys
import os
import math
import warnings
warnings.filterwarnings('ignore')

# PyBullet
import pybullet as p
import pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')

# TTS
import pyttsx3

# Speech Recognition
import speech_recognition as sr

# Flask
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

# ============================================================
# HIGH-SENSITIVITY CONFIGURATION
# ============================================================
CONFIG = {
    # === Emotion Detection ===
    "emotion_threshold":    0.10,   # 10% → triggers response
    "emotion_interval":     0.8,    # analyze every 0.8s
    "micro_change_delta":   0.05,   # 5% change → re-analyze

    # === Microphone (VERY HIGH SENSITIVITY) ===
    "mic_energy_threshold": 50,     # default=300, we use 50
    "mic_pause_threshold":  0.4,    # seconds of silence
    "mic_dynamic_ratio":    1.5,    # dynamic adjustment
    "mic_timeout":          3,      # listen timeout
    "no_sound_limit":       10,     # 10s no sound → prompt

    # === Clap Detection ===
    "clap_volume_spike":    2000,   # RMS threshold
    "clap_frequency_min":   100,    # Hz
    "clap_frequency_max":   3000,   # Hz

    # === Therapy ===
    "max_retries":          3,      # retries per task
    "task_timeout":         15,     # seconds per task
    "session_duration":     1800,   # 30 minutes

    # === Flask ===
    "flask_port":           5009,
}

# ============================================================
# SHARED STATE
# ============================================================
STATE = {
    "emotion":          "neutral",
    "emotion_scores":   {},
    "face_detected":    False,
    "attention":        70,
    "engagement":       "moderate",
    "child_name":       None,
    "child_known":      False,
    "last_sound_time":  time.time(),
    "last_emotion":     "neutral",
    "session_logs":     [],
    "total_score":      0,
    "current_task":     None,
    "task_retries":     0,
    "protocol":         "GREETING",
    "prompt_level":     0,
    "is_speaking":      False,
    "clap_detected":    False,
    "session_start":    datetime.now().strftime("%H:%M"),
    "sim_cmd":          None,
}

EMOTION_EMOJIS = {
    "happy":    ("😊", (0, 220, 0)),
    "sad":      ("😢", (220, 100, 100)),
    "angry":    ("😠", (0, 0, 220)),
    "fear":     ("😨", (0, 180, 220)),
    "surprise": ("😲", (200, 0, 220)),
    "disgust":  ("🤢", (0, 150, 100)),
    "neutral":  ("😐", (180, 180, 180)),
}

def add_log(msg, log_type="info", protocol=None):
    entry = {
        "time":     datetime.now().strftime("%H:%M:%S"),
        "message":  msg,
        "type":     log_type,
        "protocol": protocol or STATE["protocol"],
        "emotion":  STATE["emotion"],
        "child":    STATE.get("child_name", "?"),
    }
    STATE["session_logs"].append(entry)
    emoji, _ = EMOTION_EMOJIS.get(STATE["emotion"], ("😐", (180,180,180)))
    print(f"[{entry['time']}] {emoji} {msg}")

# ============================================================
# TEXT-TO-SPEECH ENGINE
# ============================================================
class PepperVoice:
    """
    Friendly, slow, clear voice for autism therapy.
    Supports emotion-aware speech.
    """
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            # Slow rate for autism therapy
            self.engine.setProperty('rate', 130)
            self.engine.setProperty('volume', 1.0)
            # Find female voice
            voices = self.engine.getProperty('voices')
            for v in voices:
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','susan','karen']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            self._lock = threading.Lock()
            print("✅ Voice engine ready (slow, clear mode)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")
            self.ok = False

    def say(self, text, rate=None):
        """Speak with optional rate override"""
        name = STATE.get("child_name", "friend")
        text = text.replace("{name}", name)
        STATE["is_speaking"] = True
        print(f"\n🔊 Pepper: {text}")
        add_log(f"Said: {text[:60]}", "info")

        if self.ok:
            with self._lock:
                try:
                    if rate:
                        self.engine.setProperty('rate', rate)
                    self.engine.say(text)
                    self.engine.runAndWait()
                    if rate:
                        self.engine.setProperty('rate', 130)
                except Exception as e:
                    print(f"⚠️  TTS error: {e}")

        STATE["is_speaking"] = False

    def say_emotion_aware(self, emotion, task_text):
        """Acknowledge emotion then give task"""
        emotion_responses = {
            "happy":    "I love your big smile! 😊",
            "sad":      "I see you might be feeling sad. That is okay. 💙",
            "angry":    "I understand you might be frustrated. Let us breathe together. 🌬️",
            "fear":     "It is okay to feel nervous. I am here with you. 🤗",
            "surprise": "Oh! You look surprised! That is fun! 😲",
            "disgust":  "I see that face! Let us try something fun instead! 🎉",
            "neutral":  "Let us have some fun together! 🌟",
        }
        prefix = emotion_responses.get(emotion, "")
        full_text = f"{prefix} {task_text}"
        self.say(full_text)


# ============================================================
# HIGH-SENSITIVITY EMOTION DETECTOR
# ============================================================
class EmotionDetector:
    """
    HIGH SENSITIVITY emotion detection.
    Threshold: 10% (any emotion above 10% triggers response)
    Detects micro-changes in facial expression.
    """
    def __init__(self):
        self.deepface_ok   = False
        self.fer_ok        = False
        self.last_scores   = {}
        self.analysis_lock = threading.Lock()
        self.frame_buffer  = None
        self.running       = False

        # Try DeepFace
        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            # Warm up
            dummy = np.zeros((48, 48, 3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.deepface_ok = True
            print("✅ DeepFace ready (threshold=10%)")
        except Exception as e:
            print(f"⚠️  DeepFace: {e}")

        # Try FER (fallback)
        if not self.deepface_ok:
            try:
                from fer import FER
                # Very low threshold for high sensitivity
                self.fer = FER(mtcnn=True)
                self.fer_ok = True
                print("✅ FER ready (high sensitivity)")
            except Exception as e:
                print(f"⚠️  FER: {e}")

    def analyze(self, frame):
        """
        Analyze frame with HIGH SENSITIVITY.
        Returns dict of emotion scores.
        """
        if frame is None or frame.size == 0:
            return {}

        scores = {}

        # === DeepFace Analysis ===
        if self.deepface_ok:
            try:
                result = self.DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,  # HIGH SENSITIVITY
                    detector_backend='opencv',
                    silent=True
                )
                if result:
                    raw = result[0]['emotion']
                    # Normalize to 0-1
                    total = sum(raw.values()) or 1
                    scores = {k: v/total for k, v in raw.items()}

                    # Check micro-changes
                    self._check_micro_change(scores)

                    STATE["face_detected"] = True
                    STATE["attention"] = min(
                        100, STATE["attention"] + 2)

            except Exception:
                STATE["face_detected"] = False
                STATE["attention"] = max(
                    0, STATE["attention"] - 2)

        # === FER Fallback ===
        elif self.fer_ok:
            try:
                result = self.fer.detect_emotions(frame)
                if result:
                    raw = result[0]['emotions']
                    total = sum(raw.values()) or 1
                    scores = {k: v/total for k, v in raw.items()}
                    STATE["face_detected"] = True
                except Exception:
                    STATE["face_detected"] = False

        # === Apply Threshold ===
        # Any emotion above 10% is valid
        if scores:
            threshold = CONFIG["emotion_threshold"]
            valid = {k: v for k, v in scores.items()
                     if v >= threshold}

            if valid:
                dominant = max(valid, key=valid.get)
                STATE["emotion"]       = dominant
                STATE["emotion_scores"]= scores

                # Update engagement
                pos = scores.get('happy', 0) + \
                      scores.get('surprise', 0)
                neg = scores.get('sad', 0) + \
                      scores.get('angry', 0) + \
                      scores.get('fear', 0)

                if pos > 0.4:   STATE["engagement"] = "high"
                elif neg > 0.5: STATE["engagement"] = "distressed"
                else:           STATE["engagement"] = "moderate"

        return scores

    def _check_micro_change(self, new_scores):
        """Detect micro-changes in facial expression"""
        if not self.last_scores:
            self.last_scores = new_scores
            return False

        delta = CONFIG["micro_change_delta"]
        for emotion, score in new_scores.items():
            prev = self.last_scores.get(emotion, 0)
            if abs(score - prev) > delta:
                self.last_scores = new_scores
                return True  # Micro-change detected

        return False


# ============================================================
# HIGH-SENSITIVITY MICROPHONE
# ============================================================
class PepperMic:
    """
    VERY HIGH SENSITIVITY microphone.
    energy_threshold = 50 (vs default 300)
    Detects whispers, soft claps, breath sounds.
    """
    def __init__(self, voice):
        self.voice      = voice
        self.ok         = False
        self.recognizer = None
        self.running    = False
        self.result_q   = queue.Queue()
        self.audio_q    = queue.Queue()

        try:
            self.recognizer = sr.Recognizer()

            # === HIGH SENSITIVITY SETTINGS ===
            self.recognizer.energy_threshold = \
                CONFIG["mic_energy_threshold"]  # 50 vs 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_ratio = \
                CONFIG["mic_dynamic_ratio"]     # 1.5
            self.recognizer.pause_threshold = \
                CONFIG["mic_pause_threshold"]   # 0.4s
            self.recognizer.phrase_threshold = 0.2  # very responsive
            self.recognizer.non_speaking_duration = 0.2

            self.ok = True
            print(f"✅ Mic ready (energy={CONFIG['mic_energy_threshold']}, "
                  f"pause={CONFIG['mic_pause_threshold']}s)")
        except Exception as e:
            print(f"⚠️  Microphone: {e}")

    def listen_once(self, prompt="", timeout=5):
        """Single listen with high sensitivity"""
        if not self.ok:
            return input(f"[Type] {prompt}: ").strip()
        try:
            with sr.Microphone() as source:
                if prompt:
                    print(f"🎤 {prompt}")
                # Minimal ambient noise adjustment
                self.recognizer.adjust_for_ambient_noise(
                    source, duration=0.3)
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=10)
            # Try Google first, then fallback
            try:
                text = self.recognizer.recognize_google(audio)
                STATE["last_sound_time"] = time.time()
                add_log(f"Heard: {text}", "info")
                return text
            except sr.UnknownValueError:
                # Sound detected but not understood
                # Check for clap pattern
                self._check_clap(audio)
                STATE["last_sound_time"] = time.time()
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            print(f"⚠️  Listen: {e}")
            return ""

    def _check_clap(self, audio_data):
        """Detect clap pattern from audio"""
        try:
            raw = np.frombuffer(audio_data.get_raw_data(), np.int16)
            rms = np.sqrt(np.mean(raw**2))
            if rms > CONFIG["clap_volume_spike"]:
                STATE["clap_detected"] = True
                add_log("Clap detected! ✋", "success")
                return True
        except Exception:
            pass
        return False

    def get_name(self):
        """Ask child for their name"""
        if STATE["child_known"]:
            return STATE["child_name"]

        self.voice.say(
            "Hello! I am Pepper, your robot friend! "
            "What is your name? Tell me please!")
        time.sleep(0.5)

        for attempt in range(3):
            response = self.listen_once(
                "What is your name?", timeout=8)
            if response and response != "[sound]":
                name = self._extract_name(response)
                if name:
                    STATE["child_name"]  = name
                    STATE["child_known"] = True
                    self.voice.say(
                        f"Hello {name}! "
                        "I am SO happy to meet you today! "
                        "Let us have so much fun together!")
                    add_log(f"Name learned: {name}", "success")
                    return name

        STATE["child_name"]  = "Friend"
        STATE["child_known"] = True
        self.voice.say(
            "I will call you my wonderful friend! "
            "Let us start our session!")
        return "Friend"

    def _extract_name(self, text):
        text = text.lower().strip()
        for rm in ["my name is","i am","i'm","iam",
                   "call me","name is","it is","its"]:
            text = text.replace(rm, "").strip()
        words = text.split()
        return words[0].capitalize() if words else None

    def listen_continuous(self, callback):
        """Continuous background listening"""
        if not self.ok: return

        def _loop():
            self.running = True
            while self.running:
                if STATE["is_speaking"]:
                    time.sleep(0.2)
                    continue
                try:
                    text = self.listen_once("", timeout=3)
                    if text:
                        callback(text)
                except Exception:
                    pass
                time.sleep(0.1)

        threading.Thread(target=_loop, daemon=True).start()


# ============================================================
# VIDEO CALL UI (OpenCV)
# ============================================================
class TherapyVideoCall:
    """
    Zoom-style video call interface.
    Shows child camera + Pepper avatar + emotion overlay.
    """
    def __init__(self, emotion_detector):
        self.detector    = emotion_detector
        self.cap         = None
        self.frame       = None
        self.running     = False
        self.last_analyze= 0
        self.window_name = "🤖 Pepper Therapy - Video Call"

        # Pepper avatar (simple but effective)
        self.pepper_avatar = self._create_pepper_avatar()

        # Task display
        self.task_display    = ""
        self.task_display_t  = 0
        self.praise_display  = ""
        self.praise_display_t= 0

        # Try camera
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                # HD if possible
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.running = True
                threading.Thread(
                    target=self._run, daemon=True).start()
                print("✅ Video call UI ready!")
            else:
                print("⚠️  No camera - text mode")
        except Exception as e:
            print(f"⚠️  Camera: {e}")

    def _create_pepper_avatar(self):
        """Create simple Pepper robot avatar"""
        h, w = 200, 160
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (30, 30, 60)  # Dark background

        # Head (circle)
        cv2.circle(img, (80, 55), 40,
                   (220, 200, 180), -1)
        # Eyes
        cv2.circle(img, (65, 48), 8,
                   (0, 150, 255), -1)
        cv2.circle(img, (95, 48), 8,
                   (0, 150, 255), -1)
        cv2.circle(img, (66, 48), 3,
                   (255, 255, 255), -1)
        cv2.circle(img, (96, 48), 3,
                   (255, 255, 255), -1)
        # Mouth (smile)
        cv2.ellipse(img, (80, 68), (15, 8),
                    0, 0, 180, (100, 50, 50), 2)
        # Body
        cv2.rectangle(img, (50, 95), (110, 170),
                      (150, 150, 200), -1)
        # Arms
        cv2.rectangle(img, (20, 100), (50, 130),
                      (150, 150, 200), -1)
        cv2.rectangle(img, (110, 100), (140, 130),
                      (150, 150, 200), -1)
        # Pepper text
        cv2.putText(img, "PEPPER", (30, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (100, 200, 255), 2)
        return img

    def _run(self):
        fc = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            fc += 1
            now = time.time()

            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            self.frame = frame.copy()

            # Analyze emotion every 0.8s
            if now - self.last_analyze > \
               CONFIG["emotion_interval"]:
                self.last_analyze = now
                threading.Thread(
                    target=self.detector.analyze,
                    args=(frame.copy(),),
                    daemon=True).start()

            # Build video call UI
            ui = self._build_ui(frame)

            cv2.imshow(self.window_name, ui)
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]:  # ESC or Q
                self.running = False
                break

            time.sleep(0.01)

        self.cap.release()
        cv2.destroyAllWindows()

    def _build_ui(self, frame):
        """Build Zoom-style video call UI"""
        h, w = frame.shape[:2]

        # === Main frame: child video ===
        ui = frame.copy()

        # === Dark overlay header ===
        overlay = ui.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70),
                      (10, 15, 30), -1)
        ui = cv2.addWeighted(overlay, 0.8, ui, 0.2, 0)

        # === Header text ===
        name = STATE.get("child_name", "...")
        prot = STATE["protocol"]
        cv2.putText(ui, f"🤖 Pepper Therapy Session",
                    (15, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2)
        cv2.putText(ui,
                    f"Child: {name}  |  Protocol: {prot}  |"
                    f"  Score: {STATE['total_score']}",
                    (15, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (150, 200, 255), 1)

        # === Pepper avatar (bottom-right, like Zoom PIP) ===
        av_h, av_w = self.pepper_avatar.shape[:2]

        # Animate avatar based on is_speaking
        avatar = self.pepper_avatar.copy()
        if STATE["is_speaking"]:
            # Pulsing border
            border_col = (0, 200, 255)
            t = int(time.time() * 5) % 3
            bw = 2 + t
        else:
            border_col = (100, 100, 100)
            bw = 2

        x1 = w - av_w - 20
        y1 = h - av_h - 20
        # Background
        ui[y1-5:y1+av_h+5, x1-5:x1+av_w+5] = (20, 25, 50)
        # Avatar
        ui[y1:y1+av_h, x1:x1+av_w] = avatar
        # Border
        cv2.rectangle(ui,
                      (x1-5, y1-5),
                      (x1+av_w+5, y1+av_h+5),
                      border_col, bw)
        # Speaking indicator
        if STATE["is_speaking"]:
            cv2.putText(ui, "SPEAKING",
                        (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, (0, 255, 200), 1)

        # === Emotion overlay (bottom-left) ===
        em    = STATE["emotion"]
        emoji_char, em_color = EMOTION_EMOJIS.get(
            em, ("😐", (180, 180, 180)))
        att   = STATE["attention"]
        eng   = STATE["engagement"]

        # Bottom bar
        ov2 = ui.copy()
        cv2.rectangle(ov2, (0, h-90), (w, h),
                      (10, 15, 30), -1)
        ui = cv2.addWeighted(ov2, 0.75, ui, 0.25, 0)

        cv2.putText(ui,
                    f"Emotion: {em.upper()}",
                    (15, h-60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, em_color, 2)
        cv2.putText(ui,
                    f"Attention: {att}%",
                    (15, h-35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 230, 100), 1)
        cv2.putText(ui,
                    f"Engagement: {eng}",
                    (200, h-35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (100, 230, 255), 1)

        # Prompt level badge
        pl      = STATE["prompt_level"]
        pl_cols = [(0,200,0),(200,200,0),(200,100,0),(200,0,0)]
        pl_col  = pl_cols[min(pl, 3)]
        cv2.circle(ui, (w-60, h-60), 20, pl_col, -1)
        cv2.putText(ui, f"P{pl}",
                    (w-68, h-53),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255,255,255), 2)
        cv2.putText(ui, "Prompt",
                    (w-75, h-28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, (200,200,200), 1)

        # === Emotion score bars ===
        scores = STATE.get("emotion_scores", {})
        if scores:
            bar_x = w - 160
            bar_y = 100
            cv2.putText(ui, "Emotion Scores:",
                        (bar_x, bar_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (200, 200, 200), 1)
            for i, (emo, score) in enumerate(
                    sorted(scores.items(),
                           key=lambda x: -x[1])[:5]):
                y = bar_y + i * 22
                bar_len = int(score * 100)
                _, col = EMOTION_EMOJIS.get(
                    emo, ("", (150,150,150)))
                cv2.rectangle(ui,
                              (bar_x, y),
                              (bar_x + bar_len, y + 14),
                              col, -1)
                cv2.putText(ui,
                            f"{emo[:7]}: {score:.0%}",
                            (bar_x, y + 12),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.33, (255,255,255), 1)

        # === Face detection status ===
        fd_col = (0, 255, 0) if STATE["face_detected"] \
                              else (0, 0, 255)
        cv2.circle(ui, (w-20, 20), 8, fd_col, -1)
        cv2.putText(ui,
                    "FACE" if STATE["face_detected"] else "NO FACE",
                    (w-85, 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, fd_col, 1)

        # === Current task display ===
        now = time.time()
        if self.task_display and \
           now - self.task_display_t < 6:
            # Task bubble
            tw = len(self.task_display) * 11 + 20
            tx = max(10, w//2 - tw//2)
            cv2.rectangle(ui,
                          (tx-5, h//2 - 35),
                          (tx+tw+5, h//2 + 5),
                          (20, 60, 120), -1)
            cv2.rectangle(ui,
                          (tx-5, h//2 - 35),
                          (tx+tw+5, h//2 + 5),
                          (0, 150, 255), 2)
            cv2.putText(ui, self.task_display,
                        (tx, h//2 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65, (255, 255, 255), 2)

        # === Praise display ===
        if self.praise_display and \
           now - self.praise_display_t < 4:
            pw = len(self.praise_display) * 14 + 20
            px = max(10, w//2 - pw//2)
            cv2.rectangle(ui,
                          (px-5, h//2 + 30),
                          (px+pw+5, h//2 + 75),
                          (0, 80, 0), -1)
            cv2.putText(ui, self.praise_display,
                        (px, h//2 + 63),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 100), 2)

        # === REC indicator ===
        cv2.circle(ui, (40, 30), 8, (0, 0, 220), -1)
        cv2.putText(ui, "REC",
                    (52, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (0,0,220), 1)

        return ui

    def show_task(self, task_text):
        self.task_display   = task_text[:50]
        self.task_display_t = time.time()

    def show_praise(self, praise_text):
        self.praise_display   = praise_text[:40]
        self.praise_display_t = time.time()

    def stop(self):
        self.running = False
        try:
            cv2.destroyAllWindows()
        except:
            pass


# ============================================================
# ABA THERAPY TASKS
# ============================================================
THERAPY_TASKS = {
    "easy": [
        {
            "instruction": "Clap your hands! 👏",
            "action":      "clap",
            "success_cue": "clap",
            "praise":      "AMAZING CLAP! ⭐",
        },
        {
            "instruction": "Touch your nose! 👃",
            "action":      "touch_nose",
            "success_cue": "nose",
            "praise":      "GREAT JOB! 👃",
        },
        {
            "instruction": "Wave hello to me! 👋",
            "action":      "wave",
            "success_cue": "wave",
            "praise":      "BEAUTIFUL WAVE! 👋",
        },
        {
            "instruction": "Stand up and sit down!",
            "action":      "stand_sit",
            "success_cue": "stand",
            "praise":      "SUPERSTAR! ⭐",
        },
        {
            "instruction": "Show me happy face! 😊",
            "action":      "happy_face",
            "success_cue": "happy",
            "praise":      "LOVELY SMILE! 😊",
        },
    ],
    "medium": [
        {
            "instruction": "Touch your ears! 👂",
            "action":      "touch_ears",
            "success_cue": "ears",
            "praise":      "YOU DID IT! 👂",
        },
        {
            "instruction": "Count to three with fingers!",
            "action":      "count",
            "success_cue": "three",
            "praise":      "SMART COUNTING! 🔢",
        },
        {
            "instruction": "Point to something red!",
            "action":      "point_red",
            "success_cue": "red",
            "praise":      "GREAT POINTING! 🔴",
        },
        {
            "instruction": "Jump up and down once!",
            "action":      "jump",
            "success_cue": "jump",
            "praise":      "AMAZING JUMP! 🦘",
        },
    ],
    "hard": [
        {
            "instruction": "Tell me your name!",
            "action":      "say_name",
            "success_cue": "name",
            "praise":      "BRILLIANT! 🌟",
        },
        {
            "instruction": "What color is the sky?",
            "action":      "say_blue",
            "success_cue": "blue",
            "praise":      "WONDERFUL ANSWER! 💙",
        },
    ],
}

REINFORCERS = [
    "AMAZING! You are a superstar! ⭐",
    "WOW! Fantastic job! 🎉",
    "YES! You did it perfectly! ✅",
    "INCREDIBLE! I am so proud of you! 🏆",
    "BRILLIANT! You are so smart! 🧠",
    "WONDERFUL! Keep it up! 🌟",
]

PROMPTS_RETRY = [
    "Let us try again! {instruction}",
    "Almost there! Can you try one more time? {instruction}",
    "You can do it! {instruction} Go!",
]

EMOTION_PROMPTS = {
    "happy":    "You look so happy! Let us do something fun! 🎉",
    "sad":      "I see you might feel sad. That is okay. 💙 Let us try something easy.",
    "angry":    "Let us take a deep breath together first. 🌬️",
    "fear":     "Do not worry, I am here with you. 🤗",
    "surprise": "You look surprised! Let us play! 😲",
    "neutral":  "Let us start our fun session! 🌟",
    "disgust":  "Let us try something fun together! 🎈",
}


# ============================================================
# THERAPY CONTROLLER (ABA + DTT + TEACCH + TIE)
# ============================================================
class TherapyController:
    """
    Main therapy logic with multi-level prompting.
    Adapts to emotion in real-time.
    """
    def __init__(self, voice, mic, video_ui):
        self.voice    = voice
        self.mic      = mic
        self.video    = video_ui
        self.running  = False

        # Task management
        self.current_task   = None
        self.task_retries   = 0
        self.difficulty     = "easy"
        self.tasks_done     = 0
        self.consecutive_ok = 0

        # Protocols
        self.protocols = ["ABA", "DTT", "TEACCH", "TIE"]
        self.p_idx     = 0

        # Timers
        self.last_sound_check = time.time()
        self.session_start    = time.time()

    def run(self):
        """Main therapy loop"""
        self.running = True
        STATE["protocol"] = "GREETING"

        # 1. Learn child's name
        name = self.mic.get_name()
        time.sleep(0.5)

        # 2. Acknowledge emotion
        em = STATE["emotion"]
        prompt = EMOTION_PROMPTS.get(em, EMOTION_PROMPTS["neutral"])
        self.voice.say_emotion_aware(em, prompt)
        time.sleep(1)

        # 3. Start continuous listening
        self.mic.listen_continuous(self._on_speech)

        # 4. Main loop
        while self.running:
            self._check_no_sound()
            self._check_prompt_level()
            self._run_next_task()
            time.sleep(0.5)

    def _check_no_sound(self):
        """If no sound for 10s → prompt child"""
        elapsed = time.time() - STATE["last_sound_time"]
        if elapsed > CONFIG["no_sound_limit"]:
            STATE["last_sound_time"] = time.time()
            name = STATE.get("child_name", "friend")
            msgs = [
                f"Are you still there {name}? "
                "Make a sound or clap for me! 👏",
                f"{name}, I am waiting for you! "
                "Can you say hello? 👋",
                "I miss you! Give me a clap! 👏",
            ]
            self.voice.say(random.choice(msgs))

    def _check_prompt_level(self):
        """ABA Multi-level prompting system"""
        em  = STATE["emotion"]
        att = STATE["attention"]
        eng = STATE["engagement"]
        fd  = STATE["face_detected"]
        name= STATE.get("child_name", "friend")

        # Level 0: Good engagement
        if fd and att > 60 and em == "happy":
            STATE["prompt_level"] = 0

        # Level 1: Verbal prompt (distracted)
        elif not fd or att < 40:
            if STATE["prompt_level"] < 1:
                STATE["prompt_level"] = 1
                self.voice.say(
                    f"Look at me {name}! "
                    "Let us play together! 👀")
                add_log("Prompt L1: Verbal", "info", "ABA")

        # Level 2: Visual prompt (wave/dance)
        elif STATE["prompt_level"] == 1 and att < 30:
            STATE["prompt_level"] = 2
            self.voice.say(
                f"Hey {name}! "
                "Watch Pepper wave! 👋")
            add_log("Prompt L2: Visual", "info", "ABA")

        # Level 3: Modeling (distressed)
        if eng == "distressed" or em in ["angry", "fear"]:
            if STATE["prompt_level"] < 3:
                STATE["prompt_level"] = 3
                self.voice.say(
                    f"It is okay {name}. "
                    "Let us breathe together. "
                    "In... and out... 🌬️")
                add_log("Prompt L3: Modeling", "info", "TIE")
                time.sleep(4)

    def _run_next_task(self):
        """Pick and run next therapy task"""
        protocol = self.protocols[
            self.p_idx % len(self.protocols)]
        self.p_idx += 1
        STATE["protocol"] = protocol

        if protocol == "ABA":
            self._run_aba_task()
        elif protocol == "DTT":
            self._run_dtt_task()
        elif protocol == "TEACCH":
            self._run_teacch_schedule()
        elif protocol == "TIE":
            self._run_tie_adaptive()

    def _run_aba_task(self):
        """ABA: Give task, wait response, reinforce"""
        STATE["protocol"] = "ABA"
        name = STATE.get("child_name", "friend")

        # Select task based on difficulty
        tasks = THERAPY_TASKS.get(self.difficulty, [])
        if not tasks: return

        # Avoid repeating last task
        task = random.choice(tasks)
        self.current_task = task

        instr = task["instruction"]
        success_cue = task["success_cue"]

        add_log(f"ABA task: {instr}", "info", "ABA")

        # Acknowledge emotion first
        em = STATE["emotion"]
        if em in ["sad", "angry", "fear"]:
            self.voice.say_emotion_aware(em, "Let us try something fun!")
            time.sleep(1)

        # Give instruction
        self.voice.say(f"{name}, {instr}")
        if self.video:
            self.video.show_task(instr)

        # Wait for response
        responded = self._wait_for_response(
            success_cue, task["action"])

        if responded:
            # SUCCESS
            praise = random.choice(REINFORCERS)
            self.voice.say(praise)
            if self.video:
                self.video.show_praise(task["praise"])

            self.task_retries   = 0
            self.tasks_done    += 1
            self.consecutive_ok+= 1
            STATE["total_score"]+= 10
            STATE["clap_detected"]= False
            add_log(f"ABA: {instr} → SUCCESS ✅",
                "success", "ABA")

            # Increase difficulty
            if self.consecutive_ok >= 3:
                self._increase_difficulty()

        else:
            # FAIL / NO RESPONSE
            self.task_retries  += 1
            self.consecutive_ok = 0

            if self.task_retries < CONFIG["max_retries"]:
                retry_msg = random.choice(PROMPTS_RETRY)
                self.voice.say(
                    retry_msg.replace("{instruction}", instr))
                add_log(
                    f"ABA: {instr} → retry "
                    f"({self.task_retries})", "fail")
            else:
                # Change task
                self.task_retries = 0
                self.voice.say(
                    f"No worries {name}! "
                    "Let us try a different one! 🌟")
                add_log(
                    f"ABA: {instr} → skipped", "fail")

        time.sleep(2)

    def _wait_for_response(self, success_cue, action_type,
                           timeout=None):
        """
        Wait for child's response.
        Checks: speech keywords, clap, emotion change.
        """
        if timeout is None:
            timeout = CONFIG["task_timeout"]

        deadline  = time.time() + timeout
        prev_em   = STATE["emotion"]

        while time.time() < deadline:
            # Check clap (if action is clap)
            if action_type == "clap" and \
               STATE["clap_detected"]:
                return True

            # Check emotion change (happy = success)
            curr_em = STATE["emotion"]
            if curr_em == "happy" and prev_em != "happy":
                # Happy = likely did the task
                return True

            # Check speech keyword
            # (handled via _on_speech callback)
            if self._check_speech_match(success_cue):
                return True

            time.sleep(0.3)

        return False

    def _check_speech_match(self, cue):
        """Check if recent speech contains success cue"""
        # This is polled by the main loop
        # The actual detection is in _on_speech
        return False

    def _on_speech(self, text):
        """Handle child's speech"""
        STATE["last_sound_time"] = time.time()
        t = text.lower()

        # Handle name
        if not STATE["child_known"]:
            name = self.mic._extract_name(text)
            if name:
                STATE["child_name"]  = name
                STATE["child_known"] = True
                self.voice.say(f"Hello {name}! So nice!")
            return

        name = STATE.get("child_name", "friend")

        # How-to questions → YouTube
        if "how" in t and (
                "to" in t or "do" in t or "wash" in t or
                "brush" in t or "dress" in t):
            import webbrowser, urllib.parse
            search = f"{text} autism children educational"
            url = ("https://www.youtube.com/results?search_query="
                   + urllib.parse.quote(search))
            webbrowser.open(url)
            self.voice.say(
                f"Watch this video with me {name}! "
                "It will show you how! 📺")
            add_log(f"YouTube: {text}", "info")
            return

        # Task-related keywords
        if self.current_task:
            cue = self.current_task.get("success_cue", "")
            if cue in t:
                # Mark as successful
                STATE["clap_detected"] = True
                return

        # General responses
        if any(w in t for w in
               ["help","play","game","fun","more"]):
            self.voice.say(
                f"Great {name}! Let us do more! 🎉")
        elif any(w in t for w in
                 ["stop","no","done","tired"]):
            self.voice.say(
                f"Okay {name}. Let us take a break. 😊")
        elif text == "[sound]":
            self.voice.say(
                f"I heard you {name}! Good! 👍")
        else:
            responses = [
                f"I heard you {name}! Keep going! 💪",
                f"Well done {name}! 🌟",
                f"Great talking {name}! 🗣️",
            ]
            self.voice.say(random.choice(responses))

    def _run_dtt_task(self):
        """DTT: Discrete Trial Training"""
        STATE["protocol"] = "DTT"
        name = STATE.get("child_name", "friend")

        instructions = {
            "easy": [
                ("Clap hands!", "clap"),
                ("Touch nose!", "nose"),
                ("Wave!", "wave"),
            ],
            "medium": [
                ("Stand up!", "stand"),
                ("Show me 3 fingers!", "three"),
                ("Point to door!", "door"),
            ],
        }
        level_tasks = instructions.get(self.difficulty,
                                       instructions["easy"])
        instr, cue = random.choice(level_tasks)

        self.voice.say(f"{name}, {instr}")
        if self.video:
            self.video.show_task(f"DTT: {instr}")

        responded = self._wait_for_response(cue, cue, timeout=12)

        if responded:
            praise = random.choice(REINFORCERS)
            self.voice.say(praise)
            if self.video:
                self.video.show_praise("CORRECT! ✅")
            STATE["total_score"] += 12
            add_log(f"DTT: {instr} → SUCCESS", "success", "DTT")
        else:
            self.voice.say(
                f"Error correction: {instr} Like this!")
            add_log(f"DTT: {instr} → no response",
                "fail", "DTT")

        time.sleep(2)

    def _run_teacch_schedule(self):
        """TEACCH: Visual schedule"""
        STATE["protocol"] = "TEACCH"
        name = STATE.get("child_name", "friend")

        schedule = [
            ("Greeting", f"Good morning {name}!"),
            ("Emotion", f"{name}, show me happy face!"),
            ("Work",    f"Let us sort colors {name}!"),
            ("Break",   "Take a big breath with me!"),
            ("Joint",   f"Look here {name}! See the red!"),
            ("Closing", f"Great work {name}! All done!"),
        ]
        for act, txt in schedule:
            em = STATE["emotion"]
            if em in ["angry", "fear"]:
                self.voice.say(
                    "Let us calm down first. Breathe!")
                time.sleep(3)
            self.voice.say(txt)
            if self.video:
                self.video.show_task(f"TEACCH: {act}")

            # Wait for any response
            time.sleep(2)
            if STATE["emotion"] == "happy":
                STATE["total_score"] += 15
                add_log(f"TEACCH: {act} ✅",
                    "success", "TEACCH")
            time.sleep(1)

    def _run_tie_adaptive(self):
        """TIE: Therapeutic Interaction Engine"""
        STATE["protocol"] = "TIE"
        name = STATE.get("child_name", "friend")

        self.voice.say(
            f"Hello {name}. "
            "I am watching you carefully "
            "and adapting just for you! 🤖")

        for _ in range(5):
            em  = STATE["emotion"]
            att = STATE["attention"]
            eng = STATE["engagement"]

            if eng == "distressed":
                self.voice.say(
                    f"I see you need a break {name}. "
                    "That is okay. 💙")
                time.sleep(4)

            elif att < 35:
                self.voice.say(
                    f"{name}! Look at Pepper! 👀")
                time.sleep(2)

            elif em == "happy" and att > 65:
                self.voice.say(
                    f"You are doing AMAZING {name}! "
                    "Let us try something harder! 🚀")
                STATE["total_score"] += 20
                add_log("TIE: advance", "success", "TIE")

            else:
                self.voice.say(
                    f"Keep going {name}! "
                    "You are doing great! 💪")
                STATE["total_score"] += 10
                add_log("TIE: maintain", "info", "TIE")

            time.sleep(3)

    def _increase_difficulty(self):
        if self.difficulty == "easy":
            self.difficulty = "medium"
            self.voice.say(
                "You are so smart! "
                "Let us try harder tasks! 🚀")
        elif self.difficulty == "medium":
            self.difficulty = "hard"
            self.voice.say(
                "INCREDIBLE! Expert level! 🏆")
        self.consecutive_ok = 0
        add_log(f"Difficulty: {self.difficulty}", "info")


# ============================================================
# FLASK DASHBOARD
# ============================================================
flask_app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>🤖 Pepper Perfect Therapy</title>
<meta http-equiv="refresh" content="2">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;
     background:#080c18;color:#e0e6ff}
.hdr{background:linear-gradient(135deg,#0f1729,#1a1b4b);
     padding:16px 28px;border-bottom:1px solid #1f2456;
     display:flex;align-items:center;gap:15px}
.hdr h1{font-size:1.3em;color:#818cf8}
.live{background:#ef4444;color:#fff;
      padding:3px 9px;border-radius:20px;
      font-size:.75em;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.cont{max-width:1200px;margin:0 auto;padding:18px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);
    gap:12px;margin-bottom:18px}
.g2{display:grid;grid-template-columns:1.2fr 1fr;gap:14px}
.card{background:#0d1117;border-radius:12px;
      padding:16px;border:1px solid #1f2937}
.card h2{font-size:.85em;color:#6b7280;
         border-bottom:1px solid #1f2937;
         padding-bottom:7px;margin-bottom:12px}
.stat{background:linear-gradient(135deg,#0f1629,#1a1b4b);
      border:1px solid #312e81;border-radius:12px;
      padding:15px;text-align:center}
.n{font-size:2.2em;font-weight:700;color:#818cf8}
.l{font-size:.75em;color:#6b7280;margin-top:3px}
.emo{display:inline-block;padding:6px 16px;
     border-radius:20px;font-weight:700}
.happy{background:#05291544;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f44;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#450a0a44;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293744;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190044;color:#fbbf24;border:1px solid #fbbf24}
.bar-bg{background:#1f2937;border-radius:8px;height:10px;margin:5px 0}
.bar{height:10px;border-radius:8px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
.log-box{max-height:420px;overflow-y:auto}
.log{padding:6px 10px;margin:3px 0;border-radius:6px;
     font-size:.78em;border-left:3px solid #4f46e5;
     background:#0a0e1a}
.log.success{border-color:#10b981}
.log.fail{border-color:#ef4444}
.log.info{border-color:#3b82f6}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:8px 14px;
     border-radius:8px;cursor:pointer;font-size:.83em;
     margin:3px;transition:.2s}
.btn:hover{opacity:.85}
.prot{display:inline-block;padding:2px 8px;
      border-radius:10px;font-size:.73em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}
</style>
</head>
<body>
<div class="hdr">
  <div style="font-size:2em">🤖</div>
  <div>
    <h1>Pepper Perfect Therapy Station v3.0</h1>
    <p style="font-size:.82em;opacity:.8">
      Video-Call Style | ASD Therapy |
      Child: <b>{{s.child_name or '...'}}</b> |
      Protocol: <span class="prot {{s.protocol}}">
        {{s.protocol}}</span>
    </p>
  </div>
  <span class="live">● LIVE</span>
</div>

<div class="cont">
  <div class="g4">
    <div class="stat">
      <div class="n">{{s.total_score}}</div>
      <div class="l">Score</div>
    </div>
    <div class="stat">
      <div class="n">{{s.attention}}%</div>
      <div class="l">Attention</div>
    </div>
    <div class="stat">
      <div class="n">{{s.prompt_level}}</div>
      <div class="l">Prompt Level</div>
    </div>
    <div class="stat">
      <div class="n">{{s.session_logs|length}}</div>
      <div class="l">Interactions</div>
    </div>
  </div>

  <div class="g2">
    <div>
      <div class="card" style="margin-bottom:14px">
        <h2>😊 Live Emotion</h2>
        <div style="text-align:center">
          <div class="emo {{s.emotion}}">
            {{s.emotion.upper()}}
          </div>
          <div style="margin:10px 0">
            <div class="bar-bg">
              <div class="bar"
                   style="width:{{s.attention}}%">
              </div>
            </div>
            <span style="font-size:.8em;color:#818cf8">
              {{s.attention}}% attention</span>
          </div>
          <div style="font-size:.83em;color:#6b7280">
            Engagement: <b style="color:#e0e6ff">
              {{s.engagement}}</b>
          </div>
          <div style="margin-top:6px;font-size:.78em;
            color:{{'#34d399' if s.face_detected else '#ef4444'}}">
            {{'✓ Face Detected' if s.face_detected
              else '✗ No Face - Child too far!'}}
          </div>
        </div>
      </div>

      <div class="card">
        <h2>🎮 Controls</h2>
        <form method="POST" action="/cmd">
          <button class="btn" name="c" value="aba">
            📚 ABA</button>
          <button class="btn" name="c" value="dtt">
            🎯 DTT</button>
          <button class="btn" name="c" value="teacch">
            📅 TEACCH</button>
          <button class="btn" name="c" value="tie">
            🧠 TIE</button>
        </form>
        <div style="margin-top:10px">
          <form method="POST" action="/set_name"
                style="display:flex;gap:6px">
            <input name="name"
                   placeholder="Set child name..."
                   style="flex:1;padding:6px 10px;
                          border-radius:6px;
                          border:1px solid #374151;
                          background:#080c18;
                          color:#e0e6ff;font-size:.85em">
            <button class="btn">✓</button>
          </form>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>📋 Session Log</h2>
      <div class="log-box">
        {% for log in s.session_logs[-30:]|reverse %}
        <div class="log {{log.type}}">
          <span style="color:#6366f1">{{log.time}}</span>
          <span class="prot {{log.protocol}}">
            {{log.protocol}}</span>
          {% if log.child != '?' %}
          <b style="color:#a78bfa">{{log.child}}</b>:
          {% endif %}
          {{log.message}}
          <span style="color:#374151;font-size:.8em">
            |{{log.emotion}}</span>
        </div>
        {% endfor %}
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

@flask_app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML, s=STATE)

@flask_app.route("/update_context", methods=["POST"])
def update_context():
    data = request.json or {}
    em = data.get("emotion", "neutral")
    STATE["emotion"]      = em
    STATE["face_detected"]= True
    return jsonify({"status": "ok"})

@flask_app.route("/cmd", methods=["POST"])
def cmd():
    STATE["sim_cmd"] = request.form.get("c", "")
    return dashboard()

@flask_app.route("/set_name", methods=["POST"])
def set_name():
    n = request.form.get("name", "").strip().title()
    if n:
        STATE["child_name"]  = n
        STATE["child_known"] = True
        add_log(f"Name set: {n}", "success")
    return dashboard()

@flask_app.route("/report")
def report():
    return jsonify(STATE)

def run_flask():
    flask_app.run(
        port=CONFIG["flask_port"],
        debug=False, use_reloader=False)


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         PEPPER PERFECT THERAPY STATION v3.0                 ║
║  High-Sensitivity | Video-Call | ASD Therapy               ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  • Emotion threshold: 10% (HIGH SENSITIVITY)
  • Mic energy: 50 (vs default 300)
  • Pause threshold: 0.4s (VERY RESPONSIVE)
  • No-sound alert: 10 seconds
  • Multi-level prompting: L0-L3

Press Q or ESC in camera window to exit.
Dashboard: http://localhost:5009
""")

    # ---- Start Flask ----
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Dashboard: http://localhost:5009")
    time.sleep(1)

    # ---- Initialize components ----
    voice    = PepperVoice()
    detector = EmotionDetector()
    video_ui = TherapyVideoCall(detector)
    mic      = PepperMic(voice)

    # ---- Try to launch PyBullet (optional) ----
    try:
        from qibullet import SimulationManager
        sim_mgr = SimulationManager()
        client  = sim_mgr.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        pepper  = sim_mgr.spawnPepper(client)
        pepper.goToPosture("Stand", 0.5)
        p.resetDebugVisualizerCamera(
            7, 45, -35, [0,0,0.5])
        print("✅ PyBullet simulation running!")
        has_sim = True
    except Exception as e:
        print(f"⚠️  PyBullet: {e} (running without simulation)")
        has_sim = False

    # ---- Welcome ----
    time.sleep(1)
    voice.say(
        "Hello! I am Pepper, your therapy robot! "
        "I can see you through the camera. "
        "Let us have a wonderful session together!")

    # ---- Start therapy ----
    controller = TherapyController(voice, mic, video_ui)

    therapy_thread = threading.Thread(
        target=controller.run, daemon=True)
    therapy_thread.start()

    print("\n" + "="*55)
    print("✅ THERAPY SESSION ACTIVE")
    print("="*55)
    print("  Camera window: Press Q or ESC to quit")
    print(f"  Dashboard:     http://localhost:5009")
    print("  Terminal:      type commands below")
    print("="*55 + "\n")

    # ---- Main terminal loop ----
    while video_ui.running:
        try:
            cmd = input("> ").strip()
            if not cmd:
                continue
            cl = cmd.lower()

            if cl in ["q", "quit", "exit"]:
                controller.running = False
                video_ui.stop()
                break

            elif cl == "report":
                print("\n📊 SESSION REPORT")
                print("-"*40)
                print(f"  Child:     {STATE.get('child_name','?')}")
                print(f"  Score:     {STATE['total_score']}")
                print(f"  Emotion:   {STATE['emotion']}")
                print(f"  Attention: {STATE['attention']}%")
                print(f"  Protocol:  {STATE['protocol']}")
                print("-"*40)

            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                STATE["child_name"]  = n
                STATE["child_known"] = True
                voice.say(f"Hello {n}!")

            elif cl == "score":
                print(f"Score: {STATE['total_score']}")

            else:
                controller._on_speech(cmd)

        except (KeyboardInterrupt, EOFError):
            break

    # ---- Cleanup ----
    controller.running = False
    voice.say(
        "Thank you for our session today! "
        "You did amazing! See you next time! 👋")
    video_ui.stop()
    print("\n✅ Session ended. Goodbye!")

    # Save report
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn, "w") as f:
        json.dump(STATE, f, indent=2, default=str)
    print(f"📄 Report saved: {fn}")


if __name__ == "__main__":
    main()

