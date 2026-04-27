#!/usr/bin/env python3
import rospy
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from geometry_msgs.msg import Twist
import time
import random
import threading

class PepperNatural:
    def __init__(self):
        rospy.init_node('pepper_natural', anonymous=True)
        
        # منشورات الحركات
        self.arm_right_pub = rospy.Publisher('/pepper_dcm/RightArm_controller/command', JointTrajectory, queue_size=10)
        self.arm_left_pub = rospy.Publisher('/pepper_dcm/LeftArm_controller/command', JointTrajectory, queue_size=10)
        self.head_pub = rospy.Publisher('/pepper_dcm/Head_controller/command', JointTrajectory, queue_size=10)
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        
        time.sleep(1)
        
        # وضع البداية
        self.reset_arms_to_sides()
        self.reset_head()
        print("✅ Pepper is ready - arms down, standing in the room")
    
    def reset_arms_to_sides(self):
        """Arms down by the sides"""
        # Right arm
        msg_right = JointTrajectory()
        msg_right.joint_names = ['RShoulderPitch', 'RShoulderRoll', 'RElbowYaw', 'RElbowRoll', 'RWristYaw']
        point = JointTrajectoryPoint()
        point.positions = [0.0, 0.0, 0.0, 0.0, 0.0]
        point.time_from_start = rospy.Duration(0.3)
        msg_right.points = [point]
        self.arm_right_pub.publish(msg_right)
        
        # Left arm
        msg_left = JointTrajectory()
        msg_left.joint_names = ['LShoulderPitch', 'LShoulderRoll', 'LElbowYaw', 'LElbowRoll', 'LWristYaw']
        msg_left.points = [point]
        self.arm_left_pub.publish(msg_left)
    
    def reset_head(self):
        """Head neutral position"""
        msg = JointTrajectory()
        msg.joint_names = ['HeadYaw', 'HeadPitch']
        point = JointTrajectoryPoint()
        point.positions = [0.0, 0.0]
        point.time_from_start = rospy.Duration(0.3)
        msg.points = [point]
        self.head_pub.publish(msg)
    
    def move_head(self, yaw=0.0, pitch=0.0):
        """Move head - yaw: left/right, pitch: up/down"""
        msg = JointTrajectory()
        msg.joint_names = ['HeadYaw', 'HeadPitch']
        point = JointTrajectoryPoint()
        point.positions = [yaw, pitch]
        point.time_from_start = rospy.Duration(0.2)
        msg.points = [point]
        self.head_pub.publish(msg)
    
    def walk(self, speed_x=0.5, duration=2.0):
        """Walk at given speed"""
        twist = Twist()
        twist.linear.x = speed_x
        twist.angular.z = 0.0
        
        start_time = time.time()
        rate = rospy.Rate(10)
        
        direction = "forward" if speed_x > 0 else "backward"
        print(f"🚶 Pepper is walking {direction}...")
        
        while time.time() - start_time < duration:
            self.cmd_vel_pub.publish(twist)
            rate.sleep()
        
        # Stop
        twist.linear.x = 0.0
        self.cmd_vel_pub.publish(twist)
        print("🛑 Pepper stopped")
    
    def turn(self, angular_speed=0.5, duration=1.0):
        """Turn left or right"""
        twist = Twist()
        twist.angular.z = angular_speed
        
        start_time = time.time()
        rate = rospy.Rate(10)
        
        direction = "right" if angular_speed < 0 else "left"
        print(f"🔄 Pepper turning {direction}...")
        
        while time.time() - start_time < duration:
            self.cmd_vel_pub.publish(twist)
            rate.sleep()
        
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)
    
    def wave(self):
        """Wave hand"""
        print("👋 Pepper waves...")
        msg = JointTrajectory()
        msg.joint_names = ['RShoulderPitch', 'RShoulderRoll', 'RElbowYaw', 'RElbowRoll', 'RWristYaw']
        point = JointTrajectoryPoint()
        point.positions = [0.3, -0.5, 0.2, 0.1, 0.1]
        point.time_from_start = rospy.Duration(0.3)
        msg.points = [point]
        self.arm_right_pub.publish(msg)
        time.sleep(0.5)
        
        point.positions = [0.0, 0.0, 0.0, 0.0, 0.0]
        point.time_from_start = rospy.Duration(0.3)
        msg.points = [point]
        self.arm_right_pub.publish(msg)
    
    def nod(self):
        """Nod head yes"""
        print("👌 Pepper nods...")
        self.move_head(yaw=0.0, pitch=0.2)
        time.sleep(0.3)
        self.move_head(yaw=0.0, pitch=-0.1)
        time.sleep(0.3)
        self.reset_head()
    
    def look_around(self):
        """Look around the room naturally"""
        print("👀 Pepper looks around...")
        for yaw in [0.5, -0.5, 0.3, -0.3, 0.0]:
            self.move_head(yaw=yaw, pitch=0.0)
            time.sleep(0.4)
    
    def random_walk(self, duration=10.0):
        """Walk randomly around the room"""
        print(f"🚶 Pepper is moving randomly around the room for {duration} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Random speed and direction
            speed = random.uniform(0.3, 0.8)
            direction = random.choice([-1, 1])
            walk_time = random.uniform(1.0, 3.0)
            
            self.walk(speed_x=speed * direction, duration=walk_time)
            
            # Random turn
            if random.random() > 0.5:
                turn_speed = random.uniform(0.3, 0.8)
                turn_dir = random.choice([-1, 1])
                self.turn(angular_speed=turn_speed * turn_dir, duration=random.uniform(0.5, 1.5))
            
            # Random head movement
            self.look_around()
        
        print("✅ Random walk finished")
    
    def process_command(self, command):
        """Process English commands"""
        cmd = command.lower().strip()
        
        if cmd in ['exit', 'quit', 'bye']:
            return False
        
        elif cmd in ['wave', 'hello', 'hi']:
            self.wave()
        
        elif cmd in ['walk', 'go forward', 'move forward']:
            self.walk(speed_x=0.6, duration=2.0)
        
        elif cmd in ['walk fast', 'go fast', 'run']:
            self.walk(speed_x=1.2, duration=1.5)
        
        elif cmd in ['walk slow', 'go slow']:
            self.walk(speed_x=0.3, duration=3.0)
        
        elif cmd in ['back', 'go back', 'backward']:
            self.walk(speed_x=-0.5, duration=2.0)
        
        elif cmd in ['come', 'come here']:
            self.look_around()
            self.walk(speed_x=0.7, duration=2.0)
        
        elif cmd in ['turn left', 'left']:
            self.turn(angular_speed=0.6, duration=1.0)
        
        elif cmd in ['turn right', 'right']:
            self.turn(angular_speed=-0.6, duration=1.0)
        
        elif cmd in ['look', 'look around']:
            self.look_around()
        
        elif cmd in ['nod', 'yes']:
            self.nod()
        
        elif cmd in ['random', 'explore', 'move around']:
            self.random_walk(duration=8.0)
        
        elif cmd in ['stop', 'halt']:
            twist = Twist()
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_vel_pub.publish(twist)
            print("🛑 Pepper stopped")
        
        elif cmd in ['help', 'commands']:
            self.show_help()
        
        else:
            # Natural head movement when listening
            self.move_head(yaw=0.15, pitch=0.05)
            time.sleep(0.3)
            self.move_head(yaw=-0.15, pitch=0.05)
            time.sleep(0.3)
            self.reset_head()
            print("🤖 Pepper: (Listening... moves head naturally)")
        
        return True
    
    def show_help(self):
        """Show available commands"""
        print("\n" + "="*50)
        print("🤖 AVAILABLE COMMANDS:")
        print("="*50)
        print("  • wave / hello / hi          - Wave hand")
        print("  • walk / go forward          - Walk forward")
        print("  • walk fast / run            - Walk fast")
        print("  • walk slow                  - Walk slow")
        print("  • back / go back             - Walk backward")
        print("  • come / come here           - Come forward")
        print("  • turn left / left           - Turn left")
        print("  • turn right / right         - Turn right")
        print("  • look / look around         - Look around the room")
        print("  • random / explore           - Random walk around the room")
        print("  • nod / yes                  - Nod head")
        print("  • stop                       - Stop moving")
        print("  • exit / quit                - Exit program")
        print("="*50 + "\n")
    
    def run(self):
        """Main loop"""
        print("\n" + "="*50)
        print("🤖 PEPPER IS READY!")
        print("📍 Sitting in the room with arms down")
        print("💬 Speak naturally in English")
        print("="*50)
        self.show_help()
        
        # Initial look around
        self.look_around()
        
        while True:
            try:
                command = input("\n💬 You: ").strip()
                if not command:
                    continue
                
                if not self.process_command(command):
                    print("👋 Goodbye! Pepper waves...")
                    self.wave()
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    pepper = PepperNatural()
    pepper.run()
