import urllib.request, json, re

keys = [
    "gw_9300321ad25e8c9ee671b39b683681ed21befc8ff886fa982f049992417ee03a8f7f24b7a7dfcd789945c74bfff26452",
    "gw_91a3dc4dfa157a8971e67fb7e38d3add0fdd3f4dfc0caf21ac82fc29c650efee85c7920c8a113a09b7a4a670ba466fe9"
]
url = 'https://openapi.msu.io/v1rc1/msn/rewards/0'
payload = {'layerDescs': [{'layerId': 130002}]}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'x-nxopen-api-key': keys[0], 'User-Agent': 'Mozilla/5.0'},
    method='POST'
)

with urllib.request.urlopen(req) as resp:
    d = json.loads(resp.read().decode('utf-8'))
    items = d['data']['rewardInformations']['rewardInformations'][0]['fieldInformation']['items']
    for it in items:
        if it.get('key', {}).get('itemId') == 1:
            print("ENABLE_BOOST:", it.get('enableBoostOption'))
            print(json.dumps(it, indent=2))
