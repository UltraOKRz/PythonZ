import requests
import re

url = "https://msu-explorer.xangle.io/address/0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
print("Explorer Status:", r.status_code)

# Check for JSON payloads or api calls in HTML
api_calls = re.findall(r'https?://[a-zA-Z0-9.-]+/[a-zA-Z0-9._/-]+', r.text)
interesting = [a for a in set(api_calls) if any(k in a for k in ['api', 'xangle', 'msu', 'balance', 'token'])]
print("Interesting links/APIs:", interesting[:10])

# Check for keywords
keywords = ['NXPC', 'NESO', 'Balance', '0x69ca']
for kw in keywords:
    matches = [m.start() for m in re.finditer(kw, r.text, re.IGNORECASE)]
    print(f"Keyword '{kw}' found: {len(matches)} times")
    for idx in matches[:3]:
        snippet = r.text[max(0, idx-50):min(len(r.text), idx+100)].replace('\n', ' ')
        print(f"  Snippet: {snippet}")
