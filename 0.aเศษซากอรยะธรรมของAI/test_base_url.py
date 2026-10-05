import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
# Search for constructor or instantiation of httpRequest
matches = [m.start() for m in re.finditer(r'new\s+[A-Za-z0-9_$]+\s*\(\s*\{[^}]*BASE', r.text)]
for idx in matches[:5]:
    print("Match BASE:", r.text[idx:idx+150])

# Search for any full URL strings
urls = set(re.findall(r'https://[a-zA-Z0-9.-]+\.xangle\.io[a-zA-Z0-9._/-]*', r.text))
print("All xangle URLs found:")
for u in sorted(urls):
    print(" ", u)
