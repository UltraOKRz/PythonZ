import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
routes = set(re.findall(r'["\'](/[a-zA-Z0-9_\-\/]+)["\']', r.text))
filtered = [x for x in routes if any(k in x.lower() for k in ['account', 'address', 'search', 'detail', 'info', 'balance'])]
print("Found filtered paths:", len(filtered))
for p in sorted(filtered)[:25]:
    print(" ", p)
