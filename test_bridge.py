from robot_bridge import RobotBridge

# إنشاء نسخة من الجسر
robot = RobotBridge()

# اختبار الدوال
robot.say("مرحباً، أنا جاهز للعمل")
robot.show_tablet("http://your-server/image.jpg")
robot.move_joint("RShoulderPitch", 0.5)
