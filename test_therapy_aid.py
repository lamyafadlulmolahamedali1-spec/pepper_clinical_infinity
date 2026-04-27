#!/usr/bin/env python3
"""اختبار Therapy Aid Tool - تتبع التقدم"""
import time
import random

print("🔬 Testing Therapy Aid Tool")
print("="*50)

class TherapySession:
    def __init__(self):
        self.sessions = []
        self.current_session = []
    
    def start_session(self):
        self.current_session = []
        print("📋 Session started!")
    
    def record_interaction(self, success):
        self.current_session.append(success)
        print(f"   Recorded: {'✅ Success' if success else '❌ Attempt'}")
    
    def end_session(self):
        if self.current_session:
            success_rate = sum(self.current_session) / len(self.current_session) * 100
            self.sessions.append(success_rate)
            print(f"📊 Session complete! Success rate: {success_rate:.1f}%")
            return success_rate
        return 0

# Simulation
therapy = TherapySession()
therapy.start_session()

print("\n🎮 Simulating therapy interactions...")
for i in range(5):
    success = random.choice([True, True, False, True, True])
    therapy.record_interaction(success)
    time.sleep(0.5)

therapy.end_session()
print(f"\n📈 Overall progress: {len(therapy.sessions)} sessions completed")
print("✅ Test complete!")
