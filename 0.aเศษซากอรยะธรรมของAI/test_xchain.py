import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
matches = [m.start() for m in re.finditer(r'X-Chain', r.text, re.IGNORECASE)]
for idx in matches:
    print(r.text[max(0, idx-50):min(len(r.text), idx+100)])
