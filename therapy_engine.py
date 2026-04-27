"""
Therapeutic Interaction Engine (TIE)
Implements: ABA + TEACCH + DTT + Joint Attention + Emotion Recognition
"""

import random
import time
import json
from datetime import datetime

# ========== Therapy Protocols ==========

ABA_PROGRAMS = {
    "DTT": {
        "name": "Discrete Trial Training",
        "steps": ["instruction", "prompt", "response", "reinforcement", "inter_trial"],
        "reinforcers": ["Great job!", "Awesome!", "You did it!", "Wonderful!", "Super star!"],
        "prompts": ["verbal", "gestural", "physical", "visual"]
    },
    "NET": {
        "name": "Natural Environment Training",
        "activities": ["play_with_ball", "sort_colors", "stack_blocks", "puzzle"],
    },
    "PRT": {
        "name": "Pivotal Response Training",
        "targets": ["motivation", "self_management", "responsivity", "self_initiation"]
    }
}

TEACCH_SCHEDULES = {
    "morning": [
        {"time": "09:00", "activity": "greeting_circle",    "duration": 5,  "visual": "🌅"},
        {"time": "09:05", "activity": "emotion_check_in",   "duration": 3,  "visual": "😊"},
        {"time": "09:08", "activity": "DTT_session",        "duration": 10, "visual": "📚"},
        {"time": "09:18", "activity": "sensory_break",      "duration": 5,  "visual": "🎯"},
        {"time": "09:23", "activity": "joint_attention",    "duration": 8,  "visual": "👀"},
        {"time": "09:31", "activity": "free_play",          "duration": 5,  "visual": "🎮"},
        {"time": "09:36", "activity": "emotion_recognition","duration": 7,  "visual": "🎭"},
        {"time": "09:43", "activity": "closing_circle",     "duration": 5,  "visual": "⭐"},
    ]
}

EMOTIONS_CARDS = ["happy", "sad", "angry", "surprised", "scared", "calm", "excited", "tired"]

JOINT_ATTENTION_OBJECTS = ["red_ball", "yellow_block", "blue_puzzle", "green_toy", "picture_book"]

class TherapyEngine:
    def __init__(self, session_config=None):
        self.config = session_config or self._default_config()
        self.current_protocol = "ABA_DTT"
        self.current_activity = None
        self.activity_index = 0
        self.schedule = TEACCH_SCHEDULES["morning"]
        self.session_log = []
        self.session_start = datetime.now()
        self.dtt_trial_count = 0
        self.dtt_success_count = 0
        self.reinforcement_given = 0
        self.emotion_trials = []
        self.joint_attention_trials = []

        print(f"[THERAPY ENGINE] Initialized | Protocol: {self.current_protocol}")
        print(f"[THERAPY ENGINE] Child: {self.config['child_name']} | Goal: {self.config['primary_goal']}")

    def _default_config(self):
        return {
            "child_name": "Child",
            "severity": "moderate",
            "primary_goal": "joint_attention",
            "reinforcer_type": "verbal_praise",
            "session_duration": 30,
            "prompt_level": "gestural",
            "schedule_type": "morning"
        }

    def get_next_activity(self):
        """TEACCH: Get next scheduled activity"""
        if self.activity_index >= len(self.schedule):
            self.activity_index = 0
        activity = self.schedule[self.activity_index]
        self.activity_index += 1
        self.current_activity = activity["activity"]
        print(f"[TEACCH] {activity['visual']} Next: {activity['activity']} ({activity['duration']} min)")
        return activity

    def run_dtt_trial(self, child):
        """ABA: Run one Discrete Trial Training trial"""
        self.dtt_trial_count += 1
        program = ABA_PROGRAMS["DTT"]

        # Step 1: Instruction
        instruction = self._get_dtt_instruction()
        print(f"[DTT] Trial #{self.dtt_trial_count} | Instruction: '{instruction}'")

        # Step 2: Prompt if needed
        prompt = self.config.get("prompt_level", "gestural")
        print(f"[DTT] Prompt type: {prompt}")

        # Step 3: Child responds
        responded, response = child.respond_to_robot(f"DTT_{instruction}")

        # Step 4: Reinforcement
        if responded:
            self.dtt_success_count += 1
            reinforcer = random.choice(program["reinforcers"])
            self.reinforcement_given += 1
            print(f"[DTT] ✅ SUCCESS | Reinforcer: '{reinforcer}'")
            result = "success"
        else:
            print(f"[DTT] ❌ No response | Error correction applied")
            result = "fail"

        # Step 5: Inter-trial interval
        inter_trial = random.uniform(2, 4)
        print(f"[DTT] Inter-trial interval: {inter_trial:.1f}s")

        # Log
        trial_log = {
            "trial": self.dtt_trial_count,
            "instruction": instruction,
            "prompt": prompt,
            "result": result,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self.session_log.append({"type": "DTT", "data": trial_log})
        return result

    def _get_dtt_instruction(self):
        instructions = [
            "Touch your nose",
            "Clap your hands",
            "Stand up",
            "Point to the ball",
            "Say hello",
            "Show me happy face",
            "Pick up the block",
            "Look at me"
        ]
        return random.choice(instructions)

    def run_joint_attention(self, child):
        """Joint Attention Training"""
        target_object = random.choice(JOINT_ATTENTION_OBJECTS)
        print(f"[JOINT ATTENTION] 👀 Pointing to: {target_object}")
        print(f"[JOINT ATTENTION] Robot says: 'Look! Look at the {target_object}!'")

        success = child.check_joint_attention(target_object)

        result = {
            "object": target_object,
            "success": success,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self.joint_attention_trials.append(result)
        self.session_log.append({"type": "joint_attention", "data": result})

        if success:
            print(f"[JOINT ATTENTION] ✅ Child looked at {target_object}!")
        else:
            print(f"[JOINT ATTENTION] ❌ Child did not follow gaze")

        return success

    def run_emotion_recognition(self, child):
        """Emotion Recognition Training"""
        emotion = random.choice(EMOTIONS_CARDS)
        print(f"[EMOTION] 🎭 Showing emotion card: {emotion}")
        print(f"[EMOTION] Robot says: 'What feeling is this? Is this {emotion}?'")

        success = child.recognize_emotion(emotion)

        result = {
            "emotion": emotion,
            "success": success,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self.emotion_trials.append(result)
        self.session_log.append({"type": "emotion_recognition", "data": result})

        if success:
            print(f"[EMOTION] ✅ Correct! Child recognized {emotion}")
            print(f"[EMOTION] Robot: 'Excellent! That IS {emotion}! Great job!'")
        else:
            print(f"[EMOTION] ❌ Incorrect | Robot models emotion again")
            print(f"[EMOTION] Robot: 'This is {emotion}. Can you show me {emotion}?'")

        return success

    def handle_meltdown(self, child):
        """ABA: Meltdown intervention protocol"""
        print(f"[MELTDOWN] ⚠️  Meltdown detected for {child.name}")
        print(f"[MELTDOWN] Protocol: Reduce stimulation, calm voice, sensory support")

        strategies = [
            "Speaking softly and calmly",
            "Giving personal space",
            "Offering sensory toy",
            "Using visual calm-down card",
            "Counting down timer"
        ]
        strategy = random.choice(strategies)
        print(f"[MELTDOWN] Strategy: {strategy}")

        child.respond_to_robot("calm_down_protocol")
        self.session_log.append({
            "type": "meltdown_intervention",
            "data": {"strategy": strategy, "timestamp": datetime.now().strftime("%H:%M:%S")}
        })

    def run_sensory_break(self):
        """TEACCH: Structured sensory break"""
        activities = ["deep_breathing", "stretching", "quiet_corner", "fidget_toy", "music_listening"]
        activity = random.choice(activities)
        print(f"[SENSORY BREAK] 🎯 Activity: {activity}")
        print(f"[SENSORY BREAK] Duration: 5 minutes")
        self.session_log.append({
            "type": "sensory_break",
            "data": {"activity": activity}
        })
        return activity

    def decide_action(self, child_state):
        """Main decision engine: choose therapy action based on child state"""

        # Priority 1: Meltdown
        if child_state["is_melting_down"]:
            return "meltdown_intervention"

        # Priority 2: Follow TEACCH schedule
        activity = self.current_activity or self.get_next_activity()["activity"]

        action_map = {
            "greeting_circle":     "greet",
            "emotion_check_in":    "emotion_check",
            "DTT_session":         "run_dtt",
            "sensory_break":       "sensory_break",
            "joint_attention":     "joint_attention",
            "free_play":           "free_play",
            "emotion_recognition": "emotion_recognition",
            "closing_circle":      "closing"
        }

        return action_map.get(activity, "run_dtt")

    def execute_action(self, action, child):
        """Execute the decided therapy action"""
        print(f"\n[THERAPY] ▶ Executing: {action}")

        if action == "run_dtt":
            return self.run_dtt_trial(child)
        elif action == "joint_attention":
            return self.run_joint_attention(child)
        elif action == "emotion_recognition":
            return self.run_emotion_recognition(child)
        elif action == "meltdown_intervention":
            return self.handle_meltdown(child)
        elif action == "sensory_break":
            return self.run_sensory_break()
        elif action == "greet":
            print(f"[GREET] 🌅 Robot: 'Good morning {child.name}! Ready to learn today?'")
            return child.respond_to_robot("greeting")
        elif action == "free_play":
            print(f"[FREE PLAY] 🎮 Unstructured play time")
            return "free_play"
        elif action == "closing":
            print(f"[CLOSING] ⭐ Robot: 'Great session today {child.name}! You did amazing!'")
            return child.respond_to_robot("closing")
        else:
            return self.run_dtt_trial(child)

    def get_session_summary(self, child):
        """Generate full session report"""
        duration = (datetime.now() - self.session_start).seconds // 60
        dtt_rate = round((self.dtt_success_count / max(1, self.dtt_trial_count)) * 100, 1)
        ja_rate = round(sum(1 for t in self.joint_attention_trials if t["success"]) /
                        max(1, len(self.joint_attention_trials)) * 100, 1)
        er_rate = round(sum(1 for t in self.emotion_trials if t["success"]) /
                        max(1, len(self.emotion_trials)) * 100, 1)

        summary = {
            "session_date": self.session_start.strftime("%Y-%m-%d"),
            "session_time": self.session_start.strftime("%H:%M"),
            "duration_minutes": duration,
            "child_report": child.get_report(),
            "therapy_results": {
                "DTT": {
                    "trials": self.dtt_trial_count,
                    "successes": self.dtt_success_count,
                    "success_rate": dtt_rate
                },
                "joint_attention": {
                    "trials": len(self.joint_attention_trials),
                    "success_rate": ja_rate
                },
                "emotion_recognition": {
                    "trials": len(self.emotion_trials),
                    "success_rate": er_rate
                }
            },
            "reinforcements_given": self.reinforcement_given,
            "session_log": self.session_log
        }

        # Save to file
        filename = f"session_{self.session_start.strftime('%Y%m%d_%H%M')}.json"
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n[REPORT] 📊 Session saved to {filename}")
        return summary

