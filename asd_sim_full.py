#!/usr/bin/env python3
"""
ASD Therapy Simulation - FULL VERSION
يدمج:
- asd_sim.py          (أطفال يتحركون + Pepper تتحرك + camera)
- ai_chat_module.py   (AI chat متطور)
- motion_words_module.py (حركة حسب الكلمة)
"""

import sys, time, math, random, threading
import pybullet as p
import pyttsx3
sys.path.insert(0, '/home/lamya/pepper_duo/src')
from qibullet import SimulationManager
import pybullet_data

from ai_chat_module      import AIChatModule
from motion_words_module import MotionWordsModule

# ========== VOICE ==========
class Voice:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 145)
            self.engine.setProperty('volume', 1.0)
            for v in self.engine.getProperty('voices'):
                if any(x in v.name.lower() for x in ['female','zira','hazel','susan']):
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

# ========== ASD CHILD ==========
class ASDChild:
    SEVERITY = {
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
        "moderate": [1.0,0.6, 0.0,1],
        "severe":   [0.9,0.15,0.15,1],
    }

    def __init__(self, name, base_pos, severity):
        self.name=name; self.base_pos=list(base_pos)
        self.pos=list(base_pos); self.severity=severity
        self.params=self.SEVERITY[severity]
        self.behavior="wandering"; self.emotion="calm"
        self.is_meltdown=False; self.meltdown_time=0
        self.last_change=time.time()
        self.wander_vel=[random.uniform(-0.008,0.008),random.uniform(-0.008,0.008)]
        self.wander_offset=[0.0,0.0]
        self.interactions=0; self.successes=0; self.score=0
        self.torso_id=None; self.head_id=None
        self._create_body()

    def _create_body(self):
        col=self.COLORS[self.severity]; skin=[1.0,0.82,0.65,1.0]
        vs=p.createVisualShape(p.GEOM_BOX,halfExtents=[0.13,0.09,0.21],rgbaColor=col)
        cs=p.createCollisionShape(p.GEOM_BOX,halfExtents=[0.13,0.09,0.21])
        self.torso_id=p.createMultiBody(0,cs,vs,[self.pos[0],self.pos[1],0.41])
        vs2=p.createVisualShape(p.GEOM_SPHERE,radius=0.11,rgbaColor=skin)
        cs2=p.createCollisionShape(p.GEOM_SPHERE,radius=0.11)
        self.head_id=p.createMultiBody(0,cs2,vs2,[self.pos[0],self.pos[1],0.74])
        emoji={"mild":"🟢","moderate":"🟠","severe":"🔴"}
        p.addUserDebugText(f"{self.name} {emoji[self.severity]}",
            [self.pos[0],self.pos[1],1.0],[0,0,0],textSize=0.9,lifeTime=0)

    def update(self):
        now=time.time()
        if now-self.last_change > self.params["attention"]:
            self.last_change=now
            if not self.is_meltdown and random.random()<self.params["meltdown"]:
                self.is_meltdown=True; self.meltdown_time=now
                self.emotion="overwhelmed"
                self.behavior=random.choice(self.BEHAVIORS[self.severity])
                print(f"[{self.name}] ⚠️  MELTDOWN: {self.behavior}")
            elif self.is_meltdown and now-self.meltdown_time>10:
                self.is_meltdown=False; self.emotion="calm"; self.behavior="wandering"
                print(f"[{self.name}] ✅ Calmed down")
            else:
                self.behavior=random.choice(
                    self.BEHAVIORS[self.severity] if random.random()<self.params["repetitive"]
                    else ["wandering","neutral"])
                self.emotion=random.choice(["calm","happy","anxious","sad","excited"])

        spd=0.005 if not self.is_meltdown else 0.009
        self.wander_vel[0]+=random.uniform(-0.001,0.001)
        self.wander_vel[1]+=random.uniform(-0.001,0.001)
        self.wander_vel[0]=max(-spd,min(spd,self.wander_vel[0]))
        self.wander_vel[1]=max(-spd,min(spd,self.wander_vel[1]))
        self.wander_offset[0]+=self.wander_vel[0]
        self.wander_offset[1]+=self.wander_vel[1]
        lim=0.4
        if abs(self.wander_offset[0])>lim: self.wander_vel[0]*=-1
        if abs(self.wander_offset[1])>lim: self.wander_vel[1]*=-1
        self.pos[0]=self.base_pos[0]+self.wander_offset[0]
        self.pos[1]=self.base_pos[1]+self.wander_offset[1]
        try:
            p.resetBasePositionAndOrientation(self.torso_id,[self.pos[0],self.pos[1],0.41],[0,0,0,1])
            p.resetBasePositionAndOrientation(self.head_id, [self.pos[0],self.pos[1],0.74],[0,0,0,1])
        except: pass

    def respond(self,action):
        self.interactions+=1
        if self.is_meltdown: return False
        ok=random.random()<self.params["response"]
        if ok: self.successes+=1; self.score+=10
        return ok

    def success_rate(self):
        return 0 if not self.interactions else round(self.successes/self.interactions*100,1)


# ========== MAIN ==========
class ASDTherapyFull:
    def __init__(self):
        self.voice  = Voice()
        self.ai     = AIChatModule()

        # PyBullet
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0,0,-9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        self._build_room()

        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand",0.5)
        self.rx=0.0; self.ry=0.0; self.head_yaw=0.0
        self.auto_walk=True

        # Motion module - بعد spawn Pepper
        self.motion = MotionWordsModule(self.pepper)

        self.children = [
            ASDChild("Ahmed", [ 1.5,-1.2,0], "mild"),
            ASDChild("Sara",  [-1.2, 1.3,0], "moderate"),
            ASDChild("Yusuf", [ 0.5,-2.0,0], "severe"),
            ASDChild("Layla", [ 2.8,-0.2,0], "moderate"),
            ASDChild("Omar",  [-2.2,-1.0,0], "mild"),
        ]

        self.therapy_running=False
        self.kid_idx=0

        threading.Thread(target=self._sim_loop,      daemon=True).start()
        threading.Thread(target=self._children_loop, daemon=True).start()
        threading.Thread(target=self._walk_loop,     daemon=True).start()

        p.resetDebugVisualizerCamera(7,45,-35,[0,0,0.5])
        time.sleep(2)

        intro = "Hello everyone! I am Pepper. Let us start our therapy session!"
        self.voice.say(intro)
        self.motion.perform(intro)

        threading.Thread(target=self._therapy_loop, daemon=True).start()

        print("\n" + "="*55)
        print("✅ ASD THERAPY FULL SIMULATION RUNNING")
        print("="*55)
        print("Commands:")
        print("  'ask [question]' → AI answers")
        print("  'child [name] [message]' → talk to child")
        print("  'parent [question]' → parent guidance")
        print("  'report' → session report")
        print("  'exit'")
        print("="*55+"\n")

    def _build_room(self):
        print("🏠 Building room...")
        p.loadURDF("plane.urdf") if False else None
        wc=[0.85,0.85,0.9,1]
        for pos,ext in [([0,-4,1.1],[5,0.1,1.1]),([0,4,1.1],[5,0.1,1.1]),
                        ([5,0,1.1],[0.1,4,1.1]),([-5,0,1.1],[0.1,4,1.1])]:
            p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=ext,rgbaColor=wc),pos)
        p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[4.5,3.5,0.02],rgbaColor=[0.6,0.5,0.4,1]),[0,0,0.01])
        p.createMultiBody(0,-1,p.createVisualShape(p.GEOM_BOX,halfExtents=[0.8,0.6,0.35],rgbaColor=[0.55,0.35,0.15,1]),[2,1.5,0.35])
        print("✅ Room ready!")

    def _sim_loop(self):
        while True:
            p.stepSimulation()
            time.sleep(1/240.)

    def _children_loop(self):
        while True:
            for c in self.children: c.update()
            time.sleep(0.05)

    def _walk_loop(self):
        t=0
        while True:
            if self.auto_walk:
                t+=0.015
                self.rx+=0.02*math.cos(t*0.4)
                self.ry+=0.02*math.sin(t*0.5)
                self.rx=max(-3.5,min(3.5,self.rx))
                self.ry=max(-2.8,min(2.8,self.ry))
                try: self.pepper.setPosition([self.rx,self.ry,0.8])
                except: pass
            time.sleep(0.06)

    def _move_to_child(self, child):
        self.auto_walk=False
        tx,ty=child.pos[0],child.pos[1]
        for _ in range(80):
            dx=tx-self.rx; dy=ty-self.ry
            dist=math.sqrt(dx**2+dy**2)
            if dist<0.8: break
            step=min(0.055,dist-0.7)
            self.rx+=dx/dist*step; self.ry+=dy/dist*step
            self.head_yaw=math.atan2(dy,dx)
            try:
                self.pepper.setPosition([self.rx,self.ry,0.8])
                self.pepper.setAngles("HeadYaw",  self.head_yaw*0.5,0.1)
                self.pepper.setAngles("HeadPitch",-0.1,0.08)
            except: pass
            time.sleep(0.04)
        dx=tx-self.rx; dy=ty-self.ry
        self.head_yaw=math.atan2(dy,dx)
        try: self.pepper.setAngles("HeadYaw",self.head_yaw*0.5,0.1)
        except: pass
        time.sleep(0.3)

    def _speak_and_move(self, text):
        """تكلم + حرك في نفس الوقت"""
        threading.Thread(target=self.motion.perform, args=(text,), daemon=True).start()
        self.voice.say(text)
        # عرض النص في PyBullet
        try:
            pos=p.getBasePositionAndOrientation(self.pepper.body)[0]
            p.addUserDebugText(text[:50],[pos[0],pos[1],pos[2]+1.2],[0,0,0],textSize=0.85,lifeTime=4)
        except: pass

    def _therapy_loop(self):
        self.therapy_running=True
        print("\n🏥 THERAPY SESSION STARTED!\n")
        time.sleep(2)

        while self.therapy_running:
            child=self.children[self.kid_idx % len(self.children)]
            self.kid_idx+=1

            print(f"\n[THERAPY] 🚶 → {child.name} ({child.severity})")
            print(f"[{child.name}] {child.behavior} | {child.emotion}")

            self._move_to_child(child)

            # AI يولد جملة علاجية مناسبة
            ai_text = self.ai.generate_therapy_prompt(
                child.name, "DTT_and_joint_attention", child.severity)

            self._speak_and_move(ai_text)
            time.sleep(0.8)

            responded = child.respond("therapy")

            if responded:
                praise = self.ai.chat(
                    f"Give ONE short praise for {child.name} who just succeeded!",
                    {"child": child.name, "severity": child.severity})
                self._speak_and_move(praise)
            else:
                retry = f"That is okay {child.name}! Let us try again!"
                self._speak_and_move(retry)

            print(f"[{child.name}] Rate:{child.success_rate()}% Score:{child.score}")
            self.auto_walk=True
            time.sleep(10)

    def print_report(self):
        print("\n"+"="*55)
        print("📊 FINAL SESSION REPORT")
        print("="*55)
        for c in self.children:
            bar="█"*int(c.success_rate()/10)+"░"*(10-int(c.success_rate()/10))
            print(f"👦 {c.name:6} ({c.severity:8}) [{bar}] {c.success_rate()}% Score:{c.score}")
        summary = self.ai.get_summary()
        print(f"\n🤖 AI Summary: {summary}")
        print("="*55)

    def run(self):
        while True:
            try:
                cmd=input("\n> ").strip()
                if not cmd: continue
                cl=cmd.lower()

                if cl.startswith("ask "):
                    q=cmd[4:]
                    reply=self.ai.chat(q)
                    self._speak_and_move(reply)

                elif cl.startswith("child "):
                    parts=cmd.split(None,2)
                    name=parts[1].title() if len(parts)>1 else "Ahmed"
                    msg =parts[2] if len(parts)>2 else "hello"
                    sev = next((c.severity for c in self.children if c.name==name),"moderate")
                    reply=self.ai.chat_with_child(name,msg,sev)
                    self._speak_and_move(reply)

                elif cl.startswith("parent "):
                    q=cmd[7:]
                    reply=self.ai.chat_with_parent(q)
                    self._speak_and_move(reply)

                elif cl=="report":
                    self.print_report()

                elif cl in ["exit","quit"]:
                    self.therapy_running=False
                    self.voice.say("Goodbye! Great session today!")
                    self.print_report()
                    break

                else:
                    # أي كلام → AI يرد + حركة
                    reply=self.ai.chat(cmd)
                    self._speak_and_move(reply)

            except KeyboardInterrupt:
                self.therapy_running=False
                self.print_report()
                break

if __name__ == "__main__":
    sim = ASDTherapyFull()
    sim.run()
