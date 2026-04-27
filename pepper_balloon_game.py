#!/usr/bin/env python3
"""
Pepper Balloon Game - Pepper moves around trying to catch balloons
"""

import os
import sys
import time
import threading
import random
import math
import requests
import subprocess
from qibullet import SimulationManager
import pybullet as p
import pybullet_data

# ========== Settings ==========
DASHBOARD_URL = "http://localhost:5001"

# ========== Balloon Class ==========
class Balloon:
    def __init__(self, x, y, z, color):
        self.x = x
        self.y = y
        self.z = z
        self.speed_x = random.uniform(-0.03, 0.03)
        self.speed_y = random.uniform(-0.03, 0.03)
        self.speed_z = random.uniform(0.02, 0.05)
        self.color = color
        self.caught = False
        self.body_id = None
        self.create()
    
    def create(self):
        visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.12, rgbaColor=self.color)
        self.body_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=visual,
                                          basePosition=[self.x, self.y, self.z])
        string = p.createVisualShape(p.GEOM_CYLINDER, radius=0.008, length=0.2, rgbaColor=[0.5, 0.5, 0.5, 1])
        p.createMultiBody(baseMass=0, baseVisualShapeIndex=string,
                          basePosition=[self.x, self.y, self.z - 0.13])
    
    def update(self):
        if self.caught:
            return
        self.x += self.speed_x
        self.y += self.speed_y
        self.z += self.speed_z
        if self.z > 2.8:
            self.z = 0.3
            self.x = random.uniform(-3, 3)
            self.y = random.uniform(-2.5, 2.5)
        if abs(self.x) > 4:
            self.speed_x = -self.speed_x
        if abs(self.y) > 3.5:
            self.speed_y = -self.speed_y
        p.resetBasePositionAndOrientation(self.body_id, [self.x, self.y, self.z], [0, 0, 0, 1])
    
    def catch(self):
        self.caught = True
        p.removeBody(self.body_id)

# ========== Build Room ==========
def build_room():
    print("🏠 Building room...")
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf")
    rug = p.createVisualShape(p.GEOM_BOX, halfExtents=[4.5, 3.5, 0.02], rgbaColor=[0.5, 0.3, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=rug, basePosition=[0, 0, 0.01])
    # Walls
    wall_color = [0.85, 0.85, 0.9, 1]
    wall = p.createVisualShape(p.GEOM_BOX, halfExtents=[5, 0.1, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, -4, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall, basePosition=[0, 4, 1.1])
    wall_side = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 4, 2.2], rgbaColor=wall_color)
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[5, 0, 1.1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=wall_side, basePosition=[-5, 0, 1.1])
    # Table
    table = p.createVisualShape(p.GEOM_BOX, halfExtents=[1, 0.8, 0.4], rgbaColor=[0.6, 0.4, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=table, basePosition=[2, 1.5, 0.4])
    print("✅ Room ready!")

# ========== Pepper Balloon Game ==========
class PepperBalloonGame:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setRealTimeSimulation(1)
        p.setGravity(0, 0, -9.81)
        
        build_room()
        
        print("🤖 Spawning Pepper...")
        self.pepper = self.sim_manager.spawnPepper(self.client)
        self.pepper.goToPosture("Stand", 0.5)
        
        self.x, self.y, self.angle = 0, 0, 0
        self.balloons = []
        self.score = 0
        self.create_balloons()
        
        self.running = True
        
        p.resetDebugVisualizerCamera(cameraDistance=7, cameraYaw=45, cameraPitch=-30, cameraTargetPosition=[0, 0, 1])
        
        print("\n" + "="*50)
        print("🎈 PEPPER BALLOON GAME")
        print("="*50)
        print("Pepper will try to catch balloons!")
        print("Type: catch | stop | score | exit")
        print("="*50)
        
        threading.Thread(target=self.move_towards_balloons, daemon=True).start()
        threading.Thread(target=self.run_simulation, daemon=True).start()
    
    def create_balloons(self):
        colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1], 
                  [1, 1, 0.2, 1], [1, 0.5, 0.2, 1], [1, 0.2, 1, 1]]
        for i in range(10):
            x = random.uniform(-2.5, 2.5)
            y = random.uniform(-2, 2)
            z = random.uniform(0.5, 2)
            self.balloons.append(Balloon(x, y, z, colors[i % len(colors)]))
        print(f"🎈 Created {len(self.balloons)} balloons!")
    
    def move_towards_balloons(self):
        while self.running:
            # Find nearest balloon
            nearest = None
            min_dist = 999
            for b in self.balloons:
                if not b.caught:
                    dist = math.sqrt((b.x - self.x)**2 + (b.y - self.y)**2)
                    if dist < min_dist:
                        min_dist = dist
                        nearest = b
            if nearest:
                # Move towards balloon
                dx = nearest.x - self.x
                dy = nearest.y - self.y
                angle_to = math.atan2(dy, dx)
                # Turn towards balloon
                angle_diff = angle_to - self.angle
                if angle_diff > 0.1:
                    self.angle += 0.08
                elif angle_diff < -0.1:
                    self.angle -= 0.08
                # Move forward
                self.x += 0.04 * math.cos(self.angle)
                self.y += 0.04 * math.sin(self.angle)
                # Boundaries
                self.x = max(-3.2, min(3.2, self.x))
                self.y = max(-2.8, min(2.8, self.y))
                try:
                    self.pepper.setPosition([self.x, self.y, 0.8])
                except:
                    pass
                
                # Catch if close enough
                if min_dist < 0.5:
                    nearest.catch()
                    self.balloons.remove(nearest)
                    self.score += 10
                    self.celebrate()
                    # Create new balloon
                    colors = [[1, 0.2, 0.2, 1], [0.2, 1, 0.2, 1], [0.2, 0.2, 1, 1]]
                    new_balloon = Balloon(random.uniform(-2.5, 2.5), random.uniform(-2, 2), 0.3, random.choice(colors))
                    self.balloons.append(new_balloon)
                    print(f"🎉 Caught balloon! Score: {self.score}")
                    self.send_to_dashboard()
            time.sleep(0.05)
    
    def celebrate(self):
        # Raise arms to celebrate
        try:
            for _ in range(2):
                self.pepper.setAngles("LShoulderPitch", 1.2, 0.2)
                self.pepper.setAngles("RShoulderPitch", 1.2, 0.2)
                time.sleep(0.2)
                self.pepper.setAngles("LShoulderPitch", 0, 0.2)
                self.pepper.setAngles("RShoulderPitch", 0, 0.2)
                time.sleep(0.2)
        except:
            pass
    
    def send_to_dashboard(self):
        try:
            requests.post(f"{DASHBOARD_URL}/api/update-score", 
                         json={"score": self.score, "game": "balloon_catch"}, timeout=1)
        except:
            pass
    
    def run_simulation(self):
        while self.running:
            p.stepSimulation()
            for b in self.balloons:
                b.update()
            time.sleep(1/240.)
    
    def run(self):
        while True:
            try:
                cmd = input("\n🎮 Command (catch/stop/score/exit): ").strip().lower()
                if cmd == 'exit':
                    self.running = False
                    print("👋 Game ended!")
                    break
                elif cmd == 'score':
                    print(f"🏆 Score: {self.score}")
                elif cmd == 'stop':
                    print("⏸️ Stopped moving")
                    time.sleep(1)
                elif cmd == 'catch':
                    print("🎈 Chasing balloons!")
            except KeyboardInterrupt:
                self.running = False
                break

if __name__ == "__main__":
    game = PepperBalloonGame()
    game.run()
