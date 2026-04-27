#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  UNIFIED AI THERAPY HUB - COMPLETE PLATFORM                        ║
║  Port 5001: Master Dashboard (Single Source of Truth)              ║
║  Port 5007: AI Brain (Gemini 1.5)                                  ║
║  Port 5009: Game & Learning Server                                  ║
║                                                                      ║
║  Features:                                                           ║
║  ✅ Gemini AI (multi-model fallback)                                ║
║  ✅ 9-Emotion Detection (DeepFace + OpenCV)                         ║
║  ✅ Action Verification (raise hand, clap, wave)                    ║
║  ✅ ABA/DTT/TEACCH/TIE protocols                                    ║
║  ✅ Interruptible speech                                             ║
║  ✅ energy_threshold=10 (whisper detection)                         ║
║  ✅ PyBullet simulation                                              ║
║  ✅ Mini windows (320x240)                                          ║
║  ✅ YouTube auto-search                                              ║
║  ✅ Reverse proxy (no 404s)                                         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ── SUPPRESS NOISE ──────────────────────────────────────────────────
import os, sys, ctypes, warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
warnings.filterwarnings('ignore')
try:
    _a = ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

# ── IMPORTS ─────────────────────────────────────────────────────────
import cv2, numpy as np, threading, time, random
import json, math, re, webbrowser, urllib.parse, queue
import pyttsx3, speech_recognition as sr
from flask import (Flask, request, jsonify,
                   render_template_string, redirect)
from datetime import datetime
import pybullet as p, pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')
import google.generativeai as genai
import requests as http_req

# ── PORTS ────────────────────────────────────────────────────────────
PORT_MASTER = 5001   # Single Source of Truth
PORT_AI     = 5007   # Gemini Brain
PORT_GAME   = 5009   # Games

# ── GEMINI ───────────────────────────────────────────────────────────
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)

THERAPY_PROMPT = """You are Pepper, a certified pediatric robotic therapist for ASD children.
Commander: Lamya (Lead Developer - treat her with highest respect).

CLINICAL PROTOCOLS: ABA, DTT, TEACCH, TIE
CORE RULES:
- Max 2 short sentences per response
- Immediate positive reinforcement  
- Use child's name constantly
- Ultra patient, warm, enthusiastic

ACTION TOKENS (embed in response):
[WAVE][CLAP][NOD][DANCE][POINT][HUG][CELEBRATE][THINK]

TRIGGERS:
[YOUTUBE: query] → educational video
[GAME] → open game server
[REWARD: N] → give N stars (1-5)
[VERIFY: action] → camera verifies child did action

EMOTION RESPONSE:
- happy/joy → [CELEBRATE] advance task [REWARD:3]
- sad/fear → [HUG] easier task, comfort
- angry → [NOD] breathing, pause tasks
- confused → [THINK] re-explain simply
- surprised → share excitement

ALWAYS end with one clear task or question."""

# ── PLATFORM STATE ───────────────────────────────────────────────────
S = {
    # Child
    "name": "Friend", "known": False,
    "age": 6, "diagnosis": "ASD Level 2",

    # Perception
    "emotion": "neutral",
    "emotion_scores": {},
    "emotion_9": {
        "happy":0,"sad":0,"angry":0,"fear":0,
        "surprise":0,"disgust":0,"neutral":1,
        "joy":0,"confused":0
    },
    "face_detected": False,
    "attention": 70,
    "engagement": "moderate",
    "hand_raised": False,
    "waving": False,
    "clapping": False,
    "verify_action": None,
    "verify_result": False,

    # Session
    "protocol": "GREETING",
    "difficulty": "easy",
    "is_speaking": False,
    "interrupt": False,
    "last_sound": time.time(),
    "clap_detected": False,
    "current_task": None,
    "task_success": False,

    # Progress
    "score": 0, "tokens": 0,
    "stars_today": 0, "streak": 0,
    "skills": {
        "emotions":50,"social":50,
        "motor":50,"communication":50,"focus":50
    },

    # History (for charts)
    "att_history":   [],
    "score_history": [],
    "emo_history":   [],
    "time_labels":   [],

    # Logs & notes
    "logs": [], "parent_notes": [],
    "chat_history": [],       # parent chatbot
    "session_chat": [],       # live session

    # Assessment
    "iasq_score": None, "iasq_result": None,

    # Control
    "sim_cmd": None,
    "gemini_ok": False,
    "session_start": datetime.now().strftime("%H:%M"),
    "uptime_start": time.time(),
}

_log_lock = threading.Lock()

def log(msg, t="info", proto=None):
    with _log_lock:
        e = {
            "time":  datetime.now().strftime("%H:%M:%S"),
            "msg":   str(msg)[:120], "type": t,
            "proto": proto or S["protocol"],
            "emo":   S["emotion"],
            "child": S["name"],
        }
        S["logs"].append(e)
        if len(S["logs"]) % 3 == 0:
            S["att_history"].append(S["attention"])
            S["score_history"].append(S["score"])
            S["emo_history"].append(S["emotion"])
            S["time_labels"].append(
                datetime.now().strftime("%H:%M:%S"))
            for k in ["att_history","score_history",
                      "emo_history","time_labels"]:
                if len(S[k]) > 60: S[k] = S[k][-60:]
        print(f"[{e['time']}][{t.upper()}] {msg[:65]}")

# ══════════════════════════════════════════════════════════════════════
# GEMINI BRAIN
# ══════════════════════════════════════════════════════════════════════
class GeminiBrain:
    MODELS = [
        "gemini-2.0-flash","gemini-2.0-flash-lite",
        "gemini-1.5-flash-latest","gemini-1.5-flash",
        "gemini-1.5-pro","gemini-pro",
    ]
    def __init__(self):
        self.ok = False
        self.model_name = "fallback"
        self.therapy_chat = None
        self.parent_chat  = None
        self._lock = threading.Lock()

        for mn in self.MODELS:
            try:
                m = genai.GenerativeModel(
                    mn,
                    system_instruction=THERAPY_PROMPT,
                    generation_config=genai.GenerationConfig(
                        temperature=0.8,
                        max_output_tokens=120,
                    ))
                c = m.start_chat(history=[])
                r = c.send_message("Say READY in 3 words max")
                self.therapy_model = m
                self.therapy_chat  = c
                self.model_name    = mn
                self.ok = True
                S["gemini_ok"] = True
                print(f"✅ Gemini: {mn} → {r.text.strip()[:30]}")
                break
            except Exception as e:
                print(f"⚠️  {mn}: {str(e)[:55]}")

        # Parent chatbot
        if self.ok:
            try:
                pm = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=(
                        "You are an autism specialist helping parents. "
                        "Answer ONLY autism-related questions. "
                        "Be warm, evidence-based. "
                        f"Child: {S['name']}, age {S['age']}. "
                        "Support Arabic and English."
                    ),
                    generation_config=genai.GenerationConfig(
                        temperature=0.6, max_output_tokens=250))
                self.parent_chat = pm.start_chat(history=[])
            except: pass

    def ctx(self):
        return (
            f"[child={S['name']} age={S['age']} "
            f"emotion={S['emotion']} "
            f"attention={S['attention']}% "
            f"protocol={S['protocol']} "
            f"score={S['score']} "
            f"difficulty={S['difficulty']} "
            f"hand_raised={S['hand_raised']}] "
        )

    def ask(self, prompt):
        if not self.ok: return self._fb()
        with self._lock:
            try:
                r = self.therapy_chat.send_message(
                    self.ctx() + prompt)
                return r.text.strip()
            except Exception as e:
                print(f"⚠️  Gemini: {e}")
                try:
                    self.therapy_chat = \
                        self.therapy_model.start_chat(history=[])
                except: pass
                return self._fb()

    def parent_ask(self, q):
        if not self.parent_chat: return (
            "I'm here to help with autism questions.")
        try:
            r = self.parent_chat.send_message(q)
            return r.text.strip()
        except: return "Please consult your child's specialist."

    def _fb(self):
        n = S["name"]
        return random.choice([
            f"Clap hands {n}! [CLAP]",
            f"Touch nose {n}! 👃",
            f"Wave hello {n}! [WAVE]",
            f"Show happy face {n}! 😊",
        ])

# ══════════════════════════════════════════════════════════════════════
# EMOTION ENGINE (9 emotions + action verification)
# ══════════════════════════════════════════════════════════════════════
class EmotionEngine:
    """
    9 emotions: happy, sad, angry, fear, surprise,
                disgust, neutral, joy, confused
    + action verification (hand raise, wave, clap)
    """
    COLORS = {
        "happy":    (0,220,80),   "sad":     (100,100,220),
        "angry":    (0,0,220),    "fear":    (0,180,220),
        "surprise": (200,50,220), "disgust": (0,180,100),
        "neutral":  (180,180,180),"joy":     (0,255,180),
        "confused": (200,150,0),
    }

    def __init__(self):
        self.ok_deepface = False
        self.ok_cascade  = False
        self._lock   = threading.Lock()
        self._win    = None
        self._busy   = False
        self.prev_frame = None
        self.hand_pts_history = []

        # DeepFace
        try:
            from deepface import DeepFace
            self.DF = DeepFace
            dummy = np.zeros((48,48,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.ok_deepface = True
            print("✅ DeepFace (9-emotion) ready")
        except Exception as e:
            print(f"⚠️  DeepFace: {e}")

        # OpenCV cascades
        try:
            cp = cv2.data.haarcascades
            self.face_c  = cv2.CascadeClassifier(
                cp+'haarcascade_frontalface_default.xml')
            self.smile_c = cv2.CascadeClassifier(
                cp+'haarcascade_smile.xml')
            self.eye_c   = cv2.CascadeClassifier(
                cp+'haarcascade_eye.xml')
            self.body_c  = cv2.CascadeClassifier(
                cp+'haarcascade_upperbody.xml')
            if not self.face_c.empty():
                self.ok_cascade = True
                print("✅ OpenCV cascades ready")
        except Exception as e:
            print(f"⚠️  Cascades: {e}")

        # MediaPipe hands
        self.ok_mp = False
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.hands    = self.mp_hands.Hands(
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5)
            self.ok_mp = True
            print("✅ MediaPipe hands ready")
        except Exception as e:
            print(f"⚠️  MediaPipe: {e}")

    def analyze_async(self, frame):
        if self._busy: return
        self._busy = True
        threading.Thread(
            target=self._analyze,
            args=(frame.copy(),),
            daemon=True).start()

    def _analyze(self, frame):
        try:
            small = cv2.resize(frame, (300, 300))
            scores = self._get_scores(small)
            self._detect_actions(frame)
            self._update_state(scores)
            self._draw_window(small, scores)
        except: pass
        finally: self._busy = False

    def _get_scores(self, frame):
        # Layer 1: DeepFace
        if self.ok_deepface:
            try:
                r = self.DF.analyze(
                    frame, actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True)
                if r:
                    raw   = r[0].get('emotion', {})
                    total = sum(raw.values()) or 1
                    scores = {k:v/total for k,v in raw.items()}
                    # Map to 9 emotions
                    scores["joy"] = scores.get("happy",0) * 0.4
                    scores["confused"] = (
                        scores.get("disgust",0)*0.3 +
                        scores.get("neutral",0)*0.1)
                    S["face_detected"] = True
                    return scores
            except: pass

        # Layer 2: OpenCV
        if not self.ok_cascade:
            return {"neutral":1.0}

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)
        faces = self.face_c.detectMultiScale(
            gray, 1.05, 3, minSize=(20,20))

        if len(faces) == 0:
            S["face_detected"] = False
            S["attention"] = max(0, S["attention"]-3)
            return {"neutral":0.8,"confused":0.2}

        S["face_detected"] = True
        S["attention"] = min(100, S["attention"]+3)

        x,y,w,h = sorted(faces,
            key=lambda f:f[2]*f[3],reverse=True)[0]
        roi  = gray[y:y+h, x:x+w]
        bright = float(np.mean(roi))

        smiles = self.smile_c.detectMultiScale(
            roi, 1.5, 8, minSize=(15,15))
        eyes   = self.eye_c.detectMultiScale(
            roi, 1.1, 5, minSize=(10,10))
        ns, ne = len(smiles), len(eyes)

        if ns > 1:
            return {"happy":0.6,"joy":0.25,
                    "neutral":0.10,"surprise":0.05}
        elif ns == 1:
            return {"happy":0.45,"joy":0.15,
                    "neutral":0.25,"surprise":0.15}
        elif ne >= 2:
            if bright > 130:
                return {"neutral":0.5,"happy":0.2,
                        "surprise":0.15,"confused":0.15}
            else:
                return {"sad":0.4,"fear":0.2,
                        "neutral":0.25,"confused":0.15}
        elif ne == 1:
            return {"neutral":0.4,"sad":0.25,
                    "confused":0.2,"fear":0.15}
        else:
            return {"angry":0.35,"disgust":0.25,
                    "sad":0.2,"confused":0.2}

    def _detect_actions(self, frame):
        """Detect: hand raise, wave, clap via MediaPipe"""
        if not self.ok_mp: return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)
            h, w = frame.shape[:2]

            if not res.multi_hand_landmarks:
                S["hand_raised"] = False
                S["waving"]      = False
                return

            for lm in res.multi_hand_landmarks:
                # Wrist y vs middle finger tip y
                wrist  = lm.landmark[0]
                middle = lm.landmark[12]
                index  = lm.landmark[8]

                # Hand raised: wrist below middle (in image coords)
                if wrist.y > middle.y + 0.15:
                    S["hand_raised"] = True
                else:
                    S["hand_raised"] = False

                # Wave: horizontal movement of wrist
                wx = wrist.x
                self.hand_pts_history.append(wx)
                if len(self.hand_pts_history) > 15:
                    self.hand_pts_history.pop(0)
                if len(self.hand_pts_history) >= 10:
                    spread = (max(self.hand_pts_history) -
                              min(self.hand_pts_history))
                    S["waving"] = spread > 0.15

            # Clap detection: 2 hands close together
            if (res.multi_hand_landmarks and
                    len(res.multi_hand_landmarks) >= 2):
                h1 = res.multi_hand_landmarks[0].landmark[0]
                h2 = res.multi_hand_landmarks[1].landmark[0]
                dist = abs(h1.x - h2.x)
                if dist < 0.15:
                    S["clapping"] = True
                    S["clap_detected"] = True
                else:
                    S["clapping"] = False

            # Verify requested action
            va = S.get("verify_action")
            if va:
                if "hand" in va.lower() and S["hand_raised"]:
                    S["verify_result"] = True
                    S["verify_action"] = None
                    log("✅ Action verified: hand raised","success")
                elif "wave" in va.lower() and S["waving"]:
                    S["verify_result"] = True
                    S["verify_action"] = None
                    log("✅ Action verified: wave","success")
                elif "clap" in va.lower() and S["clapping"]:
                    S["verify_result"] = True
                    S["verify_action"] = None
                    log("✅ Action verified: clap","success")

        except: pass

    def _update_state(self, scores):
        if not scores: return
        dom  = max(scores, key=scores.get)
        S["emotion"]        = dom
        S["emotion_scores"] = scores
        S["emotion_9"].update(scores)

        pos = (scores.get("happy",0)+scores.get("joy",0)+
               scores.get("surprise",0))
        neg = (scores.get("sad",0)+scores.get("angry",0)+
               scores.get("fear",0))
        if pos > 0.5:   S["engagement"] = "high"
        elif neg > 0.5: S["engagement"] = "distressed"
        else:           S["engagement"] = "moderate"

    def _draw_window(self, frame, scores):
        disp = frame.copy()
        em   = S["emotion"]
        col  = self.COLORS.get(em, (180,180,180))

        # Score bars
        sorted_scores = sorted(
            scores.items(), key=lambda x:-x[1])[:9]
        for i,(e,s) in enumerate(sorted_scores):
            y   = 5 + i*27
            bl  = int(s*130)
            c   = self.COLORS.get(e,(150,150,150))
            cv2.rectangle(disp,(3,y),(3+bl,y+20),c,-1)
            cv2.rectangle(disp,(3,y),(133,y+20),(40,40,40),1)
            cv2.putText(disp,f"{e[:7]}:{s:.0%}",
                (5,y+14),cv2.FONT_HERSHEY_SIMPLEX,
                0.33,(255,255,255),1)

        # Action indicators
        acts = []
        if S["hand_raised"]: acts.append("HAND↑")
        if S["waving"]:      acts.append("WAVE~")
        if S["clapping"]:    acts.append("CLAP!")
        if acts:
            cv2.putText(disp," ".join(acts),
                (3,285),cv2.FONT_HERSHEY_SIMPLEX,
                0.45,(0,255,100),2)

        # Attention bar
        bw = int(S["attention"]/100*298)
        cv2.rectangle(disp,(0,292),(298,299),(20,20,40),-1)
        cv2.rectangle(disp,(0,292),(bw,299),col,-1)

        # Header
        cv2.rectangle(disp,(0,0),(300,18),(0,0,0),-1)
        cv2.putText(disp,
            f"9-EMO | {em.upper()} | Att:{S['attention']}%",
            (3,13),cv2.FONT_HERSHEY_SIMPLEX,
            0.33,(0,200,255),1)

        with self._lock:
            self._win = disp.copy()

    def get_window(self):
        with self._lock:
            return self._win.copy() if self._win is not None \
                   else None


# ══════════════════════════════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════════════════════════════
class Camera:
    def __init__(self):
        self.cap = None; self.idx = -1
        self._lk = threading.Lock(); self._frm = None
        for i in [1,0,2,3]:
            try:
                c = cv2.VideoCapture(i)
                if c.isOpened():
                    ret,f = c.read()
                    if ret and f is not None and f.size>0:
                        c.set(cv2.CAP_PROP_FRAME_WIDTH,640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
                        c.set(cv2.CAP_PROP_FPS,30)
                        self.cap=c; self.idx=i
                        print(f"✅ Camera index {i}")
                        return
                    c.release()
            except: pass
        print("⚠️  No camera")

    def read(self):
        if not self.cap: return False,None
        ret,f = self.cap.read()
        if ret and f is not None:
            f = cv2.flip(f,1)
            with self._lk: self._frm=f.copy()
            return True,f
        return False,None


# ══════════════════════════════════════════════════════════════════════
# VOICE ENGINE (interruptible)
# ══════════════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok=False; self._lk=threading.Lock()
        try:
            self.e=pyttsx3.init()
            self.e.setProperty('rate',128)
            self.e.setProperty('volume',1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice',v.id); break
            self.ok=True
            print("✅ Voice (interruptible, rate=128)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")

    def say(self, text):
        S["interrupt"] = False
        name = S.get("name","Friend")
        text = str(text).replace("{name}",name)
        # Clean tokens
        for t in ["[WAVE]","[CLAP]","[NOD]","[DANCE]",
                  "[POINT]","[HUG]","[CELEBRATE]","[THINK]",
                  "[GAME]"]:
            text = text.replace(t,"")
        text = re.sub(r'\[YOUTUBE:[^\]]+\]','',text)
        text = re.sub(r'\[REWARD:\d+\]','',text)
        text = re.sub(r'\[VERIFY:[^\]]+\]','',text)
        text = text.strip()
        if not text: return

        S["is_speaking"] = True
        # Add to session chat
        S["session_chat"].append({
            "role":"pepper","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(S["session_chat"])>30:
            S["session_chat"]=S["session_chat"][-30:]
        print(f"\n🔊 Pepper: {text}")
        log(f"Said: {text[:60]}")

        if self.ok:
            with self._lk:
                try:
                    self.e.say(text)
                    self.e.runAndWait()
                except: pass
        S["is_speaking"] = False

    def stop(self):
        """Interrupt current speech"""
        S["interrupt"] = True
        if self.ok:
            try: self.e.stop()
            except: pass
        S["is_speaking"] = False


# ══════════════════════════════════════════════════════════════════════
# MICROPHONE (energy=10, whisper detection)
# ══════════════════════════════════════════════════════════════════════
class Mic:
    def __init__(self):
        self.ok=False; self.running=False
        try:
            self.r = sr.Recognizer()
            # ═══ MAXIMUM SENSITIVITY ═══
            self.r.energy_threshold               = 10
            self.r.dynamic_energy_threshold       = False
            self.r.pause_threshold                = 0.4
            self.r.phrase_threshold               = 0.1
            self.r.non_speaking_duration          = 0.1
            self.ok=True
            print("✅ Mic (energy=10, whisper detection)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen(self, timeout=5):
        if not self.ok:
            return input("👶 Type: ").strip()
        try:
            with sr.Microphone() as src:
                # Minimal ambient adjustment
                self.r.adjust_for_ambient_noise(
                    src, duration=0.1)
                audio = self.r.listen(
                    src,timeout=timeout,
                    phrase_time_limit=15)
            try:
                text = self.r.recognize_google(audio)
                S["last_sound"] = time.time()
                S["session_chat"].append({
                    "role":"child","text":text,
                    "time":datetime.now().strftime("%H:%M:%S")})
                if len(S["session_chat"])>30:
                    S["session_chat"]=S["session_chat"][-30:]
                log(f"Heard: {text}")
                return text
            except sr.UnknownValueError:
                self._clap(audio)
                S["last_sound"] = time.time()
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError:
            return ""
        except Exception:
            return ""

    def _clap(self, audio):
        try:
            raw = np.frombuffer(
                audio.get_raw_data(),np.int16)
            rms = float(np.sqrt(np.mean(
                raw.astype(np.float64)**2)))
            if rms > 800:
                S["clap_detected"] = True
                log("👏 Clap!","success")
        except: pass

    def get_name(self, voice):
        if S["known"]: return S["name"]
        voice.say(
            "Hello! I am Pepper! What is your name?")
        for _ in range(3):
            r = self.listen(8)
            if r and r not in ["[sound]",""]:
                n = self._extract(r)
                if n:
                    S["name"]=n; S["known"]=True
                    log(f"Name: {n}","success")
                    return n
        S["name"]="Friend"; S["known"]=True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm",
                   "call me","name is"]:
            t = t.replace(rm,"").strip()
        w = t.split()
        return w[0].capitalize() if w else None

    def listen_bg(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if S["is_speaking"]:
                    time.sleep(0.15)
                    continue
                text = self.listen(4)
                if text:
                    # If Pepper speaking, interrupt first
                    if S["is_speaking"]:
                        S["interrupt"] = True
                    try: callback(text)
                    except Exception as e:
                        print(f"⚠️  cb:{e}")
                time.sleep(0.05)
        threading.Thread(target=_loop,daemon=True).start()


# ══════════════════════════════════════════════════════════════════════
# ACTION ENGINE (tokens → PyBullet)
# ══════════════════════════════════════════════════════════════════════
class Actions:
    def __init__(self, pepper=None):
        self.pepper = pepper

    def process(self, text):
        clean = text
        for tok,fn in [
            ("[WAVE]",      self._wave),
            ("[CLAP]",      self._clap),
            ("[NOD]",       self._nod),
            ("[DANCE]",     self._dance),
            ("[POINT]",     self._point),
            ("[HUG]",       self._hug),
            ("[CELEBRATE]", self._celebrate),
            ("[THINK]",     self._think),
        ]:
            if tok in text:
                clean = clean.replace(tok,"")
                threading.Thread(
                    target=fn,daemon=True).start()

        # YouTube
        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]',text)
        if yt:
            clean = clean.replace(yt.group(0),"")
            q = yt.group(1).strip()
            url = ("https://www.youtube.com/results?"
                   "search_query="+urllib.parse.quote(
                       q+" autism children educational"))
            webbrowser.open(url)
            log(f"📺 YouTube: {q}")

        # Image
        img = re.search(r'\[IMAGE:\s*(.+?)\]',text)
        if img:
            clean = clean.replace(img.group(0),"")
            webbrowser.open(
                "https://www.google.com/search?tbm=isch&q="
                +urllib.parse.quote(img.group(1)))

        # Reward
        rew = re.search(r'\[REWARD:(\d+)\]',text)
        if rew:
            clean = clean.replace(rew.group(0),"")
            stars = int(rew.group(1))
            S["tokens"]     += stars
            S["stars_today"] += stars

        # Verify
        vry = re.search(r'\[VERIFY:\s*(.+?)\]',text)
        if vry:
            clean = clean.replace(vry.group(0),"")
            S["verify_action"] = vry.group(1).strip()
            S["verify_result"] = False
            log(f"👁️  Verifying: {vry.group(1)}")

        # Game
        if "[GAME]" in text:
            clean = clean.replace("[GAME]","")
            webbrowser.open(f"http://localhost:{PORT_GAME}")

        return clean.strip()

    def _sa(self,j,a,s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2)
        self._sa("RElbowRoll",0.8,0.2); time.sleep(0.3)
        for _ in range(3):
            self._sa("RWristYaw",0.5,0.25); time.sleep(0.2)
            self._sa("RWristYaw",-0.5,0.25); time.sleep(0.2)
        self._sa("RShoulderPitch",1.0,0.15)

    def _clap(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.8,0.25)
            self._sa("RShoulderPitch",0.8,0.25); time.sleep(0.18)
            self._sa("LShoulderPitch",1.1,0.25)
            self._sa("RShoulderPitch",1.1,0.25); time.sleep(0.18)

    def _nod(self):
        for _ in range(2):
            self._sa("HeadPitch",0.3,0.2); time.sleep(0.3)
            self._sa("HeadPitch",-0.1,0.2); time.sleep(0.3)
        self._sa("HeadPitch",0.0,0.15)

    def _dance(self):
        for _ in range(5):
            self._sa("LShoulderPitch",0.15,0.2)
            self._sa("RShoulderPitch",0.9,0.2)
            self._sa("HeadYaw",0.4,0.2); time.sleep(0.22)
            self._sa("LShoulderPitch",0.9,0.2)
            self._sa("RShoulderPitch",0.15,0.2)
            self._sa("HeadYaw",-0.4,0.2); time.sleep(0.22)
        self._sa("HeadYaw",0,0.1)

    def _point(self):
        self._sa("LShoulderPitch",0.1,0.15)
        self._sa("LElbowYaw",-1.5,0.15); time.sleep(1.0)
        self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        self._sa("LShoulderPitch",0.5,0.1)
        self._sa("RShoulderPitch",0.5,0.1)
        self._sa("LShoulderRoll",0.35,0.1)
        self._sa("RShoulderRoll",-0.35,0.1); time.sleep(1.5)
        self._sa("LShoulderPitch",1.0,0.1)
        self._sa("RShoulderPitch",1.0,0.1)
        self._sa("LShoulderRoll",0.0,0.1)
        self._sa("RShoulderRoll",0.0,0.1)

    def _celebrate(self):
        for _ in range(3):
            self._sa("LShoulderPitch",0.05,0.25)
            self._sa("RShoulderPitch",0.05,0.25)
            self._sa("HeadPitch",-0.2,0.2); time.sleep(0.25)
            self._sa("LShoulderPitch",1.0,0.25)
            self._sa("RShoulderPitch",1.0,0.25)
            self._sa("HeadPitch",0.0,0.2); time.sleep(0.25)

    def _think(self):
        self._sa("HeadYaw",0.35,0.1)
        self._sa("HeadPitch",-0.15,0.1); time.sleep(1.8)
        self._sa("HeadYaw",0.0,0.1)
        self._sa("HeadPitch",0.0,0.1)


# ══════════════════════════════════════════════════════════════════════
# PYBULLET SIMULATION
# ══════════════════════════════════════════════════════════════════════
class Sim:
    def __init__(self):
        self.pepper=None; self.ok=False
        self.rx=self.ry=0.0
        self.auto_walk=True; self.balloons=[]

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim  = QS()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(
                pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._room(); 
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._balloons(); self._kids()
            p.resetDebugVisualizerCamera(
                7,45,-35,[0,0,0.5])
            self.ok = True
            for fn in [self._sim_loop,
                       self._walk_loop,
                       self._arm_loop]:
                threading.Thread(
                    target=fn,daemon=True).start()
            print("✅ PyBullet therapy room ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _room(self):
        wc=[0.88,0.88,0.92,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(
                    p.GEOM_BOX,halfExtents=ext,
                    rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        for txt,pos in [
            ("ABA",[-4,3,2]),("DTT",[4,3,2]),
            ("TEACCH",[0,4,2]),("TIE",[-4,-3,2]),
            ("HUB:5001",[0,0,2.8])]:
            p.addUserDebugText(txt,pos,
                [.4,.5,.9],textSize=1.1,lifeTime=0)

    def _balloons(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
              [1,1,.2,1],[1,.5,.2,1],[.8,.2,.8,1],
              [.2,.8,.8,1],[.8,.2,.8,1]]
        for i in range(8):
            vs=p.createVisualShape(p.GEOM_SPHERE,
               radius=.15,rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,
               [random.uniform(-3,3),
                random.uniform(-2,2),
                random.uniform(.8,2.2)])
            self.balloons.append({
                "id":bid,
                "x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

    def _kids(self):
        for nm,pos,col in [
            ("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1]),
            ("Sara", [-1.2,1.3,0],[1.,.6,.0,1]),
            ("Yusuf",[.5,-2.,0], [.9,.15,.15,1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=[.13,.09,.21],
                    rgbaColor=col),
                [pos[0],pos[1],.41])
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_SPHERE,
                    radius=.11,
                    rgbaColor=[1.,.82,.65,1.]),
                [pos[0],pos[1],.74])
            p.addUserDebugText(nm,
                [pos[0],pos[1],1.05],
                [0,0,0],textSize=.85,lifeTime=0)

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
                        b["id"],
                        [b["x"],b["y"],b["z"]],
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
                if S["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph)
                    R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles(
                        "LShoulderPitch",L,.07)
                    self.pepper.setAngles(
                        "RShoulderPitch",R,.07)
                    self.pepper.setAngles(
                        "HeadPitch",-0.05,.04)
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
                [pos[0],pos[1],pos[2]+1.35],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass


# ══════════════════════════════════════════════════════════════════════
# MINI DISPLAY (320x240 windows)
# ══════════════════════════════════════════════════════════════════════
class MiniDisplay:
    def __init__(self, em_eng, cam):
        self.em=em_eng; self.cam=cam
        self.running=False
        self.task_text=""; self.task_t=0
        self.praise_text=""; self.praise_t=0
        self.ai_text=""; self.ai_t=0
        self._last_em=0
        self.avatar=self._avatar()
        self.running=True
        threading.Thread(
            target=self._run,daemon=True).start()
        print("✅ Mini display (320x240) started!")

    def _avatar(self):
        img=np.zeros((120,90,3),dtype=np.uint8)
        img[:] = (10,15,38)
        cv2.circle(img,(45,30),22,(220,195,173),-1)
        for ex in [37,53]:
            cv2.circle(img,(ex,26),5,(0,140,255),-1)
            cv2.circle(img,(ex,26),2,(255,255,255),-1)
        cv2.ellipse(img,(45,37),(7,4),0,0,180,(70,35,35),1)
        cv2.rectangle(img,(28,52),(62,90),(120,135,190),-1)
        cv2.rectangle(img,(8,53),(28,70),(120,135,190),-1)
        cv2.rectangle(img,(62,53),(82,70),(120,135,190),-1)
        cv2.putText(img,"PEPPER",(8,108),
            cv2.FONT_HERSHEY_SIMPLEX,0.38,(80,180,255),1)
        return img

    def _run(self):
        no_cam = self.cam.idx < 0
        while self.running:
            try:
                if no_cam:
                    frame = self._sim_frame()
                else:
                    ret,f = self.cam.read()
                    frame = f if ret else self._sim_frame()

                now = time.time()
                if now-self._last_em > 0.8 and not no_cam:
                    self._last_em = now
                    self.em.analyze_async(frame.copy())

                # Build mini UI (320x240)
                ui = self._build(frame)
                mini = cv2.resize(ui,(960,540))
                cv2.imshow("Pepper Therapy",mini)

                # Emotion window (320x320 → shown small)
                ew = self.em.get_window()
                if ew is not None:
                    ew_small = cv2.resize(ew,(320,320))
                    cv2.imshow("Emotion (9)",ew_small)

                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'),ord('Q'),27]:
                    self.running=False; break

            except Exception as e:
                print(f"⚠️  display:{e}")
                time.sleep(0.1)
            time.sleep(0.018)
        try: cv2.destroyAllWindows()
        except: pass

    def _sim_frame(self):
        h,w=480,640
        f=np.zeros((h,w,3),dtype=np.uint8)
        f[:] = (7,10,25)
        t=time.time()
        for i in range(0,w,60):
            cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,60):
            cv2.line(f,(0,i),(w,i),(15,22,50),1)
        r=int(30+12*math.sin(t*1.5))
        col=(int(50+50*math.sin(t)),
             int(100+100*math.cos(t*0.7)),220)
        cv2.circle(f,(w//2,h//2-40),r,col,3)
        cv2.putText(f,"SIMULATION",
            (w//2-80,h//2+20),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,
            (100,150,255),2)
        return f

    def _build(self, frame):
        h,w = frame.shape[:2]
        ui  = frame.copy()

        # Header
        ov=ui.copy()
        cv2.rectangle(ov,(0,0),(w,55),(6,10,25),-1)
        ui=cv2.addWeighted(ov,0.85,ui,0.15,0)

        gem = "✅" if S["gemini_ok"] else "⚠️"
        cv2.putText(ui,
            f"Therapy Hub {gem}  Port:{PORT_MASTER}",
            (10,22),cv2.FONT_HERSHEY_SIMPLEX,
            0.6,(255,255,255),2)
        cv2.putText(ui,
            f"{S['name']} | {S['protocol']} | "
            f"Score:{S['score']} | ⭐{S['tokens']}",
            (10,45),cv2.FONT_HERSHEY_SIMPLEX,
            0.4,(140,190,255),1)

        # Avatar PIP (mini)
        av=self.avatar.copy()
        ah,aw=av.shape[:2]
        if S["is_speaking"]:
            t=int(time.time()*6)%3
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                (0,160+t*18,255),1+t//2)
        x1=w-aw-8; y1=h-ah-60
        ui[y1:y1+ah,x1:x1+aw] = av
        cv2.rectangle(ui,(x1-2,y1-2),
            (x1+aw+2,y1+ah+2),
            (0,200,255) if S["is_speaking"]
            else (40,40,80),1)

        # Bottom emotion bar
        ov2=ui.copy()
        cv2.rectangle(ov2,(0,h-60),(w,h),(6,10,25),-1)
        ui=cv2.addWeighted(ov2,0.78,ui,0.22,0)

        EC={
            "happy":(0,220,80),"sad":(100,100,220),
            "angry":(0,0,220),"fear":(0,180,220),
            "surprise":(200,50,220),"disgust":(0,180,100),
            "neutral":(180,180,180),"joy":(0,255,180),
            "confused":(200,150,0),
        }
        em = S["emotion"]
        ec = EC.get(em,(180,180,180))
        att= S["attention"]

        cv2.putText(ui,f"{em.upper()}",
            (10,h-38),cv2.FONT_HERSHEY_SIMPLEX,
            0.7,ec,2)
        bw2=int(att/100*(w-160))
        cv2.rectangle(ui,(10,h-25),(w-150,h-17),
            (25,28,55),-1)
        cv2.rectangle(ui,(10,h-25),(10+bw2,h-17),ec,-1)
        cv2.putText(ui,
            f"Att:{att}%  {S['engagement']}",
            (10,h-6),cv2.FONT_HERSHEY_SIMPLEX,
            0.38,(255,230,100),1)

        # Hand/Wave/Clap indicators
        inds=[]
        if S["hand_raised"]: inds.append("HAND↑")
        if S["waving"]:      inds.append("WAVE~")
        if S["clapping"]:    inds.append("CLAP!")
        if inds:
            cv2.putText(ui," ".join(inds),
                (w-200,h-38),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,(0,255,100),2)

        # Prompt level
        pl = S.get("prompt_level",0)
        plc= [(0,200,0),(200,200,0),
              (200,100,0),(200,0,0)][min(pl,3)]
        cv2.circle(ui,(w-30,h-40),15,plc,-1)
        cv2.putText(ui,f"P{pl}",
            (w-37,h-34),cv2.FONT_HERSHEY_SIMPLEX,
            0.5,(255,255,255),2)

        # Task display
        now=time.time()
        if self.task_text and now-self.task_t<8:
            tl=min(len(self.task_text)*13,w-60)
            tx=max(10,w//2-tl//2)
            cv2.rectangle(ui,(tx-5,h//2-38),
                (tx+tl+5,h//2+8),(12,45,110),-1)
            cv2.rectangle(ui,(tx-5,h//2-38),
                (tx+tl+5,h//2+8),(0,140,255),2)
            cv2.putText(ui,self.task_text[:50],
                (tx,h//2-10),cv2.FONT_HERSHEY_SIMPLEX,
                0.65,(255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_t<4:
            cv2.putText(ui,self.praise_text[:35],
                (w//2-150,h//2+50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,(0,255,100),2)

        # AI text preview
        if self.ai_text and now-self.ai_t<5:
            lines=[self.ai_text[i:i+60]
                   for i in range(0,
                   min(len(self.ai_text),120),60)]
            for li,ln in enumerate(lines[:2]):
                cv2.putText(ui,ln,
                    (10,h-70-li*20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,(200,255,200),1)

        # Face dot
        fdc=(0,255,0) if S["face_detected"] else (0,0,255)
        cv2.circle(ui,(w-10,15),6,fdc,-1)
        cv2.circle(ui,(36,20),7,(0,0,220),-1)
        cv2.putText(ui,"REC",(48,26),
            cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,220),1)

        if S["clap_detected"]:
            cv2.putText(ui,"👏 CLAP!",
                (w//2-60,70),
                cv2.FONT_HERSHEY_SIMPLEX,1.0,
                (0,255,100),3)
        return ui

    def show_task(self,t): self.task_text=t;self.task_t=time.time()
    def show_praise(self,t): self.praise_text=t;self.praise_t=time.time()
    def show_ai(self,t): self.ai_text=t[:120];self.ai_t=time.time()
    def stop(self):
        self.running=False; time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass


# ══════════════════════════════════════════════════════════════════════
# FLASK APPS (3 servers)
# ══════════════════════════════════════════════════════════════════════

# ── GAME SERVER (5009) ───────────────────────────────────────────────
game_app = Flask("game_server")

GAME_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>🎮 Therapy Game Zone</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;
     font-family:'Segoe UI',sans-serif;
     display:flex;flex-direction:column;
     align-items:center;padding:20px;min-height:100vh}
h1{color:#a78bfa;font-size:1.4em;margin-bottom:20px}
.games{display:grid;grid-template-columns:repeat(3,1fr);
       gap:16px;width:100%;max-width:900px}
.game{background:#0c0f1e;border:2px solid #1a1f40;
      border-radius:14px;padding:20px;text-align:center;
      cursor:pointer;transition:.3s}
.game:hover{border-color:#a78bfa;transform:translateY(-3px)}
.icon{font-size:3em;margin-bottom:10px}
.gname{font-size:.95em;font-weight:700;color:#e0e6ff}
.gdesc{font-size:.75em;color:#6b7280;margin-top:5px}
.score{background:#1a0a3d;border-radius:8px;
       padding:8px 15px;margin:15px 0;
       font-size:.85em;color:#a78bfa}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:10px 20px;
     border-radius:8px;cursor:pointer;font-size:.85em;
     margin:5px;transition:.2s}
.btn:hover{opacity:.85}
canvas{border:2px solid #4f46e5;border-radius:8px;
       background:#000;margin-top:10px}
#active-game{width:100%;max-width:900px;margin-top:15px}
</style>
</head><body>
<h1>🎮 Pepper Therapy Game Zone</h1>
<div class="score" id="score-disp">
  Score: <span id="pts">0</span> ⭐ |
  Level: <span id="lvl">1</span>
</div>

<div class="games">
  <div class="game" onclick="startGame('balloons')">
    <div class="icon">🎈</div>
    <div class="gname">Pop the Balloons!</div>
    <div class="gdesc">Touch happy balloons</div>
  </div>
  <div class="game" onclick="startGame('colors')">
    <div class="icon">🎨</div>
    <div class="gname">Color Match</div>
    <div class="gdesc">Match the colors game</div>
  </div>
  <div class="game" onclick="startGame('emotions')">
    <div class="icon">😊</div>
    <div class="gname">Emotion Mirror</div>
    <div class="gdesc">Mirror Pepper's face</div>
  </div>
  <div class="game" onclick="startGame('numbers')">
    <div class="icon">🔢</div>
    <div class="gname">Count with Pepper</div>
    <div class="gdesc">Counting fun game</div>
  </div>
  <div class="game" onclick="startGame('shapes')">
    <div class="icon">⭐</div>
    <div class="gname">Shape Sorter</div>
    <div class="gdesc">Match the shapes</div>
  </div>
  <div class="game" onclick="startGame('memory')">
    <div class="icon">🧠</div>
    <div class="gname">Memory Cards</div>
    <div class="gdesc">Flip and match!</div>
  </div>
</div>

<div id="active-game"></div>
<div style="margin-top:15px">
  <button class="btn" onclick="window.location='http://localhost:5001'">
    ← Back to Dashboard
  </button>
</div>

<script>
var score=0,level=1;

function startGame(type){
  var div=document.getElementById('active-game');
  if(type==='balloons'){
    div.innerHTML='<canvas id="gc" width="800" height="400"></canvas>';
    runBalloons();
  } else if(type==='emotions'){
    div.innerHTML=emoGame();
  } else if(type==='colors'){
    div.innerHTML=colorGame();
  } else if(type==='numbers'){
    div.innerHTML=numGame();
  } else if(type==='memory'){
    div.innerHTML=memGame();
  } else {
    div.innerHTML='<p style="color:#a78bfa;padding:20px">Coming soon! Great choice! 🌟</p>';
  }
}

function addScore(n){
  score+=n; level=Math.floor(score/50)+1;
  document.getElementById('pts').textContent=score;
  document.getElementById('lvl').textContent=level;
}

function runBalloons(){
  var c=document.getElementById('gc');
  var ctx=c.getContext('2d');
  var balls=[];
  for(var i=0;i<8;i++){
    balls.push({
      x:Math.random()*750+25,
      y:Math.random()*350+25,
      r:30+Math.random()*20,
      vx:(Math.random()-0.5)*2,
      vy:(Math.random()-0.5)*2,
      color:['#f87171','#34d399','#60a5fa',
              '#fbbf24','#c084fc','#f97316'][Math.floor(Math.random()*6)],
      alive:true
    });
  }
  c.onclick=function(e){
    var rect=c.getBoundingClientRect();
    var mx=e.clientX-rect.left,my=e.clientY-rect.top;
    balls.forEach(function(b){
      if(!b.alive) return;
      var d=Math.sqrt((mx-b.x)**2+(my-b.y)**2);
      if(d<b.r){ b.alive=false; addScore(10); }
    });
    if(balls.every(function(b){return !b.alive;})){
      balls.forEach(function(b){
        b.alive=true;
        b.x=Math.random()*750+25;
        b.y=Math.random()*350+25;
      });
    }
  };
  function loop(){
    ctx.fillStyle='#0a0f1e';
    ctx.fillRect(0,0,800,400);
    balls.forEach(function(b){
      if(!b.alive) return;
      b.x+=b.vx; b.y+=b.vy;
      if(b.x<b.r||b.x>800-b.r) b.vx*=-1;
      if(b.y<b.r||b.y>400-b.r) b.vy*=-1;
      ctx.beginPath();
      ctx.arc(b.x,b.y,b.r,0,Math.PI*2);
      ctx.fillStyle=b.color;
      ctx.fill();
      ctx.fillStyle='white';
      ctx.font='20px sans-serif';
      ctx.textAlign='center';
      ctx.fillText('🎈',b.x,b.y+7);
    });
    requestAnimationFrame(loop);
  }
  loop();
}

function emoGame(){
  var emos=['😊','😢','😠','😨','😲','😄','😕'];
  var names=['Happy','Sad','Angry','Scared','Surprised','Joyful','Confused'];
  var idx=Math.floor(Math.random()*emos.length);
  return '<div style="text-align:center;padding:20px">'+
    '<p style="color:#a78bfa;font-size:.9em">Show this face!</p>'+
    '<div style="font-size:5em;margin:15px">'+emos[idx]+'</div>'+
    '<p style="color:#e0e6ff;font-size:1.1em;font-weight:700">'+names[idx]+'</p>'+
    '<button class="btn btn-g" onclick="addScore(20);this.textContent=\'✅ Amazing!\'" '+
    'style="margin-top:15px;background:linear-gradient(135deg,#059669,#10b981)">'+
    'I did it! 🎉</button>'+
    '<button class="btn" onclick="document.getElementById(\'active-game\').innerHTML=emoGame()" '+
    'style="margin-top:15px">Next ➡️</button></div>';
}

function colorGame(){
  var colors=['Red','Blue','Green','Yellow','Purple','Orange'];
  var hexes=['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7','#f97316'];
  var idx=Math.floor(Math.random()*colors.length);
  var btns=colors.map(function(c,i){
    return '<button class="btn" onclick="checkColor('+i+','+idx+')" '+
      'style="background:'+hexes[i]+';margin:5px">'+c+'</button>';
  }).join('');
  return '<div style="text-align:center;padding:20px">'+
    '<p style="color:#a78bfa">What color is this?</p>'+
    '<div style="width:120px;height:120px;background:'+hexes[idx]+
    ';border-radius:50%;margin:15px auto"></div>'+
    '<div id="color-btns">'+btns+'</div></div>';
}

function checkColor(chosen,correct){
  if(chosen===correct){
    addScore(15);
    document.getElementById('color-btns').innerHTML=
      '<p style="color:#34d399;font-size:1.2em">✅ Correct! Amazing!</p>'+
      '<button class="btn" onclick="document.getElementById(\'active-game\').innerHTML=colorGame()">Next ➡️</button>';
  } else {
    document.getElementById('color-btns').innerHTML=
      '<p style="color:#f87171">Try again! You can do it! 💪</p>'+
      '<button class="btn" onclick="document.getElementById(\'active-game\').innerHTML=colorGame()">Try Again ↩️</button>';
  }
}

function numGame(){
  var n=Math.floor(Math.random()*9)+1;
  var items='';
  for(var i=0;i<n;i++) items+='⭐ ';
  var opts=[n,n-1>0?n-1:n+2,n+1,n+2>10?n-2:n+2]
    .sort(function(){return Math.random()-0.5;})
    .filter(function(x,i,a){return a.indexOf(x)===i;})
    .slice(0,4);
  var btns=opts.map(function(x){
    return '<button class="btn" onclick="checkNum('+x+','+n+')" '+
      'style="font-size:1.2em;padding:12px 20px">'+x+'</button>';
  }).join('');
  return '<div style="text-align:center;padding:20px">'+
    '<p style="color:#a78bfa">Count the stars!</p>'+
    '<div style="font-size:1.5em;margin:15px;letter-spacing:5px">'+items+'</div>'+
    '<p style="color:#6b7280;margin-bottom:10px">How many?</p>'+
    '<div>'+btns+'</div></div>';
}

function checkNum(chosen,correct){
  if(chosen===correct){
    addScore(20);
    alert('✅ YES! You counted '+correct+'! Amazing! 🌟');
    document.getElementById('active-game').innerHTML=numGame();
  } else {
    alert('Try again! Count carefully! 💪');
  }
}

function memGame(){
  var pairs=['🐶','🐱','🐻','🦊','🐼','🐨'];
  var cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});
  var html='<div style="display:grid;grid-template-columns:repeat(4,1fr);'+
    'gap:10px;max-width:400px;margin:15px auto">';
  var flipped=[],matched=[];
  cards.forEach(function(c,i){
    html+='<div id="mc'+i+'" onclick="flipCard('+i+')" '+
      'style="height:70px;background:#1f2937;border-radius:8px;'+
      'display:flex;align-items:center;justify-content:center;'+
      'font-size:2em;cursor:pointer;border:2px solid #374151">❓</div>';
  });
  html+='</div>';
  window._memCards=cards;
  window._memFlipped=[];
  window._memMatched=[];
  return html;
}

window.flipCard=function(idx){
  var cards=window._memCards;
  var el=document.getElementById('mc'+idx);
  if(window._memFlipped.length>=2) return;
  if(window._memMatched.includes(idx)) return;
  if(window._memFlipped.includes(idx)) return;
  el.textContent=cards[idx];
  window._memFlipped.push(idx);
  if(window._memFlipped.length===2){
    var a=window._memFlipped[0],b=window._memFlipped[1];
    if(cards[a]===cards[b]){
      window._memMatched.push(a,b);
      addScore(25);
      window._memFlipped=[];
      if(window._memMatched.length===cards.length)
        setTimeout(function(){
          alert('🎉 You matched all pairs! Amazing!');
          document.getElementById('active-game').innerHTML=memGame();
        },500);
    } else {
      setTimeout(function(){
        document.getElementById('mc'+a).textContent='❓';
        document.getElementById('mc'+b).textContent='❓';
        window._memFlipped=[];
      },1000);
    }
  }
};
</script>
</body></html>"""

@game_app.route("/")
def game_home():
    return GAME_HTML

@game_app.route("/api/state")
def game_state():
    return jsonify({
        "score": S["score"],
        "name":  S["name"],
        "emotion": S["emotion"],
    })


# ── AI BRAIN SERVER (5007) ───────────────────────────────────────────
ai_app = Flask("ai_brain")

@ai_app.route("/")
def ai_status():
    return jsonify({
        "status": "AI Brain Online",
        "model":  _gemini.model_name if _gemini else "N/A",
        "gemini_ok": S["gemini_ok"],
        "emotion": S["emotion"],
        "score":  S["score"],
    })

@ai_app.route("/ask", methods=["POST"])
def ai_ask():
    data = request.json or {}
    q    = data.get("prompt","")
    if not q: return jsonify({"error":"no prompt"}),400
    resp = _gemini.ask(q) if _gemini else "Gemini offline"
    return jsonify({"response":resp,"model":S.get("model","N/A")})

@ai_app.route("/parent_ask", methods=["POST"])
def ai_parent_ask():
    data = request.json or {}
    q    = data.get("question","")
    resp = _gemini.parent_ask(q) if _gemini else "Offline"
    return jsonify({"answer":resp})

@ai_app.route("/state")
def ai_get_state():
    return jsonify({k:v for k,v in S.items()
                    if k not in ["logs","parent_notes",
                                 "session_chat","chat_history"]})

@ai_app.route("/cmd", methods=["POST"])
def ai_cmd():
    data = request.json or {}
    S["sim_cmd"] = data.get("cmd","")
    return jsonify({"status":"ok"})

# ── MASTER DASHBOARD (5001) ─────────────────────────────────────────
master_app = Flask("master_hub")

IASQ_QUESTIONS = [
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

MASTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 Unified Therapy Hub — Port 5001</title>
<meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#060912;--card:#0c0f1e;--border:#1a1f40;
  --purple:#a78bfa;--blue:#60a5fa;--green:#34d399;
  --red:#f87171;--yellow:#fbbf24;--text:#e0e6ff;
  --muted:#6b7280;
}
body{font-family:'Segoe UI',system-ui,sans-serif;
     background:var(--bg);color:var(--text);font-size:14px}

/* HEADER */
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);
     padding:12px 22px;display:flex;align-items:center;
     gap:10px;border-bottom:2px solid #4f46e5;
     position:sticky;top:0;z-index:100}
.hdr h1{font-size:1.1em;color:var(--purple)}
.badge{padding:2px 9px;border-radius:12px;
       font-size:.67em;font-weight:700}
.live{background:#ef4444;color:#fff;
      animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.port{background:#1a2555;color:var(--blue);
      border:1px solid var(--blue)}
.gem-ok{background:#052918;color:var(--green);
        border:1px solid var(--green)}
.gem-off{background:#2a1515;color:var(--red);
         border:1px solid var(--red)}

/* LAYOUT */
.main{max-width:1400px;margin:0 auto;padding:12px;
      display:flex;flex-direction:column;gap:10px}
.row{display:grid;gap:10px}
.r3{grid-template-columns:1fr 1fr 1fr}
.r2{grid-template-columns:1fr 1fr}
.r4{grid-template-columns:repeat(4,1fr)}
.r5{grid-template-columns:repeat(5,1fr)}
.card{background:var(--card);border-radius:11px;
      padding:13px;border:1px solid var(--border)}
.card h2{font-size:.8em;color:#818cf8;
         border-bottom:1px solid var(--border);
         padding-bottom:5px;margin-bottom:9px;
         display:flex;align-items:center;gap:5px}

/* STATS */
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:9px;
      padding:12px;text-align:center;cursor:default;
      transition:.2s}
.stat:hover{border-color:var(--purple);
            transform:translateY(-1px)}
.n{font-size:1.8em;font-weight:700;color:var(--purple)}
.l{font-size:.68em;color:var(--muted);margin-top:2px}
.n-g{color:var(--green)}.n-b{color:var(--blue)}
.n-y{color:var(--yellow)}.n-r{color:var(--red)}

/* EMOTION */
.emo{display:inline-block;padding:5px 14px;
     border-radius:15px;font-weight:700}
.happy{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprise{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.joy{background:#05291555;color:#34d399;border:1px solid #34d399}
.confused{background:#2a1a0055;color:#fb923c;border:1px solid #fb923c}
.disgust{background:#0a291555;color:#6ee7b7;border:1px solid #6ee7b7}

/* BARS */
.bar-bg{background:#1f2937;border-radius:6px;
        height:9px;margin:4px 0}
.bar{height:9px;border-radius:6px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}

/* BUTTONS */
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:6px 12px;
     border-radius:7px;cursor:pointer;font-size:.75em;
     margin:3px;transition:.2s;font-family:inherit}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}

/* PROTOCOL */
.prot{display:inline-block;padding:2px 7px;
      border-radius:7px;font-size:.67em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}

/* INPUTS */
input,textarea,select{
  width:100%;padding:6px 9px;border-radius:6px;
  border:1px solid var(--border);background:#07090f;
  color:var(--text);font-size:.78em;font-family:inherit;
  outline:none}
input:focus,textarea:focus,select:focus{
  border-color:var(--purple)}
textarea{resize:vertical;min-height:60px}

/* LOGS */
.log-box{max-height:220px;overflow-y:auto;
         scrollbar-width:thin;
         scrollbar-color:#4f46e5 #0c0f1e}
.log-item{padding:4px 7px;margin:2px 0;
          border-radius:5px;font-size:.72em;
          border-left:3px solid #4f46e5;
          background:#07090f;line-height:1.4}
.log-item.success{border-color:var(--green)}
.log-item.fail{border-color:var(--red)}
.log-item.info{border-color:var(--blue)}

/* CHARTS */
.chart-wrap{position:relative;height:160px;
            background:#07090f;border-radius:8px;
            padding:6px}

/* CHAT */
.chat-box{height:180px;overflow-y:auto;
          background:#07090f;border-radius:8px;
          padding:9px;margin-bottom:7px;
          scrollbar-width:thin}
.cm{padding:6px 10px;margin:3px 0;
    border-radius:8px;font-size:.78em;line-height:1.5}
.cm-p{background:#1e1b4b;border-left:3px solid var(--purple)}
.cm-c{background:#052918;border-left:3px solid var(--green)}
.cm-par{background:#1a1f40;border-left:3px solid var(--blue)}

/* NOTES */
.note{background:#0a1020;border-left:3px solid var(--purple);
      padding:7px 9px;margin:3px 0;
      border-radius:0 6px 6px 0;font-size:.73em;line-height:1.5}

/* HELP */
.help-card{background:#0a1020;border-radius:8px;
           padding:10px;border-left:4px solid var(--purple)}
.hc-title{color:var(--purple);font-weight:700;
          font-size:.78em;margin-bottom:4px}
.hc-body{color:#9ca3af;font-size:.73em;line-height:1.6}
.tip{background:#051a0f;border:1px solid var(--green);
     border-radius:5px;padding:6px;margin-top:5px;
     font-size:.71em;color:#6ee7b7}

/* TABS */
.tabs{display:flex;gap:5px;flex-wrap:wrap;
      margin-bottom:10px}
.tab{padding:6px 13px;border-radius:7px;cursor:pointer;
     font-size:.76em;background:#1f2937;color:#9ca3af;
     border:1px solid var(--border);transition:.2s}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tab-content{display:none}
.tab-content.active{display:block}

/* SCROLL */
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:#0c0f1e}
::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:4px}

/* IFRAME */
iframe{width:100%;border:2px solid var(--border);
       border-radius:10px;background:#000}

/* ACTIONS */
.action-badge{display:inline-block;padding:3px 8px;
  border-radius:10px;font-size:.7em;font-weight:700;
  margin:2px}
.action-on{background:#052918;color:var(--green);
           border:1px solid var(--green)}
.action-off{background:#1f2937;color:#374151;
            border:1px solid #374151}

@media(max-width:900px){
  .r3,.r4,.r5{grid-template-columns:1fr 1fr}
  .r2{grid-template-columns:1fr}
}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div style="font-size:1.7em">🤖</div>
  <div>
    <h1>Unified Therapy Hub — Single Source of Truth</h1>
    <p style="font-size:.74em;opacity:.8">
      Commander: <b>Lamya</b> |
      Child: <b>{{s.name}}</b> |
      Age: {{s.age}} |
      <span class="prot {{s.protocol}}">{{s.protocol}}</span> |
      {{s.difficulty.upper()}} |
      Started: {{s.session_start}}
    </p>
  </div>
  <span class="badge live">● LIVE</span>
  <span class="badge port">:5001</span>
  <span class="badge {% if s.gemini_ok %}gem-ok{% else %}gem-off{% endif %}">
    {% if s.gemini_ok %}⚡ Gemini AI{% else %}⚠️ Offline{% endif %}
  </span>
  <span class="badge port" style="background:#052918;color:#34d399">
    AI:5007
  </span>
  <span class="badge port" style="background:#1a0a3d;color:#c084fc">
    Games:5009
  </span>
</div>

<div class="main">

  <!-- STATS -->
  <div class="row r5">
    <div class="stat">
      <div class="n n-g">{{s.score}}</div>
      <div class="l">🏆 Score</div>
    </div>
    <div class="stat">
      <div class="n n-y">⭐{{s.tokens}}</div>
      <div class="l">🎯 Tokens</div>
    </div>
    <div class="stat">
      <div class="n n-b">{{s.attention}}%</div>
      <div class="l">👀 Attention</div>
    </div>
    <div class="stat">
      <div class="n">P{{s.get('prompt_level',0)}}</div>
      <div class="l">💡 Prompt Lvl</div>
    </div>
    <div class="stat">
      <div class="n n-g">{{s.streak}}</div>
      <div class="l">🔥 Streak</div>
    </div>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <div class="tab active" onclick="showTab('overview')">📊 Overview</div>
    <div class="tab" onclick="showTab('charts')">📈 Charts</div>
    <div class="tab" onclick="showTab('games')">🎮 Games</div>
    <div class="tab" onclick="showTab('assessment')">📋 Assessment</div>
    <div class="tab" onclick="showTab('chatbot')">💬 AI Chatbot</div>
    <div class="tab" onclick="showTab('notes')">📝 Notes</div>
    <div class="tab" onclick="showTab('help')">💡 Help</div>
    <div class="tab" onclick="showTab('settings')">⚙️ Settings</div>
  </div>

  <!-- OVERVIEW TAB -->
  <div id="tab-overview" class="tab-content active">
    <div class="row r3">

      <!-- EMOTION + ACTIONS -->
      <div class="card">
        <h2>😊 Live Emotion + Actions (9 types)</h2>
        <div style="text-align:center;padding:6px">
          <div class="emo {{s.emotion}}">
            {{s.emotion.upper()}}
          </div>
          <div style="margin:8px 0">
            <div class="bar-bg">
              <div class="bar"
                   style="width:{{s.attention}}%"></div>
            </div>
            <span style="font-size:.72em;color:var(--purple)">
              {{s.attention}}% attention</span>
          </div>
          <div style="font-size:.75em;margin:5px 0">
            Engagement:
            <b style="color:var(--text)">{{s.engagement}}</b>
          </div>
          <div style="font-size:.7em;margin:4px 0;color:
            {{'#34d399' if s.face_detected else '#f87171'}}">
            {{'✅ Face Detected' if s.face_detected
              else '❌ No Face!'}}
          </div>

          <!-- 9 emotion bars -->
          <div style="margin-top:8px;text-align:left">
            {% for em,sc in s.emotion_scores.items() %}
            {% if sc > 0.04 %}
            <div style="display:flex;align-items:center;
                        gap:5px;margin:2px 0">
              <span style="width:52px;font-size:.65em;
                           color:var(--muted)">
                {{em[:7]}}</span>
              <div style="flex:1;background:#1f2937;
                          height:7px;border-radius:4px">
                <div style="width:{{(sc*100)|int}}%;
                            height:7px;border-radius:4px;
                            background:#6366f1"></div>
              </div>
              <span style="font-size:.65em;color:var(--purple);
                           min-width:28px">
                {{(sc*100)|int}}%</span>
            </div>{% endif %}{% endfor %}
          </div>

          <!-- Action badges -->
          <div style="margin-top:9px">
            <span class="action-badge
              {{'action-on' if s.hand_raised else 'action-off'}}">
              ✋ Hand Raised</span>
            <span class="action-badge
              {{'action-on' if s.waving else 'action-off'}}">
              👋 Waving</span>
            <span class="action-badge
              {{'action-on' if s.clapping else 'action-off'}}">
              👏 Clapping</span>
          </div>
          {% if s.verify_action %}
          <div style="margin-top:5px;font-size:.72em;
                      color:var(--yellow)">
            ⏳ Verifying: {{s.verify_action}}</div>
          {% endif %}
          {% if s.verify_result %}
          <div style="font-size:.72em;color:var(--green)">
            ✅ Action Verified!</div>
          {% endif %}
        </div>
      </div>

      <!-- CONTROLS -->
      <div class="card">
        <h2>🎮 Therapy Controls</h2>
        <form method="POST" action="/cmd">
          <div style="margin-bottom:7px">
            <div style="font-size:.7em;color:var(--muted);
                        margin-bottom:4px">Protocols</div>
            <button class="btn" name="c" value="aba">📚 ABA</button>
            <button class="btn" name="c" value="dtt">🎯 DTT</button>
            <button class="btn" name="c" value="teacch">📅 TEACCH</button>
            <button class="btn" name="c" value="tie">🧠 TIE</button>
          </div>
          <div style="margin-bottom:7px">
            <div style="font-size:.7em;color:var(--muted);
                        margin-bottom:4px">Quick Actions</div>
            <button class="btn btn-g" name="c" value="dance">💃 Dance</button>
            <button class="btn btn-y" name="c" value="celebrate">🎉 Celebrate</button>
            <button class="btn btn-b" name="c" value="game">🎮 Games</button>
            <button class="btn btn-r" name="c" value="break">⏸ Break</button>
          </div>
        </form>

        <!-- SKILLS VIDEOS -->
        <div style="font-size:.7em;color:var(--muted);
                    margin:7px 0 4px">📺 Skill Videos</div>
        <div style="display:flex;flex-wrap:wrap;gap:2px">
          {% for sk in skills %}
          <form method="POST" action="/skill"
                style="display:inline">
            <button class="btn btn-y" name="s"
                    value="{{sk}}"
                    style="font-size:.65em;padding:3px 6px">
              {{sk}}</button>
          </form>{% endfor %}
        </div>

        <form method="POST" action="/search"
              style="display:flex;gap:5px;margin-top:7px">
          <input name="q" placeholder="Search video...">
          <button class="btn">🔍</button>
        </form>

        <!-- PARENT MESSAGE -->
        <form method="POST" action="/parent_msg"
              style="display:flex;gap:5px;margin-top:7px">
          <input name="msg"
                 placeholder="Send to child via Pepper...">
          <button class="btn btn-g">📤</button>
        </form>

        <!-- SET NAME -->
        <form method="POST" action="/name"
              style="display:flex;gap:5px;margin-top:7px">
          <input name="n" placeholder="Child name...">
          <button class="btn">✓</button>
        </form>
      </div>

      <!-- LIVE SESSION CHAT -->
      <div class="card">
        <h2>💬 Live Session Chat</h2>
        <div class="chat-box" id="chat-session">
          {% for msg in s.session_chat[-20:]|reverse %}
          <div class="cm {{'cm-p' if msg.role=='pepper' else 'cm-c'}}">
            <span style="color:{{'var(--purple)' if msg.role=='pepper' else 'var(--green)'}};
                         font-size:.65em">
              {{'🤖 Pepper' if msg.role=='pepper' else '👦 '+s.name}}
              [{{msg.time}}]</span><br>
            {{msg.text}}
          </div>{% endfor %}
        </div>
        <div style="margin-top:6px;
                    display:flex;justify-content:space-between;
                    align-items:center">
          <div style="font-size:.7em;color:var(--muted)">
            {{s.logs|length}} interactions |
            Score: <b style="color:var(--purple)">{{s.score}}</b>
          </div>
          <div>
            {% if s.clap_detected %}
            <span style="color:var(--yellow);font-weight:700">
              👏 CLAP!</span>
            {% endif %}
            {% if s.is_speaking %}
            <span style="color:var(--blue);font-size:.72em">
              🔊 Speaking...</span>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- CHARTS TAB -->
  <div id="tab-charts" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>📈 Attention Over Time</h2>
        <div class="chart-wrap">
          <canvas id="attChart"></canvas>
        </div>
      </div>
      <div class="card">
        <h2>🏆 Score Progress</h2>
        <div class="chart-wrap">
          <canvas id="scoreChart"></canvas>
        </div>
      </div>
    </div>
    <div class="row r2">
      <div class="card">
        <h2>😊 Emotion Distribution (9 types)</h2>
        <div class="chart-wrap">
          <canvas id="emoChart"></canvas>
        </div>
      </div>
      <div class="card">
        <h2>🎯 Skills Progress</h2>
        <div style="display:grid;
                    grid-template-columns:repeat(5,1fr);
                    gap:6px;margin-top:8px">
          {% for sk,val in s.skills.items() %}
          <div style="text-align:center">
            <div style="height:70px;background:#1f2937;
                        border-radius:6px;position:relative;
                        overflow:hidden">
              <div style="position:absolute;bottom:0;
                          width:100%;height:{{val}}%;
                          background:linear-gradient(0deg,
                          #6366f1,#a78bfa);
                          border-radius:6px"></div>
            </div>
            <div style="font-size:.63em;color:var(--muted);
                        margin-top:3px">{{sk}}</div>
            <div style="font-size:.7em;color:var(--purple);
                        font-weight:700">{{val}}%</div>
          </div>{% endfor %}
        </div>
      </div>
    </div>

    <div class="card">
      <h2>📋 Session Log</h2>
      <div class="log-box">
        {% for lg in s.logs[-50:]|reverse %}
        <div class="log-item {{lg.type}}">
          <span style="color:#6366f1">{{lg.time}}</span>
          <span class="prot {{lg.proto}}">{{lg.proto}}</span>
          <b style="color:var(--purple)">{{lg.child}}</b>:
          {{lg.msg}}
          <span style="color:#374151;font-size:.73em">
            |{{lg.emo}}</span>
        </div>{% endfor %}
      </div>
      <a href="/export" class="btn btn-g"
         style="display:inline-block;margin-top:7px;
                text-decoration:none">
        📥 Export</a>
    </div>
  </div>

  <!-- GAMES TAB (embedded) -->
  <div id="tab-games" class="tab-content">
    <div class="card">
      <h2>🎮 Game Zone (Port 5009)</h2>
      <div style="margin-bottom:8px;display:flex;gap:8px;
                  flex-wrap:wrap">
        <a href="http://localhost:5009"
           target="_blank" class="btn btn-g">
          🚀 Open Full Game Zone</a>
        <a href="http://localhost:5007"
           target="_blank" class="btn">
          🧠 AI Brain (5007)</a>
        <button class="btn btn-y"
          onclick="document.getElementById('game-frame').src='http://localhost:5009'">
          🔄 Reload Games</button>
      </div>
      <iframe id="game-frame"
              src="http://localhost:5009"
              height="550"
              title="Therapy Games">
      </iframe>
    </div>
  </div>

  <!-- ASSESSMENT TAB -->
  <div id="tab-assessment" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>📋 IASQ Screening (10 Questions)</h2>
        {% if s.iasq_result %}
        <div style="background:#051a0f;border-radius:8px;
                    padding:10px;margin-bottom:10px;
                    border:1px solid var(--green)">
          <div style="font-size:.8em;color:var(--green);
                      font-weight:700">
            Result: {{s.iasq_result}}</div>
          <div style="font-size:.72em;color:var(--muted)">
            Score: {{s.iasq_score}}/50</div>
        </div>{% endif %}
        <form method="POST" action="/iasq">
          {% for i,q in questions.items() %}
          <div style="background:#0a1020;border-radius:7px;
                      padding:10px;margin:5px 0;
                      border:1px solid var(--border)">
            <div style="font-size:.78em;color:var(--text);
                        margin-bottom:6px">
              {{i}}. {{q.q}}</div>
            <div style="display:flex;gap:5px;flex-wrap:wrap">
              {% for j in range(5) %}
              <label style="cursor:pointer;font-size:.7em;
                             color:var(--muted)">
                <input type="radio" name="q{{i}}"
                       value="{{j}}"
                       style="width:auto;margin:0 3px">
                {{j}}
              </label>{% endfor %}
            </div>
          </div>{% endfor %}
          <button class="btn btn-g"
                  style="width:100%;margin-top:8px;padding:9px">
            🔍 Calculate Result</button>
        </form>
      </div>
      <div class="card">
        <h2>📊 Assessment Analysis</h2>
        {% if s.iasq_result %}
        {% set pct=(s.iasq_score/50*100)|int %}
        <div style="text-align:center;padding:15px">
          <div style="font-size:2.2em;font-weight:700;
            color:{{'#34d399' if pct<40 else '#fbbf24' if pct<70 else '#f87171'}}">
            {{s.iasq_result}}</div>
          <div class="bar-bg" style="margin:10px 0">
            <div style="width:{{pct}}%;height:9px;
                        border-radius:6px;
                        background:{{'#34d399' if pct<40 else '#fbbf24' if pct<70 else '#f87171'}}">
            </div>
          </div>
          <div style="font-size:.75em;color:var(--muted)">
            {{pct}}% — Score {{s.iasq_score}}/50</div>
        </div>
        <div style="font-size:.74em;color:#9ca3af;
                    line-height:1.7;margin-top:10px">
          <b style="color:var(--purple)">Recommendations:</b><br>
          {% if pct<40 %}
          • Continue 2x/week therapy sessions<br>
          • Focus on social skills and communication<br>
          • Monitor progress monthly
          {% elif pct<70 %}
          • Increase to 3x/week therapy<br>
          • Start intensive ABA + DTT programs<br>
          • Consult developmental pediatrician
          {% else %}
          • Seek immediate specialist evaluation<br>
          • Consider intensive early intervention (EIBI)<br>
          • Apply for special education support
          {% endif %}
        </div>
        {% else %}
        <div style="text-align:center;padding:30px;
                    color:var(--muted);font-size:.8em">
          Complete the IASQ test to see results here.
        </div>{% endif %}
      </div>
    </div>
  </div>

  <!-- CHATBOT TAB -->
  <div id="tab-chatbot" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>🤖 Autism Specialist AI (Arabic + English)</h2>
        <div class="chat-box" id="chat-parent">
          {% for msg in s.chat_history[-20:]|reverse %}
          <div class="cm {{'cm-p' if msg.role=='pepper' else 'cm-par'}}">
            <span style="color:{{'var(--purple)' if msg.role=='pepper' else 'var(--blue)'}};
                         font-size:.65em">
              {{'🤖 Pepper' if msg.role=='pepper'
                else '👨‍👩‍👧 Parent'}} [{{msg.time}}]</span><br>
            {{msg.text}}
          </div>{% endfor %}
          {% if not s.chat_history %}
          <div style="color:var(--muted);text-align:center;
                      padding:20px;font-size:.78em">
            Ask anything about autism, therapy, or your child 🤗
          </div>{% endif %}
        </div>
        <form method="POST" action="/parent_ask"
              style="display:flex;gap:5px">
          <input name="question"
                 placeholder="Ask (English or Arabic)...">
          <button class="btn btn-g">💬</button>
        </form>
      </div>
      <div class="card">
        <h2>📚 Quick Questions</h2>
        {% set qs=[
          "My child has a meltdown, what should I do?",
          "How do I improve eye contact?",
          "Best way to teach toilet training?",
          "How to handle repetitive behaviors?",
          "What is the best therapy for autism?",
          "How to help with sleep problems?",
          "My child avoids food textures - help!",
          "كيف أتعامل مع نوبات الغضب؟",
          "كيف أساعد طفلي على التواصل البصري؟",
          "ما هي أفضل طريقة لتعليم طفلي؟",
        ]%}
        {% for q in qs %}
        <form method="POST" action="/parent_ask">
          <button class="btn"
                  name="question" value="{{q}}"
                  style="width:100%;text-align:left;
                         margin:2px 0;font-size:.71em;
                         padding:6px 9px">
            {{q}}</button>
        </form>{% endfor %}
      </div>
    </div>
  </div>

  <!-- NOTES TAB -->
  <div id="tab-notes" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>📝 Add Observation</h2>
        <form method="POST" action="/add_note">
          <select name="category" style="margin-bottom:7px">
            <option>behavior</option>
            <option>progress</option>
            <option>concern</option>
            <option>milestone 🎉</option>
            <option>other</option>
          </select>
          <textarea name="note"
            placeholder="Record what you observed...
Example: Made eye contact for 5 seconds!
Example: Had meltdown when TV was turned off."></textarea>
          <button class="btn btn-g"
                  style="width:100%;margin-top:7px;padding:9px">
            ➕ Save Note</button>
        </form>
      </div>
      <div class="card">
        <h2>📋 Notes History</h2>
        <div style="max-height:320px;overflow-y:auto">
          {% for note in s.parent_notes[-20:]|reverse %}
          <div class="note">
            <div style="display:flex;justify-content:space-between;
                        margin-bottom:3px">
              <span style="color:var(--purple);font-size:.68em;
                           font-weight:700">
                {{note.category.upper()}}</span>
              <span style="color:var(--muted);font-size:.67em">
                {{note.time}}</span>
            </div>
            {{note.text}}
          </div>{% endfor %}
        </div>
      </div>
    </div>
  </div>

  <!-- HELP TAB -->
  <div id="tab-help" class="tab-content">
    <div class="row r3">
      <div class="help-card">
        <div class="hc-title">🎯 ABA Protocol</div>
        <div class="hc-body">
          Break tasks into tiny steps. Give immediate specific
          praise within 2 seconds. Use token economy (stars).
          Repeat 10-20 trials per session.
        </div>
        <div class="tip">💡 If child fails 3×  → switch to
          easier version immediately.</div>
      </div>
      <div class="help-card">
        <div class="hc-title">📚 DTT Protocol</div>
        <div class="hc-body">
          ONE instruction at a time. Wait 5 seconds.
          Prompt hierarchy: verbal → gestural → physical.
          Always end with feedback. Keep sessions 10-15 min.
        </div>
        <div class="tip">💡 Same words, same order every time.
          Consistency = less anxiety.</div>
      </div>
      <div class="help-card">
        <div class="hc-title">📅 TEACCH Visual Schedules</div>
        <div class="hc-body">
          Picture schedule for every day.
          Show NEXT item only (not whole day).
          Use visual timers. Keep workspace organized.
        </div>
        <div class="tip">💡 Let child check off activities.
          Gives control, reduces meltdowns.</div>
      </div>
      <div class="help-card">
        <div class="hc-title">⚠️ Meltdown Protocol</div>
        <div class="hc-body">
          1. Stay calm<br>
          2. Remove triggers immediately<br>
          3. Give physical space<br>
          4. Speak softly, max 5 words<br>
          5. NO forced eye contact<br>
          6. Offer comfort item
        </div>
        <div class="tip">💡 Keep "calm kit": headphones,
          fidget toy, weighted blanket.</div>
      </div>
      <div class="help-card">
        <div class="hc-title">👏 Reinforcement Guide</div>
        <div class="hc-body">
          Praise within 2 seconds of success.
          Be SPECIFIC: "Great clapping!" not "Good job!".
          Find top 3 motivators for YOUR child.
        </div>
        <div class="tip">💡 Create "reward menu" with
          10 items child loves.</div>
      </div>
      <div class="help-card">
        <div class="hc-title">📊 Dashboard Guide</div>
        <div class="hc-body">
          <b>Att >70%</b> → engaged ✅<br>
          <b>P0</b> → great, no prompts ✅<br>
          <b>P1</b> → verbal reminder ℹ️<br>
          <b>P2</b> → visual cue ⚠️<br>
          <b>P3</b> → direct support 🛑<br>
          <b>Distressed</b> → take break now
        </div>
        <div class="tip">💡 Screenshot & share with
          therapist every week.</div>
      </div>
    </div>
    <!-- Printable summary -->
    <div class="card" style="margin-top:10px">
      <h2>📋 Session Summary</h2>
      <div style="background:#0a1020;border-radius:8px;
                  padding:12px;font-size:.76em;
                  color:#9ca3af;line-height:2">
        Child: <b style="color:var(--text)">{{s.name}}</b> |
        Age: {{s.age}} | Date: {{now}}<br>
        Score: <b style="color:var(--purple)">{{s.score}}</b> |
        Tokens: <b style="color:var(--yellow)">⭐{{s.tokens}}</b> |
        Interactions: {{s.logs|length}}<br>
        Emotion: {{s.emotion}} |
        Protocol: {{s.protocol}} |
        Level: {{s.difficulty.upper()}}<br>
        IASQ: {{s.iasq_result or 'Not taken'}} |
        Notes: {{s.parent_notes|length}}
      </div>
      <div style="margin-top:8px;display:flex;gap:7px">
        <a href="/export" class="btn btn-g"
           style="text-decoration:none">📥 Export JSON</a>
        <a href="/export_notes" class="btn"
           style="text-decoration:none">📝 Export Notes</a>
      </div>
    </div>
  </div>

  <!-- SETTINGS TAB -->
  <div id="tab-settings" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>👦 Child Profile</h2>
        <form method="POST" action="/update_child">
          <label style="font-size:.73em;color:var(--muted)">Name</label>
          <input name="name" value="{{s.name}}"
                 style="margin-bottom:7px">
          <label style="font-size:.73em;color:var(--muted)">Age</label>
          <input name="age" type="number"
                 value="{{s.age}}" min="1" max="18"
                 style="margin-bottom:7px">
          <label style="font-size:.73em;color:var(--muted)">Diagnosis</label>
          <select name="diagnosis" style="margin-bottom:7px">
            <option {{'selected' if s.diagnosis=='ASD Level 1'}}>ASD Level 1</option>
            <option {{'selected' if s.diagnosis=='ASD Level 2'}}>ASD Level 2</option>
            <option {{'selected' if s.diagnosis=='ASD Level 3'}}>ASD Level 3</option>
            <option>Suspected ASD</option>
          </select>
          <button class="btn btn-g"
                  style="width:100%;padding:9px">
            💾 Save Profile</button>
        </form>
      </div>
      <div class="card">
        <h2>⚙️ Therapy Settings</h2>
        <form method="POST" action="/update_settings">
          <label style="font-size:.73em;color:var(--muted)">Difficulty</label>
          <select name="difficulty" style="margin-bottom:7px">
            <option {{'selected' if s.difficulty=='easy'}}>easy</option>
            <option {{'selected' if s.difficulty=='medium'}}>medium</option>
            <option {{'selected' if s.difficulty=='hard'}}>hard</option>
          </select>
          <label style="font-size:.73em;color:var(--muted)">
            Mic Sensitivity (lower=more sensitive)</label>
          <input name="mic_energy" type="number"
                 value="10" min="5" max="100"
                 style="margin-bottom:7px">
          <label style="font-size:.73em;color:var(--muted)">
            Camera Window Scale</label>
          <select name="cam_scale" style="margin-bottom:7px">
            <option value="mini">Mini (320x240)</option>
            <option value="medium">Medium (640x480)</option>
            <option value="large">Large (960x540)</option>
          </select>
          <button class="btn btn-g"
                  style="width:100%;padding:9px">
            💾 Save Settings</button>
        </form>
      </div>
    </div>
  </div>

</div><!-- end main -->

<script>
// TABS
function showTab(name){
  document.querySelectorAll('.tab-content')
    .forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab')
    .forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name)
    .classList.add('active');
  event.target.classList.add('active');
}

// CHARTS
const attData   = {{att_history|tojson}};
const scoreData = {{score_history|tojson}};
const emoData   = {{emo_dist|tojson}};
const labels    = Array.from(
  {length:attData.length},(_,i)=>i+1);

const CO={
  responsive:true,maintainAspectRatio:false,
  plugins:{legend:{labels:{
    color:'#9ca3af',font:{size:10}}}},
  scales:{
    x:{ticks:{color:'#6b7280',font:{size:8}},
       grid:{color:'#1f2937'}},
    y:{ticks:{color:'#6b7280',font:{size:8}},
       grid:{color:'#1f2937'}}
  }
};

if(document.getElementById('attChart')){
  new Chart(document.getElementById('attChart'),{
    type:'line',
    data:{labels,datasets:[{
      label:'Attention %',data:attData,
      borderColor:'#6366f1',
      backgroundColor:'rgba(99,102,241,0.12)',
      tension:0.4,fill:true,pointRadius:2,
    }]},
    options:{...CO,scales:{...CO.scales,
      y:{...CO.scales.y,min:0,max:100}}}
  });
}
if(document.getElementById('scoreChart')){
  new Chart(document.getElementById('scoreChart'),{
    type:'bar',
    data:{labels,datasets:[{
      label:'Score',data:scoreData,
      backgroundColor:'rgba(167,139,250,0.5)',
      borderColor:'#a78bfa',borderWidth:1,
    }]},
    options:CO
  });
}
if(document.getElementById('emoChart')&&
   Object.keys(emoData).length>0){
  const EC={
    happy:'#34d399',sad:'#60a5fa',angry:'#f87171',
    neutral:'#9ca3af',fear:'#fbbf24',
    surprise:'#c084fc',joy:'#34d399',
    confused:'#fb923c',disgust:'#6ee7b7'
  };
  new Chart(document.getElementById('emoChart'),{
    type:'doughnut',
    data:{
      labels:Object.keys(emoData),
      datasets:[{
        data:Object.values(emoData),
        backgroundColor:Object.keys(emoData)
          .map(e=>EC[e]||'#6366f1'),
      }]
    },
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'right',
        labels:{color:'#9ca3af',font:{size:9}}}}}
  });
}

// Auto-scroll chats
['chat-session','chat-parent'].forEach(id=>{
  const el=document.getElementById(id);
  if(el) el.scrollTop=el.scrollHeight;
});
</script>
</body></html>"""

SKILLS_LIST = [
    "wash face","brush teeth","emotions",
    "colors","numbers","alphabet","sharing",
    "greetings","animals","shapes","toilet",
]
_gemini = None

@master_app.route("/")
def master_dash():
    emo_dist = {}
    for e in S["emo_history"]:
        emo_dist[e] = emo_dist.get(e,0)+1
    qs = {i+1:q for i,q in enumerate(IASQ_QUESTIONS)}
    return render_template_string(
        MASTER_HTML, s=S, skills=SKILLS_LIST,
        att_history=S["att_history"][-40:],
        score_history=S["score_history"][-40:],
        emo_dist=emo_dist,
        questions=qs,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"))

# Reverse-proxy CMD → forwards to AI (5007) too
@master_app.route("/cmd", methods=["POST"])
def master_cmd():
    c = request.form.get("c","")
    S["sim_cmd"] = c
    # Forward to AI brain
    try:
        http_req.post(
            f"http://localhost:{PORT_AI}/cmd",
            json={"cmd":c}, timeout=1)
    except: pass
    return master_dash()

@master_app.route("/skill", methods=["POST"])
def master_skill():
    s   = request.form.get("s","")
    url = ("https://www.youtube.com/results?search_query="
           +urllib.parse.quote(
               s+" autism children educational"))
    webbrowser.open(url)
    log(f"📺 YouTube: {s}")
    return master_dash()

@master_app.route("/search", methods=["POST"])
def master_search():
    q   = request.form.get("q","")
    url = ("https://www.youtube.com/results?search_query="
           +urllib.parse.quote(
               q+" autism educational children"))
    webbrowser.open(url)
    return master_dash()

@master_app.route("/name", methods=["POST"])
def master_name():
    n = request.form.get("n","").strip().title()
    if n: S["name"]=n; S["known"]=True
    return master_dash()

@master_app.route("/parent_msg", methods=["POST"])
def master_parent_msg():
    msg = request.form.get("msg","").strip()
    if msg:
        S["sim_cmd"] = f"parent_msg:{msg}"
    return master_dash()

@master_app.route("/parent_ask", methods=["POST"])
def master_parent_ask():
    q = request.form.get("question","").strip()
    if q and _gemini:
        S["chat_history"].append({
            "role":"parent","text":q,
            "time":datetime.now().strftime("%H:%M:%S")})
        ans = _gemini.parent_ask(q)
        S["chat_history"].append({
            "role":"pepper","text":ans,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(S["chat_history"])>40:
            S["chat_history"]=S["chat_history"][-40:]
    return master_dash()

@master_app.route("/iasq", methods=["POST"])
def master_iasq():
    total = sum(
        int(request.form.get(f"q{i}",0))
        for i in range(1,11))
    if   total <= 20: res="Low Risk ✅"
    elif total <= 35: res="Medium Risk ⚠️"
    else:             res="High Risk 🔴"
    S["iasq_score"]  = total
    S["iasq_result"] = res
    log(f"IASQ: {res} score={total}","success")
    return master_dash()

@master_app.route("/add_note", methods=["POST"])
def master_add_note():
    note = request.form.get("note","").strip()
    cat  = request.form.get("category","other")
    if note:
        S["parent_notes"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": note, "category": cat})
    return master_dash()

@master_app.route("/update_child", methods=["POST"])
def master_update_child():
    S["name"]      = request.form.get("name","Friend").strip().title()
    S["age"]       = int(request.form.get("age",6))
    S["diagnosis"] = request.form.get("diagnosis","ASD Level 2")
    return master_dash()

@master_app.route("/update_settings", methods=["POST"])
def master_update_settings():
    S["difficulty"] = request.form.get("difficulty","easy")
    return master_dash()

@master_app.route("/export")
def master_export():
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(S,f,indent=2,default=str)
    return jsonify({"saved":fn,"score":S["score"]})

@master_app.route("/export_notes")
def master_export_notes():
    fn = f"notes_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(S["parent_notes"],f,indent=2)
    return jsonify({"saved":fn})

@master_app.route("/api/state")
def master_api_state():
    return jsonify({
        "emotion":  S["emotion"],
        "attention":S["attention"],
        "score":    S["score"],
        "child":    S["name"],
        "protocol": S["protocol"],
        "hand_raised": S["hand_raised"],
        "gemini_ok":   S["gemini_ok"],
    })

# ── 404 CATCH-ALL ────────────────────────────────────────────────────
@master_app.errorhandler(404)
def not_found(e):
    return redirect("/"), 302

@master_app.errorhandler(405)
def method_not_allowed(e):
    return redirect("/"), 302


# ══════════════════════════════════════════════════════════════════════
# THERAPY CONTROLLER
# ══════════════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self, gemini, voice, mic,
                 display, sim, actions):
        self.g=gemini; self.v=voice; self.m=mic
        self.d=display; self.s=sim; self.a=actions
        self.running=False

    def _speak(self, text):
        clean = self.a.process(str(text))
        self.d.show_ai(clean)
        if self.s.ok:
            self.s.show_text(clean[:55])
        self.v.say(clean)

    def _ask(self, prompt):
        resp = self.g.ask(prompt)
        self._speak(resp)
        return resp

    def run(self):
        self.running = True
        name = self.m.get_name(self.v)
        S["protocol"] = "GREETING"
        resp = self.g.ask(
            f"Child name is {name}. "
            "Start warmly! [WAVE]. Give first task!")
        self._speak(resp)
        time.sleep(0.5)
        self.m.listen_bg(self._on_speech)

        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx = 0
        last_em = S["emotion"]
        em_t = time.time()
        S["prompt_level"] = 0

        while self.running:
            # Silence check
            if time.time()-S["last_sound"] > 10:
                S["last_sound"] = time.time()
                self._ask("Child silent 10s. Fun prompt!")

            # Prompt level check
            self._prompt_check()

            # Emotion change
            curr = S["emotion"]
            if curr!=last_em and time.time()-em_t > 7:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear","confused"]:
                    self._ask(
                        f"Child just became {curr}. React!")

            # Dashboard command
            self._handle_cmd()

            # Protocol
            prot = protocols[p_idx%len(protocols)]
            p_idx+=1; S["protocol"]=prot
            self._protocol(prot)
            time.sleep(0.3)

    def _prompt_check(self):
        em  = S["emotion"]
        att = S["attention"]
        eng = S["engagement"]
        fd  = S["face_detected"]
        pl  = S.get("prompt_level",0)

        if fd and att>60 and em in ["happy","neutral","joy"]:
            S["prompt_level"] = 0
        elif not fd or att<40:
            if pl < 1:
                S["prompt_level"] = 1
                self._ask(
                    "Child distracted. "
                    "Verbal attention prompt! [POINT]")
        if eng=="distressed" and pl<3:
            S["prompt_level"] = 3
            self._ask(
                f"Child distressed ({em}). "
                "Immediate calming! [HUG]")

    def _handle_cmd(self):
        cmd = S.get("sim_cmd")
        if not cmd: return
        S["sim_cmd"] = None

        if cmd=="dance":
            self._ask("Dance celebrate! [DANCE]")
        elif cmd=="game":
            webbrowser.open(
                f"http://localhost:{PORT_GAME}")
            self._ask("Game time! [CELEBRATE][GAME]")
        elif cmd=="celebrate":
            self._ask(
                "Big celebration! "
                "[CELEBRATE][CLAP][DANCE]")
        elif cmd=="break":
            self._ask("Sensory break. Calm. [NOD]")
        elif cmd.startswith("parent_msg:"):
            msg = cmd[11:]
            self._ask(f"Tell child: {msg}")
        elif cmd in ["aba","dtt","teacch","tie"]:
            S["protocol"] = cmd.upper()

    def _protocol(self, prot):
        name = S["name"]
        em   = S["emotion"]
        att  = S["attention"]
        diff = S["difficulty"]

        if prot=="ABA":
            TASKS = {
                "easy":  ["Clap hands!","Touch nose!",
                          "Wave hello!","Show happy face!",
                          "Open mouth wide!"],
                "medium":["Stand up!","Touch ears!",
                          "Raise your hand!",
                          "Count 3 fingers!","Jump once!"],
                "hard":  ["Say your full name!",
                          "What color is sky?",
                          "Name 2 animals!",
                          "What do you eat for breakfast?"],
            }
            task = random.choice(
                TASKS.get(diff,TASKS["easy"]))
            S["current_task"] = task
            S["task_success"]  = False

            # Request action verification if motor task
            if any(w in task.lower()
                   for w in ["hand","wave","clap","stand",
                              "jump","touch"]):
                verify_token = f"[VERIFY: {task}]"
                S["verify_action"] = task
                S["verify_result"] = False

            resp = self.g.ask(
                f"ABA task '{task}' for {name}. "
                f"Em:{em} Att:{att}%")
            self._speak(resp)
            self.d.show_task(task)

            success = self._wait(task, 12)
            if success:
                S["score"]   += 10
                S["streak"]  += 1
                S["tokens"]  += 1
                S["clap_detected"] = False
                S["task_success"]  = False
                S["verify_action"] = None

                resp = self.g.ask(
                    f"{name} did '{task}'! "
                    "[CLAP][REWARD:2]")
                self._speak(resp)
                self.d.show_praise("AMAZING! ⭐⭐")
                log(f"ABA: {task} ✅","success","ABA")

                # Level up
                if S["streak"] >= 3:
                    if diff=="easy":
                        S["difficulty"]="medium"
                    elif diff=="medium":
                        S["difficulty"]="hard"
                    S["streak"]=0
                    self._ask(
                        "Leveled up! "
                        "[DANCE][CELEBRATE]")

                # Update skills
                sp = min(95, 40+S["score"]//5)
                for sk in S["skills"]:
                    S["skills"][sk] = min(
                        100,S["skills"][sk]+
                        random.randint(0,2))
            else:
                S["streak"] = 0
                resp = self.g.ask(
                    f"{name} needs help with '{task}'. "
                    "Gentle retry.")
                self._speak(resp)
                log(f"ABA: {task} ❌","fail","ABA")
            time.sleep(2)

        elif prot=="DTT":
            resp = self.g.ask(
                f"ONE DTT trial for {name}. "
                f"Diff:{diff} Em:{em}")
            self._speak(resp)
            self.d.show_task("DTT Trial")
            ok = self._wait("DTT",10)
            if ok:
                S["score"] += 12; S["tokens"] += 1
                self._ask(f"DTT success! [CLAP][REWARD:1]")
                self.d.show_praise("CORRECT! ✅")
                log("DTT ✅","success","DTT")
            else:
                self._ask("DTT error correction. Try again.")
                log("DTT ❌","fail","DTT")
            time.sleep(2)

        elif prot=="TEACCH":
            resp = self.g.ask(
                f"TEACCH schedule step for {name}. Em:{em}")
            self._speak(resp)
            time.sleep(3)
            if S["emotion"] in ["happy","joy"]:
                S["score"] += 15
            log("TEACCH ✅","success","TEACCH")

        elif prot=="TIE":
            resp = self.g.ask(
                f"TIE adaptive for {name}. "
                f"Em:{em} Att:{att}% "
                f"Eng:{S['engagement']}")
            self._speak(resp)
            time.sleep(3)
            S["score"] += 8
            log("TIE ✅","success","TIE")

    def _wait(self, task, timeout=12):
        deadline = time.time()+timeout
        while time.time()<deadline:
            if S["clap_detected"] and \
               "clap" in task.lower():
                return True
            if S["task_success"]:
                return True
            if S["verify_result"]:
                S["verify_result"]=False
                return True
            if (S["emotion"] in ["happy","joy"]
                    and S["attention"]>65):
                return True
            time.sleep(0.25)
        return False

    def _on_speech(self, text):
        S["last_sound"] = time.time()
        if not text: return
        t    = text.lower()
        name = S["name"]

        if text=="[sound]":
            self.v.say(f"I heard you {name}!")
            return

        # Interrupt if speaking
        if S["is_speaking"]:
            self.v.stop()

        # Name learning
        if not S["known"]:
            n = self.m._extract(text)
            if n:
                S["name"]=n; S["known"]=True
                self._ask(
                    f"Child is {n}. Welcome! [WAVE]")
            return

        # How-to → YouTube
        edu = ["how","what is","show me","what does",
               "teach","explain","كيف","ما هو","أرني"]
        if any(w in t for w in edu):
            resp = self.g.ask(
                f"Child asked: '{text}'. "
                "Answer simply. Use [YOUTUBE:...] "
                "for educational video.")
            self._speak(resp)
            return

        # Game request
        if any(w in t for w in
               ["play","game","fun","العب","لعبة"]):
            self._ask(
                f"{name} wants game! [GAME][CELEBRATE]")
            return

        # Task success keywords
        task = S.get("current_task","")
        if task:
            kws = task.lower().replace("!","").split()
            if any(w in t for w in kws if len(w)>2):
                S["task_success"] = True

        # General
        resp = self.g.ask(
            f"Child said: '{text}'. Therapy response.")
        self._speak(resp)


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
def run_server(app, port, name):
    """Run Flask server"""
    app.run(port=port,debug=False,
            use_reloader=False,threaded=True)

def main():
    global _gemini

    print("""
╔══════════════════════════════════════════════════════════╗
║  UNIFIED AI THERAPY HUB                                 ║
║  🌐 Master:  http://localhost:5001                      ║
║  🧠 AI:      http://localhost:5007                      ║
║  🎮 Games:   http://localhost:5009                      ║
║  📹 Windows: 320x240 (mini)                             ║
║  🎤 Mic:     energy=10 (whisper detection)              ║
╚══════════════════════════════════════════════════════════╝
""")

    # Start all 3 Flask servers
    for app, port, name in [
        (game_app,   PORT_GAME,   "Game"),
        (ai_app,     PORT_AI,     "AI"),
        (master_app, PORT_MASTER, "Master"),
    ]:
        t = threading.Thread(
            target=run_server,
            args=(app, port, name),
            daemon=True)
        t.start()
        print(f"✅ {name} server: http://localhost:{port}")
        time.sleep(0.4)

    time.sleep(0.8)

    # Init components
    gemini  = GeminiBrain()
    _gemini = gemini
    voice   = Voice()
    camera  = Camera()
    em_eng  = EmotionEngine()
    display = MiniDisplay(em_eng, camera)
    mic     = Mic()
    sim     = Sim()
    pepper  = sim.launch()
    actions = Actions(pepper)

    time.sleep(1.5)
    S["name"] = "Friend"

    voice.say(
        "Welcome to the Unified Therapy Hub! "
        "I am Pepper! Let us begin!")
    if pepper:
        threading.Thread(
            target=actions._wave,daemon=True).start()

    ctrl = TherapyCtrl(
        gemini,voice,mic,display,sim,actions)
    threading.Thread(
        target=ctrl.run,daemon=True).start()

    print("\n" + "="*55)
    print("✅ ALL SYSTEMS ACTIVE")
    print("="*55)
    print(f"🌐 Master Dashboard: http://localhost:{PORT_MASTER}")
    print(f"🧠 AI Brain:         http://localhost:{PORT_AI}")
    print(f"🎮 Games:            http://localhost:{PORT_GAME}")
    print("📹 Mini windows: Press Q to quit")
    print("⌨️  Commands: 'report' | 'name X' | 'exit'")
    print("="*55+"\n")

    while getattr(display,'running',True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()
            if cl in ["q","exit","quit"]:
                ctrl.running=False; display.stop(); break
            elif cl=="report":
                print(f"Score:{S['score']} "
                      f"Tokens:⭐{S['tokens']} "
                      f"Emotion:{S['emotion']} "
                      f"Att:{S['attention']}% "
                      f"Hand:{S['hand_raised']}")
            elif cl.startswith("name "):
                n=cl[5:].strip().title()
                S["name"]=n; S["known"]=True
                voice.say(f"Hello {n}!")
            elif cl=="interrupt":
                voice.stop()
                print("🛑 Speech interrupted!")
            else:
                ctrl._on_speech(cmd)
        except (KeyboardInterrupt,EOFError):
            break

    ctrl.running=False
    voice.say("Goodbye! Amazing session today!")
    fn=f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(S,f,indent=2,default=str)
    print(f"📄 Saved: {fn}")

if __name__=="__main__":
    main()
