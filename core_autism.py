#!/usr/bin/env python3

import json
import time
import random
from datetime import datetime
import os

class PepperAutismCore:
    def __init__(self):
        self.child = {
            'id': 'CHILD001',
            'name': 'طفل',
            'age': 8,
            'level': 1
        }
        self.session = {
            'start': None,
            'end': None,
            'reinforcements': 0,
            'activities': []
        }
        print("🧩 Pepper Autism Core Initialized")
    
    def start_session(self):
        self.session['start'] = datetime.now()
        print("\n" + "="*60)
        print(f"🎯 بدء جلسة لـ {self.child['name']}")
        print("="*60)
        return True
    
    def welcome_activity(self):
        print("\n👋 نشاط الترحيب")
        print("🤖: مرحباً! كيف حالك اليوم؟")
        time.sleep(1)
        
        # Visual schedule (TEACCH)
        print("\n📅 جدول اليوم:")
        schedule = [
            "😊 التعرف على المشاعر",
            "🧠 لعبة الذاكرة",
            "🧘 استراحة حسية",
            "🗣️ محادثة"
        ]
        for i, act in enumerate(schedule, 1):
            print(f"   {i}. {act}")
        
        self.session['activities'].append('welcome')
        return True
    
    def emotion_recognition(self):
        print("\n😊 نشاط التعرف على المشاعر")
        emotions = [
            ("😊 سعيد", "ابتسامة"),
            ("😢 حزين", "دموع"),
            ("😠 غاضب", "عبوس"),
            ("😐 محايد", "طبيعي")
        ]
        
        for emotion, desc in emotions[:2]:
            print(f"\n🤖: كيف تبدو هذه المشاعر؟ {emotion}")
            print(f"📝: {desc}")
            time.sleep(1)
            
            # Positive reinforcement (ABA)
            if random.random() > 0.3:
                print("⭐ أحسنت! إجابة صحيحة")
                self.session['reinforcements'] += 1
            else:
                print("🔄 دعنا نحاول مرة أخرى")
        
        self.session['activities'].append('emotion')
        return True
    
    def memory_game(self):
        print("\n🧠 لعبة الذاكرة")
        print("📱: 8 بطاقات على الشاشة")
        
        pairs = 0
        attempts = 0
        
        while pairs < 3:  # 3 pairs to win
            attempts += 1
            print(f"\n🔄 محاولة {attempts}")
            time.sleep(0.5)
            
            if random.random() > 0.4:  # 60% success rate
                pairs += 1
                print(f"✅ وجدت زوج! ({pairs}/3)")
                print("⭐ تعزيز!")
                self.session['reinforcements'] += 1
            else:
                print("❌ ليس متطابقاً، حاول مرة أخرى")
        
        print(f"\n🎉 أكملت اللعبة في {attempts} محاولة!")
        self.session['activities'].append('memory_game')
        return True
    
    def sensory_break(self):
        print("\n🧘 استراحة حسية")
        
        # Calming activities
        print("\n🌊 تمرين التنفس:")
        for i in range(3):
            print(f"   {i+1}. شهيق... (3 ثوان)")
            time.sleep(0.5)
            print(f"      زفير... (3 ثوان)")
            time.sleep(0.5)
        
        print("\n🎵 تشغيل موسيقى هادئة")
        print("🖼️ عرض صور مريحة على التابلت")
        
        self.session['activities'].append('sensory_break')
        return True
    
    def communication_activity(self):
        print("\n🗣️ نشاط التواصل")
        
        questions = [
            "ماذا فعلت اليوم في المدرسة؟",
            "ما هو طعامك المفضل؟",
            "ما هي لعبتك المفضلة؟",
            "كيف تشعر الآن؟"
        ]
        
        for q in questions[:2]:
            print(f"\n🤖: {q}")
            print("👤: [استجابة الطفل]")
            time.sleep(1)
            
            if random.random() > 0.2:
                print("⭐ تعزيز التواصل")
                self.session['reinforcements'] += 1
        
        self.session['activities'].append('communication')
        return True
    
    def goodbye_activity(self):
        self.session['end'] = datetime.now()
        duration = (self.session['end'] - self.session['start']).seconds
        
        print("\n" + "="*60)
        print("👋 وداعاً!")
        print("="*60)
        print(f"\n📊 ملخص الجلسة:")
        print(f"   ⏱️ المدة: {duration} ثانية")
        print(f"   ⭐ التعزيزات: {self.session['reinforcements']}")
        print(f"   📈 الأنشطة: {len(self.session['activities'])}")
        
        self.session['activities'].append('goodbye')
        return True
    
    def run_full_session(self):
        """Run complete therapy session"""
        self.start_session()
        self.welcome_activity()
        self.emotion_recognition()
        self.memory_game()
        self.sensory_break()
        self.communication_activity()
        self.goodbye_activity()
        
        # Generate report
        report = {
            'child': self.child['name'],
            'date': datetime.now().isoformat(),
            'duration': (self.session['end'] - self.session['start']).seconds,
            'reinforcements': self.session['reinforcements'],
            'activities': self.session['activities']
        }
        
        print("\n✅ انتهت الجلسة بنجاح")
        return report

if __name__ == "__main__":
    print("🧩 Pepper Autism Support Platform")
    print("Based on TEACCH + ABA + TIE")
    
    pepper = PepperAutismCore()
    report = pepper.run_full_session()
