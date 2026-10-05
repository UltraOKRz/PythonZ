import re

file_path = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\โพสิชั่น.pyw"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Clean up __init__ (remove is_float_mode and multiple withdraws)
init_pattern = r"    def __init__\(self, root, is_float_mode=False, sim_data=None\):(.*?)        self\.win_bg = tk\.Toplevel\(self\.root\)"
init_replace = """    def __init__(self, root):
        self.root = root
        self.root.withdraw() # ซ่อนหน้าต่างหลักเพื่อแก้จอดำของ Windows
        
        self.trans_key = "#000001"
        self.markets = ["FUTURES", "SPOT"]
        self.market_symbols = {"binance_SPOT": [], "binance_FUTURES": [], "okx_SPOT": [], "okx_FUTURES": []}
        self.ws = None
        self.ws_keep_running = False
        self.last_ws_msg_time = 0
        self.active_sim = None
        self.current_live_price = 0.0
        self.current_pct_change = 0.0

        # --- Redraw Queue (แก้กราฟไม่ขยับ ให้ดิ้นได้ 60 FPS) ---
        self._full_redraw_pending = False
        self._hover_redraw_pending = False

        # --- Chart Variables ---
        self.chart_view_size = 60
        self.chart_offset = 0
        self.chart_tf_var = None

        self.is_full_chart_open = False
        self.full_chart_win = None
        self.full_chart_data = None
        self.full_kline_close_time = 0
        self.is_fetching_full = False
        
        self.hover_timer = None
        self.hover_chart_win = None
        self.hover_chart_data = None
        self.hover_kline_close_time = 0
        self.is_fetching_hover = False
        
        # --- Axis & Drawing ---
        self.y_zoom = 1.0
        self.y_pan = 0.0
        self._actual_min_p = 0
        self._actual_rng = 1
        self._last_view_times = []
        self.c_pad_r = 75  # Increased from 65 to 75 to fix right-side padding issue
        self.c_pad_b = 25

        self.is_drawing_mode = False
        self.draw_start_point = None 
        self.temp_mouse_pos = None 
        self.selected_line_idx = None
        self.dragging_handle = None 

        self.load_config()
        
        # โครงสร้างหน้าต่าง 3 ชั้น
        self.win_set = tk.Toplevel(self.root)
        self.win_set.title("Binance Position Simulator")
        self.win_set.config(bg="#1e2329")
        self.win_set.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.win_bg = tk.Toplevel(self.root)"""
content = re.sub(init_pattern, init_replace, content, flags=re.DOTALL)


# 2. Fix __init__ bottom (remove if is_float_mode block)
init_bottom_pattern = r"        self\.win_fg\.withdraw\(\)\n\n        if is_float_mode:.*?        self\.show_settings\(\)"
init_bottom_replace = """        self.win_fg.withdraw()

        self.setup_settings_ui()
        self.setup_floating_ui()

        self.win_bg.bind("<ButtonPress-1>", self.start_drag)
        self.win_bg.bind("<B1-Motion>", self.do_drag)
        self.win_fg.bind("<ButtonPress-1>", self.start_drag)
        self.win_fg.bind("<B1-Motion>", self.do_drag)

        threading.Thread(target=self.fetch_all_symbols, daemon=True).start()
        
        self.show_settings()
        self.update_fallback_loop()"""
content = re.sub(init_bottom_pattern, init_bottom_replace, content, flags=re.DOTALL)


# 3. Clean up start_simulation (remove subprocess)
start_sim_pattern = r"        # Spawn subprocess for the floating window!.*?        else:\n            self\.launch_float_window\(\)"
start_sim_replace = """        
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
        
        if self.active_sim.get("market") == "SPOT":
            self.lbl_side_sym.config(text=f"[Spot {self.active_sim['symbol']}]", fg="#00e676")
            self.lbl_entry.pack_forget()
            self.entry_sep.pack_forget()
        else:
            side_color = "#00bfff" if self.active_sim.get("side", "Long") == "Long" else "#ff9800"
            self.lbl_side_sym.config(text=f"[{self.active_sim.get('side', 'Long')} {self.active_sim['symbol']}]", fg=side_color)
            entry_val = self.active_sim['entry']
            self.lbl_entry.config(text=f"Entry: {entry_val:,.4f}" if entry_val < 1 else f"Entry: {entry_val:,.2f}")
            self.lbl_entry.pack(side=tk.LEFT, padx=6)
            self.entry_sep.pack(side=tk.LEFT)
            
        self.lbl_live.config(text="Live: Connecting...", fg="#f0b90b")
        self.lbl_pnl.config(text="$0.00 (0.00%)", fg="#ffffff")
        
        self.win_bg.deiconify()
        self.win_fg.deiconify()
        self.win_fg.lift()
        
        self.current_live_price = 0.0
        self.last_ws_msg_time = 0
        threading.Thread(target=lambda: self.start_ws(self.active_sim["market"], self.active_sim["symbol"]), daemon=True).start()
        threading.Thread(target=self.fetch_live_price_rest, daemon=True).start()"""
content = re.sub(start_sim_pattern, start_sim_replace, content, flags=re.DOTALL)


# 4. Remove launch_float_window completely
content = re.sub(r"    def launch_float_window\(self\):.*?    def show_settings\(self\):", "    def show_settings(self):", content, flags=re.DOTALL)

# 5. Fix setup_floating_ui (restore gear icon and close_widget logic)
setup_floating_pattern = r"        tk\.Button\(f, text=\"✖\", command=self\.close_widget.*?\)\.pack\(side=tk\.RIGHT, padx=4\)"
setup_floating_replace = """        tk.Button(f, text="✖", command=self.close_widget, bg=self.trans_key, fg="#ff3d57", bd=0, font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(2, 4))
        tk.Button(f, text="⚙", command=self.show_settings, bg=self.trans_key, fg="#aaa", bd=0, font=("Arial", 10), cursor="hand2").pack(side=tk.RIGHT, padx=4)"""
content = re.sub(setup_floating_pattern, setup_floating_replace, content, flags=re.DOTALL)

# 6. Restore close_widget (no sys.exit, instead just call show_settings)
close_widget_pattern = r"    def close_widget\(self\):.*?        if getattr\(self, 'is_float_mode', False\):\n            self\.root\.destroy\(\)\n            import sys\n            sys\.exit\(0\)"
close_widget_replace = """    def close_widget(self):
        self.ws_keep_running = False
        if self.ws:
            try: self.ws.close()
            except: pass
        self.win_bg.withdraw()
        self.win_fg.withdraw()
        self.close_full_chart()
        self.close_hover_chart()
        self.show_settings()"""
content = re.sub(close_widget_pattern, close_widget_replace, content, flags=re.DOTALL)

# 7. Restore __main__
main_pattern = r"if __name__ == \"__main__\":\n    import sys\n    root = tk\.Tk\(\)\n    if len\(sys\.argv\) > 2 and sys\.argv\[1\] == \"--float\":.*?\n    root\.mainloop\(\)"
main_replace = """if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceSimulatorApp(root)
    root.mainloop()"""
content = re.sub(main_pattern, main_replace, content, flags=re.DOTALL)

# 8. Fix hover preview TF
hover_pattern = r"res = requests\.get\(f\"{endpoint}\?symbol=\{self\.active_sim\['symbol'\]\}&interval=1m&limit=100\", headers=headers, timeout=3\)"
hover_replace = """current_tf = self.cfg_data.get("chart_tf", "1m")
            res = requests.get(f"{endpoint}?symbol={self.active_sim['symbol']}&interval={current_tf}&limit=100", headers=headers, timeout=3)"""
content = re.sub(hover_pattern, hover_replace, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Restore applied.")
