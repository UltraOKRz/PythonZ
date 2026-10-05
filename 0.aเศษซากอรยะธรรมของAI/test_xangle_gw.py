import requests

addr = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://msu-explorer.xangle.io",
    "Referer": "https://msu-explorer.xangle.io/"
}

test_urls = [
    f"https://api-gateway.xangle.io/explorer/nexon/account/{addr}",
    f"https://api-gateway.xangle.io/explorer/nexon/address/{addr}",
    f"https://api-gateway.xangle.io/explorer/nexon/accounts/{addr}",
    f"https://api-gateway.xangle.io/api/explorer/nexon/account/{addr}",
    f"https://api-gateway.xangle.io/explorer/henesys/account/{addr}",
    f"https://api-gateway.xangle.io/explorer/henesys/address/{addr}"
]

for u in test_urls:
    try:
        r = requests.get(u, headers=headers, timeout=5)
        print(u, "->", r.status_code)
        if r.status_code == 200:
            print("Response:", r.text[:300])
    except Exception as e:
        print(u, "->", e)
