"""
Autism Child Simulation for PyBullet
Simulates children with ASD at 3 severity levels: Mild, Moderate, Severe
Random behaviors based on severity level
"""

import pybullet as p
import numpy as np
import random
import time
import math

# ========== ASD Severity Levels ==========
SEVERITY = {
    "mild": {
        "attention_span": 15,        # seconds
        "meltdown_chance": 0.05,
        "response_chance": 0.75,
        "eye_contact_chance": 0.6,
        "repetitive_chance": 0.2,
        "joint_attention_chance": 0.65,
        "emotion_recognition": 0.6,
        "color": [0.2, 0.8, 0.2, 1]  # green
    },
    "moderate": {
        "attention_span": 8,
        "meltdown_chance": 0.15,
        "response_chance": 0.45,
        "eye_contact_chance": 0.3,
        "repetitive_chance": 0.45,
        "joint_attention_chance": 0.35,
        "emotion_recognition": 0.35,
        "color": [1.0, 0.6, 0.0, 1]  # orange
    },
    "severe": {
        "attention_span": 3,
        "meltdown_chance": 0.35,
        "response_chance": 0.15,
        "eye_contact_chance": 0.05,
        "repetitive_chance": 0.75,
        "joint_attention_chance": 0.1,
        "emotion_recognition": 0.1,
        "color": [0.9, 0.1, 0.1, 1]  # red
    }
}

# ========== Behaviors ==========
BEHAVIORS = {
    "repetitive": [
        "rocking", "hand_flapping", "spinning", "lining_objects"
    ],
    "meltdown": [
        "crying", "covering_ears", "running_away", "floor_sitting"
    ],
    "positive": [
        "clapping", "smiling", "pointing", "making_eye_contact"
    ],
    "neutral": [
        "wandering", "ignoring", "self_stimming", "fixating"
    ]
}

class AutismChild:
    def __init__(self, physics_client, position, severity_level="moderate", name="Child"):
        self.client = physics_client
        self.position = list(position)
        self.severity = severity_level
        self.params = SEVERITY[severity_level]
        self.name = name

        # State tracking
        self.current_behavior = "neutral"
        self.behavior_detail = "wandering"
        self.attention_timer = 0
        self.last_behavior_change = time.time()
        self.is_melting_down = False
        self.meltdown_timer = 0
        self.session_score = 0
        self.total_interactions = 0
        self.successful_responses = 0
        self.joint_attention_active = False
        self.emotion_shown = None

        # Movement
        self.target_position = list(position)
        self.move_speed = 0.01 if severity_level != "severe" else 0.005
        self.wander_timer = 0

        # Emotion state
        self.emotions = ["happy", "sad", "anxious", "calm", "overwhelmed"]
        self.current_emotion = "calm"

        # Build child in PyBullet
        self._create_child_body()
        print(f"[CHILD] {self.name} created | Severity: {severity_level.upper()} | Position: {position}")

    def _create_child_body(self):
        """Create a simple humanoid child representation in PyBullet"""
        col = self.params["color"]

        # Body (torso)
        torso_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.15, 0.1, 0.2])
        torso_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.15, 0.1, 0.2],
                                        rgbaColor=col)
        self.torso = p.createMultiBody(
            baseMass=1,
            baseCollisionShapeIndex=torso_col,
            baseVisualShapeIndex=torso_vis,
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.6]
        )

        # Head
        head_col = p.createCollisionShape(p.GEOM_SPHERE, radius=0.12)
        head_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.12,
                                       rgbaColor=[1.0, 0.85, 0.7, 1.0])
        self.head = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=head_col,
            baseVisualShapeIndex=head_vis,
            basePosition=[self.position[0], self.position[1], self.position[2] + 0.95]
        )

        # Indicator sphere above head (shows severity)
        indicator_vis = p.createVisualShape(p.GEOM_SPHERE, radius=0.06,
                                            rgbaColor=col)
        indicator_col = p.createCollisionShape(p.GEOM_SPHERE, radius=0.06)
        self.indicator = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=indicator_col,
            baseVisualShapeIndex=indicator_vis,
            basePosition=[self.position[0], self.position[1], self.position[2] + 1.2]
        )

        print(f"[CHILD] {self.name} body created in PyBullet")

    def update_position(self):
        """Move child body parts together"""
        x, y, z = self.position
        p.resetBasePositionAndOrientation(
            self.torso, [x, y, z + 0.6], [0, 0, 0, 1])
        p.resetBasePositionAndOrientation(
            self.head, [x, y, z + 0.95], [0, 0, 0, 1])
        p.resetBasePositionAndOrientation(
            self.indicator, [x, y, z + 1.2], [0, 0, 0, 1])

    def _random_wander(self, bounds=3.0):
        """Generate random target position for wandering"""
        self.target_position = [
            random.uniform(-bounds, bounds),
            random.uniform(-bounds, bounds),
            0
        ]

    def _move_toward_target(self):
        """Move child toward target position"""
        dx = self.target_position[0] - self.position[0]
        dy = self.target_position[1] - self.position[1]
        dist = math.sqrt(dx**2 + dy**2)

        if dist > 0.1:
            self.position[0] += (dx / dist) * self.move_speed
            self.position[1] += (dy / dist) * self.move_speed
            self.update_position()
        else:
            self._random_wander()

    def decide_behavior(self):
        """Randomly decide behavior based on severity"""
        now = time.time()
        elapsed = now - self.last_behavior_change

        # Check attention span
        if elapsed > self.params["attention_span"]:
            self.last_behavior_change = now

            # Meltdown check
            if random.random() < self.params["meltdown_chance"] and not self.is_melting_down:
                self._start_meltdown()
                return

            # Recovery from meltdown
            if self.is_melting_down:
                self.meltdown_timer += elapsed
                if self.meltdown_timer > 10:
                    self._end_meltdown()
                return

            # Normal behavior selection
            roll = random.random()
            if roll < self.params["repetitive_chance"]:
                self.current_behavior = "repetitive"
                self.behavior_detail = random.choice(BEHAVIORS["repetitive"])
            elif roll < self.params["repetitive_chance"] + 0.2:
                self.current_behavior = "positive"
                self.behavior_detail = random.choice(BEHAVIORS["positive"])
            else:
                self.current_behavior = "neutral"
                self.behavior_detail = random.choice(BEHAVIORS["neutral"])

            # Random emotion
            self.current_emotion = random.choice(self.emotions)
            print(f"[{self.name}] Behavior: {self.behavior_detail} | Emotion: {self.current_emotion}")

    def _start_meltdown(self):
        self.is_melting_down = True
        self.meltdown_timer = 0
        self.current_behavior = "meltdown"
        self.behavior_detail = random.choice(BEHAVIORS["meltdown"])
        self.current_emotion = "overwhelmed"
        print(f"[{self.name}] ⚠️  MELTDOWN: {self.behavior_detail}")

    def _end_meltdown(self):
        self.is_melting_down = False
        self.meltdown_timer = 0
        self.current_behavior = "neutral"
        self.current_emotion = "calm"
        print(f"[{self.name}] ✅ Meltdown ended - calming down")

    def respond_to_robot(self, robot_action):
        """Child responds to Pepper's therapeutic actions"""
        self.total_interactions += 1
        responded = random.random() < self.params["response_chance"]

        if responded:
            self.successful_responses += 1
            self.session_score += 10
            if self.is_melting_down:
                self._end_meltdown()
            response = random.choice(BEHAVIORS["positive"])
            print(f"[{self.name}] ✅ Responded to {robot_action}: {response}")
            return True, response
        else:
            print(f"[{self.name}] ❌ No response to {robot_action}")
            return False, "ignoring"

    def check_joint_attention(self, robot_pointing_at):
        """Check if child follows joint attention cue"""
        if random.random() < self.params["joint_attention_chance"]:
            self.joint_attention_active = True
            self.session_score += 15
            print(f"[{self.name}] 👀 Joint attention: looking at {robot_pointing_at}")
            return True
        self.joint_attention_active = False
        return False

    def recognize_emotion(self, shown_emotion):
        """Child tries to recognize a shown emotion"""
        self.emotion_shown = shown_emotion
        if random.random() < self.params["emotion_recognition"]:
            self.session_score += 20
            print(f"[{self.name}] 😊 Recognized emotion: {shown_emotion}")
            return True
        print(f"[{self.name}] 😕 Failed to recognize: {shown_emotion}")
        return False

    def step(self):
        """Main update loop - call every simulation step"""
        self.decide_behavior()
        if not self.is_melting_down:
            self._move_toward_target()
        self.wander_timer += 1

    def get_state(self):
        """Return current child state for therapy engine"""
        return {
            "name": self.name,
            "severity": self.severity,
            "behavior": self.current_behavior,
            "behavior_detail": self.behavior_detail,
            "emotion": self.current_emotion,
            "is_melting_down": self.is_melting_down,
            "joint_attention": self.joint_attention_active,
            "session_score": self.session_score,
            "success_rate": (self.successful_responses / max(1, self.total_interactions)) * 100,
            "position": self.position
        }

    def get_report(self):
        """Generate session report"""
        return {
            "child_name": self.name,
            "severity": self.severity,
            "total_interactions": self.total_interactions,
            "successful_responses": self.successful_responses,
            "success_rate": round((self.successful_responses / max(1, self.total_interactions)) * 100, 1),
            "session_score": self.session_score,
            "final_emotion": self.current_emotion
        }

