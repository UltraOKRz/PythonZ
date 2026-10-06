import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os
import sys
import json
import time
import math
import threading
from datetime import datetime
import re
import win32gui

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Import Core Constants and Shared Helpers
from modules.common import (
    CONFIG_FILE, LAYERS_CACHE_FILE, ICONS_CACHE_DIR, DEFAULT_WALLET,
    ZONE_ICONS_MAP, 
    get_default_wallet, get_api_keys,
    format_compact_number, format_compact_stock,
    StrokeLabel
)

# Import Mixins
from modules.api_client import ApiClientMixin
from modules.ocr_engine import OcrEngineMixin
from modules.modals import ModalsMixin
from modules.map_manager import MapManagerMixin, parse_zone_and_submap

# Import UI Frames (Modular Component Architecture)
from modules.ui_frames import (
    TitleFrame, MapBannerFrame, TimerFrame, WalletFrame, BadgesFrame,
    BoostTopFrame, SafeZoneFrame, PoolInfoFrame, HotFarmFrame, StatusFooterFrame
)



class TimerToolApp(ApiClientMixin, MapManagerMixin, OcrEngineMixin, ModalsMixin):
    format_compact_number = staticmethod(format_compact_number)
    format_compact_stock = staticmethod(format_compact_stock)

    def __init__(self, root):
        self.root = root
        self.root.withdraw() # ซ่อน root window
        
        self.trans_key = "#000001"
        self.bg_color = "#121418" # พื้นหลังคุมโทน MS แท้ๆ
        
        # ขนาดเริ่มต้น Default (ตั้งแถบข้าง Vertical Sidebar เป็นค่าเริ่มต้นตามคำสั่ง)
        self.v2_w = 491
        self.v2_h = 418
        self.sidebar_w = 184
        self.sidebar_h = 768
        self.full_w = 184
        self.full_h = 768
        self.mini_w = 560
        self.mini_h = 72
        self.custom_font_size = 0  # 0 = ค่ามาตรฐานตามระบบออโต้สเกล, หรือระบุขนาดเจาะจง (เช่น 7, 8, 9, 10)

        
        # State & Settings
        self.api_keys = get_api_keys()
        self.current_key_idx = 0
        self.wallet_neso_str = "..."
        self.wallet_neso_compact = "..."
        self.wallet_nesolet_str = "..."
        self.wallet_nesolet_compact = "..."
        self.current_town_name = ""
        self.detected_submap_name = ""
        self.is_in_town = False
        self.has_no_drop = False
        self.is_pinned = False
        self.sound_enabled = True
        self.mode = "ServerTime" # เริ่มต้นเป็น ServerTime เสมอ
        self.server_name = "Fang" # เซิร์ฟเวอร์เริ่มต้น
        self.world_id = 0
        self.opacity = 1.0 # 10, 30, 50, 70, 100%
        self.wallet_addr = get_default_wallet()
        
        # ข้อมูลแมพ/ฟิลด์ที่เลือก (เริ่มต้นดึงจาก Config หรือรอสแกนตรวจจับในเกม)
        self.selected_layer_id = None
        self.selected_layer_name = "รอตรวจจับแมพในเกม..."
        self.selected_group_name = ""
        self.layers_list = []
        
        # ข้อมูล NESO แยก 2 ตัว
        self.neso_normal_rate = "40.0%"
        self.neso_normal_stock = "..."
        self.neso_boost_rate = "..."
        self.neso_boost_mult = ""   
        self.neso_boost_stock = "..."
        self.neso_normal_rate_f = 0.0
        self.neso_normal_stock_f = 0.0
        self.neso_boost_rate_f = 0.0
        self.neso_boost_stock_f = 0.0
        self.neso_boost_min_f = 0.0
        self.neso_boost_max_f = 0.0
        self.neso_boost_sure_min = 0.0
        self.neso_boost_sure_max = 0.0
        self.neso_boost_extra_min = 0.0
        self.neso_boost_extra_max = 0.0
        self.neso_boost_total_min = 0.0
        self.neso_boost_total_max = 0.0
        self.neso_boost_sure_txt = "--"
        self.neso_boost_extra_txt = "--"
        self.neso_boost_total_txt = "--"
        self.last_update_str = "--:--:--"
        self.last_fetch_ts = 0
        self.is_fetching = False
        self.is_in_town = False  # True เมื่อ OCR ตรวจพบว่าอยู่ในเมือง/Town (ไม่มีดรอป)
        
        # สำหรับโหมด Manual
        self.manual_running = False
        self.manual_remaining = 20 * 60
        self.last_manual_tick = time.time()
        
        self.has_alerted_2m = False
        self.has_alerted_19m30s = True
        self.has_alerted_0m = False
        self.pulse_state = False
        self.settings_win = None
        self.map_picker_win = None
        self.bottom_panel_win = None
        self.popup_menu = None
        self.show_server_bar = False
        self.show_mode_bar = False
        self.zone_photo_cache = {}
        self.btn_ocr = None
        self.btn_map = None
        self.lbl_poll_countdown = None
        self.last_ocr_map_str = ""  # จำ OCR text ล่าสุดเพื่อ Same-Map Retention
        
        self.pos_x = 0
        self.pos_y = 20
        self.is_compact_folded = True
        self.custom_ocr_region = None
        self.custom_char_ocr_region = None
        self.current_char_name = ""
        self.current_char_asset_key = ""
        self.current_char_level = ""
        self.current_char_job = ""
        self.current_char_nesolet_loaded = False
        self.last_nesolet_fetch_ts = 0
        self.account_characters = []
        self.cmd_logs = [">_ ระบบพร้อมทำงาน..."]
        self.char_crop_win = None
        self.txt_cmd = None
        self.btn_char_ocr = None
        self.best_zone_map = None
        self.lbl_hot_map = None
        self.lbl_hot_rate = None
        self.lbl_hot_qty = None
        self.last_hot_log_ts = 0
        self.last_hot_logged_lid = None
        
        self.neso_normal_drop_qty = "..."
        self.neso_boost_drop_qty = "..."
        self.neso_boost_detail = ""
        self.neso_boost_charge = ""
        self.server_ping_ms = 0
        self.api_call_count = 0
        self.nxpc_usd = 0.0
        self.nxpc_thb = 0.0
        self.show_nxpc_thb = False
        self.nxpc_last_fetch = 0
        
        self.load_layers_cache()
        self.load_config()
        
        # บังคับโหมดเริ่มต้นเป็น ServerTime (SYNC) ทุกครั้งที่เปิดโปรแกรมใหม่
        self.mode = "ServerTime"
        
        # -------------------------------------------------------------
        # 🛡️ โครงสร้างเลเยอร์สไตล์ MS (แก้จอดำ Z-order ถาวร)
        # -------------------------------------------------------------
        self.win_bg = tk.Toplevel(self.root)
        self.win_bg.overrideredirect(True)
        self.win_bg.attributes("-topmost", True)
        self.win_bg.attributes("-alpha", self.opacity)
        self.win_bg.config(bg=self.bg_color, highlightbackground="#00f2fe", highlightthickness=1)
        
        self.win_fg = tk.Toplevel(self.root)
        self.win_fg.overrideredirect(True)
        self.win_fg.attributes("-topmost", True)
        self.win_fg.attributes("-transparentcolor", self.trans_key)
        self.win_fg.config(bg=self.trans_key)
        
        try:
            self.win_fg.transient(self.win_bg)
        except:
            pass
        self.win_fg.lift()
        
        # ระบบลากหน้าต่าง
        self.drag_x = 0
        self.drag_y = 0
        self.win_bg.bind("<ButtonPress-1>", self.start_drag)
        self.win_bg.bind("<B1-Motion>", self.do_drag)
        self.win_bg.bind("<ButtonRelease-1>", self.end_drag)
        self.win_fg.bind("<ButtonPress-1>", self.start_drag)
        self.win_fg.bind("<B1-Motion>", self.do_drag)
        self.win_fg.bind("<ButtonRelease-1>", self.end_drag)
        
        # Frame หลักบน win_fg
        self.main_container = tk.Frame(self.win_fg, bg=self.trans_key)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.main_container.bind("<ButtonPress-1>", self.start_drag)
        self.main_container.bind("<B1-Motion>", self.do_drag)
        self.main_container.bind("<ButtonRelease-1>", self.end_drag)
        
        self.apply_geometry()
        self.setup_ui_elements()
        
        # ดึงข้อมูล Drop Rate ครั้งแรกใน Background Thread
        self.fetch_drop_data_async()
        
        # 🚀 ออโต้สแกนตรวจจับแมพในเกมทันทีที่เปิดโปรแกรม
        self.auto_detect_map_async(silent=True)

        # 🪙 ดึงข้อมูลตัวละครและ Nesolet ครั้งแรกใน Background Thread
        threading.Thread(target=self._auto_init_character, daemon=True).start()
        
        # 📊 เริ่มระบบ Income Tracker Mod เบื้องหลังอัตโนมัติ (ติดตามยอดฟาร์มและซิงค์ On-Chain ตลอดเวลา)
        try:
            from Mod.income_tracker import IncomeTrackerMod
            self._income_tracker_mod = IncomeTrackerMod(self)
        except Exception as e:
            print("Auto-init IncomeTrackerMod error:", e)
        
        # เริ่มการวนลูปนาฬิกา
        self.update_clock_loop()

    def log_cmd(self, msg):
        try:
            line = str(msg)
            self.cmd_logs.append(line)
            if len(self.cmd_logs) > 30:
                self.cmd_logs.pop(0)
            if hasattr(self, 'root') and self.root:
                self.root.after(0, self.refresh_cmd_view)
        except Exception:
            pass

    def refresh_cmd_view(self):
        if hasattr(self, 'txt_cmd') and self.txt_cmd and self.txt_cmd.winfo_exists():
            try:
                recent_logs = self.cmd_logs[-3:] if self.cmd_logs else [">_ พร้อมทำงาน..."]
                txt = "\n".join(recent_logs)
                if isinstance(self.txt_cmd, (tk.Label, StrokeLabel)):
                    w = self.f_cmd_box.winfo_width() if hasattr(self, 'f_cmd_box') and self.f_cmd_box and self.f_cmd_box.winfo_exists() else 0
                    if w > 50:
                        self.txt_cmd.config(text=txt, wraplength=max(80, w - 28))
                    else:
                        self.txt_cmd.config(text=txt)
                elif isinstance(self.txt_cmd, tk.Text):
                    self.txt_cmd.config(state=tk.NORMAL)
                    self.txt_cmd.delete("1.0", tk.END)
                    self.txt_cmd.insert(tk.END, txt)
                    self.txt_cmd.see(tk.END)
                    self.txt_cmd.config(state=tk.DISABLED)
            except Exception:
                pass



    def update_drop_ui(self):
        """อัปเดตตัวเลข % และ สต็อก บน Widget ทั้งหมด"""
        # คำนวน expected drop
        norm_drop = int((self.neso_normal_rate_f / 100.0) * self.neso_normal_stock_f) if hasattr(self, 'neso_normal_rate_f') else 0
        boost_drop = int((self.neso_boost_rate_f / 100.0) * self.neso_boost_stock_f) if hasattr(self, 'neso_boost_rate_f') else 0

        # ตรวจสอบสถานะว่าอยู่ในจุดปลอดภัย หรือ แมพที่ไม่มีดรอป
        is_safe = self.is_in_town or getattr(self, 'has_no_drop', False)
        t_name = getattr(self, 'current_town_name', '')
        sub_name = getattr(self, 'detected_submap_name', '')

        # -------------------------------------------------------------
        # 1. Full Mode: การแสดงผลเรตการดรอปใน Pool Zone
        # -------------------------------------------------------------
        if is_safe:
            # 🛡️ สลับมาแสดงแผ่นป้าย Safe Zone (ร.1) ปิดทับแผงตัวเลขดรอป
            if getattr(self, 'f_boost_info_left', None) and self.f_boost_info_left.winfo_ismapped():
                self.f_boost_info_left.pack_forget()
            if getattr(self, 'f_hot_farm', None) and self.f_hot_farm.winfo_ismapped():
                self.f_hot_farm.pack_forget()

            if getattr(self, 'f_safe_zone_banner', None):
                if not self.f_safe_zone_banner.winfo_ismapped():
                    if getattr(self, 'f_bot_action', None):
                        self.f_safe_zone_banner.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=2, before=self.f_bot_action)
                    else:
                        self.f_safe_zone_banner.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=2)
                
                town_disp = t_name if t_name else (sub_name if sub_name else "จุดปลอดภัย")
                if getattr(self, 'lbl_sz_town', None):
                    self.lbl_sz_town.config(text=f"🏙️ {town_disp}")

            if getattr(self, 'lbl_flame', None):
                self.lbl_flame.config(text="🌿 SAFE ZONE", fg="#4ade80")
            if getattr(self, 'lbl_neso_boost_val', None):
                self.lbl_neso_boost_val.config(text="🛡️ ปลอดภัย", fg="#94a3b8")
            if getattr(self, 'lbl_boost_hdr_mult', None):
                self.lbl_boost_hdr_mult.config(text="")

            # ป้ายเหรียญ NESO สไตล์ในเกม (Normal & Boost)
            if getattr(self, 'lbl_neso_badge_norm_stock', None) is not None and self.lbl_neso_badge_norm_stock.winfo_exists():
                self.lbl_neso_badge_norm_stock.config(text="--", fg="#64748b")
            if getattr(self, 'lbl_neso_badge_stock', None) is not None and self.lbl_neso_badge_stock.winfo_exists():
                self.lbl_neso_badge_stock.config(text="--", fg="#64748b")
            if getattr(self, 'lbl_last_update', None) is not None and self.lbl_last_update.winfo_exists():
                safe_txt = f"🛡️ เซฟโซน ({sub_name})" if sub_name else "🛡️ เซฟโซน / นอกพื้นที่ฟาร์ม"
                self.lbl_last_update.config(text=safe_txt)
        else:
            # ⚔️ อยู่ในแมพฟาร์ม: ซ่อนป้าย Safe Zone แล้วคืนแผงตัวเลขดรอป
            if getattr(self, 'f_safe_zone_banner', None) and self.f_safe_zone_banner.winfo_ismapped():
                self.f_safe_zone_banner.pack_forget()

            if getattr(self, 'f_boost_info_left', None) and not self.f_boost_info_left.winfo_ismapped():
                if getattr(self, 'f_bot_action', None) and self.f_bot_action.winfo_ismapped():
                    self.f_boost_info_left.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(3, 1), before=self.f_bot_action)
                else:
                    self.f_boost_info_left.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(3, 1))

            if getattr(self, 'f_hot_farm', None) and not self.f_hot_farm.winfo_ismapped():
                if getattr(self, 'f_cmd_box', None) and self.f_cmd_box.winfo_ismapped():
                    self.f_hot_farm.pack(side=tk.TOP, fill=tk.X, pady=(0, 2), before=self.f_cmd_box)
                else:
                    self.f_hot_farm.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))

            if getattr(self, 'lbl_flame', None):
                self.lbl_flame.config(text="💧 BOOST DROP!", fg="#38bdf8")

            if getattr(self, 'lbl_neso_norm_val', None) is not None and self.lbl_neso_norm_val.winfo_exists():
                self.lbl_neso_norm_val.config(text=self.neso_normal_rate, fg="#f87171")
            if getattr(self, 'lbl_neso_norm_stock', None) is not None and self.lbl_neso_norm_stock.winfo_exists():
                self.lbl_neso_norm_stock.config(text=f"📦 {self.format_compact_number(getattr(self, 'neso_normal_stock_f', 0.0))}")
            if getattr(self, 'lbl_neso_norm_drop', None) is not None and self.lbl_neso_norm_drop.winfo_exists():
                self.lbl_neso_norm_drop.config(text=f"= {self.format_compact_number(norm_drop)}")
                
            # ป้ายเหรียญ NESO สไตล์ในเกม (Normal & Boost)
            if getattr(self, 'lbl_neso_badge_norm_stock', None) is not None and self.lbl_neso_badge_norm_stock.winfo_exists():
                norm_stk_f = getattr(self, 'neso_normal_stock_f', 0.0)
                self.lbl_neso_badge_norm_stock.config(text=f"{self.format_compact_number(norm_stk_f)}", fg="#bbf246")
            if getattr(self, 'lbl_neso_badge_stock', None) is not None and self.lbl_neso_badge_stock.winfo_exists():
                stk_val = getattr(self, 'neso_boost_stock', '---')
                self.lbl_neso_badge_stock.config(text=f"{stk_val}", fg="#bbf246")

            # Boost Drop แถบบน: % รวม และ ตัวคูณ
            if getattr(self, 'lbl_neso_boost_val', None) is not None and self.lbl_neso_boost_val.winfo_exists():
                self.lbl_neso_boost_val.config(text=self.neso_boost_rate, fg="#4ade80")
            if getattr(self, 'lbl_boost_hdr_mult', None) is not None and self.lbl_boost_hdr_mult.winfo_exists():
                self.lbl_boost_hdr_mult.config(text=f"({self.neso_boost_mult})" if self.neso_boost_mult else "")
                
            if getattr(self, 'lbl_boost_sure_val', None) is not None and self.lbl_boost_sure_val.winfo_exists():
                self.lbl_boost_sure_val.config(text=f"{self.neso_boost_sure_txt}")
            if getattr(self, 'lbl_boost_sure_rate', None) is not None and self.lbl_boost_sure_rate.winfo_exists():
                self.lbl_boost_sure_rate.config(text=f"{self.neso_boost_extra_txt}")
                
            if getattr(self, 'lbl_boost_expected', None) is not None and self.lbl_boost_expected.winfo_exists():
                is_vert = getattr(self, 'full_w', 460) <= 240
                unit_neso = " N" if is_vert else " NESO"
                if hasattr(self, 'neso_boost_total_min') and getattr(self, 'neso_boost_total_max', 0) > 0:
                    self.lbl_boost_expected.config(text=f"{self.neso_boost_total_min:.2f} ~ {self.neso_boost_total_max:.2f}{unit_neso}")
                else:
                    self.lbl_boost_expected.config(text=f"{self.neso_boost_total_txt}")

            if getattr(self, 'lbl_boost_rate_total', None) is not None and self.lbl_boost_rate_total.winfo_exists():
                self.lbl_boost_rate_total.config(text=f" {self.neso_boost_rate}")
            if getattr(self, 'lbl_boost_rate_breakdown', None) is not None and self.lbl_boost_rate_breakdown.winfo_exists():
                bd_txt = getattr(self, 'neso_boost_breakdown_txt', '')
                if "(" in bd_txt and ")" in bd_txt:
                    sub_part = bd_txt[bd_txt.find("("):bd_txt.rfind(")")+1]
                    self.lbl_boost_rate_breakdown.config(text=f" {sub_part}")
                else:
                    self.lbl_boost_rate_breakdown.config(text=f" {bd_txt}")
                    
            if getattr(self, 'lbl_neso_boost_stock', None) is not None and self.lbl_neso_boost_stock.winfo_exists():
                stk_txt = getattr(self, 'neso_boost_stock', '---')
                self.lbl_neso_boost_stock.config(text=f" {stk_txt} NESO")
            if getattr(self, 'lbl_neso_boost_charge', None) is not None and self.lbl_neso_boost_charge.winfo_exists():
                chg_txt = getattr(self, 'neso_boost_charge', '---')
                self.lbl_neso_boost_charge.config(text=f" {chg_txt}")
                
            if getattr(self, 'lbl_last_update', None) is not None and self.lbl_last_update.winfo_exists():
                self.lbl_last_update.config(text=f"🕒 อัปเดตล่าสุด: {self.last_update_str}")

        # -------------------------------------------------------------
        # 2. กระเป๋า NESO & Nesolet (อัปเดตทุกโหมด)
        # -------------------------------------------------------------
        if getattr(self, 'lbl_wallet_neso_val', None) is not None and self.lbl_wallet_neso_val.winfo_exists():
            val_txt = f"{self.wallet_neso_compact}\nNESO" if self.wallet_neso_compact != "..." else "...\nNESO"
            self.lbl_wallet_neso_val.config(text=val_txt)
        if getattr(self, 'lbl_nesolet', None) is not None and self.lbl_nesolet.winfo_exists():
            self.lbl_nesolet.config(text=f"{self.wallet_nesolet_str}\nNesolet")
        if hasattr(self, '_update_nxpc_label'):
            self._update_nxpc_label()

        # -------------------------------------------------------------
        # 3. Mini Mode UI
        # -------------------------------------------------------------
        if getattr(self, 'lbl_mini_norm_rate', None) is not None and self.lbl_mini_norm_rate.winfo_exists():
            self.lbl_mini_norm_rate.config(text="🏙️ Safe" if is_safe else f"N {self.neso_normal_rate}", fg="#64748b" if is_safe else "#38bdf8")
        if getattr(self, 'lbl_mini_norm_stock', None) is not None and self.lbl_mini_norm_stock.winfo_exists():
            self.lbl_mini_norm_stock.config(text="--" if is_safe else f"📦{format_compact_stock(self.neso_normal_stock)}")
        if getattr(self, 'lbl_mini_boost_rate', None) is not None and self.lbl_mini_boost_rate.winfo_exists():
            self.lbl_mini_boost_rate.config(text="🛡️ Safe" if is_safe else f"⚡{self.neso_boost_rate}", fg="#64748b" if is_safe else "#fbbf24")
        if getattr(self, 'lbl_mini_boost_stock', None) is not None and self.lbl_mini_boost_stock.winfo_exists():
            self.lbl_mini_boost_stock.config(text="--" if is_safe else f"📦{format_compact_stock(self.neso_boost_stock)}")
        if getattr(self, 'lbl_mini_wallet_neso', None) is not None and self.lbl_mini_wallet_neso.winfo_exists():
            self.lbl_mini_wallet_neso.config(text=f"💰{self.wallet_neso_compact}")

        # -------------------------------------------------------------
        # 4. แถบ Map Banner (แสดงชื่อโซนหลัก + ชื่อแมพย่อยบรรทัดสอง)
        # -------------------------------------------------------------
        if self.is_in_town:
            main_title = f"🏙️ {t_name}" if t_name else "🏙️ ในเมือง / เซฟโซน"
            sub_title = f"📍 {sub_name} (จุดปลอดภัย)" if sub_name and sub_name != t_name else "📍 จุดปลอดภัย (ไม่มีการดรอป)"
            ico_key = t_name if t_name else "Default_Town"
        elif getattr(self, 'has_no_drop', False):
            m_short = self.selected_layer_name if self.selected_layer_id else "รอตรวจจับ..."
            grp = f" [{self.selected_group_name}]" if self.selected_group_name else ""
            main_title = f"{m_short}{grp}"
            sub_title = f"📍 {sub_name} (ไม่มีดรอป)" if sub_name else "📍 นอกพื้นที่ฟาร์มเหรียญ"
            ico_key = self.selected_layer_name
        else:
            m_short = self.selected_layer_name if self.selected_layer_id else "รอตรวจจับ..."
            grp = f" [{self.selected_group_name}]" if self.selected_group_name else ""
            main_title = f"{m_short}{grp}"
            sub_title = f"📍 {sub_name}" if sub_name else "📍 กำลังฟาร์ม"
            ico_key = self.selected_layer_name

        ico_full = self.get_zone_icon(ico_key, size_h=31)
        ico_mini = self.get_zone_icon(ico_key, size_h=18)

        # อัปเดตไอคอนแมพ
        if getattr(self, 'lbl_map_icon', None) is not None and self.lbl_map_icon.winfo_exists():
            if ico_full:
                self.lbl_map_icon.config(image=ico_full)
            else:
                self.lbl_map_icon.config(image="")

        # อัปเดตบรรทัด 1 (โซนหลัก)
        if getattr(self, 'lbl_map_main', None) is not None and self.lbl_map_main.winfo_exists():
            self.lbl_map_main.config(text=main_title)

        # อัปเดตบรรทัด 2 (แมพย่อยจริงจากมินิแมพ)
        if getattr(self, 'lbl_map_sub', None) is not None and self.lbl_map_sub.winfo_exists():
            sub_fg = "#94a3b8" if is_safe else "#38bdf8"
            self.lbl_map_sub.config(text=sub_title, fg=sub_fg)

        # อัปเดต Mini Mode map
        disp_m_mini = sub_name if sub_name else (t_name if self.is_in_town else self.selected_layer_name)
        if len(disp_m_mini) > 17:
            disp_m_mini = disp_m_mini[:15] + ".."
        if getattr(self, 'lbl_mini_map', None) is not None and self.lbl_mini_map.winfo_exists():
            if ico_mini:
                self.lbl_mini_map.config(text=f" {disp_m_mini}", image=ico_mini, compound=tk.LEFT)
        # อัปเดตข้อมูลแมพแนะนำสุดฮอตในโซน (แสดงผลอย่างเดียว ไม่ปนกับแมพหลัก)
        is_vert_mode = getattr(self, 'full_w', 460) <= 240
        if getattr(self, 'lbl_hot_map', None) is not None and self.lbl_hot_map.winfo_exists():
            if self.best_zone_map:
                b_name = self.best_zone_map.get("layerName", "")
                max_chars = 9 if is_vert_mode else 22
                if len(b_name) > max_chars:
                    b_name = b_name[:max_chars - 1] + ".."
                self.lbl_hot_map.config(text=f"🔥 {b_name}", fg="#fde047")
            else:
                self.lbl_hot_map.config(text="🔥 แนะนำ..." if is_vert_mode else "🔥 แนะนำในโซน...", fg="#94a3b8")

        if getattr(self, 'lbl_hot_qty', None) is not None and self.lbl_hot_qty.winfo_exists():
            if self.best_zone_map:
                exp_min = self.best_zone_map.get("exp_min", 0.0)
                exp_max = self.best_zone_map.get("exp_max", 0.0)
                if exp_max > 0:
                    if is_vert_mode:
                        q_txt = f"{exp_min:.1f}~{exp_max:.1f}"
                    else:
                        q_txt = f"{exp_min:.2f} ~ {exp_max:.2f} N"
                else:
                    q_txt = "--" if is_vert_mode else "-- N"
                self.lbl_hot_qty.config(text=f"⚡{q_txt}", fg="#facc15")
            else:
                self.lbl_hot_qty.config(text="--" if is_vert_mode else "-- N", fg="#64748b")

        if getattr(self, 'lbl_hot_rate', None) is not None and self.lbl_hot_rate.winfo_exists():
            if self.best_zone_map:
                r_val = self.best_zone_map.get('rate', 0.0)
                self.lbl_hot_rate.config(text=f"{r_val:.1f}%", fg="#4ade80")
            else:
                self.lbl_hot_rate.config(text="--%", fg="#64748b")

        # อัปเดตปุ่ม Char OCR ให้แสดงชื่อตัวละครที่ตรวจจับได้
        if getattr(self, 'btn_char_ocr', None) is not None and self.btn_char_ocr.winfo_exists():
            c_name = getattr(self, 'current_char_name', '')
            if c_name:
                disp_c = c_name if len(c_name) <= 9 else c_name[:8] + ".."
                self.btn_char_ocr.config(text=f"👤 {disp_c}", fg="#c084fc", bg="#2e1065")
            else:
                self.btn_char_ocr.config(text="👤 Char", fg="#a855f7", bg="#1e1b2e")

        # รีเฟรชข้อความ CMD Terminal
        self.refresh_cmd_view()

        # ออโต้สเกลตัวอักษรและข้อความในกรอบสีเขียวให้พอดีกับความกว้างหน้าต่าง
        self.update_auto_scale_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.pos_x = cfg.get("pos_x", 100)
                    self.pos_y = cfg.get("pos_y", 100)
                    # จำขนาดหน้าต่างล่าสุดแบบชุดเดียว ไม่สลับหรือฟิกดีฟอลต์
                    self.full_w = max(160, cfg.get("full_w", cfg.get("sidebar_w", 184)))
                    self.full_h = max(350, cfg.get("full_h", cfg.get("sidebar_h", 768)))
                    self.sidebar_w = self.full_w
                    self.sidebar_h = self.full_h
                    self.mini_w = max(460, cfg.get("mini_w", 560))
                    self.mini_h = max(64, cfg.get("mini_h", 72))
                    self.custom_font_size = int(cfg.get("custom_font_size", 0))
                    self.opacity = cfg.get("opacity", 1.0)
                    self.sound_enabled = cfg.get("sound_enabled", True)
                    self.server_name = cfg.get("server_name", "Fang")
                    self.selected_layer_id = cfg.get("selected_layer_id", None)
                    self.selected_layer_name = cfg.get("selected_layer_name", "รอตรวจจับแมพในเกม...")
                    self.selected_group_name = cfg.get("selected_group_name", "")
                    self.is_pinned = cfg.get("is_pinned", False)
                    self.is_mini = False
                    self.is_compact_folded = cfg.get("is_compact_folded", False)
                    self.wallet_addr = cfg.get("wallet_addr", self.wallet_addr)
                    self.custom_ocr_region = cfg.get("custom_ocr_region", None)
                    self.custom_char_ocr_region = cfg.get("custom_char_ocr_region", None)
                    self.current_char_name = cfg.get("current_char_name", "")
                    self.current_char_asset_key = cfg.get("current_char_asset_key", "")
                    self.current_char_level = cfg.get("current_char_level", "")
                    self.current_char_job = cfg.get("current_char_job", "")
            except Exception as e:
                print("Error loading config:", e)

    def save_config(self):
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
            cur_w = self.win_bg.winfo_width()
            cur_h = self.win_bg.winfo_height()
            if cur_w > 100 and cur_h > 50:
                if self.is_mini:
                    self.mini_w = max(460, cur_w)
                    self.mini_h = max(64, cur_h)
                else:
                    self.full_w = max(160, cur_w)
                    self.full_h = max(350, cur_h)
                    self.sidebar_w = self.full_w
                    self.sidebar_h = self.full_h
        except Exception:
            pass

        cfg = {
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "full_w": self.full_w,
            "full_h": self.full_h,
            "sidebar_w": self.full_w,
            "sidebar_h": self.full_h,
            "mini_w": self.mini_w,
            "mini_h": self.mini_h,
            "custom_font_size": getattr(self, 'custom_font_size', 0),
            "opacity": self.opacity,
            "sound_enabled": self.sound_enabled,
            "mode": self.mode,
            "server_name": self.server_name,
            "selected_layer_id": self.selected_layer_id,
            "selected_layer_name": self.selected_layer_name,
            "selected_group_name": self.selected_group_name,
            "is_pinned": self.is_pinned,
            "is_mini": self.is_mini,
            "is_compact_folded": getattr(self, 'is_compact_folded', False),
            "wallet_addr": self.wallet_addr,
            "custom_ocr_region": getattr(self, 'custom_ocr_region', None),
            "custom_char_ocr_region": getattr(self, 'custom_char_ocr_region', None),
            "current_char_name": getattr(self, 'current_char_name', ""),
            "current_char_asset_key": getattr(self, 'current_char_asset_key', ""),
            "current_char_level": getattr(self, 'current_char_level', ""),
            "current_char_job": getattr(self, 'current_char_job', "")
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            print("Error saving config:", e)

    def apply_geometry(self):
        # ล็อกพิกัดจริงปัจจุบันสดๆ ป้องกันหน้าต่างดิ้นหนี/กระโดดตำแหน่ง
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
        except Exception:
            pass

        w = self.mini_w if self.is_mini else self.full_w
        if self.is_mini:
            h = self.mini_h
        elif getattr(self, 'is_compact_folded', False):
            h = self.sidebar_h if self.full_w <= 240 else self.v2_h
        else:
            h = self.full_h
        geom = f"{w}x{h}+{self.pos_x}+{self.pos_y}"
        self.win_bg.geometry(geom)
        self.win_fg.geometry(geom)
        try:
            self.win_bg.update_idletasks()
            self.win_fg.update_idletasks()
            self.update_auto_scale_ui(w)
        except:
            pass
        self.win_fg.lift()
        if hasattr(self, 'grip_win') and self.grip_win.winfo_exists():
            self.grip_win.lift()
        if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
            self.btn_bottom_menu.lift()

    def start_drag(self, event):
        if self.is_pinned:
            return
        self.drag_x = event.x_root - self.win_bg.winfo_x()
        self.drag_y = event.y_root - self.win_bg.winfo_y()

    def do_drag(self, event):
        if self.is_pinned:
            return
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.win_bg.geometry(f"+{x}+{y}")
        self.win_fg.geometry(f"+{x}+{y}")
        self.win_fg.lift()
        if hasattr(self, 'grip_win') and self.grip_win.winfo_exists():
            self.grip_win.lift()
        if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
            self.btn_bottom_menu.lift()
        self.pos_x = x
        self.pos_y = y

    def end_drag(self, event):
        """บันทึกพิกัดเมื่อผู้ใช้ปล่อยเมาส์จากการลาก (ไม่กระตุก Disk I/O ระหว่างลาก)"""
        self.save_config()

    def start_resize(self, event):
        # 🛡️ กฎเหล็ก: ดึงพิกัดจริงปัจจุบันสดๆ ก่อนเริ่มลาก ยึดมุมบนซ้ายไว้สนิท 100%
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
        except Exception:
            pass
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._start_w = self.win_bg.winfo_width()
        self._start_h = self.win_bg.winfo_height()

    def do_resize(self, event):
        """ย่อ-ขยายหน้าต่างแบบลื่นไหลไร้รอยต่อ ป้องกัน Lag ด้วย Debounce"""
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y

        if self.is_mini:
            new_w = max(460, self._start_w + dx)
            new_h = 64
            self.mini_w = new_w
            self.mini_h = new_h
        else:
            new_w = max(160, self._start_w + dx)
            new_h = max(350, self._start_h + dy)
            self.full_w = new_w
            self.full_h = new_h
            self.sidebar_w = new_w
            self.sidebar_h = new_h

        geom = f"{new_w}x{new_h}+{self.pos_x}+{self.pos_y}"
        self.win_bg.geometry(geom)
        self.win_fg.geometry(geom)

        # ⚡ Debounce การคำนวณกราฟิกที่มี Overhead สูง (Redraw Timer & Auto Scale)
        if hasattr(self, '_resize_debounce_id') and self._resize_debounce_id:
            try:
                self.root.after_cancel(self._resize_debounce_id)
            except:
                pass

        def _deferred_resize():
            try:
                if not self.is_mini:
                    self.redraw_circular_timer()
                    self.update_auto_scale_ui(new_w)
                self.win_fg.lift()
                if hasattr(self, 'grip_win') and self.grip_win.winfo_exists():
                    self.grip_win.lift()
                if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
                    self.btn_bottom_menu.lift()
            except Exception:
                pass

        self._resize_debounce_id = self.root.after(40, _deferred_resize)

    def end_resize(self, event):
        """บันทึกขนาดหน้าต่างเมื่อปล่อยเมาส์จากการลากมุม และวาดผลลัพธ์สุดท้ายให้คมชัด"""
        if hasattr(self, '_resize_debounce_id') and self._resize_debounce_id:
            try:
                self.root.after_cancel(self._resize_debounce_id)
            except:
                pass
        try:
            if not self.is_mini:
                self.redraw_circular_timer()
                self.update_auto_scale_ui(self.full_w)
            self.win_fg.lift()
            if hasattr(self, 'grip_win') and self.grip_win.winfo_exists():
                self.grip_win.lift()
            if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu.winfo_exists():
                self.btn_bottom_menu.lift()
        except:
            pass
        self.save_config()

    def snap_to_game_bounds(self):
        """ปรับขนาดและตำแหน่งแนบขอบเกมและหน้าจอ Windows อัตโนมัติอิงจากตำแหน่งปัจจุบัน"""
        try:
            # 🛡️ 1. อัปเดตพิกัดสดๆ ปัจจุบันก่อน
            try:
                cur_x = self.win_bg.winfo_x()
                cur_y = self.win_bg.winfo_y()
                if cur_x > -10000 and cur_y > -10000:
                    self.pos_x = cur_x
                    self.pos_y = cur_y
            except Exception:
                pass

            # 2. ค้นหาหน้าต่างเกม MapleStory N
            game_hwnd = None
            def _find_game(h, _):
                nonlocal game_hwnd
                if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                    t = win32gui.GetWindowText(h).lower()
                    if "maplestory" in t and not any(x in t for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                        game_hwnd = h
            win32gui.EnumWindows(_find_game, None)

            screen_w = self.win_bg.winfo_screenwidth()
            screen_h = self.win_bg.winfo_screenheight()

            # ความสูงคงเดิมตามที่ผู้ใช้ตั้งไว้ (ไม่ยืดลงมาสุดขอบจอ)
            cur_h = self.win_bg.winfo_height()
            new_h = cur_h if cur_h > 100 else (self.sidebar_h if getattr(self, 'is_compact_folded', False) else self.full_h)

            if not game_hwnd:
                # ถ้าไม่พบเกม ให้แนบขอบจอซ้ายหรือขวาตามตำแหน่งปัจจุบัน โดยคงความสูงเดิมไว้
                target_w = 176 if getattr(self, 'is_compact_folded', False) else 256
                if self.pos_x < screen_w // 2:
                    self.pos_x = 0
                else:
                    self.pos_x = max(0, screen_w - target_w)
                self.full_w = target_w
                self.full_h = new_h
                self.sidebar_w = target_w
                self.sidebar_h = new_h
                self.apply_geometry()
                self.save_config()
                self.log_cmd(f"📐 แนบขอบจอ: {target_w}x{new_h}")
                return

            gx1, gy1, gx2, gy2 = win32gui.GetWindowRect(game_hwnd)
            win_center_x = self.pos_x + (self.win_bg.winfo_width() // 2)

            if win_center_x < (gx1 + gx2) // 2:
                # 👈 อยู่ฝั่งซ้ายของเกม: ยึดขอบจอซ้ายถึงขอบเกมซ้าย
                new_x = 0
                available_w = max(160, gx1 - new_x)
                new_w = min(available_w, 280) if available_w > 160 else 176
            else:
                # 👉 อยู่ฝั่งขวาของเกม: ยึดขอบขวาของเกมถึงขอบจอขวา
                new_x = gx2
                available_w = max(160, screen_w - gx2)
                new_w = min(available_w, 280) if available_w > 160 else 176

            # คงตำแหน่ง Y และความสูง H เดิมไว้ ไม่ยืดลงสุดจอ
            self.pos_x = new_x
            self.full_w = new_w
            self.full_h = new_h
            if new_w <= 240:
                self.sidebar_w = new_w
                self.sidebar_h = new_h
            else:
                self.v2_w = new_w
                self.v2_h = new_h

            self.apply_geometry()
            self.save_config()
            self.log_cmd(f"📐 Snap เกม: {new_w}x{new_h}")
        except Exception as err:
            self.log_cmd(f"⚠️ Snap error: {err}")


    def set_preset_size(self, w, h):
        """ปุ่มลัดเลือกขนาดหน้าต่าง S/M/L ในตั้งค่า"""
        self.full_w = w
        self.full_h = h
        self.mini_w = w
        if not self.is_mini:
            self.apply_geometry()
            self.setup_ui_elements()
        self.save_config()

    def toggle_mini_mode(self):
        # ล็อกพิกัดจริงล่าสุดก่อนสลับโหมด เพื่อให้ตำแหน่งนิ่งสนิท 100%
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
        except Exception:
            pass

        self.is_mini = not self.is_mini
        self.apply_geometry()
        self.setup_ui_elements()
        self.save_config()

    def toggle_vertical_hud_mode(self, e=None):
        """สลับโหมดหน้าต่างระหว่าง V.2 ปกติ (แนวนอน 460x275) กับ Vertical Sidebar (แถบข้าง 170x380)"""
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
        except Exception:
            pass

        cur_w = self.win_bg.winfo_width() if self.win_bg.winfo_width() > 100 else getattr(self, 'full_w', 170)
        cur_h = self.win_bg.winfo_height() if self.win_bg.winfo_height() > 50 else getattr(self, 'full_h', 380)

        if cur_w <= 240:
            # อยู่โหมดแนวตั้ง (Sidebar) -> จำขนาด sidebar ล่าสุดไว้ แล้วสลับไป V.2 แนวนอน
            self.sidebar_w = cur_w
            self.sidebar_h = max(520, cur_h)
            self.full_w = getattr(self, 'v2_w', 491)
            self.full_h = getattr(self, 'v2_h', 444)
        else:
            # อยู่โหมดแนวนอน V.2 -> จำขนาด V.2 ล่าสุดไว้ แล้วสลับเป็น Vertical Sidebar
            self.v2_w = cur_w
            self.v2_h = cur_h
            self.full_w = max(160, getattr(self, 'sidebar_w', 184))
            self.full_h = max(540, getattr(self, 'sidebar_h', 768))

        self.apply_geometry()
        self.setup_ui_elements()
        self.save_config()

    def update_auto_scale_ui(self, width=None):
        """ออโต้สเกลขนาดตัวอักษรและรูปแบบข้อความในกรอบสีเขียวตามความกว้างหน้าต่างจริง Real-time"""
        if getattr(self, 'is_mini', False):
            return
        try:
            w = width or self.win_bg.winfo_width()
        except:
            w = getattr(self, 'full_w', 460)

        if not w or w <= 100:
            w = getattr(self, 'full_w', 460)

        # 1. แถบหัวเขียว (BOOST DROP! & Rate)
        if hasattr(self, 'lbl_flame') and self.lbl_flame.winfo_exists():
            if w <= 240:
                self.lbl_flame.config(text="💧 BOOST", font=("Segoe UI", 7, "bold"))
            elif w < 380:
                self.lbl_flame.config(text="💧 BOOST", font=("Segoe UI", 7, "bold"))
            else:
                self.lbl_flame.config(text="💧 BOOST DROP!", font=("Segoe UI", 7, "bold"))

        # ย่อปุ่มสลับโหมดและปุ่มเลือกแมพเมื่อจอแคบ
        if hasattr(self, 'lbl_title') and self.lbl_title.winfo_exists():
            self.lbl_title.config(text="⇋ โหมด" if w <= 240 else "⇋ แถบข้าง")
        if hasattr(self, 'lbl_arr') and self.lbl_arr.winfo_exists():
            self.lbl_arr.config(text="▾" if w <= 240 else "เลือกแมพ ▾ ")
        if hasattr(self, 'lbl_map_main') and self.lbl_map_main.winfo_exists():
            self.lbl_map_main.config(wraplength=max(80, w - 50))
        if hasattr(self, 'lbl_map_sub') and self.lbl_map_sub.winfo_exists():
            self.lbl_map_sub.config(wraplength=max(80, w - 50))

        # 2. ปรับขนาด Font และข้อความตามความกว้างหน้าต่าง (พร้อมรองรับ custom_font_size จากหน้าต่างตั้งค่า)
        c_fs = getattr(self, 'custom_font_size', 0)
        if c_fs and c_fs > 0:
            # ผู้ใช้ระบุขนาดตัวอักษรเอง (Custom Font Size)
            sz_main = c_fs
            sz_sub = max(5, c_fs - 1)
            f_main_lbl = ("Segoe UI", sz_main, "bold")
            f_main_val = ("Consolas", sz_main, "bold")
            f_sub_lbl = ("Segoe UI", sz_sub)
            f_sub_val = ("Consolas", sz_sub, "bold")
            if w <= 240:
                unit_neso = " N"
                sure_prefix = "[พื้นฐาน] "
                extra_prefix = "[+1] "
                rate_prefix = "📊 "
            else:
                unit_neso = " NESO"
                sure_prefix = "[พื้นฐาน] "
                extra_prefix = "[+1] "
                rate_prefix = "📊 ดรอป:"
        elif w >= 450:
            f_main_lbl = ("Segoe UI", 9, "bold")
            f_main_val = ("Consolas", 10, "bold")
            f_sub_lbl = ("Segoe UI", 7)
            f_sub_val = ("Consolas", 7, "bold")
            unit_neso = " NESO"
            sure_prefix = "[พื้นฐาน] "
            extra_prefix = "[+1 ดรอป] "
            rate_prefix = "📊 อัตราดรอป:"
        elif w >= 390:
            f_main_lbl = ("Segoe UI", 8, "bold")
            f_main_val = ("Consolas", 9, "bold")
            f_sub_lbl = ("Segoe UI", 7)
            f_sub_val = ("Consolas", 7, "bold")
            unit_neso = " NESO"
            sure_prefix = "[พื้นฐาน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 ดรอป:"
        elif w <= 240: # แคบพิเศษแบบแถบข้าง Vertical HUD
            f_main_lbl = ("Segoe UI", 7, "bold")
            f_main_val = ("Consolas", 7, "bold")
            f_sub_lbl = ("Segoe UI", 6)
            f_sub_val = ("Consolas", 6, "bold")
            unit_neso = " N"
            sure_prefix = "[พื้นฐาน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 "
        else: # แคบปานกลาง (< 390)
            f_main_lbl = ("Segoe UI", 7, "bold")
            f_main_val = ("Consolas", 8, "bold")
            f_sub_lbl = ("Segoe UI", 6)
            f_sub_val = ("Consolas", 6, "bold")
            unit_neso = " N"
            sure_prefix = "[พื้นฐาน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 ดรอป:"

        # คำนวณความกว้างสูงสุดสำหรับตัดบรรทัดแยกตามหมวด (Category-isolated auto-wrap)
        content_w = max(100, w - 24)

        # -------------------------------------------------------------
        # 🔴 ฟิกขนาด Font โซนเวลา, กระเป๋า และ เหรียญ Badges ให้คงที่ทั้งสองโหมด
        #    (ไม่ปรับตาม custom_font_size หรือความกว้างหน้าต่าง ตามคำสั่งฟิกถาวร)
        # -------------------------------------------------------------
        timer_sz = 17
        wal_sz = 13
        badge_sz = 17

        if getattr(self, 'lbl_timer_text', None) is not None and self.lbl_timer_text.winfo_exists():
            self.lbl_timer_text.config(font=("Consolas", timer_sz, "bold"))
        if hasattr(self, 'lbl_wallet_neso_val') and self.lbl_wallet_neso_val.winfo_exists():
            self.lbl_wallet_neso_val.config(font=("Consolas", wal_sz, "bold"))
        if hasattr(self, 'lbl_nesolet') and self.lbl_nesolet.winfo_exists():
            self.lbl_nesolet.config(font=("Consolas", wal_sz, "bold"))
        if hasattr(self, 'lbl_neso_badge_norm_stock') and self.lbl_neso_badge_norm_stock.winfo_exists():
            self.lbl_neso_badge_norm_stock.config(font=("Consolas", badge_sz, "bold"))
        if hasattr(self, 'lbl_neso_badge_stock') and self.lbl_neso_badge_stock.winfo_exists():
            self.lbl_neso_badge_stock.config(font=("Consolas", badge_sz, "bold"))

        # -------------------------------------------------------------
        # 🟢 หมวด 1: อัปเดต Font และข้อความ Label แถว 1 (⚡Drop+BOOTs)
        #    (ตามคำสั่ง: เฉพาะบรรทัดนี้ ค่าดีฟอลตัวเลขใหญ่ขึ้น 2 size, ตัวอักษรลดลง 1 size)
        # -------------------------------------------------------------
        row1_lbl_sz = max(6, f_main_lbl[1] - 1)
        row1_val_sz = f_main_val[1] + 2
        f_row1_lbl = ("Segoe UI", row1_lbl_sz, "bold")
        f_row1_val = ("Consolas", row1_val_sz, "bold")

        if hasattr(self, 'lbl_exp_t') and self.lbl_exp_t.winfo_exists():
            self.lbl_exp_t.config(text="⚡Drop+BOOTs", font=f_row1_lbl)
        if hasattr(self, 'lbl_boost_expected') and self.lbl_boost_expected.winfo_exists():
            self.lbl_boost_expected.config(font=f_row1_val, wraplength=content_w)
            if hasattr(self, 'neso_boost_total_min') and getattr(self, 'neso_boost_total_max', 0) > 0:
                self.lbl_boost_expected.config(text=f"{self.neso_boost_total_min:.2f} ~ {self.neso_boost_total_max:.2f}{unit_neso}")

        # Dynamic Line-Wrap สำหรับแถว 1: ถ้าจอแคบ (<= 240) หรือฟอนต์ใหญ่ (>= 10) ให้แยกเป็น 2 บรรทัด
        if hasattr(self, 'lbl_exp_t') and hasattr(self, 'lbl_boost_expected'):
            if self.lbl_exp_t.winfo_exists() and self.lbl_boost_expected.winfo_exists():
                if w <= 240 or (c_fs and c_fs >= 10):
                    self.lbl_exp_t.pack_configure(side=tk.TOP, anchor="center")
                    self.lbl_boost_expected.pack_configure(side=tk.TOP, anchor="center", padx=(0, 0))
                else:
                    self.lbl_exp_t.pack_configure(side=tk.LEFT, anchor="center")
                    self.lbl_boost_expected.pack_configure(side=tk.LEFT, anchor="center", padx=(4, 0))

        # -------------------------------------------------------------
        # 🟢 หมวด 1: อัปเดต Font และข้อความ Label แถว 2 ([แน่นอน] + [+1])
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_sure_t') and self.lbl_sure_t.winfo_exists():
            self.lbl_sure_t.config(text=sure_prefix, font=f_main_lbl)
        if hasattr(self, 'lbl_boost_sure_val') and self.lbl_boost_sure_val.winfo_exists():
            self.lbl_boost_sure_val.config(font=f_main_val, wraplength=content_w)
            if hasattr(self, 'neso_boost_sure_min') and getattr(self, 'neso_boost_sure_max', 0) > 0:
                self.lbl_boost_sure_val.config(text=f"{self.neso_boost_sure_min:.2f} ~ {self.neso_boost_sure_max:.2f}{unit_neso}")
        if hasattr(self, 'lbl_sure_p') and self.lbl_sure_p.winfo_exists():
            self.lbl_sure_p.config(font=f_main_lbl)
        if hasattr(self, 'lbl_extra_t') and self.lbl_extra_t.winfo_exists():
            self.lbl_extra_t.config(text=extra_prefix, font=f_main_lbl)
        if hasattr(self, 'lbl_boost_sure_rate') and self.lbl_boost_sure_rate.winfo_exists():
            self.lbl_boost_sure_rate.config(font=f_main_val, wraplength=content_w)

        # Dynamic Line-Wrap สำหรับแถว 2 เมื่อหน้าต่างถูกบีบแคบ หรือเมื่อฟอนต์ถูกขยายใหญ่จนล้น
        font_threshold = 445 if (not c_fs or c_fs <= 8) else 520
        if hasattr(self, 'f_sure_part1') and hasattr(self, 'f_sure_part2'):
            if self.f_sure_part1.winfo_exists() and self.f_sure_part2.winfo_exists():
                if w < font_threshold or (c_fs and c_fs >= 10):
                    self.f_sure_part1.pack_configure(side=tk.TOP, anchor="center")
                    self.f_sure_part2.pack_configure(side=tk.TOP, anchor="center", pady=(1, 0))
                    if hasattr(self, 'lbl_sure_p') and self.lbl_sure_p.winfo_exists():
                        self.lbl_sure_p.config(text="+ ")
                    # ✅ เมื่อฟอนต์ >= 11: แยก [+1 label] กับ [ค่า] ออกเป็น 2 บรรทัดใน f_sure_part2
                    if c_fs and c_fs >= 11:
                        if hasattr(self, 'lbl_extra_t') and self.lbl_extra_t.winfo_exists():
                            self.lbl_extra_t.pack_configure(side=tk.TOP, anchor="center")
                        if hasattr(self, 'lbl_boost_sure_rate') and self.lbl_boost_sure_rate.winfo_exists():
                            self.lbl_boost_sure_rate.pack_configure(side=tk.TOP, anchor="center", padx=(0, 0))
                            self.lbl_boost_sure_rate.config(wraplength=max(50, content_w - 10))
                    else:
                        if hasattr(self, 'lbl_extra_t') and self.lbl_extra_t.winfo_exists():
                            self.lbl_extra_t.pack_configure(side=tk.LEFT, anchor="center")
                        if hasattr(self, 'lbl_boost_sure_rate') and self.lbl_boost_sure_rate.winfo_exists():
                            self.lbl_boost_sure_rate.pack_configure(side=tk.LEFT, anchor="center")
                            self.lbl_boost_sure_rate.config(wraplength=max(50, content_w))
                else:
                    self.f_sure_part1.pack_configure(side=tk.LEFT, anchor="center")
                    self.f_sure_part2.pack_configure(side=tk.LEFT, anchor="center", pady=(0, 0))
                    if hasattr(self, 'lbl_sure_p') and self.lbl_sure_p.winfo_exists():
                        self.lbl_sure_p.config(text=" + ")
                    if hasattr(self, 'lbl_extra_t') and self.lbl_extra_t.winfo_exists():
                        self.lbl_extra_t.pack_configure(side=tk.LEFT, anchor="center")
                    if hasattr(self, 'lbl_boost_sure_rate') and self.lbl_boost_sure_rate.winfo_exists():
                        self.lbl_boost_sure_rate.pack_configure(side=tk.LEFT, anchor="center")
                        self.lbl_boost_sure_rate.config(wraplength=max(80, content_w))

        # -------------------------------------------------------------
        # 🟢 หมวด 2: อัปเดต Font Label แถว 3 (📊 อัตราดรอป)
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_rate_t') and self.lbl_rate_t.winfo_exists():
            self.lbl_rate_t.config(text=rate_prefix, font=f_sub_lbl)
        if hasattr(self, 'lbl_boost_rate_total') and self.lbl_boost_rate_total.winfo_exists():
            self.lbl_boost_rate_total.config(font=f_sub_val)
        if hasattr(self, 'lbl_boost_rate_breakdown') and self.lbl_boost_rate_breakdown.winfo_exists():
            self.lbl_boost_rate_breakdown.config(font=f_sub_val, wraplength=content_w)

        # Dynamic Line-Wrap สำหรับแถว 3: ถ้าจอแคบ หรือฟอนต์ใหญ่ ให้ตัด breakdown ขึ้นบรรทัดใหม่
        if hasattr(self, 'f_rate_part1') and hasattr(self, 'f_rate_part2'):
            if self.f_rate_part1.winfo_exists() and self.f_rate_part2.winfo_exists():
                if w <= 240 or (c_fs and c_fs >= 10):
                    self.f_rate_part1.pack_configure(side=tk.TOP, anchor="center")
                    self.f_rate_part2.pack_configure(side=tk.TOP, anchor="center", padx=(0, 0))
                else:
                    self.f_rate_part1.pack_configure(side=tk.LEFT, anchor="center")
                    self.f_rate_part2.pack_configure(side=tk.LEFT, anchor="center", padx=(2, 0))

        # -------------------------------------------------------------
        # 🟢 แถว 4: ข้อมูล Stock / Charge
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_stk_t') and self.lbl_stk_t.winfo_exists():
            self.lbl_stk_t.config(font=f_sub_lbl)
        if hasattr(self, 'lbl_neso_boost_stock') and self.lbl_neso_boost_stock.winfo_exists():
            self.lbl_neso_boost_stock.config(font=f_sub_val)
        if hasattr(self, 'lbl_chg_t') and self.lbl_chg_t.winfo_exists():
            self.lbl_chg_t.config(font=f_sub_lbl)
        if hasattr(self, 'lbl_neso_boost_charge') and self.lbl_neso_boost_charge.winfo_exists():
            self.lbl_neso_boost_charge.config(font=f_sub_val)

        # Dynamic Line-Wrap สำหรับแถว 4: ถ้าจอแคบ หรือฟอนต์ใหญ่ ให้ตัด charge ขึ้นบรรทัดใหม่
        if hasattr(self, 'f_stk_part1') and hasattr(self, 'f_stk_part2'):
            if self.f_stk_part1.winfo_exists() and self.f_stk_part2.winfo_exists():
                if w <= 240 or (c_fs and c_fs >= 10):
                    self.f_stk_part1.pack_configure(side=tk.TOP, anchor="center")
                    self.f_stk_part2.pack_configure(side=tk.TOP, anchor="center", padx=(0, 0))
                else:
                    self.f_stk_part1.pack_configure(side=tk.LEFT, anchor="center")
                    self.f_stk_part2.pack_configure(side=tk.LEFT, anchor="center", padx=(2, 0))

        # -------------------------------------------------------------
        # 🟢 แถบ Hot Farm Recommender: ตัดบรรทัดและปรับฟอนต์ให้สมส่วน
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_hot_map') and self.lbl_hot_map.winfo_exists():
            self.lbl_hot_map.config(font=f_sub_lbl, wraplength=max(70, w - 60))
        if hasattr(self, 'lbl_hot_rate') and self.lbl_hot_rate.winfo_exists():
            self.lbl_hot_rate.config(font=f_sub_val)
        if hasattr(self, 'lbl_hot_qty') and self.lbl_hot_qty.winfo_exists():
            self.lbl_hot_qty.config(font=f_sub_val)

    def toggle_compact_fold(self, e=None):
        """พับ/กาง หน้าต่างย่อแบบรูปที่ 1 (ซ่อนเฉพาะแถบแดงล่าง ข้อมูลบนครบถ้วน 100%)"""
        try:
            cur_x = self.win_bg.winfo_x()
            cur_y = self.win_bg.winfo_y()
            if cur_x > -10000 and cur_y > -10000:
                self.pos_x = cur_x
                self.pos_y = cur_y
        except Exception:
            pass

        self.is_compact_folded = not getattr(self, 'is_compact_folded', False)
        cur_w = self.win_bg.winfo_width() if self.win_bg.winfo_width() > 100 else self.full_w

        if self.is_compact_folded:
            # พับย่อ: ซ่อนเฉพาะแถบแดงล่าง เหลือข้อมูลครบตามรูปที่ 1 เป๊ะๆ
            if hasattr(self, 'f_red_box') and self.f_red_box.winfo_exists():
                self.f_red_box.pack_forget()
            if hasattr(self, 'btn_fold_toggle') and self.btn_fold_toggle.winfo_exists():
                self.btn_fold_toggle.config(text="▲ กางแถบควบคุมล่าง", bg="#2a1616", fg="#fca5a5")
            fold_h = max(520, getattr(self, 'sidebar_h', 768) - 140) if cur_w <= 240 else getattr(self, 'v2_h', 444)
            geom = f"{cur_w}x{fold_h}+{self.pos_x}+{self.pos_y}"
            self.win_bg.geometry(geom)
            self.win_fg.geometry(geom)
        else:
            # กางกลับมาครบทุกส่วน
            if hasattr(self, 'f_red_box') and self.f_red_box.winfo_exists():
                self.f_red_box.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=(1, 3))
            if hasattr(self, 'btn_fold_toggle') and self.btn_fold_toggle.winfo_exists():
                self.btn_fold_toggle.config(text="▼ พับเก็บแถบล่าง", bg="#161c28", fg="#64748b")
            full_h = max(580, getattr(self, 'sidebar_h', 768)) if cur_w <= 240 else getattr(self, 'full_h', 444)
            geom = f"{cur_w}x{full_h}+{self.pos_x}+{self.pos_y}"
            self.win_bg.geometry(geom)
            self.win_fg.geometry(geom)

        try:
            self.win_bg.update_idletasks()
            self.win_fg.update_idletasks()
            self.update_auto_scale_ui(cur_w)
            self.win_fg.lift()
        except:
            pass
        self.save_config()

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.save_config()
        self.setup_ui_elements()

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.save_config()
        self.setup_ui_elements()

    def switch_mode(self, new_mode):
        self.mode = new_mode
        self.manual_running = False
        self.has_alerted_2m = False
        self.has_alerted_19m30s = False
        self.has_alerted_0m = False
        self.save_config()
        self.setup_ui_elements()

    def switch_server(self, new_server):
        self.server_name = new_server
        server_map = {"Fang": 0, "Ain": 1, "Errai": 2}
        self.world_id = server_map.get(new_server, 0)
        self.save_config()
        self.setup_ui_elements()
        self.fetch_drop_data_async()

    def show_server_dropdown(self, widget=None):
        """กดแล้วสไลด์คลี่แถบเลือกเซิร์ฟเวอร์ลงมาในหน้าต่าง Overlay ทันที"""
        self.show_server_bar = not self.show_server_bar
        self.show_mode_bar = False
        if self.is_mini:
            self.mini_h = 94 if self.show_server_bar else 64
            self.apply_geometry()
        self.setup_ui_elements()

    def select_server_and_close(self, s_name):
        self.show_server_bar = False
        if self.is_mini:
            self.mini_h = 64
            self.apply_geometry()
        self.switch_server(s_name)

    def show_mode_dropdown(self, widget=None):
        """กดแล้วสไลด์คลี่แถบเลือกโหมดลงมาในหน้าต่าง Overlay ทันที"""
        self.show_mode_bar = not self.show_mode_bar
        self.show_server_bar = False
        if self.is_mini:
            self.mini_h = 94 if self.show_mode_bar else 64
            self.apply_geometry()
        self.setup_ui_elements()

    def select_mode_and_close(self, m_name):
        self.show_mode_bar = False
        if self.is_mini:
            self.mini_h = 64
            self.apply_geometry()
        self.switch_mode(m_name)

    def toggle_manual_play(self):
        self.manual_running = not self.manual_running
        self.last_manual_tick = time.time()
        self.setup_ui_elements()

    def reset_manual_timer(self):
        self.manual_remaining = 20 * 60
        self.manual_running = False
        self.has_alerted_2m = False
        self.has_alerted_0m = False
        self.play_alert(1000, 100)
        self.setup_ui_elements()

    def set_opacity(self, val):
        self.opacity = float(val)
        try:
            self.win_bg.attributes("-alpha", self.opacity)
        except:
            pass
        if hasattr(self, 'win_fg') and self.win_fg:
            try:
                self.win_fg.attributes("-alpha", 1.0)
            except:
                pass
        self.save_config()
        if self.settings_win and self.settings_win.winfo_exists():
            self.refresh_settings_ui()

    def cycle_opacity(self):
        """วนสลับความโปร่งแสงของพื้นหลัง (100% -> 60% -> 25% -> 0% -> 100%)
           โดยที่ตัวหนังสือสำคัญและกล่องการ์ดจะไม่จาง คมชัด 100% ตลอดเวลา!"""
        op_levels = [1.0, 0.60, 0.25, 0.0]
        cur_idx = 0
        min_diff = 999.0
        for i, lv in enumerate(op_levels):
            diff = abs(self.opacity - lv)
            if diff < min_diff:
                min_diff = diff
                cur_idx = i
        next_idx = (cur_idx + 1) % len(op_levels)
        next_op = op_levels[next_idx]
        self.set_opacity(next_op)
        pct = int(round(next_op * 100))
        self.log_cmd(f"🌓 พื้นหลัง: {pct}% (อักษร & การ์ดชัด 100%)")

    def play_alert(self, freq=1200, duration=200):
        if self.sound_enabled and HAS_WINSOUND:
            try:
                winsound.Beep(freq, duration)
            except:
                pass


    def setup_ui_elements(self):
        for w in self.main_container.winfo_children():
            w.destroy()

        if self.is_mini:
            # =========================================================
            # 🟢 โหมดจิ๋ว SLIM BAR
            # =========================================================
            bar = tk.Frame(self.main_container, bg=self.trans_key)
            bar.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
            bar.bind("<ButtonPress-1>", self.start_drag)
            bar.bind("<B1-Motion>", self.do_drag)
            bar.bind("<ButtonRelease-1>", self.end_drag)

            f_r = tk.Frame(bar, bg=self.trans_key)
            f_r.pack(side=tk.RIGHT)

            grip_m = tk.Label(f_r, text=" ◢ ", font=("Segoe UI", 9, "bold"), fg="#00f2fe", 
                              bg="#182230", cursor="size_nw_se", padx=2, pady=1, relief="groove", bd=1)
            grip_m.pack(side=tk.RIGHT, padx=(2, 0))
            grip_m.bind("<ButtonPress-1>", self.start_resize)
            grip_m.bind("<B1-Motion>", self.do_resize)
            grip_m.bind("<ButtonRelease-1>", self.end_resize)

            btn_x = tk.Label(f_r, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg=self.trans_key, cursor="hand2", width=2)
            btn_x.pack(side=tk.RIGHT, padx=1)
            btn_x.bind("<Button-1>", lambda e: self.close_app())

            btn_set = tk.Label(f_r, text="⚙", font=("Segoe UI", 9), fg="#94a3b8", bg=self.trans_key, cursor="hand2", width=2)
            btn_set.pack(side=tk.RIGHT, padx=1)
            btn_set.bind("<Button-1>", lambda e: self.open_settings())

            btn_alpha_m = tk.Label(f_r, text="🌓", font=("Segoe UI", 9), fg="#38bdf8", bg=self.trans_key, cursor="hand2", width=2)
            btn_alpha_m.pack(side=tk.RIGHT, padx=1)
            btn_alpha_m.bind("<Button-1>", lambda e: self.cycle_opacity())
            btn_alpha_m.bind("<Enter>", lambda e: btn_alpha_m.config(fg="#ffffff"))
            btn_alpha_m.bind("<Leave>", lambda e: btn_alpha_m.config(fg="#38bdf8"))

            btn_exp = tk.Label(f_r, text="🗖", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg=self.trans_key, cursor="hand2", width=2)
            btn_exp.pack(side=tk.RIGHT, padx=1)
            btn_exp.bind("<Button-1>", lambda e: self.toggle_mini_mode())

            f_left_col = tk.Frame(bar, bg=self.trans_key)
            f_left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
            f_left_col.bind("<ButtonPress-1>", self.start_drag)
            f_left_col.bind("<B1-Motion>", self.do_drag)
            f_left_col.bind("<ButtonRelease-1>", self.end_drag)

            f_top_sub = tk.Frame(f_left_col, bg=self.trans_key)
            f_top_sub.pack(side=tk.TOP, anchor="w", fill=tk.X)
            f_top_sub.bind("<ButtonPress-1>", self.start_drag)
            f_top_sub.bind("<B1-Motion>", self.do_drag)
            f_top_sub.bind("<ButtonRelease-1>", self.end_drag)

            btn_srv = tk.Label(f_top_sub, text=f"[{self.server_name[:1]}▾]", font=("Consolas", 8, "bold"), 
                               fg="#f59e0b", bg=self.trans_key, cursor="hand2")
            btn_srv.pack(side=tk.LEFT, padx=(0, 1))
            btn_srv.bind("<Button-1>", lambda e, w=btn_srv: self.show_server_dropdown(w))

            mode_tag = "ST" if self.mode == "ServerTime" else "MN"
            lbl_m = tk.Label(f_top_sub, text=f"[{mode_tag}▾]", font=("Consolas", 8, "bold"), 
                             fg="#38ef7d" if self.mode == "ServerTime" else "#f59e0b", bg=self.trans_key, cursor="hand2")
            lbl_m.pack(side=tk.LEFT, padx=(0, 1))
            lbl_m.bind("<Button-1>", lambda e, w=lbl_m: self.show_mode_dropdown(w))

            btn_mini_scan = tk.Label(f_top_sub, text="[🔍]", font=("Consolas", 8, "bold"),
                                     fg="#38bdf8", bg=self.trans_key, cursor="hand2")
            btn_mini_scan.pack(side=tk.LEFT, padx=(0, 2))
            btn_mini_scan.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

            self.lbl_clock_mini = tk.Label(f_top_sub, text="00:00:00", font=("Consolas", 8, "bold"), 
                                           fg="#94a3b8", bg=self.trans_key)
            self.lbl_clock_mini.pack(side=tk.LEFT, padx=(1, 3))
            self.lbl_clock_mini.bind("<ButtonPress-1>", self.start_drag)
            self.lbl_clock_mini.bind("<B1-Motion>", self.do_drag)

            self.lbl_time_mini = tk.Label(f_top_sub, text="00:00", font=("Consolas", 12, "bold"), 
                                          fg="#ffffff", bg=self.trans_key)
            self.lbl_time_mini.pack(side=tk.LEFT, padx=(1, 2))
            self.lbl_time_mini.bind("<ButtonPress-1>", self.start_drag)
            self.lbl_time_mini.bind("<B1-Motion>", self.do_drag)

            if self.mode == "Manual":
                play_ico = "⏸" if self.manual_running else "▶"
                btn_p = tk.Label(f_top_sub, text=play_ico, font=("Segoe UI", 8, "bold"), 
                                 fg="#38ef7d" if self.manual_running else "#f59e0b", bg=self.trans_key, cursor="hand2")
                btn_p.pack(side=tk.LEFT, padx=(0, 2))
                btn_p.bind("<Button-1>", lambda e: self.toggle_manual_play())

            # (ร.1) กรอบแสดงชื่อแผนที่ สีแดง (เข้ม) เพื่อความโดดเด่น
            f_map_mini = tk.Frame(f_left_col, bg="#3a1c1c", bd=1, relief="solid", highlightbackground="#ef4444", highlightthickness=1, cursor="hand2", padx=3, pady=1)
            f_map_mini.pack(side=tk.TOP, anchor="w", fill=tk.X, pady=(2, 0))
            f_map_mini.bind("<Button-1>", lambda e: self.open_map_picker())

            self.lbl_mini_map = tk.Label(f_map_mini, text="🗺️ รอตรวจจับแมพ...", font=("Segoe UI", 7, "bold"), 
                                         fg="#ffffff", bg="#3a1c1c", cursor="hand2")
            self.lbl_mini_map.pack(side=tk.LEFT, anchor="w")
            self.lbl_mini_map.bind("<Button-1>", lambda e: self.open_map_picker())

            f_m_norm = tk.Frame(bar, bg="#161f2e", bd=1, relief="solid", padx=4, pady=2, cursor="hand2")
            f_m_norm.pack(side=tk.LEFT, padx=2)
            f_m_norm.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_mini_norm_rate = tk.Label(f_m_norm, text="Town", font=("Consolas", 8, "bold"), fg="#64748b", bg="#161f2e")
            self.lbl_mini_norm_rate.pack(anchor="w")
            self.lbl_mini_norm_rate.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_mini_norm_stock = tk.Label(f_m_norm, text="--", font=("Consolas", 8, "bold"), fg="#94a3b8", bg="#161f2e")
            self.lbl_mini_norm_stock.pack(anchor="w")
            self.lbl_mini_norm_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            f_m_boost = tk.Frame(bar, bg="#241b12", bd=1, relief="solid", padx=4, pady=2, cursor="hand2")
            f_m_boost.pack(side=tk.LEFT, padx=2)
            f_m_boost.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_mini_boost_rate = tk.Label(f_m_boost, text="Town", font=("Consolas", 8, "bold"), fg="#64748b", bg="#241b12")
            self.lbl_mini_boost_rate.pack(anchor="w")
            self.lbl_mini_boost_rate.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_mini_boost_stock = tk.Label(f_m_boost, text="--", font=("Consolas", 8, "bold"), fg="#fbbf24", bg="#241b12")
            self.lbl_mini_boost_stock.pack(anchor="w")
            self.lbl_mini_boost_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # แสดงยอดเงินย่อใน Mini Mode
            f_m_wal = tk.Frame(bar, bg="#1a1c29", bd=1, relief="solid", padx=4, pady=2, cursor="hand2")
            f_m_wal.pack(side=tk.LEFT, padx=2)
            f_m_wal.bind("<Button-1>", lambda e: self.open_wallet_inapp_modal())
            self.lbl_mini_wallet_neso = tk.Label(f_m_wal, text="💰...", font=("Consolas", 8, "bold"), fg="#c084fc", bg="#1a1c29")
            self.lbl_mini_wallet_neso.pack(anchor="w")
            self.lbl_mini_wallet_neso.bind("<Button-1>", lambda e: self.open_wallet_inapp_modal())

        else:
            # =========================================================
            # 🔵 โหมดเต็ม FULL OVERLAY (Modular Component Layout)
            # =========================================================
            # 1. แถบ Title Bar ด้านบนสุด (Widget 1)
            self.frame_title = TitleFrame(self.main_container, self)
            self.frame_title.pack(fill=tk.X, side=tk.TOP)

            # 2. แถบ Map Banner ใต้ Title Bar (Widget 2)
            self.frame_map = MapBannerFrame(self.main_container, self)
            self.frame_map.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 3))

            # ---------------------------------------------------------
            # 🎯 กรอบ Pool Zone (เส้นขอบสีเหลือง)
            # ---------------------------------------------------------
            self.f_pool_zone = tk.Frame(self.main_container, bg=self.trans_key, bd=1, highlightbackground="#f59e0b", highlightthickness=1)
            self.f_pool_zone.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
            self.f_pool_zone.bind("<ButtonPress-1>", self.start_drag)
            self.f_pool_zone.bind("<B1-Motion>", self.do_drag)
            self.f_pool_zone.bind("<ButtonRelease-1>", self.end_drag)

            # 3. Timer Zone (Widget 3)
            self.frame_timer = TimerFrame(self.f_pool_zone, self)
            self.frame_timer.pack(side=tk.TOP, fill=tk.X, padx=1, pady=(0, 1))

            # 4. Wallet Frame (Widget 4)
            self.frame_wallet = WalletFrame(self.frame_timer, self)
            self.frame_wallet.pack(side=tk.TOP, fill=tk.X, padx=1, pady=(1, 1))

            # 5. Badges Frame (Widget 5)
            self.frame_badges = BadgesFrame(self.frame_timer, self)
            self.frame_badges.pack(side=tk.TOP, fill=tk.X, padx=1, pady=(1, 1))

            # Boost Container
            self.c_boost_container = tk.Frame(self.f_pool_zone, bg=self.trans_key)
            self.c_boost_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(2, 0))

            # 6. Boost Top Header (Widget 6)
            self.frame_boost_top = BoostTopFrame(self.c_boost_container, self)
            self.frame_boost_top.pack(side=tk.TOP, fill=tk.X, pady=(0, 1))

            # Boost Bottom Area
            self.c_boost_bot = tk.Frame(self.c_boost_container, bg=self.trans_key, bd=0, cursor="hand2")
            self.c_boost_bot.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
            self.c_boost_bot.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # 7. Safe Zone Banner (Widget 7)
            self.frame_safe_zone = SafeZoneFrame(self.c_boost_bot, self)
            self.f_safe_zone_banner = self.frame_safe_zone

            # 8. Pool Info Frame 4 แถว (Widget 8)
            self.frame_pool_info = PoolInfoFrame(self.c_boost_bot, self)
            self.f_boost_info_left = self.frame_pool_info

            # พื้นที่ล่างของ Boost Zone
            self.f_bot_action = tk.Frame(self.c_boost_bot, bg=self.trans_key)
            self.f_bot_action.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=3, pady=(1, 2))

            # 9. Hot Farm Recommender (Widget 9)
            self.frame_hot_farm = HotFarmFrame(self.f_bot_action, self)
            self.frame_hot_farm.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
            self.f_hot_farm = self.frame_hot_farm

            # Mini CMD Terminal Box
            f_cmd_box = tk.Frame(self.f_bot_action, bg="#08101a", bd=1, relief="solid",
                                 highlightbackground="#1e293b", highlightthickness=1)
            f_cmd_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(1, 1))
            self.f_cmd_box = f_cmd_box

            self.btn_snap_game = tk.Label(f_cmd_box, text=" 📐 ", font=("Segoe UI", 7, "bold"),
                                          fg="#38bdf8", bg="#0f172a", relief="solid", bd=1,
                                          highlightbackground="#38bdf8", highlightthickness=1,
                                          cursor="hand2", padx=2, pady=0)
            self.btn_snap_game.pack(side=tk.RIGHT, anchor="se")
            self.btn_snap_game.bind("<Button-1>", lambda e: self.snap_to_game_bounds())

            self.txt_cmd = StrokeLabel(f_cmd_box, text=">_ พร้อมทำงาน...", font=("Consolas", 11),
                                       fg="#38bdf8", bg="#08101a", stroke_color="#000000", stroke_width=1,
                                       anchor="nw", justify="left")
            self.txt_cmd.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=2)
            self.txt_cmd.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

            def _on_cmd_resize(e=None):
                if hasattr(self, 'txt_cmd') and self.txt_cmd and self.txt_cmd.winfo_exists():
                    w = f_cmd_box.winfo_width()
                    if w > 50:
                        self.txt_cmd.config(wraplength=max(80, w - 28))
            f_cmd_box.bind("<Configure>", _on_cmd_resize)

            # 10. Status Footer (Widget 10)
            self.frame_footer = StatusFooterFrame(self.f_bot_action, self)
            self.frame_footer.pack(side=tk.TOP, fill=tk.X, pady=(1, 16))
            self.f_status_footer = self.frame_footer

            # 🕹️ Grip ปรับขนาดมุมขวาล่างสุด
            if hasattr(self, 'grip_win') and self.grip_win is not None:
                try:
                    self.grip_win.destroy()
                except:
                    pass
            self.grip_win = tk.Label(self.win_fg, text=" ◢ ", font=("Segoe UI", 8, "bold"),
                                      fg="#ffffff", bg="#dc2626", relief="solid", bd=1,
                                      highlightbackground="#ffffff", highlightthickness=1,
                                      cursor="size_nw_se", padx=2, pady=0)
            self.grip_win.place(relx=1.0, rely=1.0, anchor="se")
            self.grip_win.lift()
            self.grip_win.bind("<ButtonPress-1>", self.start_resize)
            self.grip_win.bind("<B1-Motion>", self.do_resize)
            self.grip_win.bind("<ButtonRelease-1>", self.end_resize)
            self.grip_fold = self.grip_win

            # 🗂️ ปุ่มเมนูแถบล่าง
            if hasattr(self, 'btn_bottom_menu') and self.btn_bottom_menu is not None:
                try:
                    self.btn_bottom_menu.destroy()
                except:
                    pass
            self.btn_bottom_menu = tk.Label(self.win_fg, text=" ▲ แถบล่าง ", font=("Segoe UI", 7, "bold"),
                                            fg="#38bdf8", bg="#182230", relief="solid", bd=1,
                                            highlightbackground="#38bdf8", highlightthickness=1,
                                            cursor="hand2", padx=3, pady=0)
            self.btn_bottom_menu.place(relx=0.0, rely=1.0, anchor="sw")
            self.btn_bottom_menu.lift()
            self.btn_bottom_menu.bind("<Button-1>", lambda e: self.open_bottom_panel_modal())
            self.btn_fold_toggle = self.btn_bottom_menu

        # เรียก update_drop_ui() ท้ายสุดเพื่อให้ label แสดงค่าปัจจุบันทันที (ไม่กระพริบ)
        self.update_drop_ui()
        self.update_auto_scale_ui()

    def trigger_scan_and_refresh(self):
        """รวม Scan Map + Refresh ข้อมูลดรอป+กระเป๋า (ไม่สแกนตัวละครซ้ำให้รก)"""
        # รีเซ็ต last_ocr_map_str เพื่อบังคับ fresh scan (กดปุ่มเอง = ต้องการ full refresh)
        self.last_ocr_map_str = ""
        self.auto_detect_map_async(silent=False)
        self.fetch_drop_data_async()

    def _update_nxpc_label(self):
        val_str = f"฿{self.nxpc_thb:.2f}" if self.show_nxpc_thb else f"${self.nxpc_usd:.4f}"
        if getattr(self, 'lbl_nxpc', None) is not None and self.lbl_nxpc.winfo_exists():
            self.lbl_nxpc.config(text=f"NXPC: {val_str}")
        if getattr(self, 'lbl_bp_nxpc', None) is not None and self.lbl_bp_nxpc.winfo_exists():
            self.lbl_bp_nxpc.config(text=f"NXPC: {val_str}")

    def toggle_nxpc_currency(self):
        self.show_nxpc_thb = not self.show_nxpc_thb
        self._update_nxpc_label()



    def redraw_circular_timer(self, remaining_seconds, total_seconds, countdown_str, theme_color):
        """วาดหลอดแคปซูลเวลานับถอยหลังนีออน HUD ฝังตัวเลขนับเวลาขนาด 15 bold ไว้ตรงกลางหลอด"""
        canvas = getattr(self, 'canvas_timer_capsule', getattr(self, 'canvas_timer_ring', None))
        if not canvas or not canvas.winfo_exists():
            return
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            cw = 120
            ch = 28
        canvas.delete("all")

        pad_x = 2
        pad_y = 2
        bar_w = cw - (pad_x * 2)
        bar_h = ch - (pad_y * 2)

        # 1. หลอดพื้นหลังแคปซูล (Dark Capsule Background with border)
        canvas.create_rectangle(pad_x, pad_y, pad_x + bar_w, pad_y + bar_h,
                                fill="#090d16", outline="#1e293b", width=1)

        # 2. หลอดความคืบหน้าเวลา (Progress Fill)
        fraction = max(0.0, min(1.0, (remaining_seconds / total_seconds) if total_seconds > 0 else 0.0))
        fill_w = bar_w * fraction
        if fill_w > 0:
            # ใช้สีเข้ม/โปร่งตาเล็กน้อยสำหรับพื้นหลอด และมีเส้นแถบหัวหลอดเรืองแสง
            canvas.create_rectangle(pad_x + 1, pad_y + 1, pad_x + fill_w, pad_y + bar_h - 1,
                                    fill="#132738" if theme_color == "#00f2fe" else "#231e13", outline="")
            # เส้นขอบบนหลอดวิ่ง
            canvas.create_line(pad_x + 1, pad_y + 1, pad_x + fill_w, pad_y + 1,
                               fill=theme_color, width=1)
            # เส้นขอบล่างหลอดวิ่ง
            canvas.create_line(pad_x + 1, pad_y + bar_h - 1, pad_x + fill_w, pad_y + bar_h - 1,
                               fill=theme_color, width=1)
            # แถบไฟนีออนนำหน้า (Leading Neon Head)
            head_x = pad_x + fill_w
            canvas.create_line(head_x, pad_y + 1, head_x, pad_y + bar_h - 1,
                               fill=theme_color, width=2)

        # 3. ตัวเลขเวลานับถอยหลัง ขนาด 15 bold คมชัดตรงกลางหลอดแคปซูล (Shadow + Text)
        cx = cw / 2
        cy = ch / 2
        canvas.create_text(cx + 1, cy + 1, text=countdown_str,
                           font=("Consolas", 15, "bold"), fill="#000000")
        canvas.create_text(cx, cy, text=countdown_str,
                           font=("Consolas", 15, "bold"), fill=theme_color)

    def calculate_remaining(self):
        total_cycle = 20 * 60 # 1200 วินาที
        if self.mode == "ServerTime":
            now = datetime.now()
            sec_in_hour = now.minute * 60 + now.second
            passed = sec_in_hour % total_cycle
            remaining = total_cycle - passed
            if remaining == total_cycle:
                remaining = 0
            return remaining, total_cycle
        else:
            now_time = time.time()
            elapsed = now_time - self.last_manual_tick
            self.last_manual_tick = now_time
            if self.manual_running:
                self.manual_remaining -= elapsed
                if self.manual_remaining <= 0:
                    self.manual_remaining = total_cycle
            return max(0, int(self.manual_remaining)), total_cycle

    def update_clock_loop(self):
        # บังคับเลเยอร์ตามสูตร MS
        if getattr(self, 'win_fg', None) and self.win_fg.winfo_viewable():
            self.win_fg.lift()
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
        if self.map_picker_win and self.map_picker_win.winfo_exists():
            self.map_picker_win.lift()

        # เวลาไทยปัจจุบัน (Center)
        now = datetime.now()
        date_str = now.strftime("%d/%m/%y")
        time_real_str = now.strftime("%H:%M:%S")

        remaining_seconds, total_seconds = self.calculate_remaining()
        mins = int(remaining_seconds) // 60
        secs = int(remaining_seconds) % 60
        countdown_str = f"{mins:02d}:{secs:02d}"

        # 🔄 ตรวจสอบหน้าต่างเกมเพื่อสลับโหมด 8s (Active) / 16s (Eco 50% เมื่อพับจอ)
        is_game_active = False
        try:
            fg_hwnd = win32gui.GetForegroundWindow()
            if fg_hwnd:
                fg_title = win32gui.GetWindowText(fg_hwnd).lower()
                if "maplestory" in fg_title:
                    is_game_active = True
        except Exception:
            is_game_active = True
            
        # 🔄 ตรวจสอบสถานะ: กำลังฟาร์ม / พัก / อยู่ในเมือง / พับจอเกม เพื่อปรับจังหวะการดึงข้อมูล Drop และ Nesolet แบบ Dynamic
        is_tracking_farm = False
        if hasattr(self, 'income_tracker') and getattr(self.income_tracker, 'is_tracking', False):
            is_tracking_farm = True

        is_in_town = getattr(self, 'is_in_town', False)

        # คำนวณช่วงเวลารีเฟรชตามการใช้งานจริง (อัปเกรดสูตรใหม่ เซฟคีย์ขั้นสุด!):
        # 1. อยู่ในเมือง (Town) -> ยืนนิ่งๆ ไม่มียอดดึงช้าๆ 15s
        # 2. ฟาร์มอยู่ (Farming) -> ดึงไวเนียนตา 5s (ถ้าพับจอปรับเป็น 8s)
        # 3. พัก/นอกรอบฟาร์ม (Idle/Paused) -> พักโควต้า 10s (ถ้าพับจอปรับเป็น 15s)
        if is_in_town:
            target_interval = 15
            state_tag = " [Town]"
        elif getattr(self, 'has_no_drop', False) or getattr(self, 'selected_layer_name', '') == "ไม่พบ":
            target_interval = 10 if is_game_active else 15
            state_tag = " [Idle]" if is_game_active else " [Idle-Bg]"
        else:
            # ดึงไวขึ้นถ้าอยู่ในแมพฟาร์มปกติ (ไม่จำเป็นต้องเปิด Mod Tracker ก็ได้)
            target_interval = 5 if is_game_active else 8
            state_tag = " [Farm]" if is_game_active else " [Farm-Bg]"

        self.current_poll_target_interval = target_interval

        # 🔄 เช็ครอบรีเฟรชข้อมูล Drop
        elapsed_fetch = time.time() - self.last_fetch_ts
        poll_remain = max(0, int(target_interval - elapsed_fetch))
        if elapsed_fetch >= target_interval:
            self.fetch_drop_data_async()
            poll_remain = target_interval

        # อัปเดตตัวนับเวลารีเช็คตรงกรอบสีแดง (นับถอยหลังตามค่าจริงที่แปรผันตามสถานะ)
        if hasattr(self, 'lbl_poll_countdown') and self.lbl_poll_countdown and self.lbl_poll_countdown.winfo_exists():
            if self.is_fetching:
                self.lbl_poll_countdown.config(text="⏳ กำลังดึง...", fg="#38bdf8")
            elif self.neso_boost_stock in ["...", "รอเซิร์ฟเวอร์"] or self.neso_boost_rate in ["...", "รอข้อมูล"]:
                self.lbl_poll_countdown.config(text=f"⏳ รอ ({poll_remain}s{state_tag})", fg="#f59e0b")
            else:
                self.lbl_poll_countdown.config(text=f"🔄 {poll_remain}s{state_tag}", fg="#94a3b8")



        # 🔔 แจ้งเตือนล่วงหน้า 30 วินาที (ตอนนาทีที่ 19:30 ของรอบ 20 นาที - รองรับทั้ง 2 โหมด)
        if remaining_seconds <= 30 and remaining_seconds > 1:
            if not self.has_alerted_19m30s:
                self.has_alerted_19m30s = True
                self.play_alert(950, 180) # เสียงบี๊บเตือนเตรียมตัว
        else:
            self.has_alerted_19m30s = False

        # 🔔 เตือน 0 นาที (เฉพาะเมื่อครบ 20 นาทีเป๊ะ)
        if remaining_seconds <= 1 or remaining_seconds >= (total_seconds - 2):
            if not self.has_alerted_0m:
                self.has_alerted_0m = True
                self.play_alert(1400, 350)
                # เมื่อครบรอบ 20 นาที ให้ดึงข้อมูลดรอปใหม่ทันที!
                self.fetch_drop_data_async()
        else:
            self.has_alerted_0m = False

        self.pulse_state = not self.pulse_state
        
        # สีธีมเตือน
        if remaining_seconds <= 120:
            theme_color = "#ff4d4f" if self.pulse_state else "#ff7875"
        elif remaining_seconds <= 300:
            theme_color = "#f59e0b"
        else:
            theme_color = "#00f2fe"

        self.win_bg.config(highlightbackground=theme_color)

        # ⚡ Smart Auto-Scan: เช็คการเปลี่ยนฉากด้วย White Masking + Black Screen (เบาหวิว 0.1ms ไม่กินเครื่อง)
        # ตรวจสอบทุกๆ 1.2 วินาที ถ้าเกิดการเปลี่ยนแมพจริง (วาป/จอดำ/ตัวหนังสือเปลี่ยน) ถึงจะปลุก OCR
        now_ts = time.time()
        if not hasattr(self, 'last_transition_check_ts'):
            self.last_transition_check_ts = now_ts
        if not hasattr(self, 'last_auto_scan_ts'):
            self.last_auto_scan_ts = now_ts

        # 1. เช็คเหตุการณ์เปลี่ยนแมพแบบ Real-time ทุก 1.2 วินาที (หากเกม Active)
        if is_game_active and (now_ts - self.last_transition_check_ts >= 1.2):
            self.last_transition_check_ts = now_ts
            if self.check_map_screen_transition():
                self.last_auto_scan_ts = now_ts
                self.auto_detect_map_async(silent=True)

        # 2. Safety Heartbeat Check (กันเหนียว ตรวจจับสำรองทุก 45 วิ หรือ 15 วิถ้ายังไม่รู้แมพ)
        safety_interval = 15.0 if not getattr(self, 'selected_layer_id', None) else 45.0
        if now_ts - self.last_auto_scan_ts >= safety_interval:
            self.last_auto_scan_ts = now_ts
            self.auto_detect_map_async(silent=True)

        # 🪙 ดึง Nesolet ประจำตัวละครเบื้องหลัง (กำหนดขั้นต่ำที่ 15s คงที่เพื่อไม่ให้เปลือง Rate limit)
        if not hasattr(self, 'last_nesolet_fetch_ts'):
            self.last_nesolet_fetch_ts = now_ts
        
        nesolet_poll_interval = 15.0
        
        if now_ts - self.last_nesolet_fetch_ts >= nesolet_poll_interval:
            self.last_nesolet_fetch_ts = now_ts
            if getattr(self, 'current_char_asset_key', None):
                threading.Thread(target=self._fetch_character_detail, args=(self.current_char_asset_key, self.current_char_name, True), daemon=True).start()
            elif getattr(self, 'current_char_name', None) and getattr(self, 'account_characters', None):
                matched = next((c for c in self.account_characters if c.get('name', '').lower() == self.current_char_name.lower()), None)
                if matched and matched.get('assetKey'):
                    self.current_char_asset_key = matched.get('assetKey')
                    threading.Thread(target=self._fetch_character_detail, args=(self.current_char_asset_key, self.current_char_name, True), daemon=True).start()
            else:
                threading.Thread(target=self._auto_init_character, daemon=True).start()

        if self.is_mini:
            if getattr(self, 'lbl_clock_mini', None) is not None and self.lbl_clock_mini.winfo_exists():
                self.lbl_clock_mini.config(text=time_real_str)
            if getattr(self, 'lbl_time_mini', None) is not None and self.lbl_time_mini.winfo_exists():
                self.lbl_time_mini.config(text=countdown_str, fg="#ffffff" if remaining_seconds > 120 else theme_color)
        else:
            if getattr(self, 'lbl_real_date', None) is not None and self.lbl_real_date.winfo_exists():
                self.lbl_real_date.config(text=date_str)
            if getattr(self, 'lbl_real_time', None) is not None and self.lbl_real_time.winfo_exists():
                self.lbl_real_time.config(text=time_real_str)
            if getattr(self, 'lbl_bp_real_time', None) is not None and self.lbl_bp_real_time.winfo_exists():
                self.lbl_bp_real_time.config(text=time_real_str)

            if getattr(self, 'lbl_timer_text', None) is not None and self.lbl_timer_text.winfo_exists():
                self.lbl_timer_text.config(text=countdown_str, fg=theme_color)

            # อัปเดตนาฬิกาวงแหวนกลม พร้อมตัวเลข 17 bold ตรงกลาง
            if getattr(self, 'canvas_timer_ring', None) is not None and self.canvas_timer_ring.winfo_exists():
                self.redraw_circular_timer(remaining_seconds, total_seconds, countdown_str, theme_color)

            if getattr(self, 'canvas_timer_bar', None) is not None and self.canvas_timer_bar.winfo_exists():
                self.canvas_timer_bar.delete("all")
                cw = self.canvas_timer_bar.winfo_width()
                ch = self.canvas_timer_bar.winfo_height()
                if cw > 1:
                    fraction = remaining_seconds / total_seconds
                    bar_w = cw * fraction
                    self.canvas_timer_bar.create_rectangle(0, 0, bar_w, ch, fill=theme_color, outline="")

            # Update red box info
            if getattr(self, 'lbl_last_update', None) is not None and self.lbl_last_update.winfo_exists():
                self.lbl_last_update.config(text=f"🕒 {self.last_update_str}")
            
            ping_col = "#38ef7d" if self.server_ping_ms < 150 else "#f59e0b" if self.server_ping_ms < 300 else "#ef4444"
            calls = getattr(self, 'api_call_count', 0)
            ping_text = f"📶 {self.server_ping_ms}ms (Req:{calls})"
            if getattr(self, 'lbl_ping', None) is not None and self.lbl_ping.winfo_exists():
                self.lbl_ping.config(text=ping_text, fg=ping_col)
            if getattr(self, 'lbl_bp_ping', None) is not None and self.lbl_bp_ping.winfo_exists():
                self.lbl_bp_ping.config(text=ping_text, fg=ping_col)

            if hasattr(self, '_update_nxpc_label'):
                self._update_nxpc_label()

        # วนรอบทุก 250ms ลื่นไหล
        self.root.after(250, self.update_clock_loop)

    def reset_api_counter(self):
        """รีเซ็ตตัวนับรอบการยิง API เป็น 0 เมื่อคลิกที่ป้าย Ping"""
        self.api_call_count = 0
        self.log_cmd("🔄 รีเซ็ตตัวนับการยิง API เป็น 0 แล้ว")

def main():
    root = tk.Tk()
    app = TimerToolApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
