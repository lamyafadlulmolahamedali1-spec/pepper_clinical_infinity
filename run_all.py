#!/usr/bin/env python3
"""
FULL ASD THERAPY - PyBullet + Pepper + Kids + Voice + Emotion + Report
Run: python3 run_all.py
"""

import sys, time, math, random, threading, json, os
import pybullet as p
import pybullet_data
import pyttsx3
from datetime import datetime

sys.path.insert(0, '/home/lamya/pepper_duo/src')
from qibullet import SimulationManager

# ========== VOICE ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 140)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice ready!")
        except Exception as e:
            print(f"⚠️  Voice: {e}")
            self.ok = False

    def say(self, text):
        print(f"🔊 Pepper: {text}")
        if not self.ok: return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except: pass

# ========== EMOTION DETECTOR ==========
class EmotionDetector:
    def __init__(self):
        self.current_emotion  = "neutral"
        self.attention_score  = 70
        self.engagement_level = "moderate"
        self.face_detected    = True
        self.emotion_counts   = {}
        self.emotion_history  = []
        self.cap              = None
        self.deepface_ok      = False
        self.mediapipe_ok     = False

        # DeepFace
        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            self.deepface_ok = True
            print("✅ DeepFace ready!")
        except: print("⚠️  DeepFace not available - using simulation")

        # MediaPipe
        try:
            import mediapipe as mp
            self.mp_face  = mp.solutions.face_mesh
            self.face_mesh= self.mp_face.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5)
            self.mediapipe_ok = True
            print("✅ MediaPipe ready!")
        except: print("⚠️  MediaPipe not available")

        # Webcam
        try:
            import cv2
            self.cv2 = cv2
            self.cap  = cv2.VideoCapture(0)
            if self.cap.isOpened():
                print("✅ Webcam ready!")
                threading.Thread(target=self._camera_loop, daemon=True).start()
            else:
                self.cap = None
                threading.Thread(target=self._simulate, daemon=True).start()
        except:
            threading.Thread(target=self._simulate, daemon=True).start()

    def _camera_loop(self):
        fc = 0
        while True:
            ret, frame = self.cap.read()
            if not ret: continue
            fc += 1

            if self.deepface_ok and fc % 15 == 0:
                threading.Thread(
                    target=self._analyze_deepface,
                    args=(frame.copy(),), daemon=True).start()

            if self.mediapipe_ok:
                self._analyze_mediapipe(frame)

            # عرض نافذة الكاميرا
            self._draw_overlay(frame)
            self.cv2.imshow("Pepper Vision - Emotion Monitor", frame)
            self.cv2.waitKey(1)
            time.sleep(0.033)

    def _analyze_deepface(self, frame):
        try:
            result = self.DeepFace.analyze(
                frame, actions=['emotion'],
                enforce_detection=False, silent=True)
            if result:
                emotion = result[0]['dominant_emotion']
                self.current_emotion = emotion
                self.face_detected   = True
                self.emotion_counts[emotion] = \
                    self.emotion_counts.get(emotion, 0) + 1
                self.emotion_history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "emotion": emotion
                })
                # engagement
                scores = result[0]['emotion']
                pos = scores.get('happy',0) + scores.get('surprise',0)
                neg = scores.get('sad',0) + scores.get('angry',0) + \
                      scores.get('fear',0)
                if pos > 40:   self.engagement_level = "high"
                elif neg > 50: self.engagement_level = "distressed"
                else:          self.engagement_level = "moderate"
        except: pass

    def _analyze_mediapipe(self, frame):
        try:
            rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
            res = self.face_mesh.process(rgb)
            if res.multi_face_landmarks:
                self.face_detected    = True
                self.attention_score  = min(100, self.attention_score + 2)
            else:
                self.face_detected   = False
                self.attention_score = max(0, self.attention_score - 3)
        except: pass

    def _draw_overlay(self, frame):
        colors = {
            "happy":(0,255,0),"sad":(255,0,0),
            "angry":(0,0,255),"neutral":(200,200,200),
            "fear":(0,165,255),"surprise":(0,255,255)
        }
        col = colors.get(self.current_emotion,(255,255,255))
        self.cv2.putText(frame,
            f"Emotion: {self.current_emotion}",
            (10,35), self.cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
        self.cv2.putText(frame,
            f"Attention: {self.attention_score}%",
            (10,70), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        self.cv2.putText(frame,
            f"Engagement: {self.engagement_level}",
            (10,105), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        status = "✓ FACE" if self.face_detected else "✗ NO FACE"
        self.cv2.putText(frame, status,
            (10,140), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (0,255,0) if self.face_detected else (0,0,255), 2)

    def _simulate(self):
        """محاكاة المشاعر لو ما في كاميرا"""
        pool = ["happy","happy","neutral","neutral","sad","surprise"]
        while True:
            self.current_emotion  = random.choice(pool)
            self.face_detected    = random.random() > 0.15
            self.attention_score  = random.randint(45, 92)
            self.engagement_level = random.choice(
                ["high","moderate","moderate","low"])
            self.emotion_counts[self.current_emotion] = \
                self.emotion_counts.get(self.current_emotion, 0) + 1
            self.emotion_history.append({
                "time":    datetime.now().strftime("%H:%M:%S"),
                "emotion": self.current_emotion
            })
            time.sleep(4)

    def get_state(self):
        return {
            "emotion":      self.current_emotion,
            "attention":    self.attention_score,
            "engagement":   self.engagement_level,
            "face_detected": self.face_detected
        }

    def stop(self):
        if self.cap:
            self.cap.release()
        try:
            self.cv2.destroyAllWindows()
        except: pass

# ========== ASD CHILD ==========
class ASDChild:
    SEVERITY_PARAMS = {
        "mild":     {"response":0.75,"attention":12,"meltdown":0.05,"repetitive":0.20},
        "moderate": {"response":0.45,"attention":7, "meltdown":0.15,"repetitive":0.45},
        "severe":   {"response":0.15,"attention":3, "meltdown":0.35,"repetitive":0.75},
    }
    BEHAVIORS = {
        "mild":     ["wandering","smiling","brief_eye_contact","pointing"],
        "moderate": ["hand_flapping","rocking","ignoring","fixating"],
        "severe":   ["spinning","covering_ears","running_away","self_stimming"],
    }
    COLORS = {
        "mild":     [0.2,0.85,0.2,1],
        "moderate": [1.0,0.60,0.0,1],
        "severe":   [0.9,0.15,0.15,1],
    }

    def __init__(self, name, base_pos, severity):
        self.name       = name
        self.base_pos   = list(base_pos)
        self.pos        = list(base_pos)
        self.severity   = severity
        self.params     = self.SEVERITY_PARAMS[severity]
        self.behavior   = "wandering"
        self.emotion    = "calm"
        self.is_meltdown= False
        self.meltdown_t = 0
        self.last_change= time.time()
        self.wander_vel = [random.uniform(-0.006,0.006),
                           random.uniform(-0.006,0.006)]
        self.wander_off = [0.0, 0.0]
        self.interactions = 0
        self.successes    = 0
        self.score        = 0
        self.torso_id     = None
        self.head_id      = None
        self._build()

    def _build(self):
        col  = self.COLORS[self.severity]
        skin = [1.0, 0.82, 0.65, 1.0]
        vs = p.createVisualShape(
            p.GEOM_BOX, halfExtents=[0.13,0.09,0.21], rgbaColor=col)
        cs = p.createCollisionShape(
            p.GEOM_BOX, halfExtents=[0.13,0.09,0.21])
        self.torso_id = p.createMultiBody(
            0, cs, vs, [self.pos[0], self.pos[1], 0.41])
        vs2 = p.createVisualShape(
            p.GEOM_SPHERE, radius=0.11, rgbaColor=skin)
        cs2 = p.createCollisionShape(
            p.GEOM_SPHERE, radius=0.11)
        self.head_id = p.createMultiBody(
            0, cs2, vs2, [self.pos[0], self.pos[1], 0.74])
        emoji = {"mild":"🟢","moderate":"🟠","severe":"🔴"}
        p.addUserDebugText(
            f"{self.name} {emoji[self.severity]}",
            [self.pos[0], self.pos[1], 1.05],
            [0,0,0], textSize=0.9, lifeTime=0)

    def update(self):
        now = time.time()
        if now - self.last_change > self.params["attention"]:
            self.last_change = now
            if not self.is_meltdown and \
               random.random() < self.params["meltdown"]:
                self.is_meltdown = True
                self.meltdown_t  = now
                self.emotion     = "overwhelmed"
                self.behavior    = random.choice(
                    self.BEHAVIORS[self.severity])
                print(f"[{self.name}] ⚠️  MELTDOWN: {self.behavior}")
            elif self.is_meltdown and now - self.meltdown_t > 10:
                self.is_meltdown = False
                self.emotion     = "calm"
                self.behavior    = "wandering"
                print(f"[{self.name}] ✅ Calmed down")
            else:
                pool = self.BEHAVIORS[self.severity] \
                    if random.random() < self.params["repetitive"] \
                    else ["wandering","neutral"]
                self.behavior = random.choice(pool)
                self.emotion  = random.choice(
                    ["calm","happy","anxious","sad","excited"])

        spd = 0.005 if not self.is_meltdown else 0.009
        self.wander_vel[0] += random.uniform(-0.001, 0.001)
        self.wander_vel[1] += random.uniform(-0.001, 0.001)
        self.wander_vel[0]  = max(-spd, min(spd, self.wander_vel[0]))
        self.wander_vel[1]  = max(-spd, min(spd, self.wander_vel[1]))
        self.wander_off[0] += self.wander_vel[0]
        self.wander_off[1] += self.wander_vel[1]
        if abs(self.wander_off[0]) > 0.4: self.wander_vel[0] *= -1
        if abs(self.wander_off[1]) > 0.4: self.wander_vel[1] *= -1
        self.pos[0] = self.base_pos[0] + self.wander_off[0]
        self.pos[1] = self.base_pos[1] + self.wander_off[1]
        try:
            p.resetBasePositionAndOrientation(
                self.torso_id,
                [self.pos[0], self.pos[1], 0.41], [0,0,0,1])
            p.resetBasePositionAndOrientation(
                self.head_id,
                [self.pos[0], self.pos[1], 0.74], [0,0,0,1])
        except: pass

    def respond(self, action, emotion_state):
        self.interactions += 1
        if self.is_meltdown: return False
        base = self.params["response"]
        if emotion_state.get("emotion") == "happy":    base += 0.15
        if emotion_state.get("attention", 50) > 70:    base += 0.10
        if emotion_state.get("engagement") == "high":  base += 0.10
        if emotion_state.get("engagement") == "distressed": base -= 0.20
        ok = random.random() < max(0.05, min(0.95, base))
        if ok:
            self.successes += 1
            self.score     += 10
        return ok

    def success_rate(self):
        if not self.interactions: return 0
        return round(self.successes / self.interactions * 100, 1)

# ========== MAIN SIMULATION ==========
class FullTherapySim:
    def __init__(self):
        self.voice    = Voice()
        self.detector = EmotionDetector()

        # PyBullet
        self.sim_mgr = SimulationManager()
        self.client  = self.sim_mgr.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        self._build_room()

        # Pepper
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_mgr.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        self.rx = 0.0
        self.ry = 0.0
        self.head_yaw  = 0.0
        self.auto_walk = True
        self.is_talking= False

        # أطفال
        self.children = [
            ASDChild("Ahmed", [ 1.5, -1.2, 0], "mild"),
            ASDChild("Sara",  [-1.2,  1.3, 0], "moderate"),
            ASDChild("Yusuf", [ 0.5, -2.0, 0], "severe"),
            ASDChild("Layla", [ 2.8, -0.2, 0], "moderate"),
            ASDChild("Omar",  [-2.2, -1.0, 0], "mild"),
        ]

        # Session data
        self.session_log   = []
        self.session_start = datetime.now()
        self.kid_idx       = 0
        self.current_protocol = "ABA"

        # Threads
        threading.Thread(target=self._sim_loop,      daemon=True).start()
        threading.Thread(target=self._children_loop, daemon=True).start()
        threading.Thread(target=self._walk_loop,     daemon=True).start()
        threading.Thread(target=self._arm_loop,      daemon=True).start()

        p.resetDebugVisualizerCamera(
            7, 45, -35, [0,0,0.5])
        time.sleep(2)

        intro = "Hello everyone! I am Pepper. Starting therapy session!"
        self._speak_show(intro)
        threading.Thread(
            target=self._therapy_loop, daemon=True).start()

        print("\n" + "="*55)
        print("✅ FULL THERAPY SIMULATION RUNNING")
        print("="*55)
        print("Commands: 'report' | 'skip' | 'exit'")
        print("="*55 + "\n")

    def _build_room(self):
        print("🏠 Building therapy room...")
        wc = [0.85, 0.85, 0.9, 1]
        for pos, ext in [
            ([0,-4,1.1],[5,0.1,1.1]), ([0,4,1.1],[5,0.1,1.1]),
            ([5,0,1.1],[0.1,4,1.1]), ([-5,0,1.1],[0.1,4,1.1])]:
            p.createMultiBody(0,-1,
                p.createVisualShape(
                    p.GEOM_BOX,halfExtents=ext,rgbaColor=wc), pos)
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[4.5,3.5,0.02],
                rgbaColor=[0.6,0.5,0.4,1]), [0,0,0.01])
        p.createMultiBody(0,-1,
            p.createVisualShape(p.GEOM_BOX,
                halfExtents=[0.8,0.6,0.35],
                rgbaColor=[0.55,0.35,0.15,1]), [2,1.5,0.35])
        # protocol signs
        protocols = [
            ("ABA",   [-3, 3, 1.5]),
            ("TEACCH",[ 0, 3.5, 1.5]),
            ("DTT",   [ 3, 3, 1.5]),
            ("TIE",   [-3,-3, 1.5]),
        ]
        for name, pos in protocols:
            p.addUserDebugText(
                name, pos, [0.2,0.2,0.8],
                textSize=1.5, lifeTime=0)
        print("✅ Room ready!")

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            time.sleep(1/240.)

    def _children_loop(self):
        while True:
            for c in self.children:
                c.update()
            time.sleep(0.05)

    def _walk_loop(self):
        t = 0
        while True:
            if self.auto_walk:
                t += 0.015
                self.rx += 0.018 * math.cos(t * 0.4)
                self.ry += 0.018 * math.sin(t * 0.5)
                self.rx = max(-3.5, min(3.5, self.rx))
                self.ry = max(-2.8, min(2.8, self.ry))
                try:
                    self.pepper.setPosition(
                        [self.rx, self.ry, 0.8])
                except: pass
            time.sleep(0.06)

    def _arm_loop(self):
        """أيدي سلسة أثناء الكلام"""
        phase = 0
        while True:
            try:
                if self.is_talking:
                    phase += 0.07
                    L = 0.5 + 0.3 * math.sin(phase)
                    R = 0.5 + 0.3 * math.sin(phase + math.pi * 0.6)
                    self.pepper.setAngles("LShoulderPitch", L, 0.07)
                    self.pepper.setAngles("RShoulderPitch", R, 0.07)
                    self.pepper.setAngles("LElbowRoll",
                        -0.3 - 0.15*math.sin(phase*0.7), 0.07)
                    self.pepper.setAngles("RElbowRoll",
                        0.3 + 0.15*math.sin(phase*0.7), 0.07)
                else:
                    self.pepper.setAngles("LShoulderPitch",1.0,0.04)
                    self.pepper.setAngles("RShoulderPitch",1.0,0.04)
                    self.pepper.setAngles("LElbowRoll",-0.2,0.04)
                    self.pepper.setAngles("RElbowRoll", 0.2,0.04)
            except: pass
            time.sleep(0.04)

    def _move_to_child(self, child):
        """Pepper تتحرك للطفل وتقف أمامه"""
        self.auto_walk = False
        tx, ty = child.pos[0], child.pos[1]

        for _ in range(100):
            dx = tx - self.rx
            dy = ty - self.ry
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 0.85: break

            step = min(0.055, dist - 0.75)
            self.rx += dx / dist * step
            self.ry += dy / dist * step

            # رأس ينظر للطفل
            self.head_yaw = math.atan2(dy, dx)
            try:
                self.pepper.setPosition([self.rx, self.ry, 0.8])
                self.pepper.setAngles(
                    "HeadYaw", self.head_yaw * 0.5, 0.1)
                self.pepper.setAngles("HeadPitch", -0.1, 0.08)
            except: pass
            time.sleep(0.04)

        # اتجه للطفل مباشرة
        dx = tx - self.rx
        dy = ty - self.ry
        self.head_yaw = math.atan2(dy, dx)
        try:
            self.pepper.setAngles(
                "HeadYaw", self.head_yaw * 0.5, 0.12)
        except: pass
        time.sleep(0.5)

    def _speak_show(self, text):
        """تكلم + حرك + عرض نص في PyBullet"""
        self.is_talking = True
        try:
            pos = p.getBasePositionAndOrientation(
                self.pepper.body)[0]
            p.addUserDebugText(
                text[:55],
                [pos[0], pos[1], pos[2]+1.25],
                [0,0,0], textSize=0.85, lifeTime=5)
        except: pass
        self.voice.say(text)
        self.is_talking = False

    def _log(self, event, detail, result, child=None):
        state = self.detector.get_state()
        entry = {
            "time":      datetime.now().strftime("%H:%M:%S"),
            "protocol":  self.current_protocol,
            "event":     event,
            "detail":    detail,
            "result":    result,
            "emotion":   state["emotion"],
            "attention": state["attention"],
            "child":     child.name if child else "-"
        }
        self.session_log.append(entry)
        print(f"[{entry['time']}][{self.current_protocol}] "
              f"{event} | {detail} → {result} "
              f"| 😊{state['emotion']} 👁️{state['attention']}%")

    def _adapt_to_emotion(self, child):
        """تكيّف Pepper مع مشاعر الطفل"""
        state = self.detector.get_state()
        if state["engagement"] == "distressed" or \
           state["emotion"] in ["angry","fear"]:
            self._speak_show(
                f"It is okay {child.name}. "
                "Let us breathe together. In... out...")
            self._log("adaptation","distressed_detected",
                "sensory_break", child)
            time.sleep(3)
            return "break"
        if state["attention"] < 30:
            self._speak_show(
                f"Hey {child.name}! Look at me!")
            self._log("adaptation","low_attention",
                "redirect", child)
            return "redirect"
        return "continue"

    # ===== ABA Protocol =====
    def _run_aba(self, child, trials=4):
        self.current_protocol = "ABA"
        print(f"\n{'='*45}")
        print(f"📚 ABA - {child.name} ({child.severity})")
        print(f"{'='*45}")
        self._speak_show(
            f"Hello {child.name}! Let us do ABA therapy!")
        self._log("ABA_start", child.name,
            child.severity, child)

        reinforcers = ["Amazing!","Super star!",
                       "You did it!","Wonderful!","Great job!"]
        instructions = {
            "mild":   ["Point to the ball","Show me happy face",
                       "What color is this?","Can you count to 3?"],
            "moderate":["Clap your hands","Touch your nose",
                        "Wave hello","Stand up"],
            "severe": ["Look at me","Touch nose","Clap","Wave"],
        }

        for i in range(trials):
            action = self._adapt_to_emotion(child)
            if action == "break":
                time.sleep(2)
                continue

            instr = random.choice(instructions[child.severity])
            self._speak_show(f"{child.name}, {instr}!")
            self._log("DTT_trial", instr, "prompted", child)
            time.sleep(1.5)

            state     = self.detector.get_state()
            responded = child.respond("ABA", state)

            if responded:
                r = random.choice(reinforcers)
                self._speak_show(r)
                self._log("DTT_result", instr, f"SUCCESS-{r}", child)
                # احتفال
                self.is_talking = True
                try:
                    for _ in range(2):
                        self.pepper.setAngles(
                            "LShoulderPitch",0.1,0.2)
                        self.pepper.setAngles(
                            "RShoulderPitch",0.1,0.2)
                        time.sleep(0.2)
                        self.pepper.setAngles(
                            "LShoulderPitch",0.9,0.2)
                        self.pepper.setAngles(
                            "RShoulderPitch",0.9,0.2)
                        time.sleep(0.2)
                except: pass
                self.is_talking = False
            else:
                self._speak_show(
                    f"Let us try again {child.name}! {instr}")
                self._log("DTT_result", instr,
                    "NO_RESPONSE", child)
            time.sleep(2)

    # ===== TEACCH Protocol =====
    def _run_teacch(self, child):
        self.current_protocol = "TEACCH"
        print(f"\n{'='*45}")
        print(f"📅 TEACCH - {child.name}")
        print(f"{'='*45}")
        schedule = [
            ("🌅","Greeting",
             f"Good morning {child.name}! How are you today?"),
            ("😊","Emotion Check",
             f"{child.name}, show me a happy face!"),
            ("📚","Work Task",
             f"Let us sort these colors {child.name}!"),
            ("🎯","Sensory Break",
             "Let us breathe together. In and out..."),
            ("👀","Joint Attention",
             f"Look {child.name}! See the red ball!"),
            ("⭐","Closing",
             f"Great job {child.name}! All done!"),
        ]
        self._speak_show(
            f"Hello {child.name}! Let us check our schedule!")
        self._log("TEACCH_start", child.name,
            "visual_schedule", child)

        for emoji, activity, text in schedule:
            action = self._adapt_to_emotion(child)
            if action == "break":
                time.sleep(2)

            print(f"\n{emoji} {activity}")
            self._speak_show(text)
            self._log("TEACCH_activity", activity,
                "in_progress", child)

            state     = self.detector.get_state()
            responded = child.respond("TEACCH", state)
            result    = "success" if responded else "needs_support"

            if responded:
                child.score += 15
                self._speak_show("Excellent! Well done!")
            self._log("TEACCH_result", activity, result, child)
            time.sleep(2)

    # ===== DTT Protocol =====
    def _run_dtt(self, child, trials=5):
        self.current_protocol = "DTT"
        print(f"\n{'='*45}")
        print(f"🎯 DTT - {child.name}")
        print(f"{'='*45}")
        self._speak_show(
            f"DTT time {child.name}! Listen carefully!")
        self._log("DTT_start", child.name,
            child.severity, child)

        prompts = ["verbal","gestural","physical","visual"]
        tasks   = [
            ("Clap your hands","clap"),
            ("Touch your nose","nose"),
            ("Stand up","stand"),
            ("Wave hello","wave"),
            ("Point to the door","point"),
        ]

        for i in range(trials):
            action = self._adapt_to_emotion(child)
            if action == "break":
                time.sleep(2)
                continue

            task_text, task_type = random.choice(tasks)
            prompt = random.choice(prompts)
            self._speak_show(
                f"{child.name}, {task_text}! [{prompt} prompt]")
            self._log("DTT_instruction",
                f"{task_text} [{prompt}]", "waiting", child)
            time.sleep(1.5)

            state     = self.detector.get_state()
            responded = child.respond("DTT", state)

            if responded:
                child.score += 12
                self._speak_show(
                    random.choice(["Amazing!","Super!","Yes!"]))
                self._log("DTT_response",
                    task_text, "CORRECT", child)
            else:
                self._speak_show(
                    f"Error correction: {task_text}")
                self._log("DTT_response",
                    task_text, "ERROR_CORRECTION", child)
            time.sleep(2)

    # ===== TIE Protocol =====
    def _run_tie(self, child):
        self.current_protocol = "TIE"
        print(f"\n{'='*45}")
        print(f"🧠 TIE - {child.name}")
        print(f"{'='*45}")
        self._speak_show(
            f"Hello {child.name}. I am watching and adapting for you!")
        self._log("TIE_start", child.name,
            "adaptive_mode", child)

        for _ in range(6):
            state = self.detector.get_state()

            # قرار TIE
            if state["engagement"] == "distressed":
                decision = "calm_down"
                self._speak_show(
                    "Let us calm down. Breathe with me slowly.")
                time.sleep(3)
            elif state["attention"] < 35:
                decision = "redirect"
                self._speak_show(
                    f"Hey {child.name}! Look here!")
            elif state["emotion"] == "happy" and \
                 state["attention"] > 65:
                decision = "advance"
                task = random.choice([
                    "Can you do two things? Clap then wave!",
                    "Tell me your name!",
                    "What color is the ball?"])
                self._speak_show(task)
                responded = child.respond("TIE_advance", state)
                if responded:
                    child.score += 20
                    self._speak_show(
                        "Incredible! You are a champion!")
            else:
                decision = "maintain"
                self._speak_show(
                    f"Good {child.name}! Keep going!")
                responded = child.respond("TIE", state)
                if responded:
                    child.score += 10
                    self._speak_show("Well done!")

            self._log("TIE_decision", decision,
                f"emotion={state['emotion']}", child)
            time.sleep(2.5)

    # ===== MAIN THERAPY LOOP =====
    def _therapy_loop(self):
        print("\n🏥 THERAPY LOOP STARTED!\n")
        time.sleep(2)

        protocols = ["ABA","TEACCH","DTT","TIE"]
        p_idx = 0

        while True:
            child    = self.children[self.kid_idx % len(self.children)]
            protocol = protocols[p_idx % len(protocols)]
            self.kid_idx += 1
            p_idx   += 1

            print(f"\n[THERAPY] 🚶 → {child.name} | Protocol: {protocol}")

            # Pepper تتحرك للطفل
            self._move_to_child(child)
            time.sleep(0.3)

            # تنفيذ البروتوكول
            if protocol == "ABA":
                self._run_aba(child, trials=3)
            elif protocol == "TEACCH":
                self._run_teacch(child)
            elif protocol == "DTT":
                self._run_dtt(child, trials=3)
            elif protocol == "TIE":
                self._run_tie(child)

            # تقرير مصغر
            print(f"\n[{child.name}] "
                  f"Rate:{child.success_rate()}% "
                  f"Score:{child.score} "
                  f"Emotion:{self.detector.current_emotion}")

            self.auto_walk = True
            time.sleep(8)

    # ===== REPORT =====
    def generate_report(self):
        duration = (datetime.now() - self.session_start).seconds // 60
        data = {
            "date":     datetime.now().strftime("%Y-%m-%d"),
            "time":     self.session_start.strftime("%H:%M"),
            "duration": duration,
            "children": [],
            "emotion_summary": self.detector.emotion_counts,
            "session_log":     self.session_log
        }
        for c in self.children:
            data["children"].append({
                "name":         c.name,
                "severity":     c.severity,
                "interactions": c.interactions,
                "successes":    c.successes,
                "success_rate": c.success_rate(),
                "score":        c.score
            })

        # حفظ JSON
        fn = f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(fn,"w") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Report saved: {fn}")

        # طباعة ملخص
        print("\n" + "="*55)
        print("📊 SESSION REPORT")
        print("="*55)
        for c in self.children:
            bar = "█"*int(c.success_rate()/10) + \
                  "░"*(10-int(c.success_rate()/10))
            print(f"👦 {c.name:6} ({c.severity:8}) "
                  f"[{bar}] {c.success_rate()}% "
                  f"Score:{c.score}")
        print("\n😊 Emotions:")
        for em,cnt in sorted(
                self.detector.emotion_counts.items(),
                key=lambda x:-x[1]):
            print(f"   {em:12}: {cnt}")
        print("="*55)
        return data

    def run(self):
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                if cmd == "report":
                    self.generate_report()
                elif cmd == "skip":
                    self.kid_idx += 1
                    print("⏭️  Skipping to next child...")
                elif cmd in ["exit","quit"]:
                    self.generate_report()
                    self.detector.stop()
                    break
            except KeyboardInterrupt:
                self.generate_report()
                self.detector.stop()
                break

# ===== RUN =====
if __name__ == "__main__":
    sim = FullTherapySim()
    sim.run()
