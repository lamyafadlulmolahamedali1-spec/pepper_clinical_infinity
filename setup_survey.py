import csv
import os

# تعريف الأسئلة والبيانات المطلوبة للاستبيان
survey_data = [
    ["Pepper Clinical Infinity V6 - Participation Form"],
    ["-----------------------------------------------"],
    ["اسم ولي الأمر (Parent Name):"],
    ["اسم الطفل (Child Name):"],
    ["عمر الطفل (Child Age):"],
    ["التشخيص (Diagnosis):"],
    ["المهارات المستهدفة (Target Skills):"],
    ["وسيلة التواصل (Contact Info - WhatsApp/Telegram):"],
    ["ملاحظات إضافية (Notes):"]
]

file_path = os.path.expanduser("~/pepper_duo/src/Pepper_V6_Survey_Template.csv")

with open(file_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in survey_data:
        writer.writerow(row)

print(f"✅ تم إنشاء ملف الاستبيان بنجاح في: {file_path}")
print("يمكنك الآن طباعة الملف أو إرساله للأهالي كنموذج.")
