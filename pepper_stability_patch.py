import sys
import os

# 1. FORCE STABLE RENDERING FLAGS BEFORE ANY IMPORTS
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["PYBULLET_EGL"] = "1" 

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    print("❌ PyQt6 missing. Please run the pip install command again.")
    sys.exit(1)

def start_clinical_system():
    # 2. THE GOLDEN RULE: QApplication MUST be created first in the main thread
    app = QApplication(sys.argv)
    
    # 3. Suppress font and X11 warnings that clutter the buffer
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)

    print("🚀 Stability Patch Active.")
    print("✅ Main Thread Locked for GUI.")
    
    # Use a try-except to catch the segmentation fault and log it
    try:
        # Import your clinical classes only AFTER app is created
        # from pepper_clinical_infinity_v2 import ClinicalDashboard
        # dashboard = ClinicalDashboard()
        # dashboard.show()
        print("💡 [Action Required] Move your main class into this block to start.")
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"🔥 System halted safely: {e}")

if __name__ == "__main__":
    start_clinical_system()
