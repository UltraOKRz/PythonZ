import urllib.request
import json
import re

# 1. ดูโค้ดใน RewardsPage.js และ shared-DoizAeRs.js เรื่อง world / servers
with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\RewardsPage.js", "r", encoding="utf-8") as f:
    text_reward = f.read()

# หาคำว่า Fang, Ain, world, servers
print("--- Searching for World / Fang / Server in RewardsPage ---")
for m in re.finditer(r'(?:Fang|Ain|worldId|server|worlds)', text_reward, re.IGNORECASE):
    s = max(0, m.start() - 100)
    e = min(len(text_reward), m.end() + 100)
    print(text_reward[s:e])
    print("-" * 40)

# ลองดึง API /rewards/server ซ้ำ
req = urllib.request.Request("https://msutool.com/api/rewards/server", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    server_info = json.loads(resp.read().decode("utf-8"))
    print("\nAPI /rewards/server:\n", json.dumps(server_info, indent=2))

# ลองทดสอบ world 0, 1, 2, 3
for w in [0, 1, 2, 3]:
    try:
        url = f"https://msutool.com/api/rewards/world/{w}"
        req_w = urllib.request.Request(url, data=b'{"layerDescs":[{"layerId":122001}]}', 
                                      headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req_w) as r:
            res_w = json.loads(r.read().decode("utf-8"))
            print(f"\nWorld {w} Response: success={res_w.get('success')} updatedAt={res_w.get('data', {}).get('updatedAt')}")
    except Exception as e:
        print(f"\nWorld {w} Error:", e)
