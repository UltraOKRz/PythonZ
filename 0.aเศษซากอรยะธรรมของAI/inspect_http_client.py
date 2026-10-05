import urllib.request
import re

base = "https://msutool.com"
url = base + "/assets/http-client-_dUyW1sf.js"

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    code = resp.read().decode("utf-8", errors="ignore")

# หา baseURL หรือ axios.create หรือ host
with open(r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\0.aเศษซากอรยะธรรมของAI\http_client_code.txt", "w", encoding="utf-8") as f:
    f.write(code)

matches = re.findall(r'(baseURL|baseUrl|BASE_URL|create\(\{.*?baseURL.*?\})', code)
print("Matches:", matches)

# หา api URLs
urls = re.findall(r'https?://[a-zA-Z0-9_\-\.\:/]+', code)
print("URLs in client:")
for u in set(urls):
    print(u)
