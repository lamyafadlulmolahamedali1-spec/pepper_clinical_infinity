#!/usr/bin/env python3
"""
Pepper with Simple Voice Recognition
Using arecord + direct Google API
"""

import os
import time
import random
import webbrowser
import urllib.parse
import subprocess
import json
import requests

# ========== Settings ==========
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"

# ========== Jokes ==========
JOKES = [
    "Why did the teddy bear say no to dessert? Because it was stuffed! 🧸",
    "What do you call a sleeping dinosaur? A dino-snore! 🦕",
    "Why don't elephants use computers? They're afraid of the mouse! 🐭",
    "What did the big flower say to the little flower? Hi, bud! 🌸",
    "Why did the cookie go to the doctor? Because it felt crummy! 🍪",
    "What do you call a bear with no teeth? A gummy bear! 🐻",
    "Why did the sun go to school? To get brighter! ☀️",
    "What do you call a fish with no eyes? A fsh! 🐟",
]

# ========== Voice Recognition ==========
def record_audio(duration=4):
    """Record audio using arecord"""
    filename = "/tmp/voice.wav"
    cmd = f"arecord -D plughw:1,6 -d {duration} -f cd -t wav {filename} 2>/dev/null"
    os.system(cmd)
    return filename if os.path.exists(filename) else None

def recognize_with_google(audio_file):
    """Send audio to Google Speech Recognition"""
    try:
        # Use Google's free speech API endpoint
        import base64
        import subprocess
        
        # Convert to FLAC (better compression)
        flac_file = "/tmp/voice.flac"
        subprocess.run([
            "ffmpeg", "-i", audio_file, "-ar", "16000", "-ac", "1", 
            "-c:a", "flac", flac_file, "-y"
        ], capture_output=True)
        
        if not os.path.exists(flac_file):
            return None
        
        # Read audio data
        with open(flac_file, 'rb') as f:
            audio_data = f.read()
        
        # Google Speech API (free endpoint)
        url = "https://www.google.com/speech-api/v2/recognize"
        params = {
            "output": "json",
            "lang": "en-US",
            "key": "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"
        }
        
        headers = {
            "Content-Type": "audio/flac"
        }
        
        response = requests.post(url, params=params, headers=headers, data=audio_data, timeout=10)
        
        if response.status_code == 200:
            # Parse response (Google returns multiple JSON lines)
            for line in response.text.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        if 'result' in data and data['result']:
                            text = data['result'][0]['alternative'][0]['transcript']
                            return text.lower()
                    except:
                        pass
        
        # Alternative: Try Vosk (offline) if available
        return None
        
    except Exception as e:
        print(f"   Recognition error: {e}")
        return None

def listen():
    """Listen and recognize speech"""
    print("   🎤 Listening... (say something clearly)")
    
    # Record
    audio_file = record_audio(4)
    if not audio_file:
        print("   ❌ Recording failed")
        return None
    
    print("   🔍 Recognizing...")
    
    # Try Google recognition
    text = recognize_with_google(audio_file)
    
    if text:
        print(f"   ✅ Heard: '{text}'")
        return text
    else:
        print("   ❌ Could not recognize. Try speaking clearly!")
        return None

# ========== Command Processing ==========
def process_command(cmd):
    """Process voice/text commands"""
    cmd = cmd.lower().strip()
    
    # Movement commands
    if cmd in ["walk", "move", "go", "forward", "go forward"]:
        return "Walking forward! 🚶‍♂️"
    elif cmd in ["come", "come here", "come to me"]:
        return "Coming to you! 🚶‍♂️✨"
    elif cmd in ["back", "backward", "move back", "go back"]:
        return "Walking backward! 🔙"
    elif cmd in ["left", "turn left"]:
        return "Turning left! 🔄"
    elif cmd in ["right", "turn right"]:
        return "Turning right! 🔄"
    elif cmd in ["dance", "dance!", "let's dance"]:
        return "Let's dance! 💃🕺"
    elif cmd in ["wave", "hello", "hi", "hey", "say hello"]:
        return "Hello! 👋"
    elif cmd in ["joke", "tell joke", "funny", "say a joke"]:
        return random.choice(JOKES) + " 😂"
    
    # How-to questions
    if "how to" in cmd:
        topic = cmd.replace("how to", "").replace("?", "").replace("please", "").strip()
        if topic:
            search = f"{topic} {CARTOON_SUFFIX}"
            url = f"{YOUTUBE_BASE}{urllib.parse.quote(search)}"
            webbrowser.open(url)
            return f"📺 Opening cartoon video about {topic}! Watch and learn! 🌟"
        else:
            return "What would you like to learn? Say 'how to wash my face'!"
    
    # General responses
    if "hello" in cmd or "hi" in cmd:
        return "Hello there! How can I help you? 😊"
    if "thank" in cmd:
        return "You're welcome! I'm happy to help! 🌟"
    if "good" in cmd:
        return "I'm glad you're doing well! 🎉"
    
    return None

# ========== AI Chat (fallback) ==========
def ai_chat(message):
    """Get AI response for general chat"""
    try:
        data = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short, fun sentence in ENGLISH."},
                {"role": "user", "content": message}
            ]
        }
        response = requests.post("https://text.pollinations.ai/v1/chat/completions", json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except:
        pass
    return f"That's interesting! Tell me more, friend! 😊"

# ========== Main ==========
def main():
    print("\n" + "="*60)
    print("🤖 PEPPER - Voice Controlled Robot Assistant")
    print("="*60)
    print("🎤 Say commands out loud OR type them!")
    print("")
    print("📝 COMMANDS:")
    print("   • walk / come / dance / wave / joke")
    print("   • how to [anything] - opens cartoon video")
    print("   • or just chat with me!")
    print("="*60)
    
    print("\n🤖 Pepper: Hello! I'm Pepper! What would you like to do?")
    print("   (Type 't' for typing, 's' for speaking, or 'exit' to quit)")
    
    while True:
        try:
            choice = input("\n🎤 (t)ype / (s)peak / (e)xit: ").strip().lower()
            
            if choice == 'e':
                print("\n🤖 Pepper: Goodbye! Come play again soon! 👋")
                break
            
            elif choice == 's':
                text = listen()
                if text:
                    response = process_command(text)
                    if response:
                        print(f"🤖 Pepper: {response}")
                    else:
                        print(f"🤖 Pepper: I heard '{text}', but I don't understand.")
                        print("   Try: walk, dance, wave, joke, or how to...")
                else:
                    print("🤖 Pepper: I didn't hear anything. Try speaking clearly!")
                    
            elif choice == 't':
                cmd = input("👶 You: ").strip()
                if cmd.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    print("🤖 Pepper: Goodbye! See you next time! 👋")
                    break
                if cmd:
                    response = process_command(cmd)
                    if response:
                        print(f"🤖 Pepper: {response}")
                    else:
                        # Try AI chat
                        ai_response = ai_chat(cmd)
                        print(f"🤖 Pepper: {ai_response}")
                else:
                    print("🤖 Pepper: Say something!")
            else:
                print("🤖 Pepper: Type 't' to type, 's' to speak, or 'e' to exit")
                
        except KeyboardInterrupt:
            print("\n\n🤖 Pepper: Goodbye! 👋")
            break
        except Exception as e:
            print(f"🤖 Pepper: Oops! {e}. Try again!")

if __name__ == "__main__":
    main()
