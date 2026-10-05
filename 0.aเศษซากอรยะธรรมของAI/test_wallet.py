import requests

addr = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"

# Check direct URL on explorer and navigator
endpoints = [
    f"https://msu-explorer.xangle.io/api/v1/address/{addr}",
    f"https://msu.io/navigator/user/{addr}",
    f"https://msu.io/navigator/account/{addr}",
    f"https://msu-explorer.xangle.io/address/{addr}"
]

for url in endpoints:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        print(f"URL: {url} -> Status: {r.status_code}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
