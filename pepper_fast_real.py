import time
import pybullet as p
import pybullet_data
import threading
import random
import os
from qibullet import SimulationManager
import pyttsx3

class PepperFastReal:
    def __init__(self):
        print("🚀 تشغيل Pepper السريع مع صور افتراضية...")
        
        self.init_voice()
        
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        p.resetDebugVisualizerCamera(4.0, 50, -30, [0, 0, 1])
        
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[-2, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        self.setup_scientists()
        self.running = True
        self.current_target = 0
        
        print(f"✅ تم تجهيز {len(self.scientists)} عالم")
        self.speak("I am ready!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('volume', 1.0)

    def speak(self, text):
        def t():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=t, daemon=True).start()

    def setup_scientists(self):
        self.scientists = [
            {'name': 'Albert Einstein', 'pos': [2, -1.5, 0.5], 'color': [0.9, 0.8, 0.7],
             'facts': ['developed relativity', 'won Nobel Prize', 'said: imagination is important']},
            {'name': 'Marie Curie', 'pos': [2, 0, 0.5], 'color': [0.8, 0.7, 0.9],
             'facts': ['discovered radium', 'two Nobel Prizes', 'died from radiation']},
            {'name': 'Isaac Newton', 'pos': [2, 1.5, 0.5], 'color': [0.7, 0.9, 0.8],
             'facts': ['laws of motion', 'gravity', 'invented calculus']},
            {'name': 'Nikola Tesla', 'pos': [2, 3, 0.5], 'color': [0.9, 0.9, 0.6],
             'facts': ['alternating current', 'Tesla coil', 'wireless energy']},
            {'name': 'Stephen Hawking', 'pos': [2, -3, 0.5], 'color': [0.7, 0.7, 0.9],
             'facts': ['black holes', 'A Brief History of Time', 'ALS']}
        ]
        
        for s in self.scientists:
            # إنشاء قاعدة ملونة لكل عالم
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.5, 0.1, 0.7])
            vis_id = p.createVisualShape(
                p.GEOM_BOX,
                halfExtents=[0.5, 0.1, 0.7],
                rgbaColor=[*s['color'], 1.0]
            )
            p.createMultiBody(0, col_id, vis_id, s['pos'])
            
            # إطار أبيض
            pos = s['pos']
            corners = [
                [pos[0]-0.5, pos[1], pos[2]-0.7],
                [pos[0]+0.5, pos[1], pos[2]-0.7],
                [pos[0]+0.5, pos[1], pos[2]+0.7],
                [pos[0]-0.5, pos[1], pos[2]+0.7]
            ]
            for i in range(4):
                p.addUserDebugLine(corners[i], corners[(i+1)%4], [1,1,1], 2, 0)
            
            # اسم العالم
            p.addUserDebugText(s['name'], [pos[0], pos[1], pos[2]+0.9], [1,1,1], 1.2, 0)

    def move_to_target(self, target_pos):
        current = self.pepper.getPosition()
        dx = target_pos[0] - current[0]
        dy = target_pos[1] - current[1]
        if abs(dx) > 0.3 or abs(dy) > 0.3:
            self.pepper.move(0.3 * dx, 0, 0.15 * dy)
            return False
        return True

    def wave(self):
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.2)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.2)

    def draw_green_box_and_talk(self, scientist):
        pos = scientist['pos']
        corners = [
            [pos[0]-0.5, pos[1], pos[2]-0.7],
            [pos[0]+0.5, pos[1], pos[2]-0.7],
            [pos[0]+0.5, pos[1], pos[2]+0.7],
            [pos[0]-0.5, pos[1], pos[2]+0.7]
        ]
        for i in range(4):
            p.addUserDebugLine(corners[i], corners[(i+1)%4], [0,1,0], 4, 3)
        p.addUserDebugText(scientist['name'], [pos[0], pos[1], pos[2]+0.9], [0,1,0], 1.5, 3)
        
        fact = random.choice(scientist['facts'])
        text = f"I see {scientist['name']}! He {fact}"
        print(f"🤖 Pepper: {text}")
        self.speak(text)
        self.wave()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يتحرك ويتكلم!")
        print("="*60 + "\n")
        
        recognized = [False] * len(self.scientists)
        while self.running:
            if self.current_target < len(self.scientists):
                target = self.scientists[self.current_target]
                if self.move_to_target(target['pos']):
                    if not recognized[self.current_target]:
                        self.draw_green_box_and_talk(target)
                        recognized[self.current_target] = True
                        time.sleep(2)
                    self.current_target += 1
            else:
                self.current_target = 0
                recognized = [False] * len(self.scientists)
                self.speak("One more time!")
            
            time.sleep(0.3)

    def __del__(self):
        self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperFastReal()
    app.run()
