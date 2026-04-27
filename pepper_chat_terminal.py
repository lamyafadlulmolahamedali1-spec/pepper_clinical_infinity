#!/usr/bin/env python3
"""
Pepper Chat Terminal - Separate window for typing
"""

import time
import threading
import sys

print("\n" + "="*55)
print("🤖 PEPPER CHAT - Type your messages here")
print("="*55)
print("📝 Type 'exit' to quit")
print("="*55)

while True:
    try:
        user_input = input("\n👶 You: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("🤖 Pepper: Goodbye! 👋")
            break
        
        if user_input:
            print(f"🤖 Pepper: I heard you say: '{user_input}'")
            print("   (This is a test - full AI will respond)")
            
    except KeyboardInterrupt:
        print("\n🤖 Pepper: Goodbye! 👋")
        break
