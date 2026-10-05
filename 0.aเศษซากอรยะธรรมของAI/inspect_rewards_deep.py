import urllib.request
import re
import json

base = "https://msutool.com"
url = base + "/assets/RewardsPage-Day_TeWi.js"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    code = resp.read().decode("utf-8", errors="ignore")

# หา API endpoints หรือ fetch หรือ axios
calls = re.findall(r'(?:fetch|get|post|axios|api)\s*\(.*?\)', code)
apis = re.findall(r'https?://[a-zA-Z0-9_\-\.\:/]+', code)
paths = re.findall(r'[\'\"`](/(?:api|v[0-9]|reward|pool|layer|field)[^\'\"`]+)[\'\"`]', code)

# หา function / hooks เช่น useQuery, useReward, getPool, getField
queries = re.findall(r'(?:useQuery|queryKey|mutation|queryFn)[^;{}]+', code)

with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\reward_analysis.txt", "w", encoding="utf-8") as f:
    f.write(f"=== URLS ===\n" + "\n".join(set(apis)) + "\n\n")
    f.write(f"=== PATHS ===\n" + "\n".join(set(paths)) + "\n\n")
    f.write(f"=== CALLS ===\n" + "\n".join(calls[:30]) + "\n\n")
    f.write(f"=== QUERIES ===\n" + "\n".join(queries[:30]) + "\n\n")
    f.write(f"=== CODE SNIPPET (First 5000 chars) ===\n" + code[:5000] + "\n")

print("Analysis written to reward_analysis.txt")
