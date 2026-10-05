import re
import os

filepath = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Init DCA data in __init__
pattern1 = r'(self\.cfg_data = json\.load\(f\)\n\s*except:\n\s*self\.cfg_data = \{\})\n\s*(if "opacity" not in self\.cfg_data:)'
replacement1 = r'\1\n        if "spot_dca" not in self.cfg_data: self.cfg_data["spot_dca"] = {}\n        \2'
content = re.sub(pattern1, replacement1, content)

# 2. Add DCA Manager button in `show_step_3_view` (Spot section)
pattern2 = r'            else:\n                tk\.Label\(f, text="จำนวนเหรียญ \(Amount\):", bg="#1e2329", fg="#fff"\)\.grid\(row=1, column=0, sticky=tk\.W, pady=5\)\n                self\.margin_var = tk\.DoubleVar\(value=self\.cfg_data\.get\("margin", 1\.0\)\)\n                tk\.Entry\(f, textvariable=self\.margin_var, font=\("Arial", 10\)\)\.grid\(row=1, column=1, sticky=tk\.EW, pady=5\)\n                \n                self\.entry_var = tk\.DoubleVar\(value=0\.0\)\n                self\.lev_var = tk\.IntVar\(value=1\)\n                self\.side_var = tk\.StringVar\(value="Long"\)'
replacement2 = r"""            else:
                tk.Button(f, text="➕ จัดการประวัติซื้อ (Spot DCA)", font=("Arial", 10, "bold"), bg="#00bfff", fg="#000", cursor="hand2", command=self.open_dca_manager).grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=10)
                
                tk.Label(f, text="จำนวนเหรียญรวม (Sim):", bg="#1e2329", fg="#fff").grid(row=2, column=0, sticky=tk.W, pady=5)
                self.margin_var = tk.DoubleVar(value=self.cfg_data.get("margin", 1.0))
                tk.Entry(f, textvariable=self.margin_var, font=("Arial", 10), state="disabled").grid(row=2, column=1, sticky=tk.EW, pady=5)
                
                self.entry_var = tk.DoubleVar(value=0.0)
                self.lev_var = tk.IntVar(value=1)
                self.side_var = tk.StringVar(value="Long")"""
content = re.sub(pattern2, replacement2, content)

# 3. Modify API fetch listbox for SPOT to show Average Entry if available
pattern3 = r'            if market == "FUTURES":\n                sign = "\+" if d\[\'pnl\'\] >= 0 else ""\n                self\.pos_listbox\.insert\(tk\.END, f"\{d\[\'symbol\'\]\} \| \{d\[\'side\'\]\} \{d\[\'amt\'\]:,\.4f\} \| Entry \{d\[\'entry\'\]:,\.4f\} \| PNL \{sign\}\$\{d\[\'pnl\'\]:,\.2f\}"\)\n            else:\n                self\.pos_listbox\.insert\(tk\.END, f"\{d\[\'symbol\'\]\} \| Balance \{d\[\'amt\'\]:,\.4f\}"\)'
replacement3 = r"""            if market == "FUTURES":
                sign = "+" if d['pnl'] >= 0 else ""
                self.pos_listbox.insert(tk.END, f"{d['symbol']} | {d['side']} {d['amt']:,.4f} | Entry {d['entry']:,.4f} | PNL {sign}${d['pnl']:,.2f}")
            else:
                dca = self.cfg_data.get("spot_dca", {}).get(d['symbol'], [])
                if dca:
                    total_amt = sum(x["a"] for x in dca)
                    avg_p = sum(x["p"] * x["a"] for x in dca) / total_amt if total_amt > 0 else 0
                    self.pos_listbox.insert(tk.END, f"{d['symbol']} | Bal {d['amt']:,.4f} | Avg Entry {avg_p:,.4f}")
                else:
                    self.pos_listbox.insert(tk.END, f"{d['symbol']} | Bal {d['amt']:,.4f}")"""
content = re.sub(pattern3, replacement3, content)

# 4. In `start_simulation`, calculate Spot Average Entry and total amount
pattern4 = r'            else:\n                sym = data\["symbol"\]\n                if sym != "USDT" and not sym\.endswith\("USDT"\): sym \+= "USDT"\n                self\.cfg_data\["symbol"\] = sym\n                self\.cfg_data\["entry"\] = 0\n                self\.cfg_data\["side"\] = "Long"\n                self\.cfg_data\["margin"\] = data\["amt"\] \n                self\.cfg_data\["leverage"\] = 1'
replacement4 = r"""            else:
                sym = data["symbol"]
                if sym != "USDT" and not sym.endswith("USDT"): sym += "USDT"
                self.cfg_data["symbol"] = sym
                
                dca = self.cfg_data.get("spot_dca", {}).get(sym, [])
                if dca:
                    total_amt = sum(x["a"] for x in dca)
                    avg_p = sum(x["p"] * x["a"] for x in dca) / total_amt if total_amt > 0 else 0
                    self.cfg_data["entry"] = avg_p
                    if mode != "API": self.cfg_data["margin"] = total_amt
                    else: self.cfg_data["margin"] = data["amt"]
                else:
                    self.cfg_data["entry"] = 0
                    self.cfg_data["margin"] = data["amt"]
                
                self.cfg_data["side"] = "Long"
                self.cfg_data["leverage"] = 1"""
content = re.sub(pattern4, replacement4, content)

# 5. In `start_simulation` floating UI init
pattern5 = r'        if self\.active_sim\.get\("market"\) == "SPOT":\n            self\.lbl_side_sym\.config\(text=f"\[Spot \{self\.active_sim\[\'symbol\'\]\}\]", fg="#00e676"\)\n            self\.lbl_entry\.pack_forget\(\)\n            self\.entry_sep\.pack_forget\(\)'
replacement5 = r"""        if self.active_sim.get("market") == "SPOT":
            self.lbl_side_sym.config(text=f"[Spot {self.active_sim['symbol']}]", fg="#00e676")
            entry_val = self.active_sim.get('entry', 0)
            if entry_val > 0:
                self.lbl_entry.config(text=f"Avg: {entry_val:,.4f}" if entry_val < 1 else f"Avg: {entry_val:,.2f}")
                self.lbl_entry.pack(side=tk.LEFT, padx=6)
                self.entry_sep.pack(side=tk.LEFT)
            else:
                self.lbl_entry.pack_forget()
                self.entry_sep.pack_forget()"""
content = re.sub(pattern5, replacement5, content)

# 6. Update `update_sim_ui` for PNL calculation
pattern6 = r'            if market == "FUTURES":\n                entry, margin, lev, side = self\.active_sim\["entry"\], self\.active_sim\["margin"\], self\.active_sim\["leverage"\], self\.active_sim\["side"\]\n                if entry > 0 and margin > 0:\n                    qty = \(margin \* lev\) / entry\n                    pnl = \(live_price - entry\) \* qty if side == "Long" else \(entry - live_price\) \* qty\n                    roe = \(pnl / margin\) \* 100\n                    color = up_col if pnl >= 0 else dn_col\n                    sign = "\+" if pnl >= 0 else ""\n                    self\.lbl_pnl\.config\(text=f"\{sign\}\$\{pnl:,\.2f\} \(\{sign\}\{roe:,\.2f\}%\)", fg=color\)\n            else:\n                amt = self\.active_sim\["margin"\]\n                val = amt \* live_price\n                self\.lbl_pnl\.config\(text=f"≈ \$\{val:,\.2f\} \(Spot\)", fg="#00bfff"\)'
replacement6 = r"""            entry = self.active_sim.get("entry", 0)
            margin = self.active_sim.get("margin", 0)
            lev = self.active_sim.get("leverage", 1)
            side = self.active_sim.get("side", "Long")
            
            if market == "FUTURES":
                if entry > 0 and margin > 0:
                    qty = (margin * lev) / entry
                    pnl = (live_price - entry) * qty if side == "Long" else (entry - live_price) * qty
                    roe = (pnl / margin) * 100
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"{sign}${pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
            else:
                val = margin * live_price
                if entry > 0:
                    pnl = (live_price - entry) * margin
                    cost = entry * margin
                    roe = (pnl / cost) * 100 if cost > 0 else 0
                    color = up_col if pnl >= 0 else dn_col
                    sign = "+" if pnl >= 0 else ""
                    self.lbl_pnl.config(text=f"Value: ${val:,.2f} | PNL {sign}${pnl:,.2f} ({sign}{roe:,.2f}%)", fg=color)
                else:
                    self.lbl_pnl.config(text=f"Value: ${val:,.2f} (Spot)", fg="#00bfff")"""
content = re.sub(pattern6, replacement6, content)

# 7. Chart UI integration in `render_candlesticks`
pattern7 = r'        if self\.active_sim\.get\("market"\) == "SPOT":\n            amt = self\.active_sim\["margin"\]\n            val = amt \* live_price\n            canvas\.create_text\(5, inner_h - 15, text=f"Spot Balance: \{amt:,\.4f\} \{self\.active_sim\[\'symbol\'\]\.replace\(\'USDT\',\'\'\)\} ≈ \$\{val:,\.2f\}", fill="#00e676", anchor=tk\.W, font=\(\"Arial\", 9, \"bold\"\)\)\n            \n        elif entry_price > 0:'
replacement7 = r"""        if entry_price > 0:"""
content = re.sub(pattern7, replacement7, content)

# Add [B] tags in `render_candlesticks`
pattern8 = r'        # เส้น Live Price'
replacement8 = r"""        # Draw [B] DCA tags for Spot
        if self.active_sim and self.active_sim.get("market") == "SPOT":
            dca_list = self.cfg_data.get("spot_dca", {}).get(self.active_sim['symbol'], [])
            for buy in dca_list:
                bp = buy["p"]
                ba = buy["a"]
                y_b = inner_h - ((bp - act_min) / act_rng) * inner_h
                if 0 <= y_b <= inner_h:
                    canvas.create_line(inner_w - 15, y_b, inner_w, y_b, fill="#00e676", dash=(1,1))
                    canvas.create_text(inner_w - 18, y_b, text=f"[B] {ba:g}", fill="#00e676", anchor=tk.E, font=("Arial", 7))

        # เส้น Live Price"""
content = re.sub(pattern8, replacement8, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Spot DCA integration applied.")
