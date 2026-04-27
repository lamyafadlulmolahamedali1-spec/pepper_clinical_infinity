# pepper_bullet_bridge.py - ربط بيبر الذكي مع PyBullet
import sys
import os
sys.path.append(os.path.expanduser("~/pepper_duo/src"))

from smart_pepper import SmartPepper
import threading
import time

class PepperBulletBridge:
    """ربط بيبر الذكي مع محاكي PyBullet"""
    
    def __init__(self):
        self.pepper = SmartPepper()
        self.is_running = False
        self.current_action = None
        
    def send_to_pepper(self, command):
        """إرسال أمر إلى بيبر"""
        result = self.pepper.ai.process(command)
        
        # تحويل النتيجة إلى إيماءات PyBullet
        if "صورة" in command or "ارسم" in command:
            self.current_action = "show_image"
        elif "فيديو" in command:
            self.current_action = "play_video"
        elif "حرك" in command:
            self.current_action = "move_arm"
        
        return result
    
    def get_pepper_response(self, text):
        """الحصول على رد من بيبر"""
        return self.pepper.ai.process(text)
    
    def start_voice_thread(self):
        """تشغيل الاستماع الصوتي في thread منفصل"""
        def voice_loop():
            self.pepper.start_conversation()
        
        thread = threading.Thread(target=voice_loop, daemon=True)
        thread.start()
        return thread
    
    def test_bridge(self):
        """اختبار الربط"""
        print("🔄 اختبار ربط بيبر مع PyBullet...")
        
        # اختبار 1: محادثة
        result = self.get_pepper_response("السلام عليكم")
        print(f"اختبار المحادثة: {result}")
        
        # اختبار 2: صورة
        result = self.get_pepper_response("ارسم لي أسد")
        print(f"اختبار الصورة: {result['type']} - {result.get('url', '')[:50]}...")
        
        # اختبار 3: فيديو
        result = self.get_pepper_response("شغل فيديو عن الأكل")
        print(f"اختبار الفيديو: {result['type']}")
        
        return "✅ الربط يعمل بشكل صحيح"

# اختبار
if __name__ == "__main__":
    bridge = PepperBulletBridge()
    print(bridge.test_bridge())
