#!/usr/bin/env python3
import os, sys, threading, time
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QObject, pyqtSignal, Qt

# إعدادات البيئة لمنع رسائل التحذير
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# 1. نظام الإشارات (حل مشكلة QBasicTimer)
class TabletSignals(QObject):
    update_text = pyqtSignal(str)

class PepperTablet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pepper Tablet")
        self.setFixedSize(720, 940)
        self.layout = QVBoxLayout()
        self.label = QLabel("Waiting for Pepper...")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 30px; font-weight: bold;")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        
        self.signals = TabletSignals()
        self.signals.update_text.connect(self.safe_update)

    def safe_update(self, text):
        self.label.setText(text)

# 2. منطق الجلسة الذكية (الذي يطلبه المستخدم)
def therapy_logic(ui):
    # إعداد Gemini هنا (تأكدي من استخدام مفتاح جديد)
    ui.signals.update_text.emit("بيبر جاهز! قل لي اسمك.")
    # محاكاة لطلبات الجلسة الذكية
    time.sleep(3)
    ui.signals.update_text.emit("اغمض عينيك الآن...")
    time.sleep(3)
    ui.signals.update_status = "احسب لي كم إصبع في يدك؟" 
    ui.signals.update_text.emit("كم إصبع في يدك؟ 🖐️")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PepperTablet()
    window.show()
    
    # تشغيل منطق الروبوت في خيط منفصل تماماً
    logic_thread = threading.Thread(target=therapy_logic, args=(window,), daemon=True)
    logic_thread.start()
    
    sys.exit(app.exec())
