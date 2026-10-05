import re

path = r'c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Main\โพสิชั่น.pyw'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add variables to __init__
content = content.replace(
    'self.current_pct_change = 0.0',
    'self.current_pct_change = 0.0\n        self.display_currency = "USDT"\n        self.usdt_thb_rate = 34.00'
)

# 2. Add fetch_usdt_thb to __init__ threading
content = content.replace(
    'threading.Thread(target=self.fetch_all_symbols, daemon=True).start()',
    'threading.Thread(target=self.fetch_all_symbols, daemon=True).start()\n        threading.Thread(target=self.fetch_usdt_thb, daemon=True).start()'
)

# 3. Add fetch_usdt_thb method definition before on_closing
new_method = '''
    def fetch_usdt_thb(self):
        import time, requests
        while True:
            try:
                res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTTHB", timeout=5)
                if res.status_code == 200:
                    self.usdt_thb_rate = float(res.json()["price"])
            except: pass
            time.sleep(60)

'''
content = content.replace('    def on_closing(self):', new_method + '    def on_closing(self):')

# 4. Add btn_currency and toggle_currency
btn_code = '''        tk.Button(f_right, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)
        
        self.btn_currency = tk.Button(f_right, text="THB", command=self.toggle_currency, bg="#ff9800", fg="#000", bd=0, font=("Arial", 9, "bold"), cursor="hand2")
        self.btn_currency.pack(side=tk.RIGHT, padx=4)'''
content = content.replace('        tk.Button(f_right, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)', btn_code)

toggle_code = '''
    def toggle_currency(self):
        if self.display_currency == "USDT":
            self.display_currency = "THB"
            self.btn_currency.config(text="USDT", bg="#00bfff", fg="#fff")
        else:
            self.display_currency = "USDT"
            self.btn_currency.config(text="THB", bg="#ff9800", fg="#000")
        self.update_sim_ui(self.current_live_price, self.current_pct_change)

    def start_drag(self, event):'''
content = content.replace('    def start_drag(self, event):', toggle_code)

# 5. Modify update_sim_ui
old_update_sim_ui = '''            if market == "FUTURES":
                if entry > 0 and margin > 0:
                    qty = (margin * lev) / entry
                    pnl = (live_price - entry) * qty if side == "Long" else (entry - live_price) * qty
                    roe = (pnl / margin) * 100
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"PNL: {sign}${pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
            else:
                val = margin * live_price
                if entry > 0:
                    pnl = (live_price - entry) * margin
                    cost = entry * margin
                    roe = (pnl / cost) * 100 if cost > 0 else 0
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"Value: ${val:,.2f} | PNL: {sign}${pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
                else:
                    self.lbl_pnl.config(text=f"Value: ${val:,.2f} (Spot)", fg="#00bfff")'''

new_update_sim_ui = '''            rate = self.usdt_thb_rate if getattr(self, "display_currency", "USDT") == "THB" else 1.0
            sym_char = "฿" if getattr(self, "display_currency", "USDT") == "THB" else "$"
            
            if market == "FUTURES":
                if entry > 0 and margin > 0:
                    qty = (margin * lev) / entry
                    pnl = (live_price - entry) * qty if side == "Long" else (entry - live_price) * qty
                    roe = (pnl / margin) * 100
                    disp_pnl = pnl * rate
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"PNL: {sign}{sym_char}{disp_pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
            else:
                val = (margin * live_price) * rate
                if entry > 0:
                    pnl = (live_price - entry) * margin
                    cost = entry * margin
                    roe = (pnl / cost) * 100 if cost > 0 else 0
                    disp_pnl = pnl * rate
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"Value: {sym_char}{val:,.2f} | PNL: {sign}{sym_char}{disp_pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
                else:
                    self.lbl_pnl.config(text=f"Value: {sym_char}{val:,.2f} (Spot)", fg="#00bfff")'''

content = content.replace(old_update_sim_ui, new_update_sim_ui)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully!')
