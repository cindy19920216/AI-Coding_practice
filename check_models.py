# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

src = open(r'C:\Users\Check\Desktop\AI 금융_FINAL\improve_sentiment.py', encoding='utf-8').read()
m = re.search(r"_KEY_LITERAL\s*=\s*'([^']+)'", src)
api_key = m.group(1) if m else ''

from google import genai
client = genai.Client(api_key=api_key)

print("사용 가능한 모델 (generateContent 지원):")
for model in client.models.list():
    if 'generateContent' in str(getattr(model, 'supported_actions', '')):
        print(f"  {model.name}")
