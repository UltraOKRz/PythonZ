import tkinter as tk
from tkinter import ttk
import websocket
import json
import threading
import time
import os
import sys
import subprocess
import requests
import ssl
import math
import bisect
import hmac
import hashlib
import base64
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_config.json")

class BinanceSimulatorApp:
    def __init__(self, root):
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
        self.display_currency = "USDT"
        self.usdt_thb_rate = 34.00

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
        
        self.win_bg = tk.Toplevel(self.root)
        self.win_bg.overrideredirect(True)
        self.win_bg.attributes("-topmost", True)
        self.win_bg.config(bg="#121418", highlightbackground="#444", highlightthickness=1)
        self.win_bg.withdraw()
        
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

        try:
            self.win_fg.transient(self.win_bg)
        except: pass

        threading.Thread(target=self.fetch_all_symbols, daemon=True).start()
        threading.Thread(target=self.fetch_usdt_thb, daemon=True).start()
        
        self.show_settings()
        self.update_fallback_loop()


    def fetch_usdt_thb(self):
        import time, requests
        while True:
            try:
                res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=USDTTHB", timeout=5)
                if res.status_code == 200:
                    self.usdt_thb_rate = float(res.json()["price"])
            except: pass
            time.sleep(60)

    def on_closing(self):
        self.ws_keep_running = False
        self.save_config()
        self.root.destroy()

    def load_config(self):
        default_config = {
            "market": "FUTURES", "symbol": "BTCUSDT", "entry": 0.0, 
            "margin": 100.0, "leverage": 20, "side": "Long", "opacity": 0.85,
            "chart_tf": "1m", "saved_lines": {},
            "api_keys": {
                "binance": {"key": "", "secret": "", "passphrase": ""},
                "okx": {"key": "", "secret": "", "passphrase": ""}
            },
            "active_exchange": "binance"
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.cfg_data = {**default_config, **cfg}
                    if "api_keys" not in self.cfg_data: self.cfg_data["api_keys"] = default_config["api_keys"]
                    if "saved_lines" not in self.cfg_data: self.cfg_data["saved_lines"] = {}
            except: self.cfg_data = default_config
        else: self.cfg_data = default_config

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: 
                json.dump(self.cfg_data, f, indent=4, ensure_ascii=False)
        except: pass

    def get_colors(self): return "#00e676", "#ff3d57"

    # ==========================================
    # 1. UI Settings & Floating
    # ==========================================
    def show_settings(self):
        self.active_sim = None
        self.ws_keep_running = False
        if self.ws:
            try: self.ws.close()
            except: pass
        self.close_full_chart()
        self.close_hover_chart()
            
        self.win_bg.withdraw()
        self.win_fg.withdraw()
        
        # Do not use root position since it's withdrawn (can be off-screen).
        # Center the window on screen instead.
        self.root.update_idletasks()
        w = 450
        h = 550
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.win_set.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.win_set.deiconify()

    def start_simulation(self):
        mode = getattr(self, 'mode_var', None)
        mode_val = mode.get() if mode else "SIM"
        if mode_val == "SIM":
            self.cfg_data["market"] = self.market_var.get()
            self.cfg_data["symbol"] = self.sym_var.get().upper().strip()
            self.cfg_data["entry"] = self.entry_var.get()
            self.cfg_data["margin"] = self.margin_var.get()
            self.cfg_data["leverage"] = self.lev_var.get()
            self.cfg_data["side"] = self.side_var.get()
        else:
            if not hasattr(self, 'pos_listbox') or not self.pos_listbox.curselection():
                return 
                
            idx = self.pos_listbox.curselection()[0]
            data = self.api_fetched_data[idx]
            market = self.market_var.get()
            
            self.cfg_data["market"] = market
            if market == "FUTURES":
                self.cfg_data["symbol"] = data["symbol"]
                self.cfg_data["entry"] = data["entry"]
                self.cfg_data["side"] = data["side"]
                lev = float(data["raw"].get("leverage", data["raw"].get("lever", 1)))
                self.cfg_data["leverage"] = lev
                qty = data["amt"]
                margin = (data["entry"] * qty) / lev if lev > 0 else 0
                self.cfg_data["margin"] = margin
            else:
                sym = data["symbol"]
                if sym != "USDT" and not sym.endswith("USDT"): sym += "USDT"
                self.cfg_data["symbol"] = sym
                
                dca = self.cfg_data.get("spot_dca", {}).get(sym, [])
                if dca:
                    total_amt = sum(x["a"] for x in dca)
                    avg_p = sum(x["p"] * x["a"] for x in dca) / total_amt if total_amt > 0 else 0
                    self.cfg_data["entry"] = avg_p
                    if mode_val != "API": self.cfg_data["margin"] = total_amt
                    else: self.cfg_data["margin"] = data["amt"]
                else:
                    self.cfg_data["entry"] = 0
                    self.cfg_data["margin"] = data["amt"]
                
                self.cfg_data["side"] = "Long"
                self.cfg_data["leverage"] = 1
                
        self.cfg_data["mode"] = mode_val
                
        self.ws_keep_running = False
        if self.ws:
            try: self.ws.close()
            except: pass
            
        self.save_config()
        self.active_sim = self.cfg_data.copy()
        
        
        x, y = self.win_set.winfo_x(), self.win_set.winfo_y()
        # Ensure we don't spawn off-screen if win_set was hidden
        if x < 0 or y < 0:
            ws = self.root.winfo_screenwidth()
            hs = self.root.winfo_screenheight()
            x, y = int(ws/2 - 350), int(hs/2 - 20)
            
        self.win_set.withdraw()
        
        if not hasattr(self, 'current_width'): self.current_width = 480
        self.win_bg.geometry(f"{self.current_width}x45+{x}+{y}")
        self.win_fg.geometry(f"{self.current_width}x45+{x}+{y}")
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
            self.lbl_margin.pack(side=tk.LEFT)
            
        self.lbl_live.config(text="Live: Connecting...", fg="#f0b90b")
        self.lbl_pnl.config(text="$0.00 (0.00%)", fg="#ffffff")
        
        self.win_bg.deiconify()
        self.win_fg.deiconify()
        self.win_fg.lift()
        
        self.current_live_price = 0.0
        self.last_ws_msg_time = 0
        threading.Thread(target=lambda: self.start_ws(self.active_sim["market"], self.active_sim["symbol"]), daemon=True).start()
        threading.Thread(target=self.fetch_live_price_rest, daemon=True).start()

    def setup_settings_ui(self):
        self.win_set.geometry("450x550")
        self.win_set.title("Connect API")
        
        self.step_container = tk.Frame(self.win_set, bg="#1e2329")
        self.step_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.show_step_1_exchange_selection()

    def clear_step_container(self):
        for widget in self.step_container.winfo_children(): widget.destroy()

    def show_step_1_exchange_selection(self):
        self.clear_step_container()
        tk.Label(self.step_container, text="1. เลือก Exchange ที่ต้องการเชื่อมต่อ", bg="#1e2329", fg="#f0b90b", font=("Arial", 12, "bold")).pack(pady=(0, 20))
        
        tk.Button(self.step_container, text="Binance", font=("Arial", 14, "bold"), bg="#f3ba2f", fg="#000", height=2, cursor="hand2", command=lambda: self.show_step_2_api_input("binance")).pack(fill=tk.X, pady=10)
        tk.Button(self.step_container, text="OKX", font=("Arial", 14, "bold"), bg="#ffffff", fg="#000", height=2, cursor="hand2", command=lambda: self.show_step_2_api_input("okx")).pack(fill=tk.X, pady=10)

    def show_step_2_api_input(self, exchange):
        self.cfg_data["active_exchange"] = exchange
        self.save_config()
        self.clear_step_container()
        
        exch_name = "Binance" if exchange == "binance" else "OKX"
        tk.Label(self.step_container, text=f"2. กรอก API Key ของ {exch_name}", bg="#1e2329", fg="#f0b90b", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        tip_text = "ไปที่ Profile -> API Management -> Create API\nเลือก Read-only และ Enable Futures" if exchange == "binance" else "ไปที่ Profile -> API -> Create V5 API\nเลือกสิทธิ์ Read และต้องกรอก Passphrase"
        tk.Label(self.step_container, text=tip_text, bg="#1e2329", fg="#00bfff", font=("Arial", 9), justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 15))
        
        keys = self.cfg_data.get("api_keys", {}).get(exchange, {})
        
        tk.Label(self.step_container, text="API Key:", bg="#1e2329", fg="#fff").pack(anchor=tk.W)
        self.api_key_var = tk.StringVar(value=keys.get("key", ""))
        tk.Entry(self.step_container, textvariable=self.api_key_var, font=("Arial", 10), width=40).pack(pady=(0, 10))
        
        tk.Label(self.step_container, text="API Secret:", bg="#1e2329", fg="#fff").pack(anchor=tk.W)
        self.api_secret_var = tk.StringVar(value=keys.get("secret", ""))
        tk.Entry(self.step_container, textvariable=self.api_secret_var, font=("Arial", 10), width=40, show="*").pack(pady=(0, 10))
        
        if exchange == "okx":
            tk.Label(self.step_container, text="Passphrase:", bg="#1e2329", fg="#fff").pack(anchor=tk.W)
            self.api_pass_var = tk.StringVar(value=keys.get("passphrase", ""))
            tk.Entry(self.step_container, textvariable=self.api_pass_var, font=("Arial", 10), width=40, show="*").pack(pady=(0, 10))
            
        btn_frame = tk.Frame(self.step_container, bg="#1e2329")
        btn_frame.pack(pady=20, fill=tk.X)
        tk.Button(btn_frame, text="< กลับ", command=self.show_step_1_exchange_selection, bg="#444", fg="#fff", width=10, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(btn_frame, text="บันทึก & ถัดไป >", command=lambda: self.connect_and_fetch(exchange), bg="#00bfff", fg="#000", font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(10, 0))

    def connect_and_fetch(self, exchange):
        self.cfg_data["api_keys"][exchange]["key"] = self.api_key_var.get().strip()
        self.cfg_data["api_keys"][exchange]["secret"] = self.api_secret_var.get().strip()
        if exchange == "okx": self.cfg_data["api_keys"][exchange]["passphrase"] = self.api_pass_var.get().strip()
        self.save_config()
        self.show_step_3_position_selection()

    def show_step_3_position_selection(self):
        self.clear_step_container()
        tk.Label(self.step_container, text="3. เลือกข้อมูลที่ต้องการแสดง", bg="#1e2329", fg="#f0b90b", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        self.market_var = tk.StringVar(value=self.cfg_data.get("market", "FUTURES"))
        self.mode_var = tk.StringVar(value="API")
        
        f_top = tk.Frame(self.step_container, bg="#1e2329")
        f_top.pack(fill=tk.X, pady=5)
        
        tk.Radiobutton(f_top, text="Futures", variable=self.market_var, value="FUTURES", bg="#1e2329", fg="#fff", selectcolor="#000", command=self.refresh_step_3_view).pack(side=tk.LEFT)
        tk.Radiobutton(f_top, text="Spot", variable=self.market_var, value="SPOT", bg="#1e2329", fg="#fff", selectcolor="#000", command=self.refresh_step_3_view).pack(side=tk.LEFT, padx=10)
        
        tk.Label(f_top, text="|", bg="#1e2329", fg="#555").pack(side=tk.LEFT, padx=10)
        
        tk.Radiobutton(f_top, text="ดึงจาก API", variable=self.mode_var, value="API", bg="#1e2329", fg="#00bfff", selectcolor="#000", command=self.refresh_step_3_view).pack(side=tk.LEFT)
        tk.Radiobutton(f_top, text="จำลอง (Sim)", variable=self.mode_var, value="SIM", bg="#1e2329", fg="#ff9800", selectcolor="#000", command=self.refresh_step_3_view).pack(side=tk.LEFT)

        self.dynamic_frame = tk.Frame(self.step_container, bg="#1e2329")
        self.dynamic_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        f_bottom = tk.Frame(self.step_container, bg="#1e2329")
        f_bottom.pack(fill=tk.X, pady=10, side=tk.BOTTOM)
        
        tk.Label(f_bottom, text="ความโปร่งใส (Opacity):", bg="#1e2329", fg="#fff", font=("Arial", 9)).pack(anchor=tk.W)
        self.op_slider = tk.Scale(f_bottom, from_=10, to=100, orient=tk.HORIZONTAL, bg="#1e2329", fg="#ffffff", highlightthickness=0, command=self.on_opacity_change)
        self.op_slider.set(int(self.cfg_data.get("opacity", 0.85) * 100))
        self.op_slider.pack(fill=tk.X, pady=(0, 10))

        btn_frame = tk.Frame(f_bottom, bg="#1e2329")
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="< กลับ", command=lambda: self.show_step_2_api_input(self.cfg_data["active_exchange"]), bg="#444", fg="#fff", width=10, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(btn_frame, text="เริ่มกราฟ >", command=self.start_simulation, bg="#8a2be2", fg="white", font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(10, 0))
        
        self.refresh_step_3_view()

    def refresh_step_3_view(self):
        for w in self.dynamic_frame.winfo_children(): w.destroy()
        
        mode = self.mode_var.get()
        
        mode = self.mode_var.get()
        market = self.market_var.get()
        if mode == "API":

            self.pos_listbox = tk.Listbox(self.dynamic_frame, bg="#121418", fg="#00e676", font=("Arial", 10), selectbackground="#00bfff", activestyle="none", highlightthickness=0)
            self.pos_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
            self.lbl_api_status = tk.Label(self.dynamic_frame, text="รอเชื่อมต่อ API...", bg="#1e2329", fg="#aaa")
            self.lbl_api_status.pack()
            self.fetch_api_positions()
        else:
            f = tk.Frame(self.dynamic_frame, bg="#1e2329")
            f.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            
            tk.Label(f, text="เหรียญ (Symbol):", bg="#1e2329", fg="#fff").grid(row=0, column=0, sticky=tk.W, pady=5)
            self.sym_var = tk.StringVar(value=self.cfg_data.get("symbol", "BTCUSDT"))
            self.sym_cb = ttk.Combobox(f, textvariable=self.sym_var, font=("Arial", 10))
            self.sym_cb.grid(row=0, column=1, sticky=tk.EW, pady=5)
            self.sym_cb.bind("<KeyRelease>", self.on_sym_type)
            
            if market == "FUTURES":
                tk.Label(f, text="ราคาเข้า (Entry):", bg="#1e2329", fg="#fff").grid(row=1, column=0, sticky=tk.W, pady=5)
                entry_f = tk.Frame(f, bg="#1e2329")
                entry_f.grid(row=1, column=1, sticky=tk.EW, pady=5)
                self.entry_var = tk.DoubleVar(value=self.cfg_data.get("entry", 0.0))
                tk.Entry(entry_f, textvariable=self.entry_var, font=("Arial", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Button(entry_f, text="ดึงราคาล่าสุด", command=self.fetch_live_entry_price, bg="#444", fg="#00bfff", font=("Arial", 8), cursor="hand2", bd=0, padx=4).pack(side=tk.RIGHT, padx=(4,0))
                
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
                tk.Button(f, text="➕ จัดการประวัติซื้อ (Spot DCA)", font=("Arial", 10, "bold"), bg="#00bfff", fg="#000", cursor="hand2", command=self.open_dca_manager).grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=10)
                
                tk.Label(f, text="จำนวนเหรียญรวม (Sim):", bg="#1e2329", fg="#fff").grid(row=2, column=0, sticky=tk.W, pady=5)
                self.margin_var = tk.DoubleVar(value=self.cfg_data.get("margin", 1.0))
                tk.Entry(f, textvariable=self.margin_var, font=("Arial", 10), state="disabled").grid(row=2, column=1, sticky=tk.EW, pady=5)
                
                self.entry_var = tk.DoubleVar(value=0.0)
                self.lev_var = tk.IntVar(value=1)
                self.side_var = tk.StringVar(value="Long")

            
            f.columnconfigure(1, weight=1)
            
            exchange = self.cfg_data.get("active_exchange", "binance")
            market = self.market_var.get()
            key = f"{exchange}_{market}"
            self._current_sim_symbols = self.market_symbols.get(key, [])
            if self._current_sim_symbols:
                self.sym_cb.config(values=self._current_sim_symbols)

    def fetch_live_entry_price(self):
        def _fetch():
            symbol = self.sym_var.get().strip().upper()
            if not symbol: return
            market = self.market_var.get()
            exchange = self.cfg_data.get("active_exchange", "binance")
            try:
                if exchange == "binance":
                    url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}" if market == "FUTURES" else f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                    res = requests.get(url, timeout=3).json()
                    if "price" in res:
                        self.root.after(0, lambda: self.entry_var.set(float(res["price"])))
                elif exchange == "okx":
                    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
                    res = requests.get(url, timeout=3).json()
                    if "data" in res and len(res["data"]) > 0:
                        self.root.after(0, lambda: self.entry_var.set(float(res["data"][0]["last"])))
            except: pass
        threading.Thread(target=_fetch, daemon=True).start()


    def open_dca_manager(self, target_sym=None):
        sym = target_sym if target_sym else self.sym_var.get().strip().upper()
        if not sym:
            return
            
        win = tk.Toplevel(self.root)
        win.title(f"Spot DCA Manager: {sym}")
        win.geometry("400x460")
        win.config(bg="#121418")
        win.attributes("-topmost", True)
        
        tk.Label(win, text=f"จัดการประวัติซื้อ (DCA) - {sym}", bg="#121418", fg="#f0b90b", font=("Arial", 12, "bold")).pack(pady=10)
        
        f_input = tk.Frame(win, bg="#121418")
        f_input.pack(fill=tk.X, padx=20)
        
        tk.Label(f_input, text="ราคา (Price):", bg="#121418", fg="#fff").grid(row=0, column=0, sticky=tk.W, pady=2)
        p_var = tk.DoubleVar(value=0.0)
        tk.Entry(f_input, textvariable=p_var, width=15).grid(row=0, column=1, padx=5)
        
        tk.Label(f_input, text="จำนวน (Amount):", bg="#121418", fg="#fff").grid(row=1, column=0, sticky=tk.W, pady=2)
        a_var = tk.DoubleVar(value=0.0)
        tk.Entry(f_input, textvariable=a_var, width=15).grid(row=1, column=1, padx=5)
        
        lb_frame = tk.Frame(win, bg="#121418")
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        lb = tk.Listbox(lb_frame, bg="#1e2329", fg="#00e676", font=("Arial", 10), selectbackground="#444")
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lb_frame, command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.config(yscrollcommand=sb.set)
        
        lbl_summary = tk.Label(win, text="", bg="#121418", fg="#00bfff", font=("Arial", 10, "bold"))
        lbl_summary.pack(pady=5)
        
        if "spot_dca" not in self.cfg_data: self.cfg_data["spot_dca"] = {}
        if sym not in self.cfg_data["spot_dca"]: self.cfg_data["spot_dca"][sym] = []
        dca_list = self.cfg_data["spot_dca"][sym]
        
        def refresh_list():
            lb.delete(0, tk.END)
            total_amt = 0.0
            total_cost = 0.0
            for i, d in enumerate(dca_list):
                p = d["p"]
                a = d["a"]
                total_amt += a
                total_cost += p * a
                lb.insert(tk.END, f"#{i+1} | ราคา {p:,.4f} | จำนวน {a:g}")
            
            avg = total_cost / total_amt if total_amt > 0 else 0
            lbl_summary.config(text=f"รวม: {total_amt:g} | ต้นทุนเฉลี่ย: {avg:,.4f}")
            self.save_config()
            
            if self.market_var.get() == "SPOT" and not getattr(self, "is_fetching_api", False):
                self.margin_var.set(total_amt)
                
            if getattr(self, "active_sim", None) and self.active_sim.get("symbol") == sym and self.active_sim.get("market") == "SPOT":
                self.active_sim["entry"] = avg
                if self.active_sim.get("mode") != "API":
                    self.active_sim["margin"] = total_amt
                
                # Update UI immediately
                if avg > 0:
                    self.lbl_entry.config(text=f"Avg: {avg:,.4f}" if avg < 1 else f"Avg: {avg:,.2f}")
                    self.lbl_entry.pack(side=tk.LEFT)
                    self.sep_live.pack(side=tk.LEFT)
                else:
                    self.lbl_entry.pack_forget()
                    self.sep_live.pack_forget()
                
                # Update Size too!
                self.lbl_size.config(text=f"Size: {total_amt:g} {self.active_sim['symbol'].replace('USDT','')}")
                    
                self.request_chart_redraw("full")
                self.request_chart_redraw("hover")

        def fetch_latest_price():
            if getattr(self, "active_sim", None) and self.active_sim.get("symbol") == sym and getattr(self, "current_live_price", 0) > 0:
                p_var.set(round(self.current_live_price, 8))
                btn_fetch.config(text="✓ สำเร็จ", bg="#00e676", fg="#000")
                win.after(1000, lambda: btn_fetch.config(text="⚡ ดึงราคาล่าสุด", bg="#2b313a", fg="#00bfff") if win.winfo_exists() else None)
                return

            def _worker():
                try:
                    btn_fetch.config(text="กำลังดึง...", state=tk.DISABLED)
                    res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=4)
                    if res.status_code == 200:
                        p = float(res.json()["price"])
                        p_var.set(round(p, 8))
                        if win.winfo_exists():
                            btn_fetch.config(text="✓ สำเร็จ", bg="#00e676", fg="#000", state=tk.NORMAL)
                            win.after(1000, lambda: btn_fetch.config(text="⚡ ดึงราคาล่าสุด", bg="#2b313a", fg="#00bfff") if win.winfo_exists() else None)
                    else:
                        if win.winfo_exists():
                            btn_fetch.config(text="❌ ไม่พบราคา", bg="#ff3d57", fg="#fff", state=tk.NORMAL)
                            win.after(1500, lambda: btn_fetch.config(text="⚡ ดึงราคาล่าสุด", bg="#2b313a", fg="#00bfff") if win.winfo_exists() else None)
                except Exception:
                    if win.winfo_exists():
                        btn_fetch.config(text="❌ ผิดพลาด", bg="#ff3d57", fg="#fff", state=tk.NORMAL)
                        win.after(1500, lambda: btn_fetch.config(text="⚡ ดึงราคาล่าสุด", bg="#2b313a", fg="#00bfff") if win.winfo_exists() else None)

            threading.Thread(target=_worker, daemon=True).start()

        def add_record():
            try:
                p = float(p_var.get())
                a = float(a_var.get())
                if p > 0 and a > 0:
                    dca_list.append({"p": p, "a": a, "t": int(time.time() * 1000)})
                    p_var.set(0.0)
                    a_var.set(0.0)
                    refresh_list()
            except: pass
            
        def del_record():
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                dca_list.pop(idx)
                refresh_list()
                
        def clear_all():
            dca_list.clear()
            refresh_list()
            
        btn_fetch = tk.Button(f_input, text="⚡ ดึงราคาล่าสุด", bg="#2b313a", fg="#00bfff", font=("Arial", 8, "bold"), command=fetch_latest_price, cursor="hand2")
        btn_fetch.grid(row=0, column=2, sticky=tk.NSEW, padx=5, pady=2)

        tk.Button(f_input, text="➕ เพิ่ม (Add)", bg="#00e676", fg="#000", font=("Arial", 9, "bold"), command=add_record, cursor="hand2").grid(row=1, column=2, sticky=tk.NSEW, padx=5, pady=2)
        
        btn_f = tk.Frame(win, bg="#121418")
        btn_f.pack(fill=tk.X, padx=20, pady=(0, 20))
        tk.Button(btn_f, text="ลบรายการที่เลือก", bg="#ff9800", fg="#000", command=del_record).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
        tk.Button(btn_f, text="🗑️ ล้างประวัติทั้งหมด", bg="#ff3d57", fg="#fff", command=clear_all).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5,0))
        
        refresh_list()

    def on_sym_type(self, event):
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Escape'): return
        val = self.sym_var.get().upper()
        if not hasattr(self, '_current_sim_symbols'): return
        
        if val == "":
            self.sym_cb.config(values=self._current_sim_symbols)
        else:
            filtered = [s for s in self._current_sim_symbols if val in s]
            self.sym_cb.config(values=filtered)
            
        try:
            self.sym_cb.event_generate('<Down>')
        except: pass
        self.root.after(10, lambda: self.sym_cb.focus_set())

    def fetch_api_positions(self):
        self.pos_listbox.delete(0, tk.END)
        self.lbl_api_status.config(text="กำลังดึงข้อมูล... กรุณารอสักครู่", fg="#aaa")
        threading.Thread(target=self._fetch_api_thread, daemon=True).start()

    def _fetch_api_thread(self):
        market = self.market_var.get()
        exchange = self.cfg_data["active_exchange"]
        keys = self.cfg_data.get("api_keys", {}).get(exchange, {})
        api_key = keys.get("key", "")
        api_secret = keys.get("secret", "")
        api_pass = keys.get("passphrase", "")
        
        if not api_key or not api_secret:
            self.root.after_idle(lambda: self.lbl_api_status.config(text="❌ กรุณากรอก API Key และ Secret ก่อน", fg="#ff3d57"))
            return

        try:
            results = []
            if exchange == "binance":
                ts = int(time.time() * 1000)
                qs = f"timestamp={ts}&recvWindow=10000"
                sig = hmac.new(api_secret.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
                headers = {'X-MBX-APIKEY': api_key}
                
                if market == "FUTURES":
                    res = requests.get(f"https://fapi.binance.com/fapi/v2/positionRisk?{qs}&signature={sig}", headers=headers, timeout=10)
                    if res.status_code == 200:
                        for p in res.json():
                            amt = float(p.get("positionAmt", 0))
                            if amt != 0:
                                results.append({"symbol": p["symbol"], "side": "Long" if amt > 0 else "Short", "amt": abs(amt), "entry": float(p["entryPrice"]), "pnl": float(p["unRealizedProfit"]), "raw": p})
                    else: raise Exception(res.text)
                else: 
                    res = requests.get(f"https://api.binance.com/api/v3/account?{qs}&signature={sig}", headers=headers, timeout=10)
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
                                    "wallet": "Earn" if is_earn else "Spot",
                                    "raw": b
                                })
                    else: raise Exception(res.text)
                    
                    # ดึงจาก Funding Wallet ด้วยเพื่อความครบถ้วน (เช่น USDC)
                    try:
                        res_f = requests.post(f"https://api.binance.com/sapi/v1/asset/get-funding-asset?{qs}&signature={sig}", headers=headers, timeout=5)
                        if res_f.status_code == 200 and isinstance(res_f.json(), list):
                            for fa in res_f.json():
                                free_f = float(fa.get("free", 0))
                                if free_f > 0:
                                    results.append({
                                        "symbol": fa["asset"],
                                        "raw_symbol": fa["asset"],
                                        "amt": free_f,
                                        "wallet": "Funding",
                                        "raw": fa
                                    })
                    except: pass
                        
            elif exchange == "okx":
                timestamp = datetime.utcnow().isoformat()[:-3] + "Z"
                if market == "FUTURES":
                    path = "/api/v5/account/positions"
                    sig = base64.b64encode(hmac.new(api_secret.encode('utf-8'), (timestamp + "GET" + path).encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                    headers = {"OK-ACCESS-KEY": api_key, "OK-ACCESS-SIGN": sig, "OK-ACCESS-TIMESTAMP": timestamp, "OK-ACCESS-PASSPHRASE": api_pass}
                    res = requests.get(f"https://www.okx.com{path}", headers=headers, timeout=10)
                    if res.status_code == 200 and res.json()["code"] == "0":
                        for p in res.json()["data"]:
                            amt = float(p.get("pos", 0))
                            if amt != 0:
                                results.append({"symbol": p["instId"].replace("-SWAP", "").replace("-", ""), "side": "Long" if p["posSide"] == "long" else "Short", "amt": abs(amt), "entry": float(p["avgPx"]), "pnl": float(p["upl"]), "raw": p})
                    else: raise Exception(res.text)
                else:
                    path = "/api/v5/account/balance"
                    sig = base64.b64encode(hmac.new(api_secret.encode('utf-8'), (timestamp + "GET" + path).encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                    headers = {"OK-ACCESS-KEY": api_key, "OK-ACCESS-SIGN": sig, "OK-ACCESS-TIMESTAMP": timestamp, "OK-ACCESS-PASSPHRASE": api_pass}
                    res = requests.get(f"https://www.okx.com{path}", headers=headers, timeout=10)
                    if res.status_code == 200 and res.json()["code"] == "0" and res.json()["data"]:
                        for b in res.json()["data"][0]["details"]:
                            avail = float(b["availBal"])
                            if avail > 0: results.append({"symbol": b["ccy"], "amt": avail, "raw": b})
                    else: raise Exception(res.text)

            self.api_fetched_data = results
            self.root.after_idle(self._update_pos_listbox)
        except Exception as e:
            self.root.after_idle(lambda: self.lbl_api_status.config(text=f"❌ Error: {str(e)[:50]}", fg="#ff3d57"))

    def _update_pos_listbox(self):
        self.pos_listbox.delete(0, tk.END)
        market = self.market_var.get()
        if not getattr(self, 'api_fetched_data', None):
            self.lbl_api_status.config(text="✓ ไม่พบข้อมูล (ว่างเปล่า)", fg="#00e676")
            return
            
        for d in self.api_fetched_data:
            if market == "FUTURES":
                sign = "+" if d['pnl'] >= 0 else ""
                self.pos_listbox.insert(tk.END, f"{d['symbol']} | {d['side']} {d['amt']:,.4f} | Entry {d['entry']:,.4f} | PNL {sign}${d['pnl']:,.2f}")
            else:
                wallet_tag = f" ({d['wallet']})" if d.get('wallet') and d.get('wallet') != 'Spot' else ""
                amt_val = d['amt']
                amt_str = f"{amt_val:.8f}".rstrip('0').rstrip('.') if amt_val < 0.0001 else f"{amt_val:,.4f}"
                dca = self.cfg_data.get("spot_dca", {}).get(d['symbol'], [])
                if dca:
                    total_amt = sum(x["a"] for x in dca)
                    avg_p = sum(x["p"] * x["a"] for x in dca) / total_amt if total_amt > 0 else 0
                    self.pos_listbox.insert(tk.END, f"{d['symbol']}{wallet_tag} | Bal {amt_str} | Avg Entry {avg_p:,.4f}")
                else:
                    self.pos_listbox.insert(tk.END, f"{d['symbol']}{wallet_tag} | Bal {amt_str}")
        
        self.lbl_api_status.config(text=f"✓ ดึงข้อมูลสำเร็จ ({len(self.api_fetched_data)} รายการ)", fg="#00e676")
        if self.pos_listbox.size() > 0: self.pos_listbox.select_set(0)

    def on_opacity_change(self, val):
        self.cfg_data["opacity"] = float(val) / 100.0
        if self.active_sim: self.win_bg.attributes("-alpha", self.cfg_data["opacity"])

    def setup_floating_ui(self):
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
        
        self.btn_currency = tk.Button(f_right, text="THB", command=self.toggle_currency, bg="#ff9800", fg="#000", bd=0, font=("Arial", 9, "bold"), cursor="hand2")
        self.btn_currency.pack(side=tk.RIGHT, padx=4)
        
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
        self.grip_lbl.bind("<B1-Motion>", self.do_resize)


    def toggle_currency(self):
        if self.display_currency == "USDT":
            self.display_currency = "THB"
            self.btn_currency.config(text="USDT", bg="#00bfff", fg="#fff")
        else:
            self.display_currency = "USDT"
            self.btn_currency.config(text="THB", bg="#ff9800", fg="#000")
        self.update_sim_ui(self.current_live_price, self.current_pct_change)

    def start_drag(self, event):
        self.win_fg.lift()
        self._drag_start_x, self._drag_start_y = event.x_root, event.y_root
        self._start_x, self._start_y = self.win_bg.winfo_x(), self.win_bg.winfo_y()

    def do_drag(self, event):
        new_x = self._start_x + (event.x_root - self._drag_start_x)
        new_y = self._start_y + (event.y_root - self._drag_start_y)
        self.win_bg.geometry(f"+{new_x}+{new_y}")
        self.win_fg.geometry(f"+{new_x}+{new_y}")

    def start_resize(self, event):
        self._resize_start_x = event.x_root
        self._start_w = self.win_bg.winfo_width()

    def do_resize(self, event):
        new_w = max(400, self._start_w + (event.x_root - self._resize_start_x))
        self.current_width = new_w
        self.win_bg.geometry(f"{new_w}x45")
        self.win_fg.geometry(f"{new_w}x45")

    # ==========================================
    # 2. UNIFIED CHART RENDERER (กราฟดิ้นสดๆ & Auto High/Low)
    # ==========================================
    def request_chart_redraw(self, target="full"):
        # ใช้ Event Queue เพื่อป้องกันเฟรมดรอปและอัปเดตแบบ 60FPS
        if target == "full" and self.is_full_chart_open:
            if not self._full_redraw_pending:
                self._full_redraw_pending = True
                self.root.after(16, self._execute_full_redraw) 
        elif target == "hover" and self.hover_chart_win:
            if not self._hover_redraw_pending:
                self._hover_redraw_pending = True
                self.root.after(16, self._execute_hover_redraw)

    def _execute_full_redraw(self):
        self._full_redraw_pending = False
        self.render_candlesticks(self.canvas, self.full_chart_data, self.full_kline_close_time, is_hover=False)

    def _execute_hover_redraw(self):
        self._hover_redraw_pending = False
        self.render_candlesticks(self.hover_canvas, self.hover_chart_data, self.hover_kline_close_time, is_hover=True)

    def render_candlesticks(self, canvas, data_dict, kline_close_time, is_hover=False):
        if not canvas or not canvas.winfo_exists() or not data_dict: return
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 50: return
        inner_w, inner_h = w - self.c_pad_r, h - self.c_pad_b
            
        times, opens, highs = data_dict['times'], data_dict['opens'], data_dict['highs']
        lows, closes = data_dict['lows'], data_dict['closes']

        right_margin = 6
        total_slots = self.chart_view_size + right_margin
        x_step = inner_w / total_slots
        candle_w = max(x_step * 0.65, 1)

        v_end = len(closes) - (0 if is_hover else self.chart_offset)
        v_start = v_end - self.chart_view_size
        r_start, r_end = max(0, v_start), min(len(closes), v_end)
        
        v_times, v_opens, v_highs = times[r_start:r_end], opens[r_start:r_end], highs[r_start:r_end]
        v_lows, v_closes = lows[r_start:r_end], closes[r_start:r_end]
        if not v_closes: return

        # Scaling แกน Y แบบ Auto-Fit กับแท่งเทียนที่มองเห็น
        local_max = max(v_highs)
        local_min = min(v_lows)
        
        max_p, min_p = local_max, local_min
        diff = max_p - min_p if max_p != min_p else 1
        padding = diff * 0.1
        if diff == 1 and max_p == 0: padding = 1
        max_p += padding
        min_p -= padding
        
        entry_price = self.active_sim['entry'] if self.active_sim else 0
        
        y_zoom = 1.0 if is_hover else self.y_zoom
        y_pan = 0.0 if is_hover else self.y_pan

        center = (max_p + min_p) / 2 + y_pan
        rng = diff / y_zoom
        act_min, act_max, act_rng = center - rng/2, center + rng/2, rng

        if not is_hover:
            self._actual_min_p, self._actual_max_p, self._actual_rng = act_min, act_max, act_rng
            self._last_view_times = v_times

        # วาดแกน
        canvas.create_line(inner_w, 0, inner_w, inner_h, fill="#333", width=1) 
        canvas.create_line(0, inner_h, inner_w, inner_h, fill="#333", width=1) 

        for i in range(11):
            p = act_min + (act_rng * (i/10))
            py = inner_h - (inner_h * (i/10))
            canvas.create_line(0, py, inner_w, py, fill="#1c2026", dash=(2,2))
            canvas.create_text(inner_w + 5, py, text=f"{p:,.3f}", fill="#888", anchor=tk.W, font=("Arial", 8))

        step_t = max(1, len(v_times) // 4)
        for i in range(0, len(v_times), step_t):
            slot_idx = (r_start + i) - v_start
            tx = slot_idx * x_step + x_step / 2
            if 0 <= tx <= inner_w:
                t_str = datetime.fromtimestamp(v_times[i]/1000).strftime('%H:%M\n%d/%m')
                canvas.create_line(tx, 0, tx, inner_h, fill="#1c2026", dash=(2,2))
                canvas.create_text(tx, inner_h + 12, text=t_str, fill="#aaa", font=("Arial", 8), justify=tk.CENTER)

        up_col, dn_col = self.get_colors()

        # วาดแท่งเทียน
        for i in range(len(v_closes)):
            slot_idx = (r_start + i) - v_start
            x = slot_idx * x_step + x_step/2
            y_h, y_l = inner_h - ((v_highs[i] - act_min) / act_rng) * inner_h, inner_h - ((v_lows[i] - act_min) / act_rng) * inner_h
            y_o, y_c = inner_h - ((v_opens[i] - act_min) / act_rng) * inner_h, inner_h - ((v_closes[i] - act_min) / act_rng) * inner_h
            color = up_col if v_closes[i] >= v_opens[i] else dn_col
            canvas.create_line(x, y_h, x, y_l, fill=color)
            y1, y2 = min(y_o, y_c), max(y_o, y_c)
            canvas.create_rectangle(x-candle_w/2, y1, x+candle_w/2, y2 if y2-y1>1 else y1+1, fill=color, outline=color)

        # ✨ กู้คืนเส้นชี้ราคา สูงสุด / ต่ำสุด แบบ Auto-Scale ✨
        max_idx = v_highs.index(local_max)
        min_idx = v_lows.index(local_min)
        
        x_max = ((r_start + max_idx) - v_start) * x_step + x_step/2
        y_max = inner_h - ((local_max - act_min) / act_rng) * inner_h
        if x_max > inner_w / 2:
            canvas.create_line(x_max, y_max, x_max - 20, y_max, fill="#fff", dash=(2,2))
            canvas.create_text(x_max - 25, y_max, text=f"{local_max:,.2f}", fill="#fff", anchor=tk.E, font=("Arial", 8, "bold"))
        else:
            canvas.create_line(x_max, y_max, x_max + 20, y_max, fill="#fff", dash=(2,2))
            canvas.create_text(x_max + 25, y_max, text=f"{local_max:,.2f}", fill="#fff", anchor=tk.W, font=("Arial", 8, "bold"))
            
        x_min = ((r_start + min_idx) - v_start) * x_step + x_step/2
        y_min = inner_h - ((local_min - act_min) / act_rng) * inner_h
        if x_min > inner_w / 2:
            canvas.create_line(x_min, y_min, x_min - 20, y_min, fill="#fff", dash=(2,2))
            canvas.create_text(x_min - 25, y_min, text=f"{local_min:,.2f}", fill="#fff", anchor=tk.E, font=("Arial", 8, "bold"))
        else:
            canvas.create_line(x_min, y_min, x_min + 20, y_min, fill="#fff", dash=(2,2))
            canvas.create_text(x_min + 25, y_min, text=f"{local_min:,.2f}", fill="#fff", anchor=tk.W, font=("Arial", 8, "bold"))

        def _local_t2x(target_t):
            if not v_times: return 0
            import bisect
            idx = bisect.bisect_left(times, target_t)
            if idx >= len(times):
                interval = (times[-1] - times[-2]) if len(times) > 1 else 60000
                float_idx = (len(times) - 1) + (target_t - times[-1]) / max(1, interval)
            elif idx == 0:
                interval = (times[1] - times[0]) if len(times) > 1 else 60000
                float_idx = (target_t - times[0]) / max(1, interval)
            elif times[idx] == target_t:
                float_idx = idx
            else:
                t0, t1 = times[idx-1], times[idx]
                float_idx = (idx - 1) + (target_t - t0) / max(1, (t1 - t0))
            
            slot = float_idx - v_start
            return slot * x_step + x_step / 2

        def _local_tp2xy(target_t, target_p):
            x = _local_t2x(target_t)
            y = inner_h - ((target_p - act_min) / act_rng) * inner_h
            return x, y

        # วาดเส้นเทรนด์ไลน์ที่ตีไว้
        sym_tf = f"{self.active_sim['symbol']}"
        for idx, line in enumerate(self.cfg_data.get("saved_lines", {}).get(sym_tf, [])):
            x1, y1 = _local_tp2xy(line[0], line[1])
            x2, y2 = _local_tp2xy(line[2], line[3])
            l_type = line[4] if len(line) > 4 else "trend"
            
            if l_type == "horizontal": y2 = y1 # Force horizontal
            
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0: dx = 1
            
            rx1, ry1, rx2, ry2 = x1, y1, x2, y2
            if l_type == "ray":
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "extended":
                rx1, ry1 = x1 - dx * 10000, y1 - dy * 10000
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "horizontal":
                rx1, ry1 = -10000, y1
                rx2, ry2 = 10000, y1
                
            color = "#ffffff" if (self.selected_line_idx == idx and not is_hover) else "#f0b90b"
            canvas.create_line(rx1, ry1, rx2, ry2, fill=color, width=2)
            
            if self.selected_line_idx == idx and not is_hover:
                canvas.create_oval(x1-4, y1-4, x1+4, y1+4, fill="#00e676", outline="")
                canvas.create_oval(x2-4, y2-4, x2+4, y2+4, fill="#00e676", outline="")

        if not is_hover and getattr(self, 'is_drawing_mode', False) and getattr(self, 'draw_start_point', None) and getattr(self, 'temp_mouse_pos', None):
            x1, y1 = _local_tp2xy(self.draw_start_point[0], self.draw_start_point[1])
            x2, y2 = self.temp_mouse_pos[0], self.temp_mouse_pos[1]
            l_type = self.draw_type_var.get()
            if l_type == "horizontal": y2 = y1
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0: dx = 1
            
            rx1, ry1, rx2, ry2 = x1, y1, x2, y2
            if l_type == "ray":
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "extended":
                rx1, ry1 = x1 - dx * 10000, y1 - dy * 10000
                rx2, ry2 = x1 + dx * 10000, y1 + dy * 10000
            elif l_type == "horizontal":
                rx1, ry1 = -10000, y1
                rx2, ry2 = 10000, y1
                
            canvas.create_line(rx1, ry1, rx2, ry2, fill="#fff", width=1, dash=(4,2))

        # เส้น PNL
        live_price = closes[-1]
        
        if entry_price > 0:
            raw_y_entry = inner_h - ((entry_price - act_min) / act_rng) * inner_h
            y_entry = max(10, min(inner_h - 10, raw_y_entry))
            margin = self.active_sim["margin"]
            qty = (margin * self.active_sim["leverage"]) / entry_price
            pnl = (live_price - entry_price) * qty if self.active_sim['side'] == "Long" else (entry_price - live_price) * qty
            roe = (pnl / margin) * 100
            
            if pnl > 0.01:
                pnl_bg = "#004d27"  # Dark green
                pnl_fg = "#00e676"  # Bright green
            elif pnl < -0.01:
                pnl_bg = "#59151e"  # Dark red
                pnl_fg = "#ff3d57"  # Bright red
            else:
                pnl_bg = "#333333"  # Dark gray
                pnl_fg = "#ffffff"  # White
            
            sign = "+" if pnl > 0 else ""
            
            # Draw line matching PNL color (thin, dashed)
            canvas.create_line(0, y_entry, inner_w, y_entry, fill=pnl_fg, width=1, dash=(2,2))
            
            # Entry Price right-axis label
            canvas.create_rectangle(inner_w, y_entry - 8, w, y_entry + 8, fill=pnl_fg, outline="")
            canvas.create_text(inner_w + 2, y_entry, text=f"{entry_price:,.2f}", fill="#000", anchor=tk.W, font=("Arial", 8, "bold"))
            
            # PNL text on the right side
            pnl_text = f"PNL {sign}${pnl:,.2f} ({sign}{roe:,.2f}%)"
            text_y = y_entry - 3 if y_entry > 20 else y_entry + 3
            t_anchor = tk.SE if y_entry > 20 else tk.NE
            t_id = canvas.create_text(inner_w - 20, text_y, text=pnl_text, fill=pnl_fg, anchor=t_anchor, font=("Arial", 8))
            
            # Draw background box for PNL text
            bbox = canvas.bbox(t_id)
            if bbox:
                r_id = canvas.create_rectangle(bbox[0]-4, bbox[1]-2, bbox[2]+4, bbox[3]+2, fill=pnl_bg, outline=pnl_fg, width=1)
                canvas.tag_lower(r_id, t_id)

        # Draw [B] DCA tags for Spot
        if self.active_sim and self.active_sim.get("market") == "SPOT":
            dca_list = self.cfg_data.get("spot_dca", {}).get(self.active_sim['symbol'], [])
            for buy in dca_list:
                bp = buy["p"]
                ba = buy["a"]
                y_b = inner_h - ((bp - act_min) / act_rng) * inner_h
                if 0 <= y_b <= inner_h:
                    canvas.create_line(inner_w - 15, y_b, inner_w, y_b, fill="#00e676", dash=(1,1))
                    canvas.create_text(inner_w - 18, y_b, text=f"[B] {ba:g}", fill="#00e676", anchor=tk.E, font=("Arial", 7))

        # เส้น Live Price
        y_live = inner_h - ((live_price - act_min) / act_rng) * inner_h
        canvas.create_line(0, y_live, inner_w, y_live, fill="#f0b90b", dash=(2,2))
        canvas.create_rectangle(inner_w, y_live - 9, w, y_live + 9, fill="#f0b90b", outline="")
        canvas.create_text(inner_w + 2, y_live, text=f"{live_price:,.2f}", fill="#000", anchor=tk.W, font=("Arial", 8, "bold"))
        
        # เวลานับถอยหลัง
        curr_time = time.time() * 1000
        target = kline_close_time
        if target > 0:
            while curr_time > target: 
                interval_ms = 60000 
                tf = self.chart_tf_var.get() if (self.chart_tf_var and not is_hover) else self.cfg_data.get("chart_tf", "1m")
                if tf.endswith('m'): interval_ms = int(tf[:-1]) * 60000
                elif tf.endswith('h'): interval_ms = int(tf[:-1]) * 3600000
                elif tf.endswith('d'): interval_ms = int(tf[:-1]) * 86400000
                else: interval_ms = 60000
                target += interval_ms
            time_left = max(0, int((target - curr_time) / 1000))
            mins, secs = divmod(time_left, 60)
            canvas.create_text(inner_w - 5, y_live - 12 if y_live > 20 else y_live + 12, text=f"{mins:02d}:{secs:02d}", fill="#f0b90b", anchor=tk.E, font=("Arial", 9, "bold"))
            
        if not is_hover:
            # Auto Button in bottom-right corner
            btn_x1, btn_y1 = inner_w + 2, inner_h + 2
            btn_x2, btn_y2 = w - 2, h - 2
            auto_col = "#00bfff" if (self.y_zoom != 1.0 or self.y_pan != 0.0 or getattr(self, 'chart_offset', 0) > 0) else "#aaa"
            canvas.create_rectangle(btn_x1, btn_y1, btn_x2, btn_y2, fill="#1c2026", outline="#333", width=1)
            canvas.create_text((btn_x1 + btn_x2)/2, (btn_y1 + btn_y2)/2, text="Auto", fill=auto_col, font=("Arial", 8, "bold"))

    def draw_full_canvas(self): self.render_candlesticks(self.canvas, self.full_chart_data, self.full_kline_close_time, False)
    def draw_hover_canvas(self): self.render_candlesticks(self.hover_canvas, self.hover_chart_data, self.hover_kline_close_time, True)

    # ==========================================
    # 3. HOVER CHART (Preview)
    # ==========================================
    def on_hover_live(self, event):
        if not self.active_sim or self.is_full_chart_open: return
        self.hover_timer = self.root.after(300, self.open_hover_chart)

    def on_leave_live(self, event):
        if self.hover_timer:
            self.root.after_cancel(self.hover_timer)
            self.hover_timer = None
        self.close_hover_chart()

    def open_hover_chart(self):
        if self.hover_chart_win and self.hover_chart_win.winfo_exists(): return
        self.hover_chart_win = tk.Toplevel(self.root)
        self.hover_chart_win.overrideredirect(True)
        self.hover_chart_win.attributes("-topmost", True)
        self.hover_chart_win.config(bg="#121418", highlightbackground="#444", highlightthickness=1)
        
        c_w, c_h = 500, 300
        x = self.win_bg.winfo_x() + 50
        root_y, root_h = self.win_bg.winfo_y(), self.win_bg.winfo_height()
        y = root_y + root_h + 10 if root_y - (c_h + 10) < 0 else root_y - (c_h + 10)

        self.hover_chart_win.geometry(f"{c_w}x{c_h}+{x}+{y}")
        current_tf = self.cfg_data.get("chart_tf", "1m")
        tk.Label(self.hover_chart_win, text=f"📊 {self.active_sim['symbol']} ({current_tf} Preview)", bg="#1b1f26", fg="#aaaaaa", font=("Arial", 8)).pack(fill=tk.X)
        self.hover_canvas = tk.Canvas(self.hover_chart_win, bg="#0d0f12", highlightthickness=0)
        self.hover_canvas.pack(fill=tk.BOTH, expand=True)
        
        threading.Thread(target=self.fetch_hover_data, daemon=True).start()

    def close_hover_chart(self):
        if self.hover_chart_win:
            self.hover_chart_win.destroy()
            self.hover_chart_win = None
            self.hover_chart_data = None

    def fetch_hover_data(self):
        self.is_fetching_hover = True
        endpoint = "https://fapi.binance.com/fapi/v1/klines" if self.active_sim["market"] == "FUTURES" else "https://api.binance.com/api/v3/klines"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            current_tf = self.cfg_data.get("chart_tf", "1m")
            res = requests.get(f"{endpoint}?symbol={self.active_sim['symbol']}&interval={current_tf}&limit=100", headers=headers, timeout=3)
            data = res.json()
            if res.status_code == 200 and isinstance(data, list):
                self.hover_chart_data = {
                    "times": [int(k[0]) for k in data], "opens": [float(k[1]) for k in data],
                    "highs": [float(k[2]) for k in data], "lows": [float(k[3]) for k in data], "closes": [float(k[4]) for k in data]
                }
                self.hover_kline_close_time = int(data[-1][6])
                self.request_chart_redraw("hover")
        except: pass
        self.is_fetching_hover = False

    # ==========================================
    # 4. FULL CHART (Mini TradingView)
    # ==========================================
    def open_full_chart(self, event=None):
        if not self.active_sim: return
        self.close_hover_chart()
        
        if self.is_full_chart_open: 
            self.close_full_chart()
            return
            
        self.is_full_chart_open = True
        self.full_chart_win = tk.Toplevel(self.root)
        self.full_chart_win.overrideredirect(True)
        self.full_chart_win.attributes("-topmost", True)
        self.full_chart_win.config(bg="#121418", highlightbackground="#444", highlightthickness=1)
        
        c_w, c_h = 600, 360
        x = self.win_bg.winfo_x() + 50
        root_y, root_h = self.win_bg.winfo_y(), self.win_bg.winfo_height()
        y = root_y + root_h + 10 if root_y - (c_h + 10) < 0 else root_y - (c_h + 10)
        self.full_chart_win.geometry(f"{c_w}x{c_h}+{x}+{y}")
        
        header = tk.Frame(self.full_chart_win, bg="#1b1f26")
        header.pack(fill=tk.X)
        header.bind("<ButtonPress-1>", self.chart_start_drag)
        header.bind("<B1-Motion>", self.chart_do_drag)
        
        tk.Label(header, text=f"📈 {self.active_sim['symbol']}", bg="#1b1f26", fg="#f0b90b", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=8, pady=4)
        
        tfs = ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "4h", "12h", "1d"]
        self.chart_tf_var = tk.StringVar(value=self.cfg_data.get("chart_tf", "1m"))
        cb = ttk.Combobox(header, textvariable=self.chart_tf_var, values=tfs, width=4, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", self.on_tf_change)

        self.draw_type_var = tk.StringVar(value="trend")
        self.btn_draw = tk.Menubutton(header, text="✏️ Trend Line ▼", bg="#2b313a", fg="#fff", bd=0, font=("Arial", 9), cursor="hand2", relief=tk.FLAT)
        self.btn_draw.pack(side=tk.LEFT, padx=6)
        
        self.draw_menu = tk.Menu(self.btn_draw, tearoff=0, bg="#2b313a", fg="#fff", font=("Arial", 9))
        self.btn_draw.config(menu=self.draw_menu)
        
        self.draw_menu.add_command(label="✏️ Trend Line", command=lambda: self.set_draw_mode("trend", "✏️ Trend Line ▼"))
        self.draw_menu.add_command(label="➡️ Ray", command=lambda: self.set_draw_mode("ray", "➡️ Ray ▼"))
        self.draw_menu.add_command(label="↔️ Extended", command=lambda: self.set_draw_mode("extended", "↔️ Extended ▼"))
        self.draw_menu.add_command(label="➖ Horizontal", command=lambda: self.set_draw_mode("horizontal", "➖ Horizontal ▼"))
        self.draw_menu.add_separator()
        self.draw_menu.add_command(label="❌ Cancel Draw", command=self.cancel_draw_mode)
        tk.Button(header, text="🗑️ ลบเส้น", command=self.clear_lines, bg="#2b313a", fg="#ff3d57", bd=0, font=("Arial", 9), cursor="hand2").pack(side=tk.LEFT)
        tk.Button(header, text="✖", bg="#ff3d57", fg="white", bd=0, font=("Arial", 9, "bold"), cursor="hand2", command=self.close_full_chart).pack(side=tk.RIGHT, padx=4)

        self.canvas = tk.Canvas(self.full_chart_win, bg="#0d0f12", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<MouseWheel>", self.on_chart_scroll)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_canvas_hover)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.full_chart_win.bind("<Delete>", self.delete_selected_line)
        self.full_chart_win.bind("<BackSpace>", self.delete_selected_line)

        self.full_chart_data = None
        self.chart_offset = 0 
        self.y_zoom = 1.0
        self.y_pan = 0.0
        self.is_drawing_mode = False
        self.draw_start_point = None
        self.canvas.create_text(300, 180, text="Loading Live Chart...", fill="#f0b90b")
        threading.Thread(target=self.fetch_full_chart_data, daemon=True).start()

    def close_full_chart(self):
        self.is_full_chart_open = False
        self.is_drawing_mode = False
        if self.full_chart_win: 
            self.full_chart_win.destroy()
            self.full_chart_win = None
            self.full_chart_data = None

    def chart_start_drag(self, event):
        self._c_drag_x, self._c_drag_y = event.x_root, event.y_root
        self._c_start_x, self._c_start_y = self.full_chart_win.winfo_x(), self.full_chart_win.winfo_y()

    def chart_do_drag(self, event):
        self.full_chart_win.geometry(f"+{self._c_start_x + (event.x_root - self._c_drag_x)}+{self._c_start_y + (event.y_root - self._c_drag_y)}")

    def on_tf_change(self, event):
        self.cfg_data["chart_tf"] = self.chart_tf_var.get()
        self.save_config()
        self.chart_offset = 0
        self.y_zoom = 1.0
        self.y_pan = 0.0
        self.selected_line_idx = None
        self.canvas.delete("all")
        self.canvas.create_text(300, 180, text="Loading...", fill="#f0b90b")
        threading.Thread(target=self.fetch_full_chart_data, daemon=True).start()

    # --- Interaction ---
    def on_chart_scroll(self, event):
        if not self.full_chart_data: return
        delta = event.delta if hasattr(event, 'delta') else 0
        inner_w = self.canvas.winfo_width() - self.c_pad_r
        if event.x > inner_w: 
            if delta > 0: self.y_zoom *= 1.1
            elif delta < 0: self.y_zoom /= 1.1
        else: 
            old_size = self.chart_view_size
            if delta > 0: self.chart_view_size = max(10, int(self.chart_view_size * 0.85))
            elif delta < 0: self.chart_view_size = min(1000, int(self.chart_view_size * 1.15))
            size_diff = self.chart_view_size - old_size
            mouse_x_ratio = event.x / max(1, inner_w)
            shift = int(size_diff * (1 - mouse_x_ratio))
            
            max_offset = max(0, len(self.full_chart_data["closes"]) - max(2, self.chart_view_size))
            self.chart_offset = max(0, min(self.chart_offset + shift, max_offset))
        self.request_chart_redraw("full")

    def on_canvas_double_click(self, event):
        inner_w = self.canvas.winfo_width() - self.c_pad_r
        inner_h = self.canvas.winfo_height() - self.c_pad_b
        if event.x > inner_w:
            self.y_zoom = 1.0
            self.y_pan = 0.0
        elif event.y > inner_h:
            self.chart_offset = 0
            self.chart_view_size = 60
        else:
            self.y_zoom = 1.0
            self.y_pan = 0.0
            self.chart_offset = 0
            self.chart_view_size = 60
        self.request_chart_redraw("full")

    def get_time_index(self, target_t):
        times = self._last_view_times
        if not times: return 0
        if target_t <= times[0]:
            interval = (times[1] - times[0]) if len(times) > 1 else 60000
            return (target_t - times[0]) / interval
        if target_t >= times[-1]:
            interval = (times[-1] - times[-2]) if len(times) > 1 else 60000
            return len(times) - 1 + (target_t - times[-1]) / interval
        
        idx = bisect.bisect_left(times, target_t)
        if times[idx] == target_t: return idx
        t0, t1 = times[idx-1], times[idx]
        return idx - 1 + (target_t - t0) / (t1 - t0)

    def xy_to_time_price(self, x, y):
        inner_w, inner_h = self.canvas.winfo_width() - self.c_pad_r, self.canvas.winfo_height() - self.c_pad_b
        price = self._actual_min_p + ((inner_h - y) / inner_h) * self._actual_rng
        if not self._last_view_times: return 0, price
        
        total_slots = len(self._last_view_times) + 10
        x_step = inner_w / total_slots
        idx = (x - x_step / 2) / x_step
        
        times = self._last_view_times
        if idx <= 0:
            interval = (times[1] - times[0]) if len(times) > 1 else 60000
            target_t = times[0] + idx * interval
        elif idx >= len(times) - 1:
            interval = (times[-1] - times[-2]) if len(times) > 1 else 60000
            target_t = times[-1] + (idx - (len(times) - 1)) * interval
        else:
            int_idx = int(idx)
            target_t = times[int_idx] + (idx - int_idx) * (times[int_idx+1] - times[int_idx])
            
        return target_t, price

    def time_price_to_xy(self, target_t, target_p):
        inner_w, inner_h = self.canvas.winfo_width() - self.c_pad_r, self.canvas.winfo_height() - self.c_pad_b
        if not self._last_view_times: return -10, -10
        
        idx = self.get_time_index(target_t)
        total_slots = len(self._last_view_times) + 10
        x_step = inner_w / total_slots
        x = idx * x_step + x_step / 2
        y = inner_h - ((target_p - self._actual_min_p) / self._actual_rng) * inner_h
        return x, y

    def on_canvas_press(self, event):
        if not self.full_chart_data: return
        self.canvas.focus_set()
        inner_w, inner_h = self.canvas.winfo_width() - self.c_pad_r, self.canvas.winfo_height() - self.c_pad_b

        # Check Auto Button click (bottom-right corner intersection)
        if event.x >= inner_w and event.y >= inner_h:
            self.y_zoom = 1.0
            self.y_pan = 0.0
            self.chart_offset = 0
            self.chart_view_size = 60
            self.request_chart_redraw("full")
            return

        if event.x > inner_w: 
            self._y_pan_start_y = event.y
            self._y_pan_start_val = self.y_pan
            return
        if event.y > inner_h: 
            self._x_pan_start_x = event.x
            return

        t, p = self.xy_to_time_price(event.x, event.y)

        if self.is_drawing_mode:
            if not self.draw_start_point: self.draw_start_point = (t, p)
            else:
                sym_tf = f"{self.active_sim['symbol']}"
                if sym_tf not in self.cfg_data["saved_lines"]: self.cfg_data["saved_lines"][sym_tf] = []
                self.cfg_data["saved_lines"][sym_tf].append([self.draw_start_point[0], self.draw_start_point[1], t, p, self.draw_type_var.get()])
                self.save_config()
                self.draw_start_point = None
                self.cancel_draw_mode()
            self.request_chart_redraw("full")
            return

        sym_tf = f"{self.active_sim['symbol']}"
        lines = self.cfg_data.get("saved_lines", {}).get(sym_tf, [])
        clicked_line, clicked_handle = None, None
        
        for idx, line in enumerate(lines):
            x1, y1 = self.time_price_to_xy(line[0], line[1])
            x2, y2 = self.time_price_to_xy(line[2], line[3])
            if math.hypot(event.x - x1, event.y - y1) < 10: clicked_line, clicked_handle = idx, 0; break
            if math.hypot(event.x - x2, event.y - y2) < 10: clicked_line, clicked_handle = idx, 1; break
            l_mag = math.hypot(x2 - x1, y2 - y1)
            if l_mag > 0:
                u = ((event.x - x1)*(x2 - x1) + (event.y - y1)*(y2 - y1)) / (l_mag ** 2)
                if 0 <= u <= 1:
                    if math.hypot(event.x - (x1 + u*(x2-x1)), event.y - (y1 + u*(y2-y1))) < 6:
                        clicked_line, clicked_handle = idx, 'body'; break

        self.selected_line_idx = clicked_line
        self.dragging_handle = clicked_handle
        
        if clicked_line is not None:
            self._drag_start_t, self._drag_start_p = t, p
            self.request_chart_redraw("full")
            return

        self._pan_start_x = event.x
        self._pan_start_y = event.y 

    def on_canvas_motion(self, event):
        if not self.full_chart_data: return
        inner_h = self.canvas.winfo_height() - self.c_pad_b
        
        if hasattr(self, '_y_pan_start_y'):
            self.y_pan = self._y_pan_start_val + ((event.y - self._y_pan_start_y) / inner_h) * (self._actual_rng / self.y_zoom)
            self.request_chart_redraw("full")
            return

        if self.is_drawing_mode and self.draw_start_point:
            self.temp_mouse_pos = (event.x, event.y)
            self.request_chart_redraw("full")
            return

        if getattr(self, 'selected_line_idx', None) is not None and getattr(self, 'dragging_handle', None) is not None:
            t, p = self.xy_to_time_price(event.x, event.y)
            sym_tf = f"{self.active_sim['symbol']}"
            line = self.cfg_data["saved_lines"][sym_tf][self.selected_line_idx]
            if self.dragging_handle == 0: line[0], line[1] = t, p
            elif self.dragging_handle == 1: line[2], line[3] = t, p
            elif self.dragging_handle == 'body':
                dt, dp = t - self._drag_start_t, p - self._drag_start_p
                line[0] += dt; line[1] += dp; line[2] += dt; line[3] += dp
                self._drag_start_t, self._drag_start_p = t, p
            self.request_chart_redraw("full")
            return

        if hasattr(self, '_pan_start_x'):
            dx = event.x - self._pan_start_x
            inner_w = max(1, self.canvas.winfo_width() - self.c_pad_r)
            cw = inner_w / max(1, self.chart_view_size + 6)
            shift = int(dx / max(1, cw))
            if shift != 0:
                max_offset = max(0, len(self.full_chart_data["closes"]) - max(2, self.chart_view_size))
                new_offset = max(0, min(self.chart_offset + shift, max_offset))
                if new_offset != self.chart_offset:
                    self.chart_offset = new_offset
                    self._pan_start_x += shift * cw
                else:
                    self._pan_start_x = event.x
            if self.y_zoom != 1.0:
                self.y_pan += ((event.y - self._pan_start_y) / inner_h) * (self._actual_rng / self.y_zoom)
                self._pan_start_y = event.y
            self.request_chart_redraw("full")

    def on_canvas_release(self, event):
        if hasattr(self, '_y_pan_start_y'): delattr(self, '_y_pan_start_y')
        if hasattr(self, '_pan_start_x'): delattr(self, '_pan_start_x')
        if hasattr(self, '_pan_start_y'): delattr(self, '_pan_start_y')
        if getattr(self, 'dragging_handle', None) is not None:
            self.save_config()
            self.dragging_handle = None

    def on_canvas_hover(self, event):
        if self.is_drawing_mode and self.draw_start_point:
            self.temp_mouse_pos = (event.x, event.y)
            self.request_chart_redraw("full")

    def set_draw_mode(self, mode, text):
        self.draw_type_var.set(mode)
        self.is_drawing_mode = True
        self.draw_start_point = None
        self.selected_line_idx = None
        self.btn_draw.config(text=text, bg="#f0b90b", fg="#000")
        self.canvas.config(cursor="crosshair")
        self.request_chart_redraw("full")

    def cancel_draw_mode(self):
        self.is_drawing_mode = False
        self.draw_start_point = None
        self.btn_draw.config(bg="#2b313a", fg="#fff")
        self.canvas.config(cursor="arrow")
        self.request_chart_redraw("full")

    def toggle_draw_mode(self):
        if self.is_drawing_mode: self.cancel_draw_mode()
        else: self.set_draw_mode(self.draw_type_var.get(), self.btn_draw.cget("text"))

    def delete_selected_line(self, event=None):
        if getattr(self, 'selected_line_idx', None) is not None:
            sym_tf = f"{self.active_sim['symbol']}"
            lines = self.cfg_data["saved_lines"].get(sym_tf, [])
            if 0 <= self.selected_line_idx < len(lines):
                lines.pop(self.selected_line_idx)
                self.selected_line_idx = None
                self.save_config()
                self.request_chart_redraw("full")

    def clear_lines(self):
        sym_tf = f"{self.active_sim['symbol']}"
        if sym_tf in self.cfg_data["saved_lines"]:
            self.cfg_data["saved_lines"][sym_tf] = []
            self.save_config()
            self.request_chart_redraw("full")

    def fetch_spot_trades(self, symbol):
        exchange = self.cfg_data.get("active_exchange", "binance")
        if exchange != "binance": return
        keys = self.cfg_data.get("api_keys", {}).get(exchange, {})
        api_key = keys.get("key", "")
        api_secret = keys.get("secret", "")
        if not api_key or not api_secret: return
        
        def _worker():
            try:
                ts = int(time.time() * 1000)
                qs = f"symbol={symbol}&timestamp={ts}&recvWindow=10000"
                sig = hmac.new(api_secret.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
                headers = {'X-MBX-APIKEY': api_key}
                res = requests.get(f"https://api.binance.com/api/v3/myTrades?{qs}&signature={sig}", headers=headers, timeout=5)
                if res.status_code == 200:
                    trades = []
                    for t in res.json():
                        if t.get("isBuyer", False):
                            trades.append({
                                "p": float(t["price"]),
                                "a": float(t["qty"]),
                                "t": int(t["time"])
                            })
                    if not hasattr(self, "spot_api_trades"): self.spot_api_trades = {}
                    self.spot_api_trades[symbol] = trades
                    self.request_chart_redraw("full")
            except Exception: pass
        threading.Thread(target=_worker, daemon=True).start()

    def fetch_full_chart_data(self):
        self.is_fetching_full = True
        tf = self.chart_tf_var.get()
        sym = self.active_sim['symbol']
        market = self.active_sim.get("market", "FUTURES")
        if market == "SPOT":
            self.fetch_spot_trades(sym)
        endpoint = "https://fapi.binance.com/fapi/v1/klines" if market == "FUTURES" else "https://api.binance.com/api/v3/klines"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(f"{endpoint}?symbol={sym}&interval={tf}&limit=500", headers=headers, timeout=5)
            data = res.json()
            if res.status_code == 200 and isinstance(data, list):
                self.full_chart_data = {
                    "times": [int(k[0]) for k in data], "opens": [float(k[1]) for k in data], 
                    "highs": [float(k[2]) for k in data], "lows": [float(k[3]) for k in data], "closes": [float(k[4]) for k in data]
                }
                self.full_kline_close_time = int(data[-1][6])
                self.request_chart_redraw("full")
            else:
                self.root.after_idle(lambda: self._show_error(self.canvas, f"Error: TF {tf} Invalid"))
        except Exception as e:
            self.root.after_idle(lambda: self._show_error(self.canvas, "Network Error"))
        self.is_fetching_full = False

    def _show_error(self, canvas, msg):
        if canvas and canvas.winfo_exists():
            canvas.delete("all")
            canvas.create_text(canvas.winfo_width()/2, canvas.winfo_height()/2, text=msg, fill="#ff3d57")

    # ==========================================
    # 5. Network (REST API Fallback + WebSocket)
    # ==========================================
    def fetch_all_symbols(self):
        try:
            res = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=10)
            if res.status_code == 200: self.market_symbols["binance_SPOT"] = [s['symbol'] for s in res.json()['symbols'] if s['status'] == 'TRADING']
        except: pass
        try:
            res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
            if res.status_code == 200: self.market_symbols["binance_FUTURES"] = [s['symbol'] for s in res.json()['symbols'] if s['status'] == 'TRADING']
        except: pass
        try:
            res = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SWAP", timeout=10)
            if res.status_code == 200: self.market_symbols["okx_FUTURES"] = [s['instId'].replace('-SWAP', '').replace('-', '') for s in res.json()['data']]
        except: pass
        try:
            res = requests.get("https://www.okx.com/api/v5/public/instruments?instType=SPOT", timeout=10)
            if res.status_code == 200: self.market_symbols["okx_SPOT"] = [s['instId'].replace('-', '') for s in res.json()['data']]
        except: pass

    def update_fallback_loop(self):
        if getattr(self, 'win_fg', None) and self.win_fg.winfo_viewable():
            self.win_fg.lift()
            
        if self.active_sim and (time.time() - self.last_ws_msg_time > 2.0):
            threading.Thread(target=self.fetch_live_price_rest, daemon=True).start()
            
        if self.is_full_chart_open and self.full_chart_data and self.chart_offset <= 0:
            if time.time() * 1000 > self.full_kline_close_time + 1000 and not self.is_fetching_full:
                threading.Thread(target=self.fetch_full_chart_data, daemon=True).start()
        elif self.hover_chart_win and self.hover_chart_data:
            if time.time() * 1000 > self.hover_kline_close_time + 1000 and not self.is_fetching_hover:
                threading.Thread(target=self.fetch_hover_data, daemon=True).start()
                
        self.root.after(1000, self.update_fallback_loop)

    def fetch_live_price_rest(self):
        if not self.active_sim: return
        market, symbol = self.active_sim["market"], self.active_sim["symbol"]
        endpoint = "https://fapi.binance.com/fapi/v1/ticker/24hr" if market == "FUTURES" else "https://api.binance.com/api/v3/ticker/24hr"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(f"{endpoint}?symbol={symbol}", headers=headers, timeout=2)
            if res.status_code == 200:
                data = res.json()
                price = float(data["lastPrice"])
                self.current_live_price = price
                self.current_pct_change = float(data["priceChangePercent"])
                self.last_ws_msg_time = time.time()
                self.root.after_idle(self.update_sim_ui, price, self.current_pct_change)
                self.inject_live_price(price)
        except: pass

    def start_ws(self, market, symbol):
        self.ws_keep_running = True
        sym_lower = symbol.lower()
        url = f"wss://stream.binance.com:9443/stream?streams={sym_lower}@aggTrade/{sym_lower}@ticker" if market == "SPOT" else f"wss://fstream.binance.com/stream?streams={sym_lower}@aggTrade/{sym_lower}@ticker"
        
        while self.ws_keep_running:
            self.ws = websocket.WebSocketApp(url, on_message=self.on_ws_message)
            self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=20, ping_timeout=10)
            if self.ws_keep_running: time.sleep(1)

    def on_ws_message(self, ws, message):
        try:
            raw_data = json.loads(message)
            if 'data' not in raw_data: return
            data = raw_data['data']
            stream = raw_data['stream']
            
            if '@aggTrade' in stream and 'p' in data:
                price = float(data['p'])
                self.current_live_price = price
                self.last_ws_msg_time = time.time()
                self.root.after_idle(self.update_sim_ui, price, self.current_pct_change)
                self.inject_live_price(price)
            elif '@ticker' in stream and 'P' in data:
                self.current_pct_change = float(data['P'])
        except: pass

    def inject_live_price(self, price):
        # แทรกราคาเพื่อขยับไส้เทียน/แท่งเทียนสดๆ (Real-time Wiggle)
        if self.is_full_chart_open and self.full_chart_data and self.full_chart_data['closes']:
            self.full_chart_data['closes'][-1] = price
            if price > self.full_chart_data['highs'][-1]: self.full_chart_data['highs'][-1] = price
            if price < self.full_chart_data['lows'][-1]: self.full_chart_data['lows'][-1] = price
            self.request_chart_redraw("full")
            
        if self.hover_chart_win and self.hover_chart_data and self.hover_chart_data['closes']:
            self.hover_chart_data['closes'][-1] = price
            if price > self.hover_chart_data['highs'][-1]: self.hover_chart_data['highs'][-1] = price
            if price < self.hover_chart_data['lows'][-1]: self.hover_chart_data['lows'][-1] = price
            self.request_chart_redraw("hover")

    def update_sim_ui(self, live_price, pct_change):
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
            
            rate = self.usdt_thb_rate if getattr(self, "display_currency", "USDT") == "THB" else 1.0
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
                    self.lbl_pnl.config(text=f"Value: {sym_char}{val:,.2f} (Spot)", fg="#00bfff")
        except: pass
        
        try:
            self.win_fg.update_idletasks()
            req_w = self.win_fg.winfo_reqwidth()
            target_w = max(450, req_w + 15)
            
            x = self.win_bg.winfo_x()
            y = self.win_bg.winfo_y()
            
            # If current geometry is already this, do nothing to avoid flicker
            current_geo = self.win_bg.geometry()
            curr_w = int(current_geo.split('x')[0])
            
            # We auto-scale to target_w if it's smaller, or if we want to snap
            if curr_w != target_w:
                self.current_width = target_w
                self.win_bg.geometry(f"{target_w}x45+{x}+{y}")
                self.win_fg.geometry(f"{target_w}x45+{x}+{y}")
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = BinanceSimulatorApp(root)
    root.mainloop()