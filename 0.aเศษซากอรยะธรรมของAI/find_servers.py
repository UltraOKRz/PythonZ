with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\RewardsPage.js", "r", encoding="utf-8") as f:
    code = f.read()

import re

matches = re.finditer(r'getServers', code)
for m in matches:
    start = max(0, m.start() - 200)
    end = min(len(code), m.end() + 500)
    print("Match around getServers:")
    print(code[start:end])
    print("-" * 50)
