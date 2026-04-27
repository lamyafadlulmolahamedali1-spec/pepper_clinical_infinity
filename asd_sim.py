#!/usr/bin/env python3
"""
ASD Therapy Simulation
- Moving autism children with random behaviors
- Pepper speaks with real voice
- Pepper walks to each child and does therapy
- Computer vision: Pepper camera sees children
"""

import sys, time, math, random, threading
import pybullet as p
import pyttsx3
sys.path.insert(0, '/home/lamya/pepper_duo/src')
from qibullet import SimulationManager
import pybullet_data

# ========== VOICE ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 145)
            self.engine.setProperty('volume', 1.0)
            # اختيار صوت أنثى
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel','susan']):
                    self.engine.setProperty('voice', v.id)
                    break
            self.ok = True
            print("✅ Voice ready!")
        except Exception as e:
            print(f"⚠️  Voice error: {e}")
            self.ok = False

    def say(self, text):
        print(f"🔊 Pepper: {text}")
        if not self.ok:
            return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass

# ========== AUTISM CHILD ==========
class ASDChild:
    SEVERITY = {
        "mild":     {"response": 0.75, "attention": 12, "meltdown": 0.05, "repetitive": 0.20},
        "moderate": {"response": 0.45, "attention": 7,  "meltdown": 0.15, "repetitive": 0.45},
        "severe":   {"response": 0.15, "attention": 3,  "meltdown": 0.35, "repetitive": 0.75},
    }
    BEHAVIORS = {
        "mild":     ["wandering","smiling","brief_eye_contact","pointing"],
        "moderate": ["hand_flapping","rocking","ignoring","fixating"],
        "severe":   ["spinning","covering_ears","running_away","self_stimming"],
    }
    COLORS = {
        "mild":     [0.2, 0.85, 0.2, 1],
        "moderate": [1.0, 0.6,  0.0, 1],
        "severe":   [0.9, 0.15, 0.15, 1],
    }

    def __init__(self, name, base_pos, severity):
        self.name     = name
        self.base_pos = list(base_pos)
        self.pos      = list(base_pos)
        self.severity = severity
        self.params   = self.SEVERITY[severity]

        # سلوك
        self.behavior      = "wandering"
        self.emotion       = "calm"
        self.is_meltdown   = False
        self.meltdown_time = 0
        self.last_change   = time.time()
        self.wander_offset = [0.0, 0.0]
        self.wander_vel    = [random.uniform(-0.01,0.01), random.uniform(-0.01,0.01)]

        # نتائج
        self.interactions = 0
        self.successes    = 0
        self.score        = 0

        # PyBullet bodies
        self.torso_id = None
        self.head_id  = None
        self._create_body()

    def _create_body(self):
        col  = self.COLORS[self.severity]
        skin = [1.0, 0.82, 0.65, 1.0]

        # جسم
        vs = p.createVisualShape(p.GEOM_BOX,
             halfExtents=[0.14, 0.09, 0.22], rgbaColor=col)
        cs = p.createCollisionShape(p.GEOM_BOX,
             halfExtents=[0.14, 0.09, 0.22])
        self.torso_id = p.createMultiBody(0, cs, vs,
             [self.pos[0], self.pos[1], 0.42])

        # رأس
        vs2 = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=skin)
        cs2 = p.createCollisionShape(p.GEOM_SPHERE, radius=0.12)
        self.head_id = p.createMultiBody(0, cs2, vs2,
             [self.pos[0], self.pos[1], 0.76])

        # اسم + severity فوق الرأس
        severity_emoji = {"mild":"🟢","moderate":"🟠","severe":"🔴"}
        label = f"{self.name} {severity_emoji[self.severity]}"
        p.addUserDebugText(label,
            [self.pos[0], self.pos[1], 1.0],
            [0,0,0], textSize=0.9, lifeTime=0)

        print(f"[CHILD] {self.name} ({self.severity}) created at {self.pos[:2]}")

    def update(self):
        """تحديث السلوك والحركة - يُستدعى كل frame"""
        now = time.time()

        # --- تغيير السلوك ---
        if now - self.last_change > self.params["attention"]:
            self.last_change = now

            # meltdown؟
            if not self.is_meltdown and random.random() < self.params["meltdown"]:
                self.is_meltdown   = True
                self.meltdown_time = now
                self.emotion       = "overwhelmed"
                self.behavior      = random.choice(self.BEHAVIORS[self.severity])
                print(f"[{self.name}] ⚠️  MELTDOWN: {self.behavior}")
            elif self.is_meltdown and now - self.meltdown_time > 10:
                self.is_meltdown = False
                self.emotion     = "calm"
                self.behavior    = "wandering"
                print(f"[{self.name}] ✅ Calmed down")
            else:
                # سلوك عادي
                if random.random() < self.params["repetitive"]:
                    self.behavior = random.choice(self.BEHAVIORS[self.severity])
                else:
                    self.behavior = "wandering"
                emotions = ["calm","happy","anxious","sad","excited"]
                self.emotion = random.choice(emotions)

        # --- حركة عشوائية ---
        # تغيير الاتجاه بشكل ناعم
        self.wander_vel[0] += random.uniform(-0.002, 0.002)
        self.wander_vel[1] += random.uniform(-0.002, 0.002)
        # تحديد السرعة القصوى
        speed = 0.003 if not self.is_meltdown else 0.006
        self.wander_vel[0] = max(-speed, min(speed, self.wander_vel[0]))
        self.wander_vel[1] = max(-speed, min(speed, self.wander_vel[1]))

        # تحديث الموقع
        self.wander_offset[0] += self.wander_vel[0]
        self.wander_offset[1] += self.wander_vel[1]

        # حدود الحركة حول الموقع الأصلي (±0.4م)
        limit = 0.4
        if abs(self.wander_offset[0]) > limit:
            self.wander_vel[0] *= -1
        if abs(self.wander_offset[1]) > limit:
            self.wander_vel[1] *= -1

        self.pos[0] = self.base_pos[0] + self.wander_offset[0]
        self.pos[1] = self.base_pos[1] + self.wander_offset[1]

        # تحريك الجسم في PyBullet
        try:
            p.resetBasePositionAndOrientation(
                self.torso_id,
                [self.pos[0], self.pos[1], 0.42],
                [0,0,0,1])
            p.resetBasePositionAndOrientation(
                self.head_id,
                [self.pos[0], self.pos[1], 0.76],
                [0,0,0,1])
        except:
            pass

    def respond(self, action):
        self.interactions += 1
        if self.is_meltdown:
            return False
        ok = random.random() < self.params["response"]
        if ok:
            self.successes += 1
            self.score += 10
        return ok

    def success_rate(self):
        if self.interactions == 0: return 0
        return round(self.successes / self.interactions * 100, 1)


# ========== COMPUTER VISION ==========
class PepperCamera:
    """كاميرا Pepper ترى الأطفال في PyBullet"""
    def __init__(self, pepper_obj):
        self.pepper = pepper_obj
        self.width  = 320
        self.height = 240
        self.fov    = 60

    def get_frame(self, robot_x, robot_y, head_yaw=0):
        """التقاط صورة من منظور Pepper"""
        cam_pos  = [robot_x, robot_y, 1.3]  # عين Pepper
        # اتجاه الكاميرا
        look_x = cam_pos[0] + math.cos(head_yaw) * 3
        look_y = cam_pos[1] + math.sin(head_yaw) * 3
        look_z = 0.7

        view = p.computeViewMatrix(
            cameraEyePosition=cam_pos,
            cameraTargetPosition=[look_x, look_y, look_z],
            cameraUpVector=[0, 0, 1])

        proj = p.computeProjectionMatrixFOV(
            fov=self.fov, aspect=self.width/self.height,
            nearVal=0.1, farVal=10.0)

        _, _, rgb, _, _ = p.getCameraImage(
            self.width, self.height, view, proj,
            renderer=p.ER_TINY_RENDERER)

        return rgb

    def detect_children(self, children, robot_x, robot_y, head_yaw=0):
        """Pepper تحدد أي الأطفال في مجال رؤيتها"""
        visible = []
        for child in children:
            dx = child.pos[0] - robot_x
            dy = child.pos[1] - robot_y
            dist = math.sqrt(dx**2 + dy**2)

            if dist > 4.0:
                continue

            # زاوية الطفل نسبة للرأس
            angle_to_child = math.atan2(dy, dx)
            angle_diff = angle_to_child - head_yaw
            while angle_diff >  math.pi: angle_diff -= 2*math.pi
            while angle_diff < -math.pi: angle_diff += 2*math.pi

            # مجال الرؤية ±30 درجة
            if abs(angle_diff) < math.radians(30):
                visible.append({
                    "name":     child.name,
                    "distance": round(dist, 2),
                    "angle":    round(math.degrees(angle_diff), 1),
                    "emotion":  child.emotion,
                    "behavior": child.behavior,
                    "severity": child.severity
                })

        return visible


# ========== MAIN SIMULATION ==========
class ASDTherapySimulation:
    def __init__(self):
        self.voice = Voice()

        # تشغيل PyBullet
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")

        self._build_room()

        # Pepper
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.head_yaw = 0.0
        self.auto_walk = True

        # كاميرا
        self.camera = PepperCamera(self.pepper)

        # إنشاء الأطفال
        self.children = [
            ASDChild("Ahmed",  [ 1.5, -1.2, 0], "mild"),
            ASDChild("Sara",   [-1.2,  1.3, 0], "moderate"),
            ASDChild("Yusuf",  [ 0.5, -2.0, 0], "severe"),
            ASDChild("Layla",  [ 2.8, -0.2, 0], "moderate"),
            ASDChild("Omar",   [-2.2, -1.0, 0], "mild"),
        ]

        self.therapy_running = False
        self.current_kid_idx = 0

        # Threads
        threading.Thread(target=self._sim_loop,      daemon=True).start()
        threading.Thread(target=self._children_loop, daemon=True).start()
        threading.Thread(target=self._walk_loop,     daemon=True).start()
        threading.Thread(target=self._vision_loop,   daemon=True).start()

        p.resetDebugVisualizerCamera(
            cameraDistance=7, cameraYaw=45,
            cameraPitch=-35, cameraTargetPosition=[0,0,0.5])

        time.sleep(2)
        self.voice.say("Hello! I am Pepper. Starting autism therapy session!")
        threading.Thread(target=self._therapy_loop, daemon=True).start()

        print("\n" + "="*55)
        print("✅ ASD THERAPY SIMULATION RUNNING")
        print("="*55)
        print("Commands: 'report', 'vision', 'stop', 'exit'")
        print("="*55 + "\n")

    def _build_room(self):
        print("🏠 Building therapy room...")
        wc = [0.85, 0.85, 0.9, 1]
        # جدران
        for pos, ext in [
            ([0,-4,1.1],[5,0.1,1.1]),  ([0,4,1.1],[5,0.1,1.1]),
            ([5,0,1.1],[0.1,4,1.1]),   ([-5,0,1.1],[0.1,4,1.1])]:
            vs = p.createVisualShape(p.GEOM_BOX, halfExtents=ext, rgbaColor=wc)
            p.createMultiBody(0, -1, vs, pos)
        # أرضية ملونة
        floor = p.createVisualShape(p.GEOM_BOX,
            halfExtents=[4.5,3.5,0.02], rgbaColor=[0.6,0.5,0.4,1])
        p.createMultiBody(0, -1, floor, [0,0,0.01])
        # طاولة
        tv = p.createVisualShape(p.GEOM_BOX,
            halfExtents=[0.8,0.6,0.35], rgbaColor=[0.55,0.35,0.15,1])
        p.createMultiBody(0, -1, tv, [2,1.5,0.35])
        print("✅ Room ready!")

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            time.sleep(1/240.)

    def _children_loop(self):
        """تحريك الأطفال باستمرار"""
        while True:
            for child in self.children:
                child.update()
            time.sleep(0.05)  # 20 FPS

    def _walk_loop(self):
        """Pepper تتحرك"""
        t = 0
        while True:
            if self.auto_walk:
                t += 0.015
                self.robot_x += 0.02 * math.cos(t * 0.4)
                self.robot_y += 0.02 * math.sin(t * 0.5)
                self.robot_x = max(-3.5, min(3.5, self.robot_x))
                self.robot_y = max(-2.8, min(2.8, self.robot_y))
                try:
                    self.pepper.setPosition([self.robot_x, self.robot_y, 0.8])
                except:
                    pass
            time.sleep(0.06)

    def _vision_loop(self):
        """كاميرا Pepper تفحص الأطفال كل 3 ثواني"""
        while True:
            time.sleep(3)
            visible = self.camera.detect_children(
                self.children, self.robot_x, self.robot_y, self.head_yaw)
            if visible:
                names = [v["name"] for v in visible]
                print(f"[CAMERA] 👁️  Pepper sees: {', '.join(names)}")
                for v in visible:
                    print(f"  → {v['name']} | dist:{v['distance']}m | {v['behavior']} | {v['emotion']}")

    def _move_to_child(self, child):
        """Pepper تتحرك للطفل وتقف أمامه"""
        self.auto_walk = False
        tx, ty = child.pos[0], child.pos[1]

        for _ in range(60):  # 60 خطوة
            dx = tx - self.robot_x
            dy = ty - self.robot_y
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 0.8:
                break
            step = min(0.06, dist - 0.7)
            self.robot_x += (dx/dist) * step
            self.robot_y += (dy/dist) * step
            # الرأس ينظر للطفل
            self.head_yaw = math.atan2(dy, dx)
            try:
                self.pepper.setPosition([self.robot_x, self.robot_y, 0.8])
                self.pepper.setAngles("HeadYaw",   self.head_yaw * 0.5, 0.1)
                self.pepper.setAngles("HeadPitch", -0.1, 0.08)
            except:
                pass
            time.sleep(0.04)

        # اتجه للطفل مباشرة
        dx = tx - self.robot_x
        dy = ty - self.robot_y
        self.head_yaw = math.atan2(dy, dx)
        try:
            self.pepper.setAngles("HeadYaw", self.head_yaw * 0.5, 0.1)
        except:
            pass
        time.sleep(0.4)

    def _therapy_action(self, child):
        """تنفيذ فعل علاجي مع حركة أيدي سلسة"""
        # أيدي تتحرك أثناء الكلام
        def arm_wave():
            for _ in range(3):
                try:
                    self.pepper.setAngles("LShoulderPitch", 0.3, 0.12)
                    self.pepper.setAngles("RShoulderPitch", 0.7, 0.12)
                    time.sleep(0.35)
                    self.pepper.setAngles("LShoulderPitch", 0.7, 0.12)
                    self.pepper.setAngles("RShoulderPitch", 0.3, 0.12)
                    time.sleep(0.35)
                except:
                    pass
            try:
                self.pepper.setAngles("LShoulderPitch", 1.0, 0.1)
                self.pepper.setAngles("RShoulderPitch", 1.0, 0.1)
            except:
                pass

        if child.is_meltdown:
            self.voice.say(f"It is okay {child.name}. Breathe slowly with me.")
            threading.Thread(target=arm_wave, daemon=True).start()
            child.respond("calm_down")
            return

        actions = [
            (f"Hello {child.name}! How are you today?", "greet"),
            (f"{child.name}, can you clap your hands?", "dtt"),
            (f"Look {child.name}! See the red ball!", "joint_attention"),
            (f"{child.name}, show me a happy face!", "emotion"),
            (f"Breathe with me {child.name}. In and out.", "sensory"),
            (f"{child.name}, touch your nose please!", "dtt"),
        ]
        text, atype = random.choice(actions)

        # حركة الأيدي مع الكلام
        threading.Thread(target=arm_wave, daemon=True).start()
        self.voice.say(text)

        # عرض النص في PyBullet
        try:
            pos = p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:50],
                [pos[0], pos[1], pos[2]+1.2],
                [0,0,0], textSize=0.9, lifeTime=4)
        except:
            pass

        time.sleep(0.8)
        responded = child.respond(atype)

        if responded:
            praise = f"Amazing {child.name}! Great job!"
            self.voice.say(praise)
            # احتفال
            try:
                for _ in range(2):
                    self.pepper.setAngles("LShoulderPitch", 0.2, 0.2)
                    self.pepper.setAngles("RShoulderPitch", 0.2, 0.2)
                    time.sleep(0.2)
                    self.pepper.setAngles("LShoulderPitch", 0.9, 0.2)
                    self.pepper.setAngles("RShoulderPitch", 0.9, 0.2)
                    time.sleep(0.2)
            except:
                pass
        else:
            self.voice.say(f"That is okay {child.name}. Let us try again!")

        rate = child.success_rate()
        print(f"[{child.name}] Rate:{rate}% Score:{child.score} Behavior:{child.behavior}")

    def _therapy_loop(self):
        """الثيرابي الرئيسي"""
        self.therapy_running = True
        print("\n🏥 THERAPY SESSION STARTED - Pepper visiting children!\n")

        while self.therapy_running:
            child = self.children[self.current_kid_idx % len(self.children)]
            self.current_kid_idx += 1

            print(f"\n[THERAPY] 🚶 Moving to {child.name} ({child.severity})")
            print(f"[{child.name}] Behavior:{child.behavior} Emotion:{child.emotion}")

            # تحرك للطفل
            self._move_to_child(child)

            # Computer Vision - ماذا ترى Pepper؟
            visible = self.camera.detect_children(
                self.children, self.robot_x, self.robot_y, self.head_yaw)
            if visible:
                print(f"[CAMERA] 👁️  Sees: {[v['name'] for v in visible]}")

            # الفعل العلاجي
            self._therapy_action(child)

            self.auto_walk = True
            time.sleep(8)

    def print_report(self):
        print("\n" + "="*55)
        print("📊 SESSION REPORT")
        print("="*55)
        for c in self.children:
            bar = "█"*int(c.success_rate()/10) + "░"*(10-int(c.success_rate()/10))
            print(f"👦 {c.name:6} ({c.severity:8}) [{bar}] {c.success_rate()}% | Score:{c.score}")
        print("="*55)

    def run(self):
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                if cmd == "report":
                    self.print_report()
                elif cmd == "vision":
                    v = self.camera.detect_children(
                        self.children, self.robot_x, self.robot_y, self.head_yaw)
                    print(f"[CAMERA] Pepper sees {len(v)} children: {[x['name'] for x in v]}")
                elif cmd == "stop":
                    self.therapy_running = False
                    self.voice.say("Stopping therapy session.")
                elif cmd in ["exit","quit"]:
                    self.therapy_running = False
                    self.voice.say("Goodbye!")
                    self.print_report()
                    break
            except KeyboardInterrupt:
                self.therapy_running = False
                self.print_report()
                break

if __name__ == "__main__":
    sim = ASDTherapySimulation()
    sim.run()
