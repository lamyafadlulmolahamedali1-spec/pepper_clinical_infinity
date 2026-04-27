#!/usr/bin/env python3

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import JointState
import time

class NaoControllerNode:
    def __init__(self):
        rospy.init_node('nao_controller_node', anonymous=True)
        
        rospy.Subscriber('/robot/command', String, self.command_callback)
        
        self.status_pub = rospy.Publisher('/robot/status', String, queue_size=10)
        self.joint_pub = rospy.Publisher('/joint_states', JointState, queue_size=10)
        
        rospy.loginfo("🦾 NAO Controller Node جاهز للعمل")
        
        self.current_action = None
        self.action_start_time = None
        
    def command_callback(self, msg):
        command = msg.data
        rospy.loginfo(f"📨 أمر مستلم من TIE: {command}")
        
        self.current_action = command
        self.action_start_time = time.time()
        
        if command == "greet":
            self.greet()
        elif command == "comfort":
            self.comfort()
        elif command == "celebrate":
            self.celebrate()
        elif command == "play_ball":
            self.play_ball()
        elif command == "read_book":
            self.read_book()
        elif command == "search":
            self.search()
        elif command == "idle":
            self.idle()
        else:
            rospy.logwarn(f"⚠️ أمر غير معروف: {command}")
    
    def send_joint_states(self, head_yaw=0.0, head_pitch=0.0, 
                          left_arm=[0.0]*4, right_arm=[0.0]*4):
        joint_state = JointState()
        joint_state.header.stamp = rospy.Time.now()
        joint_state.name = [
            'HeadYaw', 'HeadPitch',
            'LShoulderPitch', 'LShoulderRoll', 'LElbowYaw', 'LElbowRoll',
            'RShoulderPitch', 'RShoulderRoll', 'RElbowYaw', 'RElbowRoll'
        ]
        joint_state.position = [
            head_yaw, head_pitch,
            left_arm[0], left_arm[1], left_arm[2], left_arm[3],
            right_arm[0], right_arm[1], right_arm[2], right_arm[3]
        ]
        self.joint_pub.publish(joint_state)
    
    def greet(self):
        rospy.loginfo("👋 الروبوت يحيي الطفل")
        self.status_pub.publish(String("greeting"))
        
        for i in range(3):
            self.send_joint_states(
                head_yaw=0.5,
                left_arm=[0.5, 0.1, -0.5, 0.3],
                right_arm=[0.5, -0.1, 0.5, -0.3]
            )
            time.sleep(0.5)
            self.send_joint_states(
                head_yaw=-0.5,
                left_arm=[0.3, 0.0, -0.3, 0.1],
                right_arm=[0.3, 0.0, 0.3, -0.1]
            )
            time.sleep(0.5)
    
    def comfort(self):
        rospy.loginfo("🤗 الروبوت يحاول تهدئة الطفل")
        self.status_pub.publish(String("comforting"))
        
        for i in range(2):
            self.send_joint_states(head_pitch=0.2)
            time.sleep(1)
            self.send_joint_states(head_pitch=-0.1)
            time.sleep(1)
    
    def celebrate(self):
        rospy.loginfo("🎉 الروبوت يحتفل")
        self.status_pub.publish(String("celebrating"))
        
        for i in range(3):
            self.send_joint_states(
                left_arm=[1.0, 0.2, -0.8, 0.5],
                right_arm=[1.0, -0.2, 0.8, -0.5]
            )
            time.sleep(0.3)
            self.send_joint_states(
                left_arm=[0.0, 0.0, 0.0, 0.0],
                right_arm=[0.0, 0.0, 0.0, 0.0]
            )
            time.sleep(0.3)
    
    def play_ball(self):
        rospy.loginfo("⚽ الروبوت يلعب بالكرة")
        self.status_pub.publish(String("playing_ball"))
        
        self.send_joint_states(head_yaw=0.3, head_pitch=-0.2)
        time.sleep(1)
        self.send_joint_states(head_yaw=-0.3, head_pitch=-0.2)
        time.sleep(1)
    
    def read_book(self):
        rospy.loginfo("📚 الروبوت يقرأ كتاب")
        self.status_pub.publish(String("reading"))
        
        self.send_joint_states(head_pitch=-0.5)
        time.sleep(2)
    
    def search(self):
        rospy.loginfo("🔍 الروبوت يبحث عن طفل")
        self.status_pub.publish(String("searching"))
        
        for i in range(4):
            self.send_joint_states(head_yaw=0.8)
            time.sleep(0.5)
            self.send_joint_states(head_yaw=-0.8)
            time.sleep(0.5)
    
    def idle(self):
        self.send_joint_states()
        self.status_pub.publish(String("idle"))

if __name__ == '__main__':
    try:
        node = NaoControllerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
