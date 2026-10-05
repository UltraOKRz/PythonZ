import requests

addr = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://msu-explorer.xangle.io",
    "Referer": "https://msu-explorer.xangle.io/"
}

test_queries = [
    f"https://msu-explorer.xangle.io/api/address/info?address={addr}",
    f"https://msu-explorer.xangle.io/api/address/info/{addr}",
    f"https://msu-explorer.xangle.io/api/address/coin/list?address={addr}",
    f"https://msu-explorer.xangle.io/api/address/nft/list?address={addr}",
    f"https://api-gateway.xangle.io/api/address/info?address={addr}",
]

for url in test_queries:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"URL: {url} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("Response:", r.text[:300])
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
