import time
import pybullet as p
import pybullet_data
import threading
import random
from qibullet import SimulationManager
import pyttsx3

class PepperTalkative:
    def __init__(self):
        print("🚀 تشغيل Pepper الثرثار...")
        
        # الصوت
        self.init_voice()
        
        # محاكي خفيف
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True, automatic_scaling=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات أخف
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
        
        # Pepper واحد
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[0, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضعية البداية
        self.reset_pose()
        
        # مواضيع الكلام
        self.topics = [
            ("مرحباً! أنا Pepper، رفيقكم الآلي.", 3),
            ("أستطيع التحرك والتحدث في نفس الوقت!", 4),
            ("لماذا لا تتعب الروبوتات؟ لأنه يعاد شحنها!", 5),
            ("ما هو اسمي؟ بيبر طبعاً!", 3),
            ("أحب الحديث مع الناس، وأتعلم كل يوم.", 4),
            ("متى سيحكم الروبوتات العالم؟ عندما نتعلم الطهي!", 6),
            ("أنا سعيد جداً بلقائكم.", 3),
            ("لدي يدان يمكنهما التلويح والتحرك.", 4),
            ("هل تعلم؟ أنا أرى العالم من خلال الكاميرا.", 5),
            ("أتمنى لكم يوماً جميلاً!", 3)
        ]
        
        self.running = True
        self.speak("Hello! I am Pepper. Let me introduce myself.")
        
    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text):
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()

    def reset_pose(self):
        """وضعية الوقوف العادية"""
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def move_hand_right(self, angle):
        """تحريك اليد اليمنى"""
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [angle, 1.2], 0.2)

    def move_hand_left(self, angle):
        """تحريك اليد اليسرى"""
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57 - angle, -1.2], 0.2)

    def wave(self):
        """يلوح بيده"""
        for i in range(3):
            self.move_hand_right(-0.8)
            time.sleep(0.2)
            self.move_hand_right(0.2)
            time.sleep(0.2)
        self.reset_pose()

    def look_around(self):
        """يدور رأسه"""
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.1)

    def move_both_hands(self):
        """يحرك اليدين معاً"""
        self.move_hand_right(-0.5)
        self.move_hand_left(-0.5)
        time.sleep(0.5)
        self.reset_pose()

    def random_move(self):
        """حركة عشوائية"""
        moves = [self.wave, self.look_around, self.move_both_hands]
        random.choice(moves)()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper يتكلم ويتحرك من نفسه!")
        print("="*60 + "\n")
        
        topic_index = 0
        last_move_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # كل 7 ثواني حركة عشوائية
            if current_time - last_move_time > 7:
                self.random_move()
                last_move_time = current_time
            
            # كل 10 ثواني يتكلم
            if topic_index < len(self.topics):
                text, duration = self.topics[topic_index]
                print(f"💬 Pepper: {text}")
                self.speak(text)
                
                # حركة أثناء الكلام
                self.wave()
                
                time.sleep(duration)
                topic_index += 1
            else:
                topic_index = 0  # يعيد الكلام من البداية
                time.sleep(2)
            
            time.sleep(0.5)

    def __del__(self):
        if hasattr(self, 'sim_manager'):
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperTalkative()
    app.run()
