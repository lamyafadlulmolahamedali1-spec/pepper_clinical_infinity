#!/usr/bin/env python3
"""
اختبار شامل للصوت: تشغيل وتسجيل.
"""
import time
import sys
from speech.tts import TextToSpeech
from speech.asr import SpeechRecognizer

def test_tts():
    print("اختبار تحويل النص إلى كلام...")
    tts = TextToSpeech()
    tts.speak("Hello, I am Pepper. This is a test of my voice.")
    time.sleep(3)  # انتظار انتهاء الكلام
    print("تم اختبار TTS.")

def test_asr():
    print("اختبار التعرف على الكلام... (تحدث الآن)")
    asr = SpeechRecognizer(model_path='/app/data/vosk-model/vosk-model-small-en-us-0.15/')
    text = asr.listen(timeout=10)
    if text:
        print(f"تم التعرف على: {text}")
    else:
        print("لم يتم التعرف على أي كلام.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tts":
        test_tts()
    elif len(sys.argv) > 1 and sys.argv[1] == "asr":
        test_asr()
    else:
        print("الاستعمال: python test_audio.py [tts|asr]")
