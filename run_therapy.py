#!/usr/bin/env python3
"""
تشغيل Pepper مع الثيرابي - ملف مستقل
"""
import sys
import threading
import time
import math
import random
import pybullet as p

# استيراد الملف الأصلي كـ module
sys.path.insert(0, '/home/lamya/pepper_duo/src')

from pepper_balloon_chaser_backup_dance import PepperRobot
from therapy_integration import TherapyThread

class PepperTherapyRobot(PepperRobot):
    """Pepper + Therapy - يرث كل شيء من الأصل"""
    
    def __init__(self):
        super().__init__()
        self.therapy = None
        self.therapy_active = False
        
        # تشغيل الثيرابي تلقائياً بعد 3 ثواني
        threading.Thread(target=self._auto_start_therapy, daemon=True).start()
    
    def _auto_start_therapy(self):
        time.sleep(3)
        print("\n🏥 Auto-starting therapy mode...")
        self.therapy = TherapyThread(self)
        t = threading.Thread(target=self.therapy.run_therapy_loop, daemon=True)
        t.start()
        self.show_text("Therapy session started! 🏥")
        print("✅ Therapy ACTIVE! Pepper will visit children automatically.")
        print("   Commands: 'report', 'stop therapy', 'therapy'\n")
    
    def process_command(self, cmd):
        c = cmd.lower().strip()
        
        if c == "therapy":
            if self.therapy is None:
                self.therapy = TherapyThread(self)
                threading.Thread(target=self.therapy.run_therapy_loop, daemon=True).start()
            self.show_text("Therapy mode ON! 🏥")
            return "🏥 Therapy started!"
        
        elif c == "report":
            if self.therapy:
                self.therapy.print_final_report()
                return "📊 Report printed!"
            return "No active therapy session."
        
        elif c in ["stop therapy", "stop session"]:
            if self.therapy:
                self.therapy.stop()
                self.therapy = None
            return "🛑 Therapy stopped."
        
        # كل الأوامر الأصلية
        return super().process_command(cmd)

if __name__ == "__main__":
    robot = PepperTherapyRobot()
    robot.run()

