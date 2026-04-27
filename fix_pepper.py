import os
import google.generativeai as genai
from PyQt6.QtCore import QObject, pyqtSignal

# إعداد Gemini - استبدلي AIza... بمفتاحك الحقيقي
os.environ["GEMINI_API_KEY"] = "AIzaSy..." 
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

class TabletSignals(QObject):
    update_text = pyqtSignal(str)
    change_color = pyqtSignal(str)
    trigger_animation = pyqtSignal(str)

print("✅ الملف جاهز: fix_pepper.py")
print("✅ المكتبات محملة بنجاح!")
