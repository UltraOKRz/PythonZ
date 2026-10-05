import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
# Find HEADERS in request constructor
m = re.findall(r'HEADERS\s*:\s*\{[^}]*\}', r.text)
print("HEADERS definitions:", m)

# Search for x-project or x-chain or similar header strings
custom_headers = set(re.findall(r'["\'](x-[a-zA-Z0-9_-]+)["\']', r.text, re.IGNORECASE))
print("Custom headers:", custom_headers)

# Test GET to https://api-gateway.xangle.io/evm/address/transaction/list?address=...
addr = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
url = f"https://api-gateway.xangle.io/evm/address/transaction/list?address={addr}&page=1&size=10"
for h_name in custom_headers:
    # check if there's any value associated with it
    pass

res = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Origin": "https://msu-explorer.xangle.io"}, timeout=5)
print("Direct GET status:", res.status_code)
if res.status_code == 200:
    print("Direct GET body:", res.text[:400])
else:
    print("Direct GET error body:", res.text[:400])
