from robot_config import MODE, ROBOT_IP, PORT

class RobotBridge:
    def __init__(self):
        self.mode = MODE
        self.motion = None
        self.tts = None
        self.tablet = None
        self.video = None
        
        if self.mode == "REAL":
            import qi
            self.session = qi.Session()
            self.session.connect(f"tcp://{ROBOT_IP}:{PORT}")
            self.motion = self.session.service("ALMotion")
            self.tts = self.session.service("ALTextToSpeech")
            self.tablet = self.session.service("ALTabletService")
            self.video = self.session.service("ALVideoDevice")
            print("--- Connected to Real Pepper Hardware ---")
        else:
            print("--- Running in Simulation Mode (PyBullet) ---")

    def say(self, text):
        if self.mode == "REAL":
            self.tts.say(text)
        else:
            print(f"[SIMULATION VOICE]: {text}")

    def show_tablet(self, url):
        if self.mode == "REAL":
            self.tablet.showImage(url)
        else:
            print(f"[SIMULATION TABLET]: Showing {url}")

    def move_joint(self, name, angle):
        if self.mode == "REAL":
            self.motion.setAngles(name, angle, 0.1)
        else:
            print(f"[SIMULATION MOTION]: Moving {name} to {angle}")
