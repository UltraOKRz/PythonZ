import json

with open("layers_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

# เรียงตาม minLevel จากน้อยไปมาก ถ้าเท่ากันให้เรียงตาม layerId
sorted_cache = sorted(cache, key=lambda x: (x.get("minLevel", 0), x.get("maxLevel", 0), x.get("layerId", 0)))

with open("layers_cache.json", "w", encoding="utf-8") as f:
    json.dump(sorted_cache, f, ensure_ascii=False, indent=2)

print(f"Successfully sorted {len(sorted_cache)} layers in layers_cache.json!")
