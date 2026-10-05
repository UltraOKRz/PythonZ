import json

with open(r"1.Python Code\Cloack_Overlay\layers_cache.json", "r", encoding="utf-8") as f:
    layers = json.load(f)

print(f"Total layers: {len(layers)}")
for idx, item in enumerate(layers):
    print(f"{idx+1}. ID: {item.get('layerId')} | Name: {item.get('layerName')} | Group: {item.get('groupName')}")
