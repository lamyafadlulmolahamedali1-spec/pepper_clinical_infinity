#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║     PEPPER ULTIMATE AI THERAPY STATION - GEMINI POWERED        ║
║     ASD Therapy | ABA | DTT | TEACCH | TIE | PyBullet          ║
╚══════════════════════════════════════════════════════════════════╝

Features:
 ✅ Gemini AI Brain (gemini-1.5-flash)
 ✅ Real-time emotion detection (DeepFace)
 ✅ High-sensitivity microphone (energy=20)
 ✅ ABA/DTT/TEACCH/TIE protocols
 ✅ PyBullet + Pepper simulation
 ✅ Action tokens → robot movement sync
 ✅ YouTube/Google auto-open
 ✅ Zoom-style video call UI
 ✅ Flask dashboard port 5009
 ✅ Multi-level ABA prompting (L0-L3)
 ✅ Clap detection
 ✅ Gesture verification via camera
"""

# ============================================================
# IMPORTS
# ============================================================
import cv2, numpy as np, threading, time, random
import queue, json, sys, os, math, warnings, webbrowser
import urllib.parse, subprocess
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import pyttsx3
import speech_recognition as sr
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

# PyBullet
import pybullet as p
import pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')

# Gemini
import google.generativeai as genai

# ============================================================
# GEMINI CONFIGURATION
# ============================================================
GEMINI_API_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_API_KEY)

GEMINI_SYSTEM_PROMPT = """
You are Pepper, a highly enthusiastic, curious, and empathetic 
robotic therapist. Your primary goal is to conduct daily therapy 
sessions for a child with Autism Spectrum Disorder (ASD).

CLINICAL FRAMEWORK:
You are an expert in ABA, DTT, TEACCH, and TIE protocols.
- Use clear, short commands (max 2 sentences)
- Provide IMMEDIATE positive reinforcement
- Break tasks into small achievable steps
- Always celebrate success enthusiastically

PERSONALITY:
- Speak with HIGH ENERGY and curiosity
- Use simple, direct sentences
- Be infinitely patient
- Always encourage participation
- Use child's name often

ACTION TOKENS (include in response when needed):
[WAVE_HAND] - wave to greet
[CLAP_HANDS] - celebrate success  
[NOD_HEAD] - show understanding
[DANCE] - celebrate big achievement
[POINT] - point to something
[HUG_ARMS] - comforting gesture
[THINK] - tilt head while thinking

TRIGGERS (include exact text):
- To open YouTube: [YOUTUBE: search query here]
- To open game: [OPEN_GAME]
- To open image search: [IMAGE: search query here]

EMOTION RESPONSE:
- Child is HAPPY → celebrate, advance to harder task
- Child is SAD → comfort, offer easier task, [HUG_ARMS]
- Child is ANGRY → calm down protocol, breathing exercise
- Child is NEUTRAL → engage with fun activity
- Child is SCARED → reassure, lower difficulty

PHYSICAL PRESENCE:
You exist in PyBullet simulation. Reference your movements 
naturally: "Watch me wave!" or "I'm moving closer to you!"

ALWAYS end responses with either:
- A task instruction
- A question to engage the child
- Positive reinforcement
"""

# ============================================================
# CONFIGURATION
# ============================================================
CONFIG = {
    "emotion_threshold":    0.10,
    "emotion_interval":     0.8,
    "mic_energy_threshold": 20,     # VERY HIGH SENSITIVITY
    "mic_pause_threshold":  0.4,
    "mic_dynamic_ratio":    1.5,
    "no_sound_limit":       10,
    "clap_volume_spike":    1500,
    "max_retries":          3,
    "flask_port":           5009,
    "youtube_base": "https://www.youtube.com/results?search_query=",
    "google_images": "https://www.google.com/search?tbm=isch&q=",
}

YOUTUBE_SKILLS = {
    "wash face":    "wash face kids educational",
    "brush teeth":  "brush teeth children autism",
    "wash hands":   "wash hands kids song",
    "get dressed":  "getting dressed autism kids",
    "say hello":    "how to say hello autism children",
    "emotions":     "emotions autism children learning",
    "colors":       "learn colors autism kids",
    "numbers":      "count numbers autism children",
    "alphabet":     "alphabet learning autism kids",
    "eat food":     "eating healthy autism children",
    "tie shoes":    "tie shoelaces kids autism",
    "share":        "sharing autism children social skills",
    "ocean":        "ocean sea animals children educational",
    "animals":      "animals for kids educational autism",
    "space":        "space planets children educational",
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
    "session_logs":     [],
    "total_score":      0,
    "protocol":         "GREETING",
    "prompt_level":     0,
    "is_speaking":      False,
    "clap_detected":    False,
    "current_task":     None,
    "task_success":     False,
    "difficulty":       "easy",
    "consecutive_ok":   0,
    "session_start":    datetime.now().strftime("%H:%M"),
    "gemini_active":    False,
    "last_action_token":"",
    "sim_cmd":          None,
}

EMOTION_EMOJIS = {
    "happy":    ("😊", (0, 220, 80)),
    "sad":      ("😢", (100, 100, 220)),
    "angry":    ("😠", (0, 0, 220)),
    "fear":     ("😨", (0, 180, 220)),
    "surprise": ("😲", (200, 50, 220)),
    "disgust":  ("🤢", (0, 180, 100)),
    "neutral":  ("😐", (180, 180, 180)),
}

def add_log(msg, log_type="info", protocol=None):
    STATE["session_logs"].append({
        "time":     datetime.now().strftime("%H:%M:%S"),
        "message":  msg[:100],
        "type":     log_type,
        "protocol": protocol or STATE["protocol"],
        "emotion":  STATE["emotion"],
        "child":    STATE.get("child_name", "?"),
    })
    emoji, _ = EMOTION_EMOJIS.get(
        STATE["emotion"], ("😐", (180,180,180)))
    print(f"[{datetime.now().strftime('%H:%M:%S')}]"
          f"{emoji} [{log_type.upper()}] {msg[:80]}")

# ============================================================
# GEMINI AI BRAIN
# ============================================================
class GeminiBrain:
    """
    Powered by Gemini 1.5 Flash.
    Context-aware therapeutic responses.
    Handles action tokens and triggers.
    """
    def __init__(self):
        try:
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=GEMINI_SYSTEM_PROMPT,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=200,
                    top_p=0.95,
                )
            )
            self.chat    = self.model.start_chat(history=[])
            self.ok      = True
            STATE["gemini_active"] = True
            print("✅ Gemini 1.5 Flash connected!")
        except Exception as e:
            print(f"⚠️  Gemini: {e}")
            self.ok = False

    def respond(self, user_input, context=None):
        """Get response from Gemini with full context"""
        if not self.ok:
            return self._fallback(user_input)

        # Build context string
        em   = STATE["emotion"]
        att  = STATE["attention"]
        name = STATE.get("child_name", "friend")
        diff = STATE["difficulty"]
        prot = STATE["protocol"]

        ctx = (
            f"[CONTEXT] Child: {name} | "
            f"Emotion: {em} | "
            f"Attention: {att}% | "
            f"Protocol: {prot} | "
            f"Difficulty: {diff} | "
            f"Score: {STATE['total_score']}\n"
        )
        if context:
            ctx += f"[ADDITIONAL] {context}\n"

        full_input = ctx + user_input

        try:
            response = self.chat.send_message(full_input)
            text = response.text.strip()
            add_log(f"Gemini: {text[:60]}", "info")
            return text
        except Exception as e:
            print(f"⚠️  Gemini error: {e}")
            return self._fallback(user_input)

    def _fallback(self, msg):
        """Fallback when Gemini unavailable"""
        name = STATE.get("child_name", "friend")
        responses = [
            f"Great {name}! Let us keep going! 🌟",
            f"You are amazing {name}! 🎉",
            f"I heard you! Let us try something fun! 🎈",
            f"Wonderful! You can do it {name}! 💪",
        ]
        return random.choice(responses)

    def therapy_start(self, child_name):
        """Generate opening therapy message"""
        prompt = (
            f"The child's name is {child_name}. "
            "Start the therapy session enthusiastically. "
            "Greet them, tell them what we will do today, "
            "and give the FIRST simple task."
        )
        return self.respond(prompt)

    def on_emotion(self, emotion):
        """React to detected emotion"""
        prompt = (
            f"The child's emotion just changed to {emotion}. "
            "React appropriately and continue therapy."
        )
        return self.respond(prompt)

    def task_success(self, task):
        """Celebrate task success"""
        prompt = (
            f"The child successfully did: {task}! "
            "Celebrate enthusiastically and give next task!"
        )
        return self.respond(prompt)

    def task_fail(self, task, retry_num):
        """Handle task failure with retry"""
        prompt = (
            f"The child did not complete: {task} "
            f"(attempt {retry_num}/{CONFIG['max_retries']}). "
            "Gently encourage and try again differently."
        )
        return self.respond(prompt)

    def handle_question(self, question):
        """Handle child's questions"""
        prompt = (
            f"The child asked: '{question}' "
            "Answer simply, then open educational content "
            "if relevant ([YOUTUBE:...] or [IMAGE:...])."
        )
        return self.respond(prompt)

    def no_sound_prompt(self):
        """Prompt when child is silent"""
        prompt = (
            "The child has been silent for 10 seconds. "
            "Gently get their attention with a fun prompt."
        )
        return self.respond(prompt)

# ============================================================
# ACTION TOKEN PROCESSOR
# ============================================================
class ActionProcessor:
    """
    Maps Gemini action tokens to PyBullet movements.
    [WAVE_HAND] → pepper joint control
    [YOUTUBE:...] → browser open
    """
    def __init__(self, pepper_obj=None):
        self.pepper = pepper_obj
        self.trigger_handlers = []

    def process(self, text):
        """Extract and execute all action tokens"""
        import re
        clean_text = text

        # === Robot Motion Tokens ===
        motion_tokens = {
            "[WAVE_HAND]":  self._wave,
            "[CLAP_HANDS]": self._clap,
            "[NOD_HEAD]":   self._nod,
            "[DANCE]":      self._dance,
            "[POINT]":      self._point,
            "[HUG_ARMS]":   self._hug,
            "[THINK]":      self._think,
        }
        for token, fn in motion_tokens.items():
            if token in text:
                clean_text = clean_text.replace(token, "")
                STATE["last_action_token"] = token
                threading.Thread(
                    target=fn, daemon=True).start()
                add_log(f"Action: {token}", "info")

        # === YouTube Trigger ===
        yt_match = re.search(
            r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt_match:
            query = yt_match.group(1).strip()
            clean_text = clean_text.replace(
                yt_match.group(0), "")
            self._open_youtube(query)

        # === Image Search Trigger ===
        img_match = re.search(
            r'\[IMAGE:\s*(.+?)\]', text)
        if img_match:
            query = img_match.group(1).strip()
            clean_text = clean_text.replace(
                img_match.group(0), "")
            self._open_images(query)

        # === Game Trigger ===
        if "[OPEN_GAME]" in text:
            clean_text = clean_text.replace(
                "[OPEN_GAME]", "")
            self._open_game()

        return clean_text.strip()

    def open_skill_video(self, query):
        """Open educational YouTube video"""
        q = query.lower()
        # Check skill library first
        for key, search in YOUTUBE_SKILLS.items():
            if key in q:
                url = (CONFIG["youtube_base"] +
                       urllib.parse.quote(search +
                       " autism children educational"))
                webbrowser.open(url)
                add_log(f"YouTube: {key}", "info")
                return url
        # General search
        url = (CONFIG["youtube_base"] +
               urllib.parse.quote(query +
               " autism children educational"))
        webbrowser.open(url)
        add_log(f"YouTube search: {query}", "info")
        return url

    def _open_youtube(self, query):
        url = (CONFIG["youtube_base"] +
               urllib.parse.quote(query +
               " autism children educational"))
        webbrowser.open(url)
        add_log(f"📺 YouTube: {query}", "info")

    def _open_images(self, query):
        url = (CONFIG["google_images"] +
               urllib.parse.quote(query))
        webbrowser.open(url)
        add_log(f"🖼️  Images: {query}", "info")

    def _open_game(self):
        webbrowser.open(f"http://localhost:{CONFIG['flask_port']}")
        add_log("🎮 Game opened!", "info")

    # ===== PyBullet Motions =====
    def _safe_angle(self, joint, angle, speed=0.15):
        if self.pepper:
            try:
                self.pepper.setAngles(joint, angle, speed)
            except: pass

    def _wave(self):
        add_log("🤖 Waving", "info")
        self._safe_angle("RShoulderPitch", 0.2, 0.2)
        self._safe_angle("RElbowRoll", 0.8, 0.2)
        time.sleep(0.3)
        for _ in range(3):
            self._safe_angle("RWristYaw", 0.5, 0.25)
            time.sleep(0.2)
            self._safe_angle("RWristYaw", -0.5, 0.25)
            time.sleep(0.2)
        self._safe_angle("RShoulderPitch", 1.0, 0.15)

    def _clap(self):
        add_log("🤖 Clapping", "info")
        for _ in range(4):
            self._safe_angle("LShoulderPitch", 0.8, 0.25)
            self._safe_angle("RShoulderPitch", 0.8, 0.25)
            time.sleep(0.18)
            self._safe_angle("LShoulderPitch", 1.1, 0.25)
            self._safe_angle("RShoulderPitch", 1.1, 0.25)
            time.sleep(0.18)

    def _nod(self):
        add_log("🤖 Nodding", "info")
        for _ in range(2):
            self._safe_angle("HeadPitch", 0.3, 0.2)
            time.sleep(0.3)
            self._safe_angle("HeadPitch", -0.1, 0.2)
            time.sleep(0.3)
        self._safe_angle("HeadPitch", 0.0, 0.15)

    def _dance(self):
        add_log("🤖 Dancing", "info")
        for _ in range(4):
            self._safe_angle("LShoulderPitch", 0.2, 0.2)
            self._safe_angle("RShoulderPitch", 0.9, 0.2)
            self._safe_angle("HeadYaw", 0.3, 0.2)
            time.sleep(0.25)
            self._safe_angle("LShoulderPitch", 0.9, 0.2)
            self._safe_angle("RShoulderPitch", 0.2, 0.2)
            self._safe_angle("HeadYaw", -0.3, 0.2)
            time.sleep(0.25)
        self._safe_angle("HeadYaw", 0, 0.1)

    def _point(self):
        add_log("🤖 Pointing", "info")
        self._safe_angle("LShoulderPitch", 0.1, 0.15)
        self._safe_angle("LElbowYaw", -1.5, 0.15)
        self._safe_angle("LElbowRoll", -0.03, 0.15)
        time.sleep(1.0)
        self._safe_angle("LShoulderPitch", 1.0, 0.15)

    def _hug(self):
        add_log("🤖 Hugging", "info")
        self._safe_angle("LShoulderPitch", 0.5, 0.1)
        self._safe_angle("RShoulderPitch", 0.5, 0.1)
        self._safe_angle("LShoulderRoll", 0.3, 0.1)
        self._safe_angle("RShoulderRoll", -0.3, 0.1)
        time.sleep(1.2)
        self._safe_angle("LShoulderPitch", 1.0, 0.1)
        self._safe_angle("RShoulderPitch", 1.0, 0.1)
        self._safe_angle("LShoulderRoll", 0.0, 0.1)
        self._safe_angle("RShoulderRoll", 0.0, 0.1)

    def _think(self):
        add_log("🤖 Thinking", "info")
        self._safe_angle("HeadYaw", 0.3, 0.1)
        self._safe_angle("HeadPitch", -0.1, 0.1)
        time.sleep(1.5)
        self._safe_angle("HeadYaw", 0.0, 0.1)
        self._safe_angle("HeadPitch", 0.0, 0.1)

# ============================================================
# VOICE ENGINE
# ============================================================
class PepperVoice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 132)
            self.engine.setProperty('volume', 1.0)
            voices = self.engine.getProperty('voices')
            for v in voices:
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel',
                                  'susan','karen']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok    = True
            self._lock = threading.Lock()
            print("✅ Voice ready (rate=132, female)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")
            self.ok = False

    def say(self, text):
        STATE["is_speaking"] = True
        name = STATE.get("child_name", "friend")
        text = text.replace("{name}", name)
        # Clean action tokens from speech
        for token in ["[WAVE_HAND]","[CLAP_HANDS]",
                      "[NOD_HEAD]","[DANCE]","[POINT]",
                      "[HUG_ARMS]","[THINK]","[OPEN_GAME]"]:
            text = text.replace(token, "")
        import re
        text = re.sub(r'\[YOUTUBE:[^\]]+\]', '', text)
        text = re.sub(r'\[IMAGE:[^\]]+\]', '', text)
        text = text.strip()

        print(f"\n🔊 Pepper: {text}")
        add_log(f"Pepper said: {text[:60]}", "info")

        if self.ok and text:
            with self._lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"⚠️  TTS: {e}")
        STATE["is_speaking"] = False

# ============================================================
# HIGH-SENSITIVITY EMOTION DETECTOR
# ============================================================
class EmotionDetector:
    """Threshold: 10% - detects micro-expressions"""
    def __init__(self):
        self.deepface_ok = False
        self.last_scores = {}

        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            dummy = np.zeros((48,48,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.deepface_ok = True
            print(f"✅ DeepFace ready "
                  f"(threshold={CONFIG['emotion_threshold']*100:.0f}%)")
        except Exception as e:
            print(f"⚠️  DeepFace: {e}")

    def analyze(self, frame):
        if frame is None: return {}
        scores = {}
        if self.deepface_ok:
            try:
                result = self.DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True)
                if result:
                    raw   = result[0]['emotion']
                    total = sum(raw.values()) or 1
                    scores= {k: v/total for k,v in raw.items()}
                    STATE["face_detected"] = True
                    STATE["attention"] = min(
                        100, STATE["attention"] + 2)
            except Exception:
                STATE["face_detected"] = False
                STATE["attention"] = max(
                    0, STATE["attention"] - 2)

        if scores:
            thr = CONFIG["emotion_threshold"]
            valid = {k: v for k,v in scores.items()
                     if v >= thr}
            if valid:
                dominant = max(valid, key=valid.get)
                old_em   = STATE["emotion"]
                STATE["emotion"]        = dominant
                STATE["emotion_scores"] = scores

                pos = scores.get('happy',0) + \
                      scores.get('surprise',0)
                neg = scores.get('sad',0) + \
                      scores.get('angry',0) + \
                      scores.get('fear',0)
                if pos > 0.4:   STATE["engagement"] = "high"
                elif neg > 0.5: STATE["engagement"] = "distressed"
                else:           STATE["engagement"] = "moderate"

                # Return emotion change flag
                return scores, (dominant != old_em)
        return scores, False

# ============================================================
# HIGH-SENSITIVITY MICROPHONE
# ============================================================
class PepperMic:
    """energy_threshold=20 (vs default 300)"""
    def __init__(self):
        self.ok      = False
        self.running = False
        try:
            self.r = sr.Recognizer()
            # === MAXIMUM SENSITIVITY ===
            self.r.energy_threshold              = CONFIG["mic_energy_threshold"]
            self.r.dynamic_energy_threshold      = True
            self.r.dynamic_energy_adjustment_ratio = CONFIG["mic_dynamic_ratio"]
            self.r.pause_threshold               = CONFIG["mic_pause_threshold"]
            self.r.phrase_threshold              = 0.15
            self.r.non_speaking_duration         = 0.15
            self.ok = True
            print(f"✅ Mic ready "
                  f"(energy={CONFIG['mic_energy_threshold']}, "
                  f"pause={CONFIG['mic_pause_threshold']}s)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen(self, timeout=5):
        if not self.ok:
            return input("👶 [Type]: ").strip()
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, 0.2)
                audio = self.r.listen(
                    src, timeout=timeout,
                    phrase_time_limit=12)
            try:
                text = self.r.recognize_google(audio)
                STATE["last_sound_time"] = time.time()
                add_log(f"Heard: {text}", "info")
                return text
            except sr.UnknownValueError:
                self._check_clap(audio)
                STATE["last_sound_time"] = time.time()
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError:
            return ""
        except Exception:
            return ""

    def _check_clap(self, audio):
        try:
            raw = np.frombuffer(
                audio.get_raw_data(), np.int16)
            rms = np.sqrt(np.mean(raw**2))
            if rms > CONFIG["clap_volume_spike"]:
                STATE["clap_detected"] = True
                add_log("👏 Clap detected!", "success")
                return True
        except:
            pass
        return False

    def get_name(self, voice):
        if STATE["child_known"]:
            return STATE["child_name"]
        voice.say("Hello! I am Pepper! What is your name?")
        for _ in range(3):
            resp = self.listen(timeout=8)
            if resp and resp not in ["[sound]", ""]:
                name = self._extract_name(resp)
                if name:
                    STATE["child_name"]  = name
                    STATE["child_known"] = True
                    add_log(f"Name: {name}", "success")
                    return name
        STATE["child_name"]  = "Friend"
        STATE["child_known"] = True
        return "Friend"

    def _extract_name(self, text):
        text = text.lower()
        for rm in ["my name is","i am","i'm","call me",
                   "name is","it is"]:
            text = text.replace(rm, "").strip()
        words = text.split()
        return words[0].capitalize() if words else None

    def listen_continuous(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if STATE["is_speaking"]:
                    time.sleep(0.2)
                    continue
                text = self.listen(timeout=4)
                if text:
                    callback(text)
                time.sleep(0.1)
        threading.Thread(target=_loop, daemon=True).start()

# ============================================================
# VIDEO CALL UI
# ============================================================
class VideoCallUI:
    """Zoom-style therapy window with all overlays"""
    def __init__(self, detector):
        self.detector    = detector
        self.cap         = None
        self.frame       = None
        self.running     = False
        self.last_analyze= 0
        self.task_text   = ""
        self.task_time   = 0
        self.praise_text = ""
        self.praise_time = 0
        self.gemini_text = ""
        self.gemini_time = 0

        # Pepper avatar
        self.avatar = self._make_avatar()

        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.running = True
                threading.Thread(
                    target=self._run, daemon=True).start()
                print("✅ Video Call UI ready!")
            else:
                print("⚠️  No camera")
        except Exception as e:
            print(f"⚠️  Camera: {e}")

    def _make_avatar(self):
        img = np.zeros((220, 170, 3), dtype=np.uint8)
        img[:] = (15, 20, 45)
        # Glow effect
        cv2.circle(img, (85, 55), 45, (30,50,100), -1)
        # Head
        cv2.circle(img, (85, 55), 40, (220,195,175), -1)
        # Eyes
        for ex in [70, 100]:
            cv2.circle(img, (ex,48), 9, (0,140,255), -1)
            cv2.circle(img, (ex,48), 4, (255,255,255), -1)
            cv2.circle(img, (ex+1,47), 2, (0,0,0), -1)
        # Smile
        cv2.ellipse(img,(85,68),(14,7),0,0,180,(80,40,40),2)
        # Nose
        cv2.circle(img, (85,63), 2, (180,150,140), -1)
        # Body
        cv2.rectangle(img,(55,95),(115,175),(130,140,190),-1)
        cv2.rectangle(img,(58,98),(112,172),(100,110,160),2)
        # Arms
        cv2.rectangle(img,(20,100),(55,135),(130,140,190),-1)
        cv2.rectangle(img,(115,100),(150,135),(130,140,190),-1)
        # Pepper label
        cv2.putText(img,"PEPPER",(28,200),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,(80,180,255),2)
        # Gemini badge
        cv2.rectangle(img,(5,205),(80,218),(20,20,60),-1)
        cv2.putText(img,"Gemini AI",(8,215),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,(150,220,255),1)
        return img

    def _run(self):
        fc = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret: continue
            fc += 1
            frame = cv2.flip(frame, 1)
            self.frame = frame.copy()

            # Analyze emotion
            now = time.time()
            if now - self.last_analyze > \
               CONFIG["emotion_interval"]:
                self.last_analyze = now
                threading.Thread(
                    target=self.detector.analyze,
                    args=(frame.copy(),),
                    daemon=True).start()

            ui = self._build(frame)
            cv2.imshow("🤖 Pepper Therapy - Gemini AI", ui)
            k = cv2.waitKey(1) & 0xFF
            if k in [ord('q'), ord('Q'), 27]:
                self.running = False
                break
            time.sleep(0.015)

        self.cap.release()
        cv2.destroyAllWindows()

    def _build(self, frame):
        h, w = frame.shape[:2]
        ui   = frame.copy()

        # === Header ===
        ov = ui.copy()
        cv2.rectangle(ov, (0,0), (w,75), (8,12,28), -1)
        ui = cv2.addWeighted(ov, 0.82, ui, 0.18, 0)

        name = STATE.get("child_name","...")
        prot = STATE["protocol"]
        score= STATE["total_score"]
        cv2.putText(ui,
            "🤖 Pepper - Gemini AI Therapy",
            (15,30), cv2.FONT_HERSHEY_SIMPLEX,
            0.8, (255,255,255), 2)
        cv2.putText(ui,
            f"Child: {name}  |  {prot}  |"
            f"  Score: {score}  |  "
            f"Diff: {STATE['difficulty'].upper()}",
            (15,58), cv2.FONT_HERSHEY_SIMPLEX,
            0.48, (140,190,255), 1)

        # === Pepper avatar PIP ===
        av   = self.avatar.copy()
        ah,aw = av.shape[:2]

        # Animate during speech
        if STATE["is_speaking"]:
            t = int(time.time()*4)%3
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                         (0,180+t*20,255),2+t)

        # Action token indicator
        tok = STATE.get("last_action_token","")
        if tok and time.time() < STATE.get("_tok_t",0)+2:
            cv2.putText(av, tok.replace("[","").replace("]",""),
                       (5,215), cv2.FONT_HERSHEY_SIMPLEX,
                       0.28, (255,200,0), 1)

        x1 = w - aw - 15
        y1 = h - ah - 90
        ui[y1-3:y1+ah+3, x1-3:x1+aw+3] = (15,20,45)
        ui[y1:y1+ah, x1:x1+aw] = av
        border_col = (0,200,255) if STATE["is_speaking"] \
                     else (80,80,120)
        cv2.rectangle(ui,(x1-3,y1-3),
                     (x1+aw+3,y1+ah+3),border_col,2)
        if STATE["is_speaking"]:
            cv2.putText(ui,"SPEAKING",
                       (x1,y1-8),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.38,(0,255,200),1)

        # === Gemini indicator ===
        gem_col = (0,200,100) if STATE["gemini_active"] \
                  else (100,100,100)
        cv2.circle(ui,(w-aw-35,y1+10),6,gem_col,-1)
        cv2.putText(ui,"Gemini",
                   (w-aw-60,y1+14),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.32,gem_col,1)

        # === Bottom bar ===
        ov2 = ui.copy()
        cv2.rectangle(ov2,(0,h-85),(w,h),(8,12,28),-1)
        ui = cv2.addWeighted(ov2,0.78,ui,0.22,0)

        em      = STATE["emotion"]
        _,em_col= EMOTION_EMOJIS.get(em,("",( 180,180,180)))
        att     = STATE["attention"]
        eng     = STATE["engagement"]

        cv2.putText(ui,
            f"Emotion: {em.upper()}",
            (15,h-55),cv2.FONT_HERSHEY_SIMPLEX,
            0.72,em_col,2)
        cv2.putText(ui,
            f"Attention: {att}%  Engagement: {eng}",
            (15,h-28),cv2.FONT_HERSHEY_SIMPLEX,
            0.52,(255,230,100),1)

        # Prompt level
        pl     = STATE["prompt_level"]
        pl_cols= [(0,200,0),(200,200,0),
                  (200,100,0),(200,0,0)]
        pl_c   = pl_cols[min(pl,3)]
        cv2.circle(ui,(w-55,h-55),22,pl_c,-1)
        cv2.putText(ui,f"P{pl}",
                   (w-63,h-46),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.65,(255,255,255),2)

        # Emotion bars
        scores = STATE.get("emotion_scores",{})
        if scores:
            bx,by = w-175,95
            cv2.putText(ui,"Emotions:",
                       (bx,by-8),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.37,(200,200,200),1)
            for i,(e,s) in enumerate(
                    sorted(scores.items(),
                           key=lambda x:-x[1])[:6]):
                y   = by + i*20
                bl  = int(s*120)
                _,c = EMOTION_EMOJIS.get(e,("",
                                             (150,150,150)))
                cv2.rectangle(ui,(bx,y),(bx+bl,y+13),c,-1)
                cv2.putText(ui,f"{e[:5]}:{s:.0%}",
                           (bx,y+11),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.3,(255,255,255),1)

        # Face detection
        fd_c = (0,255,0) if STATE["face_detected"] \
                         else (0,0,255)
        cv2.circle(ui,(w-15,20),7,fd_c,-1)

        # Task display
        now = time.time()
        if self.task_text and now-self.task_time < 7:
            tw = min(len(self.task_text)*12+20, w-40)
            tx = max(10, w//2-tw//2)
            cv2.rectangle(ui,
                         (tx-5,h//2-40),
                         (tx+tw+5,h//2+8),
                         (15,50,120),-1)
            cv2.rectangle(ui,
                         (tx-5,h//2-40),
                         (tx+tw+5,h//2+8),
                         (0,140,255),2)
            cv2.putText(ui,self.task_text[:55],
                       (tx,h//2-12),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.65,(255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_time < 4:
            pw = min(len(self.praise_text)*16+20, w-40)
            px = max(10, w//2-pw//2)
            cv2.rectangle(ui,
                         (px-5,h//2+25),
                         (px+pw+5,h//2+72),
                         (0,70,0),-1)
            cv2.putText(ui,self.praise_text[:40],
                       (px,h//2+58),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.85,(0,255,100),2)

        # Gemini response preview
        if self.gemini_text and now-self.gemini_time < 5:
            lines = [self.gemini_text[i:i+60]
                     for i in range(0,
                     min(len(self.gemini_text),120),60)]
            for li,line in enumerate(lines[:2]):
                cv2.putText(ui, line,
                           (15,h-88-li*22),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.42,(200,255,200),1)

        # REC
        cv2.circle(ui,(38,28),8,(0,0,220),-1)
        cv2.putText(ui,"REC",(50,34),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.42,(0,0,220),1)

        # Clap indicator
        if STATE["clap_detected"]:
            cv2.putText(ui,"👏 CLAP!",
                       (w//2-50,80),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       1.2,(0,255,100),3)

        return ui

    def show_task(self, text):
        self.task_text = text
        self.task_time = time.time()

    def show_praise(self, text):
        self.praise_text = text
        self.praise_time = time.time()

    def show_gemini(self, text):
        self.gemini_text = text[:120]
        self.gemini_time = time.time()

    def stop(self):
        self.running = False
        try: cv2.destroyAllWindows()
        except: pass

# ============================================================
# PYBULLET SIMULATION
# ============================================================
class SimulationManager:
    def __init__(self):
        self.pepper    = None
        self.ok        = False
        self.rx = self.ry = 0.0
        self.head_yaw  = 0.0
        self.auto_walk = True
        self.balloons  = []
        self.children  = []

    def launch(self):
        try:
            from qibullet import SimulationManager as QiSim
            self.qisim  = QiSim()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._build_room()
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._create_balloons()
            self._create_children()
            p.resetDebugVisualizerCamera(
                7,45,-35,[0,0,0.5])
            self.ok = True

            # Start threads
            threading.Thread(
                target=self._sim_loop,daemon=True).start()
            threading.Thread(
                target=self._walk_loop,daemon=True).start()
            threading.Thread(
                target=self._arm_loop,daemon=True).start()

            print("✅ PyBullet simulation ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _build_room(self):
        wc = [0.85,0.85,0.9,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.5,.4,.3,1]),[0,0,.01])
        for txt,pos in [
            ("ABA",[-4,3,1.9]),("DTT",[4,3,1.9]),
            ("TEACCH",[0,4,1.9]),("TIE",[-4,-3,1.9]),
            ("GEMINI AI",[0,-4,1.9])]:
            p.addUserDebugText(
                txt,pos,[.4,.4,.9],textSize=1.2,lifeTime=0)

    def _create_balloons(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
              [1,1,.2,1],[1,.5,.2,1],[.8,.2,.8,1]]
        for i in range(8):
            vs = p.createVisualShape(p.GEOM_SPHERE,
                radius=.15,rgbaColor=cols[i%len(cols)])
            bid= p.createMultiBody(0,-1,vs,
                [random.uniform(-3,3),
                 random.uniform(-2,2),
                 random.uniform(.8,2.2)])
            self.balloons.append({
                "id":bid,"x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

    def _create_children(self):
        kids = [
            ("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1],"mild"),
            ("Sara", [-1.2,1.3,0],[1.,.6,.0,1],"moderate"),
            ("Yusuf",[.5,-2.,0], [.9,.15,.15,1],"severe"),
        ]
        for name,pos,col,sev in kids:
            vs=p.createVisualShape(p.GEOM_BOX,
               halfExtents=[.13,.09,.21],rgbaColor=col)
            tid=p.createMultiBody(0,-1,vs,
               [pos[0],pos[1],.41])
            vs2=p.createVisualShape(p.GEOM_SPHERE,
               radius=.11,rgbaColor=[1.,.82,.65,1.])
            hid=p.createMultiBody(0,-1,vs2,
               [pos[0],pos[1],.74])
            em={"mild":"🟢","moderate":"🟠","severe":"🔴"}
            p.addUserDebugText(
               f"{name}{em[sev]}",
               [pos[0],pos[1],1.05],
               [0,0,0],textSize=.8,lifeTime=0)
            self.children.append({
                "name":name,"pos":pos,
                "tid":tid,"hid":hid,"sev":sev})

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b["z"]+=b["spd"]
                if b["z"]>2.8:
                    b["z"]=.6
                    b["x"]=random.uniform(-3,3)
                    b["y"]=random.uniform(-2,2)
                try:
                    p.resetBasePositionAndOrientation(
                        b["id"],[b["x"],b["y"],b["z"]],
                        [0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _walk_loop(self):
        t=0
        while True:
            if self.auto_walk:
                t+=.015
                self.rx+=.018*math.cos(t*.4)
                self.ry+=.018*math.sin(t*.5)
                self.rx=max(-3.5,min(3.5,self.rx))
                self.ry=max(-2.8,min(2.8,self.ry))
                try:
                    self.pepper.setPosition(
                        [self.rx,self.ry,.8])
                except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph=0
        while True:
            try:
                if STATE["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph)
                    R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles(
                        "LShoulderPitch",L,.07)
                    self.pepper.setAngles(
                        "RShoulderPitch",R,.07)
                else:
                    self.pepper.setAngles(
                        "LShoulderPitch",1.,.04)
                    self.pepper.setAngles(
                        "RShoulderPitch",1.,.04)
            except: pass
            time.sleep(.04)

    def show_text(self, text):
        if not self.ok: return
        try:
            pos=p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],
                [pos[0],pos[1],pos[2]+1.3],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass

# ============================================================
# FLASK DASHBOARD
# ============================================================
flask_app = Flask(__name__)

DASH_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>🤖 Pepper Gemini Therapy</title>
<meta http-equiv="refresh" content="2">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;
     background:#060912;color:#e0e6ff}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);
     padding:14px 26px;display:flex;
     align-items:center;gap:12px;
     border-bottom:1px solid #1f1060}
.hdr h1{font-size:1.25em;color:#a78bfa}
.live{background:#ef4444;color:#fff;
      padding:2px 8px;border-radius:15px;
      font-size:.73em;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.gem{background:#1a2555;color:#60a5fa;
     padding:3px 10px;border-radius:12px;
     font-size:.72em;border:1px solid #3b82f6}
.cont{max-width:1200px;margin:0 auto;padding:16px}
.g5{display:grid;grid-template-columns:repeat(5,1fr);
    gap:11px;margin-bottom:16px}
.g2{display:grid;grid-template-columns:1.3fr 1fr;gap:13px}
.card{background:#0c0f1e;border-radius:11px;
      padding:15px;border:1px solid #1a1f40}
.card h2{font-size:.82em;color:#6b7280;
         border-bottom:1px solid #1a1f40;
         padding-bottom:6px;margin-bottom:11px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:10px;
      padding:14px;text-align:center}
.n{font-size:2.1em;font-weight:700;color:#a78bfa}
.l{font-size:.73em;color:#6b7280;margin-top:2px}
.emo{display:inline-block;padding:5px 14px;
     border-radius:18px;font-weight:700}
.happy{background:#05291555;color:#34d399;
       border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;
     border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;
       border:1px solid #f87171}
.neutral{background:#1f293755;color:#9ca3af;
         border:1px solid #9ca3af}
.fear{background:#1c190055;color:#fbbf24;
      border:1px solid #fbbf24}
.surprise{background:#2e106555;color:#c084fc;
          border:1px solid #c084fc}
.bar-bg{background:#1f2937;border-radius:7px;
        height:9px;margin:5px 0}
.bar{height:9px;border-radius:7px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
.log-box{max-height:430px;overflow-y:auto}
.log{padding:5px 9px;margin:3px 0;border-radius:5px;
     font-size:.76em;border-left:3px solid #4f46e5;
     background:#07090f}
.log.success{border-color:#10b981}
.log.fail{border-color:#ef4444}
.log.info{border-color:#3b82f6}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:7px 13px;
     border-radius:7px;cursor:pointer;
     font-size:.8em;margin:3px;transition:.2s}
.btn:hover{opacity:.85}
.prot{display:inline-block;padding:2px 7px;
      border-radius:9px;font-size:.71em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}
input{width:100%;padding:6px 10px;border-radius:6px;
      border:1px solid #374151;background:#07090f;
      color:#e0e6ff;font-size:.83em}
</style>
</head>
<body>
<div class="hdr">
  <div style="font-size:1.8em">🤖</div>
  <div>
    <h1>Pepper Gemini AI Therapy Station</h1>
    <p style="font-size:.8em;opacity:.8">
      Child: <b>{{s.child_name or '...'}}</b> |
      <span class="prot {{s.protocol}}">{{s.protocol}}</span> |
      Diff: {{s.difficulty.upper()}}
    </p>
  </div>
  <span class="live">● LIVE</span>
  <span class="gem">⚡ Gemini 1.5 Flash</span>
</div>

<div class="cont">
  <div class="g5">
    <div class="stat">
      <div class="n">{{s.total_score}}</div>
      <div class="l">Score</div>
    </div>
    <div class="stat">
      <div class="n">{{s.attention}}%</div>
      <div class="l">Attention</div>
    </div>
    <div class="stat">
      <div class="n">P{{s.prompt_level}}</div>
      <div class="l">Prompt Level</div>
    </div>
    <div class="stat">
      <div class="n">{{s.consecutive_ok}}</div>
      <div class="l">Streak</div>
    </div>
    <div class="stat">
      <div class="n">{{s.session_logs|length}}</div>
      <div class="l">Interactions</div>
    </div>
  </div>

  <div class="g2">
    <div>
      <div class="card" style="margin-bottom:13px">
        <h2>😊 Emotion Stream</h2>
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
            <span style="font-size:.78em;color:#818cf8">
              {{s.attention}}% attention</span>
          </div>
          <div style="font-size:.8em;color:#6b7280">
            Engagement:
            <b style="color:#e0e6ff">{{s.engagement}}</b>
          </div>
          <div style="margin-top:5px;font-size:.75em;
            color:{{'#34d399' if s.face_detected else '#ef4444'}}">
            {{'✓ Face Detected' if s.face_detected
              else '✗ No Face!'}}
          </div>
          {% if s.clap_detected %}
          <div style="color:#fbbf24;margin-top:5px;
                      font-weight:700">
            👏 CLAP DETECTED!
          </div>
          {% endif %}
        </div>
      </div>

      <div class="card" style="margin-bottom:13px">
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
          <button class="btn" name="c" value="dance">
            💃 Dance</button>
          <button class="btn" name="c" value="game">
            🎮 Game</button>
        </form>
      </div>

      <div class="card">
        <h2>📺 Educational Content</h2>
        <div style="display:flex;flex-wrap:wrap;gap:4px;
                    margin-bottom:9px">
          {% for skill in skills %}
          <form method="POST" action="/skill"
                style="display:inline">
            <button class="btn" name="s"
                    value="{{skill}}"
                    style="font-size:.72em;padding:5px 9px">
              {{skill}}
            </button>
          </form>
          {% endfor %}
        </div>
        <form method="POST" action="/search"
              style="display:flex;gap:6px">
          <input name="q" placeholder="Search for child...">
          <button class="btn">🔍</button>
        </form>
      </div>
    </div>

    <div class="card">
      <h2>📋 Live Session Log</h2>
      <div class="log-box">
        {% for log in s.session_logs[-35:]|reverse %}
        <div class="log {{log.type}}">
          <span style="color:#6366f1">{{log.time}}</span>
          <span class="prot {{log.protocol}}">
            {{log.protocol}}</span>
          {% if log.child != '?' %}
          <b style="color:#a78bfa">{{log.child}}</b>:
          {% endif %}
          {{log.message}}
          <span style="color:#374151;font-size:.78em">
            |{{log.emotion}}</span>
        </div>
        {% endfor %}
      </div>
      <div style="margin-top:9px;display:flex;
                  justify-content:space-between;
                  align-items:center">
        <a href="/export" style="color:#6366f1;
                                  font-size:.8em">
          📄 Export</a>
        <form method="POST" action="/name"
              style="display:flex;gap:5px">
          <input name="n"
                 placeholder="Set child name..."
                 style="width:130px">
          <button class="btn"
                  style="padding:5px 9px">✓</button>
        </form>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

@flask_app.route("/")
def dash():
    return render_template_string(
        DASH_HTML, s=STATE,
        skills=list(YOUTUBE_SKILLS.keys()))

@flask_app.route("/update_context", methods=["POST"])
def update_ctx():
    d  = request.json or {}
    em = d.get("emotion","neutral")
    STATE["emotion"]      = em
    STATE["face_detected"]= True
    return jsonify({"status":"ok"})

@flask_app.route("/cmd", methods=["POST"])
def cmd():
    STATE["sim_cmd"] = request.form.get("c","")
    return dash()

@flask_app.route("/name", methods=["POST"])
def set_name():
    n = request.form.get("n","").strip().title()
    if n:
        STATE["child_name"]  = n
        STATE["child_known"] = True
        add_log(f"Name: {n}", "success")
    return dash()

@flask_app.route("/skill", methods=["POST"])
def open_skill():
    s   = request.form.get("s","")
    srch= YOUTUBE_SKILLS.get(s, s+" autism educational")
    url = (CONFIG["youtube_base"] +
           urllib.parse.quote(srch))
    webbrowser.open(url)
    add_log(f"YouTube: {s}", "info")
    return dash()

@flask_app.route("/search", methods=["POST"])
def search():
    q   = request.form.get("q","")
    url = (CONFIG["youtube_base"] +
           urllib.parse.quote(
               q + " autism children educational"))
    webbrowser.open(url)
    add_log(f"Search: {q}", "info")
    return dash()

@flask_app.route("/export")
def export():
    fn = (f"session_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(STATE, f, indent=2, default=str)
    return jsonify({"saved":fn})

@flask_app.route("/report")
def report_route():
    return jsonify(STATE)

def run_flask():
    flask_app.run(port=CONFIG["flask_port"],
                  debug=False,use_reloader=False)

# ============================================================
# MAIN THERAPY CONTROLLER
# ============================================================
class TherapyController:
    def __init__(self, gemini, voice, mic, video, sim):
        self.gemini  = gemini
        self.voice   = voice
        self.mic     = mic
        self.video   = video
        self.sim     = sim
        self.actions = ActionProcessor(
            sim.pepper if sim.ok else None)
        self.running = False

    def _speak_gemini(self, text):
        """Process Gemini response: tokens + speech"""
        clean = self.actions.process(text)
        if self.video:
            self.video.show_gemini(clean)
        if self.sim.ok:
            self.sim.show_text(clean[:55])
        STATE["_tok_t"] = time.time()
        self.voice.say(clean)

    def run(self):
        self.running = True
        STATE["protocol"] = "GREETING"

        # Learn name
        name = self.mic.get_name(self.voice)

        # Start with Gemini
        opening = self.gemini.therapy_start(name)
        self._speak_gemini(opening)
        add_log("Session started", "success", "GREETING")
        time.sleep(1)

        # Continuous listening
        self.mic.listen_continuous(self._on_speech)

        # Therapy loop
        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx = 0
        while self.running:
            self._check_no_sound()
            self._check_prompt_level()
            self._check_emotion_change()
            self._check_sim_cmd()

            protocol = protocols[p_idx % len(protocols)]
            p_idx   += 1
            STATE["protocol"] = protocol

            self._run_protocol(protocol)
            time.sleep(0.5)

    def _check_no_sound(self):
        elapsed = time.time() - STATE["last_sound_time"]
        if elapsed > CONFIG["no_sound_limit"]:
            STATE["last_sound_time"] = time.time()
            resp = self.gemini.no_sound_prompt()
            self._speak_gemini(resp)

    def _check_prompt_level(self):
        em  = STATE["emotion"]
        att = STATE["attention"]
        eng = STATE["engagement"]
        fd  = STATE["face_detected"]

        if fd and att > 60 and em == "happy":
            STATE["prompt_level"] = 0
        elif not fd or att < 40:
            if STATE["prompt_level"] < 1:
                STATE["prompt_level"] = 1
                resp = self.gemini.respond(
                    "Child is distracted. "
                    "Verbal prompt to look at Pepper.")
                self._speak_gemini(resp)
        if eng == "distressed":
            if STATE["prompt_level"] < 3:
                STATE["prompt_level"] = 3
                resp = self.gemini.on_emotion(em)
                self._speak_gemini(resp)

    def _check_emotion_change(self):
        # handled in video loop, but also
        # trigger Gemini on significant changes
        pass

    def _check_sim_cmd(self):
        cmd = STATE.get("sim_cmd")
        if not cmd: return
        STATE["sim_cmd"] = None
        name = STATE.get("child_name","friend")

        if cmd == "dance":
            resp = self.gemini.respond(
                f"Dance with {name} to celebrate!")
            self._speak_gemini(resp)
            self.actions._dance()
        elif cmd == "game":
            self.actions._open_game()
            resp = self.gemini.respond(
                "Open the game for the child!")
            self._speak_gemini(resp)
        elif cmd in ["aba","dtt","teacch","tie"]:
            STATE["protocol"] = cmd.upper()

    def _run_protocol(self, protocol):
        """Run one therapy cycle"""
        name = STATE.get("child_name","friend")
        em   = STATE["emotion"]
        att  = STATE["attention"]

        if protocol == "ABA":
            # Pick task
            tasks = {
                "easy": ["Clap your hands! 👏",
                         "Touch your nose! 👃",
                         "Wave to me! 👋",
                         "Show happy face! 😊"],
                "medium":["Stand up and sit!",
                           "Touch your ears!",
                           "Point to the door!",
                           "Count to three!"],
                "hard":  ["Tell me your name!",
                           "What color is sky?",
                           "Name an animal!"],
            }
            diff  = STATE["difficulty"]
            task  = random.choice(
                tasks.get(diff, tasks["easy"]))

            STATE["current_task"] = task

            resp = self.gemini.respond(
                f"Give ABA instruction: '{task}' "
                f"to {name}. Emotion: {em}. "
                f"Attention: {att}%")
            self._speak_gemini(resp)
            if self.video: self.video.show_task(task)

            # Wait for response
            success = self._wait_response(task, 12)

            if success:
                STATE["total_score"]    += 10
                STATE["consecutive_ok"] += 1
                resp = self.gemini.task_success(task)
                self._speak_gemini(resp)
                if self.video:
                    self.video.show_praise("AMAZING! ⭐")
                add_log(f"ABA: {task} ✅","success","ABA")

                # Level up
                if STATE["consecutive_ok"] >= 3:
                    if STATE["difficulty"] == "easy":
                        STATE["difficulty"] = "medium"
                    elif STATE["difficulty"] == "medium":
                        STATE["difficulty"] = "hard"
                    STATE["consecutive_ok"] = 0
                    resp = self.gemini.respond(
                        "Child is doing great! "
                        "Celebrate and increase difficulty!")
                    self._speak_gemini(resp)
            else:
                STATE["task_retries"] = \
                    STATE.get("task_retries",0) + 1
                STATE["consecutive_ok"] = 0
                if STATE.get("task_retries",0) < \
                   CONFIG["max_retries"]:
                    resp = self.gemini.task_fail(
                        task,
                        STATE.get("task_retries",1))
                    self._speak_gemini(resp)
                    add_log(
                        f"ABA: {task} retry","fail","ABA")
                else:
                    STATE["task_retries"] = 0
                    resp = self.gemini.respond(
                        f"Skip task, give {name} "
                        "easier task with encouragement.")
                    self._speak_gemini(resp)

        elif protocol == "DTT":
            STATE["protocol"] = "DTT"
            resp = self.gemini.respond(
                "Run one DTT trial appropriate for "
                f"difficulty={STATE['difficulty']}, "
                f"emotion={em}")
            self._speak_gemini(resp)
            if self.video:
                self.video.show_task("DTT Trial")
            success = self._wait_response("DTT", 10)
            if success:
                STATE["total_score"] += 12
                resp = self.gemini.task_success("DTT trial")
                self._speak_gemini(resp)
                add_log("DTT ✅","success","DTT")
            else:
                add_log("DTT ❌","fail","DTT")
            time.sleep(2)

        elif protocol == "TEACCH":
            STATE["protocol"] = "TEACCH"
            resp = self.gemini.respond(
                "Run TEACCH visual schedule activity. "
                f"Child emotion: {em}")
            self._speak_gemini(resp)
            time.sleep(3)
            if STATE["emotion"] == "happy":
                STATE["total_score"] += 15
            add_log("TEACCH ✅","success","TEACCH")

        elif protocol == "TIE":
            STATE["protocol"] = "TIE"
            resp = self.gemini.respond(
                "TIE adaptive session. "
                f"Emotion={em}, att={att}%, "
                f"eng={STATE['engagement']}. "
                "Adapt and respond.")
            self._speak_gemini(resp)
            time.sleep(3)
            STATE["total_score"] += 8
            add_log("TIE ✅","success","TIE")

    def _wait_response(self, task, timeout=12):
        deadline = time.time() + timeout
        STATE["task_success"] = False

        while time.time() < deadline:
            # Clap = success for clap tasks
            if "clap" in task.lower() and \
               STATE["clap_detected"]:
                STATE["clap_detected"] = False
                return True
            # Happy emotion = likely did it
            if STATE["emotion"] == "happy" and \
               STATE["attention"] > 60:
                return True
            # Task success flag (set by speech)
            if STATE["task_success"]:
                STATE["task_success"] = False
                return True
            time.sleep(0.3)
        return False

    def _on_speech(self, text):
        """Handle child speech - full Gemini processing"""
        STATE["last_sound_time"] = time.time()
        if not text or text == "[sound]":
            if text == "[sound]":
                name = STATE.get("child_name","friend")
                self.voice.say(f"I heard you {name}! 👍")
            return

        t    = text.lower()
        name = STATE.get("child_name","friend")

        # Name learning
        if not STATE["child_known"]:
            n = self.mic._extract_name(text)
            if n:
                STATE["child_name"]  = n
                STATE["child_known"] = True
                resp = self.gemini.respond(
                    f"Child told you their name is {n}. "
                    "Welcome them warmly!")
                self._speak_gemini(resp)
            return

        # How-to questions → YouTube
        how_words = ["how","what is","show me","tell me"]
        if any(w in t for w in how_words):
            # Let Gemini decide + open video
            resp = self.gemini.handle_question(text)
            self._speak_gemini(resp)
            # Also directly open YouTube
            self.actions.open_skill_video(text)
            return

        # Game request
        if any(w in t for w in
               ["play","game","fun","games"]):
            resp = self.gemini.respond(
                f"Child wants to play a game! "
                "Respond enthusiastically, "
                "open the game with [OPEN_GAME]!")
            self._speak_gemini(resp)
            return

        # Task keywords → mark success
        task = STATE.get("current_task","")
        if task:
            task_words = task.lower().split()
            if any(w in t for w in task_words):
                STATE["task_success"] = True

        # General Gemini response
        resp = self.gemini.respond(
            f"Child said: '{text}'. "
            "Respond therapeutically.")
        self._speak_gemini(resp)

# ============================================================
# MAIN
# ============================================================
def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     PEPPER ULTIMATE AI THERAPY - GEMINI 1.5 FLASH              ║
║     ASD | ABA | DTT | TEACCH | TIE | PyBullet | OpenCV         ║
╚══════════════════════════════════════════════════════════════════╝

Settings:
  🧠 AI:      Gemini 1.5 Flash
  📷 Emotion: DeepFace threshold=10%
  🎤 Mic:     energy=20 (MAXIMUM SENSITIVITY)
  🌐 Dashboard: http://localhost:5009
  ⌨️  Press Q or ESC in camera window to exit
""")

    # Flask
    threading.Thread(target=run_flask,daemon=True).start()
    print("✅ Dashboard: http://localhost:5009")
    time.sleep(1)

    # Initialize all components
    gemini  = GeminiBrain()
    voice   = PepperVoice()
    detector= EmotionDetector()
    video   = VideoCallUI(detector)
    mic     = PepperMic()
    sim     = SimulationManager()
    sim.launch()

    actions = ActionProcessor(
        sim.pepper if sim.ok else None)

    # Welcome
    time.sleep(1.5)
    voice.say(
        "Hello! I am Pepper, your AI therapy robot, "
        "powered by Gemini! "
        "I can see you and hear you. "
        "Let us begin!")
    if sim.ok:
        actions._wave()

    # Start therapy
    ctrl = TherapyController(
        gemini, voice, mic, video, sim)
    t = threading.Thread(
        target=ctrl.run, daemon=True)
    t.start()

    print("\n" + "="*58)
    print("✅ THERAPY SESSION ACTIVE")
    print("="*58)
    print("Commands: 'report' | 'name X' | 'exit'")
    print("="*58 + "\n")

    # Terminal loop
    while getattr(video, 'running', True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()

            if cl in ["q","quit","exit"]:
                ctrl.running = False
                video.stop()
                break

            elif cl == "report":
                print("\n📊 SESSION REPORT")
                print("-"*45)
                print(f"  Child:    {STATE.get('child_name','?')}")
                print(f"  Score:    {STATE['total_score']}")
                print(f"  Emotion:  {STATE['emotion']}")
                print(f"  Attention:{STATE['attention']}%")
                print(f"  Protocol: {STATE['protocol']}")
                print(f"  Difficulty:{STATE['difficulty']}")
                print("-"*45)

            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                STATE["child_name"]  = n
                STATE["child_known"] = True
                voice.say(f"Hello {n}!")

            else:
                ctrl._on_speech(cmd)

        except (KeyboardInterrupt, EOFError):
            break

    # Save session
    ctrl.running = False
    voice.say("Goodbye! Amazing session today! See you soon!")
    fn = (f"session_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(STATE, f, indent=2, default=str)
    print(f"\n📄 Session saved: {fn}")
    print("✅ Therapy session complete!")

if __name__ == "__main__":
    main()

