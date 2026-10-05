import re

filepath = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update setup_floating_ui
new_setup_floating_ui = """    def setup_floating_ui(self):
        f = tk.Frame(self.win_fg, bg=self.trans_key)
        f.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        
        self.drag_handle = tk.Label(f, text=" ⣿ ", fg="#aaaaaa", bg=self.trans_key, font=("Arial", 14), cursor="fleur")
        self.drag_handle.pack(side=tk.LEFT, fill=tk.Y)
        
        f_right = tk.Frame(f, bg=self.trans_key)
        f_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.grip_lbl = tk.Label(f_right, text="◢", bg=self.trans_key, fg="#aaaaaa", cursor="sizing")
        self.grip_lbl.pack(side=tk.RIGHT, anchor=tk.SE)
        
        tk.Button(f_right, text="✖", command=self.show_settings, bg=self.trans_key, fg="#ff3d57", bd=0, font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(2, 4))
        tk.Button(f_right, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)
        
        self.btn_dca = tk.Button(f_right, text="➕ DCA", command=lambda: self.open_dca_manager(self.active_sim.get("symbol") if self.active_sim else None), bg=self.trans_key, fg="#00e676", bd=0, font=("Arial", 9, "bold"), cursor="hand2")
        
        f_mid = tk.Frame(f, bg=self.trans_key)
        f_mid.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        f_top = tk.Frame(f_mid, bg=self.trans_key)
        f_top.pack(side=tk.TOP, fill=tk.X, pady=(2,0))
        
        f_bot = tk.Frame(f_mid, bg=self.trans_key)
        f_bot.pack(side=tk.TOP, fill=tk.X)
        
        self.lbl_side_sym = tk.Label(f_top, text="[-]", fg="#00bfff", bg=self.trans_key, font=("Arial", 10, "bold"))
        self.lbl_side_sym.pack(side=tk.LEFT)
        
        self.sep_size = tk.Label(f_top, text=" | ", fg="#444", bg=self.trans_key, font=("Arial", 9))
        self.sep_size.pack(side=tk.LEFT)
        self.lbl_size = tk.Label(f_top, text="Size: 0.00", fg="#aaa", bg=self.trans_key, font=("Arial", 9))
        self.lbl_size.pack(side=tk.LEFT)
        
        self.sep_margin = tk.Label(f_top, text=" | ", fg="#444", bg=self.trans_key, font=("Arial", 9))
        self.sep_margin.pack(side=tk.LEFT)
        self.lbl_margin = tk.Label(f_top, text="Margin: $0.00", fg="#aaa", bg=self.trans_key, font=("Arial", 9))
        self.lbl_margin.pack(side=tk.LEFT)

        self.lbl_entry = tk.Label(f_bot, text="Entry: 0.00", fg="#aaaaaa", bg=self.trans_key, font=("Arial", 10))
        self.lbl_entry.pack(side=tk.LEFT)
        
        self.sep_live = tk.Label(f_bot, text=" | ", fg="#444", bg=self.trans_key, font=("Arial", 9))
        self.sep_live.pack(side=tk.LEFT)
        
        self.lbl_live = tk.Label(f_bot, text="Live: 0.00 (0.00%)", fg="#ffffff", bg=self.trans_key, font=("Arial", 10, "bold"), cursor="hand2")
        self.lbl_live.pack(side=tk.LEFT)
        self.lbl_live.bind("<Enter>", self.on_hover_live)
        self.lbl_live.bind("<Leave>", self.on_leave_live)
        self.lbl_live.bind("<Button-1>", self.open_full_chart)
        
        tk.Label(f_bot, text=" | ", fg="#444", bg=self.trans_key, font=("Arial", 9)).pack(side=tk.LEFT)
        self.lbl_pnl = tk.Label(f_bot, text=" PNL: $0.00 (0.00%)", fg="#fff", bg=self.trans_key, font=("Arial", 11, "bold"))
        self.lbl_pnl.pack(side=tk.LEFT, expand=True, anchor=tk.W)

        for w in [f, self.drag_handle, self.lbl_side_sym, self.lbl_entry, self.lbl_pnl, f_mid, f_top, f_bot, self.lbl_size, self.lbl_margin]:
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)

        self.grip_lbl.bind("<ButtonPress-1>", self.start_resize)
        self.grip_lbl.bind("<B1-Motion>", self.do_resize)"""

content = re.sub(r'    def setup_floating_ui\(self\):.*?    def start_drag\(self, event\):', new_setup_floating_ui + '\n\n    def start_drag(self, event):', content, flags=re.DOTALL)

# 2. Update window height and start_simulation
new_start_sim_ui = """        self.win_bg.geometry(f"700x55+{x}+{y}")
        self.win_fg.geometry(f"700x55+{x}+{y}")
        self.win_bg.attributes("-alpha", self.active_sim["opacity"])
        
        if self.active_sim.get("market") == "SPOT":
            self.lbl_side_sym.config(text=f"[Spot {self.active_sim['symbol']}]", fg="#00e676")
            entry_val = self.active_sim.get('entry', 0)
            
            self.btn_dca.pack(side=tk.RIGHT, padx=4)
            
            amt = self.active_sim.get('margin', 0)
            self.lbl_size.config(text=f"Size: {amt:g} {self.active_sim['symbol'].replace('USDT','')}")
            self.sep_size.pack(side=tk.LEFT)
            self.lbl_size.pack(side=tk.LEFT)
            
            self.lbl_margin.pack_forget()
            self.sep_margin.pack_forget()
            
            if entry_val > 0:
                self.lbl_entry.config(text=f"Avg: {entry_val:,.4f}" if entry_val < 1 else f"Avg: {entry_val:,.2f}")
                self.lbl_entry.pack(side=tk.LEFT)
                self.sep_live.pack(side=tk.LEFT)
            else:
                self.lbl_entry.pack_forget()
                self.sep_live.pack_forget()
                
        else:
            self.btn_dca.pack_forget()
            side_color = "#00bfff" if self.active_sim.get("side", "Long") == "Long" else "#ff9800"
            self.lbl_side_sym.config(text=f"[{self.active_sim.get('side', 'Long')} {self.active_sim['symbol']}]", fg=side_color)
            
            entry_val = self.active_sim['entry']
            self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")
            self.lbl_entry.pack(side=tk.LEFT)
            self.sep_live.pack(side=tk.LEFT)
            
            margin = self.active_sim.get('margin', 0)
            lev = self.active_sim.get('leverage', 1)
            qty = (margin * lev) / entry_val if entry_val > 0 else 0
            
            self.lbl_size.config(text=f"Size: {qty:g} {self.active_sim['symbol'].replace('USDT','')}")
            self.sep_size.pack(side=tk.LEFT)
            self.lbl_size.pack(side=tk.LEFT)
            
            self.lbl_margin.config(text=f"Margin: ${margin:,.2f}")
            self.sep_margin.pack(side=tk.LEFT)
            self.lbl_margin.pack(side=tk.LEFT)"""

content = re.sub(r'        self\.win_bg\.geometry\(f"700x45\+\{x\}\+\{y\}"\).*?        self\.start_ws\(self\.active_sim\.get\("market"\), self\.active_sim\["symbol"\]\)', new_start_sim_ui + '\n\n        self.start_ws(self.active_sim.get("market"), self.active_sim["symbol"])', content, flags=re.DOTALL)


# 3. Update update_sim_ui PNL text
new_update_sim_ui = """    def update_sim_ui(self, live_price, pct_change):
        if not self.active_sim or not self.win_fg.winfo_exists(): return
        try:
            market = self.active_sim.get("market", "FUTURES")
            up_col, dn_col = self.get_colors()
            live_str = f"{live_price:,.4f}" if live_price < 1 else f"{live_price:,.2f}"
            pct_col = up_col if pct_change >= 0 else dn_col
            pct_sign = "+" if pct_change > 0 else ""
            self.lbl_live.config(text=f"Live: {live_str} ({pct_sign}{pct_change:.2f}%)", fg=pct_col)
            
            entry = self.active_sim.get("entry", 0)
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
                    self.lbl_pnl.config(text=f"Value: ${val:,.2f} (Spot)", fg="#00bfff")
        except: pass"""

content = re.sub(r'    def update_sim_ui\(self, live_price, pct_change\):.*?        except: pass', new_update_sim_ui, content, flags=re.DOTALL)

# 4. Update open_dca_manager inner ui update
old_dca_ui_update = """                if avg > 0:
                    self.lbl_entry.config(text=f"Avg: {avg:,.4f}" if avg < 1 else f"Avg: {avg:,.2f}")
                    self.lbl_entry.pack(side=tk.LEFT, padx=6)
                    self.entry_sep.pack(side=tk.LEFT)
                else:
                    self.lbl_entry.pack_forget()
                    self.entry_sep.pack_forget()"""

new_dca_ui_update = """                if avg > 0:
                    self.lbl_entry.config(text=f"Avg: {avg:,.4f}" if avg < 1 else f"Avg: {avg:,.2f}")
                    self.lbl_entry.pack(side=tk.LEFT)
                    self.sep_live.pack(side=tk.LEFT)
                else:
                    self.lbl_entry.pack_forget()
                    self.sep_live.pack_forget()
                
                # Update Size too!
                self.lbl_size.config(text=f"Size: {total_amt:g} {self.active_sim['symbol'].replace('USDT','')}")"""

content = content.replace(old_dca_ui_update, new_dca_ui_update)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Floating UI Refactored.")
