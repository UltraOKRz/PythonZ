with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\http_client_code.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re

idx = text.find("publicGet")
if idx != -1:
    start = max(0, idx - 500)
    end = min(len(text), idx + 1000)
    print("Found publicGet:")
    print(text[start:end])
else:
    print("publicGet not found in file directly, searching for class or object...")
    for m in re.finditer(r'class\s+([A-Za-z0-9_]+)', text):
        print("Class:", m.group(0))
