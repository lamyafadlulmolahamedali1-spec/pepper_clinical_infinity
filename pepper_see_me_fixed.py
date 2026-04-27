import time
import pybullet as p
import pybullet_data
import threading
import queue
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr

class PepperSeeMe:
    def __init__(self):
        print("🚀 تشغيل Pepper وأنا أشوفه...")
        
        # الصوت
        self.init_voice()
        self.init_speech_recognition()
        
        # محاكي بدون scaling
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # أقل إعدادات ممكنة
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_WIREFRAME, 0)
        
        # Pepper واحد
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[0, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # وضعية وقوف طبيعية
        self.reset_pose()
        
        self.running = True
        self.questions_queue = queue.Queue()
        self.start_listener()
        
        print("✅ Pepper واقف قدامك! اسأليه وهيرد ويتحرك\n")
        self.speak("Hello! I am Pepper. Look at me!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'english' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def init_speech_recognition(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

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
        except:
            return None

    def reset_pose(self):
        self.pepper.setAngles(["HeadYaw", "HeadPitch"], [0.0, 0.2], 0.1)
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [0.2, 1.2], 0.1)
        self.pepper.setAngles(["LShoulderPitch", "LElbowRoll"], [1.57, -1.2], 0.1)

    def wave_hand(self):
        self.pepper.setAngles(["RShoulderPitch", "RElbowRoll"], [-0.8, 1.2], 0.2)
        time.sleep(0.3)
        self.pepper.setAngles(["RShoulderPitch"], [0.2], 0.2)
        time.sleep(0.3)
        self.reset_pose()

    def look_around(self):
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.1)
        time.sleep(0.3)
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.1)

    def start_listener(self):
        def listen():
            while self.running:
                text = self.listen_voice()
                if text:
                    self.questions_queue.put(text)
        threading.Thread(target=listen, daemon=True).start()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper قدامك! اتكلمي معاه")
        print("="*60 + "\n")
        
        last_move_time = time.time()
        
        while self.running:
            # حركة كل 7 ثواني عشان يبان حي
            if time.time() - last_move_time > 7:
                self.look_around()
                last_move_time = time.time()

            if not self.questions_queue.empty():
                question = self.questions_queue.get()
                print(f"\n📝 سؤالك: {question}")

                if "hello" in question or "hi" in question:
                    self.wave_hand()
                    self.speak("Hello! Nice to see you!")
                
                elif "how are you" in question:
                    self.speak("I'm doing great!")
                
                elif "move" in question:
                    self.wave_hand()
                    self.speak("I'm waving!")
                
                elif "what is your name" in question:
                    self.speak("I am Pepper.")
                
                elif "bye" in question or "goodbye" in question:
                    self.wave_hand()
                    self.speak("Goodbye!")
                    self.running = False
                    break
                
                else:
                    self.speak("That's interesting!")
                
                time.sleep(1)

            time.sleep(0.1)

    def __del__(self):
        if hasattr(self, 'sim_manager'):
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperSeeMe()
    app.run()
