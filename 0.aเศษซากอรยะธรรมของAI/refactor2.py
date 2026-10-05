import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add sys and subprocess
if "import sys" not in content:
    content = content.replace("import os", "import os\nimport sys\nimport subprocess")

# 2. Modify __init__ to accept is_float_mode
init_sig = "def __init__(self, root):"
new_init_sig = "def __init__(self, root, is_float_mode=False, sim_data=None):"
content = content.replace(init_sig, new_init_sig)

init_body_search = """        self.win_bg.withdraw()
        
        self.win_fg = tk.Toplevel(self.root)
        self.win_fg.overrideredirect(True)
        self.win_fg.attributes("-topmost", True)
        self.win_fg.attributes("-transparentcolor", self.trans_key)
        self.win_fg.config(bg=self.trans_key)
        self.win_fg.withdraw()

        self.setup_settings_ui()
        self.setup_floating_ui()

        self.win_bg.bind("<ButtonPress-1>", self.start_drag)
        self.win_bg.bind("<B1-Motion>", self.do_drag)
        self.win_fg.bind("<ButtonPress-1>", self.start_drag)
        self.win_fg.bind("<B1-Motion>", self.do_drag)

        threading.Thread(target=self.fetch_all_symbols, daemon=True).start()
        
        self.show_settings()
        self.update_fallback_loop()"""

new_init_body = """        self.win_bg.withdraw()
        
        self.win_fg = tk.Toplevel(self.root)
        self.win_fg.overrideredirect(True)
        self.win_fg.attributes("-topmost", True)
        self.win_fg.attributes("-transparentcolor", self.trans_key)
        self.win_fg.config(bg=self.trans_key)
        self.win_fg.withdraw()

        if is_float_mode:
            self.active_sim = sim_data
            self.setup_floating_ui()
            self.win_bg.bind("<ButtonPress-1>", self.start_drag)
            self.win_bg.bind("<B1-Motion>", self.do_drag)
            self.win_fg.bind("<ButtonPress-1>", self.start_drag)
            self.win_fg.bind("<B1-Motion>", self.do_drag)
            self.update_fallback_loop()
            self.launch_float_window()
        else:
            self.setup_settings_ui()
            threading.Thread(target=self.fetch_all_symbols, daemon=True).start()
            self.show_settings()"""

content = content.replace(init_body_search, new_init_body)

# 3. Add launch_float_window method
launch_float = """    def launch_float_window(self):
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x, y = int(ws/2 - 350), int(hs/2 - 20)
        self.win_bg.geometry(f"700x45+{x}+{y}")
        self.win_fg.geometry(f"700x45+{x}+{y}")
        self.win_bg.attributes("-alpha", self.active_sim["opacity"])
        
        side_color = "#00bfff" if self.active_sim.get("side", "Long") == "Long" else "#ff9800"
        self.lbl_side_sym.config(text=f"[{self.active_sim.get('side', 'Long')} {self.active_sim['symbol']}]", fg=side_color)
        entry_val = self.active_sim['entry']
        self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")
        self.lbl_live.config(text="Live: Connecting...", fg="#f0b90b")
        self.lbl_pnl.config(text="$0.00 (0.00%)", fg="#ffffff")
        
        self.win_bg.deiconify()
        self.win_fg.deiconify()
        self.win_fg.lift()
        
        self.current_live_price = 0.0
        self.last_ws_msg_time = 0
        threading.Thread(target=lambda: self.start_ws(self.active_sim["market"], self.active_sim["symbol"]), daemon=True).start()
        threading.Thread(target=self.fetch_live_price_rest, daemon=True).start()

    def show_settings(self):"""
content = content.replace("    def show_settings(self):", launch_float, 1)

# 4. Modify start_simulation
start_sim_search = """        self.save_config()
        self.active_sim = self.cfg_data.copy()
        
        
        x, y = self.win_set.winfo_x(), self.win_set.winfo_y()
        # Ensure we don't spawn off-screen if win_set was hidden
        if x < 0 or y < 0:
            ws = self.root.winfo_screenwidth()
            hs = self.root.winfo_screenheight()
            x, y = int(ws/2 - 350), int(hs/2 - 20)
            
        self.win_set.withdraw()
        
        self.win_bg.geometry(f"700x45+{x}+{y}")
        self.win_fg.geometry(f"700x45+{x}+{y}")
        self.win_bg.attributes("-alpha", self.active_sim["opacity"])
        
        side_color = "#00bfff" if self.active_sim["side"] == "Long" else "#ff9800"
        self.lbl_side_sym.config(text=f"[{self.active_sim['side']} {self.active_sim['symbol']}]", fg=side_color)
        entry_val = self.active_sim['entry']
        self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")
        self.lbl_live.config(text="Live: Connecting...", fg="#f0b90b")
        self.lbl_pnl.config(text="$0.00 (0.00%)", fg="#ffffff")
        
        self.win_bg.deiconify()
        self.win_fg.deiconify()
        self.win_fg.lift()
        
        self.current_live_price = 0.0
        self.last_ws_msg_time = 0
        threading.Thread(target=lambda: self.start_ws(self.active_sim["market"], self.active_sim["symbol"]), daemon=True).start()
        
        # แก้บั๊ก Typo Error ตรงนี้ให้ถูกต้อง
        threading.Thread(target=self.fetch_live_price_rest, daemon=True).start()"""

new_start_sim = """        self.save_config()
        self.active_sim = self.cfg_data.copy()
        
        # Spawn subprocess for the floating window!
        import subprocess, sys, json
        sim_json = json.dumps(self.active_sim)
        subprocess.Popen([sys.executable, sys.argv[0], "--float", sim_json])
        
        # Do not close the settings window so they can launch more
        # self.win_set.withdraw()"""
content = content.replace(start_sim_search, new_start_sim)

# 5. Modify main block
main_search = """if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceSimulatorApp(root)
    root.mainloop()"""

new_main = """if __name__ == "__main__":
    import sys
    root = tk.Tk()
    if len(sys.argv) > 2 and sys.argv[1] == "--float":
        import json
        sim_data = json.loads(sys.argv[2])
        app = BinanceSimulatorApp(root, is_float_mode=True, sim_data=sim_data)
    else:
        app = BinanceSimulatorApp(root)
    root.mainloop()"""
content = content.replace(main_search, new_main)

# Fix Spot side label
spot_lbl_search = """        self.lbl_side_sym = tk.Label(f, text="[-]", fg="#00bfff", bg=self.trans_key, font=("Arial", 10, "bold"))
        self.lbl_side_sym.pack(side=tk.LEFT, padx=4)
        
        tk.Label(f, text="|", fg="#444", bg=self.trans_key, font=("Arial", 10)).pack(side=tk.LEFT)
        self.lbl_entry = tk.Label(f, text="Entry: 0.00", fg="#aaaaaa", bg=self.trans_key, font=("Arial", 10))
        self.lbl_entry.pack(side=tk.LEFT, padx=6)"""

spot_lbl_new = """        self.lbl_side_sym = tk.Label(f, text="[-]", fg="#00bfff", bg=self.trans_key, font=("Arial", 10, "bold"))
        self.lbl_side_sym.pack(side=tk.LEFT, padx=4)
        
        self.entry_sep = tk.Label(f, text="|", fg="#444", bg=self.trans_key, font=("Arial", 10))
        self.entry_sep.pack(side=tk.LEFT)
        self.lbl_entry = tk.Label(f, text="Entry: 0.00", fg="#aaaaaa", bg=self.trans_key, font=("Arial", 10))
        self.lbl_entry.pack(side=tk.LEFT, padx=6)"""
content = content.replace(spot_lbl_search, spot_lbl_new)

# And in launch_float_window, hide entry if SPOT
hide_entry = """        side_color = "#00bfff" if self.active_sim.get("side", "Long") == "Long" else "#ff9800"
        self.lbl_side_sym.config(text=f"[{self.active_sim.get('side', 'Long')} {self.active_sim['symbol']}]", fg=side_color)
        entry_val = self.active_sim['entry']
        self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")"""
hide_entry_new = """        if self.active_sim.get("market") == "SPOT":
            self.lbl_side_sym.config(text=f"[Spot {self.active_sim['symbol']}]", fg="#00e676")
            self.lbl_entry.pack_forget()
            self.entry_sep.pack_forget()
        else:
            side_color = "#00bfff" if self.active_sim.get("side", "Long") == "Long" else "#ff9800"
            self.lbl_side_sym.config(text=f"[{self.active_sim.get('side', 'Long')} {self.active_sim['symbol']}]", fg=side_color)
            entry_val = self.active_sim['entry']
            self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")"""
content = content.replace(hide_entry, hide_entry_new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Phase 2 complete.")
