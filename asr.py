import queue
import sounddevice as sd
import json
import sys
import time
from vosk import Model, KaldiRecognizer

class SpeechRecognizer:
    def __init__(self, model_path, samplerate=16000):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, samplerate)
        self.queue = queue.Queue()
        self.samplerate = samplerate

    def callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}", file=sys.stderr)
        self.queue.put(bytes(indata))

    def listen(self, timeout=5):
        """الاستماع حتى نهاية الجملة أو انتهاء المهلة"""
        print("Listening...")
        try:
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                                   device=None, dtype='int16', channels=1,
                                   callback=self.callback):
                start_time = time.time()
                while time.time() - start_time < timeout:
                    data = self.queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '')
                        if text:
                            return text
                # إذا لم يتم التعرف على شيء خلال المهلة، نعيد آخر نص جزئي
                partial = json.loads(self.recognizer.PartialResult())
                text = partial.get('partial', '')
                return text if text else None
        except Exception as e:
            print(f"خطأ في الاستماع: {e}")
            return None
