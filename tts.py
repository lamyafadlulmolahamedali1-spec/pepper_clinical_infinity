import pyttsx3
import threading
import os

class TextToSpeech:
    def __init__(self):
        # التأكد من وجود محرك eSpeak
        try:
            self.engine = pyttsx3.init()
            # تعيين الصوت إلى eSpeak إذا كان متاحًا
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'espeak' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.9)
        except Exception as e:
            print(f"خطأ في تهيئة pyttsx3: {e}")
            print("سيتم استخدام gTTS كبديل (يتطلب إنترنت)")
            self.use_gtts = True
            from gtts import gTTS
            import pygame
            self.gtts_available = True
            self.engine = None
        else:
            self.use_gtts = False

    def speak(self, text):
        threading.Thread(target=self._speak, args=(text,)).start()

    def _speak(self, text):
        if self.use_gtts:
            self._speak_gtts(text)
        else:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"خطأ في pyttsx3: {e}")
                self._speak_gtts(text)

    def _speak_gtts(self, text):
        try:
            from gtts import gTTS
            import pygame
            import tempfile
            tts = gTTS(text=text, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                tts.save(f.name)
                pygame.mixer.init()
                pygame.mixer.music.load(f.name)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    threading.Event().wait(0.1)
                os.unlink(f.name)
        except Exception as e:
            print(f"فشل تشغيل الصوت عبر gTTS: {e}")
