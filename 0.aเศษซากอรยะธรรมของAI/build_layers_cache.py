import urllib.request
import json
import os

url = "https://msutool.com/api/rewards/layers"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

static_datas = data.get("data", {}).get("staticDatas", [])
print(f"Total static layers: {len(static_datas)}")

# กรองเฉพาะ LAYER_TYPE_FIELD
fields = []
for d in static_datas:
    if d.get("layerType") == "LAYER_TYPE_FIELD":
        f_info = d.get("field", {})
        fields.append({
            "layerId": d.get("layerId"),
            "layerName": f_info.get("layerName", f"Field #{d.get('layerId')}"),
            "groupName": f_info.get("groupName", ""),
            "minLevel": f_info.get("minRecommendedLevel", 0),
            "maxLevel": f_info.get("maxRecommendedLevel", 0)
        })

print(f"Total fields: {len(fields)}")
print("Sample field 0:", fields[0])

# บันทึก cache ลงใน 1.Python Code\Cloack_Overlay\layers_cache.json
out_path = os.path.abspath(r"1.Python Code\Cloack_Overlay\layers_cache.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(fields, f, ensure_ascii=False, indent=2)

print("Saved to", out_path)
