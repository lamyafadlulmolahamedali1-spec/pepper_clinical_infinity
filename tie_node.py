#!/usr/bin/env python3

import rospy
from std_msgs.msg import String

class TIENode:
    def __init__(self):
        rospy.init_node('tie_node', anonymous=True)
        
        rospy.Subscriber('/child/emotion', String, self.emotion_callback)
        rospy.Subscriber('/child/objects', String, self.objects_callback)
        rospy.Subscriber('/child/face_detected', String, self.face_callback)
        
        self.robot_cmd_pub = rospy.Publisher('/robot/command', String, queue_size=10)
        
        self.current_emotion = None
        self.current_objects = []
        self.face_present = False
        self.last_command = None
        
        self.timer = rospy.Timer(rospy.Duration(3), self.timer_callback)
        
        rospy.loginfo("🧠 TIE Node جاهز للعمل")
    
    def emotion_callback(self, msg):
        self.current_emotion = msg.data
        rospy.loginfo(f"🎭 المشاعر المستلمة: {self.current_emotion}")
        self.decide_action()
    
    def objects_callback(self, msg):
        if msg.data:
            self.current_objects = msg.data.split(',')
            rospy.loginfo(f"📋 الأشياء المستلمة: {self.current_objects}")
            self.decide_action()
    
    def face_callback(self, msg):
        self.face_present = (msg.data == "yes")
        rospy.loginfo(f"👤 وجه موجود: {self.face_present}")
    
    def timer_callback(self, event):
        self.decide_action()
    
    def decide_action(self):
        command = "idle"
        
        if self.face_present:
            if self.current_emotion:
                if self.current_emotion in ['sad', 'fear', 'angry']:
                    command = "comfort"
                    rospy.loginfo("🎯 الطفل يحتاج تهدئة")
                elif self.current_emotion in ['happy', 'surprise']:
                    command = "celebrate"
                    rospy.loginfo("🎯 الطفل سعيد -> تشجيع")
                else:
                    command = "greet"
                    rospy.loginfo("🎯 تفاعل عادي")
            
            if self.current_objects:
                if 'ball' in self.current_objects:
                    command = "play_ball"
                    rospy.loginfo("🎯 يوجد كرة -> العب مع الطفل")
                elif 'book' in self.current_objects:
                    command = "read_book"
                    rospy.loginfo("🎯 يوجد كتاب -> اقرأ مع الطفل")
        else:
            command = "search"
            rospy.loginfo("🔍 لا يوجد طفل -> ابحث عن طفل")
        
        if command != self.last_command:
            self.last_command = command
            rospy.loginfo(f"🤖 إرسال الأمر: {command}")
            self.robot_cmd_pub.publish(String(command))

if __name__ == '__main__':
    try:
        node = TIENode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
