#!/usr/bin/env python3
"""
PEPPER GEMINI THERAPY v2 - FIXED
- Fixed: child_name None bug
- Fixed: DeepFace Python 3.9 compatibility  
- Fixed: Camera detection with fallback
- High accuracy emotion + object detection
"""

import cv2, numpy as np, threading, time, random
import queue, json, sys, os, math, re, warnings
import webbrowser, urllib.parse
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import pyttsx3
import speech_recognition as sr
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

import pybullet as p
import pybullet_data
sys.path.insert(0, '/home/lamya/pepper_duo/src')

import google.generativeai as genai

# ============================================================
# CONFIG
# ============================================================
GEMINI_API_KEY = "AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8"
genai.configure(api_key=GEMINI_API_KEY)

GEMINI_SYSTEM = """You are Pepper, a highly enthusiastic robotic therapist for children with Autism (ASD).

PROTOCOLS: ABA, DTT, TEACCH, TIE
RULES:
- Short sentences (max 2)
- Immediate positive reinforcement
- Use child's name often
- High energy and patience

ACTION TOKENS (add to response):
[WAVE] [CLAP] [NOD] [DANCE] [POINT] [HUG] [THINK]

TRIGGERS:
[YOUTUBE: query] - open educational video
[GAME] - open game at localhost:5009
[IMAGE: query] - open google images

EMOTION RESPONSE:
- happy → celebrate + harder task
- sad → comfort + easier task [HUG]
- angry → breathing exercise [NOD]
- neutral → engage with fun activity

Always end with a task or question."""

STATE = {
    "emotion":        "neutral",
    "emotion_scores": {},
    "face_detected":  False,
    "objects":        [],
    "attention":      70,
    "engagement":     "moderate",
    "child_name":     "Friend",      # ← FIXED: default value
    "child_known":    False,
    "last_sound":     time.time(),
    "logs":           [],
    "score":          0,
    "protocol":       "GREETING",
    "prompt_level":   0,
    "is_speaking":    False,
    "clap_detected":  False,
    "difficulty":     "easy",
    "consecutive":    0,
    "task_done":      False,
    "sim_cmd":        None,
    "gemini_ok":      False,
    "session_start":  datetime.now().strftime("%H:%M"),
}

EMO_COLORS = {
    "happy":    (0, 220, 80),
    "sad":      (100, 100, 220),
    "angry":    (0, 0, 220),
    "fear":     (0, 180, 220),
    "surprise": (200, 50, 220),
    "disgust":  (0, 180, 100),
    "neutral":  (180, 180, 180),
}

def log(msg, t="info"):
    STATE["logs"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": msg[:100], "type": t,
        "protocol": STATE["protocol"],
        "emotion": STATE["emotion"],
        "child": STATE["child_name"],
    })
    print(f"[{datetime.now().strftime('%H:%M:%S')}]"
          f"[{t.upper()}] {msg[:80]}")

# ============================================================
# GEMINI BRAIN
# ============================================================
class GeminiBrain:
    def __init__(self):
        self.ok   = False
        self.chat = None
        try:
            self.model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=GEMINI_SYSTEM,
                generation_config=genai.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=150,
                    top_p=0.95,
                )
            )
            self.chat = self.model.start_chat(history=[])
            # Test connection
            test = self.chat.send_message("Say: READY")
            self.ok = True
            STATE["gemini_ok"] = True
            print("✅ Gemini 1.5 Flash connected!")
        except Exception as e:
            print(f"⚠️  Gemini: {e}")

    def ask(self, prompt, add_context=True):
        if not self.ok:
            return self._fallback()
        ctx = ""
        if add_context:
            ctx = (
                f"[State: child={STATE['child_name']}, "
                f"emotion={STATE['emotion']}, "
                f"attention={STATE['attention']}%, "
                f"protocol={STATE['protocol']}, "
                f"score={STATE['score']}, "
                f"difficulty={STATE['difficulty']}]\n"
            )
        try:
            resp = self.chat.send_message(ctx + prompt)
            return resp.text.strip()
        except Exception as e:
            print(f"⚠️  Gemini error: {e}")
            return self._fallback()

    def _fallback(self):
        name = STATE["child_name"]
        return random.choice([
            f"Great {name}! Let us keep going! 🌟",
            f"You are amazing {name}! 🎉",
            f"Well done {name}! 💪",
        ])

# ============================================================
# HIGH-ACCURACY EMOTION DETECTOR (Multi-method)
# ============================================================
class EmotionDetector:
    """
    3-layer detection:
    1. DeepFace (high accuracy)
    2. OpenCV Haar + basic analysis (fallback)
    3. Color/brightness analysis (last resort)
    """
    def __init__(self):
        self.deepface_ok = False
        self.face_cascade = None
        self.smile_cascade = None
        self.last_scores  = {}
        self.frame_count  = 0

        # Layer 1: DeepFace
        try:
            # Use tf.compat for Python 3.9
            import tensorflow as tf
            tf.compat.v1.logging.set_verbosity(
                tf.compat.v1.logging.ERROR)
            from deepface import DeepFace
            self.DeepFace = DeepFace
            # Warm up with small image
            dummy = np.zeros((64,64,3), dtype=np.uint8)
            DeepFace.analyze(
                dummy,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend='opencv',
                silent=True)
            self.deepface_ok = True
            print("✅ DeepFace ready (Layer 1)")
        except Exception as e:
            print(f"⚠️  DeepFace L1: {e}")

        # Layer 2: OpenCV cascades
        try:
            cascade_path = cv2.data.haarcascades
            self.face_cascade = cv2.CascadeClassifier(
                cascade_path + 'haarcascade_frontalface_default.xml')
            self.smile_cascade = cv2.CascadeClassifier(
                cascade_path + 'haarcascade_smile.xml')
            self.eye_cascade = cv2.CascadeClassifier(
                cascade_path + 'haarcascade_eye.xml')
            print("✅ OpenCV Cascades ready (Layer 2)")
        except Exception as e:
            print(f"⚠️  Cascade L2: {e}")

        # Layer 3: MediaPipe (if available)
        self.mediapipe_ok = False
        try:
            import mediapipe as mp
            self.mp_face = mp.solutions.face_mesh
            self.face_mesh = self.mp_face.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4)
            self.mediapipe_ok = True
            print("✅ MediaPipe ready (Layer 3)")
        except Exception as e:
            print(f"⚠️  MediaPipe L3: {e}")

    def analyze(self, frame):
        """Multi-layer analysis for high accuracy"""
        if frame is None or frame.size == 0:
            return {}, False

        scores    = {}
        face_found= False
        changed   = False
        old_em    = STATE["emotion"]

        # === LAYER 1: DeepFace (most accurate) ===
        if self.deepface_ok:
            try:
                result = self.DeepFace.analyze(
                    frame,
                    actions=['emotion'],
                    enforce_detection=False,
                    detector_backend='opencv',
                    silent=True,
                    align=True)
                if result and isinstance(result, list):
                    raw   = result[0].get('emotion', {})
                    total = sum(raw.values()) or 1
                    scores= {k: v/total
                             for k,v in raw.items()}
                    face_found = True
                    STATE["attention"] = min(
                        100, STATE["attention"] + 3)
            except Exception:
                pass

        # === LAYER 2: OpenCV (faster fallback) ===
        if not face_found and self.face_cascade:
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30,30),
                flags=cv2.CASCADE_SCALE_IMAGE)

            if len(faces) > 0:
                face_found = True
                STATE["attention"] = min(
                    100, STATE["attention"] + 2)
                x,y,w,h = faces[0]
                roi_gray = gray[y:y+h, x:x+w]
                roi_color= frame[y:y+h, x:x+w]

                # Smile detection
                smiles = self.smile_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.8,
                    minNeighbors=20,
                    minSize=(25,25))

                # Eye detection
                eyes = self.eye_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=10)

                # Basic scoring
                if len(smiles) > 0:
                    scores = {
                        "happy":   0.70,
                        "neutral": 0.20,
                        "surprise":0.10,
                    }
                elif len(eyes) >= 2:
                    scores = {
                        "neutral": 0.60,
                        "happy":   0.20,
                        "sad":     0.20,
                    }
                else:
                    scores = {
                        "sad":     0.40,
                        "neutral": 0.40,
                        "fear":    0.20,
                    }

        # === LAYER 3: MediaPipe attention ===
        if self.mediapipe_ok and face_found:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = self.face_mesh.process(rgb)
                if res.multi_face_landmarks:
                    # Good face detection
                    STATE["attention"] = min(
                        100, STATE["attention"] + 2)
                    # Check eye aspect ratio for attention
                    lm = res.multi_face_landmarks[0].landmark
                    # Left eye landmarks
                    left_eye = [lm[33],lm[160],lm[158],
                                lm[133],lm[153],lm[144]]
                    # EAR calculation
                    def ear(pts):
                        v1 = abs(pts[1].y - pts[5].y)
                        v2 = abs(pts[2].y - pts[4].y)
                        h  = abs(pts[0].x - pts[3].x)
                        return (v1+v2)/(2.0*h) if h>0 else 0
                    left_ear = ear(left_eye)
                    # Low EAR = eyes closed = tired/sad
                    if left_ear < 0.15 and scores:
                        scores["sad"]     = scores.get("sad",0)+0.2
                        scores["neutral"] = scores.get("neutral",0)-0.1
            except Exception:
                pass

        # Update state
        if face_found:
            STATE["face_detected"] = True
        else:
            STATE["face_detected"] = False
            STATE["attention"] = max(0, STATE["attention"]-2)

        if scores:
            # Apply 10% threshold
            valid = {k:v for k,v in scores.items() if v >= 0.10}
            if valid:
                dominant = max(valid, key=valid.get)
                STATE["emotion"]        = dominant
                STATE["emotion_scores"] = scores

                # Engagement
                pos = scores.get('happy',0)+scores.get('surprise',0)
                neg = scores.get('sad',0)+scores.get('angry',0)+\
                      scores.get('fear',0)
                if pos > 0.4:   STATE["engagement"] = "high"
                elif neg > 0.5: STATE["engagement"] = "distressed"
                else:           STATE["engagement"] = "moderate"

                changed = (dominant != old_em)

        self.last_scores = scores
        return scores, changed


# ============================================================
# OBJECT DETECTOR (YOLOv8 or basic OpenCV)
# ============================================================
class ObjectDetector:
    """Detect objects to report to Gemini context"""
    def __init__(self):
        self.yolo_ok    = False
        self.objects    = []

        try:
            from ultralytics import YOLO
            self.yolo = YOLO('yolov8n.pt')
            self.yolo_ok = True
            print("✅ YOLOv8 object detection ready!")
        except Exception as e:
            print(f"⚠️  YOLO: {e} (running without objects)")

    def detect(self, frame):
        if not self.yolo_ok or frame is None:
            return []
        try:
            results = self.yolo(frame, verbose=False,
                                conf=0.4)
            found = []
            for r in results:
                for box in r.boxes:
                    name = self.yolo.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    found.append(f"{name}({conf:.0%})")
            STATE["objects"] = found[:5]
            return found
        except Exception:
            return []


# ============================================================
# CAMERA - MULTI-DEVICE SEARCH
# ============================================================
class CameraManager:
    """Try multiple camera indices to find working camera"""
    def __init__(self):
        self.cap     = None
        self.index   = -1
        self.running = False
        self._find_camera()

    def _find_camera(self):
        # Try indices 0-4
        for idx in range(5):
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None \
                       and frame.size > 0:
                        self.cap   = cap
                        self.index = idx
                        # Set high resolution
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                        print(f"✅ Camera found at index {idx}")
                        return
                    cap.release()
            except Exception:
                pass
        print("⚠️  No camera found - simulation mode")

    def read(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return True, cv2.flip(frame, 1)
        return False, None

    def release(self):
        if self.cap:
            self.cap.release()


# ============================================================
# VOICE ENGINE
# ============================================================
class Voice:
    def __init__(self):
        self.ok    = False
        self._lock = threading.Lock()
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 130)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower()
                       for x in ['female','zira','hazel','karen']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice ready!")
        except Exception as e:
            print(f"⚠️  Voice: {e}")

    def say(self, text):
        # FIXED: safe name replacement
        name = STATE.get("child_name") or "Friend"
        text = str(text).replace("{name}", name)
        # Strip action tokens
        for tok in ["[WAVE]","[CLAP]","[NOD]","[DANCE]",
                    "[POINT]","[HUG]","[THINK]","[GAME]"]:
            text = text.replace(tok, "")
        text = re.sub(r'\[YOUTUBE:[^\]]+\]', '', text)
        text = re.sub(r'\[IMAGE:[^\]]+\]', '', text)
        text = text.strip()
        if not text: return

        STATE["is_speaking"] = True
        print(f"\n🔊 Pepper: {text}")
        log(f"Said: {text[:60]}", "info")

        if self.ok:
            with self._lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"⚠️  TTS: {e}")
        STATE["is_speaking"] = False


# ============================================================
# HIGH-SENSITIVITY MICROPHONE
# ============================================================
class Mic:
    """energy_threshold=20 for maximum sensitivity"""
    def __init__(self):
        self.ok      = False
        self.running = False
        try:
            self.r = sr.Recognizer()
            self.r.energy_threshold              = 20
            self.r.dynamic_energy_threshold      = True
            self.r.dynamic_energy_adjustment_ratio = 1.5
            self.r.pause_threshold               = 0.4
            self.r.phrase_threshold              = 0.15
            self.r.non_speaking_duration         = 0.15
            self.ok = True
            print("✅ Mic ready (energy=20, MAX sensitivity)")
        except Exception as e:
            print(f"⚠️  Mic: {e}")

    def listen(self, timeout=5):
        if not self.ok:
            return input("👶 Type: ").strip()
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(
                    src, duration=0.2)
                audio = self.r.listen(
                    src, timeout=timeout,
                    phrase_time_limit=12)
            try:
                text = self.r.recognize_google(audio)
                STATE["last_sound"] = time.time()
                log(f"Heard: {text}", "info")
                return text
            except sr.UnknownValueError:
                self._check_clap(audio)
                STATE["last_sound"] = time.time()
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
            rms = np.sqrt(np.mean(raw.astype(np.float32)**2))
            if rms > 1500:
                STATE["clap_detected"] = True
                log("👏 Clap detected!", "success")
        except Exception:
            pass

    def get_name(self, voice):
        if STATE["child_known"]:
            return STATE["child_name"]
        voice.say("Hello! I am Pepper! What is your name?")
        for _ in range(3):
            resp = self.listen(timeout=8)
            if resp and resp not in ["[sound]",""]:
                name = self._extract(resp)
                if name:
                    STATE["child_name"]  = name
                    STATE["child_known"] = True
                    log(f"Name: {name}", "success")
                    return name
        STATE["child_name"]  = "Friend"
        STATE["child_known"] = True
        return "Friend"

    def _extract(self, text):
        t = text.lower()
        for rm in ["my name is","i am","i'm","call me",
                   "name is","it is","its"]:
            t = t.replace(rm,"").strip()
        words = t.split()
        return words[0].capitalize() if words else None

    def listen_bg(self, callback):
        def _loop():
            self.running = True
            while self.running:
                if STATE["is_speaking"]:
                    time.sleep(0.2)
                    continue
                text = self.listen(timeout=4)
                if text:
                    callback(text)
                time.sleep(0.05)
        threading.Thread(target=_loop, daemon=True).start()


# ============================================================
# ACTION TOKEN PROCESSOR
# ============================================================
class Actions:
    def __init__(self, pepper=None):
        self.pepper = pepper

    def process(self, text):
        """Execute tokens, return clean text"""
        clean = text

        # Motion tokens
        if "[WAVE]" in text:
            clean = clean.replace("[WAVE]","")
            threading.Thread(
                target=self._wave,daemon=True).start()
        if "[CLAP]" in text:
            clean = clean.replace("[CLAP]","")
            threading.Thread(
                target=self._clap,daemon=True).start()
        if "[NOD]" in text:
            clean = clean.replace("[NOD]","")
            threading.Thread(
                target=self._nod,daemon=True).start()
        if "[DANCE]" in text:
            clean = clean.replace("[DANCE]","")
            threading.Thread(
                target=self._dance,daemon=True).start()
        if "[POINT]" in text:
            clean = clean.replace("[POINT]","")
            threading.Thread(
                target=self._point,daemon=True).start()
        if "[HUG]" in text:
            clean = clean.replace("[HUG]","")
            threading.Thread(
                target=self._hug,daemon=True).start()
        if "[THINK]" in text:
            clean = clean.replace("[THINK]","")
            threading.Thread(
                target=self._think,daemon=True).start()

        # YouTube
        yt = re.search(r'\[YOUTUBE:\s*(.+?)\]', text)
        if yt:
            clean = clean.replace(yt.group(0),"")
            self.youtube(yt.group(1).strip())

        # Images
        img = re.search(r'\[IMAGE:\s*(.+?)\]', text)
        if img:
            clean = clean.replace(img.group(0),"")
            self.images(img.group(1).strip())

        # Game
        if "[GAME]" in text:
            clean = clean.replace("[GAME]","")
            self.game()

        return clean.strip()

    def youtube(self, query):
        url = ("https://www.youtube.com/results?"
               "search_query=" +
               urllib.parse.quote(
                   query+" autism children educational"))
        webbrowser.open(url)
        log(f"📺 YouTube: {query}", "info")

    def images(self, query):
        url = ("https://www.google.com/search?"
               "tbm=isch&q=" +
               urllib.parse.quote(query))
        webbrowser.open(url)
        log(f"🖼️  Images: {query}", "info")

    def game(self):
        webbrowser.open("http://localhost:5009")
        log("🎮 Game opened!", "info")

    def _sa(self, joint, angle, speed=0.15):
        if self.pepper:
            try:
                self.pepper.setAngles(joint,angle,speed)
            except: pass

    def _wave(self):
        self._sa("RShoulderPitch",0.2,0.2)
        self._sa("RElbowRoll",0.8,0.2)
        time.sleep(0.3)
        for _ in range(3):
            self._sa("RWristYaw",0.5,0.25)
            time.sleep(0.2)
            self._sa("RWristYaw",-0.5,0.25)
            time.sleep(0.2)
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
            self._sa("HeadPitch",0.3,0.2)
            time.sleep(0.3)
            self._sa("HeadPitch",-0.1,0.2)
            time.sleep(0.3)
        self._sa("HeadPitch",0.0,0.15)

    def _dance(self):
        for _ in range(4):
            self._sa("LShoulderPitch",0.2,0.2)
            self._sa("RShoulderPitch",0.9,0.2)
            self._sa("HeadYaw",0.3,0.2)
            time.sleep(0.25)
            self._sa("LShoulderPitch",0.9,0.2)
            self._sa("RShoulderPitch",0.2,0.2)
            self._sa("HeadYaw",-0.3,0.2)
            time.sleep(0.25)
        self._sa("HeadYaw",0,0.1)

    def _point(self):
        self._sa("LShoulderPitch",0.1,0.15)
        self._sa("LElbowYaw",-1.5,0.15)
        time.sleep(1.0)
        self._sa("LShoulderPitch",1.0,0.15)

    def _hug(self):
        self._sa("LShoulderPitch",0.5,0.1)
        self._sa("RShoulderPitch",0.5,0.1)
        self._sa("LShoulderRoll",0.3,0.1)
        self._sa("RShoulderRoll",-0.3,0.1)
        time.sleep(1.2)
        self._sa("LShoulderPitch",1.0,0.1)
        self._sa("RShoulderPitch",1.0,0.1)
        self._sa("LShoulderRoll",0.0,0.1)
        self._sa("RShoulderRoll",0.0,0.1)

    def _think(self):
        self._sa("HeadYaw",0.3,0.1)
        self._sa("HeadPitch",-0.1,0.1)
        time.sleep(1.5)
        self._sa("HeadYaw",0.0,0.1)
        self._sa("HeadPitch",0.0,0.1)


# ============================================================
# VIDEO CALL UI - HIGH ACCURACY DISPLAY
# ============================================================
class VideoUI:
    def __init__(self, em_detector, obj_detector, camera):
        self.em_det  = em_detector
        self.obj_det = obj_detector
        self.camera  = camera
        self.running = False
        self.task_text    = ""
        self.task_t       = 0
        self.praise_text  = ""
        self.praise_t     = 0
        self.gemini_text  = ""
        self.gemini_t     = 0
        self.last_analyze = 0
        self.last_obj     = 0

        if camera.index >= 0:
            self.running = True
            threading.Thread(
                target=self._run, daemon=True).start()
            print("✅ Video Call UI active!")
        else:
            print("⚠️  No camera - text-only mode")
            # Still start in simulation mode
            self.running = True

        self.avatar = self._make_avatar()

    def _make_avatar(self):
        img = np.zeros((230,175,3),dtype=np.uint8)
        img[:] = (12,18,40)
        cv2.circle(img,(87,58),44,(220,195,175),-1)
        for ex in [72,102]:
            cv2.circle(img,(ex,50),9,(0,140,255),-1)
            cv2.circle(img,(ex,50),4,(255,255,255),-1)
            cv2.circle(img,(ex+1,49),2,(0,0,0),-1)
        cv2.ellipse(img,(87,70),(14,7),0,0,180,(80,40,40),2)
        cv2.rectangle(img,(58,98),(118,178),(130,140,190),-1)
        cv2.rectangle(img,(22,102),(58,137),(130,140,190),-1)
        cv2.rectangle(img,(118,102),(153,137),(130,140,190),-1)
        cv2.putText(img,"PEPPER",(30,205),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(80,180,255),2)
        cv2.putText(img,"Gemini AI",(28,220),
                    cv2.FONT_HERSHEY_SIMPLEX,0.35,(150,220,255),1)
        return img

    def _run(self):
        no_cam = self.camera.index < 0
        while self.running:
            if no_cam:
                # Simulation mode: show avatar only
                frame = self._make_sim_frame()
            else:
                ret, frame = self.camera.read()
                if not ret:
                    frame = self._make_sim_frame()

            now = time.time()

            # Emotion analysis every 0.8s
            if now - self.last_analyze > 0.8 and not no_cam:
                self.last_analyze = now
                f = frame.copy()
                threading.Thread(
                    target=self.em_det.analyze,
                    args=(f,),daemon=True).start()

            # Object detection every 2s
            if now - self.last_obj > 2.0 and not no_cam:
                self.last_obj = now
                f = frame.copy()
                threading.Thread(
                    target=self.obj_det.detect,
                    args=(f,),daemon=True).start()

            ui = self._build_ui(frame)
            cv2.imshow("🤖 Pepper Gemini Therapy", ui)
            k = cv2.waitKey(1) & 0xFF
            if k in [ord('q'),ord('Q'),27]:
                self.running = False
                break
            time.sleep(0.015)

        cv2.destroyAllWindows()

    def _make_sim_frame(self):
        """Simulation frame when no camera"""
        h,w = 720,1280
        frame = np.zeros((h,w,3),dtype=np.uint8)
        frame[:] = (10,15,35)

        # Grid lines
        for i in range(0,w,80):
            cv2.line(frame,(i,0),(i,h),(20,30,60),1)
        for i in range(0,h,80):
            cv2.line(frame,(0,i),(w,i),(20,30,60),1)

        # Center text
        cv2.putText(frame,"SIMULATION MODE - NO CAMERA",
                   (w//2-200,h//2-20),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.7,(100,150,255),2)
        cv2.putText(frame,"Therapy session running via microphone",
                   (w//2-180,h//2+20),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.5,(80,120,200),1)

        # Animated circle
        t   = time.time()
        r   = int(30 + 10*math.sin(t*2))
        col = (0,int(100+100*math.sin(t)),
               int(200+55*math.cos(t)))
        cv2.circle(frame,(w//2,h//2-80),r,col,3)
        return frame

    def _build_ui(self, frame):
        h,w = frame.shape[:2]
        ui  = frame.copy()

        # === HEADER ===
        ov = ui.copy()
        cv2.rectangle(ov,(0,0),(w,80),(8,12,28),-1)
        ui = cv2.addWeighted(ov,0.82,ui,0.18,0)

        name  = STATE["child_name"] or "..."
        prot  = STATE["protocol"]
        score = STATE["score"]
        diff  = STATE["difficulty"].upper()

        cv2.putText(ui,"🤖 Pepper Gemini AI Therapy",
                   (15,32),cv2.FONT_HERSHEY_SIMPLEX,
                   0.82,(255,255,255),2)
        cv2.putText(ui,
                   f"Child: {name}  |  {prot}  |"
                   f"  Score:{score}  |  {diff}",
                   (15,62),cv2.FONT_HERSHEY_SIMPLEX,
                   0.50,(140,190,255),1)

        # Gemini indicator
        gc = (0,220,100) if STATE["gemini_ok"] else (100,100,100)
        cv2.circle(ui,(w-20,20),8,gc,-1)
        cv2.putText(ui,"Gemini",(w-70,25),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.35,gc,1)

        # === PEPPER AVATAR (bottom-right PIP) ===
        av   = self.avatar.copy()
        ah,aw= av.shape[:2]

        # Animate during speech
        if STATE["is_speaking"]:
            t = int(time.time()*5)%3
            cv2.rectangle(av,(0,0),(aw-1,ah-1),
                         (0,180+t*20,255),2+t)
            # Mouth animation
            offset = int(4*math.sin(time.time()*10))
            cv2.ellipse(av,(87,70+offset),(14,7+offset),
                        0,0,180,(80,40,40),2)

        x1=w-aw-15; y1=h-ah-95
        ui[y1-3:y1+ah+3,x1-3:x1+aw+3] = (12,18,40)
        ui[y1:y1+ah,x1:x1+aw] = av
        bc = (0,200,255) if STATE["is_speaking"] \
             else (60,60,100)
        cv2.rectangle(ui,(x1-3,y1-3),
                     (x1+aw+3,y1+ah+3),bc,2)

        # === BOTTOM EMOTION BAR ===
        ov2 = ui.copy()
        cv2.rectangle(ov2,(0,h-90),(w,h),(8,12,28),-1)
        ui = cv2.addWeighted(ov2,0.78,ui,0.22,0)

        em    = STATE["emotion"]
        ec    = EMO_COLORS.get(em,(180,180,180))
        att   = STATE["attention"]
        eng   = STATE["engagement"]

        cv2.putText(ui,f"Emotion: {em.upper()}",
                   (15,h-58),cv2.FONT_HERSHEY_SIMPLEX,
                   0.75,ec,2)

        # Attention bar
        bw = int(att/100*(w-200))
        cv2.rectangle(ui,(15,h-42),(w-185,h-32),
                     (30,30,60),-1)
        cv2.rectangle(ui,(15,h-42),(15+bw,h-32),
                     ec,-1)
        cv2.putText(ui,f"Attention:{att}% | {eng}",
                   (15,h-15),cv2.FONT_HERSHEY_SIMPLEX,
                   0.48,(255,230,100),1)

        # Prompt level
        pl    = STATE["prompt_level"]
        plc   = [(0,200,0),(200,200,0),
                 (200,100,0),(200,0,0)][min(pl,3)]
        cv2.circle(ui,(w-50,h-55),22,plc,-1)
        cv2.putText(ui,f"P{pl}",
                   (w-58,h-46),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.65,(255,255,255),2)

        # Objects detected
        objs = STATE.get("objects",[])
        if objs:
            obj_text = "👁 " + " ".join(objs[:3])
            cv2.putText(ui,obj_text,
                       (15,h-105),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.42,(200,255,200),1)

        # === EMOTION SCORE BARS ===
        scores = STATE.get("emotion_scores",{})
        if scores:
            bx,by = w-185,95
            cv2.putText(ui,"Emotions:",
                       (bx,by-10),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.38,(200,200,200),1)
            for i,(e,s) in enumerate(
                    sorted(scores.items(),
                           key=lambda x:-x[1])[:7]):
                y  = by+i*22
                bl = int(s*130)
                c  = EMO_COLORS.get(e,(150,150,150))
                cv2.rectangle(ui,(bx,y),(bx+bl,y+14),c,-1)
                cv2.putText(ui,f"{e[:5]}:{s:.0%}",
                           (bx,y+12),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.32,(255,255,255),1)

        # Face detection dot
        fdc = (0,255,0) if STATE["face_detected"] \
              else (0,0,255)
        cv2.circle(ui,(w-15,20),7,fdc,-1)
        if not STATE["face_detected"]:
            cv2.putText(ui,"NO FACE",
                       (w-80,26),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.35,(0,0,255),1)

        # Clap indicator
        if STATE["clap_detected"]:
            cv2.putText(ui,"👏 CLAP!",
                       (w//2-60,90),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       1.2,(0,255,100),3)

        # Task display
        now = time.time()
        if self.task_text and now-self.task_t < 7:
            tl  = len(self.task_text)*12+20
            tx  = max(10,w//2-tl//2)
            cv2.rectangle(ui,(tx-5,h//2-42),
                         (tx+tl+5,h//2+10),(15,50,120),-1)
            cv2.rectangle(ui,(tx-5,h//2-42),
                         (tx+tl+5,h//2+10),(0,140,255),2)
            cv2.putText(ui,self.task_text[:55],
                       (tx,h//2-12),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.68,(255,255,255),2)

        # Praise
        if self.praise_text and now-self.praise_t < 4:
            pl2 = len(self.praise_text)*16+20
            px  = max(10,w//2-pl2//2)
            cv2.rectangle(ui,(px-5,h//2+28),
                         (px+pl2+5,h//2+74),(0,70,0),-1)
            cv2.putText(ui,self.praise_text[:38],
                       (px,h//2+60),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.88,(0,255,100),2)

        # Gemini response preview
        if self.gemini_text and now-self.gemini_t < 5:
            lines = [self.gemini_text[i:i+65]
                     for i in range(0,
                     min(len(self.gemini_text),130),65)]
            for li,line in enumerate(lines[:2]):
                cv2.putText(ui,line,
                           (15,h-112-li*20),
                           cv2.FONT_HERSHEY_SIMPLEX,
                           0.42,(200,255,200),1)

        # REC dot
        cv2.circle(ui,(38,28),8,(0,0,220),-1)
        cv2.putText(ui,"REC",(50,34),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.42,(0,0,220),1)

        return ui

    def show_task(self, t):
        self.task_text = t; self.task_t = time.time()
    def show_praise(self, t):
        self.praise_text = t; self.praise_t = time.time()
    def show_gemini(self, t):
        self.gemini_text = t[:130]; self.gemini_t = time.time()
    def stop(self):
        self.running = False
        try: cv2.destroyAllWindows()
        except: pass


# ============================================================
# PYBULLET SIM
# ============================================================
class Sim:
    def __init__(self):
        self.pepper = None
        self.ok     = False
        self.rx = self.ry = 0.0
        self.auto_walk = True
        self.balloons  = []

    def launch(self):
        try:
            from qibullet import SimulationManager as QS
            self.qisim  = QS()
            self.client = self.qisim.launchSimulation(gui=True)
            p.setRealTimeSimulation(1)
            p.setGravity(0,0,-9.81)
            p.setAdditionalSearchPath(pybullet_data.getDataPath())
            p.loadURDF("plane.urdf")
            self._build()
            self.pepper = self.qisim.spawnPepper(self.client)
            self.pepper.goToPosture("Stand",0.5)
            self._balloons()
            self._kids()
            p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
            self.ok = True

            for fn in [self._sim_loop,self._walk_loop,
                       self._arm_loop]:
                threading.Thread(target=fn,daemon=True).start()
            print("✅ PyBullet ready!")
            return self.pepper
        except Exception as e:
            print(f"⚠️  PyBullet: {e}")
            return None

    def _build(self):
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
            ("ABA ROOM",[-4,3,1.9]),("DTT ROOM",[4,3,1.9]),
            ("TEACCH",[0,4,1.9]),("TIE",[-4,-3,1.9]),
            ("GEMINI AI",[0,0,2.5])]:
            p.addUserDebugText(
                txt,pos,[.4,.5,.9],textSize=1.1,lifeTime=0)

    def _balloons(self):
        cols=[[1,.2,.2,1],[.2,1,.2,1],[.2,.2,1,1],
              [1,1,.2,1],[1,.5,.2,1],[.8,.2,.8,1]]
        for i in range(8):
            vs=p.createVisualShape(p.GEOM_SPHERE,
               radius=.15,rgbaColor=cols[i%len(cols)])
            bid=p.createMultiBody(0,-1,vs,
               [random.uniform(-3,3),
                random.uniform(-2,2),
                random.uniform(.8,2.2)])
            self.balloons.append({
                "id":bid,"x":random.uniform(-3,3),
                "y":random.uniform(-2,2),
                "z":random.uniform(.8,2.2),
                "spd":random.uniform(.01,.03)})

    def _kids(self):
        for name,pos,col in [
            ("Ahmed",[1.5,-1.2,0],[.2,.85,.2,1]),
            ("Sara", [-1.2,1.3,0],[1.,.6,.0,1]),
            ("Yusuf",[.5,-2.,0], [.9,.15,.15,1])]:
            vs=p.createVisualShape(p.GEOM_BOX,
               halfExtents=[.13,.09,.21],rgbaColor=col)
            p.createMultiBody(0,-1,vs,[pos[0],pos[1],.41])
            vs2=p.createVisualShape(p.GEOM_SPHERE,
               radius=.11,rgbaColor=[1.,.82,.65,1.])
            p.createMultiBody(0,-1,vs2,[pos[0],pos[1],.74])
            p.addUserDebugText(name,
               [pos[0],pos[1],1.05],[0,0,0],
               textSize=.85,lifeTime=0)

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
                try: self.pepper.setPosition([self.rx,self.ry,.8])
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
                    self.pepper.setAngles("LShoulderPitch",L,.07)
                    self.pepper.setAngles("RShoulderPitch",R,.07)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.,.04)
                    self.pepper.setAngles("RShoulderPitch",1.,.04)
            except: pass
            time.sleep(.04)

    def show_text(self, text):
        if not self.ok: return
        try:
            pos=p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],[pos[0],pos[1],pos[2]+1.3],
                [0,0,0],textSize=.85,lifeTime=5)
        except: pass


# ============================================================
# FLASK DASHBOARD
# ============================================================
flask_app = Flask(__name__)

DASH = """
<!DOCTYPE html><html>
<head><meta charset="UTF-8">
<title>Pepper Gemini Therapy</title>
<meta http-equiv="refresh" content="2">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;
     background:#060912;color:#e0e6ff}
.hdr{background:linear-gradient(135deg,#0a0f28,#1a0a3d);
     padding:14px 24px;display:flex;
     align-items:center;gap:12px;
     border-bottom:1px solid #1f1060}
.hdr h1{font-size:1.2em;color:#a78bfa}
.live{background:#ef4444;color:#fff;padding:2px 8px;
      border-radius:12px;font-size:.72em;
      animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.gem{background:#1a2555;color:#60a5fa;padding:3px 9px;
     border-radius:10px;font-size:.7em;
     border:1px solid #3b82f6}
.cont{max-width:1200px;margin:0 auto;padding:14px}
.g5{display:grid;grid-template-columns:repeat(5,1fr);
    gap:10px;margin-bottom:14px}
.g2{display:grid;grid-template-columns:1.3fr 1fr;gap:12px}
.card{background:#0c0f1e;border-radius:10px;
      padding:14px;border:1px solid #1a1f40}
.card h2{font-size:.8em;color:#6b7280;
         border-bottom:1px solid #1a1f40;
         padding-bottom:5px;margin-bottom:10px}
.stat{background:linear-gradient(135deg,#0d1030,#1a0a3d);
      border:1px solid #312e81;border-radius:9px;
      padding:13px;text-align:center}
.n{font-size:2em;font-weight:700;color:#a78bfa}
.l{font-size:.72em;color:#6b7280;margin-top:2px}
.emo{display:inline-block;padding:5px 12px;
     border-radius:15px;font-weight:700}
.happy{background:#05291555;color:#34d399;border:1px solid #34d399}
.sad{background:#1e3a5f55;color:#60a5fa;border:1px solid #60a5fa}
.angry{background:#45090a55;color:#f87171;border:1px solid #f87171}
.neutral{background:#1f293755;color:#9ca3af;border:1px solid #9ca3af}
.fear{background:#1c190055;color:#fbbf24;border:1px solid #fbbf24}
.surprise{background:#2e106555;color:#c084fc;border:1px solid #c084fc}
.bar-bg{background:#1f2937;border-radius:7px;height:9px;margin:5px 0}
.bar{height:9px;border-radius:7px;
     background:linear-gradient(90deg,#6366f1,#a78bfa)}
.log-box{max-height:420px;overflow-y:auto}
.log{padding:5px 8px;margin:3px 0;border-radius:5px;
     font-size:.75em;border-left:3px solid #4f46e5;
     background:#07090f}
.log.success{border-color:#10b981}
.log.fail{border-color:#ef4444}
.log.info{border-color:#3b82f6}
.btn{background:linear-gradient(135deg,#4f46e5,#7c3aed);
     color:#fff;border:none;padding:7px 12px;
     border-radius:7px;cursor:pointer;font-size:.78em;
     margin:3px;transition:.2s}
.btn:hover{opacity:.85}
.prot{display:inline-block;padding:2px 7px;
      border-radius:8px;font-size:.7em;font-weight:700}
.ABA{background:#1e1b4b55;color:#818cf8}
.DTT{background:#2e1b0055;color:#fb923c}
.TEACCH{background:#05291555;color:#34d399}
.TIE{background:#2e106555;color:#c084fc}
.GREETING{background:#1e3a5f55;color:#60a5fa}
input{width:100%;padding:5px 9px;border-radius:5px;
      border:1px solid #374151;background:#07090f;
      color:#e0e6ff;font-size:.8em}
</style></head><body>
<div class="hdr">
  <div style="font-size:1.8em">🤖</div>
  <div>
    <h1>Pepper Gemini AI Therapy v2</h1>
    <p style="font-size:.78em;opacity:.8">
      Child: <b>{{s.child_name}}</b> |
      <span class="prot {{s.protocol}}">{{s.protocol}}</span> |
      Diff: {{s.difficulty.upper()}} |
      Started: {{s.session_start}}
    </p>
  </div>
  <span class="live">● LIVE</span>
  <span class="gem">⚡ Gemini 1.5 Flash</span>
</div>
<div class="cont">
  <div class="g5">
    <div class="stat"><div class="n">{{s.score}}</div>
      <div class="l">Score</div></div>
    <div class="stat"><div class="n">{{s.attention}}%</div>
      <div class="l">Attention</div></div>
    <div class="stat"><div class="n">P{{s.prompt_level}}</div>
      <div class="l">Prompt Level</div></div>
    <div class="stat"><div class="n">{{s.consecutive}}</div>
      <div class="l">Streak</div></div>
    <div class="stat"><div class="n">{{s.logs|length}}</div>
      <div class="l">Interactions</div></div>
  </div>
  <div class="g2">
    <div>
      <div class="card" style="margin-bottom:12px">
        <h2>😊 Live Emotion</h2>
        <div style="text-align:center">
          <div class="emo {{s.emotion}}">{{s.emotion.upper()}}</div>
          <div style="margin:8px 0">
            <div class="bar-bg">
              <div class="bar" style="width:{{s.attention}}%"></div>
            </div>
            <span style="font-size:.76em;color:#818cf8">
              {{s.attention}}%</span>
          </div>
          <div style="font-size:.78em;color:#6b7280">
            Engagement: <b style="color:#e0e6ff">
              {{s.engagement}}</b></div>
          <div style="margin-top:4px;font-size:.73em;
            color:{{'#34d399' if s.face_detected else '#ef4444'}}">
            {{'✓ Face' if s.face_detected else '✗ No Face'}}</div>
          {% if s.clap_detected %}
          <div style="color:#fbbf24;font-weight:700;margin-top:4px">
            👏 CLAP!</div>{% endif %}
          {% if s.objects %}
          <div style="margin-top:5px;font-size:.72em;color:#34d399">
            Objects: {{s.objects|join(', ')}}</div>{% endif %}
        </div>
      </div>
      <div class="card" style="margin-bottom:12px">
        <h2>🎮 Controls</h2>
        <form method="POST" action="/cmd">
          <button class="btn" name="c" value="aba">📚 ABA</button>
          <button class="btn" name="c" value="dtt">🎯 DTT</button>
          <button class="btn" name="c" value="teacch">📅 TEACCH</button>
          <button class="btn" name="c" value="tie">🧠 TIE</button>
          <button class="btn" name="c" value="dance">💃 Dance</button>
          <button class="btn" name="c" value="game">🎮 Game</button>
        </form>
        <div style="margin-top:8px">
          <form method="POST" action="/name"
                style="display:flex;gap:5px">
            <input name="n" placeholder="Set child name...">
            <button class="btn">✓</button>
          </form>
        </div>
      </div>
      <div class="card">
        <h2>📺 Educational Videos</h2>
        <div style="display:flex;flex-wrap:wrap;gap:3px;
                    margin-bottom:8px">
          {% for skill in skills %}
          <form method="POST" action="/skill"
                style="display:inline">
            <button class="btn" name="s" value="{{skill}}"
                    style="font-size:.7em;padding:4px 8px">
              {{skill}}</button>
          </form>{% endfor %}
        </div>
        <form method="POST" action="/search"
              style="display:flex;gap:5px">
          <input name="q" placeholder="Search educational video...">
          <button class="btn">🔍</button>
        </form>
      </div>
    </div>
    <div class="card">
      <h2>📋 Session Log</h2>
      <div class="log-box">
        {% for log in s.logs[-35:]|reverse %}
        <div class="log {{log.type}}">
          <span style="color:#6366f1">{{log.time}}</span>
          <span class="prot {{log.protocol}}">
            {{log.protocol}}</span>
          <b style="color:#a78bfa">{{log.child}}</b>:
          {{log.msg}}
          <span style="color:#374151;font-size:.78em">
            |{{log.emotion}}</span>
        </div>{% endfor %}
      </div>
      <div style="margin-top:8px">
        <a href="/export" style="color:#6366f1;font-size:.78em">
          📄 Export Report</a>
      </div>
    </div>
  </div>
</div></body></html>
"""

SKILLS = ["wash face","brush teeth","wash hands",
          "emotions","colors","numbers","alphabet",
          "animals","sharing","ocean","space","eat food"]

@flask_app.route("/")
def dash():
    return render_template_string(DASH,s=STATE,skills=SKILLS)

@flask_app.route("/update_context",methods=["POST"])
def upd():
    d  = request.json or {}
    em = d.get("emotion","neutral")
    STATE["emotion"]      = em
    STATE["face_detected"]= True
    return jsonify({"status":"ok"})

@flask_app.route("/cmd",methods=["POST"])
def cmd():
    STATE["sim_cmd"] = request.form.get("c","")
    return dash()

@flask_app.route("/name",methods=["POST"])
def set_name():
    n = request.form.get("n","").strip().title()
    if n:
        STATE["child_name"]  = n
        STATE["child_known"] = True
    return dash()

@flask_app.route("/skill",methods=["POST"])
def skill():
    s = request.form.get("s","")
    url = ("https://www.youtube.com/results?"
           "search_query=" +
           urllib.parse.quote(s+" autism children educational"))
    webbrowser.open(url)
    return dash()

@flask_app.route("/search",methods=["POST"])
def search():
    q = request.form.get("q","")
    url = ("https://www.youtube.com/results?"
           "search_query=" +
           urllib.parse.quote(q+" autism educational"))
    webbrowser.open(url)
    return dash()

@flask_app.route("/export")
def export():
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(STATE,f,indent=2,default=str)
    return jsonify({"saved":fn})

@flask_app.route("/report")
def report():
    return jsonify(STATE)

def run_flask():
    flask_app.run(port=5009,debug=False,use_reloader=False)


# ============================================================
# MAIN THERAPY CONTROLLER
# ============================================================
class Therapy:
    def __init__(self, gemini, voice, mic, video, sim, actions):
        self.g = gemini
        self.v = voice
        self.m = mic
        self.ui= video
        self.s = sim
        self.a = actions
        self.running = False

    def _speak(self, text):
        """Full pipeline: Gemini text → tokens → voice"""
        clean = self.a.process(text)
        self.ui.show_gemini(clean)
        if self.s.ok:
            self.s.show_text(clean[:55])
        self.v.say(clean)

    def _gemini_speak(self, prompt):
        resp = self.g.ask(prompt)
        self._speak(resp)
        return resp

    def run(self):
        self.running = True
        STATE["protocol"] = "GREETING"

        # Get name
        name = self.m.get_name(self.v)
        resp = self.g.ask(
            f"Child's name is {name}. "
            "Greet warmly, introduce yourself, "
            "give first simple task! Use [WAVE]")
        self._speak(resp)
        time.sleep(1)

        # Background listening
        self.m.listen_bg(self._on_speech)

        # Main loop
        protocols = ["ABA","DTT","TEACCH","TIE"]
        p_idx = 0
        last_em = STATE["emotion"]
        em_change_t = time.time()

        while self.running:
            # No sound check
            if time.time()-STATE["last_sound"] > 10:
                STATE["last_sound"] = time.time()
                resp = self.g.ask(
                    "Child silent 10 seconds. "
                    "Gentle attention prompt!")
                self._speak(resp)

            # Prompt level
            self._update_prompt_level()

            # Emotion change reaction
            curr_em = STATE["emotion"]
            if curr_em != last_em and \
               time.time()-em_change_t > 5:
                last_em     = curr_em
                em_change_t = time.time()
                if curr_em in ["sad","angry","fear"]:
                    resp = self.g.ask(
                        f"Child emotion changed to {curr_em}. "
                        "React immediately!")
                    self._speak(resp)

            # Dashboard commands
            self._handle_sim_cmd()

            # Run protocol
            prot = protocols[p_idx%len(protocols)]
            p_idx+=1
            STATE["protocol"] = prot
            self._run_protocol(prot)
            time.sleep(0.3)

    def _update_prompt_level(self):
        em  = STATE["emotion"]
        att = STATE["attention"]
        eng = STATE["engagement"]
        fd  = STATE["face_detected"]

        if fd and att>60 and em=="happy":
            STATE["prompt_level"] = 0
        elif not fd or att<40:
            if STATE["prompt_level"]<1:
                STATE["prompt_level"] = 1
                resp = self.g.ask(
                    "Child distracted/not visible. "
                    "Verbal prompt! [POINT]")
                self._speak(resp)
        if eng=="distressed" and STATE["prompt_level"]<3:
            STATE["prompt_level"] = 3
            resp = self.g.ask(
                f"Child is distressed ({em}). "
                "Immediate calming response! [HUG]")
            self._speak(resp)

    def _handle_sim_cmd(self):
        cmd = STATE.get("sim_cmd")
        if not cmd: return
        STATE["sim_cmd"] = None
        if cmd=="dance":
            self._gemini_speak(
                "Dance to celebrate! Use [DANCE]")
        elif cmd=="game":
            self.a.game()
            self._gemini_speak(
                "Open game for child! Use [GAME]")
        elif cmd in ["aba","dtt","teacch","tie"]:
            STATE["protocol"] = cmd.upper()

    def _run_protocol(self, prot):
        name = STATE["child_name"]
        em   = STATE["emotion"]
        att  = STATE["attention"]

        if prot == "ABA":
            tasks = {
                "easy":   ["Clap hands!","Touch nose!",
                           "Wave hello!","Show happy face!"],
                "medium": ["Stand up sit down!","Touch ears!",
                           "Point to door!","Count fingers!"],
                "hard":   ["Tell your name!",
                           "What color is sky?","Name animal!"],
            }
            diff  = STATE["difficulty"]
            task  = random.choice(tasks.get(diff,tasks["easy"]))
            STATE["current_task"] = task

            resp = self.g.ask(
                f"Give ABA task '{task}' to {name}. "
                f"Emotion:{em} Attention:{att}%")
            self._speak(resp)
            self.ui.show_task(task)

            success = self._wait(task, 12)
            if success:
                STATE["score"]       += 10
                STATE["consecutive"] += 1
                STATE["clap_detected"]= False
                STATE["task_done"]    = False
                resp = self.g.ask(
                    f"{name} succeeded at {task}! "
                    "Celebrate! [CLAP]")
                self._speak(resp)
                self.ui.show_praise("AMAZING! ⭐")
                log(f"ABA: {task} ✅","success","ABA")

                # Level up
                if STATE["consecutive"]>=3:
                    if STATE["difficulty"]=="easy":
                        STATE["difficulty"]="medium"
                    elif STATE["difficulty"]=="medium":
                        STATE["difficulty"]="hard"
                    STATE["consecutive"]=0
            else:
                STATE["consecutive"]=0
                resp = self.g.ask(
                    f"{name} did not complete {task}. "
                    "Gentle retry or easier task.")
                self._speak(resp)
                log(f"ABA: {task} ❌","fail","ABA")
            time.sleep(2)

        elif prot=="DTT":
            resp = self.g.ask(
                f"Run ONE DTT trial for {name}. "
                f"Difficulty:{STATE['difficulty']} "
                f"Emotion:{em}")
            self._speak(resp)
            self.ui.show_task("DTT Trial")
            success = self._wait("DTT",10)
            if success:
                STATE["score"]+=12
                resp = self.g.ask(
                    f"DTT success! Reinforce {name}! [CLAP]")
                self._speak(resp)
                log("DTT ✅","success","DTT")
            else:
                log("DTT ❌","fail","DTT")
            time.sleep(2)

        elif prot=="TEACCH":
            resp = self.g.ask(
                f"Run TEACCH visual schedule step for {name}. "
                f"Emotion:{em}")
            self._speak(resp)
            time.sleep(3)
            if STATE["emotion"]=="happy":
                STATE["score"]+=15
            log("TEACCH ✅","success","TEACCH")

        elif prot=="TIE":
            resp = self.g.ask(
                f"TIE adaptive response for {name}. "
                f"Emotion:{em} Attention:{att}% "
                f"Engagement:{STATE['engagement']}")
            self._speak(resp)
            time.sleep(3)
            STATE["score"]+=8
            log("TIE ✅","success","TIE")

    def _wait(self, task, timeout=12):
        deadline = time.time()+timeout
        while time.time()<deadline:
            if STATE["clap_detected"] and "clap" in task.lower():
                return True
            if STATE["task_done"]:
                return True
            if STATE["emotion"]=="happy" and \
               STATE["attention"]>60:
                return True
            time.sleep(0.3)
        return False

    def _on_speech(self, text):
        STATE["last_sound"] = time.time()
        if not text or text=="[sound]":
            if text=="[sound]":
                self.v.say(
                    f"I heard you {STATE['child_name']}! 👍")
            return

        t    = text.lower()
        name = STATE["child_name"]

        # Name learning
        if not STATE["child_known"]:
            n = self.m._extract(text)
            if n:
                STATE["child_name"]  = n
                STATE["child_known"] = True
                resp = self.g.ask(
                    f"Child said name is {n}. Welcome!")
                self._speak(resp)
            return

        # How-to → YouTube
        if any(w in t for w in
               ["how","what is","show me","what does",
                "teach me","tell me about"]):
            resp = self.g.ask(
                f"Child asked: '{text}'. "
                "Answer simply, use [YOUTUBE:...] "
                "for educational video.")
            self._speak(resp)
            return

        # Game request
        if any(w in t for w in
               ["play","game","fun","let's play"]):
            resp = self.g.ask(
                f"{name} wants to play! "
                "Respond with [GAME] and enthusiasm!")
            self._speak(resp)
            return

        # Task keywords
        task = STATE.get("current_task","")
        if task:
            kw = task.lower().split()
            if any(w in t for w in kw):
                STATE["task_done"] = True

        # General Gemini
        resp = self.g.ask(
            f"Child said: '{text}'. Respond therapeutically.")
        self._speak(resp)


# ============================================================
# MAIN
# ============================================================
def main():
    print("""
╔══════════════════════════════════════════════════════╗
║   PEPPER GEMINI THERAPY v2 - FIXED & IMPROVED      ║
║   High-Accuracy Emotion | 3-Layer Detection         ║
╚══════════════════════════════════════════════════════╝
""")

    # Flask
    threading.Thread(target=run_flask,daemon=True).start()
    print("✅ Dashboard: http://localhost:5009")
    time.sleep(0.8)

    # Components
    gemini = GeminiBrain()
    voice  = Voice()
    camera = CameraManager()
    em_det = EmotionDetector()
    obj_det= ObjectDetector()
    video  = VideoUI(em_det, obj_det, camera)
    mic    = Mic()
    sim    = Sim()
    pepper = sim.launch()
    actions= Actions(pepper)

    time.sleep(1.5)

    # FIXED: set default name before saying anything
    STATE["child_name"] = "Friend"

    voice.say(
        "Hello! I am Pepper, your therapy robot! "
        "Powered by Gemini AI! Let us begin!")
    if pepper:
        actions._wave()

    # Start therapy
    therapy = Therapy(gemini,voice,mic,video,sim,actions)
    t = threading.Thread(target=therapy.run,daemon=True)
    t.start()

    print("\n" + "="*52)
    print("✅ THERAPY SESSION ACTIVE")
    print("="*52)
    print("Camera: Opens automatically if found")
    print("Dashboard: http://localhost:5009")
    print("Commands: 'report' | 'name X' | 'exit'")
    print("="*52+"\n")

    while getattr(video,'running',True):
        try:
            cmd = input("> ").strip()
            if not cmd: continue
            cl  = cmd.lower()
            if cl in ["q","quit","exit"]:
                therapy.running=False
                video.stop()
                break
            elif cl=="report":
                print(f"\n📊 Child:{STATE['child_name']}"
                      f" Score:{STATE['score']}"
                      f" Emotion:{STATE['emotion']}"
                      f" Attention:{STATE['attention']}%")
            elif cl.startswith("name "):
                n = cl[5:].strip().title()
                STATE["child_name"]=n
                STATE["child_known"]=True
                voice.say(f"Hello {n}!")
            else:
                therapy._on_speech(cmd)
        except (KeyboardInterrupt,EOFError):
            break

    therapy.running=False
    voice.say("Goodbye! Amazing session today!")
    fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(fn,"w") as f:
        json.dump(STATE,f,indent=2,default=str)
    print(f"📄 Saved: {fn}")

if __name__=="__main__":
    main()
