import time, hmac, hashlib, requests

key = "OUApv4KlhLg9de0FrU2UWaK25JDO9GWqTSlw5w5hG9czNnI69rbkcYOGb6e3FkfI"
secret = "6FyPpcSOjtX0mPDt3oBJJrJOmpAqu7jM5nPzV4A1rMpVKYvQZNgiePvLyJutTSdg"

ts = int(time.time() * 1000)
qs = f"timestamp={ts}&recvWindow=10000"
sig = hmac.new(secret.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256).hexdigest()
headers = {"X-MBX-APIKEY": key}

results = []
res = requests.get(f"https://api.binance.com/api/v3/account?{qs}&signature={sig}", headers=headers)
if res.status_code == 200:
    for b in res.json().get("balances", []):
        free = float(b["free"])
        if free > 0:
            raw_asset = b["asset"]
            is_earn = raw_asset.startswith("LD") and len(raw_asset) > 2
            asset = raw_asset[2:] if is_earn else raw_asset
            results.append({
                "symbol": asset,
                "raw_symbol": raw_asset,
                "amt": free,
                "wallet": "Earn" if is_earn else "Spot"
            })

res_f = requests.post(f"https://api.binance.com/sapi/v1/asset/get-funding-asset?{qs}&signature={sig}", headers=headers)
if res_f.status_code == 200:
    for fa in res_f.json():
        free_f = float(fa.get("free", 0))
        if free_f > 0:
            results.append({
                "symbol": fa["asset"],
                "raw_symbol": fa["asset"],
                "amt": free_f,
                "wallet": "Funding"
            })

for d in results:
    amt_val = d["amt"]
    amt_str = f"{amt_val:.8f}".rstrip("0").rstrip(".") if amt_val < 0.0001 else f"{amt_val:,.4f}"
    w = d.get("wallet", "")
    tag = f" ({w})" if w and w != "Spot" else ""
    print(f"{d['symbol']}{tag} | Bal {amt_str}")
