with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\http_client_code.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re

# หาตำแหน่งประกาศ pn =
matches = re.findall(r'(?:const|let|var)\s+pn\s*=\s*[^;]+;', text)
print("pn definitions:", matches)

# หรือค้นหาคำว่า pn = ในบริเวณก่อนหน้า
idx = text.find("publicGet")
if idx != -1:
    snippet = text[max(0, idx-3000):idx]
    pn_matches = re.findall(r'[a-zA-Z0-9_$]+\s*=\s*["\'`][^"\'`]*["\'`]', snippet)
    print("Recent string assignments before publicGet:")
    for p in pn_matches[-20:]:
        print(" ", p)
