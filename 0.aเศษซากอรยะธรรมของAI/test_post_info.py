import requests

addr = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"
payload = {"address": addr}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://msu-explorer.xangle.io",
    "Referer": "https://msu-explorer.xangle.io/"
}

hosts = [
    "https://api-gateway.xangle.io/api/address/info",
    "https://msu-explorer.xangle.io/api/address/info",
    "https://api-gateway.xangle.io/explorer/nexon/api/address/info",
]

for url in hosts:
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"POST {url} -> {r.status_code}")
        if r.status_code == 200:
            print("Response:", r.text[:500])
    except Exception as e:
        print(f"Error {url}: {e}")
