import urllib.request
import json

url = "https://msutool.com/api/rewards/world/0"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/json"
}
payload = {"layerDescs": [{"layerId": 122001}]}
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print(json.dumps(data, ensure_ascii=False, indent=2))
