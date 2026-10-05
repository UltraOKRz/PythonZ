import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
# Find definition of cM
m = re.search(r'class\s+cM\s*\{[^}]*constructor[^}]*\}', r.text)
if m:
    print(m.group(0))
else:
    idx = r.text.find('class cM')
    if idx != -1:
        print(r.text[idx:idx+300])
    else:
        # maybe cM=class
        idx = r.text.find('cM=')
        print("cM=", r.text[idx:idx+300])
