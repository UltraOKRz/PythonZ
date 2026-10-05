import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix the Combobox focus issue
content = re.sub(
    r"(try:\s*self\.sym_cb\.event_generate\('<Down>'\)\s*except: pass)",
    r"\1\n        self.root.after(10, lambda: self.sym_cb.focus_set())",
    content
)

# 2. Fix the Spot Simulation UI
spot_sim_ui = """
        mode = self.mode_var.get()
        market = self.market_var.get()
        if mode == "API":
"""
content = content.replace('if mode == "API":', spot_sim_ui, 1)

sim_ui_creation = """
            tk.Label(f, text="เหรียญ (Symbol):", bg="#1e2329", fg="#fff").grid(row=0, column=0, sticky=tk.W, pady=5)
            self.sym_var = tk.StringVar(value=self.cfg_data.get("symbol", "BTCUSDT"))
            self.sym_cb = ttk.Combobox(f, textvariable=self.sym_var, font=("Arial", 10))
            self.sym_cb.grid(row=0, column=1, sticky=tk.EW, pady=5)
            self.sym_cb.bind("<KeyRelease>", self.on_sym_type)
            
            if market == "FUTURES":
                tk.Label(f, text="ราคาเข้า (Entry):", bg="#1e2329", fg="#fff").grid(row=1, column=0, sticky=tk.W, pady=5)
                self.entry_var = tk.DoubleVar(value=self.cfg_data.get("entry", 0.0))
                tk.Entry(f, textvariable=self.entry_var, font=("Arial", 10)).grid(row=1, column=1, sticky=tk.EW, pady=5)
                
                tk.Label(f, text="เงินทุน (Margin):", bg="#1e2329", fg="#fff").grid(row=2, column=0, sticky=tk.W, pady=5)
                self.margin_var = tk.DoubleVar(value=self.cfg_data.get("margin", 100.0))
                tk.Entry(f, textvariable=self.margin_var, font=("Arial", 10)).grid(row=2, column=1, sticky=tk.EW, pady=5)
                
                tk.Label(f, text="Leverage:", bg="#1e2329", fg="#fff").grid(row=3, column=0, sticky=tk.W, pady=5)
                self.lev_var = tk.IntVar(value=self.cfg_data.get("leverage", 20))
                tk.Spinbox(f, from_=1, to=125, textvariable=self.lev_var, font=("Arial", 10)).grid(row=3, column=1, sticky=tk.EW, pady=5)
                
                tk.Label(f, text="ทิศทาง (Side):", bg="#1e2329", fg="#fff").grid(row=4, column=0, sticky=tk.W, pady=5)
                self.side_var = tk.StringVar(value=self.cfg_data.get("side", "Long"))
                ttk.Combobox(f, textvariable=self.side_var, values=["Long", "Short"], state="readonly", font=("Arial", 10)).grid(row=4, column=1, sticky=tk.EW, pady=5)
            else:
                tk.Label(f, text="จำนวนเหรียญ (Amount):", bg="#1e2329", fg="#fff").grid(row=1, column=0, sticky=tk.W, pady=5)
                self.margin_var = tk.DoubleVar(value=self.cfg_data.get("margin", 1.0))
                tk.Entry(f, textvariable=self.margin_var, font=("Arial", 10)).grid(row=1, column=1, sticky=tk.EW, pady=5)
                
                self.entry_var = tk.DoubleVar(value=0.0)
                self.lev_var = tk.IntVar(value=1)
                self.side_var = tk.StringVar(value="Long")
"""
content = re.sub(r'tk\.Label\(f, text="เหรียญ \(Symbol\):".*?ttk\.Combobox\(f, textvariable=self\.side_var, values=\["Long", "Short"\], state="readonly", font=\("Arial", 10\)\)\.grid\(row=4, column=1, sticky=tk\.EW, pady=5\)', sim_ui_creation, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Phase 1 complete.")
