docker start c5fce01a328d
docker exec -it c5fce01a328d bashapt-get update
apt-get install -y espeak alsa-utils pulseaudiocd /app/Research_Quiz_Full
export QT_X11_NO_MITSHM=1
python3 -c "
import sys
import builtins
import config
from robot import Robot
from Scenario2 import Scenario

builtins.links = getattr(config, 'links', {})
builtins.questions = getattr(config, 'questions', {})

try:
    pepper = Robot()
    print('\n🔊 CHECK YOUR VOLUME: Pepper is starting...\n')
    sc = Scenario('1', pepper)
    sc.welcome() 
except Exception as e:
    print(f'[ERROR]: {e}')
"This allows the container to 'talk' to your speakers
pactl load-module module-native-protocol-unix socket=/tmp/pulseaudio.socket

# This allows the container to 'see' your screen
xhost +local:docker
cat <<EOF > /app/Research_Quiz_Full/robot.py
import time
import random
import threading
from qibullet import SimulationManager

class Robot:
    def __init__(self):
        print("[INIT] Launching High-Activity Pepper...")
        self.sim = SimulationManager()
        self.client = self.sim.launchSimulation(gui=True)
        self.pepper = self.sim.spawnPepper(self.client, spawn_ground_plane=True)
        self.stand()

    def stand(self):
        self.pepper.goToPosture("StandInit", 0.6)

    def _move_around(self, duration):
        """Makes Pepper move his base, head, and arms simultaneously"""
        end_time = time.time() + duration
        while time.time() < end_time:
            # Random Base movement (Forward/Backward and Rotation)
            x_vel = random.uniform(-0.2, 0.2)
            theta_vel = random.uniform(-0.5, 0.5)
            self.pepper.moveTo(x_vel, 0, theta_vel, _async=True)
            
            # Random Arm gestures
            self.pepper.setAngles(
                ["LShoulderPitch", "RShoulderPitch", "HeadYaw", "HeadPitch"],
                [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 
                 random.uniform(-0.8, 0.8), random.uniform(-0.2, 0.2)],
                0.2
            )
            time.sleep(0.8)
        
        self.pepper.stopMove()
        self.stand()

    def say(self, text):
        # Visual Speech Bubble
        border = "=" * (len(text) + 4)
        print(f"\n{border}\n|  {text}  |\n{border}")
        
        duration = max(len(text) / 10.0, 2.5)
        # Trigger the movement thread
        threading.Thread(target=self._move_around, args=(duration,)).start()
        time.sleep(duration)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None
EOFcd /app/Research_Quiz_Full
python3 -c "
from robot import Robot
from Scenario2 import Scenario
p = Robot()
s = Scenario('1', p)
s.welcome()
"