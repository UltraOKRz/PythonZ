import urllib.request
import re

base = "https://msutool.com"
js_files = [
    "/assets/index-BNWLyfqU.js", 
    "/assets/http-client-_dUyW1sf.js", 
    "/assets/http-CySTmfY4.js"
]

for jf in js_files:
    url = base + jf
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            print(f"=== {jf} (len={len(content)}) ===")
            apis = set(re.findall(r"https?://[a-zA-Z0-9_\-\.\:/]+", content))
            for a in sorted(apis):
                if not any(k in a for k in ["w3.org", "github", "google", "schema.org", "cloudflare"]):
                    print(" URL:", a)
            paths = set(re.findall(r"[\'\"`](/(?:api|v1|v2|reward|field|pool)[^\'\"`]+)[\'\"`]", content))
            for p in sorted(paths):
                print(" Path:", p)
    except Exception as e:
        print(f"Err {jf}:", e)
