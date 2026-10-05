import urllib.request

base = "https://msutool.com"
url = base + "/assets/rewards.service-DI3GOZqE.js"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    code = resp.read().decode("utf-8", errors="ignore")

with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\rewards_service_code.js", "w", encoding="utf-8") as f:
    f.write(code)

print(f"Downloaded rewards.service (len={len(code)})")
