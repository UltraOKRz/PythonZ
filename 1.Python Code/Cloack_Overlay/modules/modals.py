# modules/modals.py
# Modals Mixin: ป๊อปอัปตั้งค่า (Settings), คลังแมพ (Map Picker), หน้าต่างลอยแถบล่าง (Bottom Panel), ระบบกระเป๋า (Wallet)
import os
import sys
import json
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from modules.common import (
    CONFIG_FILE, DEFAULT_WALLET, 
    format_compact_number, get_default_wallet, StrokeLabel
)

class ModalsMixin:
    def attach_modal_resize_grip(self, window, min_w=200, min_h=200):
        """เพื่มกริบ Resize สีแดงให้กับหน้าต่าง Modal (Toplevel) และระบบลากขยายหน้าต่าง"""
        grip = tk.Label(window, text=" ◢ ", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#dc2626", relief="solid", bd=1, highlightbackground="#ffffff", highlightthickness=1, cursor="size_nw_se", padx=2, pady=0)
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.lift()

        def start_rs(e):
            window._rs_x = e.x_root
            window._rs_y = e.y_root
            window._rs_w = window.winfo_width()
            window._rs_h = window.winfo_height()

        def do_rs(e):
            dx = e.x_root - window._rs_x
            dy = e.y_root - window._rs_y
            nw = max(min_w, window._rs_w + dx)
            nh = max(min_h, window._rs_h + dy)
            window.geometry(f"{nw}x{nh}")

        grip.bind("<ButtonPress-1>", start_rs)
        grip.bind("<B1-Motion>", do_rs)
        return grip
    def open_wallet_explorer(self):
        addr = self.wallet_addr if self.wallet_addr else get_default_wallet()
        url = f"https://msu-explorer.xangle.io/address/{addr}"
        webbrowser.open(url)

    def prompt_wallet_address_modal(self):
        """หน้าต่างขอเลขกระเป๋า EVM สำหรับผู้ใช้ใหม่ หรือกดเปลี่ยนกระเป๋า"""
        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        modal_w = 340
        modal_h = 175
        screen_w = self.root.winfo_screenwidth()
        modal_x = min(screen_w - modal_w - 20, max(20, cur_x + 15))
        modal_y = max(40, cur_y + 35)

        p_win = tk.Toplevel(self.root)
        p_win.title("ตั้งค่ากระเป๋า EVM")
        p_win.geometry(f"{modal_w}x{modal_h}+{modal_x}+{modal_y}")
        p_win.config(bg="#121721", highlightbackground="#00f2fe", highlightthickness=1)
        p_win.attributes("-topmost", True)
        p_win.overrideredirect(True)
        self.attach_modal_resize_grip(p_win)

        hdr = tk.Frame(p_win, bg="#1a2230")
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="👛 ตั้งค่ากระเป๋าเงิน EVM (NESO)", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg="#1a2230").pack(side=tk.LEFT, padx=10, pady=5)
        btn_c = tk.Label(hdr, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#1a2230", cursor="hand2")
        btn_c.pack(side=tk.RIGHT, padx=10, pady=5)
        btn_c.bind("<Button-1>", lambda e: p_win.destroy())

        body = tk.Frame(p_win, bg="#121721", padx=12, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="กรุณากรอกเลขกระเป๋า EVM (Henesys L1 / MSU Chain):", font=("Segoe UI", 8), fg="#94a3b8", bg="#121721").pack(anchor="w")
        ent = tk.Entry(body, font=("Consolas", 8), bg="#1e293b", fg="#ffffff", insertbackground="#00f2fe", bd=1, relief="solid")
        ent.pack(fill=tk.X, pady=(6, 10))
        if self.wallet_addr:
            ent.insert(0, self.wallet_addr)

        def save_and_close():
            val = ent.get().strip()
            if val and val.startswith("0x") and len(val) >= 40:
                self.wallet_addr = val
                self.save_config()
                p_win.destroy()
                threading.Thread(target=lambda: [self._fetch_wallet_neso_sync(), self.root.after(0, self.update_drop_ui)], daemon=True).start()
                self.open_wallet_inapp_modal()

        btn_ok = tk.Label(body, text="✓ บันทึกกระเป๋า", font=("Segoe UI", 9, "bold"), bg="#00f2fe", fg="#000000", cursor="hand2", pady=4)
        btn_ok.pack(fill=tk.X)
        btn_ok.bind("<Button-1>", lambda e: save_and_close())

    def open_wallet_inapp_modal(self):
        """เปิดหน้าต่างกระเป๋าเกม In-App HUD สไตล์ MapleStory Universe"""
        if not self.wallet_addr or self.wallet_addr == "0x0000000000000000000000000000000000000000":
            self.prompt_wallet_address_modal()
            return

        if hasattr(self, 'wallet_modal_win') and self.wallet_modal_win and self.wallet_modal_win.winfo_exists():
            self.wallet_modal_win.lift()
            return

        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        modal_w = 345
        modal_h = 295
        screen_w = self.root.winfo_screenwidth()
        modal_x = min(screen_w - modal_w - 20, max(20, cur_x + 15))
        modal_y = max(40, cur_y + 35)

        self.wallet_modal_win = tk.Toplevel(self.root)
        self.wallet_modal_win.title("NESO In-Game Wallet")
        self.wallet_modal_win.geometry(f"{modal_w}x{modal_h}+{modal_x}+{modal_y}")
        self.wallet_modal_win.config(bg="#0f141d", highlightbackground="#a855f7", highlightthickness=1)
        self.wallet_modal_win.attributes("-topmost", True)
        self.wallet_modal_win.overrideredirect(True)
        self.attach_modal_resize_grip(self.wallet_modal_win)

        def start_drag_wal(e):
            self.wallet_modal_win.dx = e.x_root - self.wallet_modal_win.winfo_x()
            self.wallet_modal_win.dy = e.y_root - self.wallet_modal_win.winfo_y()
        def do_drag_wal(e):
            x = e.x_root - self.wallet_modal_win.dx
            y = e.y_root - self.wallet_modal_win.dy
            self.wallet_modal_win.geometry(f"+{x}+{y}")

        self.wallet_modal_win.bind("<ButtonPress-1>", start_drag_wal)
        self.wallet_modal_win.bind("<B1-Motion>", do_drag_wal)

        hdr = tk.Frame(self.wallet_modal_win, bg="#1a1e29")
        hdr.pack(fill=tk.X)
        hdr.bind("<ButtonPress-1>", start_drag_wal)
        hdr.bind("<B1-Motion>", do_drag_wal)

        lbl_t = tk.Label(hdr, text="💰 MY IN-GAME WALLET", font=("Segoe UI", 9, "bold"), fg="#c084fc", bg="#1a1e29")
        lbl_t.pack(side=tk.LEFT, padx=10, pady=6)
        btn_close = tk.Label(hdr, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#1a1e29", cursor="hand2")
        btn_close.pack(side=tk.RIGHT, padx=10, pady=6)
        btn_close.bind("<Button-1>", lambda e: self.wallet_modal_win.destroy())

        body = tk.Frame(self.wallet_modal_win, bg="#0f141d", padx=12, pady=8)
        body.pack(fill=tk.BOTH, expand=True)

        card_bal = tk.Frame(body, bg="#181726", bd=1, relief="solid", padx=10, pady=8)
        card_bal.pack(fill=tk.X, pady=(0, 6))

        tk.Label(card_bal, text="NESO TOKEN BALANCE", font=("Segoe UI", 7, "bold"), fg="#a78bfa", bg="#181726").pack(anchor="w")
        lbl_val_big = tk.Label(card_bal, text=f"{self.wallet_neso_str} NESO", font=("Consolas", 15, "bold"), fg="#fbbf24", bg="#181726")
        lbl_val_big.pack(anchor="w", pady=(3, 1))
        tk.Label(card_bal, text=f"≈ {self.wallet_neso_compact} NESO (On-Chain Verified)", font=("Consolas", 7), fg="#94a3b8", bg="#181726").pack(anchor="w")

        f_info = tk.Frame(body, bg="#131924", bd=1, relief="solid", padx=10, pady=6)
        f_info.pack(fill=tk.X, pady=(0, 6))

        tk.Label(f_info, text="WALLET ADDRESS (EVM):", font=("Segoe UI", 7, "bold"), fg="#64748b", bg="#131924").pack(anchor="w")
        f_addr_row = tk.Frame(f_info, bg="#131924")
        f_addr_row.pack(fill=tk.X, pady=(2, 4))

        disp_addr = f"{self.wallet_addr[:10]}...{self.wallet_addr[-8:]}" if len(self.wallet_addr) > 20 else self.wallet_addr
        lbl_addr = tk.Label(f_addr_row, text=disp_addr, font=("Consolas", 8), fg="#38bdf8", bg="#131924")
        lbl_addr.pack(side=tk.LEFT)

        def copy_addr():
            self.root.clipboard_clear()
            self.root.clipboard_append(self.wallet_addr)
            btn_cp.config(text="✓ Copied", fg="#38ef7d")
            self.wallet_modal_win.after(1200, lambda: btn_cp.config(text="📋 Copy", fg="#cbd5e1") if self.wallet_modal_win and self.wallet_modal_win.winfo_exists() else None)

        btn_cp = tk.Label(f_addr_row, text="📋 Copy", font=("Segoe UI", 7, "bold"), fg="#cbd5e1", bg="#1e293b", cursor="hand2", padx=5, pady=1)
        btn_cp.pack(side=tk.RIGHT)
        btn_cp.bind("<Button-1>", lambda e: copy_addr())

        tk.Label(f_info, text="NETWORK: Henesys L1 / MSU Chain", font=("Consolas", 7, "bold"), fg="#38ef7d", bg="#131924").pack(anchor="w")

        f_game = tk.Frame(body, bg="#131924", bd=1, relief="solid", padx=10, pady=6)
        f_game.pack(fill=tk.X, pady=(0, 8))
        tk.Label(f_game, text="IN-GAME STATUS", font=("Segoe UI", 7, "bold"), fg="#64748b", bg="#131924").pack(anchor="w")
        tk.Label(f_game, text="💎 Staking / Locked: 0 NESO (Unlocked)", font=("Consolas", 7), fg="#cbd5e1", bg="#131924").pack(anchor="w")
        tk.Label(f_game, text="⚡ World Mining Rewards: Active (Fang)", font=("Consolas", 7), fg="#38ef7d", bg="#131924").pack(anchor="w")

        f_btns = tk.Frame(body, bg="#0f141d")
        f_btns.pack(fill=tk.X, pady=(2, 0))

        def refresh_wal():
            btn_rf.config(text="⏳ กำลังดึง...")
            def do_rf():
                self._fetch_wallet_neso_sync()
                self.root.after(0, self.update_drop_ui)
                self.root.after(0, lambda: [lbl_val_big.config(text=f"{self.wallet_neso_str} NESO"), btn_rf.config(text="🔄 รีเฟรช")])
            threading.Thread(target=do_rf, daemon=True).start()

        btn_rf = tk.Label(f_btns, text="🔄 รีเฟรช", font=("Segoe UI", 8, "bold"), fg="#000000", bg="#00f2fe", cursor="hand2", padx=8, pady=3)
        btn_rf.pack(side=tk.LEFT, padx=(0, 4))
        btn_rf.bind("<Button-1>", lambda e: refresh_wal())

        btn_chg = tk.Label(f_btns, text="⚙️ เปลี่ยนกระเป๋า", font=("Segoe UI", 8), fg="#cbd5e1", bg="#1e293b", cursor="hand2", padx=6, pady=3)
        btn_chg.pack(side=tk.LEFT, padx=(0, 4))
        btn_chg.bind("<Button-1>", lambda e: [self.wallet_modal_win.destroy(), self.prompt_wallet_address_modal()])

        btn_exp = tk.Label(f_btns, text="🌐 Explorer ↗", font=("Segoe UI", 8), fg="#a78bfa", bg="#1e293b", cursor="hand2", padx=6, pady=3)
        btn_exp.pack(side=tk.RIGHT)
        btn_exp.bind("<Button-1>", lambda e: self.open_wallet_explorer())

    def close_app(self):
        self.save_config()
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.destroy()
        if self.map_picker_win and self.map_picker_win.winfo_exists():
            self.map_picker_win.destroy()
        if self.bottom_panel_win and self.bottom_panel_win.winfo_exists():
            self.bottom_panel_win.destroy()
        self.root.destroy()
        os._exit(0)

    # -------------------------------------------------------------
    # 🗂️ หน้าต่างแยกเมนูด้านล่าง (Detached Bottom Panel Modal)
    # -------------------------------------------------------------
    def open_bottom_panel_modal(self):
        """เปิด/ปิด หน้าต่างแยกของแถบควบคุมด้านล่าง ไม่โดนตัดหรือหายเวลาเปลี่ยนขนาดหน้าต่างหลัก"""
        if self.bottom_panel_win and self.bottom_panel_win.winfo_exists():
            self.bottom_panel_win.destroy()
            self.bottom_panel_win = None
            if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
                self.btn_bottom_menu.config(bg="#182230", fg="#38bdf8")
            return

        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        cur_w = self.win_bg.winfo_width()
        cur_h = self.win_bg.winfo_height()

        # ขนาดเท่ากับเมนูตั้งค่าเป๊ะๆ (290x420) ตามคำสั่ง เพื่อรองรับการยัดโมดูลเพิ่มในอนาคต
        p_w = 290
        p_h = 420
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # วางด้านขวาของหน้าต่างหลัก หรือวางด้านซ้ายถ้าจอขวาเต็ม
        if cur_x + cur_w + p_w + 12 <= screen_w:
            p_x = cur_x + cur_w + 8
            p_y = cur_y
        else:
            p_x = max(10, cur_x - p_w - 8)
            p_y = cur_y

        self.bottom_panel_win = tk.Toplevel(self.root)
        self.bottom_panel_win.title("เมนูควบคุมล่าง (Bottom Menu)")
        self.bottom_panel_win.geometry(f"{p_w}x{p_h}+{p_x}+{p_y}")
        self.bottom_panel_win.config(bg="#121721", highlightbackground="#00f2fe", highlightthickness=1)
        self.bottom_panel_win.attributes("-topmost", True)
        self.bottom_panel_win.overrideredirect(True)
        self.attach_modal_resize_grip(self.bottom_panel_win)

        def start_drag_bp(e):
            self.bottom_panel_win.dx = e.x_root - self.bottom_panel_win.winfo_x()
            self.bottom_panel_win.dy = e.y_root - self.bottom_panel_win.winfo_y()
        def do_drag_bp(e):
            x = e.x_root - self.bottom_panel_win.dx
            y = e.y_root - self.bottom_panel_win.dy
            self.bottom_panel_win.geometry(f"+{x}+{y}")

        self.bottom_panel_win.bind("<ButtonPress-1>", start_drag_bp)
        self.bottom_panel_win.bind("<B1-Motion>", do_drag_bp)

        # Header ของหน้าต่างแยก (คุมโทนเดียวกับ Settings)
        hdr = tk.Frame(self.bottom_panel_win, bg="#1a2230")
        hdr.pack(fill=tk.X)
        hdr.bind("<ButtonPress-1>", start_drag_bp)
        hdr.bind("<B1-Motion>", do_drag_bp)

        lbl_t = tk.Label(hdr, text="▲ เมนูแถบล่าง (ควบคุมและโมดูล)", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1a2230")
        lbl_t.pack(side=tk.LEFT, padx=8, pady=4)
        lbl_t.bind("<ButtonPress-1>", start_drag_bp)
        lbl_t.bind("<B1-Motion>", do_drag_bp)

        def _close_bp():
            if self.bottom_panel_win and self.bottom_panel_win.winfo_exists():
                self.bottom_panel_win.destroy()
                self.bottom_panel_win = None
            if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
                self.btn_bottom_menu.config(bg="#182230", fg="#38bdf8")

        btn_x = tk.Label(hdr, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#1a2230", cursor="hand2", padx=6)
        btn_x.pack(side=tk.RIGHT, padx=4, pady=4)
        btn_x.bind("<Button-1>", lambda e: _close_bp())

        # ชั้นบน: Real Time, Server Ping, NXPC Price
        row1 = tk.Frame(self.bottom_panel_win, bg="#121721")
        row1.pack(fill=tk.X, padx=8, pady=(6, 3))

        self.lbl_bp_real_time = tk.Label(row1, text="00:00:00", font=("Consolas", 11, "bold"), fg="#38bdf8", bg="#121721")
        self.lbl_bp_real_time.pack(side=tk.LEFT)

        self.lbl_bp_ping = tk.Label(row1, text="?? ms", font=("Consolas", 8, "bold"), fg="#94a3b8", bg="#121721", cursor="hand2")
        self.lbl_bp_ping.pack(side=tk.RIGHT)
        self.lbl_bp_ping.bind("<Button-1>", lambda e: self.reset_api_counter())

        tk.Label(row1, text="|", font=("Consolas", 8), fg="#4b5563", bg="#121721").pack(side=tk.RIGHT, padx=3)

        self.lbl_bp_nxpc = tk.Label(row1, text="NXPC: $--", font=("Consolas", 8, "bold"), fg="#f59e0b", bg="#121721", cursor="hand2")
        self.lbl_bp_nxpc.pack(side=tk.RIGHT)
        self.lbl_bp_nxpc.bind("<Button-1>", lambda e: self.toggle_nxpc_currency())
        self._update_nxpc_label()

        # ชั้นกลาง: Scan Map Button
        row2 = tk.Frame(self.bottom_panel_win, bg="#121721")
        row2.pack(fill=tk.X, padx=8, pady=3)

        f_left_btn = tk.Frame(row2, bg="#16202c", bd=1, relief="solid")
        f_left_btn.pack(fill=tk.X)

        self.btn_ocr = tk.Label(f_left_btn, text="Scan Map", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#16202c", cursor="hand2", padx=8, pady=4)
        self.btn_ocr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.btn_ocr.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

        self.btn_ocr_cfg = tk.Label(f_left_btn, text="✂️", font=("Segoe UI", 8, "bold"), fg="#f472b6", bg="#231728", cursor="hand2", padx=8, pady=4)
        self.btn_ocr_cfg.pack(side=tk.RIGHT, fill=tk.Y)
        self.btn_ocr_cfg.bind("<Button-1>", lambda e: self.open_ocr_crop_tool())

        # ชั้นล่างสุด: Scout, Reset/Refresh, Pin, Sound
        row3 = tk.Frame(self.bottom_panel_win, bg="#121721")
        row3.pack(fill=tk.X, padx=8, pady=(3, 6))

        btn_rst = tk.Label(row3, text="🔄 Refresh", font=("Segoe UI", 8, "bold"), fg="#38ef7d", bg="#182230", cursor="hand2", padx=6, pady=2)
        btn_rst.pack(side=tk.LEFT, padx=(0, 4))
        btn_rst.bind("<Button-1>", lambda e: [self.reset_manual_timer() if self.mode == "Manual" else None, self.trigger_scan_and_refresh()])

        pin_col = "#38ef7d" if self.is_pinned else "#64748b"
        btn_pin = tk.Label(row3, text="📌", font=("Segoe UI", 8), fg=pin_col, bg="#182230", cursor="hand2", padx=4, pady=2)
        btn_pin.pack(side=tk.LEFT, padx=2)
        btn_pin.bind("<Button-1>", lambda e: self.toggle_pin())

        snd_col = "#38ef7d" if self.sound_enabled else "#64748b"
        snd_icon = "🔊" if self.sound_enabled else "🔇"
        btn_snd = tk.Label(row3, text=snd_icon, font=("Segoe UI", 8), fg=snd_col, bg="#182230", cursor="hand2", padx=4, pady=2)
        btn_snd.pack(side=tk.LEFT, padx=2)
        btn_snd.bind("<Button-1>", lambda e: self.toggle_sound())

        btn_scout = tk.Label(row3, text="🎒 Scout", font=("Segoe UI", 8, "bold"), fg="#00f2fe", bg="#182230", cursor="hand2", padx=6, pady=2)
        btn_scout.pack(side=tk.RIGHT)
        btn_scout.bind("<Button-1>", lambda e: self.open_wallet_explorer())

        # 📦 พื้นที่วางปุ่มโมดูลเสริม (Mod Button Bar - เรียงจากซ้ายไปขวา)
        f_modules = tk.Frame(self.bottom_panel_win, bg="#0d1117", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
        f_modules.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))
        self.f_bottom_modules = f_modules

        # แถวสำหรับวางปุ่มโมดูลต่างๆ (Pack จาก LEFT เรียงจากซ้ายไปขวา ค่อยๆ เพิ่มทีละตัว)
        f_mod_btns = tk.Frame(f_modules, bg="#0d1117")
        f_mod_btns.pack(fill=tk.X, padx=4, pady=4, anchor="nw")
        self.f_mod_btns = f_mod_btns

        # 📊 Mod 1: Farm Income Tracker (หน้าต่างแยก 177x252 px)
        btn_mod_income = tk.Label(f_mod_btns, text=" 📊 Income Tracker ", font=("Segoe UI", 7, "bold"),
                                  fg="#38ef7d", bg="#182230", relief="solid", bd=1,
                                  highlightbackground="#22c55e", highlightthickness=1,
                                  cursor="hand2", padx=6, pady=4)
        btn_mod_income.pack(side=tk.LEFT, padx=(0, 4))
        btn_mod_income.bind("<Button-1>", lambda e: self.open_income_tracker_mod())

        if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
            self.btn_bottom_menu.config(bg="#00f2fe", fg="#000000")
        self.bottom_panel_win.lift()

    def open_income_tracker_mod(self):
        """เปิด/ปิด หน้าต่างโมดูล Farm Income Tracker (ขนาด 177x252 px)"""
        if not hasattr(self, '_income_tracker_mod') or self._income_tracker_mod is None:
            try:
                from Mod.income_tracker import IncomeTrackerMod
                self._income_tracker_mod = IncomeTrackerMod(self)
            except Exception as e:
                print("Failed to load IncomeTrackerMod:", e)
                if hasattr(self, 'log_cmd'):
                    self.log_cmd(f"⚠️ โหลด Mod ไม่สำเร็จ: {e}")
                return
        
        self._income_tracker_mod.toggle_window()

    # -------------------------------------------------------------
    # 🗺️ หน้าต่างเลือกแมพ / ฟิลด์ (Map Picker Window)
    # -------------------------------------------------------------
    def open_map_picker(self):
        if self.map_picker_win and self.map_picker_win.winfo_exists():
            self.map_picker_win.lift()
            return
            
        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        picker_x = cur_x + 10
        picker_y = cur_y + 40
        
        self.map_picker_win = tk.Toplevel(self.root)
        self.map_picker_win.title("เลือกฟิลด์ (Select Field)")
        self.map_picker_win.geometry(f"280x360+{picker_x}+{picker_y}")
        self.map_picker_win.config(bg="#121721", highlightbackground="#00f2fe", highlightthickness=1)
        self.map_picker_win.attributes("-topmost", True)
        self.map_picker_win.overrideredirect(True)
        self.attach_modal_resize_grip(self.map_picker_win)
        
        # หัวหน้าต่างเลือกแมพ
        hdr = tk.Frame(self.map_picker_win, bg="#1a2230")
        hdr.pack(fill=tk.X)
        lbl_t = tk.Label(hdr, text="🗺️ เลือกฟิลด์ / แมพ", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg="#1a2230")
        lbl_t.pack(side=tk.LEFT, padx=8, pady=4)
        btn_close = tk.Label(hdr, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#1a2230", cursor="hand2")
        btn_close.pack(side=tk.RIGHT, padx=8, pady=4)
        btn_close.bind("<Button-1>", lambda e: self.map_picker_win.destroy())

        # ช่องค้นหาชื่อแมพ
        f_search = tk.Frame(self.map_picker_win, bg="#121721")
        f_search.pack(fill=tk.X, padx=8, pady=6)
        lbl_search_icon = tk.Label(f_search, text="🔍", bg="#121721", fg="#94a3b8")
        lbl_search_icon.pack(side=tk.LEFT, padx=(0, 4))
        
        entry_search = tk.Entry(f_search, font=("Segoe UI", 8), bg="#1e293b", fg="#ffffff", insertbackground="#00f2fe", bd=1, relief="solid")
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # รายการแมพ (Listbox + Scrollbar)
        f_list = tk.Frame(self.map_picker_win, bg="#121721")
        f_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        
        scrollbar = tk.Scrollbar(f_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(f_list, bg="#182230", fg="#e2e8f0", selectbackground="#00f2fe", 
                             selectforeground="#000000", font=("Segoe UI", 8), bd=0, 
                             highlightthickness=0, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        # เติมรายชื่อแมพ
        current_displayed_fields = []
        def refresh_list(query=""):
            listbox.delete(0, tk.END)
            current_displayed_fields.clear()
            q = query.lower().strip()
            for fld in self.layers_list:
                name = fld.get("layerName", "")
                group = fld.get("groupName", "")
                full_desc = f"{name} ({group})"
                if not q or q in name.lower() or q in group.lower():
                    listbox.insert(tk.END, f" {full_desc}")
                    current_displayed_fields.append(fld)

        refresh_list()
        entry_search.bind("<KeyRelease>", lambda e: refresh_list(entry_search.get()))

        def on_select(evt):
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                selected_fld = current_displayed_fields[idx]
                self.is_in_town = False
                self.has_no_drop = False
                self.current_town_name = ""
                self.detected_submap_name = ""
                self.selected_layer_id = selected_fld.get("layerId")
                self.selected_layer_name = selected_fld.get("layerName")
                self.selected_group_name = selected_fld.get("groupName")
                self.save_config()
                self.setup_ui_elements()
                self.fetch_drop_data_async()
                self.map_picker_win.destroy()

        listbox.bind("<Double-Button-1>", on_select)
        btn_pick = tk.Label(self.map_picker_win, text="✓ ยืนยันเลือกแมพนี้", font=("Segoe UI", 8, "bold"), 
                            bg="#00f2fe", fg="#000000", cursor="hand2", pady=4)
        btn_pick.pack(fill=tk.X, padx=8, pady=(0, 8))
        btn_pick.bind("<Button-1>", on_select)

    # -------------------------------------------------------------
    # ⚙️ หน้าต่างตั้งค่า (Settings Window)
    # -------------------------------------------------------------
    def open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return
            
        cur_x = self.win_bg.winfo_x()
        cur_y = self.win_bg.winfo_y()
        cur_w = self.win_bg.winfo_width()
        set_x = cur_x + cur_w + 12
        set_y = cur_y
        
        screen_w = self.root.winfo_screenwidth()
        if set_x + 290 > screen_w:
            set_x = max(10, cur_x - 300)
            
        self.settings_win = tk.Toplevel(self.root)
        self.settings_win.title("TIMER TOOL Settings")
        self.settings_win.geometry(f"290x420+{set_x}+{set_y}")
        self.settings_win.config(bg="#121721", highlightbackground="#00f2fe", highlightthickness=1)
        self.settings_win.attributes("-topmost", True)
        self.settings_win.overrideredirect(True)
        self.attach_modal_resize_grip(self.settings_win)
        
        def start_drag_set(e):
            self.settings_win.dx = e.x_root - self.settings_win.winfo_x()
            self.settings_win.dy = e.y_root - self.settings_win.winfo_y()
        def do_drag_set(e):
            x = e.x_root - self.settings_win.dx
            y = e.y_root - self.settings_win.dy
            self.settings_win.geometry(f"+{x}+{y}")
            
        self.settings_win.bind("<ButtonPress-1>", start_drag_set)
        self.settings_win.bind("<B1-Motion>", do_drag_set)
        
        self.refresh_settings_ui()
        self.settings_win.lift()

    def refresh_settings_ui(self):
        if not self.settings_win or not self.settings_win.winfo_exists():
            return
            
        for w in self.settings_win.winfo_children():
            w.destroy()
            
        # แถบหัวหน้าต่าง
        hdr = tk.Frame(self.settings_win, bg="#1a2230")
        hdr.pack(fill=tk.X)
        lbl_t = tk.Label(hdr, text="⚙️ TIMER TOOL - ตั้งค่า", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg="#1a2230")
        lbl_t.pack(side=tk.LEFT, padx=8, pady=4)
        btn_x = tk.Label(hdr, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#1a2230", cursor="hand2")
        btn_x.pack(side=tk.RIGHT, padx=8, pady=4)
        btn_x.bind("<Button-1>", lambda e: self.settings_win.destroy())
        
        # 1. เลือกเซิร์ฟเวอร์ (Fang / Ain)
        f_srv = tk.Frame(self.settings_win, bg="#121721")
        f_srv.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(f_srv, text="เซิร์ฟเวอร์ (Server):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        srv_box = tk.Frame(f_srv, bg="#121721")
        srv_box.pack(fill=tk.X, pady=2)
        
        for sname in ["Fang", "Ain"]:
            is_active = self.server_name == sname
            bg_s = "#f59e0b" if is_active else "#1e293b"
            fg_s = "#000000" if is_active else "#e2e8f0"
            btn_s = tk.Label(srv_box, text=f"👑 {sname}", font=("Segoe UI", 8, "bold"), bg=bg_s, fg=fg_s, cursor="hand2", padx=10, pady=2)
            btn_s.pack(side=tk.LEFT, padx=2)
            btn_s.bind("<Button-1>", lambda e, s=sname: [self.switch_server(s), self.refresh_settings_ui()])

        # 2. ปุ่มจุดความโปร่งใส (10 30 50 70 100)
        f_op = tk.Frame(self.settings_win, bg="#121721")
        f_op.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f_op, text="ระดับความโปร่งใส (Opacity):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        btn_box = tk.Frame(f_op, bg="#121721")
        btn_box.pack(fill=tk.X, pady=2)
        
        op_values = [0.10, 0.30, 0.50, 0.70, 1.00]
        op_labels = ["10%", "30%", "50%", "70%", "100%"]
        for val, txt in zip(op_values, op_labels):
            is_active = abs(self.opacity - val) < 0.05
            bg_b = "#00f2fe" if is_active else "#1e293b"
            fg_b = "#000000" if is_active else "#e2e8f0"
            btn = tk.Label(btn_box, text=txt, font=("Segoe UI", 8, "bold"), bg=bg_b, fg=fg_b, cursor="hand2", padx=6, pady=1)
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Button-1>", lambda e, v=val: self.set_opacity(v))

        # 3. ปุ่มเลือกขนาดหน้าต่างสำเร็จรูป (S / M / L)
        f_sz = tk.Frame(self.settings_win, bg="#121721")
        f_sz.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(f_sz, text="ขนาดหน้าต่าง (Window Size):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        sz_box = tk.Frame(f_sz, bg="#121721")
        sz_box.pack(fill=tk.X, pady=1)
        
        sizes = [("📱 แถบซ้าย", 184, 768), ("S เล็ก", 245, 600), ("M กลาง", 320, 650), ("L ใหญ่", 450, 700)]
        for label, sw, sh in sizes:
            btn_sz = tk.Label(sz_box, text=label, font=("Segoe UI", 7, "bold"), bg="#1e293b", fg="#e2e8f0", cursor="hand2", padx=5, pady=2)
            btn_sz.pack(side=tk.LEFT, padx=1)
            btn_sz.bind("<Button-1>", lambda e, w=sw, h=sh: [setattr(self, 'is_compact_folded', False), self.set_preset_size(w, h)])

        # 🎛️ กำหนดขนาดเอง (Custom Resolution W x H)
        f_custom_sz = tk.Frame(f_sz, bg="#121721")
        f_custom_sz.pack(fill=tk.X, pady=(3, 1))
        tk.Label(f_custom_sz, text="กำหนดเอง:", font=("Segoe UI", 7), fg="#94a3b8", bg="#121721").pack(side=tk.LEFT, padx=(0, 2))
        
        ent_w = tk.Entry(f_custom_sz, width=4, font=("Consolas", 8), bg="#1e293b", fg="#00f2fe", insertbackground="#00f2fe", bd=1, relief="solid")
        ent_w.insert(0, str(getattr(self, 'full_w', 184)))
        ent_w.pack(side=tk.LEFT, padx=1)
        
        tk.Label(f_custom_sz, text="x", font=("Consolas", 8), fg="#64748b", bg="#121721").pack(side=tk.LEFT, padx=1)
        
        ent_h = tk.Entry(f_custom_sz, width=4, font=("Consolas", 8), bg="#1e293b", fg="#00f2fe", insertbackground="#00f2fe", bd=1, relief="solid")
        ent_h.insert(0, str(getattr(self, 'full_h', 768)))
        ent_h.pack(side=tk.LEFT, padx=1)

        def apply_custom_res():
            try:
                rw = int(ent_w.get().strip())
                rh = int(ent_h.get().strip())
                if rw >= 150 and rh >= 300:
                    self.set_preset_size(rw, rh)
                    self.log_cmd(f"📐 กำหนดขนาด: {rw}x{rh}")
            except Exception as e:
                pass

        btn_apply_sz = tk.Label(f_custom_sz, text="ใช้ขนาดนี้", font=("Segoe UI", 7, "bold"), bg="#0284c7", fg="#ffffff", cursor="hand2", padx=4, pady=1)
        btn_apply_sz.pack(side=tk.LEFT, padx=3)
        btn_apply_sz.bind("<Button-1>", lambda e: apply_custom_res())

        # 🔤 3.1 ปรับขนาดตัวอักษรเองตามใจผู้ใช้ (Font Size Scaling) - ครอบคลุมทั้งโหมด 1 และ 2
        f_font = tk.Frame(self.settings_win, bg="#121721")
        f_font.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(f_font, text="ขนาดตัวอักษรข้อความ (Font Size):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        f_font_box = tk.Frame(f_font, bg="#121721")
        f_font_box.pack(fill=tk.X, pady=1)

        def set_font_size_val(sz):
            self.custom_font_size = int(sz)
            self.save_config()
            self.update_auto_scale_ui()
            self.refresh_settings_ui()

        # ปุ่มลัด: ออโต้, 7, 8, 9, 10, 11
        f_presets = [("ออโต้", 0), ("7", 7), ("8", 8), ("9", 9), ("10", 10), ("11", 11)]
        for f_label, f_val in f_presets:
            is_active = (getattr(self, 'custom_font_size', 0) == f_val)
            bg_f = "#00f2fe" if is_active else "#1e293b"
            fg_f = "#000000" if is_active else "#e2e8f0"
            btn_f = tk.Label(f_font_box, text=f_label, font=("Segoe UI", 7, "bold"), bg=bg_f, fg=fg_f, cursor="hand2", padx=5, pady=1)
            btn_f.pack(side=tk.LEFT, padx=1)
            btn_f.bind("<Button-1>", lambda e, v=f_val: set_font_size_val(v))

        # ช่องกรอกตัวเลขขนาดตามใจผู้ใช้
        ent_fs = tk.Entry(f_font_box, width=3, font=("Consolas", 8, "bold"), bg="#1e293b", fg="#ffffff", insertbackground="#00f2fe", bd=1, relief="solid", justify="center")
        ent_fs.pack(side=tk.LEFT, padx=(4, 2))
        cur_fs = getattr(self, 'custom_font_size', 0)
        if cur_fs > 0:
            ent_fs.insert(0, str(cur_fs))

        def apply_custom_font_entry():
            val = ent_fs.get().strip()
            if val.isdigit() and int(val) > 0:
                set_font_size_val(int(val))
            elif val == "0" or val == "":
                set_font_size_val(0)

        btn_apply_fs = tk.Label(f_font_box, text="ตั้ง", font=("Segoe UI", 7, "bold"), bg="#38ef7d", fg="#000000", cursor="hand2", padx=4, pady=1)
        btn_apply_fs.pack(side=tk.LEFT, padx=1)
        btn_apply_fs.bind("<Button-1>", lambda e: apply_custom_font_entry())

        # 4. ตัวเลือกโหมด: ServerTime หรือ Manual
        f_mode = tk.Frame(self.settings_win, bg="#121721")
        f_mode.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f_mode, text="โหมดนับเวลา (Mode):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        m_box = tk.Frame(f_mode, bg="#121721")
        m_box.pack(fill=tk.X, pady=2)
        
        is_st = self.mode == "ServerTime"
        btn_st = tk.Label(m_box, text="⏱️ ServerTime", font=("Segoe UI", 8, "bold"),
                          bg="#38ef7d" if is_st else "#1e293b",
                          fg="#000000" if is_st else "#e2e8f0", cursor="hand2", padx=8, pady=2)
        btn_st.pack(side=tk.LEFT, padx=2)
        btn_st.bind("<Button-1>", lambda e: [self.switch_mode("ServerTime"), self.refresh_settings_ui()])
        
        is_mn = self.mode == "Manual"
        btn_mn = tk.Label(m_box, text="⏳ Manual", font=("Segoe UI", 8, "bold"),
                          bg="#f59e0b" if is_mn else "#1e293b",
                          fg="#000000" if is_mn else "#e2e8f0", cursor="hand2", padx=8, pady=2)
        btn_mn.pack(side=tk.LEFT, padx=2)
        btn_mn.bind("<Button-1>", lambda e: [self.switch_mode("Manual"), self.refresh_settings_ui()])

        # 5. ช่องกรอกกระเป๋า EVM
        f_wallet = tk.Frame(self.settings_win, bg="#121721")
        f_wallet.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(f_wallet, text="เลขกระเป๋า EVM (ปุ่ม Scout):", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#121721").pack(anchor="w")
        w_in_box = tk.Frame(f_wallet, bg="#121721")
        w_in_box.pack(fill=tk.X, pady=2)
        
        self.entry_wallet = tk.Entry(w_in_box, font=("Consolas", 8), bg="#1e293b", fg="#ffffff", insertbackground="#00f2fe", bd=1, relief="solid")
        self.entry_wallet.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.entry_wallet.insert(0, self.wallet_addr)
        
        def save_wallet():
            val = self.entry_wallet.get().strip()
            if val:
                self.wallet_addr = val
                self.save_config()
                btn_sv.config(text="✓ เซฟแล้ว", bg="#38ef7d", fg="#000")
                self.settings_win.after(1200, lambda: btn_sv.config(text="💾 บันทึก", bg="#00f2fe", fg="#000") if self.settings_win and self.settings_win.winfo_exists() else None)
                
        btn_sv = tk.Label(w_in_box, text="💾 บันทึก", font=("Segoe UI", 8, "bold"), bg="#00f2fe", fg="#000000", cursor="hand2", padx=6, pady=1)
        btn_sv.pack(side=tk.RIGHT)
        btn_sv.bind("<Button-1>", lambda e: save_wallet())

