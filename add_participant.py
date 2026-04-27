import csv
import os

file_path = os.path.expanduser("~/pepper_duo/src/Participants_Database.csv")

# استقبال البيانات من الترمينال
print("--- Pepper V6: إضافة مشارك جديد يدوياً ---")
parent = input("اسم ولي الأمر: ")
child = input("اسم الطفل: ")
age = input("عمر الطفل: ")
diagnosis = input("التشخيص: ")
skills = input("المهارات المستهدفة: ")
contact = input("وسيلة التواصل: ")

# حفظ البيانات
file_exists = os.path.isfile(file_path)
with open(file_path, 'a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["Parent", "Child", "Age", "Diagnosis", "Skills", "Contact"])
    writer.writerow([parent, child, age, diagnosis, skills, contact])

print(f"✅ تم حفظ بيانات {child} بنجاح في قاعدة البيانات!")
