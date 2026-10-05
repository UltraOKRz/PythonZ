import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
idx = r.text.find('https://api-gateway.xangle.io')
print(r.text[idx-200:idx+600])
