import urllib.request
import json

url = "https://msutool.com/api/rewards/world/0"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Referer": "https://msutool.com/rewards"
}

def try_payload(payload):
    print("Testing payload:", json.dumps(payload))
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("SUCCESS! Keys:", data.keys())
            if "data" in data:
                print("data keys:", data["data"].keys())
                reward_infos = data["data"].get("rewardInformations", {}).get("rewardInformations", [])
                print(f"Total rewardInformations: {len(reward_infos)}")
                for info in reward_infos[:3]:
                    print(" Item:", json.dumps(info, ensure_ascii=False)[:300])
            return True
    except Exception as e:
        print("Failed:", e)
        return False

# แบบที่ 1: layerType
print("\n--- Try 1: layerType ---")
try_payload({"layerDescs": [{"layerType": "LAYER_TYPE_FIELD"}]})

# แบบที่ 2: layerId
print("\n--- Try 2: layerId ---")
try_payload({"layerDescs": [{"layerId": 122001}]})

# แบบที่ 3: world 1 แทนที่จะเป็น world 0
print("\n--- Try 3: world 1 ---")
url = "https://msutool.com/api/rewards/world/1"
try_payload({"layerDescs": [{"layerType": "LAYER_TYPE_FIELD"}]})
