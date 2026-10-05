import urllib.request
import json
import time

url = 'https://msutool.com/api/rewards/world/0'
req = urllib.request.Request(url, data=b'{"layerDescs":[{"layerId":122001}]}', headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    d = json.loads(r.read().decode('utf-8'))
    print('Current API timestamp:', d.get('timestamp'))
    print('Current data.updatedAt:', d.get('data', {}).get('updatedAt'))
