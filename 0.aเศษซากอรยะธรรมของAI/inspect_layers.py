import json

with open(r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\layers_cache.json', 'r', encoding='utf-8') as f:
    layers = json.load(f)

print(f"Total layers: {len(layers)}")
for l in layers:
    print(f"{l['layerId']}: {l['layerName']} ({l.get('groupName', '')})")
