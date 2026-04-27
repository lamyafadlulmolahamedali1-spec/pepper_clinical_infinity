import time
import threading
import queue
import pyttsx3
import speech_recognition as sr

class PepperTerminal:
    def __init__(self):
        print("🤖 Pepper شغال في التيرمينال...")
        
        # الصوت
        self.init_voice()
        self.init_speech_recognition()
        
        self.running = True
        self.questions_queue = queue.Queue()
        self.start_listener()
        
        print("✅ Pepper جاهز! اتكلمي معاه من الميكروفون\n")
        self.speak("Hello! I am Pepper. Ask me anything!")

    def init_voice(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 160)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
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

    def start_listener(self):
        def listen():
            while self.running:
                text = self.listen_voice()
                if text:
                    self.questions_queue.put(text)
        threading.Thread(target=listen, daemon=True).start()

    def run(self):
        print("\n" + "="*60)
        print("🌟 Pepper في التيرمينال - اسأليه وهيرد عليك بالصوت")
        print("="*60 + "\n")
        
        while self.running:
            if not self.questions_queue.empty():
                question = self.questions_queue.get()
                print(f"\n📝 سؤالك: {question}")

                if "hello" in question or "hi" in question:
                    self.speak("Hello! Nice to meet you!")
                
                elif "how are you" in question:
                    self.speak("I'm doing great! Thanks for asking.")
                
                elif "what is your name" in question:
                    self.speak("I am Pepper, your friendly robot.")
                
                elif "bye" in question or "goodbye" in question:
                    self.speak("Goodbye! It was nice talking to you!")
                    self.running = False
                    break
                
                elif "story" in question:
                    self.speak("Once upon a time, there was a robot named Pepper who loved to talk to people.")
                
                elif "joke" in question:
                    self.speak("Why don't robots get tired? Because they recharge!")
                
                else:
                    self.speak("That's interesting! Tell me more.")
                
                time.sleep(1)

            time.sleep(0.1)

if __name__ == "__main__":
    app = PepperTerminal()
    app.run()
