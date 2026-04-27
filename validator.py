def validate_movement(joint_data, task_type):
    """
    تحقق صارم: لا نجاح إلا بحركة حقيقية!
    """
    if not joint_data:
        return False
    
    # مثال لحركة التصفيق: يجب أن تكون اليدين قريبتين جداً وبسرعة معينة
    if task_type == 'clap':
        dist = joint_data.get('hands_distance', 1.0)
        # إذا كانت المسافة كبيرة، لا تعتبرها تصفيقاً مهما حدث
        if dist < 0.15: 
            return True
            
    # مثال لرفع اليدين: يجب أن يتجاوز الكوع مستوى الكتف فعلياً
    if task_type == 'raise_hands':
        y_elbow = joint_data.get('elbow_y', 1.0)
        y_shoulder = joint_data.get('shoulder_y', 0.0)
        if y_elbow < y_shoulder: # في OpenCV الـ Y تقل كلما ارتفعنا
            return True
            
    return False
