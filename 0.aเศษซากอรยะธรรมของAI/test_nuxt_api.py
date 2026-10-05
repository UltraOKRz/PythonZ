import requests
import re

url = "https://msu-explorer.xangle.io/address/0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
scripts = re.findall(r'src="(/_nuxt/[^"]+)"', r.text)
print("Nuxt scripts:", len(scripts))
for s in scripts[:5]:
    sr = requests.get("https://msu-explorer.xangle.io" + s, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    matches = set(re.findall(r'https?://[a-zA-Z0-9.-]*(?:api|explorer)[a-zA-Z0-9._/-]*', sr.text))
    endpoints = set(re.findall(r'"/(?:api|v[0-9])/?[^"]*"', sr.text))
    if matches or endpoints:
        print(s)
        print("  matches:", list(matches)[:5])
        print("  endpoints:", list(endpoints)[:5])
