import time
import webbrowser
import requests
import urllib.parse

GAME_URL = "http://localhost:5001"
CHAT_API = "https://text.pollinations.ai/v1/chat/completions"
IMAGE_API = "https://image.pollinations.ai/prompt/"
YOUTUBE_BASE = "https://www.youtube.com/results?search_query="
CARTOON_SUFFIX = "cartoon for kids educational"

def chat_with_ai(msg):
    data = {"model": "openai", "messages": [{"role": "system", "content": "You are Pepper, a friendly robot. Respond in 1 short, fun sentence in ENGLISH."}, {"role": "user", "content": msg}]}
    try:
        r = requests.post(CHAT_API, json=data, timeout=10)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "Awesome! Tell me more! 😊"

def process(cmd):
    c = cmd.lower().strip()
    if c in ["game","games","play","لعبة"]:
        webbrowser.open(GAME_URL)
        return "🎮 Opening your ASD games at http://localhost:5001!"
    elif c.startswith("how to"):
        topic = c.replace("how to","").strip()
        url = YOUTUBE_BASE + urllib.parse.quote(topic + " " + CARTOON_SUFFIX)
        webbrowser.open(url)
        return "📺 Opening cartoon video about " + topic + "!"
    elif c.startswith("picture") or c.startswith("image") or c.startswith("صورة"):
        topic = c.replace("picture","").replace("image","").replace("صورة","").strip()
        url = IMAGE_API + topic.replace(" ", "%20")
        webbrowser.open(url)
        return "🖼️ Picture of " + topic + "!"
    elif c in ["dance","رقص"]:
        return "Let's dance! 💃"
    elif c in ["wave","hello","hi"]:
        return "Hello Lamia! 👋"
    return None

print("\n" + "="*50)
print("🤖 PEPPER AI CHAT")
print("="*50)
print("Commands: game, how to wash face, picture lion, dance, wave, hello")
print("Games: http://localhost:5001")
print("="*50 + "\n")
print("🤖 Pepper: Hello Lamia! Type 'game' for your ASD games!\n")

while True:
    try:
        user = input("👶 You: ").strip()
        if user.lower() in ["exit","quit","bye","خروج"]:
            print("🤖 Pepper: Goodbye! 👋")
            break
        if not user:
            continue
        result = process(user)
        if result:
            print("🤖 Pepper: " + result)
        else:
            print("🤖 Pepper: " + chat_with_ai(user))
    except KeyboardInterrupt:
        print("\n🤖 Pepper: Goodbye! 👋")
        break
