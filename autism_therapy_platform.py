#!/usr/bin/env python3
"""
from robot_bridge import RobotBridge
╔══════════════════════════════════════════════════════════════════╗
║   ASD THERAPY PLATFORM v1.0 - PHASE 1 FOUNDATION               ║
║   Pepper + PyBullet + Gemini + DeepFace + Dashboard             ║
╚══════════════════════════════════════════════════════════════════╝

Architecture:
  ┌─────────────────────────────────────────────────────┐
  │  PERCEPTION LAYER                                   │
  │  Camera(300x300) → DeepFace → Emotion State         │
  │  Microphone(sensitivity=20) → Whisper → Intent      │
  └──────────────────┬──────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────┐
  │  BRAIN LAYER                                        │
  │  Gemini 1.5 + ABA/DTT/TEACCH/TIE Engine             │
  │  Token Economy + Prompt Hierarchy (P0→P3)           │
  └──────────────────┬──────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────┐
  │  ACTION LAYER                                       │
  │  PyBullet Pepper + Voice TTS + YouTube/Web          │
  └──────────────────┬──────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────┐
  │  DASHBOARD LAYER (Port 5007)                        │
  │  Charts + ISAA/IASQ + PDF + Parent Chatbot          │
  └─────────────────────────────────────────────────────┘
"""

# ============================================================
# IMPORTS
# ============================================================
import cv2, numpy as np, threading, time, random
import json, sys, os, math, re, warnings
import webbrowser, urllib.parse, queue
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import pyttsx3
import speech_recognition as sr
from flask import (Flask, request, jsonify,
                   render_template_string, send_file)
from datetime import datetime, timedelta
import pybullet as p
import pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')
import google.generativeai as genai

# ============================================================
# GEMINI CONFIG
# ============================================================
GEMINI_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_KEY)

THERAPY_SYSTEM = """You are Pepper, an expert pediatric robotic therapist for children with ASD.

CLINICAL EXPERTISE:
- ABA: Immediate reinforcement, token economy, behavior shaping
- DTT: Clear instructions, 5-second wait, error correction
- TEACCH: Visual schedules, structured environment
- TIE: Intensive short bursts, foundational skills

PERSONALITY: Warm, enthusiastic, patient, gentle, celebratory
SPEECH: Short (max 2 sentences). Simple words. Child's name often.
SPEED: Fast responses. No hesitation.

ACTION TOKENS (use in responses):
[WAVE] [CLAP] [NOD] [DANCE] [POINT] [HUG] [THINK] [CELEBRATE]

TRIGGERS:
[YOUTUBE: query] → open educational video
[GAME] → open game
[IMAGE: query] → open image search
[REWARD: stars] → give token reward (1-5 stars)

EMOTION PROTOCOL:
- happy+excited → [CELEBRATE] advance difficulty [REWARD:3]
- sad+tired → [HUG] easier task, comfort
- angry+frustrated → [NOD] breathe, pause
- scared+anxious → gentle voice, reassure
- neutral+distracted → [POINT] call name, redirect

SESSION TYPES respond to:
- EMOTION_GAME: teach/recognize emotions
- SOCIAL_SKILLS: greetings, sharing, help
- LIFE_SKILLS: daily tasks + YouTube
- PLAY: interactive games
- ROUTINE: TEACCH schedule

Always end with ONE clear task or question."""

PARENT_CHATBOT_SYSTEM = """You are an autism specialist supporting parents of children with ASD.
Answer ONLY autism-related questions.
Be warm, evidence-based, cite sources when possible.
Support Arabic and English.
Know child's data: {child_data}
Categories: behavior, communication, therapy, school, nutrition, sensory.
Keep answers practical and actionable."""

# ============================================================
# CONSTANTS
# ============================================================
YOUTUBE_BASE  = "https://www.youtube.com/results?search_query="
GOOGLE_IMG    = "https://www.google.com/search?tbm=isch&q="
DASHBOARD_PORT= 5007

SKILL_VIDEOS = {
    "wash face":   "how to wash face autism children",
    "brush teeth": "brush teeth autism kids song",
    "wash hands":  "wash hands song autism children",
    "get dressed": "getting dressed autism educational",
    "emotions":    "emotions learning autism children",
    "colors":      "learn colors autism kids",
    "numbers":     "count numbers autism children",
    "alphabet":    "alphabet learning autism",
    "sharing":     "sharing autism social skills",
    "greetings":   "saying hello autism children",
    "animals":     "animals for kids educational",
    "shapes":      "shapes learning autism kids",
    "toilet":      "toilet training autism step by step",
    "eating":      "eating healthy autism children",
}

IASQ_QUESTIONS = [
    {"q": "Does your child make eye contact?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child respond to their name?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child point to show interest?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child play with other children?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child use words to communicate?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child show repetitive behaviors?",
     "options": ["Always","Often","Sometimes","Rarely","Never"]},
    {"q": "Is your child sensitive to sounds?",
     "options": ["Extremely","Very","Somewhat","Slightly","Not at all"]},
    {"q": "Does your child have meltdowns?",
     "options": ["Daily","Weekly","Monthly","Rarely","Never"]},
    {"q": "Does your child follow simple instructions?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
    {"q": "Does your child show interest in others?",
     "options": ["Never","Rarely","Sometimes","Often","Always"]},
]

# ============================================================
# PLATFORM STATE
# ============================================================
PLATFORM = {
    # Child profile
    "child": {
        "name":          "Friend",
        "age":           6,
        "diagnosis":     "ASD Level 2",
        "sensitivities": ["sound", "touch"],
        "known":         False,
    },

    # Real-time perception
    "perception": {
        "emotion":        "neutral",
        "emotion_scores": {},
        "face_detected":  False,
        "attention":      70,
        "engagement":     "moderate",
        "gaze_direction": "center",
        "hand_gesture":   "none",
        "last_analyzed":  0,
    },

    # Session state
    "session": {
        "active":         False,
        "type":           "EMOTION_GAME",
        "protocol":       "GREETING",
        "start_time":     None,
        "duration_min":   10,
        "current_task":   None,
        "task_retries":   0,
        "task_success":   False,
        "prompt_level":   0,
        "difficulty":     "easy",
        "last_sound":     time.time(),
        "is_speaking":    False,
        "clap_detected":  False,
    },

    # Progress & rewards
    "progress": {
        "total_score":       0,
        "tokens":            0,     # token economy
        "stars_today":       0,
        "consecutive_ok":    0,
        "sessions_completed":0,
        "skills_data": {
            "emotions":      [],
            "social":        [],
            "motor":         [],
            "communication": [],
            "focus":         [],
        },
        "attention_history": [],
        "score_history":     [],
        "emotion_timeline":  [],
        "time_labels":       [],
    },

    # Assessment results
    "assessments": {
        "iasq_result":    None,
        "iasq_score":     0,
        "last_assessment": None,
    },

    # Logs & reports
    "logs":          [],
    "parent_notes":  [],
    "sim_cmd":       None,
    "gemini_ok":     False,
    "session_start": datetime.now().strftime("%H:%M"),
}

_log_lock = threading.Lock()

def plog(msg, log_type="info", protocol=None):
    """Platform logger - thread safe"""
    with _log_lock:
        entry = {
            "time":     datetime.now().strftime("%H:%M:%S"),
            "msg":      str(msg)[:120],
            "type":     log_type,
            "protocol": protocol or PLATFORM["session"]["protocol"],
            "emotion":  PLATFORM["perception"]["emotion"],
            "child":    PLATFORM["child"]["name"],
        }
        PLATFORM["logs"].append(entry)

        # Update history for charts (every 5 logs)
        if len(PLATFORM["logs"]) % 3 == 0:
            prog = PLATFORM["progress"]
            prog["attention_history"].append(
                PLATFORM["perception"]["attention"])
            prog["score_history"].append(
                prog["total_score"])
            prog["emotion_timeline"].append(
                PLATFORM["perception"]["emotion"])
            prog["time_labels"].append(
                datetime.now().strftime("%H:%M:%S"))
            # Keep last 60 points
            for k in ["attention_history","score_history",
                      "emotion_timeline","time_labels"]:
                if len(prog[k]) > 60:
                    prog[k] = prog[k][-60:]

        print(f"[{entry['time']}][{log_type.upper()}]"
              f"[{entry['protocol']}] {msg[:70]}")


# ============================================================
# GEMINI BRAIN
# ============================================================
class GeminiBrain:
    """Multi-model Gemini with context injection"""

    MODELS = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
        "gemini-pro",
    ]

    def __init__(self):
        self.ok         = False
        self.therapy_chat   = None
        self.parent_chat    = None
        self.model_name = "fallback"
        self._lock      = threading.Lock()

        for mn in self.MODELS:
            try:
                m = genai.GenerativeModel(
                    mn,
                    system_instruction=THERAPY_SYSTEM,
                    generation_config=genai.GenerationConfig(
                        temperature=0.75,
                        max_output_tokens=130,
                    ))
                c = m.start_chat(history=[])
                r = c.send_message("Respond: READY")
                self.therapy_model = m
                self.therapy_chat  = c
                self.model_name    = mn
                self.ok            = True
                PLATFORM["gemini_ok"] = True
                print(f"✅ Gemini: {mn}")
                break
            except Exception as e:
                print(f"⚠️  {mn}: {str(e)[:50]}")

        # Parent chatbot (separate chat)
        if self.ok:
            try:
                child = PLATFORM["child"]
                pm = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=PARENT_CHATBOT_SYSTEM.format(
                        child_data=json.dumps(child)),
                    generation_config=genai.GenerationConfig(
                        temperature=0.6,
                        max_output_tokens=300,
                    ))
                self.parent_chat = pm.start_chat(history=[])
            except Exception:
                pass

    def therapy(self, prompt):
        """Get therapy response"""
        if not self.ok:
            return self._fallback_therapy()
        ctx = self._build_ctx()
        with self._lock:
            try:
                resp = self.therapy_chat.send_message(
                    ctx + prompt)
                return resp.text.strip()
            except Exception as e:
                print(f"⚠️  therapy: {e}")
                try:
                    self.therapy_chat = \
                        self.therapy_model.start_chat(history=[])
                except: pass
                return self._fallback_therapy()

    def parent(self, question):
        """Parent chatbot response"""
        if not self.parent_chat:
            return ("I'm here to help with autism questions. "
                    "Please try again in a moment.")
        try:
            resp = self.parent_chat.send_message(question)
            return resp.text.strip()
        except Exception as e:
            return (f"I understand your question about "
                    f"'{question[:30]}...'. "
                    "Please consult your child's specialist "
                    "for personalized advice.")

    def _build_ctx(self):
        ch   = PLATFORM["child"]
        per  = PLATFORM["perception"]
        sess = PLATFORM["session"]
        prog = PLATFORM["progress"]
        return (
            f"[CONTEXT child={ch['name']} age={ch['age']} "
            f"diagnosis={ch['diagnosis']} "
            f"emotion={per['emotion']} "
            f"attention={per['attention']}% "
            f"engagement={per['engagement']} "
            f"protocol={sess['protocol']} "
            f"difficulty={sess['difficulty']} "
            f"score={prog['total_score']} "
            f"tokens={prog['tokens']} "
            f"streak={prog['consecutive_ok']}] "
        )

    def _fallback_therapy(self):
        name  = PLATFORM["child"]["name"]
        tasks = [
            f"Clap your hands {name}! 👏 [CLAP]",
            f"Touch your nose {name}! 👃",
            f"Wave to me {name}! 👋 [WAVE]",
            f"Show me happy face {name}! 😊",
            f"Stand up please {name}! 🧍",
            f"Can you count to three {name}?",
        ]
        return random.choice(tasks)


# ============================================================
# HIGH-ACCURACY EMOTION DETECTOR
# ============================================================
class EmotionEngine:
    """
    3-Layer detection:
    Layer 1: OpenCV Haar (fast, 300x300)
    Layer 2: Brightness/contrast analysis
    Layer 3: Movement detection (attention proxy)
    """

    EMO_MAPPING = {
        "smiling_wide":    "happy",
        "smiling_slight":  "happy",
        "neutral":         "neutral",
        "eyes_wide":       "surprise",
        "brows_down":      "angry",
        "mouth_down":      "sad",
        "eyes_narrow":     "fear",
    }

    def __init__(self):
        self.ok             = False
        self.face_cascade   = None
        self.smile_cascade  = None
        self.eye_cascade    = None
        self.prev_frame     = None
        self._win_lock      = threading.Lock()
        self._win_frame     = None
        self._analyze_lock  = threading.Lock()
        self._analyzing     = False

        try:
            cp = cv2.data.haarcascades
            self.face_cascade = cv2.CascadeClassifier(
                cp+'haarcascade_frontalface_default.xml')
            self.smile_cascade= cv2.CascadeClassifier(
                cp+'haarcascade_smile.xml')
            self.eye_cascade  = cv2.CascadeClassifier(
                cp+'haarcascade_eye.xml')
            if not self.face_cascade.empty():
                self.ok = True
                print("✅ EmotionEngine ready (300x300)")
        except Exception as e:
            print(f"⚠️  EmotionEngine: {e}")

        # Try DeepFace as upgrade
        self.deepface_ok = False
        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            # Quick warmup
            dummy = np.zeros((48,48,3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=['emotion'],
                enforce_detection=False, silent=True)
            self.deepface_ok = True
            print("✅ DeepFace upgrade active!")
        except Exception as e:
            print(f"⚠️  DeepFace: {e} (using OpenCV only)")

    def analyze_async(self, frame):
        """Non-blocking analysis"""
        if self._analyzing:
            return
        self._analyzing = True
        threading.Thread(
            target=self._do_analyze,
            args=(frame.copy(),),
            daemon=True).start()

    def _do_analyze(self, frame):
        try:
            scores = self._analyze_frame(frame)
            self._update_state(scores, frame)
        except Exception as e:
            pass
        finally:
            self._analyzing = False

    def _analyze_frame(self, frame):
        """Full analysis pipeline"""
        # Resize to 300x300
        small = cv2.resize(frame, (300, 300))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)

        scores    = {}
        faces_roi = []

        # === DeepFace (highest accuracy) ===
        if self.deepface_ok:
            try:
                result = self.DeepFace.analyze(
                    small,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True)
                if result:
                    raw   = result[0].get('emotion',{})
                    total = sum(raw.values()) or 1
                    scores= {k:v/total for k,v in raw.items()}
                    # Get face box
                    region = result[0].get('region',{})
                    if region:
                        faces_roi = [(
                            region.get('x',0),
                            region.get('y',0),
                            region.get('w',100),
                            region.get('h',100))]
                    self._update_window(
                        small, faces_roi, [], scores)
                    return scores
            except Exception:
                pass

        # === OpenCV fallback ===
        if not self.ok:
            return {"neutral": 1.0}

        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.05,
            minNeighbors=3, minSize=(20,20))

        if len(faces) == 0:
            return {"neutral": 0.8, "sad": 0.2}

        # Analyze largest face
        faces_sorted = sorted(faces,
            key=lambda f: f[2]*f[3], reverse=True)
        x,y,w,h = faces_sorted[0]
        roi      = gray[y:y+h, x:x+w]
        roi_c    = small[y:y+h, x:x+w]

        smiles = self.smile_cascade.detectMultiScale(
            roi, scaleFactor=1.5, minNeighbors=8,
            minSize=(15,15))
        eyes   = self.eye_cascade.detectMultiScale(
            roi, scaleFactor=1.1, minNeighbors=5,
            minSize=(10,10))

        n_smiles = len(smiles)
        n_eyes   = len(eyes)
        bright   = float(np.mean(roi))

        # Score calculation
        if n_smiles > 1:
            scores = {"happy":0.75,"neutral":0.15,
                      "surprise":0.10}
        elif n_smiles == 1:
            scores = {"happy":0.55,"neutral":0.30,
                      "surprise":0.15}
        elif n_eyes >= 2:
            if bright > 130:
                scores = {"neutral":0.50,"happy":0.25,
                          "surprise":0.15,"sad":0.10}
            else:
                scores = {"sad":0.45,"neutral":0.30,
                          "fear":0.15,"angry":0.10}
        elif n_eyes == 1:
            scores = {"neutral":0.40,"sad":0.30,
                      "fear":0.20,"angry":0.10}
        else:
            scores = {"angry":0.40,"disgust":0.25,
                      "sad":0.20,"neutral":0.15}

        # Motion analysis (attention proxy)
        if self.prev_frame is not None:
            diff  = cv2.absdiff(self.prev_frame, gray)
            motion= float(np.mean(diff))
            if motion > 15:
                # Active child → more attention
                PLATFORM["perception"]["attention"] = min(
                    100,
                    PLATFORM["perception"]["attention"]+3)
            elif motion < 2:
                # Very still → possibly distracted
                PLATFORM["perception"]["attention"] = max(
                    0,
                    PLATFORM["perception"]["attention"]-1)

        self.prev_frame = gray.copy()

        self._update_window(small, faces_sorted[:1],
                            eyes, scores)
        return scores

    def _update_state(self, scores, frame):
        if not scores: return
        dominant = max(scores, key=scores.get)
        old      = PLATFORM["perception"]["emotion"]

        PLATFORM["perception"]["emotion"]        = dominant
        PLATFORM["perception"]["emotion_scores"] = scores
        PLATFORM["perception"]["face_detected"]  = True
        PLATFORM["perception"]["last_analyzed"]  = time.time()

        pos = scores.get("happy",0)+scores.get("surprise",0)
        neg = scores.get("sad",0)+scores.get("angry",0)+\
              scores.get("fear",0)
        if pos>0.5:   PLATFORM["perception"]["engagement"]="high"
        elif neg>0.5: PLATFORM["perception"]["engagement"]="distressed"
        else:         PLATFORM["perception"]["engagement"]="moderate"

        # Attention boost when face detected
        PLATFORM["perception"]["attention"] = min(
            100, PLATFORM["perception"]["attention"]+2)

    def _update_window(self, frame, faces, eyes, scores):
        """Build 300x300 display"""
        disp = frame.copy()
        em   = PLATFORM["perception"]["emotion"]

        EMO_COLORS = {
            "happy":(0,220,80),"sad":(100,100,220),
            "angry":(0,0,220),"fear":(0,180,220),
            "surprise":(200,50,220),"disgust":(0,180,100),
            "neutral":(180,180,180),
        }
        col = EMO_COLORS.get(em,(180,180,180))

        for (x,y,w,h) in faces:
            cv2.rectangle(disp,(x,y),(x+w,y+h),col,2)
            cv2.putText(disp,em.upper(),
                (x,max(0,y-8)),
                cv2.FONT_HERSHEY_SIMPLEX,0.55,col,2)

        # Score bars
        for i,(e,s) in enumerate(
                sorted(scores.items(),key=lambda x:-x[1])[:7]):
            y2  = 8+i*26
            bl  = int(s*130)
            c2  = EMO_COLORS.get(e,(150,150,150))
            cv2.rectangle(disp,(3,y2),(3+bl,y2+18),c2,-1)
            cv2.rectangle(disp,(3,y2),(133,y2+18),(40,40,40),1)
            cv2.putText(disp,f"{e[:5]}:{s:.0%}",
                (5,y2+13),cv2.FONT_HERSHEY_SIMPLEX,
                0.32,(255,255,255),1)

        # Header
        cv2.rectangle(disp,(0,0),(300,20),(0,0,0),-1)
        cv2.putText(disp,
            f"EMOTION 300x300 | Att:{PLATFORM['perception']['attention']}%",
            (3,14),cv2.FONT_HERSHEY_SIMPLEX,
            0.33,(0,200,255),1)

        # Bottom attention bar
        att = PLATFORM["perception"]["attention"]
        bw  = int(att/100*298)
        cv2.rectangle(disp,(0,283),(298,299),(20,20,40),-1)
        cv2.rectangle(disp,(0,283),(bw,299),col,-1)

        with self._win_lock:
            self._win_frame = disp.copy()

    def get_window(self):
        with self._win_lock:
            if self._win_frame is not None:
                return self._win_frame.copy()
        return None

    def no_face(self):
        PLATFORM["perception"]["face_detected"] = False
        PLATFORM["perception"]["attention"] = max(
            0, PLATFORM["perception"]["attention"]-3)


# ============================================================
# CAMERA MANAGER
# ============================================================
class CameraEngine:
    def __init__(self):
        self.cap  = None
        self.idx  = -1
        self._lk  = threading.Lock()
        self._frm = None

        for i in [1,0,2,3]:
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, f = cap.read()
                    if ret and f is not None and f.size>0:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                        self.cap = cap
                        self.idx = i
                        print(f"✅ Camera index {i}")
                        return
                    cap.release()
            except: pass
        print("⚠️  No camera - simulation mode")

    def read(self):
        if not self.cap:
            return False, None
        ret,frame = self.cap.read()
        if ret and frame is not None:
            frame = cv2.flip(frame,1)
            with self._lk: self._frm = frame.copy()
            return True, frame
        return False, None

    def latest(self):
        with self._lk:
            return self._frm.copy() if self._frm is not None \
                   else None


# ============================================================
# VOICE ENGINE
# ============================================================
class VoiceEngine:
    def __init__(self):
        self.ok   = False
        self._lk  = threading.Lock()
        try:
            self.e = pyttsx3.init()
            self.e.setProperty('rate', 125)
            self.e.setProperty('volume', 1.0)
            for v in self.e.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','karen']):
                    self.e.setProperty('voice',v.id)
                    break
            self.ok = True
            print("✅ Voice ready (125 wpm, warm)")
        except Exception as e:
            print(f"⚠️  Voice: {e}")

    def say(self, text):
        name = PLATFORM["child"]["name"] or "Friend"
        text = str(text).replace("{name}",name)
        # Clean tokens
        for t in ["[WAVE]","[CLAP]","[NOD]","[DANCE]",
                  "[POINT]","[HUG]","[THINK]","[CELEBRATE]",
                  "[GAME]"]:
            text = text.replace(t,"")
        text = re.sub(r'\[YOUTUBE:[^\]]+\]','',text)
        text = re.sub(r'\[IMAGE:[^\]]+\]','',text)
        text = re.sub(r'\[REWARD:\d+\]','',text)
        text = text.strip()
        if not text: return

        PLATFORM["session"]["is_speaking"] = True
        print(f"\n🔊 Pepper: {text}")
        plog(f"Said: {text[:60]}")

        if self.ok:
            with self._lk:
                try:
                    self.e.say(text)
                    self.e.runAndWait()
                except: pass
        PLATFORM["session"]["is_speaking"] = False


# ============================================================
# MICROPHONE (energy=20 MAX SENSITIVITY)
# ============================================================
class MicEngine:
    def __init__(self):
        self.ok      = False
        self.running = False
        try:
            self.r = sr.Recognizer()
            # MAX SENSITIVITY
            self.r.energy_threshold               = 20
            self.r.dynamic_energy_threshold       = True
            self.r.dynamic_energy_adjustment_ratio= 1.5
            self.r.pause_threshold                = 0.4
            self.r.phrase_threshold               = 0.1
            self.r.non_speaking_duration          = 0.1
            self.ok = True
            print("✅ Mic (energy=20, MAX sensitivity)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen(self, timeout=5):
        if not self.ok:
            return input("👶 Type: ").strip()
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, 0.15)
                audio = self.r.listen(
                    src, timeout=timeout,
                    phrase_time_limit=15)
            try:
                text = self.r.recognize_google(audio)
                PLATFORM["session"]["last_sound"] = time.time()
                plog(f"Heard: {text}")
                return text
            except sr.UnknownValueError:
                self._clap(audio)
                PLATFORM["session"]["last_sound"] = time.time()
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
                audio.get_raw_data(), np.int16)
            rms = float(np.sqrt(np.mean(
                raw.astype(np.float64)**2)))
            if rms > 1000:
                PLATFORM["session"]["clap_detected"] = True
                plog("👏 Clap!", "success")
        except: pass

    def get_name(self, voice):
        if PLATFORM["child"]["known"]:
            return PLATFORM["child"]["name"]
        voice.say("Hello! I am Pepper! What is your name?")
        for _ in range(3):
            r = self.listen(8)
            if r and r not in ["[sound]",""]:
                n = self._extract(r)
                if n:
                    PLATFORM["child"]["name"]  = n
                    PLATFORM["child"]["known"] = True
                    plog(f"Name: {n}", "success")
                    return n
        PLATFORM["child"]["name"]  = "Friend"
        PLATFORM["child"]["known"] = True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm","call me",
                   "name is"]:
            t = t.replace(rm,"").strip()
        w = t.split()
        return w[0].capitalize() if w else None

    def listen_bg(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if PLATFORM["session"]["is_speaking"]:
                    time.sleep(0.2); continue
                text = self.listen(4)
                if text:
                    try: callback(text)
                    except Exception as e:
                        print(f"⚠️  cb: {e}")
                time.sleep(0.05)
        threading.Thread(target=_loop, daemon=True).start()


# ============================================================
# ACTION ENGINE (Token → PyBullet Movement)
# ============================================================
class ActionEngine:
    def __init__(self, pepper=None):
        from robot_bridge import RobotBridge
        self.robot = RobotBridge()
        self.pepper = pepper
        self._reward_queue = []

    def process(self, text):
        """Process all tokens in text"""
        clean = text

        TOKEN_MAP = {
            "[WAVE]":      self._wave,
            "[CLAP]":      self._clap,
            "[NOD]":       self._nod,
            "[DANCE]":     self._dance,
            "[POINT]":     self._point,
            "[HUG]":       self._hug,
            "[THINK]":     self._think,
            "[CELEBRATE]": self._celebrate,
        }

        for tok, fn in TOKEN_MAP.items():
            if tok in text:
                clean = clean.replace(tok,"")
                threading.Thread(
                    target=fn, daemon=True).start()

        # YouTube
        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt:
            clean = clean.replace(yt.group(0),"")
            q = yt.group(1).strip()
            url = YOUTUBE_BASE + urllib.parse.quote(
                q+" autism children educational")
            webbrowser.open(url)
            plog(f"📺 YouTube: {q}")

        # Image
        img = re.search(r'\[IMAGE:\s*(.+?)\]', text)
        if img:
            clean = clean.replace(img.group(0),"")
            webbrowser.open(GOOGLE_IMG +
                urllib.parse.quote(img.group(1)))

        # Reward
        rew = re.search(r'\[REWARD:(\d+)\]', text)
        if rew:
            clean = clean.replace(rew.group(0),"")
            stars = int(rew.group(1))
            PLATFORM["progress"]["tokens"] += stars
            PLATFORM["progress"]["stars_today"] += stars
            plog(f"⭐ Reward: {stars} stars",
                 "success")

        # Game
        if "[GAME]" in text:
            clean = clean.replace("[GAME]","")
            webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")

        return clean.strip()

    def _sa(self, j, a, s=0.15):
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
            self._sa("RShoulderPitch",0.8,0.25)
            time.sleep(0.18)
            self._sa("LShoulderPitch",1.1,0.25)
            self._sa("RShoulderPitch",1.1,0.25)
            time.sleep(0.18)

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
        self._sa("LElbowYaw",-1.5,0.15)
        time.sleep(1.0)
        self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        self._sa("LShoulderPitch",0.5,0.1)
        self._sa("RShoulderPitch",0.5,0.1)
        self._sa("LShoulderRoll",0.35,0.1)
        self._sa("RShoulderRoll",-0.35,0.1)
        time.sleep(1.5)
        self._sa("LShoulderPitch",1.0,0.1)
        self._sa("RShoulderPitch",1.0,0.1)
        self._sa("LShoulderRoll",0.0,0.1)
        self._sa("RShoulderRoll",0.0,0.1)

    def _think(self):
        self._sa("HeadYaw",0.35,0.1)
        self._sa("HeadPitch",-0.15,0.1)
        time.sleep(1.8)
        self._sa("HeadYaw",0.0,0.1)
        self._sa("HeadPitch",0.0,0.1)

    def _celebrate(self):
        for _ in range(3):
            self._sa("LShoulderPitch",0.05,0.25)
            self._sa("RShoulderPitch",0.05,0.25)
            self._sa("HeadPitch",-0.2,0.2)
            time.sleep(0.25)
            self._sa("LShoulderPitch",1.0,0.25)
            self._sa("RShoulderPitch",1.0,0.25)
            self._sa("HeadPitch",0.0,0.2)
            time.sleep(0.25)


# ============================================================
# PYBULLET SIMULATION
# ============================================================
class PepperSim:
    def __init__(self):
        self.pepper    = None
        self.ok        = False
        self.rx = self.ry = 0.0
        self.auto_walk = True
        self.balloons  = []

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim  = QS()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0, 0, -9.81)
            p.setAdditionalSearchPath(
                pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._build_room()
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand", 0.5)
            self._create_balloons()
            self._create_therapy_kids()
            p.resetDebugVisualizerCamera(
                7, 45, -35, [0, 0, 0.5])
            self.ok = True

            for fn in [self._sim_loop,
                       self._walk_loop,
                       self._arm_loop]:
                threading.Thread(
                    target=fn, daemon=True).start()

            print("✅ PyBullet therapy room ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _build_room(self):
        wc = [0.88, 0.88, 0.92, 1]
        # Walls
        for pos, ext in [
            ([0,-4,1.1],[5,.1,1.1]),([0,4,1.1],[5,.1,1.1]),
            ([5,0,1.1],[.1,4,1.1]),([-5,0,1.1],[.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=ext,rgbaColor=wc),pos)
        # Floor
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,.02],
                rgbaColor=[.55,.45,.35,1]),[0,0,.01])

        # Session zone labels
        labels = [
            ("🎭 EMOTION", [-3.5, 3, 2.0]),
            ("📚 DTT ROOM", [3.5, 3, 2.0]),
            ("📅 TEACCH",  [0, 3.8, 2.0]),
            ("🎮 PLAY",    [-3.5,-3, 2.0]),
            ("🏃 ROUTINE", [3.5,-3, 2.0]),
        ]
        for txt, pos in labels:
            p.addUserDebugText(txt, pos,
                [0.3,0.5,0.9], textSize=1.0, lifeTime=0)

        # Reward board
        p.addUserDebugText(
            "⭐ REWARD BOARD",
            [0, 0, 2.8],
            [1.0, 0.8, 0.0],
            textSize=1.5, lifeTime=0)

    def _create_balloons(self):
        cols = [[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
                [1,1,.2,1],[1,.5,.2,1],[.8,.2,.8,1],
                [.2,.8,.8,1],[.8,.2,.8,1]]
        for i in range(8):
            vs = p.createVisualShape(p.GEOM_SPHERE,
                radius=.15, rgbaColor=cols[i%len(cols)])
            bid= p.createMultiBody(0,-1,vs,
                [random.uniform(-3,3),
                 random.uniform(-2,2),
                 random.uniform(.8,2.2)])
            self.balloons.append({
                "id":bid,
                "x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

    def _create_therapy_kids(self):
        kids = [
            ("Ahmed", [1.5,-1.2,0], [.2,.85,.2,1], "mild"),
            ("Sara",  [-1.2,1.3,0], [1.,.6,.0,1],  "moderate"),
            ("Yusuf", [.5,-2.,0],   [.9,.15,.15,1], "severe"),
        ]
        for nm,pos,col,sev in kids:
            # Body
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_BOX,
                    halfExtents=[.13,.09,.21],
                    rgbaColor=col),
                [pos[0],pos[1],.41])
            # Head
            p.createMultiBody(0,-1,
                p.createVisualShape(p.GEOM_SPHERE,
                    radius=.11,
                    rgbaColor=[1.,.82,.65,1.]),
                [pos[0],pos[1],.74])
            # Label
            em = {"mild":"🟢","moderate":"🟠","severe":"🔴"}
            p.addUserDebugText(
                f"{nm}{em[sev]}",
                [pos[0],pos[1],1.05],
                [0,0,0], textSize=.85, lifeTime=0)

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            for b in self.balloons:
                b["z"] += b["spd"]
                if b["z"] > 2.8:
                    b["z"]  = .6
                    b["x"]  = random.uniform(-3,3)
                    b["y"]  = random.uniform(-2,2)
                try:
                    p.resetBasePositionAndOrientation(
                        b["id"],
                        [b["x"],b["y"],b["z"]],
                        [0,0,0,1])
                except: pass
            time.sleep(1/240.)

    def _walk_loop(self):
        t = 0
        while True:
            if self.auto_walk:
                t += .015
                self.rx += .018 * math.cos(t*.4)
                self.ry += .018 * math.sin(t*.5)
                self.rx = max(-3.5, min(3.5, self.rx))
                self.ry = max(-2.8, min(2.8, self.ry))
                try:
                    self.pepper.setPosition(
                        [self.rx,self.ry,.8])
                except: pass
            time.sleep(.06)

    def _arm_loop(self):
        ph = 0
        while True:
            try:
                if PLATFORM["session"]["is_speaking"]:
                    ph += .07
                    L = .5 + .3 * math.sin(ph)
                    R = .5 + .3 * math.sin(ph+math.pi*.6)
                    self.pepper.setAngles(
                        "LShoulderPitch",L,.07)
                    self.pepper.setAngles(
                        "RShoulderPitch",R,.07)
                    # Head tilts toward child
                    self.pepper.setAngles(
                        "HeadPitch",-0.05,.05)
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
            pos = p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],
                [pos[0],pos[1],pos[2]+1.35],
                [0,0,0], textSize=.85, lifeTime=5)
        except: pass


# ============================================================
# VIDEO DISPLAY ENGINE
# ============================================================
class DisplayEngine:
    def __init__(self, em_engine, cam):
        self.em      = em_engine
        self.cam     = cam
        self.running = False
        self.task_text    = ""
        self.task_t       = 0
        self.praise_text  = ""
        self.praise_t     = 0
        self.ai_text      = ""
        self.ai_t         = 0
        self.last_em_t    = 0
        self.avatar       = self._make_avatar()
        self._stars_t     = 0
        self._stars_n     = 0

        self.running = True
        threading.Thread(
            target=self._run, daemon=True).start()
        print("✅ Display engine started!")

    def _make_avatar(self):
        img = np.zeros((235,175,3), dtype=np.uint8)
        img[:] = (10,15,38)
        # Glow
        cv2.circle(img,(87,57),48,(20,40,90),-1)
        # Head
        cv2.circle(img,(87,57),42,(220,195,173),-1)
        # Eyes
        for ex in [71,103]:
            cv2.circle(img,(ex,49),10,(0,140,255),-1)
            cv2.circle(img,(ex,49),5,(220,240,255),-1)
            cv2.circle(img,(ex+1,48),3,(0,0,0),-1)
        # Nose
        cv2.circle(img,(87,62),2,(170,140,130),-1)
        # Mouth
        cv2.ellipse(img,(87,71),(14,7),0,0,180,(70,35,35),2)
        # Body
        cv2.rectangle(img,(57,100),(117,180),(120,135,190),-1)
        cv2.rectangle(img,(59,103),(115,177),(95,110,165),1)
        # Arms
        cv2.rectangle(img,(20,103),(57,138),(120,135,190),-1)
        cv2.rectangle(img,(117,103),(154,138),(120,135,190),-1)
        # Pepper label
        cv2.putText(img,"PEPPER",(26,203),
            cv2.FONT_HERSHEY_SIMPLEX,0.62,(80,180,255),2)
        cv2.putText(img,"Gemini AI",(24,218),
            cv2.FONT_HERSHEY_SIMPLEX,0.35,(150,220,255),1)
        return img

    def _run(self):
        no_cam  = self.cam.idx < 0
        last_em = 0

        while self.running:
            try:
                # Get frame
                if no_cam:
                    frame = self._sim_frame()
                else:
                    ret, f = self.cam.read()
                    frame  = f if ret else self._sim_frame()

                # Emotion analysis
                now = time.time()
                if now - last_em > 0.7 and not no_cam:
                    last_em = now
                    self.em.analyze_async(frame.copy())
                elif no_cam:
                    # Simulate gradual emotion change
                    if now - last_em > 5:
                        last_em = now
                        em_pool = ["happy","neutral",
                                   "happy","neutral","sad"]
                        PLATFORM["perception"]["emotion"] = \
                            random.choice(em_pool)

                # Build UI
                ui = self._build_ui(frame)
                cv2.imshow("Pepper ASD Therapy Platform",ui)

                # Emotion window
                ew = self.em.get_window()
                if ew is not None:
                    cv2.imshow("Emotion Analysis (300x300)", ew)

                key = cv2.waitKey(1) & 0xFF
                if key in [ord('q'),ord('Q'),27]:
                    self.running = False
                    break

            except Exception as e:
                print(f"⚠️  display: {e}")
                time.sleep(0.1)

            time.sleep(0.018)

        try: cv2.destroyAllWindows()
        except: pass

    def _sim_frame(self):
        h,w = 720,1280
        f   = np.zeros((h,w,3),dtype=np.uint8)
        f[:] = (7,10,25)
        t   = time.time()
        # Animated grid
        for i in range(0,w,80):
            cv2.line(f,(i,0),(i,h),(15,22,50),1)
        for i in range(0,h,80):
            cv2.line(f,(0,i),(w,i),(15,22,50),1)
        # Animated circle
        r   = int(40+15*math.sin(t*1.5))
        col = (int(50+50*math.sin(t)),
               int(100+100*math.cos(t*0.7)),220)
        cv2.circle(f,(w//2,h//2-80),r,col,3)
        # Pulsing rings
        for ri in range(1,4):
            rv  = int(40+ri*30+10*math.sin(t+ri))
            alp = max(0,int(200-ri*60))
            cv2.circle(f,(w//2,h//2-80),rv,
                (col[0]//2,col[1]//2,col[2]//2),1)

        cv2.putText(f,"SIMULATION MODE",
            (w//2-120,h//2+20),
            cv2.FONT_HERSHEY_SIMPLEX,0.9,(100,150,255),2)
        cv2.putText(f,"Therapy running via microphone + PyBullet",
            (w//2-195,h//2+55),
            cv2.FONT_HERSHEY_SIMPLEX,0.5,(70,100,200),1)
        return f

    def _build_ui(self, frame):
        h,w = frame.shape[:2]
        ui  = frame.copy()

        # === Header ===
        ov = ui.copy()
        cv2.rectangle(ov,(0,0),(w,82),(6,10,25),-1)
        ui = cv2.addWeighted(ov,0.85,ui,0.15,0)

        nm  = PLATFORM["child"]["name"]
        prt = PLATFORM["session"]["protocol"]
        sc  = PLATFORM["progress"]["total_score"]
        tk  = PLATFORM["progress"]["tokens"]
        dif = PLATFORM["session"]["difficulty"].upper()
        gem = "✅" if PLATFORM["gemini_ok"] else "⚠️"

        cv2.putText(ui,
            f"Pepper ASD Therapy  {gem} Gemini  Port:{DASHBOARD_PORT}",
            (15,30),cv2.FONT_HERSHEY_SIMPLEX,0.78,
            (255,255,255),2)
        cv2.putText(ui,
            f"Child:{nm}  {prt}  Score:{sc}  "
            f"Tokens:⭐{tk}  Level:{dif}",
            (15,60),cv2.FONT_HERSHEY_SIMPLEX,
            0.48,(140,190,255),1)

        # === Pepper Avatar PIP ===
        av   = self.avatar.copy()
        ah,aw= av.shape[:2]

        if PLATFORM["session"]["is_speaking"]:
            t  = int(time.time()*7)%4
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                (0,160+t*18,255),2+t//2)
            off = int(4*math.sin(time.time()*12))
            cv2.ellipse(av,(87,71+off),(14,7+off),
                0,0,180,(70,35,35),2)

        x1 = w-aw-12; y1 = h-ah-92
        ui[y1-3:y1+ah+3,x1-3:x1+aw+3] = (10,15,38)
        ui[y1:y1+ah,x1:x1+aw] = av
        bc = (0,200,255) if PLATFORM["session"]["is_speaking"] \
             else (40,40,80)
        cv2.rectangle(ui,(x1-3,y1-3),
            (x1+aw+3,y1+ah+3),bc,2)

        # === Bottom bar ===
        ov2 = ui.copy()
        cv2.rectangle(ov2,(0,h-95),(w,h),(6,10,25),-1)
        ui  = cv2.addWeighted(ov2,0.80,ui,0.20,0)

        em  = PLATFORM["perception"]["emotion"]
        EC  = {
            "happy":(0,220,80),"sad":(100,100,220),
            "angry":(0,0,220),"fear":(0,180,220),
            "surprise":(200,50,220),"disgust":(0,180,100),
            "neutral":(180,180,180),
        }
        ec  = EC.get(em,(180,180,180))
        att = PLATFORM["perception"]["attention"]

        cv2.putText(ui,f"Emotion: {em.upper()}",
            (15,h-62),cv2.FONT_HERSHEY_SIMPLEX,
            0.78,ec,2)
        # Attention bar
        bw = int(att/100*(w-200))
        cv2.rectangle(ui,(15,h-46),(w-185,h-35),
            (25,28,55),-1)
        cv2.rectangle(ui,(15,h-46),(15+bw,h-35),ec,-1)
        cv2.putText(ui,
            f"Attention:{att}%  "
            f"Engagement:{PLATFORM['perception']['engagement']}  "
            f"Streak:{PLATFORM['progress']['consecutive_ok']}",
            (15,h-15),cv2.FONT_HERSHEY_SIMPLEX,
            0.46,(255,230,100),1)

        # Prompt level
        pl  = PLATFORM["session"]["prompt_level"]
        plc = [(0,200,0),(200,200,0),
               (200,100,0),(200,0,0)][min(pl,3)]
        cv2.circle(ui,(w-48,h-55),22,plc,-1)
        cv2.putText(ui,f"P{pl}",
            (w-57,h-47),cv2.FONT_HERSHEY_SIMPLEX,
            0.65,(255,255,255),2)

        # Face dot
        fdc = (0,255,0) if \
            PLATFORM["perception"]["face_detected"] \
            else (0,0,255)
        cv2.circle(ui,(w-12,18),7,fdc,-1)

        # Token stars display
        stars = PLATFORM["progress"]["stars_today"]
        if stars > 0:
            star_str = "⭐"*min(stars,10)
            cv2.putText(ui,star_str,
                (15,h-108),
                cv2.FONT_HERSHEY_SIMPLEX,0.5,
                (255,200,0),1)

        # Task display
        now = time.time()
        if self.task_text and now-self.task_t < 8:
            tl  = min(len(self.task_text)*14, w-60)
            tx  = max(10, w//2-tl//2)
            cv2.rectangle(ui,(tx-6,h//2-44),
                (tx+tl+6,h//2+10),(12,45,110),-1)
            cv2.rectangle(ui,(tx-6,h//2-44),
                (tx+tl+6,h//2+10),(0,140,255),2)
            cv2.putText(ui,self.task_text[:55],
                (tx,h//2-12),
                cv2.FONT_HERSHEY_SIMPLEX,0.70,
                (255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_t < 4:
            pl2 = min(len(self.praise_text)*17, w-60)
            px  = max(10, w//2-pl2//2)
            cv2.rectangle(ui,(px-6,h//2+28),
                (px+pl2+6,h//2+78),(0,65,0),-1)
            cv2.putText(ui,self.praise_text[:38],
                (px,h//2+62),
                cv2.FONT_HERSHEY_SIMPLEX,0.92,
                (0,255,100),2)

        # AI text preview
        if self.ai_text and now-self.ai_t < 5:
            lines = [self.ai_text[i:i+65]
                     for i in range(0,
                     min(len(self.ai_text),130),65)]
            for li,line in enumerate(lines[:2]):
                cv2.putText(ui,line,
                    (15,h-115-li*22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,(200,255,200),1)

        # REC
        cv2.circle(ui,(36,26),8,(0,0,220),-1)
        cv2.putText(ui,"REC",(48,33),
            cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,0,220),1)

        # Clap flash
        if PLATFORM["session"]["clap_detected"]:
            cv2.putText(ui,"👏 CLAP!",
                (w//2-80,88),
                cv2.FONT_HERSHEY_SIMPLEX,1.2,
                (0,255,100),3)

        return ui

    def show_task(self, t):
        self.task_text = t; self.task_t = time.time()
    def show_praise(self, t):
        self.praise_text = t; self.praise_t = time.time()
    def show_ai(self, t):
        self.ai_text = t[:130]; self.ai_t = time.time()
    def stop(self):
        self.running = False
        time.sleep(0.3)
        try: cv2.destroyAllWindows()
        except: pass


# ============================================================
# DASHBOARD (Flask Port 5007)
# ============================================================
dash_app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 ASD Therapy Platform - Parent Dashboard</title>
<meta http-equiv="refresh" content="4">
<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#060912;--card:#0c0f1e;--border:#1a1f40;
  --purple:#a78bfa;--blue:#60a5fa;--green:#34d399;
  --red:#f87171;--yellow:#fbbf24;--orange:#fb923c;
  --text:#e0e6ff;--muted:#6b7280;
}
body{font-family:'Segoe UI',system-ui,sans-serif;
     background:var(--bg);color:var(--text);font-size:14px}

/* HEADER */
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d,#0a2040);
     padding:14px 24px;display:flex;align-items:center;
     gap:12px;border-bottom:2px solid #4f46e5;
     position:sticky;top:0;z-index:100}
.hdr h1{font-size:1.18em;color:var(--purple)}
.badge{padding:2px 9px;border-radius:12px;font-size:.68em;
       font-weight:700}
.live{background:#ef4444;color:#fff;
      animation:blink 1s infinite}
.gem-ok{background:#1a2555;color:var(--blue);
        border:1px solid var(--blue)}
.gem-off{background:#2a1515;color:var(--red);
         border:1px solid var(--red)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* LAYOUT */
.main{max-width:1400px;margin:0 auto;padding:14px;
      display:flex;flex-direction:column;gap:12px}
.row{display:grid;gap:12px}
.r3{grid-template-columns:1fr 1fr 1fr}
.r2{grid-template-columns:1fr 1fr}
.r4{grid-template-columns:repeat(4,1fr)}
.r5{grid-template-columns:repeat(5,1fr)}

/* CARDS */
.card{background:var(--card);border-radius:12px;
      padding:14px;border:1px solid var(--border)}
.card h2{font-size:.82em;color:#818cf8;
         border-bottom:1px solid var(--border);
         padding-bottom:6px;margin-bottom:10px;
         display:flex;align-items:center;gap:6px}

/* STAT CARDS */
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:10px;
      padding:13px;text-align:center;cursor:default}
.stat:hover{border-color:var(--purple);
            transform:translateY(-1px);transition:.2s}
.n{font-size:1.85em;font-weight:700;color:var(--purple)}
.l{font-size:.69em;color:var(--muted);margin-top:2px}
.n-g{color:var(--green)}
.n-b{color:var(--blue)}
.n-y{color:var(--yellow)}
.n-r{color:var(--red)}

/* EMOTION */
.emo{display:inline-block;padding:6px 16px;
     border-radius:18px;font-weight:700;font-size:1.05em}
.happy{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprise{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.disgust{background:#0a291555;color:#6ee7b7;border:1px solid #6ee7b7}

/* BAR */
.bar-bg{background:#1f2937;border-radius:6px;height:9px;margin:5px 0}
.bar-fill{height:9px;border-radius:6px;
          background:linear-gradient(90deg,#6366f1,#a78bfa)}

/* BUTTONS */
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:7px 13px;border-radius:7px;
     cursor:pointer;font-size:.76em;margin:3px;transition:.2s;
     font-family:inherit}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.btn-g{background:linear-gradient(135deg,#059669,#10b981)}
.btn-y{background:linear-gradient(135deg,#d97706,#f59e0b)}
.btn-r{background:linear-gradient(135deg,#dc2626,#ef4444)}
.btn-b{background:linear-gradient(135deg,#1d4ed8,#3b82f6)}

/* PROTOCOL BADGES */
.prot{display:inline-block;padding:2px 7px;border-radius:8px;
      font-size:.68em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}

/* INPUTS */
input,textarea,select{
  width:100%;padding:7px 10px;border-radius:7px;
  border:1px solid var(--border);background:#07090f;
  color:var(--text);font-size:.79em;font-family:inherit;
  outline:none;transition:.2s}
input:focus,textarea:focus,select:focus{
  border-color:var(--purple)}
textarea{resize:vertical;min-height:65px}

/* LOG */
.log-box{max-height:260px;overflow-y:auto;
         scrollbar-width:thin;
         scrollbar-color:#4f46e5 #0c0f1e}
.log-item{padding:5px 8px;margin:2px 0;border-radius:5px;
          font-size:.73em;border-left:3px solid #4f46e5;
          background:#07090f;line-height:1.45}
.log-item.success{border-color:var(--green)}
.log-item.fail{border-color:var(--red)}
.log-item.info{border-color:var(--blue)}

/* CHART */
.chart-wrap{position:relative;height:175px;
            background:#07090f;border-radius:8px;padding:8px}

/* CHAT */
.chat-box{height:195px;overflow-y:auto;background:#07090f;
          border-radius:8px;padding:10px;margin-bottom:8px;
          scrollbar-width:thin}
.chat-msg{padding:7px 11px;margin:4px 0;
          border-radius:9px;font-size:.79em;line-height:1.5}
.chat-p{background:#1e1b4b;border-left:3px solid var(--purple)}
.chat-c{background:#052918;border-left:3px solid var(--green)}
.chat-par{background:#1a1f40;border-left:3px solid var(--blue)}

/* NOTES */
.note-item{background:#0a1020;border-left:3px solid var(--purple);
           padding:8px 10px;margin:4px 0;border-radius:0 7px 7px 0;
           font-size:.74em;line-height:1.5}

/* HELP */
.help-card{background:#0a1020;border-radius:9px;padding:11px;
           border-left:4px solid var(--purple)}
.help-title{color:var(--purple);font-weight:700;
            font-size:.8em;margin-bottom:5px}
.help-body{color:#9ca3af;font-size:.74em;line-height:1.6}
.tip-box{background:#051a0f;border:1px solid var(--green);
         border-radius:6px;padding:7px;margin-top:6px;
         font-size:.72em;color:#6ee7b7}

/* ASSESSMENT */
.q-card{background:#0a1020;border-radius:9px;
        padding:12px;margin:6px 0;
        border:1px solid var(--border)}
.q-text{font-size:.8em;color:var(--text);margin-bottom:8px}
.q-opts{display:flex;gap:5px;flex-wrap:wrap}
.q-opt{background:#1f2937;color:#9ca3af;border:none;
       padding:5px 9px;border-radius:6px;cursor:pointer;
       font-size:.72em;transition:.2s}
.q-opt:hover{background:#4f46e5;color:#fff}
.q-opt.selected{background:#4f46e5;color:#fff}

/* RADAR CHART */
.skills-grid{display:grid;grid-template-columns:repeat(5,1fr);
             gap:8px;margin:8px 0}
.skill-item{text-align:center;padding:8px 4px}
.skill-bar{height:80px;background:#1f2937;border-radius:6px;
           position:relative;overflow:hidden}
.skill-fill{position:absolute;bottom:0;width:100%;
            background:linear-gradient(0deg,#6366f1,#a78bfa);
            border-radius:6px;transition:.5s}
.skill-name{font-size:.65em;color:#9ca3af;margin-top:5px}
.skill-val{font-size:.72em;color:var(--purple);font-weight:700}

/* TABS */
.tabs{display:flex;gap:6px;margin-bottom:12px;
      flex-wrap:wrap}
.tab{padding:6px 14px;border-radius:8px;cursor:pointer;
     font-size:.78em;background:#1f2937;color:#9ca3af;
     border:1px solid var(--border);transition:.2s}
.tab.active,.tab:hover{background:#4f46e5;color:#fff}
.tab-content{display:none}
.tab-content.active{display:block}

/* SCROLL */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0c0f1e}
::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:5px}

/* RESPONSIVE */
@media(max-width:900px){
  .r3,.r4,.r5{grid-template-columns:1fr 1fr}
  .r2{grid-template-columns:1fr}
}
@media(max-width:600px){
  .r3,.r4,.r5,.r2{grid-template-columns:1fr}
}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div style="font-size:1.8em">🤖</div>
  <div>
    <h1>ASD Therapy Platform — Parent Dashboard</h1>
    <p style="font-size:.76em;opacity:.8">
      Child: <b>{{p.child.name}}</b> |
      Age: {{p.child.age}} |
      <span class="prot {{p.session.protocol}}">
        {{p.session.protocol}}</span> |
      Level: {{p.session.difficulty.upper()}} |
      Started: {{p.session_start}}
    </p>
  </div>
  <span class="badge live">● LIVE</span>
  <span class="badge {% if p.gemini_ok %}gem-ok{% else %}gem-off{% endif %}">
    {% if p.gemini_ok %}⚡ Gemini Active
    {% else %}⚠️ Gemini Offline{% endif %}
  </span>
</div>

<div class="main">

  <!-- TOP STATS -->
  <div class="row r5">
    <div class="stat">
      <div class="n n-g">{{p.progress.total_score}}</div>
      <div class="l">🏆 Total Score</div>
    </div>
    <div class="stat">
      <div class="n n-y">{{p.progress.tokens}}⭐</div>
      <div class="l">🎯 Token Reward</div>
    </div>
    <div class="stat">
      <div class="n n-b">{{p.perception.attention}}%</div>
      <div class="l">👀 Attention</div>
    </div>
    <div class="stat">
      <div class="n">P{{p.session.prompt_level}}</div>
      <div class="l">💡 Prompt Level</div>
    </div>
    <div class="stat">
      <div class="n n-g">{{p.progress.consecutive_ok}}</div>
      <div class="l">🔥 Streak</div>
    </div>
  </div>

  <!-- TABS NAVIGATION -->
  <div class="tabs">
    <div class="tab active" onclick="showTab('overview')">
      📊 Overview</div>
    <div class="tab" onclick="showTab('charts')">
      📈 Charts</div>
    <div class="tab" onclick="showTab('assessment')">
      📋 Assessment</div>
    <div class="tab" onclick="showTab('chatbot')">
      💬 AI Chatbot</div>
    <div class="tab" onclick="showTab('notes')">
      📝 Notes</div>
    <div class="tab" onclick="showTab('help')">
      💡 Help Guide</div>
    <div class="tab" onclick="showTab('settings')">
      ⚙️ Settings</div>
  </div>

  <!-- TAB: OVERVIEW -->
  <div id="tab-overview" class="tab-content active">
    <div class="row r3">

      <!-- Emotion Live -->
      <div class="card">
        <h2>😊 Live Emotion Stream</h2>
        <div style="text-align:center;padding:8px">
          <div class="emo {{p.perception.emotion}}">
            {{p.perception.emotion.upper()}}
          </div>
          <div style="margin:10px 0">
            <div style="font-size:.73em;color:var(--muted)">
              Attention Level</div>
            <div class="bar-bg">
              <div class="bar-fill"
                   style="width:{{p.perception.attention}}%">
              </div>
            </div>
            <span style="font-size:.73em;color:var(--purple)">
              {{p.perception.attention}}%</span>
          </div>
          <div style="font-size:.76em;color:var(--muted)">
            Engagement:
            <b style="color:var(--text)">
              {{p.perception.engagement}}</b>
          </div>
          <div style="margin-top:5px;font-size:.71em;color:
            {{'#34d399' if p.perception.face_detected else '#f87171'}}">
            {{'✅ Face Detected' if p.perception.face_detected
              else '❌ No Face - Move Closer!'}}
          </div>
          {% if p.session.clap_detected %}
          <div style="color:var(--yellow);font-weight:700;
                      margin-top:5px;font-size:.85em">
            👏 CLAP DETECTED!</div>{% endif %}

          <!-- Emotion score bars -->
          <div style="margin-top:12px;text-align:left">
            {% for em,sc in p.perception.emotion_scores.items() %}
            {% if sc > 0.04 %}
            <div style="display:flex;align-items:center;
                        gap:6px;margin:3px 0">
              <span style="width:56px;font-size:.67em;
                           color:var(--muted)">
                {{em[:7]}}</span>
              <div style="flex:1;background:#1f2937;
                          height:8px;border-radius:4px">
                <div style="width:{{(sc*100)|int}}%;
                            height:8px;border-radius:4px;
                            background:#6366f1"></div>
              </div>
              <span style="font-size:.67em;color:var(--purple);
                           min-width:30px">
                {{(sc*100)|int}}%</span>
            </div>{% endif %}{% endfor %}
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="card">
        <h2>🎮 Therapy Controls</h2>
        <form method="POST" action="/cmd">
          <div style="margin-bottom:8px">
            <div style="font-size:.72em;color:var(--muted);
                        margin-bottom:5px">Session Types</div>
            <button class="btn" name="c" value="aba">
              📚 ABA</button>
            <button class="btn" name="c" value="dtt">
              🎯 DTT</button>
            <button class="btn" name="c" value="teacch">
              📅 TEACCH</button>
            <button class="btn" name="c" value="tie">
              🧠 TIE</button>
          </div>
          <div style="margin-bottom:8px">
            <div style="font-size:.72em;color:var(--muted);
                        margin-bottom:5px">Quick Actions</div>
            <button class="btn btn-g" name="c" value="dance">
              💃 Dance!</button>
            <button class="btn btn-y" name="c" value="game">
              🎮 Game</button>
            <button class="btn btn-b" name="c" value="celebrate">
              🎉 Celebrate!</button>
            <button class="btn btn-r" name="c" value="break">
              ⏸ Break</button>
          </div>
        </form>

        <div style="margin-top:10px">
          <div style="font-size:.72em;color:var(--muted);
                      margin-bottom:5px">📺 Quick Videos</div>
          <div style="display:flex;flex-wrap:wrap;gap:3px">
            {% for sk in skills %}
            <form method="POST" action="/skill"
                  style="display:inline">
              <button class="btn btn-y" name="s"
                      value="{{sk}}"
                      style="font-size:.67em;padding:4px 7px">
                {{sk}}</button>
            </form>{% endfor %}
          </div>
        </div>

        <div style="margin-top:9px;display:flex;gap:6px">
          <form method="POST" action="/search"
                style="flex:1;display:flex;gap:5px">
            <input name="q"
                   placeholder="Search educational video...">
            <button class="btn">🔍</button>
          </form>
        </div>
      </div>

      <!-- Live Chat -->
      <div class="card">
        <h2>💬 Live Session Chat</h2>
        <div class="chat-box" id="chat-main">
          {% for lg in p.logs[-20:]|reverse %}
          {% if 'Said:' in lg.msg %}
          <div class="chat-msg chat-p">
            <span style="color:var(--purple);font-size:.68em">
              🤖 Pepper [{{lg.time}}]</span><br>
            {{lg.msg.replace('Said: ','')}}
          </div>
          {% elif 'Heard:' in lg.msg %}
          <div class="chat-msg chat-c">
            <span style="color:var(--green);font-size:.68em">
              👦 Child [{{lg.time}}]</span><br>
            {{lg.msg.replace('Heard: ','')}}
          </div>
          {% endif %}{% endfor %}
        </div>
        <form method="POST" action="/parent_msg"
              style="display:flex;gap:5px">
          <input name="msg"
                 placeholder="Send message via Pepper...">
          <button class="btn btn-g">📤</button>
        </form>
      </div>
    </div>
  </div>

  <!-- TAB: CHARTS -->
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
        <h2>😊 Emotion Distribution</h2>
        <div class="chart-wrap">
          <canvas id="emoChart"></canvas>
        </div>
      </div>
      <div class="card">
        <h2>🎯 Skills Radar</h2>
        <div class="skills-grid">
          {% for skill,vals in p.progress.skills_data.items() %}
          {% set pct = [vals[-1] if vals else 50]|first %}
          <div class="skill-item">
            <div class="skill-bar">
              <div class="skill-fill"
                   style="height:{{pct}}%"></div>
            </div>
            <div class="skill-name">{{skill}}</div>
            <div class="skill-val">{{pct}}%</div>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>

    <!-- Session Log -->
    <div class="card">
      <h2>📋 Full Session Log</h2>
      <div class="log-box">
        {% for lg in p.logs[-50:]|reverse %}
        <div class="log-item {{lg.type}}">
          <span style="color:#6366f1">{{lg.time}}</span>
          <span class="prot {{lg.protocol}}">
            {{lg.protocol}}</span>
          <b style="color:var(--purple)">{{lg.child}}</b>:
          {{lg.msg}}
          <span style="color:#374151;font-size:.75em">
            | {{lg.emotion}}</span>
        </div>{% endfor %}
      </div>
      <div style="margin-top:8px;display:flex;
                  justify-content:space-between;
                  align-items:center">
        <a href="/export"
           class="btn btn-g"
           style="text-decoration:none">
          📥 Export Report JSON</a>
        <span style="font-size:.72em;color:var(--muted)">
          {{p.logs|length}} total interactions</span>
      </div>
    </div>
  </div>

  <!-- TAB: ASSESSMENT -->
  <div id="tab-assessment" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>📋 IASQ Screening (10 Questions)</h2>
        {% if p.assessments.iasq_result %}
        <div style="background:#051a0f;border-radius:9px;
                    padding:12px;margin-bottom:12px;
                    border:1px solid var(--green)">
          <div style="font-size:.82em;color:var(--green);
                      font-weight:700">
            Last Result: {{p.assessments.iasq_result}}</div>
          <div style="font-size:.75em;color:var(--muted)">
            Score: {{p.assessments.iasq_score}}/50 |
            {{p.assessments.last_assessment}}</div>
        </div>
        {% endif %}
        <form method="POST" action="/iasq">
          {% for i,q in questions.items() %}
          <div class="q-card">
            <div class="q-text">{{i}}. {{q.q}}</div>
            <div class="q-opts">
              {% for j,opt in enumerate(q.options) %}
              <label style="cursor:pointer">
                <input type="radio"
                       name="q{{i}}" value="{{j}}"
                       style="width:auto;margin:0 3px">
                <span class="q-opt">{{opt}}</span>
              </label>{% endfor %}
            </div>
          </div>{% endfor %}
          <button class="btn btn-g"
                  style="width:100%;margin-top:10px;
                         padding:10px">
            🔍 Calculate IASQ Result</button>
        </form>
      </div>

      <div class="card">
        <h2>📊 Assessment History</h2>
        {% if p.assessments.iasq_result %}
        <div style="text-align:center;padding:20px">
          {% set score = p.assessments.iasq_score %}
          {% set pct = (score/50*100)|int %}
          <div style="font-size:2.5em;font-weight:700;
                      color:{{'#34d399' if pct<40
                              else '#fbbf24' if pct<70
                              else '#f87171'}}">
            {{p.assessments.iasq_result}}</div>
          <div style="font-size:.8em;color:var(--muted);
                      margin-top:5px">
            Score: {{score}}/50 ({{pct}}%)</div>
          <div class="bar-bg" style="margin:10px 0">
            <div style="width:{{pct}}%;height:9px;
                        border-radius:6px;
                        background:{{'#34d399' if pct<40
                                     else '#fbbf24' if pct<70
                                     else '#f87171'}}">
            </div>
          </div>
          <div style="font-size:.75em;color:var(--muted)">
            {% if pct < 40 %}
            ✅ Low Risk - Continue regular monitoring
            {% elif pct < 70 %}
            ⚠️ Medium Risk - Recommend specialist evaluation
            {% else %}
            🔴 High Risk - Please consult specialist immediately
            {% endif %}
          </div>
        </div>
        {% else %}
        <div style="text-align:center;padding:30px;
                    color:var(--muted)">
          Complete the IASQ test to see results here.
        </div>
        {% endif %}

        <div style="margin-top:15px">
          <div style="font-size:.78em;font-weight:700;
                      color:var(--purple);margin-bottom:8px">
            Recommendations for Parents:</div>
          {% if p.assessments.iasq_result %}
          {% set pct2 = (p.assessments.iasq_score/50*100)|int %}
          <div style="font-size:.74em;color:#9ca3af;
                      line-height:1.7">
            {% if pct2 < 40 %}
            • Schedule regular therapy sessions 2x/week<br>
            • Focus on social skills and communication<br>
            • Maintain consistent daily routine<br>
            • Monitor progress monthly
            {% elif pct2 < 70 %}
            • Increase therapy to 3x/week<br>
            • Start ABA and DTT programs<br>
            • Consult developmental pediatrician<br>
            • Join parent support group
            {% else %}
            • Seek immediate specialist evaluation<br>
            • Consider intensive early intervention (EIBI)<br>
            • Apply for special education support<br>
            • Contact autism support organizations
            {% endif %}
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>

  <!-- TAB: CHATBOT -->
  <div id="tab-chatbot" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>🤖 Autism Specialist AI Chatbot</h2>
        <p style="font-size:.73em;color:var(--muted);
                  margin-bottom:10px">
          Ask any autism-related question in Arabic or English.
          Powered by Gemini AI with autism expertise.
        </p>
        <div class="chat-box" id="chat-parent"
             style="height:280px">
          {% for msg in chatbot_history %}
          <div class="chat-msg {{'chat-p' if msg.role=='pepper' else 'chat-par'}}">
            <span style="color:{{'var(--purple)' if msg.role=='pepper' else 'var(--blue)'}};
                         font-size:.68em">
              {{'🤖 Pepper' if msg.role=='pepper' else '👨‍👩‍👧 Parent'}}
              [{{msg.time}}]</span><br>
            {{msg.text}}
          </div>{% endfor %}
          {% if not chatbot_history %}
          <div style="color:var(--muted);font-size:.78em;
                      text-align:center;padding:20px">
            Ask me any question about autism, therapy,
            or your child's behavior. I'm here to help! 🤗
          </div>
          {% endif %}
        </div>
        <form method="POST" action="/parent_ask"
              style="display:flex;gap:6px">
          <input name="question"
                 placeholder="Ask about autism (English or Arabic)...">
          <button class="btn btn-g" style="white-space:nowrap">
            💬 Ask</button>
        </form>
      </div>

      <div class="card">
        <h2>📚 Quick Question Templates</h2>
        <div style="display:flex;flex-direction:column;gap:5px">
          {% set quick_qs = [
            "My child has a meltdown, what should I do?",
            "How do I improve eye contact?",
            "Best way to teach toilet training?",
            "How to communicate with school about ASD?",
            "My child eats very limited foods - help!",
            "How do I handle repetitive behaviors?",
            "What is the best therapy for my child?",
            "How to help with sleep problems?",
            "كيف أتعامل مع نوبات الغضب؟",
            "كيف أساعد طفلي على التواصل البصري؟",
          ] %}
          {% for q in quick_qs %}
          <form method="POST" action="/parent_ask">
            <button class="btn"
                    name="question" value="{{q}}"
                    style="width:100%;text-align:left;
                           font-size:.72em;padding:7px 10px">
              {{q}}</button>
          </form>{% endfor %}
        </div>
      </div>
    </div>
  </div>

  <!-- TAB: NOTES -->
  <div id="tab-notes" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>📝 Add Parent Observation</h2>
        <form method="POST" action="/add_note">
          <div style="margin-bottom:8px">
            <select name="category" style="margin-bottom:8px">
              <option value="behavior">Behavior</option>
              <option value="progress">Progress</option>
              <option value="concern">Concern</option>
              <option value="milestone">Milestone 🎉</option>
              <option value="other">Other</option>
            </select>
            <textarea name="note"
              placeholder="Describe what you observed about your child today...
Example: Child made eye contact for 5 seconds during play!
Example: Had meltdown at 3pm when TV was turned off.
Example: Successfully used 3 new words today!"></textarea>
          </div>
          <button class="btn btn-g"
                  style="width:100%;padding:10px">
            ➕ Save Observation</button>
        </form>
      </div>

      <div class="card">
        <h2>📋 Observations History</h2>
        <div style="max-height:350px;overflow-y:auto">
          {% for note in p.parent_notes[-20:]|reverse %}
          <div class="note-item">
            <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-bottom:4px">
              <span style="color:var(--purple);font-size:.7em;
                           font-weight:700">
                {{note.category.upper()}}</span>
              <span style="color:var(--muted);font-size:.68em">
                {{note.time}}</span>
            </div>
            {{note.text}}
          </div>{% endfor %}
          {% if not p.parent_notes %}
          <div style="color:var(--muted);text-align:center;
                      padding:20px;font-size:.78em">
            No observations yet. Start recording your child's progress!
          </div>{% endif %}
        </div>
      </div>
    </div>
  </div>

  <!-- TAB: HELP GUIDE -->
  <div id="tab-help" class="tab-content">
    <div class="row r3">
      <div class="help-card">
        <div class="help-title">🎯 ABA - Applied Behavior Analysis</div>
        <div class="help-body">
          Break tasks into tiny steps. Give immediate specific
          praise within 2 seconds. Use token economy (stars).
          Repeat consistently. Ignore minor unwanted behaviors.
        </div>
        <div class="tip-box">
          💡 If child fails 3 times → immediately switch
          to an easier version of the task.
        </div>
      </div>

      <div class="help-card">
        <div class="help-title">📚 DTT - Discrete Trial Training</div>
        <div class="help-body">
          ONE instruction at a time. Wait 5 seconds for response.
          Prompt if needed (verbal → gestural → physical).
          Always end trial with feedback. Keep sessions 10-15 min.
        </div>
        <div class="tip-box">
          💡 Same words, same order, every time.
          Consistency reduces child's anxiety.
        </div>
      </div>

      <div class="help-card">
        <div class="help-title">📅 TEACCH - Visual Schedules</div>
        <div class="help-body">
          Create picture schedule for every day.
          Show child what comes NEXT (not the whole day).
          Use visual timers. Structure reduces anxiety greatly.
          Keep workspace organized and predictable.
        </div>
        <div class="tip-box">
          💡 Print schedule + let child check off activities.
          This gives them control and reduces meltdowns.
        </div>
      </div>

      <div class="help-card">
        <div class="help-title">⚠️ Meltdown Protocol</div>
        <div class="help-body">
          1. Stay calm yourself (children feel your stress)<br>
          2. Remove triggers immediately<br>
          3. Give physical space<br>
          4. Speak softly, use 5-word sentences<br>
          5. Do NOT force eye contact<br>
          6. Offer comfort item (blanket, toy)
        </div>
        <div class="tip-box">
          💡 Keep a "calm kit": headphones, fidget toy,
          weighted blanket, dim lamp.
        </div>
      </div>

      <div class="help-card">
        <div class="help-title">👏 Effective Reinforcement</div>
        <div class="help-body">
          Praise immediately (within 2 seconds of success).
          Be SPECIFIC: "Great touching your nose!"
          not just "Good job!". Find YOUR child's top motivators.
          Use natural reinforcers (not just candy).
        </div>
        <div class="tip-box">
          💡 Create a "reward menu" with 5-10 items
          your child loves. Let them choose!
        </div>
      </div>

      <div class="help-card">
        <div class="help-title">📊 Reading the Dashboard</div>
        <div class="help-body">
          <b>Attention >70%</b> → Child engaged ✅<br>
          <b>P0</b> → Doing great, no prompts needed ✅<br>
          <b>P1</b> → Needs verbal reminder ℹ️<br>
          <b>P2</b> → Needs visual cue ⚠️<br>
          <b>P3</b> → Needs direct support 🛑<br>
          <b>Distressed</b> → Take break immediately
        </div>
        <div class="tip-box">
          💡 Screenshot dashboard to share progress
          with your child's therapist or school.
        </div>
      </div>
    </div>

    <!-- Session Summary for Specialist -->
    <div class="card" style="margin-top:12px">
      <h2>📋 Printable Session Summary</h2>
      <div style="background:#0a1020;border-radius:9px;
                  padding:14px;font-size:.78em;
                  line-height:2;color:#9ca3af">
        <b style="color:var(--purple)">Session Report</b><br>
        Child: <b style="color:var(--text)">
          {{p.child.name}}</b> |
        Age: <b style="color:var(--text)">
          {{p.child.age}}</b> |
        Date: <b style="color:var(--text)">
          {{now}}</b><br>
        Total Score: <b style="color:var(--purple)">
          {{p.progress.total_score}}</b> |
        Tokens Earned: <b style="color:var(--yellow)">
          ⭐{{p.progress.tokens}}</b> |
        Interactions: <b style="color:var(--purple)">
          {{p.logs|length}}</b><br>
        Dominant Emotion: <b style="color:var(--text)">
          {{p.perception.emotion}}</b> |
        Protocol: <b style="color:var(--text)">
          {{p.session.protocol}}</b> |
        Level Reached: <b style="color:var(--green)">
          {{p.session.difficulty.upper()}}</b><br>
        IASQ Result: <b style="color:var(--text)">
          {{p.assessments.iasq_result or 'Not taken'}}</b> |
        Parent Notes: <b style="color:var(--text)">
          {{p.parent_notes|length}} observations</b>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px">
        <a href="/export" class="btn btn-g"
           style="text-decoration:none">
          📥 Export JSON</a>
        <a href="/export_notes" class="btn"
           style="text-decoration:none">
          📝 Export Notes</a>
      </div>
    </div>
  </div>

  <!-- TAB: SETTINGS -->
  <div id="tab-settings" class="tab-content">
    <div class="row r2">
      <div class="card">
        <h2>👦 Child Profile</h2>
        <form method="POST" action="/update_child">
          <label style="font-size:.76em;color:var(--muted)">
            Child Name</label>
          <input name="name"
                 value="{{p.child.name}}"
                 style="margin-bottom:8px">
          <label style="font-size:.76em;color:var(--muted)">
            Age</label>
          <input name="age" type="number"
                 value="{{p.child.age}}"
                 min="1" max="18"
                 style="margin-bottom:8px">
          <label style="font-size:.76em;color:var(--muted)">
            Diagnosis</label>
          <select name="diagnosis" style="margin-bottom:8px">
            <option {{'selected' if p.child.diagnosis=='ASD Level 1'}}>
              ASD Level 1</option>
            <option {{'selected' if p.child.diagnosis=='ASD Level 2'}}>
              ASD Level 2</option>
            <option {{'selected' if p.child.diagnosis=='ASD Level 3'}}>
              ASD Level 3</option>
            <option {{'selected' if p.child.diagnosis=='Suspected ASD'}}>
              Suspected ASD</option>
          </select>
          <button class="btn btn-g"
                  style="width:100%;padding:9px">
            💾 Save Profile</button>
        </form>
      </div>

      <div class="card">
        <h2>⚙️ Therapy Settings</h2>
        <form method="POST" action="/update_settings">
          <label style="font-size:.76em;color:var(--muted)">
            Difficulty Level</label>
          <select name="difficulty" style="margin-bottom:8px">
            <option {{'selected' if p.session.difficulty=='easy'}}>
              easy</option>
            <option {{'selected' if p.session.difficulty=='medium'}}>
              medium</option>
            <option {{'selected' if p.session.difficulty=='hard'}}>
              hard</option>
          </select>
          <label style="font-size:.76em;color:var(--muted)">
            Session Duration (minutes)</label>
          <input name="duration" type="number"
                 value="{{p.session.duration_min}}"
                 min="5" max="30"
                 style="margin-bottom:8px">
          <button class="btn btn-g"
                  style="width:100%;padding:9px">
            💾 Save Settings</button>
        </form>
      </div>
    </div>
  </div>

</div><!-- end main -->

<script>
// ===== TABS =====
function showTab(name) {
  document.querySelectorAll('.tab-content')
    .forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab')
    .forEach(t => t.classList.remove('active'));
  document.getElementById('tab-'+name)
    .classList.add('active');
  event.target.classList.add('active');
}

// ===== CHARTS =====
const attData   = {{att_history|tojson}};
const scoreData = {{score_history|tojson}};
const emoData   = {{emo_dist|tojson}};
const labels    = Array.from(
  {length:attData.length},(_,i)=>i+1);

const chartOpts = {
  responsive:true, maintainAspectRatio:false,
  plugins:{legend:{labels:{
    color:'#9ca3af',font:{size:10}}}},
  scales:{
    x:{ticks:{color:'#6b7280',font:{size:9}},
       grid:{color:'#1f2937'}},
    y:{ticks:{color:'#6b7280',font:{size:9}},
       grid:{color:'#1f2937'}}
  }
};

if(document.getElementById('attChart')) {
  new Chart(document.getElementById('attChart'),{
    type:'line',
    data:{labels,datasets:[{
      label:'Attention %',data:attData,
      borderColor:'#6366f1',
      backgroundColor:'rgba(99,102,241,0.12)',
      tension:0.4,fill:true,pointRadius:2,
    }]},
    options:{...chartOpts,
      scales:{...chartOpts.scales,
        y:{...chartOpts.scales.y,min:0,max:100}}}
  });
}

if(document.getElementById('scoreChart')) {
  new Chart(document.getElementById('scoreChart'),{
    type:'bar',
    data:{labels,datasets:[{
      label:'Score',data:scoreData,
      backgroundColor:'rgba(167,139,250,0.55)',
      borderColor:'#a78bfa',borderWidth:1,
    }]},
    options:chartOpts
  });
}

if(document.getElementById('emoChart') &&
   Object.keys(emoData).length > 0) {
  const emoColors = {
    happy:'#34d399',sad:'#60a5fa',angry:'#f87171',
    neutral:'#9ca3af',fear:'#fbbf24',
    surprise:'#c084fc',disgust:'#6ee7b7'
  };
  new Chart(document.getElementById('emoChart'),{
    type:'doughnut',
    data:{
      labels:Object.keys(emoData),
      datasets:[{
        data:Object.values(emoData),
        backgroundColor:Object.keys(emoData)
          .map(e=>emoColors[e]||'#6366f1'),
      }]
    },
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{
        position:'right',
        labels:{color:'#9ca3af',font:{size:10}}}}}
  });
}

// Auto-scroll chats
['chat-main','chat-parent'].forEach(id => {
  const el = document.getElementById(id);
  if(el) el.scrollTop = el.scrollHeight;
});
</script>
</body>
</html>
"""

# Chatbot history
_chatbot_history = []

SKILLS_LIST = ["wash face","brush teeth","emotions",
               "colors","numbers","alphabet","sharing",
               "greetings","animals","shapes","toilet"]

@dash_app.route("/")
def dashboard():
    # Build emotion distribution
    emo_dist = {}
    for e in PLATFORM["progress"]["emotion_timeline"]:
        emo_dist[e] = emo_dist.get(e, 0) + 1

    # Enumerate for template
    questions_dict = {
        i+1: q for i,q in enumerate(IASQ_QUESTIONS)}

    return render_template_string(
        DASHBOARD_HTML,
        p=PLATFORM,
        skills=SKILLS_LIST,
        chatbot_history=_chatbot_history[-20:],
        att_history=PLATFORM["progress"]["attention_history"][-40:],
        score_history=PLATFORM["progress"]["score_history"][-40:],
        emo_dist=emo_dist,
        questions=questions_dict,
        enumerate=enumerate,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

@dash_app.route("/update_context", methods=["POST"])
def upd_ctx():
    d  = request.json or {}
    em = d.get("emotion","neutral")
    PLATFORM["perception"]["emotion"]       = em
    PLATFORM["perception"]["face_detected"] = True
    return jsonify({"status":"ok"})

@dash_app.route("/cmd", methods=["POST"])
def cmd():
    PLATFORM["sim_cmd"] = request.form.get("c","")
    return dashboard()

@dash_app.route("/skill", methods=["POST"])
def skill():
    s   = request.form.get("s","")
    q   = SKILL_VIDEOS.get(s, s+" autism children")
    url = YOUTUBE_BASE + urllib.parse.quote(
        q+" autism educational")
    webbrowser.open(url)
    plog(f"YouTube: {s}")
    return dashboard()

@dash_app.route("/search", methods=["POST"])
def search():
    q   = request.form.get("q","")
    url = YOUTUBE_BASE + urllib.parse.quote(
        q+" autism educational children")
    webbrowser.open(url)
    return dashboard()

@dash_app.route("/parent_msg", methods=["POST"])
def parent_msg():
    msg = request.form.get("msg","").strip()
    if msg:
        PLATFORM["sim_cmd"] = f"parent_msg:{msg}"
        plog(f"Parent msg: {msg[:40]}")
    return dashboard()

@dash_app.route("/parent_ask", methods=["POST"])
def parent_ask():
    question = request.form.get("question","").strip()
    if question and _gemini_ref:
        _chatbot_history.append({
            "role":"parent",
            "text": question,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        answer = _gemini_ref.parent(question)
        _chatbot_history.append({
            "role":"pepper",
            "text": answer,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        plog(f"Parent Q: {question[:40]}")
    return dashboard()

@dash_app.route("/iasq", methods=["POST"])
def iasq():
    total = 0
    for i in range(1, 11):
        val = request.form.get(f"q{i}")
        if val:
            total += int(val)

    # Scoring: higher = more risk for some, lower for others
    # Simplified: 0-20 low, 21-35 medium, 36-50 high
    if total <= 20:
        result = "Low Risk ✅"
    elif total <= 35:
        result = "Medium Risk ⚠️"
    else:
        result = "High Risk 🔴"

    PLATFORM["assessments"]["iasq_result"] = result
    PLATFORM["assessments"]["iasq_score"]  = total
    PLATFORM["assessments"]["last_assessment"] = \
        datetime.now().strftime("%Y-%m-%d %H:%M")

    plog(f"IASQ: {result} score={total}", "success")
    return dashboard()

@dash_app.route("/add_note", methods=["POST"])
def add_note():
    note     = request.form.get("note","").strip()
    category = request.form.get("category","other")
    if note:
        PLATFORM["parent_notes"].append({
            "time":     datetime.now().strftime("%H:%M:%S"),
            "text":     note,
            "category": category,
        })
        plog(f"Note [{category}]: {note[:40]}")
    return dashboard()

@dash_app.route("/update_child", methods=["POST"])
def update_child():
    PLATFORM["child"]["name"]      = \
        request.form.get("name","Friend").strip().title()
    PLATFORM["child"]["age"]       = \
        int(request.form.get("age", 6))
    PLATFORM["child"]["diagnosis"] = \
        request.form.get("diagnosis","ASD Level 2")
    plog("Child profile updated", "success")
    return dashboard()

@dash_app.route("/update_settings", methods=["POST"])
def update_settings():
    PLATFORM["session"]["difficulty"]   = \
        request.form.get("difficulty","easy")
    PLATFORM["session"]["duration_min"] = \
        int(request.form.get("duration",10))
    plog("Settings updated", "success")
    return dashboard()

@dash_app.route("/export")
def export():
    fn = (f"report_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(PLATFORM, f, indent=2, default=str)
    return jsonify({"saved": fn,
                    "score": PLATFORM["progress"]["total_score"],
                    "child": PLATFORM["child"]["name"]})

@dash_app.route("/export_notes")
def export_notes():
    fn = (f"notes_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(PLATFORM["parent_notes"],f,indent=2)
    return jsonify({"saved":fn})

@dash_app.route("/report")
def report():
    return jsonify({
        "child":    PLATFORM["child"]["name"],
        "emotion":  PLATFORM["perception"]["emotion"],
        "attention":PLATFORM["perception"]["attention"],
        "score":    PLATFORM["progress"]["total_score"],
        "protocol": PLATFORM["session"]["protocol"],
    })

_gemini_ref = None

def run_flask():
    dash_app.run(port=DASHBOARD_PORT,
                 debug=False,
                 use_reloader=False,
                 threaded=True)


# ============================================================
# THERAPY CONTROLLER
# ============================================================
class TherapyController:
    def __init__(self, gemini, voice, mic, display, sim,
                 actions):
        self.g  = gemini
        self.v  = voice
        self.m  = mic
        self.d  = display
        self.s  = sim
        self.a  = actions
        self.running = False

    def _speak(self, text):
        """Full pipeline: process tokens → speak → display"""
        clean = self.a.process(str(text))
        self.d.show_ai(clean)
        if self.s.ok:
            self.s.show_text(clean[:55])
        self.v.say(clean)

    def _ask(self, prompt):
        """Ask Gemini and speak result"""
        resp = self.g.therapy(prompt)
        self._speak(resp)
        return resp

    def run(self):
        self.running = True
        PLATFORM["session"]["active"]     = True
        PLATFORM["session"]["start_time"] = datetime.now()

        # Learn name
        name = self.m.get_name(self.v)
        PLATFORM["session"]["protocol"] = "GREETING"

        resp = self.g.therapy(
            f"Child name is {name}. "
            "Start enthusiastically! Use [WAVE]. "
            "Give first simple task!")
        self._speak(resp)
        time.sleep(0.5)

        # Background listening
        self.m.listen_bg(self._on_speech)

        # Main therapy loop
        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx     = 0
        last_em   = PLATFORM["perception"]["emotion"]
        em_t      = time.time()

        while self.running:
            # Check silence
            silence = time.time() - \
                      PLATFORM["session"]["last_sound"]
            if silence > 10:
                PLATFORM["session"]["last_sound"] = time.time()
                self._ask(
                    "Child silent 10 seconds. "
                    "Fun gentle prompt!")

            # Check prompt level
            self._update_prompt()

            # Emotion change reaction
            curr = PLATFORM["perception"]["emotion"]
            if curr != last_em and time.time()-em_t > 7:
                last_em = curr; em_t = time.time()
                if curr in ["sad","angry","fear","disgust"]:
                    self._ask(
                        f"Child just became {curr}. React!")

            # Dashboard commands
            self._handle_cmd()

            # Run protocol
            prot = protocols[p_idx % len(protocols)]
            p_idx += 1
            PLATFORM["session"]["protocol"] = prot
            self._run_protocol(prot)
            time.sleep(0.3)

    def _update_prompt(self):
        em  = PLATFORM["perception"]["emotion"]
        att = PLATFORM["perception"]["attention"]
        eng = PLATFORM["perception"]["engagement"]
        fd  = PLATFORM["perception"]["face_detected"]
        sess= PLATFORM["session"]

        if fd and att > 60 and em in ["happy","neutral"]:
            sess["prompt_level"] = 0

        elif not fd or att < 40:
            if sess["prompt_level"] < 1:
                sess["prompt_level"] = 1
                self._ask(
                    "Child distracted. "
                    "Verbal attention prompt! [POINT]")

        if eng == "distressed" and sess["prompt_level"] < 3:
            sess["prompt_level"] = 3
            self._ask(
                f"Child distressed ({em}). "
                "Immediate calming! [HUG]")

    def _handle_cmd(self):
        cmd = PLATFORM.get("sim_cmd")
        if not cmd: return
        PLATFORM["sim_cmd"] = None

        if cmd == "dance":
            self._ask("Do dance celebration! [DANCE]")
        elif cmd == "game":
            webbrowser.open(
                f"http://localhost:{DASHBOARD_PORT}")
            self._ask("Open game! [GAME]")
        elif cmd == "celebrate":
            self._ask(
                "Big celebration moment! "
                "[CELEBRATE][CLAP][DANCE]")
        elif cmd == "break":
            self._ask(
                "Time for sensory break. "
                "Calm activity. [NOD]")
        elif cmd.startswith("parent_msg:"):
            msg = cmd[11:]
            self._ask(
                f"Tell child (from parent): {msg}")
        elif cmd in ["aba","dtt","teacch","tie"]:
            PLATFORM["session"]["protocol"] = cmd.upper()

    def _run_protocol(self, prot):
        name = PLATFORM["child"]["name"]
        em   = PLATFORM["perception"]["emotion"]
        att  = PLATFORM["perception"]["attention"]
        diff = PLATFORM["session"]["difficulty"]

        if prot == "ABA":
            TASKS = {
                "easy":  ["Clap hands!","Touch nose!",
                          "Wave hello!","Show happy face!",
                          "Open mouth wide!"],
                "medium":["Stand up and sit!","Touch ears!",
                          "Point to door!","Count 3 fingers!",
                          "Jump once!"],
                "hard":  ["Say your full name!",
                          "What color is sky?",
                          "Name 2 animals!",
                          "What do you eat for breakfast?"],
            }
            task = random.choice(TASKS.get(diff,TASKS["easy"]))
            PLATFORM["session"]["current_task"] = task
            PLATFORM["session"]["task_retries"]  = 0

            resp = self.g.therapy(
                f"ABA instruction '{task}' for {name}. "
                f"Em:{em} Att:{att}%")
            self._speak(resp)
            self.d.show_task(task)

            success = self._wait_response(task, 12)
            prog    = PLATFORM["progress"]

            if success:
                prog["total_score"]    += 10
                prog["consecutive_ok"] += 1
                prog["tokens"]         += 1
                PLATFORM["session"]["clap_detected"] = False
                PLATFORM["session"]["task_success"]  = False

                resp = self.g.therapy(
                    f"{name} did '{task}'! "
                    "Celebrate! [CLAP][REWARD:2]")
                self._speak(resp)
                self.d.show_praise("AMAZING! ⭐⭐")
                plog(f"ABA: {task} ✅", "success", "ABA")

                # Level up
                if prog["consecutive_ok"] >= 3:
                    if diff == "easy":
                        PLATFORM["session"]["difficulty"]="medium"
                    elif diff == "medium":
                        PLATFORM["session"]["difficulty"]="hard"
                    prog["consecutive_ok"] = 0
                    self._ask(
                        "Child leveled up! "
                        "Big celebration! [DANCE][CELEBRATE]")

                # Update skill data
                skill_pct = min(95, 40 + prog["total_score"]//5)
                for sk in PLATFORM["progress"]["skills_data"]:
                    vals = PLATFORM["progress"]["skills_data"][sk]
                    vals.append(skill_pct + random.randint(-5,5))
                    if len(vals) > 20:
                        PLATFORM["progress"]["skills_data"][sk] = \
                            vals[-20:]
            else:
                prog["consecutive_ok"] = 0
                PLATFORM["session"]["task_retries"] += 1

                if PLATFORM["session"]["task_retries"] < 3:
                    resp = self.g.therapy(
                        f"{name} needs help with '{task}'. "
                        "Gentle retry differently.")
                    self._speak(resp)
                else:
                    self._ask(
                        f"Skip '{task}'. Give easier version.")
                    PLATFORM["session"]["task_retries"] = 0

                plog(f"ABA: {task} ❌", "fail", "ABA")
            time.sleep(2)

        elif prot == "DTT":
            resp = self.g.therapy(
                f"ONE DTT trial for {name}. "
                f"Diff:{diff} Em:{em}")
            self._speak(resp)
            self.d.show_task("DTT Trial")
            ok = self._wait_response("DTT", 10)
            if ok:
                PLATFORM["progress"]["total_score"] += 12
                PLATFORM["progress"]["tokens"]      += 1
                self._ask(f"DTT success! [CLAP][REWARD:1]")
                self.d.show_praise("CORRECT! ✅")
                plog("DTT ✅", "success", "DTT")
            else:
                self._ask("DTT error correction. Try again.")
                plog("DTT ❌", "fail", "DTT")
            time.sleep(2)

        elif prot == "TEACCH":
            resp = self.g.therapy(
                f"TEACCH schedule step for {name}. Em:{em}")
            self._speak(resp)
            time.sleep(3)
            if PLATFORM["perception"]["emotion"] == "happy":
                PLATFORM["progress"]["total_score"] += 15
            plog("TEACCH ✅", "success", "TEACCH")

        elif prot == "TIE":
            resp = self.g.therapy(
                f"TIE adaptive session for {name}. "
                f"Em:{em} Att:{att}% "
                f"Eng:{PLATFORM['perception']['engagement']}")
            self._speak(resp)
            time.sleep(3)
            PLATFORM["progress"]["total_score"] += 8
            plog("TIE ✅", "success", "TIE")

    def _wait_response(self, task, timeout=12):
        """Wait for child response"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            sess = PLATFORM["session"]
            # Clap for clap task
            if sess["clap_detected"] and \
               "clap" in task.lower():
                return True
            # Task keyword success
            if sess.get("task_success"):
                return True
            # Happy + attention = likely success
            if (PLATFORM["perception"]["emotion"] == "happy"
                    and PLATFORM["perception"]["attention"] > 65):
                return True
            time.sleep(0.25)
        return False

    def _on_speech(self, text):
        """Handle child's speech"""
        PLATFORM["session"]["last_sound"] = time.time()
        if not text: return
        t    = text.lower()
        name = PLATFORM["child"]["name"]

        if text == "[sound]":
            self.v.say(f"I heard you {name}! 👍")
            return

        # Name learning
        if not PLATFORM["child"]["known"]:
            n = self.m._extract(text)
            if n:
                PLATFORM["child"]["name"]  = n
                PLATFORM["child"]["known"] = True
                self._ask(
                    f"Child said name is {n}! "
                    "Welcome warmly! [WAVE]")
            return

        # How-to / educational → YouTube
        edu_words = ["how","what is","show","teach",
                     "explain","what are","what does",
                     "كيف","ما هو","أرني"]
        if any(w in t for w in edu_words):
            resp = self.g.therapy(
                f"Child asked: '{text}'. "
                "Answer simply. Use [YOUTUBE:...] if visual needed.")
            self._speak(resp)
            return

        # Game request
        if any(w in t for w in
               ["play","game","fun","games",
                "العب","لعبة","العاب"]):
            self._ask(
                f"{name} wants game! [GAME][CELEBRATE]")
            return

        # Task keywords
        task = PLATFORM["session"].get("current_task","")
        if task:
            task_kws = task.lower().replace("!","").split()
            if any(w in t for w in task_kws if len(w) > 2):
                PLATFORM["session"]["task_success"] = True

        # General Gemini response
        resp = self.g.therapy(
            f"Child said: '{text}'. "
            "Respond therapeutically.")
        self._speak(resp)


# ============================================================
# MAIN
# ============================================================
def main():
    global _gemini_ref

    print("""
╔══════════════════════════════════════════════════════════════╗
║   ASD THERAPY PLATFORM v1.0                                 ║
║   Pepper + Gemini + DeepFace + ABA/DTT/TEACCH/TIE           ║
║   Dashboard: http://localhost:5007                          ║
╚══════════════════════════════════════════════════════════════╝
""")

    # 1. Flask Dashboard
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Dashboard: http://localhost:{DASHBOARD_PORT}")
    time.sleep(0.8)

    # 2. Initialize all components
    gemini  = GeminiBrain()
    _gemini_ref = gemini
    voice   = VoiceEngine()
    camera  = CameraEngine()
    em_eng  = EmotionEngine()
    display = DisplayEngine(em_eng, camera)
    mic     = MicEngine()
    sim     = PepperSim()
    pepper  = sim.launch()
    actions = ActionEngine(pepper)

    time.sleep(1.5)

    # Set safe default
    PLATFORM["child"]["name"] = "Friend"

    # Welcome
    voice.say(
        "Hello! I am Pepper, your AI therapy partner! "
        "Ready to start our session!")
    if pepper:
        threading.Thread(
            target=actions._wave, daemon=True).start()

    # 3. Start therapy
    ctrl = TherapyController(
        gemini, voice, mic, display, sim, actions)
    t = threading.Thread(
        target=ctrl.run, daemon=True)
    t.start()

    print("\n" + "="*56)
    print("✅ PLATFORM ACTIVE")
    print("="*56)
    print(f"🌐 Dashboard:  http://localhost:{DASHBOARD_PORT}")
    print("📹 Windows:    Therapy + Emotion (300x300)")
    print("🎤 Listening:  MAX sensitivity (energy=20)")
    print("⌨️  Commands:   'report' | 'name X' | 'exit'")
    print("="*56+"\n")

    while getattr(display,'running',True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()

            if cl in ["q","exit","quit"]:
                ctrl.running = False
                display.stop()
                break

            elif cl == "report":
                prog = PLATFORM["progress"]
                print(f"\n📊 SESSION REPORT")
                print(f"   Child:    {PLATFORM['child']['name']}")
                print(f"   Score:    {prog['total_score']}")
                print(f"   Tokens:   ⭐{prog['tokens']}")
                print(f"   Emotion:  {PLATFORM['perception']['emotion']}")
                print(f"   Attention:{PLATFORM['perception']['attention']}%")
                print(f"   Protocol: {PLATFORM['session']['protocol']}")
                print(f"   Level:    {PLATFORM['session']['difficulty']}")
                print(f"   Logs:     {len(PLATFORM['logs'])}")

            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                PLATFORM["child"]["name"]  = n
                PLATFORM["child"]["known"] = True
                voice.say(f"Hello {n}!")

            else:
                ctrl._on_speech(cmd)

        except (KeyboardInterrupt, EOFError):
            break

    # Cleanup
    ctrl.running = False
    voice.say("Goodbye! Great session today! See you soon!")
    fn = (f"session_"
          f"{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(fn,"w") as f:
        json.dump(PLATFORM, f, indent=2, default=str)
    print(f"\n📄 Session saved: {fn}")
    print("✅ Platform shutdown complete.")


if __name__ == "__main__":
    main()

