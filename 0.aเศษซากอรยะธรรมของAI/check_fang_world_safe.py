import urllib.request
import json
import re

out_lines = []

# ดึงเซิร์ฟเวอร์
req = urllib.request.Request("https://msutool.com/api/rewards/server", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    server_info = json.loads(resp.read().decode("utf-8"))
    out_lines.append(f"Server Info: {json.dumps(server_info, ensure_ascii=False, indent=2)}")

# ลองทดสอบ world 0, 1, 2, 3, 4, 5
for w in [0, 1, 2, 3]:
    try:
        url = f"https://msutool.com/api/rewards/world/{w}"
        req_w = urllib.request.Request(url, data=b'{"layerDescs":[{"layerId":122001}]}', 
                                      headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req_w) as r:
            res_w = json.loads(r.read().decode("utf-8"))
            out_lines.append(f"World {w}: success={res_w.get('success')} data.worldId={res_w.get('data', {}).get('worldId')} updatedAt={res_w.get('data', {}).get('updatedAt')}")
    except Exception as e:
        out_lines.append(f"World {w} Error: {e}")

with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\world_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))

print("Done writing world_result.txt")
