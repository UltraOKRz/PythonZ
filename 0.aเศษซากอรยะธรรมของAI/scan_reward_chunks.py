import urllib.request
import re

base = "https://msutool.com"

# ดึง index.html มาหา chunk ทั้งหมด
req = urllib.request.Request(base + "/rewards?tab=pool&world=0&layerId=122001&layer=LAYER_TYPE_FIELD", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode("utf-8", errors="ignore")

js_files = re.findall(r'href="(/assets/[^"]+\.js)"', html) + re.findall(r'src="(/assets/[^"]+\.js)"', html)
print(f"Total JS files found in HTML: {len(js_files)}")

# หาใน index-BNWLyfqU.js เพิ่มด้วย เพราะ vite dynamic import chunks จะอยู่ในนั้น
req_main = urllib.request.Request(base + "/assets/index-BNWLyfqU.js", headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req_main) as resp:
    main_js = resp.read().decode("utf-8", errors="ignore")

other_chunks = set(re.findall(r'assets/([a-zA-Z0-9_\-]+\.js)', main_js))
print(f"Total other chunks referenced in main_js: {len(other_chunks)}")

# รวม chunk ทั้งหมด
all_js = set(js_files) | {f"/assets/{c}" for c in other_chunks}
print(f"Total unique chunks to scan: {len(all_js)}")

# ค้นหา chunk ที่มีคำว่า LAYER_TYPE_FIELD หรือ layerId หรือ drop หรือ pool
target_chunks = []
for c in all_js:
    try:
        req_c = urllib.request.Request(base + c, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_c) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            if "LAYER_TYPE_FIELD" in text or "layerId" in text or "rewards" in text:
                print(f"Found match in {c} (len={len(text)})")
                target_chunks.append((c, text))
    except Exception as e:
        pass

for c, text in target_chunks:
    print(f"\n=================== ANALYZING {c} ===================")
    # ค้นหา API calls (fetch, axios, get, post, rpc)
    urls = set(re.findall(r'https?://[a-zA-Z0-9_\-\.\:/]+', text))
    for u in urls:
        print(" URL:", u)
    
    # ค้นหา pattern การยิง request
    matches = re.findall(r'(?:fetch|get|post)\s*\(\s*[`\'"][^`\'"]+[`\'"]', text)
    for m in matches[:10]:
        print(" Call:", m)

    # ค้นหา contract address หรือ function call หรือ endpoint
    contracts = re.findall(r'0x[a-fA-F0-9]{40}', text)
    if contracts:
        print(" Contracts found:", set(contracts))
        
    # ค้นหาข้อความรอบๆ LAYER_TYPE_FIELD
    for m in re.finditer(r'LAYER_TYPE_FIELD', text):
        start = max(0, m.start() - 150)
        end = min(len(text), m.end() + 150)
        print(" Snippet around LAYER_TYPE_FIELD:\n", text[start:end])
