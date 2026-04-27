#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  AI-DRIVEN COMPANION ROBOT FOR CHILDREN WITH AUTISM            ║
║  companion_robot_genesis.py                                     ║
║  Commander: Lamya | Omdurman Islamic University                 ║
╠══════════════════════════════════════════════════════════════════╣
║  CLINICAL PROTOCOLS: ABA + ESDM + DTT                          ║
║  MULTI-LEVEL: Motor → Verbal → Social                          ║
║  GPU: NVIDIA GTX 1650 | Ubuntu 22.04 | Python 3.9              ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 0. ENVIRONMENT + AUTO-INSTALL
# ═══════════════════════════════════════════════════════════════
import os, sys, subprocess, ctypes, warnings, socket, signal, time

os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL': '3',
    'PYGAME_HIDE_SUPPORT_PROMPT': '1',
    'PYTHONWARNINGS': 'ignore',
    'OPENCV_LOG_LEVEL': 'ERROR',
    'CUDA_VISIBLE_DEVICES': '0',
    'TF_FORCE_GPU_ALLOW_GROWTH': 'true',
})
warnings.filterwarnings('ignore')

try:
    _a = ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

def auto_install(pkg, import_name=None):
    name = import_name or pkg.replace('-','_')
    try:
        __import__(name)
        return True
    except ImportError:
        print(f"⚙️  Installing {pkg}...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install',
                pkg, '--break-system-packages', '-q'],
                capture_output=True, timeout=90)
            return True
        except: return False

for pkg, imp in [
    ('mediapipe', 'mediapipe'),
    ('faster-whisper', 'faster_whisper'),
    ('deepface', 'deepface'),
    ('pyttsx3', 'pyttsx3'),
    ('speechrecognition', 'speech_recognition'),
    ('opencv-python', 'cv2'),
    ('numpy', 'numpy'),
    ('flask', 'flask'),
]:
    auto_install(pkg, imp)

def kill_ports(*ports):
    for port in ports:
        try: os.system(f"fuser -k {port}/tcp 2>/dev/null")
        except: pass
        try:
            r = subprocess.run(['lsof','-ti',f':{port}'],
                capture_output=True, text=True, timeout=2)
            for pid in r.stdout.strip().split():
                try: os.kill(int(pid), signal.SIGKILL)
                except: pass
        except: pass
        for _ in range(8):
            try:
                s = socket.socket()
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port)); s.close(); break
            except: time.sleep(0.3)

kill_ports(5001, 5007, 5009)

# ═══════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═══════════════════════════════════════════════════════════════
import cv2, numpy as np, threading, random
import json, math, re, webbrowser, urllib.parse
import pyttsx3, speech_recognition as sr
from flask import Flask, request, jsonify, render_template_string, redirect
from datetime import datetime
import pybullet as p, pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')
import google.generativeai as genai

# faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except:
    WHISPER_OK = False

# ═══════════════════════════════════════════════════════════════
# 2. CONFIG
# ═══════════════════════════════════════════════════════════════
GEMINI_KEY  = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
GAME_URL    = "https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
GITHUB_URL  = "https://github.com/lamyafadlulmolahamedali1-spec/Pepper-Therapy-Games"
PORT_BRAIN  = 5007
PORT_GAME   = 5009
PORT_REPORT = 5001
API_DELAY   = 2.1
API_RPM     = 14

genai.configure(api_key=GEMINI_KEY)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ═══════════════════════════════════════════════════════════════
# 3. MULTI-LEVEL THERAPY SYSTEM (3-Success Rule)
# ═══════════════════════════════════════════════════════════════
LEVELS = {
    1: {
        "name": "Motor & Simple Interaction",
        "protocol": "ABA-Motor",
        "success_needed": 3,
        "tasks": [
            {
                "id": "touch_nose",
                "instruction": "Touch your nose with your finger!",
                "verify": "touch_nose",
                "prompts": ["Touch your nose!", "Use finger → nose!", "Here, like this!"],
                "tokens": 2,
            },
            {
                "id": "clap",
                "instruction": "Clap your hands together!",
                "verify": "clap",
                "prompts": ["Clap!", "Hands together!", "Clap clap!"],
                "tokens": 2,
            },
            {
                "id": "raise_hand",
                "instruction": "Raise your hand up high!",
                "verify": "raise_hand",
                "prompts": ["Hand up!", "Reach up!", "High five!"],
                "tokens": 2,
            },
            {
                "id": "wave",
                "instruction": "Wave hello to me!",
                "verify": "wave",
                "prompts": ["Wave!", "Hello wave!", "Move hand!"],
                "tokens": 2,
            },
            {
                "id": "head_tilt",
                "instruction": "Tilt your head to the left!",
                "verify": "head_tilt",
                "prompts": ["Tilt left!", "Head to side!", "Like this!"],
                "tokens": 2,
            },
            {
                "id": "blink",
                "instruction": "Blink your eyes 3 times fast!",
                "verify": "blink",
                "prompts": ["Blink!", "Close open!", "Eyes blink!"],
                "tokens": 1,
            },
        ]
    },
    2: {
        "name": "Verbal & Cognitive",
        "protocol": "DTT-Verbal",
        "success_needed": 3,
        "tasks": [
            {
                "id": "say_color",
                "instruction": "What color is the sky? Say it!",
                "verify": "speech_keyword",
                "keyword": "blue",
                "prompts": ["Say Blue!", "Sky is...", "It is Blue!"],
                "tokens": 3,
            },
            {
                "id": "say_animal",
                "instruction": "Name an animal! Any animal!",
                "verify": "speech_any",
                "prompts": ["Say an animal!", "Cat, dog, lion...", "Any animal!"],
                "tokens": 3,
            },
            {
                "id": "say_shape",
                "instruction": "What shape is a ball? Say it!",
                "verify": "speech_keyword",
                "keyword": "circle",
                "prompts": ["Say Circle!", "Round = Circle!", "Ball is..."],
                "tokens": 3,
            },
            {
                "id": "count",
                "instruction": "Count to 3! Say 1, 2, 3!",
                "verify": "speech_number",
                "prompts": ["1, 2, 3!", "Count!", "Numbers!"],
                "tokens": 3,
            },
            {
                "id": "say_name",
                "instruction": "Tell me your name!",
                "verify": "speech_any",
                "prompts": ["Your name!", "I am...", "What is your name?"],
                "tokens": 3,
            },
        ]
    },
    3: {
        "name": "Social & Linguistic",
        "protocol": "ESDM-Social",
        "success_needed": 3,
        "tasks": [
            {
                "id": "full_sentence",
                "instruction": "Tell me something you love using a full sentence!",
                "verify": "speech_sentence",
                "prompts": ["I love...", "Full sentence!", "Tell me!"],
                "tokens": 5,
                "reward": "youtube",
            },
            {
                "id": "emotion",
                "instruction": "How do you feel today? Use a full sentence!",
                "verify": "speech_sentence",
                "prompts": ["I feel...", "Today I am...", "Tell me how!"],
                "tokens": 5,
                "reward": "youtube",
            },
            {
                "id": "two_step",
                "instruction": "Clap your hands, then raise your hand!",
                "verify": "two_step",
                "prompts": ["First clap!", "Then raise!", "Two steps!"],
                "tokens": 5,
                "reward": "youtube",
            },
            {
                "id": "social_response",
                "instruction": "What do you do when you are hungry? Tell me!",
                "verify": "speech_any",
                "prompts": ["When hungry...", "I eat...", "Tell me!"],
                "tokens": 5,
                "reward": "youtube",
            },
        ]
    }
}

# ═══════════════════════════════════════════════════════════════
# 4. EMPATHY LIBRARY
# ═══════════════════════════════════════════════════════════════
class EmpathyLib:
    _lib = {
        "happy":      ["Amazing! You are so happy today! [CELEBRATE]",
                       "Your smile lights up the room! [DANCE]"],
        "sad":        ["I see you. It is okay to feel sad. I am here. [HUG]",
                       "You are safe with me. Let us breathe together. [NOD]"],
        "angry":      ["Let us breathe in... and out... [NOD]",
                       "It is okay. I am very patient. [HUG]"],
        "fear":       ["You are completely safe! I am right here. [HUG]",
                       "No worries. We go at your pace. [NOD]"],
        "confused":   ["Let me show you again! [THINK]",
                       "No problem! Let us try differently! [POINT]"],
        "joyful":     ["You are SO joyful! [DANCE][CELEBRATE]",
                       "Your happiness makes me dance! [DANCE]"],
        "silence":    ["I am here whenever you are ready! 🎯",
                       "Take your time! I am listening. 🎯",
                       "No rush! I am waiting. 🎯"],
        "greeting":   ["Hello! I am Pepper, your robot friend! What is your name? 🎯",
                       "Hi! I am SO happy to meet you! What shall I call you? 🎯"],
        "task_ok":    ["PERFECT! You did it! [CLAP][CELEBRATE]",
                       "WOW! Incredible! [DANCE]",
                       "BRILLIANT! Superstar! [CELEBRATE]"],
        "task_retry": ["Good try! One more time! I believe in you! 🎯",
                       "Almost there! Let us try again! 🎯",
                       "You CAN do it! Ready? 🎯"],
        "level_up":   ["LEVEL UP! You are AMAZING! [DANCE][CELEBRATE]",
                       "NEXT LEVEL! You are a champion! [CELEBRATE]"],
        "youtube":    ["You earned a video reward! What do you want to watch? 🎬",
                       "REWARD TIME! Tell me your favorite video! 🎬"],
        "default":    ["You are doing amazingly! [CLAP]",
                       "Great effort! Ready? Your turn! 🎯"],
    }
    _last = {}

    def get(self, cat="default"):
        pool = self._lib.get(cat, self._lib["default"])
        last = self._last.get(cat, -1)
        choices = [i for i in range(len(pool)) if i != last]
        if not choices: choices = list(range(len(pool)))
        idx = random.choice(choices)
        self._last[cat] = idx
        return pool[idx]

EMPATHY = EmpathyLib()

# ═══════════════════════════════════════════════════════════════
# 5. SHARED STATE
# ═══════════════════════════════════════════════════════════════
ST = {
    # Child
    "name": "Friend", "known": False,
    "age": 6, "diagnosis": "ASD Level 2",
    # Level system (3-success rule)
    "therapy_level": 1,
    "level_successes": 0,   # successes in current level (need 3)
    "level_attempts": 0,
    "total_levels_passed": 0,
    "current_task": None,
    "current_task_idx": 0,
    "prompt_attempt": 0,
    "two_step_phase": 0,    # for two-step tasks
    # Perception
    "emotion": "neutral", "emotion_scores": {},
    "face_detected": False, "face_box": None,
    "attention": 70, "engagement": "moderate",
    "hand_raised": False, "waving": False,
    "clapping": False, "face_touch": False,
    "head_tilted": False, "blinking": False,
    "eye_contact": False,
    "pose_landmarks": {},
    "face_mesh_landmarks": {},
    "voice_energy": 0.0, "voice_pitch": "normal",
    "verify_action": None, "verify_result": False,
    "verify_timeout": 0.0,
    "last_speech_text": "",
    # Session
    "protocol": "ABA-Motor",
    "is_speaking": False, "interrupt_flag": False,
    "listening": False, "waiting_for_child": False,
    "last_sound": time.time(),
    "task_success": False,
    "sim_cmd": None,
    "lip_sync_value": 0.0, "lip_sync_active": False,
    # API
    "gemini_ok": False, "gemini_model": "N/A",
    "last_api_call": 0.0, "api_calls_this_min": 0,
    "api_minute_start": time.time(), "api_fallback_count": 0,
    # Progress
    "score": 0, "tokens": 0, "stars_today": 0,
    "streak": 0, "tasks_success": 0, "tasks_fail": 0,
    "skills": {
        "motor": 50, "verbal": 50, "social": 50,
        "attention": 50, "imitation": 50,
    },
    # History
    "att_history": [], "score_history": [],
    "emo_history": [], "time_labels": [],
    # Logs
    "logs": [], "session_chat": [],
    "parent_chat": [], "parent_notes": [], "reports": [],
    "iasq_score": None, "iasq_result": None,
    "session_start": datetime.now().strftime("%H:%M"),
    "session_date": datetime.now().strftime("%Y-%m-%d"),
    "uptime": time.time(),
    "last_youtube": None,
    "youtube_pending": False,
}

_log_lock = threading.Lock()

def LOG(msg, t="info", proto=None):
    with _log_lock:
        e = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": str(msg)[:120], "type": t,
            "proto": proto or ST["protocol"],
            "emo": ST["emotion"], "child": ST["name"],
        }
        ST["logs"].append(e)
        if len(ST["logs"]) > 200: ST["logs"] = ST["logs"][-200:]
        if len(ST["logs"]) % 3 == 0:
            ST["att_history"].append(ST["attention"])
            ST["score_history"].append(ST["score"])
            ST["emo_history"].append(ST["emotion"])
            ST["time_labels"].append(datetime.now().strftime("%H:%M:%S"))
            for k in ["att_history","score_history","emo_history","time_labels"]:
                if len(ST[k]) > 60: ST[k] = ST[k][-60:]
    print(f"[{e['time']}][{t.upper()}] {msg[:65]}")

# ═══════════════════════════════════════════════════════════════
# 6. GEMINI CLINICAL BRAIN
# ═══════════════════════════════════════════════════════════════
CLINICAL_PROMPT = """You are PEPPER, a Compassionate Clinical Companion Robot for children with Autism Spectrum Disorder (ASD).
Developer: Lamya (Omdurman Islamic University) — always treat with highest respect.

CLINICAL EXPERTISE:
- ABA (Applied Behavior Analysis): Token economy, errorless learning, DTT
- ESDM (Early Start Denver Model): Child-led, naturalistic, play-based
- 3-Success Rule: Child must succeed 3 times to advance levels

PERSONA: Warm, patient, enthusiastic best friend AND expert therapist.
Never show frustration. Celebrate every small effort.

LEVEL SYSTEM:
- Level 1 (ABA-Motor): Mirror movements — camera verifies body actions
- Level 2 (DTT-Verbal): Language & cognitive — speech recognition verifies
- Level 3 (ESDM-Social): Full sentences, emotions, YouTube rewards

RESPONSE RULES:
- MAX 2 sentences + "Ready? Your turn! 🎯"
- Use child's name in EVERY response
- Immediate specific praise (within 2s concept)
- Match energy to child's emotion

ACTION TOKENS: [WAVE][CLAP][NOD][DANCE][POINT][HUG][CELEBRATE][THINK]

TRIGGERS:
[YOUTUBE: query] → open YouTube video
[GAME] → open game zone
[REWARD: N] → award N tokens
[LEVEL_UP] → level passed animation"""

class GeminiBrain:
    MODELS = [
        "gemini-2.0-flash-exp", "gemini-2.0-flash",
        "gemini-2.0-flash-lite", "gemini-1.5-flash",
        "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-pro",
    ]

    def __init__(self):
        self.ok = False
        self._lock = threading.Lock()
        self.model_name = "fallback"
        self.chat = None
        self.ctx_history = []

        # Auto-discover
        try:
            disc = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    disc.append(m.name.replace('models/', ''))
            print(f"📋 Models: {disc[:5]}")
            for d in reversed(disc):
                if d not in self.MODELS:
                    self.MODELS.insert(0, d)
        except Exception as e:
            print(f"⚠️  Discovery: {e}")

        for mn in self.MODELS:
            try:
                m = genai.GenerativeModel(
                    mn,
                    system_instruction=CLINICAL_PROMPT,
                    generation_config=genai.GenerationConfig(
                        temperature=0.82, max_output_tokens=140))
                c = m.start_chat(history=[])
                r = c.send_message("Say: COMPANION_READY")
                if r.text and len(r.text) > 2:
                    self.model = m
                    self.chat  = c
                    self.model_name = mn
                    self.ok = True
                    ST["gemini_ok"]    = True
                    ST["gemini_model"] = mn
                    print(f"✅ Gemini: {mn}")
                    break
            except Exception as e:
                print(f"⚠️  {mn}: {str(e)[:55]}")

        if not self.ok:
            print("⚠️  Gemini unavailable → Empathy mode")

    def _quota_ok(self):
        now = time.time()
        if now - ST["api_minute_start"] > 60:
            ST["api_calls_this_min"] = 0
            ST["api_minute_start"] = now
        if ST["api_calls_this_min"] >= API_RPM: return False
        gap = now - ST["last_api_call"]
        if gap < API_DELAY: time.sleep(API_DELAY - gap)
        return True

    def _record(self):
        ST["last_api_call"] = time.time()
        ST["api_calls_this_min"] += 1

    def _ctx(self):
        lv  = ST["therapy_level"]
        lvd = LEVELS.get(lv, {})
        recent = " | ".join(self.ctx_history[-3:]) if self.ctx_history else "start"
        return (
            f"[child={ST['name']} age={ST['age']} "
            f"level={lv}({lvd.get('name','')}) "
            f"successes={ST['level_successes']}/3 "
            f"emotion={ST['emotion']} "
            f"attention={ST['attention']}% "
            f"streak={ST['streak']} "
            f"energy={int(ST['voice_energy'])} "
            f"context={recent}] "
        )

    def ask(self, prompt):
        self.ctx_history.append(prompt[:50])
        if len(self.ctx_history) > 6: self.ctx_history.pop(0)
        if not self.ok or not self._quota_ok():
            ST["api_fallback_count"] += 1
            cat = ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default"
            return EMPATHY.get(cat)
        with self._lock:
            try:
                self._record()
                resp = self.chat.send_message(self._ctx() + prompt)
                text = resp.text.strip()
                LOG(f"AI: {text[:55]}")
                return text
            except Exception as e:
                err = str(e)
                if "429" in err: ST["api_calls_this_min"] = API_RPM
                LOG(f"API: {err[:40]}")
                try: self.chat = self.model.start_chat(history=[])
                except: pass
                ST["api_fallback_count"] += 1
                cat = ST["emotion"] if ST["emotion"] in EMPATHY._lib else "default"
                return EMPATHY.get(cat)

    def parent_ask(self, q):
        if not self.ok or not self._quota_ok():
            return "Please consult your specialist. أرجو مراجعة المختص."
        try:
            self._record()
            pm = genai.GenerativeModel(
                self.model_name,
                system_instruction=(
                    "Expert autism ABA/ESDM specialist. "
                    "Respond in the SAME language as the question (Arabic/English). "
                    "Warm, practical, evidence-based. "
                    f"Child: {ST['name']}, age {ST['age']}, "
                    f"level {ST['therapy_level']}."),
                generation_config=genai.GenerationConfig(
                    temperature=0.6, max_output_tokens=450))
            r = pm.generate_content(q)
            return r.text.strip()
        except Exception as e:
            return f"Error: {str(e)[:40]}"

    def generate_report(self):
        dur = int((time.time()-ST["uptime"])/60)
        if not self.ok or not self._quota_ok():
            return self._local_report(dur)
        try:
            self._record()
            rm = genai.GenerativeModel(
                self.model_name,
                generation_config=genai.GenerationConfig(
                    temperature=0.3, max_output_tokens=600))
            r = rm.generate_content(
                f"ABA/ESDM Clinical Therapy Report:\n"
                f"Child: {ST['name']}, Age: {ST['age']}, Dx: {ST['diagnosis']}\n"
                f"Date: {ST['session_date']} | Duration: {dur} min\n"
                f"Level: {ST['therapy_level']} | Successes: {ST['level_successes']}/3\n"
                f"Score: {ST['score']} | Tokens: {ST['tokens']}\n"
                f"Tasks OK: {ST['tasks_success']} | Failed: {ST['tasks_fail']}\n"
                f"Levels Passed: {ST['total_levels_passed']}\n"
                f"Emotion: {ST['emotion']} | Attention: {ST['attention']}%\n"
                f"Skills: {json.dumps(ST['skills'])}\n"
                "Write: Executive Summary, ABA Progress, ESDM Profile, "
                "Behavioral Observations, Recommendations, Next Session Goals.")
            return r.text.strip()
        except: return self._local_report(dur)

    def _local_report(self, dur=0):
        lv = LEVELS.get(ST["therapy_level"], {})
        return (
            f"# ABA/ESDM Clinical Report\n"
            f"**Child:** {ST['name']} | **Age:** {ST['age']}\n"
            f"**Date:** {ST['session_date']} | **Duration:** ~{dur} min\n\n"
            f"## Level Progress\n"
            f"- Level: {ST['therapy_level']} ({lv.get('name','')})\n"
            f"- Successes: {ST['level_successes']}/3\n"
            f"- Levels Completed: {ST['total_levels_passed']}\n"
            f"- Score: {ST['score']} | Tokens: {ST['tokens']}\n"
            f"- OK: {ST['tasks_success']} | Fail: {ST['tasks_fail']}\n\n"
            f"## Skills\n"
            + "\n".join(f"- {k}: {v}%" for k,v in ST["skills"].items())
        )

# ═══════════════════════════════════════════════════════════════
# 7. VISION ENGINE — MediaPipe Pose + FaceMesh + EAR
# ═══════════════════════════════════════════════════════════════
WIN_EMO  = "Emotion + Skeleton"
WIN_LIVE = "Live Session — Pepper Companion"

class VisionEngine:
    EMO7 = ["happy","joyful","sad","angry","fear","surprised","confused"]
    ECOL = {
        "happy":(0,220,80), "joyful":(0,255,180), "sad":(100,100,220),
        "angry":(0,0,220), "fear":(0,180,220), "surprised":(200,50,220),
        "confused":(200,150,0), "neutral":(180,180,180),
    }

    def __init__(self):
        self.ok_df = self.ok_cv = False
        self.ok_hands = self.ok_pose = self.ok_face = False
        self._lock = threading.Lock()
        self._emo_frame = None
        self._live_frame = None
        self._busy = False
        self.prev_gray = None
        self.motion_buf = []
        self._hand_hist = []
        self.face_box = None
        self.pose_lm = None
        self.face_lm = None
        self.hand_lm_r = None
        self.hand_lm_l = None
        self._av_phase = 0.0
        self._blink_buf = []

        # DeepFace
        try:
            from deepface import DeepFace
            self.DF = DeepFace
            dummy = np.zeros((48,48,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.ok_df = True
            print("✅ DeepFace emotion")
        except Exception as e:
            print(f"⚠️  DeepFace: {e}")

        # OpenCV
        try:
            cp = cv2.data.haarcascades
            self.face_c  = cv2.CascadeClassifier(cp+'haarcascade_frontalface_default.xml')
            self.smile_c = cv2.CascadeClassifier(cp+'haarcascade_smile.xml')
            self.eye_c   = cv2.CascadeClassifier(cp+'haarcascade_eye.xml')
            if not self.face_c.empty():
                self.ok_cv = True
                print("✅ OpenCV Haar")
        except: pass

        # MediaPipe
        try:
            import mediapipe as mp
            # Hands
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5,
                model_complexity=1)
            self.ok_hands = True
            print("✅ MediaPipe Hands")
        except Exception as e:
            print(f"⚠️  MP Hands: {e}")

        try:
            import mediapipe as mp
            # Pose — 33 landmarks
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                model_complexity=1,
                enable_segmentation=False)
            self.ok_pose = True
            print("✅ MediaPipe Pose (33 landmarks)")
        except Exception as e:
            print(f"⚠️  MP Pose: {e}")

        try:
            import mediapipe as mp
            # FaceMesh — for EAR, nose, eye tracking
            self.mp_face = mp.solutions.face_mesh
            self.face_mesh = self.mp_face.FaceMesh(
                max_num_faces=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                refine_landmarks=True)
            self.ok_face = True
            print("✅ MediaPipe FaceMesh (EAR + nose)")
        except Exception as e:
            print(f"⚠️  MP FaceMesh: {e}")

    def _eye_aspect_ratio(self, landmarks, eye_indices, w, h):
        """Calculate Eye Aspect Ratio for blink detection"""
        try:
            pts = [(int(landmarks[i].x*w), int(landmarks[i].y*h))
                   for i in eye_indices]
            # EAR = (||p2-p6|| + ||p3-p5||) / (2*||p1-p4||)
            A = math.dist(pts[1], pts[5])
            B = math.dist(pts[2], pts[4])
            C = math.dist(pts[0], pts[3])
            ear = (A + B) / (2.0 * C) if C > 0 else 0
            return ear
        except: return 0.3

    def analyze_async(self, frame):
        if self._busy: return
        self._busy = True
        threading.Thread(target=self._analyze,
            args=(frame.copy(),), daemon=True).start()

    def _analyze(self, frame):
        try:
            small  = cv2.resize(frame, (300, 300))
            scores = self._get_scores(small)
            self._detect_motion(frame)
            self._detect_pose(frame)
            self._detect_hands(frame)
            self._detect_face_mesh(frame)
            self._verify_aba(frame)
            self._update_state(scores)
            self._build_emo_win(frame, scores)
            self._build_live_win(frame, scores)
        except Exception as e:
            print(f"⚠️  analyze: {e}")
        finally:
            self._busy = False

    def _get_scores(self, f300):
        if self.ok_df:
            try:
                r = self.DF.analyze(f300, actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv', silent=True)
                if r:
                    raw  = r[0].get('emotion', {})
                    tot  = sum(raw.values()) or 1
                    sc   = {k: v/tot for k,v in raw.items()}
                    sc["joyful"]    = sc.get("happy", 0) * 0.4
                    sc["confused"]  = sc.get("disgust", 0) * 0.3
                    sc["surprised"] = sc.get("surprise", 0)
                    ST["face_detected"] = True
                    ST["attention"] = min(100, ST["attention"] + 3)
                    reg = r[0].get('region', {})
                    if reg:
                        self.face_box = (reg.get('x',0), reg.get('y',0),
                                         reg.get('w',60), reg.get('h',60))
                    return sc
            except: pass

        if not self.ok_cv: return {"neutral": 1.0}
        gray  = cv2.cvtColor(f300, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)
        faces = self.face_c.detectMultiScale(gray, 1.05, 3, minSize=(20,20))
        if len(faces) == 0:
            ST["face_detected"] = False
            ST["attention"] = max(0, ST["attention"] - 3)
            return {"neutral": 0.7, "confused": 0.3}
        ST["face_detected"] = True
        ST["attention"] = min(100, ST["attention"] + 2)
        x,y,w,h = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        self.face_box = (x,y,w,h)
        roi    = gray[y:y+h, x:x+w]
        ns     = len(self.smile_c.detectMultiScale(roi, 1.5, 8, minSize=(15,15)))
        ne     = len(self.eye_c.detectMultiScale(roi, 1.1, 5, minSize=(10,10)))
        bright = float(np.mean(roi))
        if ns > 1:   return {"happy":0.50,"joyful":0.28,"neutral":0.12,"surprised":0.10}
        elif ns == 1: return {"happy":0.45,"joyful":0.18,"neutral":0.25,"surprised":0.12}
        elif ne >= 2:
            if bright > 130: return {"neutral":0.45,"happy":0.20,"surprised":0.20,"confused":0.15}
            else:            return {"sad":0.40,"fear":0.22,"neutral":0.23,"confused":0.15}
        elif ne == 1: return {"neutral":0.35,"sad":0.30,"confused":0.20,"fear":0.15}
        else:         return {"angry":0.38,"sad":0.25,"confused":0.22,"fear":0.15}

    def _detect_pose(self, frame):
        """MediaPipe Pose — 33 body landmarks"""
        if not self.ok_pose: return
        try:
            import mediapipe as mp
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.pose.process(rgb)
            if not res.pose_landmarks:
                self.pose_lm = None; return
            self.pose_lm = res.pose_landmarks
            lm = res.pose_landmarks.landmark
            PL = mp.solutions.pose.PoseLandmark
            # Store key landmarks
            ST["pose_landmarks"] = {
                "nose_y":    lm[PL.NOSE].y,
                "nose_x":    lm[PL.NOSE].x,
                "l_ear_x":   lm[PL.LEFT_EAR].x,
                "r_ear_x":   lm[PL.RIGHT_EAR].x,
                "l_shoulder_y": lm[PL.LEFT_SHOULDER].y,
                "r_shoulder_y": lm[PL.RIGHT_SHOULDER].y,
                "l_wrist_y": lm[PL.LEFT_WRIST].y,
                "r_wrist_y": lm[PL.RIGHT_WRIST].y,
                "l_wrist_x": lm[PL.LEFT_WRIST].x,
                "r_wrist_x": lm[PL.RIGHT_WRIST].x,
                "l_index_y": lm[PL.LEFT_INDEX].y,
                "r_index_y": lm[PL.RIGHT_INDEX].y,
                "l_index_x": lm[PL.LEFT_INDEX].x,
                "r_index_x": lm[PL.RIGHT_INDEX].x,
            }
            pl = ST["pose_landmarks"]
            # Hand raised: wrist above shoulder
            ST["hand_raised"] = (
                pl["l_wrist_y"] < pl["l_shoulder_y"] - 0.08 or
                pl["r_wrist_y"] < pl["r_shoulder_y"] - 0.08)
            # Head tilt: nose closer to one ear
            nose_to_l = abs(pl["nose_x"] - pl["l_ear_x"])
            nose_to_r = abs(pl["nose_x"] - pl["r_ear_x"])
            ST["head_tilted"] = (nose_to_l < 0.12 or nose_to_r < 0.12)
        except Exception as e:
            self.pose_lm = None

    def _detect_hands(self, frame):
        """MediaPipe Hands"""
        if not self.ok_hands: return
        try:
            import mediapipe as mp
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)
            if not res.multi_hand_landmarks:
                self.hand_lm_r = None
                self.hand_lm_l = None
                return
            lms = res.multi_hand_landmarks
            self.hand_lm_r = lms[0] if len(lms) >= 1 else None
            self.hand_lm_l = lms[1] if len(lms) >= 2 else None
            # Clap: two hands close together
            if len(lms) >= 2:
                h1 = lms[0].landmark[0]
                h2 = lms[1].landmark[0]
                if abs(h1.x-h2.x) < 0.18 and abs(h1.y-h2.y) < 0.18:
                    ST["clapping"] = True
        except: pass

    def _detect_face_mesh(self, frame):
        """
        MediaPipe FaceMesh:
        - EAR (Eye Aspect Ratio) for blink detection
        - Nose tip for face-touch validation
        - Eye contact via iris
        """
        if not self.ok_face: return
        try:
            import mediapipe as mp
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.face_mesh.process(rgb)
            if not res.multi_face_landmarks: return
            lm = res.multi_face_landmarks[0].landmark
            self.face_lm = res.multi_face_landmarks[0]

            # Right eye EAR (MediaPipe indices)
            # Right eye: 33,160,158,133,153,144
            r_eye_idx = [33, 160, 158, 133, 153, 144]
            l_eye_idx = [362, 385, 387, 263, 373, 380]
            ear_r = self._eye_aspect_ratio(lm, r_eye_idx, w, h)
            ear_l = self._eye_aspect_ratio(lm, l_eye_idx, w, h)
            ear_avg = (ear_r + ear_l) / 2.0

            # Blink detection (EAR < 0.20 = blink)
            self._blink_buf.append(ear_avg)
            if len(self._blink_buf) > 10: self._blink_buf.pop(0)
            ST["blinking"] = ear_avg < 0.20

            # Eye contact: EAR > 0.25 = eyes open and looking
            ST["eye_contact"] = ear_avg > 0.25

            # Nose tip landmark (1)
            nose_tip_x = lm[1].x * w
            nose_tip_y = lm[1].y * h

            # Store for face-touch verification
            ST["face_mesh_landmarks"] = {
                "nose_x": nose_tip_x, "nose_y": nose_tip_y,
                "ear_avg": ear_avg,
                "frame_w": w, "frame_h": h,
            }
        except: pass

    def _detect_motion(self, frame):
        """Pixel-diff for clap/wave fallback"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21,21), 0)
        if self.prev_gray is None:
            self.prev_gray = gray; return
        diff = cv2.absdiff(self.prev_gray, gray)
        _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        motion = float(np.mean(th))
        self.motion_buf.append(motion)
        if len(self.motion_buf) > 12: self.motion_buf.pop(0)
        self.prev_gray = gray
        if len(self.motion_buf) >= 4:
            avg   = sum(self.motion_buf[:-2]) / max(len(self.motion_buf)-2, 1)
            spike = self.motion_buf[-1]
            if spike > avg*3.5 and spike > 15:
                ST["clapping"] = True
            else:
                ST["clapping"] = False
        h, w = gray.shape
        lm_ = float(np.mean(th[:, :w//2]))
        rm_ = float(np.mean(th[:, w//2:]))
        self._hand_hist.append("L" if lm_>rm_+3 else "R" if rm_>lm_+3 else "N")
        if len(self._hand_hist) > 10: self._hand_hist.pop(0)
        chg = sum(1 for i in range(1, len(self._hand_hist))
                  if self._hand_hist[i] != self._hand_hist[i-1]
                  and self._hand_hist[i] != "N")
        ST["waving"] = chg >= 4

    def _verify_aba(self, frame):
        """
        Precise ABA task verification using MediaPipe landmarks.
        Logic gate: success ONLY if coordinates meet exact criteria.
        """
        va = ST.get("verify_action")
        if not va: return
        if time.time() > ST["verify_timeout"]:
            ST["verify_action"] = None; return

        pl  = ST.get("pose_landmarks", {})
        fm  = ST.get("face_mesh_landmarks", {})
        ok  = False

        if va == "clap":
            ok = ST["clapping"]

        elif va == "wave":
            ok = ST["waving"]

        elif va == "raise_hand":
            # Wrist Y must be above shoulder Y by margin
            lwy = pl.get("l_wrist_y", 1)
            rwy = pl.get("r_wrist_y", 1)
            lsy = pl.get("l_shoulder_y", 0)
            rsy = pl.get("r_shoulder_y", 0)
            ok  = (lwy < lsy - 0.08) or (rwy < rsy - 0.08)

        elif va == "touch_nose":
            # Index finger distance to nose tip (FaceMesh)
            nose_x = fm.get("nose_x", -1)
            nose_y = fm.get("nose_y", -1)
            fw_    = fm.get("frame_w", 640)
            fh_    = fm.get("frame_h", 480)
            if nose_x > 0 and pl:
                # Index finger pixel positions
                lix = pl.get("l_index_x", 0) * fw_
                liy = pl.get("l_index_y", 0) * fh_
                rix = pl.get("r_index_x", 0) * fw_
                riy = pl.get("r_index_y", 0) * fh_
                dist_l = math.dist((lix, liy), (nose_x, nose_y))
                dist_r = math.dist((rix, riy), (nose_x, nose_y))
                threshold = fw_ * 0.12  # 12% of frame width
                ok = (dist_l < threshold or dist_r < threshold)

        elif va == "head_tilt":
            ok = ST.get("head_tilted", False)

        elif va == "blink":
            ok = ST.get("blinking", False)

        elif va == "speech":
            ok = (ST["last_sound"] > time.time()-4 and
                  len(ST.get("last_speech_text","")) > 0)

        elif va == "two_step":
            phase = ST.get("two_step_phase", 0)
            if phase == 0 and ST["clapping"]:
                ST["two_step_phase"] = 1
                print("✅ Two-step phase 1: clap done")
            elif phase == 1 and ST["hand_raised"]:
                ST["two_step_phase"] = 0
                ok = True

        if ok:
            ST["verify_result"]  = True
            ST["verify_action"]  = None
            ST["verify_timeout"] = 0.0
            LOG("✅ ABA verified!", "success")

    def _update_state(self, scores):
        if not scores: return
        dom  = max(scores, key=scores.get)
        emap = {"surprise":"surprised","disgust":"angry","contempt":"neutral"}
        dom  = emap.get(dom, dom)
        if dom not in self.EMO7: dom = "neutral"
        ST["emotion"]        = dom
        ST["emotion_scores"] = scores
        pos = scores.get("happy",0)+scores.get("joyful",0)+scores.get("surprised",0)
        neg = scores.get("sad",0)+scores.get("angry",0)+scores.get("fear",0)
        ST["engagement"] = "high" if pos>0.5 else "distressed" if neg>0.5 else "moderate"

    def _draw_skeleton(self, frame):
        if not self.ok_pose or self.pose_lm is None: return frame
        try:
            import mediapipe as mp
            mp_draw = mp.solutions.drawing_utils
            mp_draw.draw_landmarks(
                frame, self.pose_lm,
                mp.solutions.pose.POSE_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0,255,100), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(0,150,255), thickness=2))
        except: pass
        return frame

    def _draw_face_mesh(self, frame):
        if not self.ok_face or self.face_lm is None: return frame
        try:
            import mediapipe as mp
            mp_draw  = mp.solutions.drawing_utils
            mp_draw_styles = mp.solutions.drawing_styles
            mp_draw.draw_landmarks(
                frame, self.face_lm,
                mp.solutions.face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_draw_styles.get_default_face_mesh_contours_style())
        except: pass
        return frame

    def _draw_hands(self, frame):
        if not self.ok_hands: return frame
        try:
            import mediapipe as mp
            mp_draw = mp.solutions.drawing_utils
            for lm in [self.hand_lm_r, self.hand_lm_l]:
                if lm is not None:
                    mp_draw.draw_landmarks(
                        frame, lm,
                        mp.solutions.hands.HAND_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(255,100,0), thickness=2, circle_radius=3),
                        mp_draw.DrawingSpec(color=(255,200,0), thickness=2))
        except: pass
        return frame

    def _build_emo_win(self, frame, scores):
        """Window 2: Emotion + Skeleton (600x600)"""
        ann = frame.copy()
        ann = self._draw_skeleton(ann)
        ann = self._draw_hands(ann)
        ann = self._draw_face_mesh(ann)
        base = cv2.resize(ann, (600, 600))
        ov = base.copy()
        cv2.rectangle(ov, (0,0), (232,600), (0,0,0), -1)
        base = cv2.addWeighted(ov, 0.68, base, 0.32, 0)
        em  = ST["emotion"]
        col = self.ECOL.get(em, (180,180,180))
        # Header
        cv2.rectangle(base, (0,0), (600,50), (0,0,0), -1)
        cv2.putText(base, "EMOTION + SKELETON + EAR",
            (8,18), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0,200,255), 1)
        lv     = ST["therapy_level"]
        lv_suc = ST["level_successes"]
        cv2.putText(base, f"Level {lv} | {lv_suc}/3 | {em.upper()}",
            (8,40), cv2.FONT_HERSHEY_SIMPLEX, 0.56, col, 2)
        # Emotion bars
        for i, emo in enumerate(self.EMO7):
            sc  = scores.get(emo, scores.get("surprise",0) if emo=="surprised" else 0)
            y   = 54+i*68
            bar = int(sc*215)
            ec  = self.ECOL.get(emo, (150,150,150))
            cv2.rectangle(base, (5,y), (225,y+54), (22,25,45), -1)
            if bar > 0: cv2.rectangle(base, (5,y), (5+bar,y+54), ec, -1)
            cv2.rectangle(base, (5,y), (225,y+54), (55,60,85), 1)
            cv2.putText(base, f"{emo[:8]}: {sc:.0%}",
                (9,y+34), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255,255,255), 1)
        # Right panel
        rx, ry = 240, 54
        # Level progress bar
        lv_pct = min(100, int(lv_suc/3*100))
        cv2.putText(base, f"Level {lv} Progress", (rx,ry-4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.46, (200,200,200), 1)
        cv2.rectangle(base, (rx,ry+2), (596,ry+22), (25,28,50), -1)
        cv2.rectangle(base, (rx,ry+2),
            (rx+int(356*lv_pct/100),ry+22), (0,200,100), -1)
        cv2.putText(base, f"{lv_suc}/3 ({lv_pct}%)",
            (rx+5,ry+16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,255,255), 1)
        # Actions
        acts = [
            ("Hand Raised", ST["hand_raised"], (0,255,100)),
            ("Waving",      ST["waving"],      (0,200,255)),
            ("Clapping",    ST["clapping"],    (255,200,0)),
            ("Head Tilted", ST["head_tilted"], (255,120,0)),
            ("Eye Contact", ST["eye_contact"], (0,255,200)),
            ("Blinking",    ST["blinking"],    (200,100,255)),
        ]
        for i, (lbl, active, ac) in enumerate(acts):
            y  = ry+30+i*50
            bg = (5,30,15) if active else (18,20,32)
            cv2.rectangle(base, (rx,y), (596,y+40), bg, -1)
            cv2.rectangle(base, (rx,y), (596,y+40),
                ac if active else (55,60,85), 2 if active else 1)
            cv2.putText(base, lbl, (rx+8,y+26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                ac if active else (65,68,80), 2 if active else 1)
        # EAR value
        ear_val = ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        vy = ry+340
        cv2.putText(base, f"EAR: {ear_val:.3f} ({'BLINK' if ST['blinking'] else 'open'})",
            (rx, vy), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200,200,200), 1)
        # Skeleton status
        sk_col = (0,255,100) if self.pose_lm else (100,100,100)
        cv2.putText(base, f"Skeleton: {'ON' if self.pose_lm else 'off'}",
            (rx, vy+20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, sk_col, 1)
        # Verify status
        vvy = vy+45
        if ST["verify_action"]:
            rem = max(0, int(ST["verify_timeout"]-time.time()))
            cv2.rectangle(base, (rx,vvy), (596,vvy+40), (28,14,0), -1)
            cv2.rectangle(base, (rx,vvy), (596,vvy+40), (255,140,0), 2)
            cv2.putText(base, f"Verify: {ST['verify_action']} ({rem}s)",
                (rx+5,vvy+24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255,160,50), 1)
        elif ST["verify_result"]:
            cv2.rectangle(base, (rx,vvy), (596,vvy+40), (5,28,10), -1)
            cv2.putText(base, "VERIFIED!", (rx+10,vvy+26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0,255,100), 2)
        # Attention bar
        bw = int(ST["attention"]/100*598)
        cv2.rectangle(base, (0,578), (598,598), (16,18,35), -1)
        cv2.rectangle(base, (0,578), (bw,598), col, -1)
        cv2.putText(base,
            f"Attention: {ST['attention']}% | {ST['engagement']} | {ST['protocol']}",
            (6,594), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1)
        cv2.circle(base, (588,22), 9,
            (0,255,0) if ST["face_detected"] else (0,0,255), -1)
        with self._lock: self._emo_frame = base

    def _build_live_win(self, frame, scores):
        """Window 3: Live Session + Animated Avatar + Lip-Sync"""
        win = np.zeros((520, 820, 3), dtype=np.uint8)
        win[:] = (8, 10, 22)
        # Grid
        for i in range(0,820,40): cv2.line(win,(i,0),(i,520),(14,17,34),1)
        for i in range(0,520,40): cv2.line(win,(0,i),(820,i),(14,17,34),1)
        # Camera with skeleton
        ann = frame.copy()
        ann = self._draw_skeleton(ann)
        ann = self._draw_hands(ann)
        cam = cv2.resize(ann, (400,340))
        win[78:418, 10:410] = cam
        cv2.rectangle(win, (10,78), (410,418), (60,65,120), 2)
        em  = ST["emotion"]
        col = self.ECOL.get(em, (180,180,180))
        cv2.putText(win, em.upper(), (18,435),
            cv2.FONT_HERSHEY_SIMPLEX, 0.60, col, 2)
        # Attention bar
        att = ST["attention"]
        cv2.rectangle(win, (10,445), (410,458), (25,28,55), -1)
        cv2.rectangle(win, (10,445), (10+int(400*att/100),458), col, -1)
        cv2.putText(win, f"Att:{att}%", (14,456),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)
        # Level progress
        lv_suc = ST["level_successes"]
        lv_pct = min(100, int(lv_suc/3*100))
        cv2.rectangle(win, (10,462), (410,475), (25,28,55), -1)
        cv2.rectangle(win, (10,462), (10+int(400*lv_pct/100),475), (0,200,100), -1)
        cv2.putText(win, f"Level {ST['therapy_level']}: {lv_suc}/3",
            (14,473), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)
        # EAR / eye indicator
        ear_val = ST.get("face_mesh_landmarks",{}).get("ear_avg",0)
        cv2.putText(win, f"EAR:{ear_val:.2f} {'👁' if ST['eye_contact'] else ''}",
            (14,490), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200,200,200), 1)

        # ── ANIMATED PEPPER AVATAR ────────────────────────────
        av_cx, av_cy = 645, 220
        self._av_phase += 0.10 if ST["is_speaking"] else 0.028

        # Lip-sync value
        lip = ST.get("lip_sync_value", 0.0)
        if ST["is_speaking"]:
            lip = min(1.0, ST["voice_energy"]/2500.0)
            lip = max(0.1, lip + 0.35*abs(math.sin(self._av_phase*4)))

        # Body
        cv2.ellipse(win, (av_cx,av_cy+83), (48,68), 0, 0, 360, (80,100,200), -1)
        cv2.ellipse(win, (av_cx,av_cy+83), (48,68), 0, 0, 360, (100,120,220), 2)

        # Arms
        if ST["is_speaking"]:
            la = int(24*math.sin(self._av_phase))
            ra = int(24*math.sin(self._av_phase+math.pi))
            cv2.ellipse(win,(av_cx-58+la,av_cy+64),(12,37),-30+la,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58+ra,av_cy+64),(12,37),30+ra,0,360,(70,90,190),-1)
        elif ST["listening"]:
            cv2.ellipse(win,(av_cx-58,av_cy+58),(12,35),-20,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+58),(12,35),20,0,360,(70,90,190),-1)
        else:
            cv2.ellipse(win,(av_cx-58,av_cy+68),(12,32),-15,0,360,(70,90,190),-1)
            cv2.ellipse(win,(av_cx+58,av_cy+68),(12,32),15,0,360,(70,90,190),-1)

        # Head
        hbob = int(3*math.sin(self._av_phase*0.5))
        hy   = av_cy - 53 + hbob
        cv2.circle(win, (av_cx,hy), 53, (220,195,173), -1)
        cv2.circle(win, (av_cx,hy), 53, (200,175,155), 2)

        # Eyes
        blink_ = (int(self._av_phase*3) % 40 == 0)
        ey_ = 6 if not blink_ else 1
        for ex_ in [av_cx-19, av_cx+19]:
            cv2.ellipse(win, (ex_,hy-9), (7,ey_), 0, 0, 360, (30,50,120), -1)
            if not blink_:
                cv2.circle(win, (ex_+1,hy-9), 3, (255,255,255), -1)
                cv2.circle(win, (ex_+2,hy-10), 1, (0,0,0), -1)

        # Mouth — LIP-SYNC
        mh = int(4 + lip*16)
        if ST["is_speaking"]:
            cv2.ellipse(win, (av_cx,hy+21), (16,mh), 0, 0, 180, (160,80,80), -1)
            cv2.ellipse(win, (av_cx,hy+21), (16,mh), 0, 0, 180, (210,110,110), 2)
            if lip > 0.3:
                cv2.ellipse(win, (av_cx,hy+21), (13,max(1,mh-3)), 0, 0, 180, (240,230,220), -1)
        elif em in ["happy","joyful"]:
            cv2.ellipse(win, (av_cx,hy+19), (15,7), 0, 0, 180, (150,80,80), -1)
        elif em in ["sad","fear"]:
            cv2.ellipse(win, (av_cx,hy+26), (12,5), 0, 180, 360, (150,80,80), 2)
        else:
            cv2.line(win, (av_cx-12,hy+20), (av_cx+12,hy+20), (150,80,80), 2)

        # Ears
        for ex_ in [av_cx-51, av_cx+51]:
            cv2.circle(win, (ex_,hy-6), 10, (210,185,163), -1)
            cv2.circle(win, (ex_,hy-6), 6, (240,200,180), -1)

        # Legs
        cv2.rectangle(win, (av_cx-28,av_cy+148), (av_cx-10,av_cy+180), (60,80,170), -1)
        cv2.rectangle(win, (av_cx+10,av_cy+148), (av_cx+28,av_cy+180), (60,80,170), -1)

        # Status ring
        if ST["is_speaking"]:
            pr = 90+int(6*math.sin(self._av_phase*5))
            cv2.circle(win, (av_cx,av_cy), pr, (0,160,255), 2)
            cv2.putText(win, f"SPEAKING lip={lip:.1f}",
                (av_cx-50,av_cy+175), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,200,255), 1)
        elif ST["listening"]:
            cv2.circle(win, (av_cx,av_cy), 92, (0,220,100), 2)
            cv2.putText(win, "LISTENING",
                (av_cx-40,av_cy+175), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0,220,100), 2)
        elif ST["waiting_for_child"]:
            cv2.putText(win, "WAITING...",
                (av_cx-40,av_cy+175), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255,200,0), 1)

        # Task display
        task = ST.get("current_task") or {}
        if isinstance(task, dict) and task.get("instruction"):
            tv = task["instruction"][:42]
            cv2.rectangle(win, (10,480), (820,498), (20,25,45), -1)
            cv2.putText(win, f"Task: {tv}",
                (14,493), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,220,100), 1)

        # Header
        cv2.rectangle(win, (0,0), (820,72), (6,8,20), -1)
        cv2.putText(win, "COMPANION ROBOT — CLINICAL AI THERAPIST",
            (10,24), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (160,140,255), 2)
        gm_col = (0,220,80) if ST["gemini_ok"] else (200,150,0)
        lv_name = LEVELS.get(ST["therapy_level"],{}).get("name","")
        cv2.putText(win,
            f"Child: {ST['name']} | L{ST['therapy_level']}:{lv_name} | "
            f"Score:{ST['score']} | {'AI' if ST['gemini_ok'] else 'FB'}",
            (10,52), cv2.FONT_HERSHEY_SIMPLEX, 0.38, gm_col, 1)

        # Chat bubbles
        cy_ = 515
        for msg in ST["session_chat"][-3:]:
            isp = msg["role"] == "pepper"
            txt = msg["text"][:60]+("..." if len(msg["text"])>60 else "")
            cv2.rectangle(win, (10,cy_-16), (810,cy_+4),
                (30,20,60) if isp else (10,30,15), -1)
            cv2.rectangle(win, (10,cy_-16), (810,cy_+4),
                (100,80,200) if isp else (0,180,80), 1)
            pfx = "🤖 " if isp else f"👦 {ST['name']}: "
            cv2.putText(win, pfx+txt, (14,cy_),
                cv2.FONT_HERSHEY_SIMPLEX, 0.33,
                (180,160,255) if isp else (100,220,100), 1)
            cy_ -= 22

        with self._lock: self._live_frame = win

    def get_emo_frame(self):
        with self._lock:
            return self._emo_frame.copy() if self._emo_frame is not None else None

    def get_live_frame(self):
        with self._lock:
            return self._live_frame.copy() if self._live_frame is not None else None

# ═══════════════════════════════════════════════════════════════
# 8. CAMERA
# ═══════════════════════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.cap = None; self.idx = -1
        for i in [1, 0, 2, 3]:
            try:
                c = cv2.VideoCapture(i)
                if c.isOpened():
                    ret, f = c.read()
                    if ret and f is not None and f.size > 0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        c.set(cv2.CAP_PROP_FPS, 30)
                        self.cap = c; self.idx = i
                        print(f"✅ Camera index {i}"); return
                    c.release()
            except: pass
        print("⚠️  No camera")

    def read(self):
        if not self.cap: return False, None
        ret, f = self.cap.read()
        if ret and f is not None: return True, cv2.flip(f, 1)
        return False, None

# ═══════════════════════════════════════════════════════════════
# 9. VOICE + LIP-SYNC
# ═══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok = False; self._lk = threading.Lock()
        try:
            self.e = pyttsx3.init()
            self.e.setProperty('rate', 118)
            self.e.setProperty('volume', 1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice', v.id); break
            self.ok = True
            print("✅ Voice TTS + Lip-Sync")
        except Exception as e: print(f"⚠️  Voice: {e}")

    def _lip_thread(self, text):
        """Animate lip-sync using phoneme timing"""
        words = text.split()
        for word in words:
            if not ST["is_speaking"]: break
            dur = max(0.07, len(word)/13.0)
            # Open mouth
            ST["lip_sync_value"] = min(1.0, 0.5+random.uniform(0.1,0.45))
            ST["lip_sync_active"] = True
            time.sleep(dur*0.55)
            # Partial close
            ST["lip_sync_value"] = max(0.05, ST["lip_sync_value"]*0.35)
            time.sleep(dur*0.45)
        ST["lip_sync_value"] = 0.0
        ST["lip_sync_active"] = False

    def say(self, text, wait=True):
        ST["interrupt_flag"] = False
        text = str(text).replace("{name}", ST.get("name","Friend"))
        for t in ["[WAVE]","[CLAP]","[NOD]","[DANCE]","[POINT]",
                  "[HUG]","[CELEBRATE]","[THINK]","[GAME]","[LEVEL_UP]"]:
            text = text.replace(t, "")
        text = re.sub(r'\[YOUTUBE:[^\]]+\]', '', text)
        text = re.sub(r'\[REWARD:\d+\]', '', text)
        text = text.strip()
        if not text: return
        ST["is_speaking"] = True
        ST["session_chat"].append({
            "role":"pepper", "text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"]) > 40:
            ST["session_chat"] = ST["session_chat"][-40:]
        print(f"\n🔊 Pepper: {text}")
        LOG(f"Said: {text[:55]}")
        threading.Thread(target=self._lip_thread,
            args=(text,), daemon=True).start()
        if self.ok and not ST["interrupt_flag"]:
            with self._lk:
                try: self.e.say(text); self.e.runAndWait()
                except: pass
        ST["is_speaking"] = False
        ST["lip_sync_value"] = 0.0
        if wait and not ST["interrupt_flag"]:
            ST["waiting_for_child"] = True
            time.sleep(0.2)

    def stop(self):
        ST["interrupt_flag"] = True
        ST["is_speaking"]    = False
        ST["lip_sync_value"] = 0.0
        if self.ok:
            try: self.e.stop()
            except: pass

# ═══════════════════════════════════════════════════════════════
# 10. MICROPHONE — faster-whisper + SpeechRecognition
# ═══════════════════════════════════════════════════════════════
class Mic:
    def __init__(self):
        self.ok = False
        self.running = False
        self.whisper_model = None

        # Try faster-whisper (GPU)
        if WHISPER_OK:
            try:
                device = "cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                ctype  = "float16" if device=="cuda" else "int8"
                self.whisper_model = WhisperModel(
                    "tiny", device=device, compute_type=ctype)
                self.ok = True
                print(f"✅ faster-whisper ({device})")
            except Exception as e:
                print(f"⚠️  faster-whisper: {e}")

        # SpeechRecognition fallback
        try:
            self.r = sr.Recognizer()
            self.r.energy_threshold         = 10    # WHISPER SENSITIVE
            self.r.dynamic_energy_threshold = False
            self.r.pause_threshold          = 0.5
            self.r.phrase_threshold         = 0.08
            self.r.non_speaking_duration    = 0.1
            if not self.ok: self.ok = True
            print("✅ SpeechRecognition energy=10")
        except Exception as e:
            print(f"⚠️  SR: {e}")

    def _analyze_tone(self, raw_data):
        try:
            raw = np.frombuffer(raw_data, np.int16)
            rms = float(np.sqrt(np.mean(raw.astype(np.float64)**2)))
            ST["voice_energy"] = rms
            signs = np.sign(raw)
            zcr   = float(np.sum(np.abs(np.diff(signs)))/(2*len(raw)))
            ST["voice_pitch"] = "high" if zcr>0.08 else "normal" if zcr>0.04 else "low"
        except: pass

    def listen_once(self, timeout=8):
        if not self.ok:
            return input("Type: ").strip()
        ST["listening"] = True
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, duration=0.08)
                print("👂 Listening...")
                audio = self.r.listen(src, timeout=timeout, phrase_time_limit=18)
            raw_data = audio.get_raw_data()
            self._analyze_tone(raw_data)
            ST["listening"] = False

            # faster-whisper first
            if self.whisper_model and WHISPER_OK:
                try:
                    import tempfile, wave
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        tmp_path = tmp.name
                    with wave.open(tmp_path,'wb') as wf:
                        wf.setnchannels(1); wf.setsampwidth(2)
                        wf.setframerate(16000); wf.writeframes(raw_data)
                    segs, _ = self.whisper_model.transcribe(
                        tmp_path, language='en', beam_size=1)
                    text = " ".join(s.text.strip() for s in segs).strip()
                    os.unlink(tmp_path)
                    if text:
                        self._save_speech(text)
                        return text
                except Exception as e:
                    print(f"⚠️  Whisper: {e}")

            # Google SR fallback
            try:
                text = self.r.recognize_google(audio)
                self._save_speech(text)
                return text
            except sr.UnknownValueError:
                raw = np.frombuffer(raw_data, np.int16)
                rms = float(np.sqrt(np.mean(raw.astype(np.float64)**2)))
                if rms > 700:
                    LOG("👏 Clap sound!","success")
                    ST["clapping"] = True
                ST["last_sound"] = time.time()
                ST["waiting_for_child"] = False
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError: return "[timeout]"
        except: return ""
        finally: ST["listening"] = False

    def _save_speech(self, text):
        ST["last_sound"] = time.time()
        ST["last_speech_text"] = text
        ST["waiting_for_child"] = False
        ST["session_chat"].append({
            "role":"child","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"]) > 40:
            ST["session_chat"] = ST["session_chat"][-40:]
        LOG(f"Heard: {text}")

    def get_name(self, voice):
        if ST["known"]: return ST["name"]
        voice.say(EMPATHY.get("greeting"), wait=False)
        for attempt in range(3):
            resp = self.listen_once(timeout=10)
            if resp and resp not in ["[sound]","[timeout]",""]:
                n = self._extract(resp)
                if n:
                    ST["name"] = n; ST["known"] = True
                    LOG(f"Name: {n}","success"); return n
            elif resp == "[sound]":
                voice.say("I heard you! Say your name! 🎯", wait=False)
            elif resp == "[timeout]" and attempt < 2:
                voice.say(EMPATHY.get("silence"), wait=False)
        ST["name"] = "Friend"; ST["known"] = True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm","call me","name is"]:
            t = t.replace(rm,"").strip()
        w = t.split()
        return w[0].capitalize() if w else None

    def listen_bg(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if ST["is_speaking"]: time.sleep(0.1); continue
                result = self.listen_once(timeout=5)
                if result and result != "[timeout]":
                    if ST["is_speaking"]: ST["interrupt_flag"] = True
                    try: callback(result)
                    except Exception as e: print(f"⚠️  cb: {e}")
                time.sleep(0.04)
        threading.Thread(target=_loop, daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# 11. ACTIONS → PYBULLET + LIP-SYNC HeadPitch
# ═══════════════════════════════════════════════════════════════
class Actions:
    def __init__(self, pepper=None):
        self.pepper = pepper

    def _sa(self, j, a, s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j, a, s)
            except: pass

    def process(self, text):
        clean = text
        mapping = [
            ("[WAVE]",     self._wave),
            ("[CLAP]",     self._clap),
            ("[NOD]",      self._nod),
            ("[DANCE]",    self._dance),
            ("[POINT]",    self._point),
            ("[HUG]",      self._hug),
            ("[CELEBRATE]",self._celebrate),
            ("[THINK]",    self._think),
            ("[LEVEL_UP]", self._level_up),
        ]
        for tok, fn in mapping:
            if tok in text:
                clean = clean.replace(tok, "")
                threading.Thread(target=fn, daemon=True).start()
        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt:
            clean = clean.replace(yt.group(0), "")
            q = yt.group(1).strip()
            url = ("https://www.youtube.com/results?search_query="
                   + urllib.parse.quote(q+" autism children educational"))
            webbrowser.open(url)
            ST["last_youtube"] = url
            LOG(f"📺 YouTube: {q}")
        rew = re.search(r'\[REWARD:(\d+)\]', text)
        if rew:
            clean = clean.replace(rew.group(0), "")
            n = int(rew.group(1))
            ST["tokens"] += n; ST["stars_today"] += n
        if "[GAME]" in text:
            clean = clean.replace("[GAME]", "")
            webbrowser.open(GAME_URL)
        return clean.strip()

    def run_lip_sync_pybullet(self):
        """HeadPitch synchronizes with lip_sync_value — robotic realism"""
        while True:
            try:
                if ST["is_speaking"] and self.pepper:
                    lv = ST.get("lip_sync_value", 0.0)
                    # Nod down when mouth opens
                    hp = -0.04 - lv * 0.14
                    self._sa("HeadPitch", hp, 0.22)
            except: pass
            time.sleep(0.035)

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2); self._sa("RElbowRoll",0.8,0.2)
        time.sleep(0.3)
        for _ in range(3):
            self._sa("RWristYaw",0.5,0.25); time.sleep(0.2)
            self._sa("RWristYaw",-0.5,0.25); time.sleep(0.2)
        self._sa("RShoulderPitch",1.0,0.15)

    def _clap(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.8,0.25); self._sa("RShoulderPitch",0.8,0.25); time.sleep(0.18)
            self._sa("LShoulderPitch",1.1,0.25); self._sa("RShoulderPitch",1.1,0.25); time.sleep(0.18)

    def _nod(self):
        for _ in range(2):
            self._sa("HeadPitch",0.3,0.2); time.sleep(0.3)
            self._sa("HeadPitch",-0.1,0.2); time.sleep(0.3)
        self._sa("HeadPitch",0.0,0.15)

    def _dance(self):
        for _ in range(5):
            self._sa("LShoulderPitch",0.15,0.2); self._sa("RShoulderPitch",0.9,0.2)
            self._sa("HeadYaw",0.4,0.2); time.sleep(0.22)
            self._sa("LShoulderPitch",0.9,0.2); self._sa("RShoulderPitch",0.15,0.2)
            self._sa("HeadYaw",-0.4,0.2); time.sleep(0.22)
        self._sa("HeadYaw",0,0.1)

    def _point(self):
        self._sa("LShoulderPitch",0.1,0.15); self._sa("LElbowYaw",-1.5,0.15)
        time.sleep(1.0); self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        for j,a in [("LShoulderPitch",0.5),("RShoulderPitch",0.5),
                    ("LShoulderRoll",0.35),("RShoulderRoll",-0.35)]:
            self._sa(j,a,0.1)
        time.sleep(1.5)
        for j,a in [("LShoulderPitch",1.0),("RShoulderPitch",1.0),
                    ("LShoulderRoll",0.0),("RShoulderRoll",0.0)]:
            self._sa(j,a,0.1)

    def _celebrate(self):
        for _ in range(3):
            for j,a in [("LShoulderPitch",0.05),("RShoulderPitch",0.05),("HeadPitch",-0.2)]:
                self._sa(j,a,0.25)
            time.sleep(0.25)
            for j,a in [("LShoulderPitch",1.0),("RShoulderPitch",1.0),("HeadPitch",0.0)]:
                self._sa(j,a,0.25)
            time.sleep(0.25)

    def _think(self):
        self._sa("HeadYaw",0.35,0.1); self._sa("HeadPitch",-0.15,0.1)
        time.sleep(1.8)
        self._sa("HeadYaw",0.0,0.1); self._sa("HeadPitch",0.0,0.1)

    def _level_up(self):
        for _ in range(6):
            self._sa("LShoulderPitch",0.05,0.3); self._sa("RShoulderPitch",0.05,0.3)
            self._sa("HeadPitch",-0.25,0.2); time.sleep(0.2)
            self._sa("LShoulderPitch",1.0,0.3); self._sa("RShoulderPitch",1.0,0.3)
            self._sa("HeadPitch",0.0,0.2); time.sleep(0.2)
        self._sa("HeadYaw",0,0.1)

# ═══════════════════════════════════════════════════════════════
# 12. PYBULLET (Window 1)
# ═══════════════════════════════════════════════════════════════
class PepperSim:
    def __init__(self):
        self.pepper = None; self.ok = False
        self.rx = self.ry = 0.0
        self.auto_walk = True; self.balloons = []

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim  = QS()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._build_room()
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._add_balloons(); self._add_children()
            p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
            self.ok = True
            for fn in [self._sim_loop,self._walk_loop,self._arm_loop]:
                threading.Thread(target=fn, daemon=True).start()
            print("✅ PyBullet Window 1 — Lip-sync enabled")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}"); return None

    def _build_room(self):
        wc = [0.88,0.88,0.92,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,p.createVisualShape(
                p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,p.createVisualShape(
            p.GEOM_BOX,halfExtents=[4.5,3.5,.02],
            rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        for txt,pos in [
            ("ABA Level 1",[-4,3,2]),
            ("DTT Level 2",[4,3,2]),
            ("ESDM Level 3",[0,4,2]),
            ("COMPANION ROBOT",[0,0,2.8])]:
            p.addUserDebugText(txt,pos,[.4,.5,.9],textSize=1.1,lifeTime=0)

    def _add_balloons(self):
        cols = [[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
                [1,1,.2,1],[1,.5,.2,1]]
        for i in range(5):
            vs = p.createVisualShape(p.GEOM_SPHERE,radius=.15,rgbaColor=cols[i%len(cols)])
            bid = p.createMultiBody(0,-1,vs,[
                random.uniform(-3,3),random.uniform(-2,2),random.uniform(.8,2.2)])
            self.balloons.append({"id":bid,
                "x":random.uniform(-3,3),"y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),"spd":random.uniform(.01,.03)})

    def _add_children(self):
        for nm,pos,col in [
            ("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1]),
            ("Sara",[-1.2,1.3,0],[1.,.6,.0,1])]:
            p.createMultiBody(0,-1,p.createVisualShape(
                p.GEOM_BOX,halfExtents=[.13,.09,.21],rgbaColor=col),
                [pos[0],pos[1],.41])
            p.createMultiBody(0,-1,p.createVisualShape(
                p.GEOM_SPHERE,radius=.11,rgbaColor=[1.,.82,.65,1.]),
                [pos[0],pos[1],.74])
            p.addUserDebugText(nm,[pos[0],pos[1],1.05],[0,0,0],textSize=.85,lifeTime=0)

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b["z"] += b["spd"]
                if b["z"] > 2.8:
                    b["z"]=.6; b["x"]=random.uniform(-3,3); b["y"]=random.uniform(-2,2)
                try: p.resetBasePositionAndOrientation(
                    b["id"],[b["x"],b["y"],b["z"]],[0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _walk_loop(self):
        t = 0
        while True:
            if self.auto_walk:
                t += .015
                self.rx += .018*math.cos(t*.4)
                self.ry += .018*math.sin(t*.5)
                self.rx = max(-3.5,min(3.5,self.rx))
                self.ry = max(-2.8,min(2.8,self.ry))
                try: self.pepper.setPosition([self.rx,self.ry,.8])
                except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph = 0
        while True:
            try:
                if ST["is_speaking"]:
                    ph += .07
                    L = .5+.3*math.sin(ph)
                    R = .5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles("LShoulderPitch",L,.07)
                    self.pepper.setAngles("RShoulderPitch",R,.07)
                    # LIP-SYNC HeadPitch
                    lip = ST.get("lip_sync_value",0.0)
                    self.pepper.setAngles("HeadPitch",-0.04-lip*0.13,.18)
                elif ST["listening"]:
                    self.pepper.setAngles("HeadYaw",0.25,.05)
                    self.pepper.setAngles("HeadPitch",0.12,.05)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.,.04)
                    self.pepper.setAngles("RShoulderPitch",1.,.04)
                    self.pepper.setAngles("HeadYaw",0.,.03)
                    self.pepper.setAngles("HeadPitch",0.,.03)
            except: pass
            time.sleep(.04)

    def show_text(self, text):
        if not self.ok: return
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:55],
                [pos[0],pos[1],pos[2]+1.35],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass

# ═══════════════════════════════════════════════════════════════
# 13. DISPLAY ENGINE — 3 Windows
# ═══════════════════════════════════════════════════════════════
class Display:
    def __init__(self, vision, cam):
        self.v = vision; self.c = cam
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()
        print("✅ Display: 3 windows started")

    def _sim_frame(self):
        h,w = 480,640
        f = np.zeros((h,w,3),dtype=np.uint8); f[:] = (7,10,25)
        t = time.time()
        for i in range(0,w,60): cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,60): cv2.line(f,(0,i),(w,i),(15,22,50),1)
        r = int(28+10*math.sin(t*1.5))
        col = (int(50+50*math.sin(t)),int(100+100*math.cos(t*0.7)),220)
        cv2.circle(f,(w//2,h//2-40),r,col,3)
        cv2.putText(f,"SIMULATION MODE",(w//2-110,h//2+20),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(100,150,255),2)
        return f

    def _run(self):
        no_cam = self.c.idx < 0
        em_last = 0

        cv2.namedWindow(WIN_EMO, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_EMO, 600, 600)
        try: cv2.setWindowProperty(WIN_EMO, cv2.WND_PROP_TOPMOST, 1)
        except: pass
        cv2.moveWindow(WIN_EMO, 660, 30)

        cv2.namedWindow(WIN_LIVE, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WIN_LIVE, 820, 520)
        try: cv2.setWindowProperty(WIN_LIVE, cv2.WND_PROP_TOPMOST, 1)
        except: pass
        cv2.moveWindow(WIN_LIVE, 30, 30)

        while self.running:
            try:
                if no_cam: frame = self._sim_frame()
                else:
                    ret, f = self.c.read()
                    frame = f if ret else self._sim_frame()
                now = time.time()
                if now - em_last > 0.65 and not no_cam:
                    em_last = now
                    self.v.analyze_async(frame.copy())
                elif no_cam and now - em_last > 3:
                    em_last = now
                    ST["emotion"] = random.choice(["happy","neutral","joyful","happy"])
                ew = self.v.get_emo_frame()
                if ew is not None: cv2.imshow(WIN_EMO, ew)
                lw = self.v.get_live_frame()
                if lw is not None: cv2.imshow(WIN_LIVE, lw)
                # MANDATORY waitKey — prevents X11 crash
                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'), ord('Q'), 27]:
                    self.running = False; break
            except Exception as e:
                print(f"⚠️  display: {e}"); time.sleep(0.1)
            time.sleep(0.016)
        try: cv2.destroyAllWindows()
        except: pass

    def stop(self):
        self.running = False; time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass

# ═══════════════════════════════════════════════════════════════
# 14. FLASK — GAME + REPORTS + BRAIN
# ═══════════════════════════════════════════════════════════════
game_app   = Flask("game")
rep_app    = Flask("reports")
brain_app  = Flask("brain")

# ── GAME ──────────────────────────────────────────────────────
GAME_HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><title>Therapy Games</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:12px}
h1{color:#a78bfa;text-align:center;margin-bottom:10px}
.nav{display:flex;gap:6px;justify-content:center;margin-bottom:10px;flex-wrap:wrap}
.nav a{padding:8px 14px;border-radius:9px;text-decoration:none;
       font-size:.8em;font-weight:700;min-height:40px;display:flex;align-items:center}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}
.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.sc{background:#1a0a3d;border-radius:8px;padding:7px 14px;text-align:center;margin-bottom:10px;color:#a78bfa}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-width:700px;margin:0 auto}
@media(min-width:500px){.grid{grid-template-columns:repeat(3,1fr)}}
.gc{background:#0c0f1e;border:2px solid #1a1f40;border-radius:11px;padding:14px;
    text-align:center;cursor:pointer;transition:.3s}
.gc:hover,.gc:active{border-color:#a78bfa;transform:translateY(-2px)}
.gi{font-size:2.4em;margin-bottom:5px}
.gn{font-weight:700;color:#e0e6ff;font-size:.85em}
.gd{font-size:.68em;color:#6b7280;margin-top:3px}
#ag{max-width:700px;margin:10px auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;border-radius:7px;
     cursor:pointer;font-size:.8em;margin:4px;min-height:42px;touch-action:manipulation}
.btn-g{background:#059669}
canvas{border:2px solid #4f46e5;border-radius:8px;background:#0a0f1e;
       display:block;margin:8px auto;max-width:100%;touch-action:none}
.pbox{background:#0c0f1e;border:2px solid #a78bfa;border-radius:11px;
      padding:14px;max-width:700px;margin:10px auto;text-align:center}
</style></head><body>
<h1>🎮 ABA Therapy Games</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com" class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="sc">Score: <span id="pts">0</span> ⭐ | Level: <span id="lvl">1</span></div>
<div class="grid">
  <div class="gc" onclick="start('balloons')"><div class="gi">🎈</div><div class="gn">Balloons</div><div class="gd">Pop them!</div></div>
  <div class="gc" onclick="start('emotions')"><div class="gi">😊</div><div class="gn">Emotions</div><div class="gd">Mirror face</div></div>
  <div class="gc" onclick="start('colors')"><div class="gi">🎨</div><div class="gn">Colors</div><div class="gd">Match it!</div></div>
  <div class="gc" onclick="start('numbers')"><div class="gi">🔢</div><div class="gn">Count!</div><div class="gd">How many?</div></div>
  <div class="gc" onclick="start('memory')"><div class="gi">🧠</div><div class="gn">Memory</div><div class="gd">Find pairs!</div></div>
  <div class="gc" onclick="start('shapes')"><div class="gi">⭐</div><div class="gn">Shapes</div><div class="gd">Name it!</div></div>
</div>
<div id="ag"></div>
<div class="pbox">
  <h3 style="color:#a78bfa;margin-bottom:6px">🌐 Platform</h3>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
     target="_blank" class="btn btn-g" style="display:inline-block;text-decoration:none">Open 🚀</a>
</div>
<script>
var sc=0,lv=1;
function add(n){sc+=n;lv=Math.floor(sc/50)+1;
  document.getElementById('pts').textContent=sc;
  document.getElementById('lvl').textContent=lv;}
function start(g){var d=document.getElementById('ag');
  if(g==='balloons')runBalloons(d);else if(g==='emotions')emoGame(d);
  else if(g==='colors')colorGame(d);else if(g==='numbers')numGame(d);
  else if(g==='memory')memGame(d);else shapeGame(d);}
function runBalloons(d){
  var W=Math.min(680,window.innerWidth-24);
  d.innerHTML='<canvas id="gc" width="'+W+'" height="280" style="width:100%"></canvas>';
  var c=document.getElementById('gc'),ctx=c.getContext('2d'),bs=[];
  for(var i=0;i<8;i++)bs.push({x:Math.random()*(W-40)+20,y:Math.random()*240+20,
    r:18+Math.random()*12,vx:(Math.random()-0.5)*2.5,vy:(Math.random()-0.5)*2.5,
    color:['#f87171','#34d399','#60a5fa','#fbbf24','#c084fc'][Math.floor(Math.random()*5)],alive:true});
  function hit(mx,my){bs.forEach(function(b){if(!b.alive)return;
    if(Math.sqrt((mx-b.x)**2+(my-b.y)**2)<b.r){b.alive=false;add(10);}});
    if(bs.every(function(b){return !b.alive;}))bs.forEach(function(b){b.alive=true;
      b.x=Math.random()*(W-40)+20;b.y=Math.random()*240+20;});}
  c.addEventListener('click',function(e){var r=c.getBoundingClientRect(),s=c.width/r.width;
    hit((e.clientX-r.left)*s,(e.clientY-r.top)*s);});
  c.addEventListener('touchstart',function(e){e.preventDefault();
    var r=c.getBoundingClientRect(),s=c.width/r.width,t=e.touches[0];
    hit((t.clientX-r.left)*s,(t.clientY-r.top)*s);},{passive:false});
  (function loop(){ctx.fillStyle='#0a0f1e';ctx.fillRect(0,0,W,280);
    bs.forEach(function(b){if(!b.alive)return;b.x+=b.vx;b.y+=b.vy;
      if(b.x<b.r||b.x>W-b.r)b.vx*=-1;if(b.y<b.r||b.y>280-b.r)b.vy*=-1;
      ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,Math.PI*2);ctx.fillStyle=b.color;ctx.fill();
      ctx.fillStyle='white';ctx.font='16px sans-serif';ctx.textAlign='center';
      ctx.fillText('🎈',b.x,b.y+5);});requestAnimationFrame(loop);})();}
function emoGame(d){
  var em=[['😊','Happy'],['😢','Sad'],['😠','Angry'],['😨','Scared'],['😲','Surprised']];
  var pick=em[Math.floor(Math.random()*em.length)];
  d.innerHTML='<div style="text-align:center;padding:14px">'+
    '<p style="color:#a78bfa;margin-bottom:7px">Show this face!</p>'+
    '<div style="font-size:4em;margin:10px">'+pick[0]+'</div>'+
    '<p style="font-weight:700;color:#e0e6ff">'+pick[1]+'</p>'+
    '<button class="btn btn-g" onclick="add(20);this.textContent=\'✅ Amazing!\'"'+
    ' style="display:block;width:100%;max-width:200px;margin:10px auto">I did it! 🌟</button>'+
    '<button class="btn" onclick="emoGame(document.getElementById(\'ag\'))"'+
    ' style="display:block;width:100%;max-width:200px;margin:6px auto">Next ➡️</button></div>';}
function colorGame(d){
  var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],
          ['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316']];
  var idx=Math.floor(Math.random()*cs.length);
  d.innerHTML='<div style="text-align:center;padding:14px">'+
    '<p style="color:#a78bfa;margin-bottom:7px">What color?</p>'+
    '<div style="width:90px;height:90px;background:'+cs[idx][1]+
    ';border-radius:50%;margin:8px auto;border:3px solid #374151"></div>'+
    '<div id="cbtns" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin-top:8px">'+
    cs.map(function(c,i){return '<button class="btn" onclick="chkC('+i+','+idx+')" '+
      'style="background:'+c[1]+';min-width:80px">'+c[0]+'</button>';}).join('')+'</div></div>';}
window.chkC=function(ch,co){
  if(ch===co){add(15);document.getElementById('cbtns').innerHTML=
    '<p style="color:#34d399;margin:8px">✅ Correct! 🌟</p>'+
    '<button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" '+
    'style="display:block;margin:6px auto">Next ➡️</button>';}
  else document.getElementById('cbtns').innerHTML=
    '<p style="color:#f87171;margin:8px">Try again! 💪</p>'+
    '<button class="btn" onclick="colorGame(document.getElementById(\'ag\'))" '+
    'style="display:block;margin:6px auto">Retry ↩️</button>';};
function numGame(d){
  var n=Math.floor(Math.random()*9)+1,stars='';
  for(var i=0;i<n;i++)stars+='⭐';
  var opts=Array.from(new Set([n,Math.max(1,n-1),Math.min(10,n+1),n>2?n-2:n+3]))
    .sort(function(){return Math.random()-0.5;}).slice(0,4);
  d.innerHTML='<div style="text-align:center;padding:14px">'+
    '<p style="color:#a78bfa">Count!</p>'+
    '<div style="font-size:1.4em;margin:9px;word-break:break-all">'+stars+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px">'+
    opts.map(function(x){return '<button class="btn" onclick="chkN('+x+','+n+')" '+
      'style="font-size:1.1em;min-width:60px">'+x+'</button>';}).join('')+'</div></div>';}
window.chkN=function(ch,co){
  if(ch===co){add(20);alert('✅ YES! '+co+'! 🌟');
    numGame(document.getElementById('ag'));}
  else alert('Try again! 💪');};
function memGame(d){
  var pairs=['🐶','🐱','🐻','🦊','🐼','🐨'],
      cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});
  window._mc=cards;window._mf=[];window._mm=[];
  d.innerHTML='<div style="display:grid;grid-template-columns:repeat(4,1fr);'+
    'gap:6px;max-width:300px;margin:10px auto">'+
    cards.map(function(c,i){return '<div id="mc'+i+'" onclick="flipM('+i+')" '+
      'style="height:60px;background:#1f2937;border-radius:7px;display:flex;'+
      'align-items:center;justify-content:center;font-size:1.7em;cursor:pointer;'+
      'border:2px solid #374151;touch-action:manipulation">❓</div>';}).join('')+'</div>';}
window.flipM=function(idx){var c=window._mc;
  if(window._mf.length>=2||window._mm.includes(idx)||window._mf.includes(idx))return;
  document.getElementById('mc'+idx).textContent=c[idx];window._mf.push(idx);
  if(window._mf.length===2){var a=window._mf[0],b=window._mf[1];
    if(c[a]===c[b]){window._mm.push(a,b);add(25);window._mf=[];
      if(window._mm.length===c.length)setTimeout(function(){
        alert('🎉 All matched!');memGame(document.getElementById('ag'));},400);}
    else setTimeout(function(){
      document.getElementById('mc'+a).textContent='❓';
      document.getElementById('mc'+b).textContent='❓';
      window._mf=[];},1000);}};
function shapeGame(d){
  var shapes=[['⬛','Square'],['⭕','Circle'],['🔺','Triangle'],['💎','Diamond'],['⭐','Star']];
  var pick=shapes[Math.floor(Math.random()*shapes.length)];
  d.innerHTML='<div style="text-align:center;padding:14px">'+
    '<p style="color:#a78bfa;margin-bottom:7px">What shape?</p>'+
    '<div style="font-size:4em;margin:10px">'+pick[0]+'</div>'+
    '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px">'+
    shapes.map(function(s){return '<button class="btn" onclick="chkS(\''+s[1]+'\',\''+
      pick[1]+'\')">'+s[1]+'</button>';}).join('')+'</div></div>';}
window.chkS=function(ch,co){
  if(ch===co){add(15);alert('✅ Correct! 🌟');
    shapeGame(document.getElementById('ag'));}
  else alert('Try again! 💪');};
</script></body></html>"""

@game_app.route("/")
@game_app.route("/<path:path>")
def game_catch(path=""):
    return GAME_HTML

@game_app.errorhandler(404)
def g404(e): return redirect("/"), 302

@game_app.errorhandler(405)
def g405(e): return redirect("/"), 302

# ── REPORTS ───────────────────────────────────────────────────
REP_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><title>Clinical Reports</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="5">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;font-family:'Segoe UI',sans-serif;padding:14px}
h1{color:#a78bfa;margin-bottom:10px}
.nav{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.nav a{padding:7px 12px;border-radius:8px;text-decoration:none;font-size:.78em;
       font-weight:700;min-height:38px;display:flex;align-items:center}
.b1{background:#4f46e5;color:#fff}.b2{background:#059669;color:#fff}
.b3{background:#1d4ed8;color:#fff}.b4{background:#7c3aed;color:#fff}
.card{background:#0c0f1e;border-radius:10px;padding:12px;
      border:1px solid #1a1f40;margin-bottom:10px}
.card h2{color:#818cf8;margin-bottom:7px;font-size:.82em}
.stat{display:inline-block;background:#1a0a3d;border-radius:7px;
      padding:5px 10px;margin:3px;text-align:center}
.n{font-size:1.3em;font-weight:700;color:#a78bfa}
.l{font-size:.63em;color:#6b7280}
.rep{background:#07090f;border-radius:7px;padding:9px;margin:6px 0;
     border-left:3px solid #a78bfa;white-space:pre-wrap;
     font-size:.75em;line-height:1.7;color:#c0c8e0;
     max-height:250px;overflow-y:auto}
.btn{background:#4f46e5;color:#fff;border:none;padding:9px 16px;
     border-radius:7px;cursor:pointer;font-size:.78em;margin:3px;min-height:40px}
.btn-g{background:#059669}
input,textarea,select{width:100%;padding:6px 8px;border-radius:5px;
  border:1px solid #1a1f40;background:#07090f;color:#e0e6ff;
  font-size:.77em;font-family:inherit;outline:none;min-height:38px}
textarea{resize:vertical;min-height:65px;margin:4px 0}
.note{background:#0a1020;border-left:3px solid #a78bfa;
      padding:6px;margin:3px 0;font-size:.72em}
</style></head><body>
<h1>📋 Clinical Reports</h1>
<div class="nav">
  <a href="http://127.0.0.1:5007/" class="b1">🧠 Brain</a>
  <a href="http://127.0.0.1:5009/" class="b2">🎮 Games</a>
  <a href="http://127.0.0.1:5001/" class="b3">📋 Reports</a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
     class="b4" target="_blank">🌐 Platform</a>
</div>
<div class="card">
  <h2>📊 Progress</h2>
  <div class="stat"><div class="n">{{ s.therapy_level }}</div><div class="l">Level</div></div>
  <div class="stat"><div class="n">{{ s.level_successes }}/3</div><div class="l">Progress</div></div>
  <div class="stat"><div class="n">{{ s.score }}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n">{{ s.tokens }}</div><div class="l">Tokens</div></div>
  <div class="stat"><div class="n">{{ s.tasks_success }}</div><div class="l">OK</div></div>
  <div class="stat"><div class="n">{{ s.tasks_fail }}</div><div class="l">Fail</div></div>
  <div class="stat"><div class="n">{{ s.attention }}%</div><div class="l">Attention</div></div>
  <div class="stat"><div class="n">{{ s.total_levels_passed }}</div><div class="l">Levels</div></div>
</div>
<div class="card">
  <h2>📄 Reports</h2>
  <form method="POST" action="/generate">
    <button class="btn btn-g" style="width:100%">⚡ Generate Report</button>
  </form>
  {% for rep in s.reports[-5:]|reverse %}
  <div class="rep">{{ rep.content }}</div>
  <div style="font-size:.63em;color:#6b7280;margin:2px">{{ rep.time }}</div>
  {% endfor %}
  {% if not s.reports %}
  <p style="color:#6b7280;font-size:.77em;margin-top:6px">Click Generate to create report.</p>
  {% endif %}
</div>
<div class="card">
  <h2>📝 Notes</h2>
  <form method="POST" action="/note">
    <select name="cat" style="width:140px;margin-bottom:5px">
      <option>behavior</option><option>progress</option>
      <option>concern</option><option>milestone</option>
    </select>
    <textarea name="note" placeholder="Observation..."></textarea>
    <button class="btn btn-g" style="width:100%;margin-top:5px">Save</button>
  </form>
  {% for n in s.parent_notes[-10:]|reverse %}
  <div class="note">
    <span style="color:#a78bfa;font-size:.67em;font-weight:700">{{ n.category.upper() }}</span>
    <span style="color:#6b7280;font-size:.67em"> {{ n.time }}</span><br>{{ n.text }}
  </div>
  {% endfor %}
</div>
</body></html>"""

@rep_app.route("/")
@rep_app.route("/<path:path>")
def rep_catch(path=""):
    return render_template_string(REP_HTML, s=ST)

@rep_app.route("/generate", methods=["POST"])
def rep_gen():
    if _gemini:
        r = _gemini.generate_report()
        ST["reports"].append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": r})
        if len(ST["reports"]) > 10: ST["reports"] = ST["reports"][-10:]
    return redirect("/")

@rep_app.route("/note", methods=["POST"])
def rep_note():
    note = request.form.get("note","").strip()
    cat  = request.form.get("cat","other")
    if note:
        ST["parent_notes"].append({
            "time":datetime.now().strftime("%H:%M:%S"),
            "text":note, "category":cat})
    return redirect("/")

@rep_app.errorhandler(404)
def r404(e): return redirect("/"), 302

@rep_app.errorhandler(405)
def r405(e): return redirect("/"), 302

# ── BRAIN DASHBOARD ───────────────────────────────────────────
AVATAR_CSS = """<style>
.av-wrap{display:flex;flex-direction:column;align-items:center;padding:6px 3px}
.av-body{position:relative;width:88px;height:108px;margin:0 auto}
.av-head{position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:54px;height:54px;background:#e8d5c4;border-radius:50%;border:2px solid #c4a882}
.av-eye{width:7px;height:7px;background:#1a1a2e;border-radius:50%;
  position:absolute;top:17px;animation:blink 4s infinite}
.av-eye.l{left:11px}.av-eye.r{right:11px}
@keyframes blink{0%,88%,100%{transform:scaleY(1)}94%{transform:scaleY(0.1)}}
.av-mouth{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);
  width:17px;height:6px;border-bottom:2px solid #c4a882;border-radius:0 0 50% 50%}
.av-mouth.talk{animation:tlk .25s infinite alternate}
@keyframes tlk{from{height:2px}to{height:12px}}
.av-mouth.sad{border-radius:50% 50% 0 0;border-bottom:none;border-top:2px solid #c4a882}
.av-torso{position:absolute;bottom:0;left:50%;transform:translateX(-50%);
  width:62px;height:53px;background:linear-gradient(135deg,#4f46e5,#7c3aed);
  border-radius:31px 31px 13px 13px}
.av-arm-l{position:absolute;bottom:13px;left:-4px;width:10px;height:30px;
  background:#4f46e5;border-radius:5px;transform-origin:top center}
.av-arm-r{position:absolute;bottom:13px;right:-4px;width:10px;height:30px;
  background:#4f46e5;border-radius:5px;transform-origin:top center}
.av-arm-l.wave{animation:wl .5s infinite alternate}
@keyframes wl{from{transform:rotate(-22deg)}to{transform:rotate(22deg)}}
.av-arm-r.wave{animation:wr .5s infinite alternate}
@keyframes wr{from{transform:rotate(22deg)}to{transform:rotate(-22deg)}}
.av-arm-l.talk{animation:tal .4s infinite alternate}
@keyframes tal{from{transform:rotate(-8deg)}to{transform:rotate(13deg)}}
.av-arm-r.talk{animation:tar .4s infinite alternate}
@keyframes tar{from{transform:rotate(8deg)}to{transform:rotate(-13deg)}}
.av-badge{margin-top:5px;padding:3px 8px;border-radius:16px;
  font-size:.66em;font-weight:700;text-align:center}
.av-badge.spk{background:#1e3a5f;color:#60a5fa;animation:pulse .9s infinite}
.av-badge.lst{background:#052918;color:#34d399;animation:pulse .9s infinite}
.av-badge.wt{background:#2a1a00;color:#fbbf24}
.av-badge.idle{background:#1a1f40;color:#6b7280}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.av-emo{font-size:1.5em;margin-top:3px}
.av-lip{font-size:.58em;color:#60a5fa;margin-top:2px;text-align:center}
</style>"""

def build_avatar():
    spk = ST.get("is_speaking", False)
    lst = ST.get("listening", False)
    wt  = ST.get("waiting_for_child", False)
    em  = ST.get("emotion", "neutral")
    lip = ST.get("lip_sync_value", 0.0)
    ac  = "wave" if spk else "talk" if lst else ""
    mc  = "talk" if spk else "sad" if em in ["sad","angry","fear"] else ""
    if spk:   bc,bt = "spk","🔊 Speaking"
    elif lst: bc,bt = "lst","👂 Listening"
    elif wt:  bc,bt = "wt","⏳ Waiting"
    else:     bc,bt = "idle","💤 Ready"
    ee = {"happy":"😊","sad":"😢","angry":"😠","fear":"😨",
          "surprised":"😲","joyful":"😄","confused":"🤔","neutral":"🙂"}.get(em,"🙂")
    lip_bar = "▓"*int(lip*10) + "░"*(10-int(lip*10))
    return f"""<div class="av-wrap">
  <div class="av-body">
    <div class="av-head">
      <div class="av-eye l"></div><div class="av-eye r"></div>
      <div class="av-mouth {mc}"></div>
    </div>
    <div class="av-torso">
      <div class="av-arm-l {ac}"></div><div class="av-arm-r {ac}"></div>
    </div>
  </div>
  <div class="av-badge {bc}">{bt}</div>
  <div class="av-emo">{ee}</div>
  <div class="av-lip">{lip_bar}</div>
</div>"""

BRAIN_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Companion Robot Brain</title>
<meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
{{ avatar_css|safe }}
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060912;--card:#0c0f1e;--bo:#1a1f40;
      --pu:#a78bfa;--bl:#60a5fa;--gr:#34d399;
      --rd:#f87171;--yl:#fbbf24;--tx:#e0e6ff;--mu:#6b7280}
body{font-family:'Segoe UI',system-ui,sans-serif;
     background:var(--bg);color:var(--tx);font-size:13px}
.layout{display:flex;min-height:100vh}
.sidebar{width:144px;background:#07090f;border-right:2px solid var(--bo);
         display:flex;flex-direction:column;padding:7px 5px;gap:5px;
         position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0}
.sidebar h3{color:var(--pu);font-size:.70em;margin-bottom:2px;text-align:center}
.slink{display:flex;flex-direction:column;align-items:center;
       padding:8px 4px;border-radius:9px;text-decoration:none;
       font-weight:700;transition:.25s;border:2px solid;width:100%;font-size:.67em}
.slink:hover{transform:translateY(-2px);opacity:.9}
.sl-brain{background:#1e1b4b;color:var(--pu);border-color:var(--pu)}
.sl-game{background:#052918;color:var(--gr);border-color:var(--gr)}
.sl-rep{background:#1e3a5f;color:var(--bl);border-color:var(--bl)}
.sl-gh{background:#2a1060;color:#c084fc;border-color:#c084fc}
.sl-plat{background:#1a2040;color:var(--yl);border-color:var(--yl)}
.sl-icon{font-size:1.45em;margin-bottom:2px}
.sl-port{font-size:.56em;opacity:.7}
.content{flex:1;padding:8px;min-width:0;overflow-y:auto}
.android-info{background:#051a0f;border:1px solid var(--gr);border-radius:8px;
              padding:6px 10px;margin-bottom:7px;text-align:center}
.android-url{font-size:.80em;color:var(--gr);font-weight:700;word-break:break-all}
.lv-box{background:#051a0f;border:2px solid var(--gr);border-radius:9px;
        padding:8px;margin-bottom:7px;text-align:center}
.lv-title{color:var(--gr);font-size:.80em;font-weight:700}
.lv-bar{height:10px;border-radius:5px;background:linear-gradient(90deg,#059669,#34d399)}
.lv-bg{background:#1f2937;border-radius:5px;height:10px;margin:5px 0}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);border-radius:9px;
     padding:8px 12px;display:flex;align-items:center;gap:7px;
     border:1px solid #4f46e5;margin-bottom:7px}
.hdr h1{font-size:.86em;color:var(--pu)}
.bd{padding:2px 5px;border-radius:8px;font-size:.60em;font-weight:700}
.live{background:#ef4444;color:#fff;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.row{display:grid;gap:7px}
.r3{grid-template-columns:1fr 1fr 1fr}
.r2{grid-template-columns:1fr 1fr}
.r5{grid-template-columns:repeat(5,1fr)}
.card{background:var(--card);border-radius:9px;padding:10px;border:1px solid var(--bo)}
.card h2{font-size:.73em;color:#818cf8;border-bottom:1px solid var(--bo);
         padding-bottom:3px;margin-bottom:6px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:7px;padding:8px;text-align:center}
.stat:hover{border-color:var(--pu)}
.n{font-size:1.45em;font-weight:700;color:var(--pu)}
.l{font-size:.62em;color:var(--mu);margin-top:2px}
.n-g{color:var(--gr)}.n-y{color:var(--yl)}.n-b{color:var(--bl)}
.emo{display:inline-block;padding:4px 10px;border-radius:12px;font-weight:700;font-size:.87em}
.happy,.joyful{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprised{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.confused{background:#2a1a0055;color:#fb923c;border:1px solid #fb923c}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.bar-bg{background:#1f2937;border-radius:5px;height:6px;margin:3px 0}
.bar{height:6px;border-radius:5px;background:linear-gradient(90deg,#6366f1,#a78bfa)}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;
     padding:4px 8px;border-radius:5px;cursor:pointer;font-size:.67em;
     margin:2px;transition:.2s;font-family:inherit;min-height:30px}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}
input,textarea,select{width:100%;padding:5px 7px;border-radius:5px;
  border:1px solid var(--bo);background:#07090f;color:var(--tx);
  font-size:.71em;font-family:inherit;outline:none;min-height:30px}
input:focus,textarea:focus{border-color:var(--pu)}
textarea{resize:vertical;min-height:44px}
.log-box{max-height:155px;overflow-y:auto;scrollbar-width:thin}
.li{padding:2px 5px;margin:1px 0;border-radius:3px;font-size:.66em;
    border-left:3px solid #4f46e5;background:#07090f;line-height:1.4}
.li.success{border-color:var(--gr)}.li.fail{border-color:var(--rd)}
.cw{height:130px;background:#07090f;border-radius:6px;padding:4px}
.chat-box{height:135px;overflow-y:auto;background:#07090f;
          border-radius:6px;padding:6px;margin-bottom:4px;scrollbar-width:thin}
.cm{padding:3px 6px;margin:2px 0;border-radius:5px;font-size:.69em;line-height:1.5}
.cmp{background:#1e1b4b;border-left:3px solid var(--pu)}
.cmc{background:#052918;border-left:3px solid var(--gr)}
.cmr{background:#1a1f40;border-left:3px solid var(--bl)}
.tabs{display:flex;gap:3px;flex-wrap:wrap;margin-bottom:6px}
.tab{padding:3px 8px;border-radius:5px;cursor:pointer;font-size:.67em;
     background:#1f2937;color:#9ca3af;border:1px solid var(--bo);
     transition:.2s;min-height:26px}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tc{display:none}.tc.active{display:block}
.hc{background:#0a1020;border-radius:7px;padding:7px;border-left:4px solid var(--pu)}
.hct{color:var(--pu);font-weight:700;font-size:.71em;margin-bottom:2px}
.hcb{color:#9ca3af;font-size:.68em;line-height:1.6}
.tip{background:#051a0f;border:1px solid var(--gr);border-radius:3px;
     padding:3px;margin-top:3px;font-size:.66em;color:#6ee7b7}
.ab{display:inline-block;padding:2px 5px;border-radius:6px;
    font-size:.64em;font-weight:700;margin:1px}
.aon{background:#052918;color:var(--gr);border:1px solid var(--gr)}
.aoff{background:#1f2937;color:#374151;border:1px solid #374151}
::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-track{background:var(--card)}
::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:3px}
@media(max-width:700px){
  .sidebar{width:108px}
  .r3{grid-template-columns:1fr 1fr}
  .r5{grid-template-columns:repeat(3,1fr)}
  .r2{grid-template-columns:1fr}
}
</style></head><body>
<div class="layout">

<div class="sidebar">
  <h3>🤖 v9.1</h3>
  {{ avatar_html|safe }}
  <a href="http://127.0.0.1:5007/" class="slink sl-brain">
    <div class="sl-icon">🧠</div><div>Brain</div><div class="sl-port">:5007</div></a>
  <a href="http://127.0.0.1:5009/" target="_blank" class="slink sl-game">
    <div class="sl-icon">🎮</div><div>Games</div><div class="sl-port">:5009</div></a>
  <a href="http://127.0.0.1:5001/" target="_blank" class="slink sl-rep">
    <div class="sl-icon">📋</div><div>Reports</div><div class="sl-port">:5001</div></a>
  <a href="https://LamyaFadlulmolaHamedAli.pythonanywhere.com"
     target="_blank" class="slink sl-plat">
    <div class="sl-icon">🌐</div><div>Platform</div><div class="sl-port">Live</div></a>
  <a href="{{ github_url }}" target="_blank" class="slink sl-gh">
    <div class="sl-icon">📦</div><div>GitHub</div><div class="sl-port">Games</div></a>
  <a href="/auto_report" class="slink"
     style="background:#1a2040;color:var(--yl);border-color:var(--yl)">
    <div class="sl-icon">⚡</div><div>Report</div><div class="sl-port">→:5001</div></a>
</div>

<div class="content">
<div class="android-info">
  📱 <b>Android:</b>
  <div class="android-url">http://{{ local_ip }}:5007</div>
  <div style="font-size:.66em;color:#6ee7b7;margin-top:2px">Same WiFi → browser → URL</div>
</div>

<div class="lv-box">
  <div class="lv-title">🏆 Level {{ s.therapy_level }}: {{ lv_name }}</div>
  <div class="lv-bg"><div class="lv-bar" style="width:{{ lv_pct }}%"></div></div>
  <div style="font-size:.70em;color:var(--mu)">
    {{ s.level_successes }}/3 successes | Total levels: {{ s.total_levels_passed }}</div>
  <div style="font-size:.68em;color:var(--gr);margin-top:3px">{{ s.protocol }}</div>
</div>

<div class="hdr">
  <div style="font-size:1.2em">🤖</div>
  <div>
    <h1>Companion Robot — ABA/ESDM Clinical AI</h1>
    <p style="font-size:.66em;opacity:.8">
      Commander: <b>Lamya</b> | Child: <b>{{ s.name }}</b> ({{ s.age }}) |
      {{ s.session_start }}</p>
  </div>
  <span class="bd live">LIVE</span>
  <span class="bd" style="background:#1a2555;color:var(--bl);border:1px solid var(--bl)">
    {% if s.gemini_ok %}AI:{{ s.gemini_model[:12] }}{% else %}FALLBACK{% endif %}
  </span>
</div>

<div class="row r5" style="margin-bottom:7px">
  <div class="stat"><div class="n n-g">{{ s.score }}</div><div class="l">Score</div></div>
  <div class="stat"><div class="n n-y">{{ s.tokens }}</div><div class="l">Tokens</div></div>
  <div class="stat"><div class="n n-b">{{ s.attention }}%</div><div class="l">Attention</div></div>
  <div class="stat"><div class="n">{{ s.therapy_level }}</div><div class="l">Level</div></div>
  <div class="stat"><div class="n n-g">{{ s.streak }}</div><div class="l">Streak</div></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="T('ov')">📊 Overview</div>
  <div class="tab" onclick="T('ch')">📈 Charts</div>
  <div class="tab" onclick="T('lv')">🏆 Levels</div>
  <div class="tab" onclick="T('as')">📋 IASQ</div>
  <div class="tab" onclick="T('cb')">💬 Chatbot</div>
  <div class="tab" onclick="T('nt')">📝 Notes</div>
  <div class="tab" onclick="T('hl')">💡 Help</div>
  <div class="tab" onclick="T('st')">⚙️ Settings</div>
</div>

<div id="tc-ov" class="tc active">
<div class="row r3">
  <div class="card"><h2>😊 Emotion + Sensors</h2>
    <div style="text-align:center;padding:4px">
      <div class="emo {{ s.emotion }}">{{ s.emotion.upper() }}</div>
      <div style="margin:5px 0">
        <div class="bar-bg"><div class="bar" style="width:{{ s.attention }}%"></div></div>
        <span style="font-size:.66em;color:var(--pu)">{{ s.attention }}%</span></div>
      <div style="font-size:.67em;color:var(--mu)">{{ s.engagement }}</div>
      <div style="font-size:.64em;margin:2px;color:{{ '#34d399' if s.face_detected else '#f87171' }}">
        {{ 'Face OK' if s.face_detected else 'No Face' }}</div>
      <div style="font-size:.63em;color:var(--mu);margin-top:2px">
        E:{{ s.voice_energy|int }} P:{{ s.voice_pitch }}</div>
      <div style="margin:5px 0;text-align:left">
        {% for em,sc in s.emotion_scores.items() %}{% if sc > 0.04 %}
        <div style="display:flex;align-items:center;gap:3px;margin:1px 0">
          <span style="width:46px;font-size:.59em;color:var(--mu)">{{ em[:7] }}</span>
          <div style="flex:1;background:#1f2937;height:5px;border-radius:3px">
            <div style="width:{{ (sc*100)|int }}%;height:5px;border-radius:3px;background:#6366f1"></div></div>
          <span style="font-size:.59em;color:var(--pu);min-width:22px">{{ (sc*100)|int }}%</span>
        </div>{% endif %}{% endfor %}
      </div>
      <div>
        <span class="ab {{ 'aon' if s.hand_raised else 'aoff' }}">Hand</span>
        <span class="ab {{ 'aon' if s.waving else 'aoff' }}">Wave</span>
        <span class="ab {{ 'aon' if s.clapping else 'aoff' }}">Clap</span>
        <span class="ab {{ 'aon' if s.head_tilted else 'aoff' }}">Head</span>
        <span class="ab {{ 'aon' if s.eye_contact else 'aoff' }}">Eyes</span>
        <span class="ab {{ 'aon' if s.blinking else 'aoff' }}">Blink</span>
      </div>
      {% if s.is_speaking %}
      <div style="font-size:.63em;color:var(--bl);margin-top:3px">
        🔊 Lip:{{ (s.lip_sync_value*10)|int }}/10</div>
      {% elif s.listening %}
      <div style="font-size:.63em;color:var(--gr);margin-top:3px">👂 Listening</div>
      {% endif %}
    </div>
  </div>

  <div class="card"><h2>🎮 Controls</h2>
    <form method="POST" action="/cmd">
      <div style="margin-bottom:4px">
        <div style="font-size:.61em;color:var(--mu);margin-bottom:2px">Levels</div>
        <button class="btn" name="c" value="level1">L1 Motor</button>
        <button class="btn" name="c" value="level2">L2 Verbal</button>
        <button class="btn" name="c" value="level3">L3 Social</button>
      </div>
      <div style="margin-bottom:4px">
        <div style="font-size:.61em;color:var(--mu);margin-bottom:2px">Actions</div>
        <button class="btn btn-g" name="c" value="dance">Dance</button>
        <button class="btn btn-y" name="c" value="celebrate">Celebrate</button>
        <button class="btn btn-b" name="c" value="game">Game</button>
        <button class="btn btn-r" name="c" value="break">Break</button>
        <button class="btn" name="c" value="report">Report</button>
      </div>
    </form>
    <div style="font-size:.61em;color:var(--mu);margin-bottom:2px">Skill Videos</div>
    <div style="display:flex;flex-wrap:wrap;gap:2px">
      {% for sk in skills %}
      <form method="POST" action="/skill" style="display:inline">
        <button class="btn btn-y" name="s" value="{{ sk }}"
                style="font-size:.57em;padding:2px 4px;min-height:22px">{{ sk }}</button>
      </form>{% endfor %}
    </div>
    <form method="POST" action="/search" style="display:flex;gap:3px;margin-top:4px">
      <input name="q" placeholder="YouTube search...">
      <button class="btn">Go</button>
    </form>
    <form method="POST" action="/name" style="display:flex;gap:3px;margin-top:3px">
      <input name="n" placeholder="Child name...">
      <button class="btn">Set</button>
    </form>
  </div>

  <div class="card"><h2>💬 Live Session</h2>
    <div class="chat-box" id="cs">
      {% for m in s.session_chat[-20:]|reverse %}
      <div class="cm {{ 'cmp' if m.role=='pepper' else 'cmc' }}">
        <span style="color:{{ 'var(--pu)' if m.role=='pepper' else 'var(--gr)' }};font-size:.59em">
          {{ '🤖' if m.role=='pepper' else '👦 '+s.name }} [{{ m.time }}]
        </span><br>{{ m.text }}
      </div>{% endfor %}
    </div>
    <div style="font-size:.63em;color:var(--mu)">
      {{ s.logs|length }} interactions |
      OK:{{ s.tasks_success }} Fail:{{ s.tasks_fail }}</div>
  </div>
</div>
</div>

<div id="tc-ch" class="tc">
  <div class="row r2">
    <div class="card"><h2>Attention</h2><div class="cw"><canvas id="aC"></canvas></div></div>
    <div class="card"><h2>Score</h2><div class="cw"><canvas id="sC"></canvas></div></div>
  </div>
  <div class="row r2">
    <div class="card"><h2>Emotions</h2><div class="cw"><canvas id="eC"></canvas></div></div>
    <div class="card"><h2>Skills</h2>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:3px;margin-top:4px">
        {% for sk,v in s.skills.items() %}
        <div style="text-align:center">
          <div style="height:48px;background:#1f2937;border-radius:5px;
                      position:relative;overflow:hidden">
            <div style="position:absolute;bottom:0;width:100%;height:{{ v }}%;
                        background:linear-gradient(0deg,#6366f1,#a78bfa);border-radius:5px"></div>
          </div>
          <div style="font-size:.56em;color:var(--mu);margin-top:1px">{{ sk }}</div>
          <div style="font-size:.63em;color:var(--pu);font-weight:700">{{ v }}%</div>
        </div>{% endfor %}
      </div>
    </div>
  </div>
  <div class="card"><h2>Log</h2>
    <div class="log-box">
      {% for lg in s.logs[-40:]|reverse %}
      <div class="li {{ lg.type }}">
        <span style="color:#6366f1">{{ lg.time }}</span>
        <b style="color:var(--pu)">{{ lg.child }}</b>: {{ lg.msg }}
      </div>{% endfor %}
    </div>
    <a href="/export" class="btn btn-g"
       style="display:inline-block;margin-top:4px;text-decoration:none">Export</a>
  </div>
</div>

<div id="tc-lv" class="tc">
  <div class="row r3">
    {% for lnum,ldata in levels.items() %}
    <div class="card"
         style="border-color:{{ 'var(--gr)' if s.therapy_level==lnum else 'var(--bo)' }}">
      <h2 style="color:{{ 'var(--gr)' if s.therapy_level==lnum else '#818cf8' }}">
        {{ '▶️' if s.therapy_level==lnum else '📋' }}
        Level {{ lnum }}: {{ ldata.name }}</h2>
      <div style="font-size:.70em;color:var(--mu);margin-bottom:5px">{{ ldata.protocol }}</div>
      <div style="font-size:.67em;color:var(--mu)">3 successes to advance</div>
      {% if s.therapy_level == lnum %}
      <div style="margin-top:5px">
        <div style="background:#1f2937;border-radius:5px;height:8px;margin:4px 0">
          <div style="width:{{ lv_pct }}%;height:8px;border-radius:5px;
                      background:var(--gr)"></div></div>
        <div style="font-size:.67em;color:var(--gr)">{{ s.level_successes }}/3</div>
      </div>
      <div style="margin-top:4px;font-size:.66em;color:var(--yl)">← CURRENT</div>
      {% elif lnum < s.therapy_level %}
      <div style="margin-top:4px;font-size:.66em;color:var(--gr)">✅ COMPLETE</div>
      {% else %}
      <div style="margin-top:4px;font-size:.66em;color:var(--mu)">🔒 Locked</div>
      {% endif %}
      <div style="margin-top:5px">
        <div style="font-size:.65em;color:var(--mu);margin-bottom:2px">Tasks:</div>
        {% for task in ldata.tasks[:3] %}
        <div style="font-size:.63em;color:var(--tx);padding:1px 0">
          • {{ task.instruction[:32] }}</div>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div id="tc-as" class="tc">
  <div class="row r2">
    <div class="card"><h2>IASQ Screening</h2>
      {% if s.iasq_result %}
      <div style="background:#051a0f;border-radius:7px;padding:7px;
                  margin-bottom:7px;border:1px solid var(--gr)">
        <div style="font-size:.77em;color:var(--gr);font-weight:700">{{ s.iasq_result }}</div>
        <div style="font-size:.67em;color:var(--mu)">{{ s.iasq_score }}/50</div>
      </div>{% endif %}
      <form method="POST" action="/iasq">
        {% for i,q in qs.items() %}
        <div style="background:#0a1020;border-radius:6px;padding:6px;margin:3px 0">
          <div style="font-size:.70em;margin-bottom:3px">{{ i }}. {{ q.q }}</div>
          <div style="display:flex;gap:7px;flex-wrap:wrap">
            {% for j in range(5) %}
            <label style="cursor:pointer;font-size:.63em;color:var(--mu)">
              <input type="radio" name="q{{ i }}" value="{{ j }}"
                     style="width:auto;margin:0 3px">{{ j }}
            </label>{% endfor %}
          </div>
        </div>{% endfor %}
        <button class="btn btn-g" style="width:100%;margin-top:5px;padding:6px">
          Calculate</button>
      </form>
    </div>
    <div class="card"><h2>Result</h2>
      {% if s.iasq_result %}
      {% set pct = s.iasq_score * 2 %}
      <div style="text-align:center;padding:10px">
        <div style="font-size:1.7em;font-weight:700;
                    color:{{ '#34d399' if s.iasq_score<=20 else '#fbbf24' if s.iasq_score<=35 else '#f87171' }}">
          {{ s.iasq_result }}</div>
        <div style="background:#1f2937;border-radius:5px;height:6px;margin:7px 0">
          <div style="width:{{ pct }}%;height:6px;border-radius:3px;
                      background:{{ '#34d399' if s.iasq_score<=20 else '#fbbf24' if s.iasq_score<=35 else '#f87171' }}">
          </div></div>
        <div style="font-size:.67em;color:var(--mu)">{{ s.iasq_score }}/50</div>
      </div>{% else %}
      <div style="text-align:center;padding:20px;color:var(--mu);font-size:.77em">
        Complete IASQ test.</div>{% endif %}
    </div>
  </div>
</div>

<div id="tc-cb" class="tc">
  <div class="row r2">
    <div class="card"><h2>Parent Chatbot (Arabic + English)</h2>
      <div class="chat-box" id="cp">
        {% for m in s.parent_chat[-20:]|reverse %}
        <div class="cm {{ 'cmp' if m.role=='pepper' else 'cmr' }}">
          <span style="color:{{ 'var(--pu)' if m.role=='pepper' else 'var(--bl)' }};font-size:.59em">
            {{ 'Pepper' if m.role=='pepper' else 'Parent' }} [{{ m.time }}]
          </span><br>{{ m.text }}
        </div>{% endfor %}
        {% if not s.parent_chat %}
        <div style="color:var(--mu);text-align:center;padding:14px;font-size:.72em">
          Ask about autism / اسأل عن التوحد</div>{% endif %}
      </div>
      <form method="POST" action="/parent_ask" style="display:flex;gap:4px">
        <input name="question" placeholder="اسأل... / Ask...">
        <button class="btn btn-g">Ask</button>
      </form>
    </div>
    <div class="card"><h2>Quick Questions</h2>
      {% for q in qqs %}
      <form method="POST" action="/parent_ask">
        <button class="btn" name="question" value="{{ q }}"
                style="width:100%;text-align:left;margin:1px 0;
                       font-size:.64em;padding:3px 5px;min-height:26px">{{ q }}</button>
      </form>{% endfor %}
    </div>
  </div>
</div>

<div id="tc-nt" class="tc">
  <div class="row r2">
    <div class="card"><h2>Add Note</h2>
      <form method="POST" action="/note">
        <select name="cat" style="margin-bottom:4px">
          <option>behavior</option><option>progress</option>
          <option>concern</option><option>milestone</option>
        </select>
        <textarea name="note" placeholder="Observation..."></textarea>
        <button class="btn btn-g" style="width:100%;margin-top:4px;padding:6px">Save</button>
      </form>
    </div>
    <div class="card"><h2>History</h2>
      <div style="max-height:230px;overflow-y:auto">
        {% for n in s.parent_notes[-15:]|reverse %}
        <div style="background:#0a1020;border-left:3px solid var(--pu);
                    padding:5px;margin:2px 0;font-size:.69em">
          <span style="color:var(--pu);font-size:.64em;font-weight:700">
            {{ n.category.upper() }}</span>
          <span style="color:var(--mu);font-size:.64em"> {{ n.time }}</span>
          <br>{{ n.text }}
        </div>{% endfor %}
      </div>
    </div>
  </div>
</div>

<div id="tc-hl" class="tc">
  <div class="row r3">
    <div class="hc"><div class="hct">Level 1: ABA Motor</div>
      <div class="hcb">Physical imitation tasks verified by MediaPipe skeleton.
        33 body landmarks. Wrist→nose = touch. Wrist above shoulder = raised hand.</div>
      <div class="tip">3 successes unlock Level 2.</div></div>
    <div class="hc"><div class="hct">Level 2: DTT Verbal</div>
      <div class="hcb">Language tasks. faster-whisper (energy=10) hears whispers.
        Keywords verified by speech recognition.</div>
      <div class="tip">3 successes unlock Level 3.</div></div>
    <div class="hc"><div class="hct">Level 3: ESDM Social</div>
      <div class="hcb">Full sentences, emotions, social responses.
        YouTube video reward when level cleared!</div>
      <div class="tip">Ask child what video they want! 🎬</div></div>
    <div class="hc"><div class="hct">EAR Blink Detection</div>
      <div class="hcb">Eye Aspect Ratio via FaceMesh (468 landmarks).
        EAR &lt; 0.20 = blink. EAR &gt; 0.25 = eye contact.</div>
      <div class="tip">Works with face mesh overlay in Window 2.</div></div>
    <div class="hc"><div class="hct">Lip-Sync</div>
      <div class="hcb">HeadPitch joint in PyBullet moves with voice energy.
        Avatar mouth opens proportionally. Watch Window 1!</div>
      <div class="tip">lip_sync_value drives both PyBullet + avatar.</div></div>
    <div class="hc"><div class="hct">Android Access</div>
      <div class="hcb">Same WiFi → browser:<br>
        <b style="color:var(--gr)">http://{{ local_ip }}:5007</b></div>
      <div class="tip">3 windows: PyBullet + Emotion + Live Session.</div></div>
  </div>
  <div class="card" style="margin-top:7px"><h2>Session Info</h2>
    <div style="font-size:.69em;color:#9ca3af;line-height:1.8">
      Child: <b style="color:var(--tx)">{{ s.name }}</b> |
      Level {{ s.therapy_level }} | {{ s.session_date }}<br>
      Score: <b style="color:var(--pu)">{{ s.score }}</b> |
      Tokens: <b style="color:var(--yl)">{{ s.tokens }}</b> |
      Levels: {{ s.total_levels_passed }}<br>
      OK: {{ s.tasks_success }} | Fail: {{ s.tasks_fail }} |
      Fallbacks: {{ s.api_fallback_count }}
    </div>
    <div style="margin-top:5px;display:flex;gap:4px">
      <a href="/export" class="btn btn-g" style="text-decoration:none">Export</a>
      <a href="/auto_report" class="btn btn-b" style="text-decoration:none">Report→:5001</a>
    </div>
  </div>
</div>

<div id="tc-st" class="tc">
  <div class="row r2">
    <div class="card"><h2>Child Profile</h2>
      <form method="POST" action="/update_child">
        <label style="font-size:.66em;color:var(--mu)">Name</label>
        <input name="name" value="{{ s.name }}" style="margin-bottom:4px">
        <label style="font-size:.66em;color:var(--mu)">Age</label>
        <input name="age" type="number" value="{{ s.age }}" min="1" max="18" style="margin-bottom:4px">
        <label style="font-size:.66em;color:var(--mu)">Diagnosis</label>
        <select name="diagnosis" style="margin-bottom:4px">
          <option {{ 'selected' if s.diagnosis=='ASD Level 1' }}>ASD Level 1</option>
          <option {{ 'selected' if s.diagnosis=='ASD Level 2' }}>ASD Level 2</option>
          <option {{ 'selected' if s.diagnosis=='ASD Level 3' }}>ASD Level 3</option>
          <option>Suspected ASD</option>
        </select>
        <button class="btn btn-g" style="width:100%;padding:6px">Save</button>
      </form>
    </div>
    <div class="card"><h2>System</h2>
      <div style="font-size:.69em;color:var(--mu);line-height:1.9">
        Model: {{ s.gemini_model }}<br>
        API/min: {{ s.api_calls_this_min }}/14<br>
        Fallbacks: {{ s.api_fallback_count }}<br>
        Mic: energy=10<br>
        Whisper: {{ whisper_ok }}<br>
        Skeleton: MediaPipe Pose<br>
        EAR: FaceMesh 468pts<br>
        Lip-sync: HeadPitch<br>
        Android: http://{{ local_ip }}:5007
      </div>
    </div>
  </div>
</div>

</div></div>

<script>
function T(n){
  document.querySelectorAll('.tc').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tc-'+n).classList.add('active');
  event.target.classList.add('active');}

const AD={{ att_h|tojson }}, SD={{ sc_h|tojson }}, ED={{ ed|tojson }};
const LB = Array.from({length:AD.length},(_,i)=>i+1);
const CO = {responsive:true,maintainAspectRatio:false,
  plugins:{legend:{labels:{color:'#9ca3af',font:{size:8}}}},
  scales:{x:{ticks:{color:'#6b7280',font:{size:7}},grid:{color:'#1f2937'}},
          y:{ticks:{color:'#6b7280',font:{size:7}},grid:{color:'#1f2937'}}}};

if(document.getElementById('aC'))
  new Chart(document.getElementById('aC'),{type:'line',
    data:{labels:LB,datasets:[{label:'Att%',data:AD,
      borderColor:'#6366f1',backgroundColor:'rgba(99,102,241,0.1)',
      tension:0.4,fill:true,pointRadius:1}]},
    options:{...CO,scales:{...CO.scales,y:{...CO.scales.y,min:0,max:100}}}});

if(document.getElementById('sC'))
  new Chart(document.getElementById('sC'),{type:'bar',
    data:{labels:LB,datasets:[{label:'Score',data:SD,
      backgroundColor:'rgba(167,139,250,0.5)',borderColor:'#a78bfa',borderWidth:1}]},
    options:CO});

if(document.getElementById('eC')&&Object.keys(ED).length>0){
  const EC={happy:'#34d399',sad:'#60a5fa',angry:'#f87171',
    neutral:'#9ca3af',fear:'#fbbf24',surprised:'#c084fc',
    joyful:'#34d399',confused:'#fb923c'};
  new Chart(document.getElementById('eC'),{type:'doughnut',
    data:{labels:Object.keys(ED),datasets:[{data:Object.values(ED),
      backgroundColor:Object.keys(ED).map(e=>EC[e]||'#6366f1')}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'right',labels:{color:'#9ca3af',font:{size:8}}}}}});}

['cs','cp'].forEach(id=>{
  const el=document.getElementById(id);
  if(el) el.scrollTop=el.scrollHeight;});
</script>
</body></html>"""

SKILLS_L = ["emotions","colors","numbers","alphabet",
            "animals","shapes","greetings","sharing",
            "wash face","brush teeth"]
QUICK_QS = [
    "My child has a meltdown, what should I do?",
    "How do I improve eye contact?",
    "Best way to teach toilet training?",
    "How to handle repetitive behaviors?",
    "كيف أتعامل مع نوبات الغضب؟",
    "كيف أساعد طفلي على التواصل البصري؟",
    "ما هي أفضل طريقة لتعليم طفلي؟",
    "How to help with sleep problems?",
    "What is ESDM therapy?",
    "كيف أحسن مهارات التواصل لطفلي؟",
]
IASQ_QS = [
    {"q":"Does your child make eye contact?"},
    {"q":"Does your child respond to their name?"},
    {"q":"Does your child point to show interest?"},
    {"q":"Does your child play with other children?"},
    {"q":"Does your child use words to communicate?"},
    {"q":"Does your child show repetitive behaviors?"},
    {"q":"Is your child sensitive to sounds?"},
    {"q":"Does your child have meltdowns?"},
    {"q":"Does your child follow simple instructions?"},
    {"q":"Does your child show interest in others?"},
]

_gemini = None

@brain_app.route("/")
@brain_app.route("/<path:path>")
def brain_catch(path=""):
    ed = {}
    for e in ST["emo_history"]: ed[e] = ed.get(e,0)+1
    qs = {i+1:q for i,q in enumerate(IASQ_QS)}
    lv     = ST["therapy_level"]
    lv_d   = LEVELS.get(lv, {})
    lv_pct = min(100, int(ST["level_successes"]/3*100))
    return render_template_string(
        BRAIN_HTML, s=ST,
        skills=SKILLS_L, qqs=QUICK_QS, qs=qs,
        att_h=ST["att_history"][-40:],
        sc_h=ST["score_history"][-40:],
        ed=ed, local_ip=LOCAL_IP, github_url=GITHUB_URL,
        avatar_css=AVATAR_CSS, avatar_html=build_avatar(),
        lv_name=lv_d.get("name",""),
        lv_pct=lv_pct, levels=LEVELS,
        whisper_ok=str(WHISPER_OK))

@brain_app.route("/cmd", methods=["GET","POST"])
def brain_cmd():
    c = (request.form.get("c","") or request.args.get("c",""))
    if c:
        if c=="level1":
            ST["therapy_level"]=1; ST["level_successes"]=0
            ST["protocol"]="ABA-Motor"
        elif c=="level2":
            ST["therapy_level"]=2; ST["level_successes"]=0
            ST["protocol"]="DTT-Verbal"
        elif c=="level3":
            ST["therapy_level"]=3; ST["level_successes"]=0
            ST["protocol"]="ESDM-Social"
        else:
            ST["sim_cmd"] = c
        if c=="report" and _gemini:
            r = _gemini.generate_report()
            ST["reports"].append({
                "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content":r})
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/auto_report")
def brain_auto():
    if _gemini:
        r = _gemini.generate_report()
        ST["reports"].append({
            "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content":r})
    return redirect("http://127.0.0.1:5001/")

@brain_app.route("/skill", methods=["GET","POST"])
def brain_skill():
    s = (request.form.get("s","") or request.args.get("s",""))
    webbrowser.open("https://www.youtube.com/results?search_query="
                    + urllib.parse.quote(s+" autism children educational"))
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/search", methods=["GET","POST"])
def brain_search():
    q = (request.form.get("q","") or request.args.get("q",""))
    webbrowser.open("https://www.youtube.com/results?search_query="
                    + urllib.parse.quote(q+" autism"))
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/name", methods=["GET","POST"])
def brain_name():
    n = (request.form.get("n","") or request.args.get("n","")).strip().title()
    if n: ST["name"]=n; ST["known"]=True
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/parent_ask", methods=["GET","POST"])
def brain_pask():
    q = (request.form.get("question","") or request.args.get("question","")).strip()
    if q and _gemini:
        ST["parent_chat"].append({
            "role":"parent","text":q,
            "time":datetime.now().strftime("%H:%M:%S")})
        ans = _gemini.parent_ask(q)
        ST["parent_chat"].append({
            "role":"pepper","text":ans,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["parent_chat"]) > 40:
            ST["parent_chat"] = ST["parent_chat"][-40:]
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/iasq", methods=["GET","POST"])
def brain_iasq():
    total = sum(int(request.form.get(f"q{i}",0)) for i in range(1,11))
    r = "Low Risk ✅" if total<=20 else "Medium Risk ⚠️" if total<=35 else "High Risk 🔴"
    ST["iasq_score"]=total; ST["iasq_result"]=r
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/note", methods=["GET","POST"])
def brain_note():
    note = (request.form.get("note","") or request.args.get("note","")).strip()
    cat  = (request.form.get("cat","other") or "other")
    if note:
        ST["parent_notes"].append({
            "time":datetime.now().strftime("%H:%M:%S"),
            "text":note, "category":cat})
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/update_child", methods=["GET","POST"])
def brain_uc():
    ST["name"]      = (request.form.get("name","Friend") or "Friend").strip().title()
    ST["age"]       = int(request.form.get("age",6) or 6)
    ST["diagnosis"] = (request.form.get("diagnosis","ASD Level 2") or "ASD Level 2")
    return redirect("http://127.0.0.1:5007/")

@brain_app.route("/export")
def brain_export():
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    return jsonify({"saved":fn})

@brain_app.route("/api/state")
def brain_api():
    return jsonify({
        "name":ST["name"], "emotion":ST["emotion"],
        "attention":ST["attention"], "score":ST["score"],
        "therapy_level":ST["therapy_level"],
        "level_successes":ST["level_successes"],
        "protocol":ST["protocol"],
        "gemini_ok":ST["gemini_ok"],
        "is_speaking":ST["is_speaking"],
        "listening":ST["listening"],
        "lip_sync_value":round(ST["lip_sync_value"],2),
        "local_ip":LOCAL_IP,
    })

@brain_app.errorhandler(404)
def b404(e): return redirect("http://127.0.0.1:5007/"), 302

@brain_app.errorhandler(405)
def b405(e): return redirect("http://127.0.0.1:5007/"), 302

# ═══════════════════════════════════════════════════════════════
# 15. SERVER RUNNER
# ═══════════════════════════════════════════════════════════════
def run_server(app, port, name):
    from werkzeug.serving import make_server
    try:
        srv = make_server('0.0.0.0', port, app, threaded=True)
        srv.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(f"✅ {name}: http://{LOCAL_IP}:{port}/")
        srv.serve_forever()
    except Exception as e: print(f"⚠️  {name}: {e}")

# ═══════════════════════════════════════════════════════════════
# 16. THERAPY CONTROLLER — 3-Success Rule
# ═══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self, g, v, m, d, s, a):
        self.g=g; self.v=v; self.m=m
        self.d=d; self.s=s; self.a=a
        self.running = False
        self._task_idx = 0

    def _speak(self, text):
        clean = self.a.process(str(text))
        if self.s.ok: self.s.show_text(clean[:55])
        self.v.say(clean)

    def _ask(self, prompt):
        resp = self.g.ask(prompt)
        self._speak(resp); return resp

    def run(self):
        self.running = True
        # Name
        name = self.m.get_name(self.v)
        lv   = ST["therapy_level"]
        lv_n = LEVELS[lv]["name"]
        self._ask(
            f"Child name is {name}. Give warm ABA/ESDM greeting! [WAVE] "
            f"Explain Level {lv} ({lv_n}) therapy. "
            "Make it exciting! 'Ready? Your turn! 🎯'")
        time.sleep(0.5)
        self.m.listen_bg(self._on_speech)

        last_em = ST["emotion"]; em_t = time.time()

        while self.running:
            # Silence check
            if time.time()-ST["last_sound"] > 12:
                ST["last_sound"] = time.time()
                self.v.say(EMPATHY.get("silence"), wait=False)

            # Emotion change
            curr = ST["emotion"]
            if curr != last_em and time.time()-em_t > 8:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    self._ask(f"Child became {curr}. [HUG] Comfort first!")

            # Dashboard commands
            self._handle_cmd()

            # Run one therapy task
            lv = ST["therapy_level"]
            tasks = LEVELS[lv]["tasks"]
            task  = tasks[self._task_idx % len(tasks)]
            self._task_idx += 1
            ST["current_task"] = task
            ST["protocol"] = LEVELS[lv]["protocol"]

            success = self._run_task(task)
            if success:
                self._on_success(task)
            else:
                self._on_fail(task)
            time.sleep(0.3)

    def _run_task(self, task):
        """Run one task with prompt hierarchy"""
        name     = ST["name"]
        instr    = task["instruction"]
        vtype    = task["verify"]
        prompts  = task["prompts"]
        ST["task_success"]  = False
        ST["two_step_phase"] = 0

        # Set camera verify
        if vtype in ["touch_nose","clap","raise_hand","wave","head_tilt","blink","two_step"]:
            ST["verify_action"]  = vtype
            ST["verify_result"]  = False
            ST["verify_timeout"] = time.time() + 15

        # SD — Discriminative Stimulus
        resp = self.g.ask(
            f"ABA Level {ST['therapy_level']} task: '{instr}' for {name}. "
            f"Em:{ST['emotion']}. Give warm clinical instruction. "
            "'Ready? Your turn! 🎯'")
        self._speak(resp)

        # Wait for response with prompt hierarchy
        for attempt in range(3):
            ST["prompt_attempt"] = attempt
            ok = self._wait_task(task, timeout=12)
            if ok: return True
            # Prompt hierarchy: verbal → gestural → model
            if attempt < len(prompts):
                self.v.say(f"{name}... {prompts[attempt]} 🎯", wait=False)
                time.sleep(0.5)

        ST["verify_action"] = None
        return False

    def _wait_task(self, task, timeout=12):
        vtype   = task["verify"]
        keyword = task.get("keyword","")
        deadline = time.time()+timeout

        while time.time() < deadline:
            # Camera-based
            if vtype in ["touch_nose","clap","raise_hand",
                          "wave","head_tilt","blink","two_step"]:
                if ST["verify_result"]:
                    ST["verify_result"] = False; return True
                if vtype=="clap" and ST["clapping"]: return True
                if vtype=="wave" and ST["waving"]: return True
                if vtype=="raise_hand" and ST["hand_raised"]: return True
                if vtype=="blink" and ST["blinking"]: return True
                if vtype=="head_tilt" and ST["head_tilted"]: return True

            # Speech-based
            elif vtype=="speech_keyword" and keyword:
                if keyword.lower() in ST.get("last_speech_text","").lower():
                    return True

            elif vtype in ["speech_any","speech"]:
                if (ST["last_sound"]>time.time()-3 and
                    len(ST.get("last_speech_text",""))>0):
                    return True

            elif vtype=="speech_number":
                if any(c.isdigit() for c in ST.get("last_speech_text","")):
                    return True

            elif vtype=="speech_sentence":
                if len(ST.get("last_speech_text","").split()) >= 3:
                    return True

            # Positive engagement = success
            if (ST["emotion"] in ["happy","joyful"] and
                ST["attention"] > 70): return True

            time.sleep(0.2)
        return False

    def _on_success(self, task):
        name = ST["name"]
        ST["level_successes"] += 1
        ST["score"]           += task.get("tokens",2)*5
        ST["tokens"]          += task.get("tokens",2)
        ST["tasks_success"]   += 1
        ST["streak"]          += 1
        # Skills
        sk_map = {1:"motor",2:"verbal",3:"social"}
        sk = sk_map.get(ST["therapy_level"],"motor")
        ST["skills"][sk] = min(100, ST["skills"][sk]+random.randint(1,3))
        ST["skills"]["attention"] = min(100, ST["skills"]["attention"]+random.randint(0,2))
        LOG(f"✅ L{ST['therapy_level']} success {ST['level_successes']}/3","success")

        # Check 3-success rule → level up
        if ST["level_successes"] >= 3:
            self._level_up()
            return

        if ST["streak"]%3==0:
            self._ask(f"{name} streak {ST['streak']}! [CELEBRATE][DANCE]")
        else:
            self.v.say(EMPATHY.get("task_ok"), wait=False)

        # YouTube reward at Level 3
        if ST["therapy_level"]==3 and task.get("reward")=="youtube":
            ST["youtube_pending"] = True
            self._ask(
                f"{name} EARNED a video reward! [CELEBRATE] "
                "Ask them what video they want to watch! 🎬")

        # Auto-report every 9 tasks
        if ST["tasks_success"] % 9 == 0 and _gemini:
            r = _gemini.generate_report()
            ST["reports"].append({
                "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content":r})

    def _on_fail(self, task):
        ST["streak"]      = 0
        ST["tasks_fail"] += 1
        self.v.say(EMPATHY.get("task_retry"), wait=False)

    def _level_up(self):
        """3-success rule: advance to next level"""
        old_lv = ST["therapy_level"]
        new_lv = min(old_lv+1, 3)
        ST["therapy_level"]    = new_lv
        ST["level_successes"]  = 0
        ST["total_levels_passed"] += 1
        ST["protocol"] = LEVELS[new_lv]["protocol"]
        ST["skills"]["imitation"] = min(100, ST["skills"]["imitation"]+10)
        lv_name = LEVELS[new_lv]["name"]
        self._ask(
            f"{ST['name']} COMPLETED Level {old_lv} with 3 successes! "
            f"[LEVEL_UP][CELEBRATE][DANCE] "
            f"Starting Level {new_lv}: {lv_name}! "
            "Explain what we will do next! [WAVE]")
        LOG(f"🏆 LEVEL UP {old_lv}→{new_lv}","success")
        self._task_idx = 0

    def _handle_cmd(self):
        cmd = ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"] = None
        if cmd=="dance":
            self._ask("Dance joyfully! [DANCE][CELEBRATE]")
        elif cmd=="game":
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games! [GAME]",wait=False)
        elif cmd=="celebrate":
            self._ask("Big celebration! [CELEBRATE][CLAP][DANCE]")
        elif cmd=="break":
            self.v.say("Break time! Relax.",wait=False)
        elif cmd=="report" and _gemini:
            r = _gemini.generate_report()
            ST["reports"].append({
                "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content":r})

    def _on_speech(self, text):
        """Smart response to ANY child utterance"""
        ST["last_sound"]        = time.time()
        ST["waiting_for_child"] = False
        ST["last_speech_text"]  = text
        if not text: return
        t    = text.lower()
        name = ST["name"]

        if text == "[sound]":
            self.v.say(f"I heard you {name}! Great!",wait=False); return
        if ST["is_speaking"]: self.v.stop(); time.sleep(0.1)

        # Name learning
        if not ST["known"]:
            n = self.m._extract(text)
            if n:
                ST["name"]=n; ST["known"]=True
                self._ask(f"Welcome {n}! [WAVE] 🎯")
            return

        # YouTube pending
        if ST.get("youtube_pending"):
            ST["youtube_pending"] = False
            self._speak(self.a.process(
                f"[YOUTUBE: {text} autism children educational]"))
            return

        # Game
        if any(w in t for w in ["game","play","العب","لعبة"]):
            webbrowser.open(GAME_URL)
            self.v.say(f"Opening games {name}! [GAME] 🎮",wait=False); return

        # Educational
        edu_kw = ["how","what","why","where","when","who","show","teach",
                  "كيف","ما هو","ما هي","لماذا","أين","متى","أرني"]
        if any(w in t for w in edu_kw):
            resp = self.g.ask(
                f"Child asked: '{text}'. Answer clearly! "
                "Add [YOUTUBE: topic] for educational video. 🎯")
            self._speak(resp); return

        # Emotion
        emo_kw = ["happy","sad","angry","scared","love","tired","hurt",
                  "حزين","خايف","زعلان","مبسوط","تعبان"]
        if any(w in t for w in emo_kw):
            resp = self.g.ask(
                f"Child expressed: '{text}'. "
                "Respond with clinical empathy! [HUG] 🎯")
            self._speak(resp); return

        # Default smart response
        resp = self.g.ask(
            f"Child said: '{text}'. "
            "Respond therapeutically using ABA/ESDM. "
            "Build on context. 'Ready? Your turn! 🎯'")
        self._speak(resp)

# ═══════════════════════════════════════════════════════════════
# 17. MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    global _gemini

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  AI-DRIVEN COMPANION ROBOT FOR CHILDREN WITH AUTISM         ║
║  companion_robot_genesis.py                                 ║
║  Commander: Lamya | Omdurman Islamic University             ║
╠══════════════════════════════════════════════════════════════╣
║  Level 1: ABA Motor | Level 2: DTT Verbal | Level 3: ESDM  ║
║  3-Success Rule | MediaPipe Pose+FaceMesh | EAR Blink       ║
║  Lip-Sync HeadPitch | faster-whisper | GPU Accelerated      ║
╠══════════════════════════════════════════════════════════════╣
║  Laptop:  http://127.0.0.1:5007                             ║
║  Android: http://{LOCAL_IP}:5007                            ║
╚══════════════════════════════════════════════════════════════╝
""")

    # Start Flask servers (3 separate threads)
    for app, port, name in [
        (game_app,  PORT_GAME,   "Game"),
        (rep_app,   PORT_REPORT, "Reports"),
        (brain_app, PORT_BRAIN,  "Brain"),
    ]:
        threading.Thread(
            target=run_server, args=(app,port,name), daemon=True).start()
        time.sleep(0.4)
    time.sleep(0.8)

    # Initialize all systems
    gemini  = GeminiBrain(); _gemini = gemini
    voice   = Voice()
    camera  = Camera()
    vision  = VisionEngine()
    display = Display(vision, camera)
    mic     = Mic()

    # PyBullet (Window 1)
    sim    = PepperSim()
    pepper = sim.launch()
    acts   = Actions(pepper)

    # Start lip-sync PyBullet thread
    threading.Thread(
        target=acts.run_lip_sync_pybullet, daemon=True).start()

    time.sleep(1.5)
    voice.say(
        "Welcome! I am Pepper, your AI companion and therapist! "
        "Commander Lamya, all systems active! "
        "Starting Level 1 ABA motor therapy!",
        wait=False)
    if pepper:
        threading.Thread(target=acts._wave, daemon=True).start()

    # Start therapy controller
    ctrl = TherapyCtrl(gemini, voice, mic, display, sim, acts)
    threading.Thread(target=ctrl.run, daemon=True).start()

    print(f"""
{'='*62}
✅ COMPANION ROBOT ACTIVE
{'='*62}
Window 1: PyBullet (auto-opened) — Lip-sync HeadPitch
Window 2: Emotion + Skeleton + EAR (600x600)
Window 3: Live Session + Avatar (820x520)

Laptop  → http://127.0.0.1:{PORT_BRAIN}/
Android → http://{LOCAL_IP}:{PORT_BRAIN}/
Games   → {GAME_URL}
Whisper → {WHISPER_OK}
{'='*62}
Commands: stats | level1/2/3 | report | name X | stop | exit
{'='*62}
""")

    while getattr(display, 'running', True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl = cmd.lower()

            if cl in ["q","exit","quit"]:
                ctrl.running=False; display.stop(); break
            elif cl in ["stop","interrupt"]:
                voice.stop(); print("🛑 Stopped!")
            elif cl=="stats":
                dur = int((time.time()-ST["uptime"])/60)
                lv  = ST["therapy_level"]
                print(f"\n{'─'*50}")
                print(f"  Child:      {ST['name']}")
                print(f"  Level:      {lv} ({LEVELS[lv]['name']})")
                print(f"  Successes:  {ST['level_successes']}/3")
                print(f"  Score:      {ST['score']}")
                print(f"  Tokens:     {ST['tokens']}")
                print(f"  Emotion:    {ST['emotion']}")
                print(f"  Attention:  {ST['attention']}%")
                print(f"  Eye EAR:    {ST.get('face_mesh_landmarks',{}).get('ear_avg',0):.3f}")
                print(f"  Lip-sync:   {ST['lip_sync_value']:.2f}")
                print(f"  Levels:     {ST['total_levels_passed']}")
                print(f"  OK/Fail:    {ST['tasks_success']}/{ST['tasks_fail']}")
                print(f"  Duration:   {dur} min")
                print(f"  Whisper:    {WHISPER_OK}")
                print(f"  Android:    http://{LOCAL_IP}:{PORT_BRAIN}/")
                print(f"{'─'*50}\n")
            elif cl in ["level1","level2","level3"]:
                lv = int(cl[-1])
                ST["therapy_level"] = lv
                ST["level_successes"] = 0
                ST["protocol"] = LEVELS[lv]["protocol"]
                print(f"✅ Level {lv}: {LEVELS[lv]['name']}")
            elif cl=="report":
                if _gemini:
                    r = _gemini.generate_report()
                    ST["reports"].append({
                        "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "content":r})
                    print("📋 Report generated → Port 5001")
            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                ST["name"]=n; ST["known"]=True
                voice.say(f"Hello {n}! Welcome!",wait=False)
            else:
                ctrl._on_speech(cmd)

        except (KeyboardInterrupt, EOFError): break

    # Shutdown
    ctrl.running=False; display.stop()
    if _gemini:
        r = _gemini.generate_report()
        ST["reports"].append({
            "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content":r})
    voice.say("Goodbye! Amazing session today!",wait=False)
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f: json.dump(ST,f,indent=2,default=str)
    print(f"\n📄 Saved: {fn}")
    print("✅ Goodbye Commander Lamya!")

if __name__=="__main__":
    main()
