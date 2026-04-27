    def safe_repeat(self, text):
        if not hasattr(self, '_last_speech_time'): self._last_speech_time = 0
        import time
        if time.time() - self._last_speech_time > 10: # لا يتكلم إلا كل 10 ثوانٍ
            self.sigs.speak.emit(text)
            self._last_speech_time = time.time()
