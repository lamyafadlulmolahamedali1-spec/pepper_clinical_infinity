#!/usr/bin/env python3

import random
import json
from datetime import datetime, timedelta

print("\n📊 PEPPER AUTISM ANALYTICS DASHBOARD")
print("="*60)

# Generate sample data
sessions = []
for i in range(10):
    date = datetime.now() - timedelta(days=i)
    sessions.append({
        'date': date.strftime('%Y-%m-%d'),
        'reinforcements': random.randint(8, 20),
        'attention': round(random.uniform(0.65, 0.95), 2),
        'activities': random.randint(4, 7)
    })

print(f"\n📈 تحليل {len(sessions)} جلسات:")
print("-"*60)

# Calculate stats
total_reinf = sum(s['reinforcements'] for s in sessions)
avg_reinf = total_reinf / len(sessions)
avg_attention = sum(s['attention'] for s in sessions) / len(sessions)

print(f"📊 إحصائيات عامة:")
print(f"   إجمالي التعزيزات: {total_reinf}")
print(f"   متوسط التعزيزات: {avg_reinf:.1f} لكل جلسة")
print(f"   متوسط الانتباه: {avg_attention:.2f}")

print(f"\n📅 تطور الأداء:")
for i, s in enumerate(sessions[:5], 1):
    print(f"   جلسة {i}: {s['date']} - تعزيزات: {s['reinforcements']}, انتباه: {s['attention']}")

print(f"\n💡 توصيات:")
if avg_attention < 0.7:
    print("   • زيادة فترات الراحة الحسية")
if avg_reinf < 12:
    print("   • تكثيف التعزيز الإيجابي")
if len(sessions) < 8:
    print("   • زيادة عدد الجلسات الأسبوعية")
else:
    print("   • الاستمرار على البرنامج الحالي")

print("\n✅ تقرير جاهز")
