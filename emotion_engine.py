from deepface import DeepFace

def get_detailed_emotion(frame):
    try:
        # This analyzes all 7 emotions: happy, sad, angry, fear, surprise, disgust, neutral
        results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        res = results[0]
        return res['dominant_emotion'], res['emotion']
    except:
        return "neutral", {"neutral": 100}
