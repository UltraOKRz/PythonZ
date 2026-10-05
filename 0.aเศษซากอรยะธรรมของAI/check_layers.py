import json
import re

with open("layers_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

cache_ids = {c["layerId"]: c for c in cache}

with open("Cloack_Overlay.pyw", "r", encoding="utf-8") as f:
    text = f.read()

alias_matches = re.findall(r'\((\d{6}),\s*\[(.*?)\]\)', text)
alias_map = {}
for lid, kws in alias_matches:
    cleaned = [re.sub(r'[\'\"\s]', '', k) for k in kws.split(',') if k.strip()]
    alias_map[int(lid)] = cleaned

extra_in_aliases = [lid for lid in alias_map if lid not in cache_ids]
print(f"Extra layer IDs in aliases not in cache: {extra_in_aliases}")
for lid in extra_in_aliases:
    print(f"  {lid}: {alias_map[lid]}")
