import urllib.request
import json
import time

url = "https://msutool.com/api/rewards/world/0"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}
payload = {"layerDescs": [{"layerId": 122001}]}

def check():
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        # ดู headers ด้วย
        resp_headers = dict(resp.headers)
        data = json.loads(resp.read().decode("utf-8"))
        return resp_headers, data

h, d = check()
print("Response Cache / CDN Headers:")
for k, v in h.items():
    if any(x in k.lower() for x in ["cache", "age", "date", "expires", "cf-"]):
        print(f"  {k}: {v}")

print("\nPayload meta:")
print("  timestamp:", d.get("timestamp"))
print("  updatedAt:", d.get("data", {}).get("updatedAt"))
r_infos = d.get("data", {}).get("rewardInformations", {}).get("rewardInformations", [])
if r_infos:
    f_info = r_infos[0].get("fieldInformation", {})
    print("  nextChargeAt:", f_info.get("nextChargeAt"))
    for itm in f_info.get("items", []):
        if itm.get("key", {}).get("itemId") == 1 and itm.get("enableBoostOption"):
            print("  Boost NESO currentStock:", itm.get("currentStock", {}).get("value"))
            print("  Boost NESO dropProb:", itm.get("dropProb", {}).get("value"))
