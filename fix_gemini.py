#!/usr/bin/env python3
"""Fix Gemini model name in autism_therapy_platform.py"""
import google.generativeai as genai
import re

genai.configure(api_key='AIzaSyDEdleVKiQ5E00wMcjMbji0G9JcYT2TvE8')

# Find working model
working_model = None
test_models = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite", 
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.5-pro-latest",
    "gemini-1.5-pro",
    "gemini-pro",
]

print("Testing Gemini models...")
for mn in test_models:
    try:
        m = genai.GenerativeModel(
            mn,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=50,
            )
        )
        r = m.generate_content("Say: READY")
        print(f"✅ WORKS: {mn} → {r.text[:30]}")
        working_model = mn
        break
    except Exception as e:
        print(f"❌ {mn}: {str(e)[:60]}")

if working_model:
    print(f"\n✅ Best model: {working_model}")
    # Patch the platform file
    try:
        with open('autism_therapy_platform.py', 'r') as f:
            content = f.read()
        # Replace MODELS list
        old = '''    MODELS = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
        "gemini-pro",
    ]'''
        new = f'''    MODELS = [
        "{working_model}",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-pro",
    ]'''
        if old in content:
            content = content.replace(old, new)
            with open('autism_therapy_platform.py', 'w') as f:
                f.write(content)
            print("✅ Platform patched with working model!")
        else:
            print("⚠️  Could not find MODELS list - manual fix needed")
            print(f"Add '{working_model}' as first model in MODELS list")
    except Exception as e:
        print(f"⚠️  Patch error: {e}")
else:
    print("\n❌ No working Gemini model found!")
    print("Check API key or internet connection")
