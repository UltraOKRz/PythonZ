import urllib.request
import json
import time

url = 'https://msutool.com/api/rewards/world/0'
req = urllib.request.Request(url, data=b'{"layerDescs":[{"layerId":122001}]}', headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})

print("Monitoring updatedAt changes for 60 seconds...")
last_updated = None
for i in range(6):
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read().decode('utf-8'))
            cur_up = d.get('data', {}).get('updatedAt')
            ts = d.get('timestamp')
            print(f"[{i*10}s] Server Time: {ts} | Data updatedAt: {cur_up}")
    except Exception as e:
        print("Err:", e)
    time.sleep(10)
