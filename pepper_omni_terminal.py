import speech_recognition as sr
import sys
import os
import time

def run_omni_direct():
    r = sr.Recognizer()
    # Device Index 4 for your ASUS TUF ALC233 Analog Mic
    mic_index = 4
    
    print("\n--- PEPPER OMNI-SYSTEM: DIRECT TERMINAL [2026] ---")
    
    try:
        while True:
            try:
                with sr.Microphone(device_index=mic_index) as source:
                    # Brief pause to ensure the stream is actually open
                    time.sleep(0.5) 
                    print("\n👂 Listening... (Speak now)")
                    r.adjust_for_ambient_noise(source, duration=0.8)
                    audio = r.listen(source, timeout=10)
                    
                    text = r.recognize_google(audio)
                    print(f"User: {text}")
                    print("Pepper: Processing...")
            
            except sr.UnknownValueError:
                print("Status: Could not hear clearly.")
            except sr.WaitTimeoutError:
                print("Status: Listening timed out.")
            except Exception as e:
                print(f"Status Error: {e}")
                time.sleep(1) # Prevent rapid-fire crashing
                    
    except KeyboardInterrupt:
        print("\n\n[SYSTEM] Terminated by years and cats and end of Fire.")
        sys.exit(0)

if __name__ == "__main__":
    run_omni_direct()
