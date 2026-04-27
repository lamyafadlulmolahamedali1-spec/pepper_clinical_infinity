import time
import pybullet as p
import pybullet_data
import random
import threading
import queue
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr

class PepperNoCamera:
    def __init__(self):
        print("🚀 تشغيل Pepper بدون كاميرا...")
        
        # الصوت
        self.init_voice()
        self.init_speech_recognition()
        
        # محاكي أخف
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(
            gui=True, 
            automatic_scaling=True
        )
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # إعدادات أخف للرسوميات (بدون ظلال، بدون إضاءة زايدة)
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
        
        # حركات ثابتة عشان يبان حي
        self.reset_pose()
        
        self.running = True
        self.questions_queue = queue.Queue()
        self.start_listener()
        
        print("✅ Pepper جاهز! شوفيه قدامك، اسأليه، وهيرد عليك بصوت\n")
        self.speak("Hello! I am Pepper. Ask me anything!")

    def init_voice(self):
        """صوت واضح وسريع"""
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)  # أسرع شوية
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        # نحاول نختار صوت طبيعي
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        print("✅ صوت Pepper جاهز")

    def init_speech_recognition(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("🎤 الميكروفون جاهز، اتكلمي...")

    def speak(self, text):
        def speak_thread():
            self.engine.say(text)
            self.engine.runAndWait()
        threading.Thread(target=speak_thread, daemon=True).start()

    def listen_voice(self):
        try:
            with self.microphone as source:
                print("🎤 استماع...")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio)
            print(f"📝 سمعت: {text}")
            return text.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            return None

    def reset_pose(self):
        """وضعية وقوف طبيعية"""
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def wave_hand(self):
        """يلوح بيده"""
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.3)
        self.reset_pose()

    def look_around(self):
        """يدور رأسه"""
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.1)

    def nod_head(self):
        """يومئ برأسه"""
        self.pepper.setAngles(["HeadPitch"], [0.3], 0.1)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadPitch"], [0.0], 0.1)

    def start_listener(self):
        def listen():
            while self.running:
                text = self.listen_voice()
                if text:
                    self.questions_queue.put(text)
        threading.Thread(target=listen, daemon=True).start()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper واقف قدامك! اسأليه وشوفيه يتحرك")
        print("="*60 + "\n")
        
        last_move_time = time.time()
        last_random_time = time.time()
        
        while self.running:
            # حركة كل 7 ثواني عشان يبان حي
            if time.time() - last_move_time > 7:
                self.look_around()
                last_move_time = time.time()

            # الأسئلة
            if not self.questions_queue.empty():
                question = self.questions_queue.get()
                print(f"\n📝 سؤالك: {question}")

                if "hello" in question or "hi" in question:
                    self.wave_hand()
                    self.speak("Hello! Nice to see you!")
                
                elif "how are you" in question:
                    self.nod_head()
                    self.speak("I'm doing great! Thanks for asking.")
                
                elif "move" in question:
                    self.wave_hand()
                    self.speak("I'm waving my hand!")
                
                elif "what is your name" in question:
                    self.nod_head()
                    self.speak("I am Pepper, your friendly robot.")
                
                elif "bye" in question or "goodbye" in question:
                    self.wave_hand()
                    self.speak("Goodbye! It was nice talking to you!")
                
                elif "story" in question:
                    self.speak("Once upon a time, there was a robot named Pepper who loved to talk to people.")
                
                elif "joke" in question:
                    self.speak("Why don't robots get tired? Because they recharge!")
                
                else:
                    self.nod_head()
                    self.speak("That's interesting! Tell me more.")
                
                time.sleep(1)

            time.sleep(0.1)

    def __del__(self):
        if hasattr(self, 'sim_manager'):
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperNoCamera()
    app.run()
