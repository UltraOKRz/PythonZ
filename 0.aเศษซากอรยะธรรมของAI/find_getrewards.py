with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\reward_analysis.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re

# อ่านโค้ดเต็มของ RewardsPage
with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\RewardsPage.js", "w", encoding="utf-8") as f_out:
    import urllib.request
    req = urllib.request.Request("https://msutool.com/assets/RewardsPage-Day_TeWi.js", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        code = resp.read().decode("utf-8", errors="ignore")
        f_out.write(code)

matches = re.finditer(r'getRewards\s*\(', code)
for m in matches:
    start = max(0, m.start() - 200)
    end = min(len(code), m.end() + 500)
    print("Match around getRewards:")
    print(code[start:end])
    print("-" * 50)
