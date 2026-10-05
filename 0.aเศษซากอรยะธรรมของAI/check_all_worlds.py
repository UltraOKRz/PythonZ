import urllib.request
import json

base = "https://msutool.com"

# ทดสอบ worldId 0, 1, 2, 3 ...
for w in range(5):
    url = f"{base}/api/rewards/world/{w}"
    try:
        req = urllib.request.Request(url, data=b'{"layerDescs":[{"layerId":122001}]}', 
                                      headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"World {w}: success={data.get('success')}, worldId={data.get('data', {}).get('worldId')}")
    except Exception as e:
        print(f"World {w} error: {e}")
