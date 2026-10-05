import json
import sys

# บันทึกสรุปลงไฟล์ markdown ใน graveyard
with open(r'1.Python Code\Cloack_Overlay\layers_cache.json', 'r', encoding='utf-8') as f:
    layers = json.load(f)

# โหลด aliases จาก Cloack_Overlay.pyw
import re
overlay_src = open(r'1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw', 'r', encoding='utf-8').read()
alias_block = re.search(r'GLOBAL_MAP_ALIASES\s*=\s*\[(.*?)\]\s*\n\s*# Step', overlay_src, re.DOTALL)

alias_map = {}
if alias_block:
    matches = re.findall(r'\((\d+),\s*\[(.*?)\]\)', alias_block.group(1), re.DOTALL)
    for lid_str, kws_str in matches:
        lid = int(lid_str)
        kws = [k.strip().strip("'\"") for k in kws_str.split(',') if k.strip().strip("'\"")]
        alias_map[lid] = kws

groups = {}
for l in sorted(layers, key=lambda x: x['layerId']):
    grp = l.get('groupName', 'Other')
    if grp not in groups:
        groups[grp] = []
    groups[grp].append(l)

out_lines = []
out_lines.append("# รายงานโครงสร้าง Map Database ของ MapleStory N (73 Layers)\n")
for gname, glist in groups.items():
    out_lines.append(f"### 📍 กลุ่มเลเวล/พลัง: **{gname}** ({len(glist)} Layers)\n")
    for item in glist:
        lid = item['layerId']
        lname = item['layerName']
        lvl = f"Lv. {item.get('minLevel')}-{item.get('maxLevel')}"
        sub_list = alias_map.get(lid, [])
        # กรองเอาเฉพาะแมพย่อยที่ไม่ใช่ชื่อตรงกับ layerName
        sub_only = [s for s in sub_list if s.lower() != lname.lower() and s.lower() not in lname.lower()]
        sub_str = ", ".join([f"`{s}`" for s in sub_only[:6]]) if sub_only else "*ใช้ชื่อโซนหลัก*"
        if len(sub_only) > 6:
            sub_str += f" *(+{len(sub_only)-6} แมพย่อย)*"
        out_lines.append(f"- **ID `{lid}`**: **{lname}** ({lvl})\n  - *แมพย่อย/คีย์เวิร์ด:* {sub_str}")
    out_lines.append("")

with open(r'0.aเศษซากอรยะธรรมของAI\layers_full_summary.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))

print("Summary written successfully.")
