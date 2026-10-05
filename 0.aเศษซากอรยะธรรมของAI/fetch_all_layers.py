import urllib.request
import json
import os

key = 'gw_91a3dc4dfa157a8971e67fb7e38d3add0fdd3f4dfc0caf21ac82fc29c650efee85c7920c8a113a09b7a4a670ba466fe9'
url = 'https://openapi.msu.io/v1rc1/msn/layers/static'

req = urllib.request.Request(
    url,
    data=json.dumps({'layerDescs': [{'layerType': 'LAYER_TYPE_FIELD'}]}).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-nxopen-api-key': key},
    method='POST'
)

with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))

static_datas = data.get('data', {}).get('staticDatas', [])
layers = []
for d in static_datas:
    f = d.get('field', {})
    layers.append({
        'layerId': d.get('layerId'),
        'layerName': f.get('layerName'),
        'groupName': f.get('groupName'),
        'minLevel': f.get('minRecommendedLevel'),
        'maxLevel': f.get('maxRecommendedLevel')
    })

target_cache = r'1.Python Code\Cloack_Overlay\layers_cache.json'
with open(target_cache, 'w', encoding='utf-8') as f:
    json.dump(layers, f, ensure_ascii=False, indent=2)

print(f'Total layers saved: {len(layers)}')
for l in sorted(layers, key=lambda x: x['layerId']):
    print(f"{l['layerId']}: {l['layerName']} ({l['groupName']})")
