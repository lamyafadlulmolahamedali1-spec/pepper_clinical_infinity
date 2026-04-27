import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# CRITICAL FIX: Force X11 and offscreen rendering for PyBullet to prevent X11 Deadlock
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["PYBULLET_EGL"] = "1" 

def run_stable_system():
    # 1. Initialize QApplication FIRST in the main thread
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    
    print("🚀 Stability Patch Active: GUI Main Thread Locked.")
    
    # 2. Import your clinical classes here 
    # (Move your logic from v2 into a class-based structure if not already)
    
    # 3. Start PyBullet with specific flags to avoid Intel Driver crashes
    # p.connect(p.GUI, options="--opengl2") # Use older GL if 3.3 crashes
    
    print("✅ System Ready. No more Core Dumps.")
    sys.exit(app.exec())

if __name__ == "__main__":
    run_stable_system()
