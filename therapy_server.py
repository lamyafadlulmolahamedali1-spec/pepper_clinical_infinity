from flask import Flask, request, jsonify, render_template_string
import datetime

app = Flask(__name__)
logs = []

HTML_PAGE = """
<html>
    <head><title>تقرير بيبر الذكي</title></head>
    <body style="font-family: sans-serif; direction: rtl; background: #f4f7f6; padding: 20px;">
        <h1 style="color: #2c3e50;">📊 سجل تفاعل بيبر (AI Vision & Voice)</h1>
        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {% for log in logs %}
                <p style="border-bottom: 1px dotted #ccc; padding: 8px; margin: 0;">{{ log }}</p>
            {% endfor %}
        </div>
        <script>setTimeout(function(){ location.reload(); }, 2000);</script>
    </body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, logs=reversed(logs))

@app.route('/update_context', methods=['POST'])
def update_context():
    data = request.json
    emo = data.get("emotion", "neutral")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{timestamp}] عيون الكمبيوتر رصدت: {emo}")
    return jsonify({"status": "ok"})

@app.route('/report', methods=['GET'])
def get_report():
    return jsonify({"full_report": logs})

if __name__ == "__main__":
    app.run(port=5009)
