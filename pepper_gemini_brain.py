#!/usr/bin/env python3
"""
Gemini AI Brain for Pepper - من مشروع GenieAI
- يدعم محادثات متعددة
- يتذكر السياق
- يدعم البحث
"""

import time
import json
import requests
from datetime import datetime

class GeminiBrain:
    def __init__(self, api_keys=None):
        """
        api_keys: قائمة مفاتيح Gemini API (للتوزيع)
        """
        self.api_keys = api_keys or []
        self.current_key_index = 0
        self.conversation_history = []
        self.max_history = 20
        
        # API endpoint
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        print(f"🧠 Gemini Brain initialized with {len(self.api_keys)} API keys")
    
    def _get_next_key(self):
        """Rotate API keys"""
        if not self.api_keys:
            return None
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _call_gemini(self, prompt, system_instruction=None):
        """Call Gemini API"""
        if not self.api_keys:
            return self._fallback_response(prompt)
        
        api_key = self._get_next_key()
        url = f"{self.api_url}?key={api_key}"
        
        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System instruction: {system_instruction}"}]
            })
        
        # Add conversation history
        for msg in self.conversation_history[-10:]:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["content"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 200,
                "topP": 0.95
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=15)
            if response.status_code == 200:
                result = response.json()
                reply = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Save to history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "model", "content": reply})
                
                # Trim history
                if len(self.conversation_history) > self.max_history:
                    self.conversation_history = self.conversation_history[-self.max_history:]
                
                return reply
            else:
                print(f"⚠️ Gemini API error: {response.status_code}")
                return self._fallback_response(prompt)
        except Exception as e:
            print(f"⚠️ Gemini API exception: {e}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt):
        """Fallback when API fails"""
        return f"That's interesting! Tell me more about '{prompt[:50]}' 😊"
    
    def chat(self, message, child_name="Child"):
        """Main chat method"""
        system_prompt = f"""You are Pepper, a friendly robot for a child named {child_name} with autism.

THERAPY RULES (ABA/DTT/TEACCH):
- Respond in short, simple English sentences (1-2 sentences)
- Use positive reinforcement: "Great job!", "Excellent!"
- Be patient and kind
- If the child asks "how to", explain step by step
- Use emojis to be encouraging 😊
- Keep responses positive and educational

Remember: You are talking to a child. Be gentle and encouraging."""
        
        return self._call_gemini(message, system_prompt)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        return "Conversation history cleared!"
    
    def get_history(self):
        """Get conversation history"""
        return self.conversation_history

# اختبار
if __name__ == "__main__":
    # ضعي مفاتيح Gemini API هنا
    api_keys = [
        # "AIzaSy..."  # ضعي مفتاحك هنا
    ]
    
    brain = GeminiBrain(api_keys)
    
    print("Testing Gemini Brain...")
    print(brain.chat("Hello! My name is Yusuf"))
    print(brain.chat("What is your name?"))
    print(brain.chat("How to brush my teeth?"))
