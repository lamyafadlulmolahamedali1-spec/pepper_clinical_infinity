#!/usr/bin/env python3
import os
import sys
import pyttsx3
import speech_recognition as sr
import google.generativeai as genai

# Completely suppress terminal noise from ALSA/JACK
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
stderr = sys.stderr
sys.stderr = open(os.devnull, 'w')

genai.configure(api_key="AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8")
model = genai.GenerativeModel('gemini-1.5-flash')

def pepper_talk(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    print(f"🤖 Pepper: {text}")
    engine.say(text)
    engine.runAndWait()

def main():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 600
    
    # Restore stderr briefly to show the start-up
    pepper_talk("Clean interface loaded. Talk to me!")

    while True:
        with sr.Microphone() as source:
            print(f"\n👂 Listening...", end=" ", flush=True)
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                print("⚡ Thinking...")
                user_text = recognizer.recognize_google(audio)
                print(f"👤 You: {user_text}")
                
                # Pepper-flavored response
                response = model.generate_content(f"The user said '{user_text}'. Reply as Pepper, a helpful social robot, in one short sentence.")
                pepper_talk(response.text)
                    
            except Exception:
                # Silently restart listening on error/silence
                print("♻️") 
                continue

if __name__ == "__main__":
    main()
