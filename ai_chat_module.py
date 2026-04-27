#!/usr/bin/env python3
"""
Advanced AI Chat for Pepper
- يتناقش في أي موضوع
- متخصص في ASD therapy
- يتذكر سياق المحادثة
- يرد بالعربي أو الإنجليزي
"""

import requests
import json
import time

CHAT_API = "https://text.pollinations.ai/v1/chat/completions"

SYSTEM_PROMPT = """You are Pepper, an AI-powered therapy robot assistant specialized in:
1. Autism Spectrum Disorder (ASD) therapy - ABA, TEACCH, DTT, Joint Attention
2. Child development and behavior
3. Parent guidance and support
4. General conversation and education

Rules:
- Keep responses SHORT (1-3 sentences max)
- Be warm, encouraging, and child-friendly
- If asked about ASD therapy, give specific evidence-based advice
- If talking TO a child: use simple words, be playful
- If talking TO a parent: be professional and supportive
- Detect language (Arabic/English) and respond in SAME language
- Never say you are an AI - you are Pepper the robot!

ASD Knowledge:
- ABA: Discrete Trial Training, reinforcement, prompting
- TEACCH: Visual schedules, structured environment
- Joint Attention: Following gaze, pointing, shared focus
- Emotion Recognition: Facial expressions, emotion cards
- Meltdown protocol: Reduce stimulation, calm voice, space"""

class AIChatModule:
    def __init__(self):
        self.conversation_history = []
        self.max_history = 10
        self.last_request_time = 0
        self.min_interval = 1.5  # ثواني بين كل طلب
        print("✅ AI Chat Module ready!")

    def chat(self, user_message, context=None):
        """
        المحادثة الرئيسية
        context: معلومات إضافية (اسم الطفل، severity، إلخ)
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        # بناء الرسائل
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # إضافة context إن وجد
        if context:
            ctx_msg = f"Current context: {json.dumps(context)}"
            messages.append({"role": "system", "content": ctx_msg})

        # إضافة تاريخ المحادثة
        messages.extend(self.conversation_history[-self.max_history:])

        # الرسالة الجديدة
        messages.append({"role": "user", "content": user_message})

        try:
            response = requests.post(
                CHAT_API,
                json={
                    "model": "openai",
                    "messages": messages,
                    "max_tokens": 150
                },
                timeout=12
            )
            self.last_request_time = time.time()

            if response.status_code == 200:
                reply = response.json()["choices"][0]["message"]["content"].strip()
                # حفظ في التاريخ
                self.conversation_history.append({"role": "user",      "content": user_message})
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
            else:
                return self._fallback(user_message)

        except Exception as e:
            print(f"[AI] Error: {e}")
            return self._fallback(user_message)

    def chat_with_child(self, child_name, child_message, severity="moderate"):
        """Pepper تتحدث مع طفل محدد"""
        context = {
            "talking_to": "child",
            "child_name": child_name,
            "severity": severity,
            "mode": "therapy_interaction"
        }
        prompt = f"{child_name} says: '{child_message}'"
        return self.chat(prompt, context)

    def chat_with_parent(self, parent_message, child_info=None):
        """Pepper تتحدث مع ولي أمر"""
        context = {
            "talking_to": "parent",
            "child_info": child_info or {},
            "mode": "parent_guidance"
        }
        return self.chat(parent_message, context)

    def generate_therapy_prompt(self, child_name, activity, severity):
        """توليد جملة علاجية مناسبة"""
        context = {
            "generate": "therapy_instruction",
            "child_name": child_name,
            "activity": activity,
            "severity": severity
        }
        prompt = f"Generate ONE short therapy instruction for {activity} with {child_name} (severity: {severity})"
        return self.chat(prompt, context)

    def explain_behavior(self, behavior, severity):
        """شرح سلوك الطفل للوالدين"""
        prompt = f"Briefly explain why a child with {severity} ASD shows '{behavior}' behavior and one tip to handle it"
        return self.chat(prompt, {"mode": "parent_education"})

    def _fallback(self, message):
        """ردود احتياطية بدون API"""
        fallbacks = [
            "That's interesting! Tell me more!",
            "Great question! Let me help you with that.",
            "I understand. Let's work on this together!",
            "You're doing amazing! Keep going!",
            "Let me think about that... Every child is unique!"
        ]
        import random
        return random.choice(fallbacks)

    def clear_history(self):
        self.conversation_history = []
        print("[AI] Conversation history cleared")

    def get_summary(self):
        """ملخص المحادثة"""
        if not self.conversation_history:
            return "No conversation yet."
        prompt = "Summarize this therapy session in 2 sentences"
        return self.chat(prompt)


# ===== اختبار مستقل =====
if __name__ == "__main__":
    ai = AIChatModule()
    print("\n🤖 AI Chat Test Mode")
    print("Commands: 'child [name]', 'parent', 'behavior [name]', 'clear', 'exit'\n")

    while True:
        try:
            user = input("You: ").strip()
            if not user:
                continue
            if user == "exit":
                break
            elif user == "clear":
                ai.clear_history()
            elif user.startswith("child "):
                name = user.split()[1]
                msg  = " ".join(user.split()[2:]) or "hello"
                print(f"Pepper: {ai.chat_with_child(name, msg)}")
            elif user == "parent":
                msg = input("Parent message: ")
                print(f"Pepper: {ai.chat_with_parent(msg)}")
            elif user.startswith("behavior "):
                b = user.replace("behavior ", "")
                print(f"Pepper: {ai.explain_behavior(b, 'moderate')}")
            else:
                print(f"Pepper: {ai.chat(user)}")
        except KeyboardInterrupt:
            break
