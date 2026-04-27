import time
import pybullet as p
import pybullet_data
import threading
import queue
from qibullet import SimulationManager
import pyttsx3
import speech_recognition as sr

class PepperUltraLight:
    def __init__(self):
        print("🚀 تشغيل Pepper بأخف إعدادات...")
        
        self.init_voice()
        self.init_speech_recognition()
        
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
        
        # أطفاء كل شي
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_TINY_RENDERER, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_WIREFRAME, 0)
        
        print("🤖 تحميل Pepper...")
        self.pepper = self.sim_manager.spawnPepper(
            self.client,
            translation=[0, 0, 0],
            quaternion=[0, 0, 0, 1]
        )
        
        # حركة بسيطة
        self.pepper.setAngles(["HeadYaw"], [0.3], 0.1)
        
        self.running = True
        self.questions_queue = queue.Queue()
        self.start_listener()
        
        print("✅ Pepper ظهر؟ خلينا نشوف...")
        self.speak("Hello! I am here!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

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
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
            text = self.recognizer.recognize_google(audio)
            print(f"📝 سمعت: {text}")
            return text.lower()
        except:
            return None

    def move_head(self):
        self.pepper.setAngles(["HeadYaw"], [0.5], 0.1)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadYaw"], [-0.5], 0.1)
        time.sleep(0.2)
        self.pepper.setAngles(["HeadYaw"], [0.0], 0.1)

    def start_listener(self):
        def listen():
            while self.running:
                text = self.listen_voice()
                if text:
                    self.questions_queue.put(text)
        threading.Thread(target=listen, daemon=True).start()

    def run(self):
        last_move = time.time()
        
        while self.running:
            if time.time() - last_move > 5:
                self.move_head()
                last_move = time.time()

            if not self.questions_queue.empty():
                question = self.questions_queue.get()
                if "hello" in question:
                    self.speak("Hello!")
                elif "how are you" in question:
                    self.speak("I'm good!")
                elif "bye" in question:
                    self.speak("Bye!")
                    break
                else:
                    self.speak("Interesting!")

            time.sleep(0.1)

    def __del__(self):
        if hasattr(self, 'sim_manager'):
            self.sim_manager.stopSimulation(self.client)

if __name__ == "__main__":
    app = PepperUltraLight()
    app.run()
