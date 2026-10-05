import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
# Find all occurrences of baseURL or api or prefix
base_urls = set(re.findall(r'baseURL\s*:\s*["\']([^"\']+)["\']', r.text))
print("baseURL:", base_urls)

# Find api calls near 'api/address'
matches = [m.start() for m in re.finditer(r'/address/info', r.text)]
for idx in matches[:5]:
    print("Context:", r.text[max(0, idx-60):min(len(r.text), idx+60)].replace('\n', ' '))
