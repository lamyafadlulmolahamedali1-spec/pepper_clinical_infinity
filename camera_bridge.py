#!/usr/bin/env python3
"""
Camera Bridge from Pepper (ROS1) to ROS2
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import subprocess
import json

class CameraBridge(Node):
    def __init__(self):
        super().__init__('camera_bridge')
        
        # Publisher لـ ROS2
        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        
        # استقبال من ROS1 عبر bridge
        self.create_subscription(Image, '/pepper_robot/camera/front/image_raw', self.image_callback, 10)
        
        self.get_logger().info("Camera Bridge initialized")
        
    def image_callback(self, msg):
        # إعادة نشر الصورة لـ ROS2
        self.image_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = CameraBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
