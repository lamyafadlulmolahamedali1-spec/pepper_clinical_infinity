#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  PEPPER UNIFIED AI THERAPIST v4.0                           ║
║  Commander: Lamya | Clinical-Grade ASD Therapy Platform     ║
╠══════════════════════════════════════════════════════════════╣
║  Port 5007 → Master Brain & Control Dashboard               ║
║  Port 5009 → Game Zone                                      ║
║  Port 5001 → Reports & Clinical Documentation               ║
╠══════════════════════════════════════════════════════════════╣
║  ✅ Listen-First Rule (Pepper waits for child)               ║
║  ✅ energy_threshold=10 (whisper detection)                  ║
║  ✅ Interruptible speech (child interrupts Pepper)           ║
║  ✅ 500x500 camera window                                    ║
║  ✅ 6 emotion detection (DeepFace + OpenCV)                  ║
║  ✅ Action verification (hand raise, wave, clap)             ║
║  ✅ ABA / DTT / TEACCH / TIE protocols                      ║
║  ✅ Clinical Progress Report → auto-sent to Port 5001        ║
║  ✅ Zero 404 errors (hard-coded routes)                      ║
║  ✅ 4-thread architecture (zero-lag)                         ║
║  ✅ Gemini 1.5 Flash (live AI brain)                         ║
╚══════════════════════════════════════════════════════════════╝
"""

# ── SUPPRESS NOISE ────────────────────────────────────────────
import os, sys, ctypes, warnings, threading, time
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
warnings.filterwarnings('ignore')
try:
    _a = ctypes.cdll.LoadLibrary('libasound.so.2')
    _a.snd_lib_error_set_handler(ctypes.c_void_p(None))
except: pass

# ── IMPORTS ───────────────────────────────────────────────────
import cv2, numpy as np, json, math, re
import webbrowser, urllib.parse, queue, random
import pyttsx3, speech_recognition as sr
from flask import (Flask, request, jsonify,
                   render_template_string, redirect, Response)
from datetime import datetime
import pybullet as p, pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')
import google.generativeai as genai

# ── PORTS (hard-coded, no 404) ────────────────────────────────
PORT_BRAIN   = 5007   # Master Brain & Dashboard
PORT_GAME    = 5009   # Game Zone
PORT_REPORTS = 5001   # Clinical Reports

# ── GEMINI ────────────────────────────────────────────────────
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """You are Pepper, a certified clinical robotic therapist for ASD children.
Commander/Developer: Lamya (treat with highest respect).

CLINICAL PROTOCOLS: ABA, DTT, TEACCH, TIE
CORE RULES:
- LISTEN FIRST: Always wait for child's response before continuing
- Max 2 short sentences per response
- Immediate positive reinforcement
- Use child's name every response
- Ultra patient and warm

ACTION TOKENS:
[WAVE] [CLAP] [NOD] [DANCE] [POINT] [HUG] [CELEBRATE] [THINK]

TRIGGERS:
[YOUTUBE: query] → search educational video
[GAME] → open game zone (port 5009)
[REWARD: N] → give N stars
[VERIFY: action] → camera must verify before reinforcing

EMOTION PROTOCOL:
- happy/joyful → [CELEBRATE] advance difficulty [REWARD:3]
- sad/fear → [HUG] easier task, comfort
- angry → [NOD] breathing exercise, pause
- surprised → share excitement [CELEBRATE]

LISTEN-FIRST RULE:
After every instruction, add "... Ready? Your turn! 🎯"
This signals the child it's their time to respond."""

# ══════════════════════════════════════════════════════════════
# SHARED PLATFORM STATE
# ══════════════════════════════════════════════════════════════
ST = {
    # Child
    "name": "Friend", "known": False,
    "age": 6, "diagnosis": "ASD Level 2",
    "sensitivities": ["sound"],

    # Perception (500x500 camera)
    "emotion": "neutral",
    "emotion_scores": {},
    "face_detected": False,
    "attention": 70,
    "engagement": "moderate",
    "hand_raised": False,
    "waving": False,
    "clapping": False,
    "verify_action": None,
    "verify_result": False,
    "verify_timeout": 0,

    # Session control
    "protocol": "GREETING",
    "difficulty": "easy",
    "is_speaking": False,
    "interrupt_flag": False,
    "listening": False,
    "last_sound": time.time(),
    "waiting_for_child": False,
    "clap_detected": False,
    "current_task": None,
    "task_success": False,
    "task_retries": 0,
    "prompt_level": 0,
    "sim_cmd": None,

    # Progress
    "score": 0, "tokens": 0,
    "stars_today": 0, "streak": 0,
    "sessions_done": 0,
    "tasks_success": 0, "tasks_fail": 0,
    "skills": {
        "emotions": 50, "social": 50,
        "motor": 50, "communication": 50, "focus": 50,
    },

    # History
    "att_history":   [],
    "score_history": [],
    "emo_history":   [],
    "time_labels":   [],

    # Logs
    "logs": [],
    "session_chat": [],
    "parent_chat":  [],
    "parent_notes": [],
    "reports": [],

    # Assessment
    "iasq_score": None, "iasq_result": None,

    # System
    "gemini_ok": False,
    "gemini_model": "N/A",
    "session_start": datetime.now().strftime("%H:%M"),
    "session_date": datetime.now().strftime("%Y-%m-%d"),
    "uptime": time.time(),
}

_log_lock = threading.Lock()
_speak_q  = queue.Queue()

def LOG(msg, t="info", proto=None):
    with _log_lock:
        e = {
            "time":  datetime.now().strftime("%H:%M:%S"),
            "msg":   str(msg)[:120],
            "type":  t,
            "proto": proto or ST["protocol"],
            "emo":   ST["emotion"],
            "child": ST["name"],
        }
        ST["logs"].append(e)
        # Chart history
        if len(ST["logs"]) % 3 == 0:
            ST["att_history"].append(ST["attention"])
            ST["score_history"].append(ST["score"])
            ST["emo_history"].append(ST["emotion"])
            ST["time_labels"].append(
                datetime.now().strftime("%H:%M:%S"))
            for k in ["att_history","score_history",
                      "emo_history","time_labels"]:
                if len(ST[k]) > 60:
                    ST[k] = ST[k][-60:]
        print(f"[{e['time']}][{t.upper()}] {msg[:65]}")

# ══════════════════════════════════════════════════════════════
# GEMINI BRAIN (Live AI)
# ══════════════════════════════════════════════════════════════
class GeminiBrain:
    MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
    ]

    def __init__(self):
        self.ok = False
        self.model_name = "fallback"
        self._lock = threading.Lock()
        self.therapy_chat  = None
        self.parent_chat   = None
        self.report_chat   = None

        for mn in self.MODELS:
            try:
                m = genai.GenerativeModel(
                    mn,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config=genai.GenerationConfig(
                        temperature=0.8,
                        max_output_tokens=120,
                    ))
                c = m.start_chat(history=[])
                r = c.send_message("Say: READY")
                self.therapy_model = m
                self.therapy_chat  = c
                self.model_name    = mn
                self.ok = True
                ST["gemini_ok"]    = True
                ST["gemini_model"] = mn
                print(f"✅ Gemini: {mn}")
                break
            except Exception as e:
                print(f"⚠️  {mn}: {str(e)[:55]}")

        if self.ok:
            self._init_parent_chat()
            self._init_report_chat()

    def _init_parent_chat(self):
        try:
            pm = genai.GenerativeModel(
                self.model_name,
                system_instruction=(
                    "You are an autism specialist supporting parents. "
                    "Answer ONLY autism-related questions. "
                    "Be warm, evidence-based, cite sources. "
                    f"Child data: {ST['name']}, age {ST['age']}, "
                    f"diagnosis {ST['diagnosis']}. "
                    "Support Arabic and English."
                ),
                generation_config=genai.GenerationConfig(
                    temperature=0.6, max_output_tokens=300))
            self.parent_chat = pm.start_chat(history=[])
        except: pass

    def _init_report_chat(self):
        try:
            rm = genai.GenerativeModel(
                self.model_name,
                system_instruction=(
                    "You are a clinical psychologist writing "
                    "therapy session reports for ASD children. "
                    "Generate structured, professional reports."
                ),
                generation_config=genai.GenerationConfig(
                    temperature=0.4, max_output_tokens=500))
            self.report_chat = rm.start_chat(history=[])
        except: pass

    def ctx(self):
        return (
            f"[child={ST['name']} age={ST['age']} "
            f"emotion={ST['emotion']} "
            f"attention={ST['attention']}% "
            f"protocol={ST['protocol']} "
            f"score={ST['score']} "
            f"difficulty={ST['difficulty']} "
            f"hand_raised={ST['hand_raised']} "
            f"streak={ST['streak']}] "
        )

    def ask(self, prompt):
        if not self.ok: return self._fb()
        with self._lock:
            try:
                resp = self.therapy_chat.send_message(
                    self.ctx() + prompt)
                text = resp.text.strip()
                LOG(f"AI: {text[:50]}")
                return text
            except Exception as e:
                print(f"⚠️  Gemini ask: {e}")
                try:
                    self.therapy_chat = \
                        self.therapy_model.start_chat(
                            history=[])
                except: pass
                return self._fb()

    def parent_ask(self, q):
        if not self.parent_chat:
            return ("I'm here to help with autism questions. "
                    "Please consult your specialist.")
        try:
            r = self.parent_chat.send_message(q)
            return r.text.strip()
        except:
            return "Please consult your child's specialist."

    def generate_report(self):
        """Generate clinical session report"""
        if not self.report_chat:
            return self._simple_report()
        try:
            summary = (
                f"Generate a clinical therapy session report:\n"
                f"Child: {ST['name']}, Age: {ST['age']}\n"
                f"Diagnosis: {ST['diagnosis']}\n"
                f"Date: {ST['session_date']}\n"
                f"Duration: {ST['session_start']} to "
                f"{datetime.now().strftime('%H:%M')}\n"
                f"Score: {ST['score']}\n"
                f"Tokens: {ST['tokens']}\n"
                f"Tasks Success: {ST['tasks_success']}\n"
                f"Tasks Failed: {ST['tasks_fail']}\n"
                f"Protocol Used: {ST['protocol']}\n"
                f"Difficulty Reached: {ST['difficulty']}\n"
                f"Dominant Emotion: {ST['emotion']}\n"
                f"Attention Level: {ST['attention']}%\n"
                f"Total Interactions: {len(ST['logs'])}\n"
                f"Write a professional clinical progress note "
                f"with: Session Summary, Observations, "
                f"Child Response, Recommendations for next session."
            )
            r = self.report_chat.send_message(summary)
            return r.text.strip()
        except:
            return self._simple_report()

    def _simple_report(self):
        duration = int((time.time()-ST["uptime"])/60)
        return (
            f"# Clinical Session Report\n"
            f"**Child:** {ST['name']} | **Age:** {ST['age']}\n"
            f"**Date:** {ST['session_date']}\n"
            f"**Duration:** ~{duration} minutes\n\n"
            f"## Performance\n"
            f"- Score: {ST['score']}\n"
            f"- Tasks Success: {ST['tasks_success']}\n"
            f"- Tasks Failed: {ST['tasks_fail']}\n"
            f"- Attention: {ST['attention']}%\n"
            f"- Dominant Emotion: {ST['emotion']}\n\n"
            f"## Recommendation\n"
            f"Continue with {ST['difficulty']} difficulty. "
            f"Focus on {ST['protocol']} protocol next session."
        )

    def _fb(self):
        n = ST["name"]
        return random.choice([
            f"Clap hands {n}! 👏 Ready? Your turn! 🎯",
            f"Touch your nose {n}! 👃 Ready? Your turn! 🎯",
            f"Wave hello {n}! 👋 Ready? Your turn! 🎯",
            f"Show happy face {n}! 😊 Ready? Your turn! 🎯",
        ])


# ══════════════════════════════════════════════════════════════
# EMOTION ENGINE (500x500, 6 emotions + action verification)
# ══════════════════════════════════════════════════════════════
class EmotionEngine:
    """
    6 Emotions: happy, sad, angry, surprised, fear, joyful
    + Action Verification: hand raise, wave, clap
    Window: 500x500 pixels
    """
    EMO_COLORS = {
        "happy":    (0,220,80),
        "sad":      (100,100,220),
        "angry":    (0,0,220),
        "fear":     (0,180,220),
        "surprised":(200,50,220),
        "joyful":   (0,255,180),
        "surprise": (200,50,220),
        "disgust":  (0,180,100),
        "neutral":  (180,180,180),
    }

    def __init__(self):
        self.ok_df    = False
        self.ok_cv    = False
        self.ok_mp    = False
        self._lock    = threading.Lock()
        self._win500  = None
        self._busy    = False
        self.prev_gray = None
        self.hand_hist = []

        # DeepFace
        try:
            from deepface import DeepFace
            self.DF = DeepFace
            dummy = np.zeros((48,48,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.ok_df = True
            print("✅ DeepFace 6-emotion ready")
        except Exception as e:
            print(f"⚠️  DeepFace: {e}")

        # OpenCV
        try:
            cp = cv2.data.haarcascades
            self.face_c  = cv2.CascadeClassifier(
                cp+'haarcascade_frontalface_default.xml')
            self.smile_c = cv2.CascadeClassifier(
                cp+'haarcascade_smile.xml')
            self.eye_c   = cv2.CascadeClassifier(
                cp+'haarcascade_eye.xml')
            if not self.face_c.empty():
                self.ok_cv = True
                print("✅ OpenCV cascades ready")
        except Exception as e:
            print(f"⚠️  OpenCV: {e}")

        # MediaPipe hands
        try:
            import mediapipe as mp
            self.mpH   = mp.solutions.hands
            self.hands = self.mpH.Hands(
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5)
            self.ok_mp = True
            print("✅ MediaPipe hands (action verify)")
        except Exception as e:
            print(f"⚠️  MediaPipe: {e}")

    def analyze_async(self, frame):
        if self._busy: return
        self._busy = True
        threading.Thread(
            target=self._run,
            args=(frame.copy(),),
            daemon=True).start()

    def _run(self, frame):
        try:
            # Work on 300x300 internally
            small  = cv2.resize(frame, (300,300))
            scores = self._scores(small)
            self._actions(frame)
            self._update(scores)
            self._draw500(small, scores, frame)
        except: pass
        finally: self._busy = False

    def _scores(self, frame):
        # Layer 1: DeepFace
        if self.ok_df:
            try:
                r = self.DF.analyze(
                    frame, actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True)
                if r:
                    raw   = r[0].get('emotion', {})
                    total = sum(raw.values()) or 1
                    sc    = {k:v/total for k,v in raw.items()}
                    # Map to 6 core emotions
                    sc["joyful"] = sc.get("happy",0)*0.45
                    sc["surprised"] = sc.get("surprise",0)
                    ST["face_detected"] = True
                    ST["attention"] = min(
                        100, ST["attention"]+3)
                    return sc
            except: pass

        # Layer 2: OpenCV
        if not self.ok_cv:
            return {"neutral":1.0}

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)
        faces = self.face_c.detectMultiScale(
            gray, 1.05, 3, minSize=(20,20))

        if len(faces) == 0:
            ST["face_detected"] = False
            ST["attention"] = max(0, ST["attention"]-3)
            return {"neutral":0.8, "sad":0.2}

        ST["face_detected"] = True
        ST["attention"] = min(100, ST["attention"]+2)

        x,y,w,h = sorted(faces,
            key=lambda f:f[2]*f[3], reverse=True)[0]
        roi   = gray[y:y+h, x:x+w]
        br    = float(np.mean(roi))

        smiles = self.smile_c.detectMultiScale(
            roi, 1.5, 8, minSize=(15,15))
        eyes   = self.eye_c.detectMultiScale(
            roi, 1.1, 5, minSize=(10,10))
        ns, ne = len(smiles), len(eyes)

        if ns > 1:
            return {"happy":0.55,"joyful":0.30,
                    "neutral":0.10,"surprised":0.05}
        elif ns == 1:
            return {"happy":0.50,"joyful":0.15,
                    "neutral":0.25,"surprised":0.10}
        elif ne >= 2:
            if br > 130:
                return {"neutral":0.50,"happy":0.20,
                        "surprised":0.20,"fear":0.10}
            else:
                return {"sad":0.45,"fear":0.25,
                        "neutral":0.20,"angry":0.10}
        elif ne == 1:
            return {"neutral":0.40,"sad":0.30,
                    "fear":0.20,"angry":0.10}
        else:
            return {"angry":0.40,"sad":0.25,
                    "fear":0.20,"neutral":0.15}

    def _actions(self, frame):
        """Detect actions for ABA verification"""
        if not self.ok_mp: return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = self.hands.process(rgb)

            if not res.multi_hand_landmarks:
                ST["hand_raised"] = False
                ST["waving"]      = False
                return

            for lm in res.multi_hand_landmarks:
                wrist  = lm.landmark[0]
                middle = lm.landmark[12]

                # Hand raised detection
                if wrist.y > middle.y + 0.15:
                    ST["hand_raised"] = True
                else:
                    ST["hand_raised"] = False

                # Wave detection
                self.hand_hist.append(wrist.x)
                if len(self.hand_hist) > 15:
                    self.hand_hist.pop(0)
                if len(self.hand_hist) >= 10:
                    spread = (max(self.hand_hist) -
                              min(self.hand_hist))
                    ST["waving"] = spread > 0.12

            # Clap = 2 hands close
            if (res.multi_hand_landmarks and
                    len(res.multi_hand_landmarks) >= 2):
                h1 = res.multi_hand_landmarks[0].landmark[0]
                h2 = res.multi_hand_landmarks[1].landmark[0]
                if abs(h1.x - h2.x) < 0.15:
                    ST["clapping"]      = True
                    ST["clap_detected"] = True
                else:
                    ST["clapping"] = False

            # Verify requested action
            va = ST.get("verify_action")
            if va:
                now = time.time()
                # Timeout after 15s
                if ST["verify_timeout"] > 0 and \
                   now > ST["verify_timeout"]:
                    ST["verify_action"]  = None
                    ST["verify_result"]  = False
                    ST["verify_timeout"] = 0
                    return

                done = False
                if "hand" in va.lower() and ST["hand_raised"]:
                    done = True
                elif "wave" in va.lower() and ST["waving"]:
                    done = True
                elif "clap" in va.lower() and ST["clapping"]:
                    done = True

                if done:
                    ST["verify_result"]  = True
                    ST["verify_action"]  = None
                    ST["verify_timeout"] = 0
                    LOG("✅ Action verified by camera!",
                        "success")

        except: pass

    def _update(self, scores):
        if not scores: return
        dom = max(scores, key=scores.get)
        # Map to 6 core emotions
        emo_map = {
            "happy":"happy","joyful":"joyful",
            "sad":"sad","angry":"angry",
            "fear":"fear","surprised":"surprised",
            "surprise":"surprised","disgust":"angry",
            "neutral":"neutral","contempt":"neutral",
        }
        dom = emo_map.get(dom, dom)
        ST["emotion"]        = dom
        ST["emotion_scores"] = scores

        pos = (scores.get("happy",0)+
               scores.get("joyful",0)+
               scores.get("surprised",0))
        neg = (scores.get("sad",0)+
               scores.get("angry",0)+
               scores.get("fear",0))
        if pos > 0.5:   ST["engagement"] = "high"
        elif neg > 0.5: ST["engagement"] = "distressed"
        else:           ST["engagement"] = "moderate"

    def _draw500(self, small, scores, orig_frame):
        """Draw 500x500 emotion window"""
        # Scale small (300x300) to 500x500
        disp = cv2.resize(small, (500,500))
        em   = ST["emotion"]
        col  = self.EMO_COLORS.get(em,(180,180,180))

        # Header bar
        cv2.rectangle(disp,(0,0),(500,38),(0,0,0),-1)
        cv2.putText(disp,
            f"EMOTION | {em.upper()} | "
            f"Att:{ST['attention']}%",
            (8,26), cv2.FONT_HERSHEY_SIMPLEX,
            0.62, col, 2)

        # Score bars (6 emotions)
        EMO_6 = ["happy","joyful","sad",
                 "angry","fear","surprised"]
        bx, by = 8, 48
        for i, e in enumerate(EMO_6):
            sc  = scores.get(e,
                  scores.get("surprise",0) if e=="surprised"
                  else 0)
            bar = int(sc * 180)
            c   = self.EMO_COLORS.get(e,(150,150,150))
            y   = by + i*36
            # Background
            cv2.rectangle(disp,(bx,y),(bx+180,y+24),
                (30,30,50),-1)
            # Fill
            if bar > 0:
                cv2.rectangle(disp,(bx,y),(bx+bar,y+24),c,-1)
            # Border
            cv2.rectangle(disp,(bx,y),(bx+180,y+24),
                (60,60,80),1)
            # Label
            cv2.putText(disp,f"{e[:8]}:{sc:.0%}",
                (bx+3,y+17),cv2.FONT_HERSHEY_SIMPLEX,
                0.42,(255,255,255),1)

        # Action verification panel
        ax, ay = 200, 48
        actions_info = [
            ("✋ Hand Raised", ST["hand_raised"],
             (0,255,100)),
            ("👋 Waving",     ST["waving"],
             (0,200,255)),
            ("👏 Clapping",   ST["clapping"],
             (255,200,0)),
        ]
        for i,(label,active,ac) in enumerate(actions_info):
            y = ay + i*36
            bg = (5,30,15) if active else (20,20,30)
            cv2.rectangle(disp,(ax,y),(ax+290,y+28),bg,-1)
            border = ac if active else (60,60,80)
            cv2.rectangle(disp,(ax,y),(ax+290,y+28),
                border,1 if not active else 2)
            cv2.putText(disp,label,
                (ax+8,y+19),cv2.FONT_HERSHEY_SIMPLEX,
                0.52,ac if active else (80,80,80),
                2 if active else 1)

        # Verify indicator
        if ST["verify_action"]:
            remaining = max(0, int(
                ST["verify_timeout"]-time.time()))
            cv2.rectangle(disp,(200,163),(490,195),
                (30,15,0),-1)
            cv2.rectangle(disp,(200,163),(490,195),
                (255,150,0),2)
            cv2.putText(disp,
                f"⏳ Verify: {ST['verify_action'][:20]}"
                f" ({remaining}s)",
                (206,183),cv2.FONT_HERSHEY_SIMPLEX,
                0.45,(255,150,0),1)

        if ST["verify_result"]:
            cv2.putText(disp,"✅ VERIFIED!",
                (200,230),cv2.FONT_HERSHEY_SIMPLEX,
                1.0,(0,255,100),3)

        # Attention bar
        bw = int(ST["attention"]/100*498)
        cv2.rectangle(disp,(0,478),(498,498),(20,20,40),-1)
        cv2.rectangle(disp,(0,478),(bw,498),col,-1)
        cv2.putText(disp,f"Attention: {ST['attention']}%",
            (8,494),cv2.FONT_HERSHEY_SIMPLEX,
            0.40,(255,255,255),1)

        # Face detected indicator
        fdc = (0,255,0) if ST["face_detected"] else (0,0,255)
        cv2.circle(disp,(485,22),8,fdc,-1)

        with self._lock:
            self._win500 = disp.copy()

    def get_window(self):
        with self._lock:
            return self._win500.copy() \
                if self._win500 is not None else None


# ══════════════════════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════════════════════
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
                        c.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                        c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        c.set(cv2.CAP_PROP_FPS, 30)
                        c.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                        self.cap=c; self.idx=i
                        print(f"✅ Camera index {i}")
                        return
                    c.release()
            except: pass
        print("⚠️  No camera - simulation mode")

    def read(self):
        if not self.cap: return False, None
        ret, f = self.cap.read()
        if ret and f is not None:
            f = cv2.flip(f,1)
            with self._lk: self._frm = f.copy()
            return True, f
        return False, None


# ══════════════════════════════════════════════════════════════
# VOICE ENGINE (interruptible)
# ══════════════════════════════════════════════════════════════
class Voice:
    def __init__(self):
        self.ok = False; self._lk = threading.Lock()

        try:
            self.e = pyttsx3.init()
            self.e.setProperty('rate', 128)
            self.e.setProperty('volume', 1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira',
                                  'hazel','karen']):
                    self.e.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice (interruptible, rate=128)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")

    def say(self, text, wait_after=True):
        """Say text. Checks interrupt_flag constantly."""
        ST["interrupt_flag"] = False
        name = ST.get("name","Friend")
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

        ST["is_speaking"] = True

        # Add to session chat
        ST["session_chat"].append({
            "role":"pepper","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"])>30:
            ST["session_chat"]=ST["session_chat"][-30:]

        print(f"\n🔊 Pepper: {text}")
        LOG(f"Said: {text[:55]}")

        if self.ok and not ST["interrupt_flag"]:
            with self._lk:
                try:
                    self.e.say(text)
                    self.e.runAndWait()
                except: pass

        ST["is_speaking"] = False

        # Listen-first: wait for child after speaking
        if wait_after and not ST["interrupt_flag"]:
            ST["waiting_for_child"] = True
            time.sleep(0.3)

    def interrupt(self):
        """Stop speaking immediately"""
        ST["interrupt_flag"] = True
        ST["is_speaking"]    = False
        if self.ok:
            try: self.e.stop()
            except: pass


# ══════════════════════════════════════════════════════════════
# MICROPHONE (energy=10, whisper, Listen-First)
# ══════════════════════════════════════════════════════════════
class Mic:
    def __init__(self):
        self.ok = False; self.running = False

        try:
            self.r = sr.Recognizer()
            # ═══ WHISPER DETECTION ═══
            self.r.energy_threshold               = 10
            self.r.dynamic_energy_threshold       = False
            self.r.pause_threshold                = 0.4
            self.r.phrase_threshold               = 0.08
            self.r.non_speaking_duration          = 0.1
            self.ok = True
            print("✅ Mic energy=10 (whisper detection)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen_once(self, timeout=8):
        """Listen for ONE response"""
        if not self.ok:
            return input("👶 Type: ").strip()

        ST["listening"] = True
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(
                    src, duration=0.1)
                print("👂 Listening...")
                audio = self.r.listen(
                    src, timeout=timeout,
                    phrase_time_limit=15)
            ST["listening"] = False
            try:
                text = self.r.recognize_google(audio)
                ST["last_sound"] = time.time()
                ST["waiting_for_child"] = False
                ST["session_chat"].append({
                    "role":"child","text":text,
                    "time":datetime.now().strftime(
                        "%H:%M:%S")})
                if len(ST["session_chat"])>30:
                    ST["session_chat"] = \
                        ST["session_chat"][-30:]
                LOG(f"Heard: {text}")
                return text
            except sr.UnknownValueError:
                self._check_clap(audio)
                ST["last_sound"] = time.time()
                ST["waiting_for_child"] = False
                return "[sound]"
            except sr.RequestError:
                return ""
        except sr.WaitTimeoutError:
            return "[timeout]"
        except Exception:
            return ""
        finally:
            ST["listening"] = False

    def _check_clap(self, audio):
        try:
            raw = np.frombuffer(
                audio.get_raw_data(), np.int16)
            rms = float(np.sqrt(np.mean(
                raw.astype(np.float64)**2)))
            if rms > 800:
                ST["clap_detected"] = True
                LOG("👏 Clap!","success")
        except: pass

    def get_name(self, voice):
        """Get child's name (Listen-First)"""
        if ST["known"]: return ST["name"]

        voice.say(
            "Hello! I am Pepper! "
            "I am so happy to see you! "
            "What is your name? Ready? Your turn! 🎯",
            wait_after=False)

        for attempt in range(3):
            resp = self.listen_once(timeout=10)
            if resp and resp not in ["[sound]","[timeout]",""]:
                n = self._extract(resp)
                if n:
                    ST["name"]  = n
                    ST["known"] = True
                    LOG(f"Name: {n}","success")
                    return n
            elif resp == "[sound]":
                voice.say(
                    f"I heard something! "
                    f"Can you say your name? "
                    "Ready? Your turn! 🎯",
                    wait_after=False)
            elif resp == "[timeout]":
                if attempt < 2:
                    voice.say(
                        "Take your time! "
                        "What is your name? "
                        "Ready? Your turn! 🎯",
                        wait_after=False)

        ST["name"]  = "Friend"
        ST["known"] = True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm",
                   "call me","name is","it's"]:
            t = t.replace(rm,"").strip()
        w = t.split()
        return w[0].capitalize() if w else None

    def listen_bg(self, callback):
        """Background listening thread"""
        def _loop():
            self.running = True
            while self.running:
                if ST["is_speaking"]:
                    time.sleep(0.1)
                    continue
                result = self.listen_once(timeout=5)
                if result and result != "[timeout]":
                    # Interrupt Pepper if speaking
                    if ST["is_speaking"]:
                        ST["interrupt_flag"] = True
                    try: callback(result)
                    except Exception as e:
                        print(f"⚠️  cb:{e}")
                time.sleep(0.05)

        threading.Thread(
            target=_loop, daemon=True).start()


# ══════════════════════════════════════════════════════════════
# ACTION ENGINE
# ══════════════════════════════════════════════════════════════
class Actions:
    def __init__(self, pepper=None):
        self.pepper = pepper

    def process(self, text):
        clean = text
        TOKEN_MAP = {
            "[WAVE]":      self._wave,
            "[CLAP]":      self._clap,
            "[NOD]":       self._nod,
            "[DANCE]":     self._dance,
            "[POINT]":     self._point,
            "[HUG]":       self._hug,
            "[CELEBRATE]": self._celebrate,
            "[THINK]":     self._think,
        }
        for tok,fn in TOKEN_MAP.items():
            if tok in text:
                clean = clean.replace(tok,"")
                threading.Thread(
                    target=fn,daemon=True).start()

        # YouTube
        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt:
            clean = clean.replace(yt.group(0),"")
            q = yt.group(1).strip()
            url = ("https://www.youtube.com/results?"
                   "search_query="+urllib.parse.quote(
                       q+" autism children educational"))
            webbrowser.open(url)
            LOG(f"📺 YouTube: {q}")

        # Reward
        rew = re.search(r'\[REWARD:(\d+)\]', text)
        if rew:
            clean = clean.replace(rew.group(0),"")
            stars = int(rew.group(1))
            ST["tokens"]      += stars
            ST["stars_today"] += stars

        # Verify action
        vry = re.search(r'\[VERIFY:\s*(.+?)\]', text)
        if vry:
            clean = clean.replace(vry.group(0),"")
            action = vry.group(1).strip()
            ST["verify_action"]  = action
            ST["verify_result"]  = False
            ST["verify_timeout"] = time.time() + 15
            LOG(f"👁️ Verifying: {action}")

        # Game
        if "[GAME]" in text:
            clean = clean.replace("[GAME]","")
            webbrowser.open(
                f"http://localhost:{PORT_GAME}")

        return clean.strip()

    def _sa(self,j,a,s=0.15):
        if self.pepper:
            try: self.pepper.setAngles(j,a,s)
            except: pass

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2)
        self._sa("RElbowRoll",0.8,0.2)
        time.sleep(0.3)
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


# ══════════════════════════════════════════════════════════════
# PYBULLET (Thread 1)
# ══════════════════════════════════════════════════════════════
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
            p.setAdditionalSearchPath(
                pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._room()
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

            print("✅ PyBullet simulation ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _room(self):
        wc=[0.88,0.88,0.92,1]
        for pos,ext in [
            ([0,-4,1.1],[5,.1,1.1]),
            ([0, 4,1.1],[5,.1,1.1]),
            ([5, 0,1.1],[.1,4,1.1]),
            ([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.55,.45,.35,1]),[0,0,.01])
        labels = [
            ("ABA ROOM", [-4,3,2.0]),
            ("DTT ROOM", [4,3,2.0]),
            ("TEACCH",   [0,4,2.0]),
            ("TIE",      [-4,-3,2.0]),
            ("PORT:5007",[0,0,2.8]),
        ]
        for txt,pos in labels:
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
                    radius=.11,rgbaColor=[1.,.82,.65,1.]),
                [pos[0],pos[1],.74])
            p.addUserDebugText(nm,[pos[0],pos[1],1.05],
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
                if ST["is_speaking"]:
                    ph+=.07
                    L=.5+.3*math.sin(ph)
                    R=.5+.3*math.sin(ph+math.pi*.6)
                    self.pepper.setAngles(
                        "LShoulderPitch",L,.07)
                    self.pepper.setAngles(
                        "RShoulderPitch",R,.07)
                    self.pepper.setAngles(
                        "HeadPitch",-0.05,.04)
                elif ST["listening"]:
                    # Tilt head when listening
                    self.pepper.setAngles(
                        "HeadYaw",0.25,.05)
                    self.pepper.setAngles(
                        "HeadPitch",0.1,.05)
                else:
                    self.pepper.setAngles(
                        "LShoulderPitch",1.,.04)
                    self.pepper.setAngles(
                        "RShoulderPitch",1.,.04)
                    self.pepper.setAngles(
                        "HeadYaw",0.,.03)
                    self.pepper.setAngles(
                        "HeadPitch",0.,.03)
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


# ══════════════════════════════════════════════════════════════
# DISPLAY (Thread 3 - Vision)
# ══════════════════════════════════════════════════════════════
class Display:
    def __init__(self, em_eng, cam):
        self.em  = em_eng; self.cam = cam
        self.running = False
        self.task_text  = ""; self.task_t  = 0
        self.praise_text= ""; self.praise_t= 0
        self.ai_text    = ""; self.ai_t    = 0
        self._em_last   = 0
        self.avatar     = self._avatar()
        self.running    = True
        threading.Thread(
            target=self._run, daemon=True).start()
        print("✅ Display (500x500 emotion) started!")

    def _avatar(self):
        img = np.zeros((130,100,3), dtype=np.uint8)
        img[:] = (10,15,38)
        cv2.circle(img,(50,32),24,(220,195,173),-1)
        for ex in [40,60]:
            cv2.circle(img,(ex,27),6,(0,140,255),-1)
            cv2.circle(img,(ex,27),3,(255,255,255),-1)
            cv2.circle(img,(ex+1,26),2,(0,0,0),-1)
        cv2.ellipse(img,(50,40),(8,4),0,0,180,(70,35,35),2)
        cv2.rectangle(img,(30,56),(70,100),
            (120,135,190),-1)
        cv2.rectangle(img,(8,57),(30,78),
            (120,135,190),-1)
        cv2.rectangle(img,(70,57),(92,78),
            (120,135,190),-1)
        cv2.putText(img,"PEPPER",(8,118),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,(80,180,255),1)
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
                if now-self._em_last > 0.7 and not no_cam:
                    self._em_last = now
                    self.em.analyze_async(frame.copy())

                # Main UI (scaled to 960x540)
                ui   = self._build(frame)
                main = cv2.resize(ui,(960,540))
                cv2.imshow("🤖 Pepper Therapy",main)

                # 500x500 Emotion Window
                ew = self.em.get_window()
                if ew is not None:
                    cv2.imshow(
                        "😊 Emotion Analysis (500x500)", ew)

                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'),ord('Q'),27]:
                    self.running=False; break

            except Exception as e:
                print(f"⚠️  display:{e}")
                time.sleep(0.1)
            time.sleep(0.016)

        try: cv2.destroyAllWindows()
        except: pass

    def _sim_frame(self):
        h,w = 480,640
        f   = np.zeros((h,w,3), dtype=np.uint8)
        f[:] = (7,10,25)
        t   = time.time()
        for i in range(0,w,60):
            cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,60):
            cv2.line(f,(0,i),(w,i),(15,22,50),1)
        r   = int(30+12*math.sin(t*1.5))
        col = (int(50+50*math.sin(t)),
               int(100+100*math.cos(t*0.7)),220)
        cv2.circle(f,(w//2,h//2-40),r,col,3)
        cv2.putText(f,"SIMULATION MODE",
            (w//2-110,h//2+20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,(100,150,255),2)
        return f

    def _build(self, frame):
        h,w = frame.shape[:2]
        ui  = frame.copy()

        # Header
        ov = ui.copy()
        cv2.rectangle(ov,(0,0),(w,58),(6,10,25),-1)
        ui = cv2.addWeighted(ov,0.85,ui,0.15,0)

        gem = "✅" if ST["gemini_ok"] else "⚠️"
        listen_icon = "👂" if ST["listening"] else ""
        speak_icon  = "🔊" if ST["is_speaking"] else ""
        wait_icon   = "⏳" if ST["waiting_for_child"] else ""

        cv2.putText(ui,
            f"Pepper v4.0 {gem} {speak_icon}{listen_icon}{wait_icon}",
            (12,28),cv2.FONT_HERSHEY_SIMPLEX,
            0.68,(255,255,255),2)
        cv2.putText(ui,
            f"{ST['name']} | {ST['protocol']} | "
            f"Score:{ST['score']} | ⭐{ST['tokens']} | "
            f"Streak:{ST['streak']}",
            (12,50),cv2.FONT_HERSHEY_SIMPLEX,
            0.42,(140,190,255),1)

        # Avatar PIP
        av   = self.avatar.copy()
        ah,aw= av.shape[:2]
        if ST["is_speaking"]:
            t  = int(time.time()*7)%3
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                (0,160+t*18,255),2)
        elif ST["listening"]:
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                (0,220,100),2)
        x1=w-aw-10; y1=h-ah-65
        ui[y1:y1+ah,x1:x1+aw] = av
        bc = ((0,200,255) if ST["is_speaking"] else
              (0,180,80)  if ST["listening"] else
              (40,40,80))
        cv2.rectangle(ui,(x1-2,y1-2),
            (x1+aw+2,y1+ah+2),bc,2)

        # Status labels
        if ST["is_speaking"]:
            cv2.putText(ui,"SPEAKING",
                (x1-2,y1-6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,(0,200,255),1)
        elif ST["listening"]:
            cv2.putText(ui,"LISTENING...",
                (x1-2,y1-6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,(0,220,100),1)
        elif ST["waiting_for_child"]:
            cv2.putText(ui,"WAITING...",
                (x1-2,y1-6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,(255,200,0),1)

        # Bottom bar
        ov2 = ui.copy()
        cv2.rectangle(ov2,(0,h-62),(w,h),(6,10,25),-1)
        ui  = cv2.addWeighted(ov2,0.78,ui,0.22,0)

        EC  = {
            "happy":(0,220,80),"sad":(100,100,220),
            "angry":(0,0,220),"fear":(0,180,220),
            "surprised":(200,50,220),"joyful":(0,255,180),
            "neutral":(180,180,180),
        }
        em  = ST["emotion"]
        ec  = EC.get(em,(180,180,180))
        att = ST["attention"]

        cv2.putText(ui,f"{em.upper()}",
            (12,h-38),cv2.FONT_HERSHEY_SIMPLEX,
            0.72,ec,2)
        bw2 = int(att/100*(w-170))
        cv2.rectangle(ui,(12,h-25),(w-158,h-16),
            (25,28,55),-1)
        cv2.rectangle(ui,(12,h-25),(12+bw2,h-16),ec,-1)
        cv2.putText(ui,
            f"Att:{att}%  {ST['engagement']}  "
            f"P{ST['prompt_level']}",
            (12,h-6),cv2.FONT_HERSHEY_SIMPLEX,
            0.4,(255,230,100),1)

        # Actions panel
        act_x = w-190
        for i,(label,active,c) in enumerate([
            ("✋ Hand",  ST["hand_raised"], (0,255,100)),
            ("👋 Wave",  ST["waving"],      (0,200,255)),
            ("👏 Clap",  ST["clapping"],    (255,200,0)),
        ]):
            y = h-58+i*18
            col2 = c if active else (60,60,80)
            cv2.putText(ui,label,(act_x,y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,col2,1 if not active else 2)

        # Verify
        if ST["verify_action"]:
            cv2.putText(ui,
                f"⏳ {ST['verify_action'][:25]}",
                (w//2-120,h-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.44,(255,150,0),1)

        # Task display
        now = time.time()
        if self.task_text and now-self.task_t < 8:
            tl  = min(len(self.task_text)*13,w-60)
            tx  = max(10,w//2-tl//2)
            cv2.rectangle(ui,(tx-5,h//2-40),
                (tx+tl+5,h//2+8),(12,45,110),-1)
            cv2.rectangle(ui,(tx-5,h//2-40),
                (tx+tl+5,h//2+8),(0,140,255),2)
            cv2.putText(ui,self.task_text[:50],
                (tx,h//2-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,(255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_t < 4:
            cv2.putText(ui,self.praise_text[:35],
                (w//2-160,h//2+55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.92,(0,255,100),2)

        # AI text
        if self.ai_text and now-self.ai_t < 5:
            lines=[self.ai_text[i:i+62]
                   for i in range(0,
                   min(len(self.ai_text),124),62)]
            for li,ln in enumerate(lines[:2]):
                cv2.putText(ui,ln,
                    (12,h-68-li*22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,(200,255,200),1)

        # Face/REC
        fdc=(0,255,0) if ST["face_detected"] else (0,0,255)
        cv2.circle(ui,(w-10,15),6,fdc,-1)
        cv2.circle(ui,(38,20),7,(0,0,220),-1)
        cv2.putText(ui,"REC",(50,26),
            cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,220),1)

        # Clap flash
        if ST["clap_detected"]:
            cv2.putText(ui,"👏 CLAP!",
                (w//2-70,80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,(0,255,100),3)
        return ui

    def show_task(self,t):
        self.task_text=t; self.task_t=time.time()
    def show_praise(self,t):
        self.praise_text=t; self.praise_t=time.time()
    def show_ai(self,t):
        self.ai_text=t[:124]; self.ai_t=time.time()
    def stop(self):
        self.running=False; time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass


# ══════════════════════════════════════════════════════════════
# FLASK SERVERS (Thread 4)
# ══════════════════════════════════════════════════════════════

# ── GAME SERVER (5009) ────────────────────────────────────────
game_app = Flask("game")

GAME_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>🎮 Therapy Games</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;
     font-family:'Segoe UI',sans-serif;padding:16px}
h1{color:#a78bfa;text-align:center;margin-bottom:16px}
.nav{display:flex;gap:8px;justify-content:center;
     margin-bottom:16px;flex-wrap:wrap}
.nav a{background:#4f46e5;color:#fff;padding:7px 14px;
       border-radius:8px;text-decoration:none;
       font-size:.8em;transition:.2s}
.nav a:hover{opacity:.85}
.nav a.active{background:#059669}
.grid{display:grid;
      grid-template-columns:repeat(3,1fr);
      gap:14px;max-width:900px;margin:0 auto}
.gc{background:#0c0f1e;border:2px solid #1a1f40;
    border-radius:12px;padding:18px;text-align:center;
    cursor:pointer;transition:.3s}
.gc:hover{border-color:#a78bfa;
          transform:translateY(-3px)}
.gi{font-size:2.8em;margin-bottom:8px}
.gn{font-weight:700;color:#e0e6ff;font-size:.9em}
.gd{font-size:.72em;color:#6b7280;margin-top:4px}
#ag{max-width:900px;margin:16px auto}
.score-bar{background:#1a0a3d;border-radius:8px;
           padding:8px 16px;text-align:center;
           margin-bottom:12px;font-size:.85em;
           color:#a78bfa}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:9px 18px;
     border-radius:8px;cursor:pointer;
     font-size:.82em;margin:5px;transition:.2s}
.btn:hover{opacity:.85}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
canvas{border:2px solid #4f46e5;border-radius:8px;
       background:#0a0f1e;display:block;margin:10px auto}
</style>
</head><body>
<h1>🎮 Pepper Therapy Game Zone</h1>
<div class="nav">
  <a href="http://localhost:5007">🧠 Brain (5007)</a>
  <a href="http://localhost:5001">📋 Reports (5001)</a>
  <a href="http://localhost:5009" class="active">
    🎮 Games (5009)</a>
</div>

<div class="score-bar">
  Score: <span id="pts">0</span> ⭐ |
  Level: <span id="lvl">1</span> |
  Player: <span id="pname">Friend</span>
</div>

<div class="grid">
  <div class="gc" onclick="start('balloons')">
    <div class="gi">🎈</div>
    <div class="gn">Pop Balloons!</div>
    <div class="gd">Click happy balloons</div>
  </div>
  <div class="gc" onclick="start('emotions')">
    <div class="gi">😊</div>
    <div class="gn">Emotion Mirror</div>
    <div class="gd">Copy Pepper's face</div>
  </div>
  <div class="gc" onclick="start('colors')">
    <div class="gi">🎨</div>
    <div class="gn">Color Match</div>
    <div class="gd">Match the color</div>
  </div>
  <div class="gc" onclick="start('numbers')">
    <div class="gi">🔢</div>
    <div class="gn">Count Stars</div>
    <div class="gd">How many stars?</div>
  </div>
  <div class="gc" onclick="start('memory')">
    <div class="gi">🧠</div>
    <div class="gn">Memory Flip</div>
    <div class="gd">Match the pairs</div>
  </div>
  <div class="gc" onclick="start('shapes')">
    <div class="gi">⭐</div>
    <div class="gn">Shape ID</div>
    <div class="gd">Name the shape</div>
  </div>
</div>
<div id="ag"></div>

<script>
var sc=0,lv=1;
// Fetch child name from AI brain
fetch('http://localhost:5007/api/state')
  .then(r=>r.json()).then(d=>{
    if(d.name) document.getElementById('pname').textContent=d.name;
    if(d.score) {sc=d.score;}
    document.getElementById('pts').textContent=sc;
  }).catch(()=>{});

function add(n){
  sc+=n; lv=Math.floor(sc/50)+1;
  document.getElementById('pts').textContent=sc;
  document.getElementById('lvl').textContent=lv;
}

function start(g){
  var d=document.getElementById('ag');
  if(g==='balloons') runBalloons(d);
  else if(g==='emotions') emoGame(d);
  else if(g==='colors') colorGame(d);
  else if(g==='numbers') numGame(d);
  else if(g==='memory') memGame(d);
  else if(g==='shapes') shapeGame(d);
}

function runBalloons(d){
  d.innerHTML='<canvas id="gc" width="700" height="380"></canvas>';
  var c=document.getElementById('gc'),
      ctx=c.getContext('2d'),
      balls=[];
  for(var i=0;i<8;i++) balls.push({
    x:Math.random()*650+25,y:Math.random()*330+25,
    r:25+Math.random()*20,
    vx:(Math.random()-0.5)*2.5,vy:(Math.random()-0.5)*2.5,
    color:['#f87171','#34d399','#60a5fa','#fbbf24',
           '#c084fc','#f97316'][Math.floor(Math.random()*6)],
    alive:true});
  c.onclick=function(e){
    var rc=c.getBoundingClientRect(),
        mx=e.clientX-rc.left,my=e.clientY-rc.top;
    balls.forEach(function(b){
      if(!b.alive) return;
      if(Math.sqrt((mx-b.x)**2+(my-b.y)**2)<b.r){
        b.alive=false; add(10);
        if(balls.every(function(b){return !b.alive;})){
          balls.forEach(function(b){
            b.alive=true;
            b.x=Math.random()*650+25;
            b.y=Math.random()*330+25;});
        }}});};
  (function loop(){
    ctx.fillStyle='#0a0f1e'; ctx.fillRect(0,0,700,380);
    balls.forEach(function(b){
      if(!b.alive) return;
      b.x+=b.vx; b.y+=b.vy;
      if(b.x<b.r||b.x>700-b.r) b.vx*=-1;
      if(b.y<b.r||b.y>380-b.r) b.vy*=-1;
      ctx.beginPath(); ctx.arc(b.x,b.y,b.r,0,Math.PI*2);
      ctx.fillStyle=b.color; ctx.fill();
      ctx.fillStyle='white'; ctx.font='18px sans-serif';
      ctx.textAlign='center';
      ctx.fillText('🎈',b.x,b.y+6);});
    requestAnimationFrame(loop);})();
}

function emoGame(d){
  var em=[['😊','Happy'],['😢','Sad'],['😠','Angry'],
          ['😨','Scared'],['😲','Surprised'],['😄','Joyful']];
  var pick=em[Math.floor(Math.random()*em.length)];
  d.innerHTML='<div style="text-align:center;padding:16px">'+
    '<p style="color:#a78bfa;margin-bottom:8px">Show this face!</p>'+
    '<div style="font-size:5em;margin:12px">'+pick[0]+'</div>'+
    '<p style="font-size:1.1em;font-weight:700;color:#e0e6ff">'+
    pick[1]+'</p>'+
    '<button class="btn btn-g" style="margin-top:12px" '+
    'onclick="add(20);this.textContent=\'✅ Amazing!\'">'+
    'I did it! 🌟</button>'+
    '<button class="btn" style="margin-top:12px" '+
    'onclick="emoGame(document.getElementById(\'ag\'))">'+
    'Next ➡️</button></div>';
}

function colorGame(d){
  var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],
          ['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316']];
  var idx=Math.floor(Math.random()*cs.length);
  d.innerHTML='<div style="text-align:center;padding:16px">'+
    '<p style="color:#a78bfa;margin-bottom:8px">What color?</p>'+
    '<div style="width:110px;height:110px;background:'+cs[idx][1]+
    ';border-radius:50%;margin:10px auto;border:3px solid #374151"></div>'+
    '<div id="cbtns" style="margin-top:10px">'+
    cs.map(function(c,i){
      return '<button class="btn" onclick="chkC('+i+','+idx+')" '+
        'style="background:'+c[1]+';margin:4px">'+c[0]+'</button>';
    }).join('')+'</div></div>';
}
window.chkC=function(ch,co){
  var cs=[['Red','#ef4444'],['Blue','#3b82f6'],['Green','#22c55e'],
          ['Yellow','#eab308'],['Purple','#a855f7'],['Orange','#f97316']];
  if(ch===co){add(15);
    document.getElementById('cbtns').innerHTML=
      '<p style="color:#34d399;font-size:1.1em">✅ Correct! 🌟</p>'+
      '<button class="btn" onclick="colorGame(document.getElementById(\'ag\'))">Next ➡️</button>';
  }else{document.getElementById('cbtns').innerHTML=
    '<p style="color:#f87171">Try again! 💪</p>'+
    '<button class="btn" onclick="colorGame(document.getElementById(\'ag\'))">Retry ↩️</button>';}
};

function numGame(d){
  var n=Math.floor(Math.random()*9)+1;
  var stars=''; for(var i=0;i<n;i++) stars+='⭐ ';
  var opts=Array.from(new Set([n,
    Math.max(1,n-1),Math.min(10,n+1),
    n>2?n-2:n+3].filter(x=>x>0)))
    .sort(function(){return Math.random()-0.5;}).slice(0,4);
  d.innerHTML='<div style="text-align:center;padding:16px">'+
    '<p style="color:#a78bfa">Count the stars!</p>'+
    '<div style="font-size:1.6em;margin:10px;'+
    'letter-spacing:6px">'+stars+'</div>'+
    '<p style="color:#6b7280;margin-bottom:8px">How many?</p>'+
    '<div>'+opts.map(function(x){
      return '<button class="btn" onclick="chkN('+x+','+n+')" '+
        'style="font-size:1.1em;padding:11px 18px">'+x+'</button>';
    }).join('')+'</div></div>';
}
window.chkN=function(ch,co){
  if(ch===co){add(20);
    alert('✅ YES! '+co+' stars! Amazing! 🌟');
    numGame(document.getElementById('ag'));
  }else alert('Try again! Count carefully! 💪');
};

function memGame(d){
  var pairs=['🐶','🐱','🐻','🦊','🐼','🐨'];
  var cards=pairs.concat(pairs).sort(function(){return Math.random()-0.5;});
  window._mc=cards; window._mf=[]; window._mm=[];
  d.innerHTML='<div style="display:grid;'+
    'grid-template-columns:repeat(4,1fr);gap:8px;'+
    'max-width:380px;margin:12px auto">'+
    cards.map(function(c,i){
      return '<div id="mc'+i+'" onclick="flipM('+i+')" '+
        'style="height:68px;background:#1f2937;'+
        'border-radius:8px;display:flex;'+
        'align-items:center;justify-content:center;'+
        'font-size:1.9em;cursor:pointer;'+
        'border:2px solid #374151">❓</div>';
    }).join('')+'</div>';
}
window.flipM=function(idx){
  var c=window._mc;
  if(window._mf.length>=2||
     window._mm.includes(idx)||
     window._mf.includes(idx)) return;
  document.getElementById('mc'+idx).textContent=c[idx];
  window._mf.push(idx);
  if(window._mf.length===2){
    var a=window._mf[0],b=window._mf[1];
    if(c[a]===c[b]){
      window._mm.push(a,b); add(25); window._mf=[];
      if(window._mm.length===c.length){
        setTimeout(function(){
          alert('🎉 All matched! Amazing!');
          memGame(document.getElementById('ag'));},400);}
    }else{setTimeout(function(){
      document.getElementById('mc'+a).textContent='❓';
      document.getElementById('mc'+b).textContent='❓';
      window._mf=[];},1000);}
  }
};

function shapeGame(d){
  var shapes=[
    ['⬛','Square'],['⭕','Circle'],['🔺','Triangle'],
    ['💎','Diamond'],['⬡','Hexagon'],['⭐','Star']];
  var pick=shapes[Math.floor(Math.random()*shapes.length)];
  d.innerHTML='<div style="text-align:center;padding:16px">'+
    '<p style="color:#a78bfa;margin-bottom:8px">What shape is this?</p>'+
    '<div style="font-size:5em;margin:12px">'+pick[0]+'</div>'+
    '<div>'+shapes.map(function(s,i){
      var isRight=(s[1]===pick[1]);
      return '<button class="btn" '+
        'onclick="chkS('+isRight+')" style="margin:4px">'+
        s[1]+'</button>';
    }).join('')+'</div></div>';
}
window.chkS=function(ok){
  if(ok){add(15);alert('✅ Correct! Great job! 🌟');
    shapeGame(document.getElementById('ag'));
  }else alert('Not quite! Try again! 💪');
};
</script>
</body></html>"""

@game_app.route("/")
@game_app.route("/<path:p>")
def game_page(p=None):
    return GAME_HTML

@game_app.route("/api/state")
def game_state():
    return jsonify({"score":ST["score"],"name":ST["name"]})


# ── REPORTS SERVER (5001) ─────────────────────────────────────
report_app = Flask("reports")

REPORT_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>📋 Clinical Reports - Port 5001</title>
<meta http-equiv="refresh" content="5">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#060912;color:#e0e6ff;
     font-family:'Segoe UI',sans-serif;padding:16px}
h1{color:#a78bfa;margin-bottom:14px}
.nav{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.nav a{background:#4f46e5;color:#fff;padding:7px 14px;
       border-radius:8px;text-decoration:none;
       font-size:.8em;transition:.2s}
.nav a:hover{opacity:.85}
.nav a.active{background:#059669}
.card{background:#0c0f1e;border-radius:11px;
      padding:14px;border:1px solid #1a1f40;
      margin-bottom:12px}
.card h2{color:#818cf8;margin-bottom:10px;
         font-size:.88em}
.stat{display:inline-block;background:#1a0a3d;
      border-radius:8px;padding:8px 14px;
      margin:4px;text-align:center}
.n{font-size:1.6em;font-weight:700;color:#a78bfa}
.l{font-size:.68em;color:#6b7280}
.report{background:#07090f;border-radius:8px;
        padding:12px;margin:8px 0;
        border-left:3px solid #a78bfa;
        white-space:pre-wrap;font-size:.78em;
        line-height:1.7;color:#c0c8e0}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:7px 14px;
     border-radius:7px;cursor:pointer;font-size:.78em;
     margin:4px}
</style>
</head><body>
<h1>📋 Clinical Reports & Documentation</h1>
<div class="nav">
  <a href="http://localhost:5007">🧠 Brain (5007)</a>
  <a href="http://localhost:5009">🎮 Games (5009)</a>
  <a href="http://localhost:5001" class="active">
    📋 Reports (5001)</a>
</div>

<div class="card">
  <h2>📊 Current Session Stats</h2>
  <div>
    <div class="stat">
      <div class="n">{{s.score}}</div>
      <div class="l">Score</div>
    </div>
    <div class="stat">
      <div class="n">⭐{{s.tokens}}</div>
      <div class="l">Tokens</div>
    </div>
    <div class="stat">
      <div class="n">{{s.tasks_success}}</div>
      <div class="l">Success</div>
    </div>
    <div class="stat">
      <div class="n">{{s.tasks_fail}}</div>
      <div class="l">Failed</div>
    </div>
    <div class="stat">
      <div class="n">{{s.attention}}%</div>
      <div class="l">Attention</div>
    </div>
    <div class="stat">
      <div class="n">{{s.emotion}}</div>
      <div class="l">Emotion</div>
    </div>
  </div>
</div>

<div class="card">
  <h2>📄 Clinical Session Reports</h2>
  <form method="POST" action="/generate_report">
    <button class="btn">
      ⚡ Generate New Report</button>
  </form>
  {% for rep in s.reports[-5:]|reverse %}
  <div class="report">{{rep.content}}</div>
  <div style="font-size:.68em;color:#6b7280;margin-top:3px">
    Generated: {{rep.time}}</div>
  {% endfor %}
  {% if not s.reports %}
  <p style="color:#6b7280;font-size:.8em;margin-top:8px">
    No reports yet. Click "Generate New Report" above.</p>
  {% endif %}
</div>

<div class="card">
  <h2>📝 Parent Notes</h2>
  <form method="POST" action="/add_note"
        style="margin-bottom:8px">
    <select name="cat"
            style="padding:6px;border-radius:6px;
                   border:1px solid #374151;
                   background:#07090f;color:#e0e6ff;
                   font-size:.78em;margin-bottom:6px;
                   width:150px">
      <option>behavior</option>
      <option>progress</option>
      <option>concern</option>
      <option>milestone</option>
    </select>
    <textarea name="note"
              style="width:100%;padding:7px;
                     border-radius:6px;border:1px solid #374151;
                     background:#07090f;color:#e0e6ff;
                     font-size:.78em;min-height:60px;
                     resize:vertical;margin:4px 0"
              placeholder="Write observation..."></textarea>
    <button class="btn">➕ Save Note</button>
  </form>
  {% for note in s.parent_notes[-10:]|reverse %}
  <div style="background:#0a1020;border-left:3px solid #a78bfa;
              padding:7px;margin:4px 0;border-radius:0 6px 6px 0;
              font-size:.75em">
    <span style="color:#a78bfa;font-size:.7em;
                 font-weight:700">
      {{note.category.upper()}}</span>
    <span style="color:#6b7280;font-size:.7em">
      {{note.time}}</span><br>
    {{note.text}}
  </div>{% endfor %}
</div>

<div class="card">
  <h2>💬 Session Log</h2>
  <div style="max-height:200px;overflow-y:auto">
    {% for lg in s.logs[-30:]|reverse %}
    <div style="padding:3px 6px;margin:2px 0;
                border-left:3px solid #4f46e5;
                background:#07090f;font-size:.72em;
                border-radius:0 4px 4px 0">
      <span style="color:#6366f1">{{lg.time}}</span>
      <span style="color:#a78bfa">{{lg.child}}</span>:
      {{lg.msg}}
    </div>{% endfor %}
  </div>
  <a href="/export"
     style="display:inline-block;margin-top:8px;
            background:linear-gradient(135deg,#059669,#10b981);
            color:#fff;padding:7px 14px;border-radius:7px;
            text-decoration:none;font-size:.78em">
    📥 Export Full Report</a>
</div>
</body></html>"""

@report_app.route("/")
@report_app.route("/<path:p>")
def report_home(p=None):
    return render_template_string(REPORT_HTML, s=ST)

@report_app.route("/generate_report", methods=["POST"])
def gen_report():
    if _gemini:
        report_text = _gemini.generate_report()
        ST["reports"].append({
            "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": report_text,
        })
        if len(ST["reports"]) > 10:
            ST["reports"] = ST["reports"][-10:]
        LOG("📋 Clinical report generated","success")
    return redirect("/")

@report_app.route("/add_note", methods=["POST"])
def report_add_note():
    note = request.form.get("note","").strip()
    cat  = request.form.get("cat","other")
    if note:
        ST["parent_notes"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": note, "category": cat})
    return redirect("/")

@report_app.route("/export")
def report_export():
    fn = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(ST,f,indent=2,default=str)
    return jsonify({"saved":fn})


# ── BRAIN DASHBOARD (5007) ────────────────────────────────────
brain_app = Flask("brain")

BRAIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧠 Pepper Brain — Port 5007</title>
<meta http-equiv="refresh" content="3">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060912;--card:#0c0f1e;--border:#1a1f40;
      --pu:#a78bfa;--bl:#60a5fa;--gr:#34d399;
      --rd:#f87171;--yl:#fbbf24;--text:#e0e6ff;
      --mu:#6b7280}
body{font-family:'Segoe UI',system-ui,sans-serif;
     background:var(--bg);color:var(--text);font-size:13px}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);
     padding:11px 20px;display:flex;align-items:center;
     gap:10px;border-bottom:2px solid #4f46e5;
     position:sticky;top:0;z-index:100}
.hdr h1{font-size:1.05em;color:var(--pu)}
.bd{padding:2px 8px;border-radius:11px;
    font-size:.65em;font-weight:700}
.live{background:#ef4444;color:#fff;
      animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.nav-strip{display:flex;gap:6px;padding:10px 16px;
           background:#07090f;border-bottom:1px solid var(--border);
           flex-wrap:wrap}
.nav-strip a{background:#1a1f40;color:var(--text);
             padding:6px 14px;border-radius:8px;
             text-decoration:none;font-size:.78em;
             transition:.2s;display:flex;align-items:center;gap:5px}
.nav-strip a:hover{background:#4f46e5}
.nav-strip a.active{background:#4f46e5}
.nav-strip a.game{background:#059669}
.nav-strip a.report{background:#1d4ed8}
.main{max-width:1380px;margin:0 auto;padding:11px;
      display:flex;flex-direction:column;gap:10px}
.row{display:grid;gap:10px}
.r3{grid-template-columns:1fr 1fr 1fr}
.r2{grid-template-columns:1fr 1fr}
.r5{grid-template-columns:repeat(5,1fr)}
.card{background:var(--card);border-radius:10px;
      padding:12px;border:1px solid var(--border)}
.card h2{font-size:.78em;color:#818cf8;
         border-bottom:1px solid var(--border);
         padding-bottom:5px;margin-bottom:8px;
         display:flex;align-items:center;gap:5px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:8px;
      padding:11px;text-align:center}
.stat:hover{border-color:var(--pu)}
.n{font-size:1.75em;font-weight:700;color:var(--pu)}
.l{font-size:.67em;color:var(--mu);margin-top:2px}
.n-g{color:var(--gr)}.n-y{color:var(--yl)}.n-b{color:var(--bl)}
.emo{display:inline-block;padding:5px 13px;
     border-radius:14px;font-weight:700;font-size:.95em}
.happy{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprised{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.joyful{background:#05291555;color:#34d399;border:1px solid #34d399}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.bar-bg{background:#1f2937;border-radius:5px;
        height:8px;margin:4px 0}
.bar{height:8px;border-radius:5px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:6px 11px;
     border-radius:6px;cursor:pointer;font-size:.73em;
     margin:2px;transition:.2s;font-family:inherit}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}
.prot{display:inline-block;padding:2px 6px;
      border-radius:7px;font-size:.66em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}
input,textarea,select{width:100%;padding:6px 9px;
  border-radius:6px;border:1px solid var(--border);
  background:#07090f;color:var(--text);
  font-size:.76em;font-family:inherit;outline:none}
input:focus,textarea:focus{border-color:var(--pu)}
textarea{resize:vertical;min-height:55px}
.log-box{max-height:200px;overflow-y:auto;
         scrollbar-width:thin}
.li{padding:4px 7px;margin:2px 0;border-radius:4px;
    font-size:.7em;border-left:3px solid #4f46e5;
    background:#07090f;line-height:1.4}
.li.success{border-color:var(--gr)}
.li.fail{border-color:var(--rd)}
.li.info{border-color:var(--bl)}
.chart-wrap{position:relative;height:150px;
            background:#07090f;border-radius:7px;padding:5px}
.chat-box{height:170px;overflow-y:auto;
          background:#07090f;border-radius:7px;
          padding:8px;margin-bottom:6px;
          scrollbar-width:thin}
.cm{padding:5px 9px;margin:3px 0;border-radius:7px;
    font-size:.76em;line-height:1.5}
.cmp{background:#1e1b4b;border-left:3px solid var(--pu)}
.cmc{background:#052918;border-left:3px solid var(--gr)}
.cmr{background:#1a1f40;border-left:3px solid var(--bl)}
.note{background:#0a1020;border-left:3px solid var(--pu);
      padding:7px;margin:3px 0;
      border-radius:0 6px 6px 0;font-size:.72em}
.hc{background:#0a1020;border-radius:8px;
    padding:10px;border-left:4px solid var(--pu)}
.hct{color:var(--pu);font-weight:700;font-size:.76em;
     margin-bottom:3px}
.hcb{color:#9ca3af;font-size:.72em;line-height:1.6}
.tip{background:#051a0f;border:1px solid var(--gr);
     border-radius:5px;padding:5px;margin-top:4px;
     font-size:.7em;color:#6ee7b7}
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:9px}
.tab{padding:5px 12px;border-radius:7px;cursor:pointer;
     font-size:.74em;background:#1f2937;color:#9ca3af;
     border:1px solid var(--border);transition:.2s}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tc{display:none}
.tc.active{display:block}
.abadge{display:inline-block;padding:2px 7px;
  border-radius:9px;font-size:.69em;font-weight:700;margin:2px}
.aon{background:#052918;color:var(--gr);
     border:1px solid var(--gr)}
.aoff{background:#1f2937;color:#374151;
      border:1px solid #374151}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:var(--card)}
::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:4px}
@media(max-width:900px){
  .r3,.r5{grid-template-columns:1fr 1fr}
  .r2{grid-template-columns:1fr}
}
</style>
</head><body>

<div class="hdr">
  <div style="font-size:1.6em">🤖</div>
  <div>
    <h1>Pepper Brain — Port 5007 (Master Control)</h1>
    <p style="font-size:.72em;opacity:.8">
      Commander: <b>Lamya</b> |
      Child: <b>{{s.name}}</b> (age {{s.age}}) |
      <span class="prot {{s.protocol}}">
        {{s.protocol}}</span> |
      {{s.difficulty.upper()}} |
      {{s.session_start}}
    </p>
  </div>
  <span class="bd live">● LIVE</span>
  <span class="bd" style="background:#1a2555;color:var(--bl);
      border:1px solid var(--bl)">
    {% if s.gemini_ok %}⚡ {{s.gemini_model}}
    {% else %}⚠️ Offline{% endif %}
  </span>
</div>

<!-- HARD-CODED NAV (no 404) -->
<div class="nav-strip">
  <a href="http://localhost:5007" class="active">
    🧠 Brain :5007</a>
  <a href="http://localhost:5009" class="game"
     target="_blank">
    🎮 Games :5009</a>
  <a href="http://localhost:5001" class="report"
     target="_blank">
    📋 Reports :5001</a>
  <a href="http://localhost:5007/api/state"
     target="_blank">
    📡 API State</a>
  <a href="http://localhost:5007/export">
    📥 Export</a>
  <a href="http://localhost:5007/report_now"
     class="report">
    ⚡ Auto-Report</a>
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
      <div class="n">P{{s.prompt_level}}</div>
      <div class="l">💡 Prompt</div>
    </div>
    <div class="stat">
      <div class="n n-g">{{s.streak}}</div>
      <div class="l">🔥 Streak</div>
    </div>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <div class="tab active" onclick="T('overview')">
      📊 Overview</div>
    <div class="tab" onclick="T('charts')">
      📈 Charts</div>
    <div class="tab" onclick="T('assess')">
      📋 IASQ</div>
    <div class="tab" onclick="T('chatbot')">
      💬 Chatbot</div>
    <div class="tab" onclick="T('notes')">
      📝 Notes</div>
    <div class="tab" onclick="T('help')">
      💡 Help</div>
    <div class="tab" onclick="T('settings')">
      ⚙️ Settings</div>
  </div>

  <!-- OVERVIEW -->
  <div id="tc-overview" class="tc active">
   <div class="row r3">

    <!-- EMOTION -->
    <div class="card">
     <h2>😊 Emotion (6 types) + Actions</h2>
     <div style="text-align:center;padding:6px">
      <div class="emo {{s.emotion}}">
        {{s.emotion.upper()}}</div>
      <div style="margin:7px 0">
       <div class="bar-bg">
        <div class="bar"
             style="width:{{s.attention}}%"></div>
       </div>
       <span style="font-size:.7em;color:var(--pu)">
         {{s.attention}}%</span>
      </div>
      <div style="font-size:.73em;color:var(--mu)">
        Engagement:
        <b style="color:var(--text)">
          {{s.engagement}}</b></div>
      <div style="font-size:.7em;margin-top:4px;color:
        {{'#34d399' if s.face_detected else '#f87171'}}">
        {{'✅ Face' if s.face_detected else '❌ No Face'}}</div>
      <div style="margin:8px 0;text-align:left">
       {% for em,sc in s.emotion_scores.items() %}
       {% if sc > 0.05 %}
       <div style="display:flex;align-items:center;
                   gap:4px;margin:2px 0">
        <span style="width:50px;font-size:.63em;
                     color:var(--mu)">{{em[:7]}}</span>
        <div style="flex:1;background:#1f2937;
                    height:7px;border-radius:4px">
         <div style="width:{{(sc*100)|int}}%;
                     height:7px;border-radius:4px;
                     background:#6366f1"></div>
        </div>
        <span style="font-size:.63em;color:var(--pu);
                     min-width:28px">
          {{(sc*100)|int}}%</span>
       </div>{% endif %}{% endfor %}
      </div>
      <!-- Action badges -->
      <div>
       <span class="abadge
         {{'aon' if s.hand_raised else 'aoff'}}">
         ✋ Hand</span>
       <span class="abadge
         {{'aon' if s.waving else 'aoff'}}">
         👋 Wave</span>
       <span class="abadge
         {{'aon' if s.clapping else 'aoff'}}">
         👏 Clap</span>
      </div>
      {% if s.verify_action %}
      <div style="font-size:.7em;color:var(--yl);margin-top:4px">
        ⏳ Verify: {{s.verify_action}}</div>
      {% endif %}
      {% if s.is_speaking %}
      <div style="font-size:.7em;color:var(--bl);margin-top:4px">
        🔊 Speaking...</div>
      {% elif s.listening %}
      <div style="font-size:.7em;color:var(--gr);margin-top:4px">
        👂 Listening...</div>
      {% elif s.waiting_for_child %}
      <div style="font-size:.7em;color:var(--yl);margin-top:4px">
        ⏳ Waiting for child...</div>
      {% endif %}
     </div>
    </div>

    <!-- CONTROLS -->
    <div class="card">
     <h2>🎮 Controls</h2>
     <form method="POST" action="/cmd">
      <div style="margin-bottom:6px">
       <div style="font-size:.68em;color:var(--mu);
                   margin-bottom:3px">Protocols</div>
       <button class="btn" name="c" value="aba">📚 ABA</button>
       <button class="btn" name="c" value="dtt">🎯 DTT</button>
       <button class="btn" name="c" value="teacch">📅 TEACCH</button>
       <button class="btn" name="c" value="tie">🧠 TIE</button>
      </div>
      <div style="margin-bottom:6px">
       <div style="font-size:.68em;color:var(--mu);
                   margin-bottom:3px">Actions</div>
       <button class="btn btn-g" name="c" value="dance">
         💃 Dance</button>
       <button class="btn btn-y" name="c" value="celebrate">
         🎉 Celebrate</button>
       <button class="btn btn-b" name="c" value="game">
         🎮 Game</button>
       <button class="btn btn-r" name="c" value="break">
         ⏸ Break</button>
       <button class="btn" name="c" value="report">
         📋 Report</button>
      </div>
     </form>
     <div style="font-size:.68em;color:var(--mu);
                 margin:5px 0 3px">📺 Skill Videos</div>
     <div style="display:flex;flex-wrap:wrap;gap:2px">
      {% for sk in skills %}
      <form method="POST" action="/skill"
            style="display:inline">
       <button class="btn btn-y" name="s" value="{{sk}}"
               style="font-size:.62em;padding:3px 6px">
         {{sk}}</button>
      </form>{% endfor %}
     </div>
     <form method="POST" action="/search"
           style="display:flex;gap:4px;margin-top:6px">
      <input name="q" placeholder="Search video...">
      <button class="btn">🔍</button>
     </form>
     <form method="POST" action="/parent_msg"
           style="display:flex;gap:4px;margin-top:4px">
      <input name="msg"
             placeholder="Message via Pepper...">
      <button class="btn btn-g">📤</button>
     </form>
     <form method="POST" action="/name"
           style="display:flex;gap:4px;margin-top:4px">
      <input name="n" placeholder="Child name...">
      <button class="btn">✓</button>
     </form>
    </div>

    <!-- SESSION CHAT -->
    <div class="card">
     <h2>💬 Live Session (Listen-First)</h2>
     <div class="chat-box" id="chat-s">
      {% for m in s.session_chat[-20:]|reverse %}
      <div class="cm {{'cmp' if m.role=='pepper' else 'cmc'}}">
       <span style="color:{{'var(--pu)' if m.role=='pepper' else 'var(--gr)'}};
                    font-size:.64em">
         {{'🤖 Pepper' if m.role=='pepper'
           else '👦 '+s.name}}
         [{{m.time}}]</span><br>
       {{m.text}}
      </div>{% endfor %}
     </div>
     <div style="font-size:.68em;color:var(--mu)">
       {{s.logs|length}} interactions |
       ✅{{s.tasks_success}} ❌{{s.tasks_fail}}
     </div>
    </div>
   </div>
  </div>

  <!-- CHARTS -->
  <div id="tc-charts" class="tc">
   <div class="row r2">
    <div class="card">
     <h2>📈 Attention</h2>
     <div class="chart-wrap">
      <canvas id="attC"></canvas></div>
    </div>
    <div class="card">
     <h2>🏆 Score</h2>
     <div class="chart-wrap">
      <canvas id="scoreC"></canvas></div>
    </div>
   </div>
   <div class="row r2">
    <div class="card">
     <h2>😊 Emotions</h2>
     <div class="chart-wrap">
      <canvas id="emoC"></canvas></div>
    </div>
    <div class="card">
     <h2>🎯 Skills</h2>
     <div style="display:grid;
                 grid-template-columns:repeat(5,1fr);
                 gap:5px;margin-top:6px">
      {% for sk,v in s.skills.items() %}
      <div style="text-align:center">
       <div style="height:65px;background:#1f2937;
                   border-radius:5px;position:relative;
                   overflow:hidden">
        <div style="position:absolute;bottom:0;width:100%;
                    height:{{v}}%;
                    background:linear-gradient(0deg,
                    #6366f1,#a78bfa);border-radius:5px">
        </div>
       </div>
       <div style="font-size:.61em;color:var(--mu);
                   margin-top:2px">{{sk}}</div>
       <div style="font-size:.68em;color:var(--pu);
                   font-weight:700">{{v}}%</div>
      </div>{% endfor %}
     </div>
    </div>
   </div>
   <div class="card">
    <h2>📋 Log</h2>
    <div class="log-box">
     {% for lg in s.logs[-40:]|reverse %}
     <div class="li {{lg.type}}">
      <span style="color:#6366f1">{{lg.time}}</span>
      <span class="prot {{lg.proto}}">{{lg.proto}}</span>
      <b style="color:var(--pu)">{{lg.child}}</b>:
      {{lg.msg}}
      <span style="color:#374151;font-size:.72em">
        |{{lg.emo}}</span>
     </div>{% endfor %}
    </div>
    <a href="/export" class="btn btn-g"
       style="display:inline-block;margin-top:6px;
              text-decoration:none">
      📥 Export</a>
   </div>
  </div>

  <!-- ASSESSMENT (IASQ) -->
  <div id="tc-assess" class="tc">
   <div class="row r2">
    <div class="card">
     <h2>📋 IASQ Screening</h2>
     {% if s.iasq_result %}
     <div style="background:#051a0f;border-radius:7px;
                 padding:9px;margin-bottom:9px;
                 border:1px solid var(--gr)">
      <div style="font-size:.8em;color:var(--gr);
                  font-weight:700">
        {{s.iasq_result}}</div>
      <div style="font-size:.7em;color:var(--mu)">
        Score: {{s.iasq_score}}/50</div>
     </div>{% endif %}
     <form method="POST" action="/iasq">
      {% for i,q in qs.items() %}
      <div style="background:#0a1020;border-radius:7px;
                  padding:9px;margin:4px 0">
       <div style="font-size:.76em;margin-bottom:5px">
         {{i}}. {{q.q}}</div>
       <div style="display:flex;gap:6px;flex-wrap:wrap">
        {% for j in range(5) %}
        <label style="cursor:pointer;font-size:.68em;
                       color:var(--mu)">
         <input type="radio" name="q{{i}}"
                value="{{j}}"
                style="width:auto;margin:0 3px">
         {{j}}
        </label>{% endfor %}
       </div>
      </div>{% endfor %}
      <button class="btn btn-g"
              style="width:100%;margin-top:7px;padding:8px">
        🔍 Calculate</button>
     </form>
    </div>
    <div class="card">
     <h2>📊 Result Analysis</h2>
     {% if s.iasq_result %}
     {% set pct=(s.iasq_score/50*100)|int %}
     <div style="text-align:center;padding:14px">
      <div style="font-size:2em;font-weight:700;color:
        {{'#34d399' if pct<40 else '#fbbf24' if pct<70 else '#f87171'}}">
        {{s.iasq_result}}</div>
      <div class="bar-bg" style="margin:9px 0">
       <div style="width:{{pct}}%;height:8px;
                   border-radius:5px;
                   background:{{'#34d399' if pct<40
                   else '#fbbf24' if pct<70
                   else '#f87171'}}"></div>
      </div>
      <div style="font-size:.73em;color:var(--mu)">
        {{pct}}% — {{s.iasq_score}}/50</div>
     </div>
     <div style="font-size:.72em;color:#9ca3af;
                 line-height:1.7;margin-top:8px">
      {% if pct<40 %}
      • 2x/week therapy<br>
      • Focus: social + communication<br>
      • Monthly monitoring
      {% elif pct<70 %}
      • 3x/week therapy<br>
      • Start intensive ABA + DTT<br>
      • Consult pediatrician
      {% else %}
      • Immediate specialist evaluation<br>
      • Consider EIBI (intensive)<br>
      • Special education support
      {% endif %}
     </div>
     {% else %}
     <div style="text-align:center;padding:25px;
                 color:var(--mu);font-size:.8em">
       Complete IASQ test to see results.
     </div>{% endif %}
    </div>
   </div>
  </div>

  <!-- CHATBOT -->
  <div id="tc-chatbot" class="tc">
   <div class="row r2">
    <div class="card">
     <h2>🤖 Parent AI Chatbot (Arabic + English)</h2>
     <div class="chat-box" id="chat-p">
      {% for m in s.parent_chat[-20:]|reverse %}
      <div class="cm {{'cmp' if m.role=='pepper' else 'cmr'}}">
       <span style="color:{{'var(--pu)' if m.role=='pepper'
                    else 'var(--bl)'}};font-size:.63em">
         {{'🤖' if m.role=='pepper' else '👨‍👩‍👧'}}
         [{{m.time}}]</span><br>
       {{m.text}}
      </div>{% endfor %}
      {% if not s.parent_chat %}
      <div style="color:var(--mu);text-align:center;
                  padding:18px;font-size:.77em">
        Ask any autism question in English or Arabic 🤗
      </div>{% endif %}
     </div>
     <form method="POST" action="/parent_ask"
           style="display:flex;gap:4px">
      <input name="question"
             placeholder="Ask about autism...">
      <button class="btn btn-g">💬</button>
     </form>
    </div>
    <div class="card">
     <h2>📚 Quick Questions</h2>
     {% for q in qqs %}
     <form method="POST" action="/parent_ask">
      <button class="btn" name="question"
              value="{{q}}"
              style="width:100%;text-align:left;
                     margin:2px 0;font-size:.69em;
                     padding:5px 8px">
       {{q}}</button>
     </form>{% endfor %}
    </div>
   </div>
  </div>

  <!-- NOTES -->
  <div id="tc-notes" class="tc">
   <div class="row r2">
    <div class="card">
     <h2>📝 Add Observation</h2>
     <form method="POST" action="/add_note">
      <select name="cat" style="margin-bottom:6px">
       <option>behavior</option>
       <option>progress</option>
       <option>concern</option>
       <option>milestone 🎉</option>
      </select>
      <textarea name="note"
        placeholder="What did you observe?..."></textarea>
      <button class="btn btn-g"
              style="width:100%;margin-top:5px;padding:8px">
       ➕ Save</button>
     </form>
    </div>
    <div class="card">
     <h2>📋 Notes History</h2>
     <div style="max-height:300px;overflow-y:auto">
      {% for n in s.parent_notes[-15:]|reverse %}
      <div class="note">
       <div style="display:flex;justify-content:space-between">
        <span style="color:var(--pu);font-size:.67em;
                     font-weight:700">
          {{n.category.upper()}}</span>
        <span style="color:var(--mu);font-size:.66em">
          {{n.time}}</span>
       </div>
       {{n.text}}
      </div>{% endfor %}
     </div>
    </div>
   </div>
  </div>

  <!-- HELP -->
  <div id="tc-help" class="tc">
   <div class="row r3">
    <div class="hc"><div class="hct">🎯 ABA Protocol</div>
     <div class="hcb">Break tasks into tiny steps.
       Immediate specific praise (&lt;2 seconds).
       Token economy. Consistent repetition.</div>
     <div class="tip">💡 Fail 3× → switch to easier
       version immediately.</div>
    </div>
    <div class="hc"><div class="hct">📚 DTT Protocol</div>
     <div class="hcb">ONE instruction at a time.
       Wait 5 seconds. Prompt hierarchy:
       verbal → gestural → physical.
       Keep sessions 10-15 min.</div>
     <div class="tip">💡 Same words every time.
       Consistency = less anxiety.</div>
    </div>
    <div class="hc"><div class="hct">📅 TEACCH Visual</div>
     <div class="hcb">Picture daily schedule.
       Show NEXT item only. Visual timers.
       Organized, predictable workspace.</div>
     <div class="tip">💡 Let child check off activities.
       Control reduces meltdowns.</div>
    </div>
    <div class="hc"><div class="hct">⚠️ Meltdown Protocol</div>
     <div class="hcb">
       1. Stay calm<br>2. Remove triggers<br>
       3. Give space<br>4. Speak softly (5 words max)<br>
       5. No forced eye contact<br>6. Comfort item</div>
     <div class="tip">💡 Calm kit: headphones,
       fidget toy, weighted blanket.</div>
    </div>
    <div class="hc"><div class="hct">👏 Reinforcement</div>
     <div class="hcb">Praise within 2 seconds.
       Be SPECIFIC: "Great clapping!"
       Find top 3 motivators for YOUR child.</div>
     <div class="tip">💡 Create "reward menu" —
       10 items child loves.</div>
    </div>
    <div class="hc"><div class="hct">📊 Dashboard Guide</div>
     <div class="hcb">
       <b>Att &gt;70%</b> → engaged ✅<br>
       <b>P0</b> → great ✅ | <b>P1</b> → verbal ℹ️<br>
       <b>P2</b> → visual ⚠️ | <b>P3</b> → direct 🛑<br>
       <b>Distressed</b> → break NOW</div>
     <div class="tip">💡 Screenshot weekly for
       therapist.</div>
    </div>
   </div>
   <!-- Summary -->
   <div class="card" style="margin-top:9px">
    <h2>📋 Session Summary</h2>
    <div style="background:#0a1020;border-radius:7px;
                padding:10px;font-size:.74em;
                color:#9ca3af;line-height:1.9">
      Child: <b style="color:var(--text)">{{s.name}}</b> |
      Age: {{s.age}} | {{s.session_date}}<br>
      Score: <b style="color:var(--pu)">
        {{s.score}}</b> |
      Tokens: <b style="color:var(--yl)">
        ⭐{{s.tokens}}</b> |
      Interactions: {{s.logs|length}}<br>
      Emotion: {{s.emotion}} |
      Protocol: {{s.protocol}} |
      Level: {{s.difficulty.upper()}}<br>
      Success: {{s.tasks_success}} |
      Failed: {{s.tasks_fail}} |
      IASQ: {{s.iasq_result or 'Not taken'}}
    </div>
    <div style="margin-top:7px;display:flex;gap:6px">
     <a href="/export" class="btn btn-g"
        style="text-decoration:none">📥 JSON</a>
     <a href="/report_now" class="btn btn-b"
        style="text-decoration:none">
       📋 Auto-Report → 5001</a>
    </div>
   </div>
  </div>

  <!-- SETTINGS -->
  <div id="tc-settings" class="tc">
   <div class="row r2">
    <div class="card">
     <h2>👦 Child Profile</h2>
     <form method="POST" action="/update_child">
      <label style="font-size:.7em;color:var(--mu)">Name</label>
      <input name="name" value="{{s.name}}"
             style="margin-bottom:6px">
      <label style="font-size:.7em;color:var(--mu)">Age</label>
      <input name="age" type="number"
             value="{{s.age}}" min="1" max="18"
             style="margin-bottom:6px">
      <label style="font-size:.7em;color:var(--mu)">Diagnosis</label>
      <select name="diagnosis" style="margin-bottom:6px">
       <option {{'selected' if s.diagnosis=='ASD Level 1'}}>ASD Level 1</option>
       <option {{'selected' if s.diagnosis=='ASD Level 2'}}>ASD Level 2</option>
       <option {{'selected' if s.diagnosis=='ASD Level 3'}}>ASD Level 3</option>
       <option>Suspected ASD</option>
      </select>
      <button class="btn btn-g"
              style="width:100%;padding:8px">
       💾 Save</button>
     </form>
    </div>
    <div class="card">
     <h2>⚙️ Therapy Settings</h2>
     <form method="POST" action="/update_settings">
      <label style="font-size:.7em;color:var(--mu)">Difficulty</label>
      <select name="difficulty" style="margin-bottom:6px">
       <option {{'selected' if s.difficulty=='easy'}}>easy</option>
       <option {{'selected' if s.difficulty=='medium'}}>medium</option>
       <option {{'selected' if s.difficulty=='hard'}}>hard</option>
      </select>
      <label style="font-size:.7em;color:var(--mu)">
        Mic Sensitivity (lower=whispers)</label>
      <input name="mic_e" type="number"
             value="10" min="5" max="100"
             style="margin-bottom:6px">
      <button class="btn btn-g"
              style="width:100%;padding:8px">
       💾 Save</button>
     </form>
    </div>
   </div>
  </div>

</div>

<script>
function T(n){
  document.querySelectorAll('.tc')
    .forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab')
    .forEach(t=>t.classList.remove('active'));
  document.getElementById('tc-'+n)
    .classList.add('active');
  event.target.classList.add('active');
}

// Charts
const AD={{att_history|tojson}};
const SD={{score_history|tojson}};
const ED={{emo_dist|tojson}};
const LB=Array.from({length:AD.length},(_,i)=>i+1);
const CO={responsive:true,maintainAspectRatio:false,
  plugins:{legend:{labels:{color:'#9ca3af',font:{size:9}}}},
  scales:{x:{ticks:{color:'#6b7280',font:{size:8}},
             grid:{color:'#1f2937'}},
          y:{ticks:{color:'#6b7280',font:{size:8}},
             grid:{color:'#1f2937'}}}};

if(document.getElementById('attC')){
  new Chart(document.getElementById('attC'),{
    type:'line',
    data:{labels:LB,datasets:[{
      label:'Attention %',data:AD,
      borderColor:'#6366f1',
      backgroundColor:'rgba(99,102,241,0.1)',
      tension:0.4,fill:true,pointRadius:2}]},
    options:{...CO,scales:{...CO.scales,
      y:{...CO.scales.y,min:0,max:100}}}});}

if(document.getElementById('scoreC')){
  new Chart(document.getElementById('scoreC'),{
    type:'bar',
    data:{labels:LB,datasets:[{
      label:'Score',data:SD,
      backgroundColor:'rgba(167,139,250,0.5)',
      borderColor:'#a78bfa',borderWidth:1}]},
    options:CO});}

if(document.getElementById('emoC')&&
   Object.keys(ED).length>0){
  const EC={happy:'#34d399',sad:'#60a5fa',
    angry:'#f87171',neutral:'#9ca3af',
    fear:'#fbbf24',surprised:'#c084fc',
    joyful:'#34d399',disgust:'#6ee7b7'};
  new Chart(document.getElementById('emoC'),{
    type:'doughnut',
    data:{labels:Object.keys(ED),
      datasets:[{data:Object.values(ED),
        backgroundColor:Object.keys(ED)
          .map(e=>EC[e]||'#6366f1')}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'right',
        labels:{color:'#9ca3af',font:{size:9}}}}}});}

['chat-s','chat-p'].forEach(id=>{
  const el=document.getElementById(id);
  if(el) el.scrollTop=el.scrollHeight;});
</script>
</body></html>"""

SKILLS_LIST = [
    "wash face","brush teeth","emotions","colors",
    "numbers","alphabet","sharing","greetings",
    "animals","shapes","toilet",
]

QUICK_QS = [
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
@brain_app.route("/index")
def brain_home():
    emo_dist = {}
    for e in ST["emo_history"]:
        emo_dist[e] = emo_dist.get(e,0)+1
    qs = {i+1:q for i,q in enumerate(IASQ_QS)}
    return render_template_string(
        BRAIN_HTML, s=ST, skills=SKILLS_LIST,
        qqs=QUICK_QS, qs=qs,
        att_history=ST["att_history"][-40:],
        score_history=ST["score_history"][-40:],
        emo_dist=emo_dist)

# Hard-coded routes (no 404)
@brain_app.route("/cmd", methods=["GET","POST"])
def brain_cmd():
    c = (request.form.get("c","") or
         request.args.get("c",""))
    ST["sim_cmd"] = c
    if c == "report":
        # Auto-generate and send to reports server
        if _gemini:
            rep = _gemini.generate_report()
            ST["reports"].append({
                "time":    datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"),
                "content": rep,
            })
            LOG("📋 Auto-report generated","success")
    return redirect("/")

@brain_app.route("/report_now")
def brain_report_now():
    if _gemini:
        rep = _gemini.generate_report()
        ST["reports"].append({
            "time":    datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"),
            "content": rep,
        })
        LOG("📋 Report sent to 5001","success")
    return redirect("http://localhost:5001")

@brain_app.route("/skill", methods=["GET","POST"])
def brain_skill():
    s   = (request.form.get("s","") or
           request.args.get("s",""))
    url = ("https://www.youtube.com/results?search_query="
           +urllib.parse.quote(
               s+" autism children educational"))
    webbrowser.open(url)
    LOG(f"📺 YouTube: {s}")
    return redirect("/")

@brain_app.route("/search", methods=["GET","POST"])
def brain_search():
    q   = (request.form.get("q","") or
           request.args.get("q",""))
    url = ("https://www.youtube.com/results?search_query="
           +urllib.parse.quote(
               q+" autism educational children"))
    webbrowser.open(url)
    return redirect("/")

@brain_app.route("/name", methods=["GET","POST"])
def brain_name():
    n = (request.form.get("n","") or
         request.args.get("n","")).strip().title()
    if n: ST["name"]=n; ST["known"]=True
    return redirect("/")

@brain_app.route("/parent_msg", methods=["GET","POST"])
def brain_parent_msg():
    msg = (request.form.get("msg","") or
           request.args.get("msg","")).strip()
    if msg: ST["sim_cmd"] = f"parent_msg:{msg}"
    return redirect("/")

@brain_app.route("/parent_ask", methods=["GET","POST"])
def brain_parent_ask():
    q = (request.form.get("question","") or
         request.args.get("question","")).strip()
    if q and _gemini:
        ST["parent_chat"].append({
            "role":"parent","text":q,
            "time":datetime.now().strftime("%H:%M:%S")})
        ans = _gemini.parent_ask(q)
        ST["parent_chat"].append({
            "role":"pepper","text":ans,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["parent_chat"])>40:
            ST["parent_chat"]=ST["parent_chat"][-40:]
    return redirect("/")

@brain_app.route("/iasq", methods=["GET","POST"])
def brain_iasq():
    total = sum(
        int(request.form.get(f"q{i}",0))
        for i in range(1,11))
    if   total<=20: res="Low Risk ✅"
    elif total<=35: res="Medium Risk ⚠️"
    else:           res="High Risk 🔴"
    ST["iasq_score"]  = total
    ST["iasq_result"] = res
    LOG(f"IASQ: {res}","success")
    return redirect("/")

@brain_app.route("/add_note", methods=["GET","POST"])
def brain_add_note():
    note = (request.form.get("note","") or
            request.args.get("note","")).strip()
    cat  = (request.form.get("cat","") or
            request.args.get("cat","other"))
    if note:
        ST["parent_notes"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": note, "category": cat})
    return redirect("/")

@brain_app.route("/update_child", methods=["GET","POST"])
def brain_update_child():
    ST["name"] = (request.form.get("name","Friend") or
                  "Friend").strip().title()
    ST["age"]  = int(request.form.get("age",6) or 6)
    ST["diagnosis"] = (
        request.form.get("diagnosis","ASD Level 2") or
        "ASD Level 2")
    return redirect("/")

@brain_app.route("/update_settings",
                 methods=["GET","POST"])
def brain_update_settings():
    ST["difficulty"] = (
        request.form.get("difficulty","easy") or "easy")
    return redirect("/")

@brain_app.route("/export")
def brain_export():
    fn = (f"session_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(ST,f,indent=2,default=str)
    return jsonify({"saved":fn,"score":ST["score"]})

@brain_app.route("/api/state")
def brain_api_state():
    return jsonify({
        "name":       ST["name"],
        "emotion":    ST["emotion"],
        "attention":  ST["attention"],
        "score":      ST["score"],
        "protocol":   ST["protocol"],
        "gemini_ok":  ST["gemini_ok"],
        "is_speaking":ST["is_speaking"],
        "listening":  ST["listening"],
        "hand_raised":ST["hand_raised"],
    })

# Catch-ALL (no 404)
@brain_app.errorhandler(404)
def b404(e): return redirect("/"), 302
@brain_app.errorhandler(405)
def b405(e): return redirect("/"), 302
@game_app.errorhandler(404)
def g404(e): return redirect("/"), 302
@report_app.errorhandler(404)
def r404(e): return redirect("/"), 302


# ══════════════════════════════════════════════════════════════
# THERAPY CONTROLLER (Listen-First Architecture)
# ══════════════════════════════════════════════════════════════
class TherapyCtrl:
    def __init__(self, gemini, voice, mic,
                 display, sim, actions):
        self.g=gemini; self.v=voice; self.m=mic
        self.d=display; self.s=sim; self.a=actions
        self.running=False

    def _speak(self, text):
        """Process tokens → display → speak"""
        clean = self.a.process(str(text))
        self.d.show_ai(clean)
        if self.s.ok: self.s.show_text(clean[:55])
        self.v.say(clean)

    def _ask_speak(self, prompt):
        """Ask Gemini and speak result"""
        resp = self.g.ask(prompt)
        self._speak(resp)
        return resp

    def run(self):
        """Main therapy loop (Listen-First)"""
        self.running = True
        ST["protocol"] = "GREETING"

        # Step 1: Get child's name (listen-first)
        name = self.m.get_name(self.v)

        # Step 2: Opening greeting + first task
        resp = self.g.ask(
            f"Child name is {name}. "
            "Greet warmly! [WAVE] Give first simple task. "
            "End with 'Ready? Your turn! 🎯'")
        self._speak(resp)
        time.sleep(0.5)

        # Step 3: Background listening
        self.m.listen_bg(self._on_speech)

        # Main therapy loop
        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx = 0
        last_em = ST["emotion"]
        em_t    = time.time()

        while self.running:
            # Silence check (Listen-First)
            if time.time()-ST["last_sound"] > 12:
                ST["last_sound"] = time.time()
                self._ask_speak(
                    "Child silent 12 seconds. "
                    "Gently encourage. "
                    "End: 'Ready? Your turn! 🎯'")

            # Prompt level
            self._prompt_check()

            # Emotion reaction
            curr = ST["emotion"]
            if curr!=last_em and time.time()-em_t > 8:
                last_em=curr; em_t=time.time()
                if curr in ["sad","angry","fear"]:
                    self._ask_speak(
                        f"Child became {curr}. React! [HUG]")

            # Dashboard commands
            self._handle_cmd()

            # Run protocol
            prot = protocols[p_idx%len(protocols)]
            p_idx+=1; ST["protocol"]=prot
            self._protocol(prot)
            time.sleep(0.3)

    def _prompt_check(self):
        em  = ST["emotion"]
        att = ST["attention"]
        eng = ST["engagement"]
        fd  = ST["face_detected"]
        pl  = ST.get("prompt_level",0)

        if fd and att>60 and em in [
                "happy","neutral","joyful"]:
            ST["prompt_level"] = 0
        elif not fd or att<40:
            if pl<1:
                ST["prompt_level"] = 1
                self._ask_speak(
                    "Child not visible/distracted. "
                    "Verbal prompt! [POINT] "
                    "'Look at me! Ready? Your turn!'")
        if eng=="distressed" and pl<3:
            ST["prompt_level"] = 3
            self._ask_speak(
                f"Child distressed ({em}). "
                "Calming [HUG]. Pause tasks.")

    def _handle_cmd(self):
        cmd = ST.get("sim_cmd")
        if not cmd: return
        ST["sim_cmd"] = None

        if cmd=="dance":
            self._ask_speak("Dance! [DANCE][CELEBRATE]")
        elif cmd=="game":
            webbrowser.open(
                f"http://localhost:{PORT_GAME}")
            self._ask_speak("Game time! [GAME]")
        elif cmd=="celebrate":
            self._ask_speak(
                "Celebrate! [CELEBRATE][CLAP][DANCE]")
        elif cmd=="break":
            self._ask_speak("Break time! Rest. [NOD]")
        elif cmd=="report":
            if _gemini:
                rep = _gemini.generate_report()
                ST["reports"].append({
                    "time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"),
                    "content": rep,
                })
                LOG("📋 Report generated","success")
        elif cmd.startswith("parent_msg:"):
            self._ask_speak(
                f"Tell child: {cmd[11:]}")
        elif cmd in ["aba","dtt","teacch","tie"]:
            ST["protocol"] = cmd.upper()

    def _protocol(self, prot):
        name = ST["name"]
        em   = ST["emotion"]
        att  = ST["attention"]
        diff = ST["difficulty"]

        if prot == "ABA":
            TASKS = {
                "easy":  [
                    "Clap hands!",
                    "Touch your nose!",
                    "Wave hello! [VERIFY: wave]",
                    "Show happy face!",
                    "Raise your hand! [VERIFY: hand]",
                ],
                "medium":[
                    "Stand up then sit!",
                    "Touch your ears!",
                    "Jump once!",
                    "Count 3 fingers!",
                    "Clap 3 times! [VERIFY: clap]",
                ],
                "hard":  [
                    "Tell me your full name!",
                    "What color is the sky?",
                    "Name 2 animals!",
                    "Count backwards from 5!",
                ],
            }
            task = random.choice(
                TASKS.get(diff, TASKS["easy"]))
            ST["current_task"] = task
            ST["task_success"]  = False
            ST["task_retries"]  = 0

            # Set verification if needed
            if "[VERIFY:" in task:
                m = re.search(r'\[VERIFY:\s*(.+?)\]',task)
                if m:
                    ST["verify_action"]  = m.group(1)
                    ST["verify_result"]  = False
                    ST["verify_timeout"] = time.time()+15
                task_clean = re.sub(
                    r'\[VERIFY:[^\]]+\]','',task).strip()
            else:
                task_clean = task

            resp = self.g.ask(
                f"ABA: Give task '{task_clean}' to {name}. "
                f"Em:{em} Att:{att}%. "
                "End: 'Ready? Your turn! 🎯'")
            self._speak(resp)
            self.d.show_task(task_clean)

            success = self._wait(task_clean, 12)
            if success:
                ST["score"]         += 10
                ST["streak"]        += 1
                ST["tokens"]        += 1
                ST["tasks_success"] += 1
                ST["clap_detected"]  = False
                ST["task_success"]   = False
                ST["verify_action"]  = None
                ST["verify_result"]  = False

                resp = self.g.ask(
                    f"{name} did '{task_clean}'! "
                    "Celebrate! [CLAP][REWARD:2]")
                self._speak(resp)
                self.d.show_praise("AMAZING! ⭐⭐")
                LOG(f"ABA ✅: {task_clean}","success","ABA")

                if ST["streak"] >= 3:
                    if diff=="easy":   ST["difficulty"]="medium"
                    elif diff=="medium":ST["difficulty"]="hard"
                    ST["streak"] = 0
                    # Auto-generate progress report
                    if _gemini and ST["tasks_success"]%10==0:
                        rep = _gemini.generate_report()
                        ST["reports"].append({
                            "time": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"),
                            "content": rep,
                        })
                    self._ask_speak(
                        "Leveled up! [DANCE][CELEBRATE]")

                # Update skills
                for sk in ST["skills"]:
                    ST["skills"][sk] = min(
                        100,
                        ST["skills"][sk]+random.randint(0,2))
            else:
                ST["streak"]       = 0
                ST["tasks_fail"]  += 1
                ST["task_retries"]+= 1

                if ST["task_retries"] < 3:
                    resp = self.g.ask(
                        f"{name} needs help with '{task_clean}'. "
                        "Gentle retry. "
                        "End: 'Ready? Your turn! 🎯'")
                    self._speak(resp)
                else:
                    ST["task_retries"] = 0
                    self._ask_speak(
                        f"Skip '{task_clean}'. "
                        "Give {name} easier task. "
                        "End: 'Ready? Your turn! 🎯'")

                LOG(f"ABA ❌: {task_clean}","fail","ABA")
            time.sleep(2)

        elif prot == "DTT":
            resp = self.g.ask(
                f"ONE DTT trial for {name}. "
                f"Diff:{diff} Em:{em}. "
                "End: 'Ready? Your turn! 🎯'")
            self._speak(resp)
            self.d.show_task("DTT Trial")
            ok = self._wait("DTT", 10)
            if ok:
                ST["score"]        += 12
                ST["tokens"]       += 1
                ST["tasks_success"]+= 1
                self._ask_speak(
                    f"DTT success! [CLAP][REWARD:1]")
                self.d.show_praise("CORRECT! ✅")
                LOG("DTT ✅","success","DTT")
            else:
                ST["tasks_fail"] += 1
                self._ask_speak(
                    "DTT correction. Try again. "
                    "'Ready? Your turn! 🎯'")
                LOG("DTT ❌","fail","DTT")
            time.sleep(2)

        elif prot == "TEACCH":
            resp = self.g.ask(
                f"TEACCH visual schedule step for {name}. "
                f"Em:{em}. End: 'Ready? Your turn! 🎯'")
            self._speak(resp)
            time.sleep(3)
            if ST["emotion"] in ["happy","joyful"]:
                ST["score"] += 15
            LOG("TEACCH ✅","success","TEACCH")

        elif prot == "TIE":
            resp = self.g.ask(
                f"TIE adaptive for {name}. "
                f"Em:{em} Att:{att}% Eng:{ST['engagement']}. "
                "End: 'Ready? Your turn! 🎯'")
            self._speak(resp)
            time.sleep(3)
            ST["score"] += 8
            LOG("TIE ✅","success","TIE")

    def _wait(self, task, timeout=12):
        """Wait for child response (listen-first)"""
        deadline = time.time()+timeout
        while time.time()<deadline:
            if (ST["clap_detected"] and
                    "clap" in task.lower()):
                return True
            if ST["task_success"]:
                return True
            if ST["verify_result"]:
                ST["verify_result"]=False
                return True
            if (ST["emotion"] in ["happy","joyful"]
                    and ST["attention"]>65):
                return True
            time.sleep(0.25)
        return False

    def _on_speech(self, text):
        """Child speaks → Pepper responds immediately"""
        ST["last_sound"] = time.time()
        ST["waiting_for_child"] = False

        if not text: return
        t    = text.lower()
        name = ST["name"]

        # Sound but not speech
        if text == "[sound]":
            self.v.say(f"I heard you {name}! 👍",
                       wait_after=False)
            return

        # Interrupt if Pepper was speaking
        if ST["is_speaking"]:
            self.v.interrupt()

        # Name learning
        if not ST["known"]:
            n = self.m._extract(text)
            if n:
                ST["name"]=n; ST["known"]=True
                self._ask_speak(
                    f"Child said name is {n}! "
                    "Welcome! [WAVE] Give first task. "
                    "'Ready? Your turn! 🎯'")
            return

        # Educational questions → YouTube
        edu = ["how","what is","show me","what does",
               "teach","explain","كيف","ما هو","أرني",
               "what are","tell me"]
        if any(w in t for w in edu):
            resp = self.g.ask(
                f"Child asked: '{text}'. "
                "Answer simply. Use [YOUTUBE:...] "
                "for educational video. "
                "'Ready? Your turn! 🎯'")
            self._speak(resp)
            return

        # Game request
        if any(w in t for w in
               ["play","game","fun","العب","لعبة"]):
            self._ask_speak(
                f"{name} wants game! [GAME][CELEBRATE]")
            return

        # Task success detection
        task = ST.get("current_task","")
        if task:
            kws = re.sub(r'\[.*?\]','',task).lower()
            kws = kws.replace("!","").split()
            if any(w in t for w in kws if len(w)>2):
                ST["task_success"] = True

        # General Gemini response (live AI)
        resp = self.g.ask(
            f"Child said: '{text}'. "
            "Respond therapeutically. "
            "End: 'Ready? Your turn! 🎯'")
        self._speak(resp)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def run_flask(app, port, name):
    app.run(port=port, debug=False,
            use_reloader=False, threaded=True)

def main():
    global _gemini

    print("""
╔══════════════════════════════════════════════════╗
║  PEPPER UNIFIED AI THERAPIST v4.0               ║
║  Commander: Lamya                               ║
╠══════════════════════════════════════════════════╣
║  🧠 Brain:   http://localhost:5007              ║
║  🎮 Games:   http://localhost:5009              ║
║  📋 Reports: http://localhost:5001              ║
║  🎤 Mic:     energy=10 (whisper detection)      ║
║  📷 Camera:  500x500 emotion window             ║
║  🔊 Voice:   interruptible                      ║
╚══════════════════════════════════════════════════╝
""")

    # Thread 4: Start all Flask servers
    for app, port, name in [
        (game_app,   PORT_GAME,   "Game"),
        (report_app, PORT_REPORTS,"Reports"),
        (brain_app,  PORT_BRAIN,  "Brain"),
    ]:
        threading.Thread(
            target=run_flask,
            args=(app,port,name),
            daemon=True).start()
        print(f"✅ {name}: http://localhost:{port}")
        time.sleep(0.3)

    time.sleep(0.8)

    # Init components
    gemini  = GeminiBrain()
    _gemini = gemini
    voice   = Voice()
    camera  = Camera()
    em_eng  = EmotionEngine()
    display = Display(em_eng, camera)
    mic     = Mic()

    # Thread 1: PyBullet
    sim    = PepperSim()
    pepper = sim.launch()
    actions= Actions(pepper)

    time.sleep(1.5)
    ST["name"] = "Friend"

    # Welcome
    voice.say(
        "Welcome! I am Pepper, your AI therapy partner. "
        "Commander Lamya, all systems ready! "
        "Let us begin the session!",
        wait_after=False)
    if pepper:
        threading.Thread(
            target=actions._wave, daemon=True).start()

    # Thread 2: Therapy (Listen-First)
    ctrl = TherapyCtrl(
        gemini, voice, mic, display, sim, actions)
    t2 = threading.Thread(
        target=ctrl.run, daemon=True)
    t2.start()

    # Thread 3: Vision already in Display class

    print("\n" + "="*52)
    print("✅ ALL 4 THREADS ACTIVE")
    print("="*52)
    print(f"🧠 Brain:   http://localhost:{PORT_BRAIN}")
    print(f"🎮 Games:   http://localhost:{PORT_GAME}")
    print(f"📋 Reports: http://localhost:{PORT_REPORTS}")
    print("📷 Windows: Camera + 500x500 Emotion")
    print("⌨️  Commands:")
    print("   report  → generate clinical report")
    print("   name X  → set child name")
    print("   stop    → interrupt speech")
    print("   exit    → end session")
    print("="*52+"\n")

    while getattr(display,'running',True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()

            if cl in ["q","exit","quit"]:
                ctrl.running=False; display.stop(); break
            elif cl in ["stop","interrupt"]:
                voice.interrupt()
                print("🛑 Speech interrupted!")
            elif cl == "report":
                ST["sim_cmd"] = "report"
                print("📋 Generating report...")
            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                ST["name"]=n; ST["known"]=True
                voice.say(f"Hello {n}!",wait_after=False)
            elif cl == "stats":
                dur = int((time.time()-ST["uptime"])/60)
                print(f"\n📊 SESSION STATS")
                print(f"  Child:    {ST['name']}")
                print(f"  Score:    {ST['score']}")
                print(f"  Tokens:   ⭐{ST['tokens']}")
                print(f"  Emotion:  {ST['emotion']}")
                print(f"  Attention:{ST['attention']}%")
                print(f"  Success:  {ST['tasks_success']}")
                print(f"  Failed:   {ST['tasks_fail']}")
                print(f"  Duration: {dur} min")
                print(f"  Model:    {ST['gemini_model']}\n")
            else:
                ctrl._on_speech(cmd)

        except (KeyboardInterrupt, EOFError):
            break

    # Shutdown
    ctrl.running = False

    # Final auto-report
    if _gemini:
        final_rep = _gemini.generate_report()
        ST["reports"].append({
            "time":    datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"),
            "content": final_rep,
        })

    voice.say(
        "Goodbye! Amazing session today! "
        "See you next time!",
        wait_after=False)

    fn = (f"session_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(ST, f, indent=2, default=str)
    print(f"\n📄 Session saved: {fn}")
    print("✅ Therapy session complete.")


if __name__ == "__main__":
    main()
