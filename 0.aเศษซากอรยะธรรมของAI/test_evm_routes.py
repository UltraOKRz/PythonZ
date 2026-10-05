import requests
import re

r = requests.get('https://msu-explorer.xangle.io/_nuxt/CLo8Sbti.js', headers={'User-Agent': 'Mozilla/5.0'})
# Find where evmAddressController is instantiated
matches = [m.start() for m in re.finditer(r'evmAddressController', r.text)]
for idx in matches[:5]:
    print("Match:", r.text[idx:idx+250])

matches2 = [m.start() for m in re.finditer(r'/evm/address', r.text)]
for idx in matches2[:5]:
    print("Match evm/address:", r.text[idx-50:idx+150])
