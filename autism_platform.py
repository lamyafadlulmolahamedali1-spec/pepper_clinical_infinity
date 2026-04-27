import time
import random
from datetime import datetime

print("\n" + "🌟"*40)
print("🧩 PEPPER AUTISM SUPPORT PLATFORM")
print("🌟"*40 + "\n")

class AutismSession:
    def __init__(self):
        self.rewards = 0
        self.activities_done = []
        self.start = datetime.now()
    
    def run(self):
        print("🤖: مرحباً! أنا Pepper، جاهز لمساعدتك")
        time.sleep(1)
        
        # Activity 1: Emotions
        print("\n1️⃣ 😊 نشاط المشاعر")
        emotions = ["سعيد 😊", "حزين 😢", "غاضب 😠"]
        for e in emotions:
            print(f"   هل هذا وجه {e}؟")
            time.sleep(0.3)
            print("   ⭐ أحسنت!")
            self.rewards += 1
        
        # Activity 2: Memory
        print("\n2️⃣ 🧠 لعبة الذاكرة")
        for i in range(3):
            print(f"   بطاقة {i+1} متطابقة ✓")
            time.sleep(0.3)
            self.rewards += 1
        
        # Activity 3: Break
        print("\n3️⃣ 🧘 استراحة")
        print("   شهيق... زفير...")
        time.sleep(1)
        
        # Summary
        duration = (datetime.now() - self.start).seconds
        print("\n" + "="*50)
        print("📊 نتائج الجلسة")
        print("="*50)
        print(f"⏱️ المدة: {duration} ثانية")
        print(f"⭐ التعزيزات: {self.rewards}")
        print("="*50)
        print("\n✅ شكراً لك! جلسة ناجحة")

# Run session
session = AutismSession()
session.run()
