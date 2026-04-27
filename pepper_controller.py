#!/usr/bin/env python3
"""
Pepper Controller Bridge
يستقبل أوامر TIE ويحولها إلى حركات Pepper عبر ROS1
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess
import time

class PepperController(Node):
    def __init__(self):
        super().__init__('pepper_controller')
        
        # اشتراك في أوامر TIE
        self.subscription = self.create_subscription(
            String,
            '/robot/therapy_action',
            self.therapy_action_callback,
            10
        )
        
        self.get_logger().info("Pepper Controller Bridge initialized")
        
    def send_pepper_command(self, cmd):
        """إرسال أمر إلى Pepper عبر Docker"""
        docker_cmd = f'docker exec pepper_live bash -c "source /opt/ros/noetic/setup.bash && {cmd}"'
        subprocess.Popen(docker_cmd, shell=True)
        
    def therapy_action_callback(self, msg):
        action = msg.data
        self.get_logger().info(f"Received TIE action: {action}")
        
        if action == "positive_reinforcement":
            # Pepper يرفع ذراعه ويقول "أحسنت!"
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/RightArm_controller/command std_msgs/Float64 "data: 1.0"')
            time.sleep(0.5)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/RightArm_controller/command std_msgs/Float64 "data: 0.0"')
            
        elif action == "attention_cue":
            # Pepper يحرك رأسه لجذب الانتباه
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/Head_controller/command std_msgs/Float64 "data: 1.0"')
            time.sleep(0.5)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/Head_controller/command std_msgs/Float64 "data: -1.0"')
            time.sleep(0.5)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/Head_controller/command std_msgs/Float64 "data: 0.0"')
            
        elif action == "instruction":
            # Pepper يرفع يده اليسرى كإشارة
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/LeftArm_controller/command std_msgs/Float64 "data: 1.2"')
            time.sleep(1.0)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/LeftArm_controller/command std_msgs/Float64 "data: 0.0"')
            
        elif action == "calming":
            # Pepper يخفض رأسه ويهدأ
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/Head_pitch_controller/command std_msgs/Float64 "data: -0.5"')
            time.sleep(2.0)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/Head_pitch_controller/command std_msgs/Float64 "data: 0.0"')
            
        elif action == "start_activity":
            # Pepper يمشي للأمام قليلاً
            self.send_pepper_command('rostopic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.3}" -r 10 & sleep 2 && rostopic pub -1 /cmd_vel geometry_msgs/Twist "linear: {x: 0.0}"')
            
        elif action == "praise":
            # Pepper يصفق (محاكاة)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/RightHand_controller/command std_msgs/Float64 "data: 0.8"')
            time.sleep(0.3)
            self.send_pepper_command('rostopic pub -1 /pepper_dcm/RightHand_controller/command std_msgs/Float64 "data: 0.0"')

def main(args=None):
    rclpy.init(args=args)
    node = PepperController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
