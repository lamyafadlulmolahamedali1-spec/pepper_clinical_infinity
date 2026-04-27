import time
import threading
import pyttsx3
import random
from qibullet import SimulationManager

# Check if you have socketio installed for the "Real Connection"
try:
    import socketio
    SIO_OK = True
except:
    SIO_OK = False

class PepperTherapyAI:
    def __init__(self):
        self.sim_manager = SimulationManager()
        self.client = self.sim_manager.launchSimulation(gui=True)
        self.pepper = self.sim_manager.spawnPepper(self.client, spawn_ground_plane=True)
        self.engine = pyttsx3.init()
        
        if SIO_OK:
            self.sio = socketio.Client()
            self.setup_socket_events()

    def setup_socket_events(self):
        @self.sio.on('game_move')
        def on_move(data):
            # Data from your Tic-Tac-Toe dashboard
            move = data.get('position')
            self.speak(f"I saw that, Ahmed! You put your mark in the {move} square. Great choice!")
            self.pepper.setAngles("RHand", 1.0, 0.1) # Smooth hand move

        @self.sio.on('game_won')
        def on_win(data):
            self.speak("Victory! Ahmed, you won the game! Let's do a happy dance.")
            self.happy_dance()

    def speak(self, text):
        print(f"🤖 Pepper: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def happy_dance(self):
        """Smooth dance movements around the room"""
        self.pepper.moveTo(0.5, 0.5, 1.5) # Walk in a small circle
        self.pepper.setAngles(["LShoulderPitch", "RShoulderPitch"], [-0.5, -0.5], 0.2)
        time.sleep(1)
        self.pepper.goToPosture("Stand", 0.5)

    def start_bridge(self):
        if SIO_OK:
            try:
                self.sio.connect('http://localhost:5009')
                print("✅ Connected to Games Dashboard!")
            except:
                print("⚠️ Dashboard not running on 5009. Running in Simulation mode.")
        
        self.speak("Hello! I am ready to play Tic-Tac-Toe with you through my tablet.")
        # Make Pepper walk to the 'starting position' smoothly
        self.pepper.moveTo(1.0, 0, 0, _async=True)

if __name__ == "__main__":
    bot = PepperTherapyAI()
    bot.start_bridge()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.sim_manager.stopSimulation(bot.client)
