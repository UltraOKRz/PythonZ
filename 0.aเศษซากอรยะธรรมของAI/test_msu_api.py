import urllib.request
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://msutool.com/rewards?tab=pool&world=0&layerId=122001&layer=LAYER_TYPE_FIELD"
}

def test_endpoint(name, url, method="GET", data=None):
    print(f"\n--- Testing {name}: {url} ---")
    try:
        body = json.dumps(data).encode("utf-8") if data else None
        h = dict(headers)
        if body:
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            data_res = json.loads(raw)
            print("Status: 200 OK")
            print("Response preview:", json.dumps(data_res, ensure_ascii=False, indent=2)[:1000])
            return data_res
    except Exception as e:
        print("Error:", e)
        return None

# 1. /rewards/server
test_endpoint("Server Info", "https://msutool.com/api/rewards/server")

# 2. /rewards/layers
layers_data = test_endpoint("Layers Static", "https://msutool.com/api/rewards/layers")

# 3. /rewards/world/0
# เช็ค layer 122001 (LAYER_TYPE_FIELD)
payload = {
    "layerDescs": [
        {"layerId": 122001, "layerType": "LAYER_TYPE_FIELD"}
    ]
}
reward_res = test_endpoint("Get Rewards for 122001", "https://msutool.com/api/rewards/world/0", method="POST", data=payload)
