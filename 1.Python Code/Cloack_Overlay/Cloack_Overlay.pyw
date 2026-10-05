import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os
import sys
import json
import time
import math
import webbrowser
import threading
import urllib.request
from datetime import datetime
import difflib
import asyncio
import re

# ไลบรารีสำหรับ Zone Icon และ OCR
from PIL import Image, ImageTk
import mss
import win32gui
import winocr

# เสียงเตือนบน Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cos_config.json")
LAYERS_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layers_cache.json")
ICONS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons_cache")
os.makedirs(ICONS_CACHE_DIR, exist_ok=True)

DEFAULT_WALLET = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"

def format_compact_number(num):
    """ฟังก์ชันย่อตัวเลขจำนวนมากให้อ่านง่ายและไม่ล้นกรอบ (เช่น 1.50M, 15.0k)"""
    try:
        val = float(num)
        if val >= 1_000_000:
            return f"{val/1_000_000:.2f}M"
        elif val >= 10_000:
            return f"{val/1_000:.1f}k"
        else:
            return f"{int(val):,}"
    except Exception:
        return str(num)

class StrokeLabel(tk.Canvas):
    """Widget ป้ายข้อความพร้อมเส้นขอบ Stroke รอบตัวหนังสือ คมชัดไม่แตกบนพื้นหลังโปร่งใส (Game/RPG HUD Style)"""
    def __init__(self, master=None, text="", font=None, fg="#ffffff", bg=None, 
                 stroke_color="#000000", stroke_width=1, anchor="w", justify="left", 
                 padx=0, pady=0, wraplength=0, **kwargs):
        self._text = str(text)
        self._font = font or ("Segoe UI", 9)
        self._fg = fg
        self._stroke_color = stroke_color
        self._stroke_width = stroke_width
        self._anchor = anchor
        self._justify = justify
        self._padx = padx
        self._pady = pady
        self._wraplength = wraplength
        
        canvas_kwargs = {}
        for k in ['cursor', 'takefocus', 'relief', 'bd', 'borderwidth']:
            if k in kwargs:
                canvas_kwargs[k] = kwargs[k]
        
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, **canvas_kwargs)
        self._redraw()

    def _redraw(self):
        self.delete("all")
        if not self._text:
            super().configure(width=1, height=1)
            return

        font_obj = tkfont.Font(font=self._font)
        sw = self._stroke_width
        raw_lines = self._text.split("\n")
        lines = []
        if self._wraplength and self._wraplength > 0:
            for rline in raw_lines:
                words = rline.split(" ")
                cur = ""
                for w in words:
                    test = cur + (" " if cur else "") + w
                    if font_obj.measure(test) <= self._wraplength:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                if cur:
                    lines.append(cur)
        else:
            lines = raw_lines

        line_h = font_obj.metrics("linespace")
        max_w = max((font_obj.measure(l) for l in lines), default=1)
        tot_h = line_h * max(len(lines), 1)

        req_w = max_w + (sw * 2) + (self._padx * 2) + 2
        req_h = tot_h + (sw * 2) + (self._pady * 2) + 2
        super().configure(width=req_w, height=req_h)

        if "w" in self._anchor:
            base_x = sw + self._padx + 1
            txt_anchor = "nw"
        elif "e" in self._anchor:
            base_x = req_w - sw - self._padx - 1
            txt_anchor = "ne"
        else:
            base_x = req_w // 2
            txt_anchor = "n"

        cur_y = sw + self._pady + 1
        draw_text_full = "\n".join(lines)
        if sw > 0 and self._stroke_color:
            for dx in range(-sw, sw + 1):
                for dy in range(-sw, sw + 1):
                    if dx != 0 or dy != 0:
                        self.create_text(
                            base_x + dx, cur_y + dy,
                            text=draw_text_full,
                            font=self._font,
                            fill=self._stroke_color,
                            anchor=txt_anchor,
                            justify=self._justify
                        )

        self.create_text(
            base_x, cur_y,
            text=draw_text_full,
            font=self._font,
            fill=self._fg,
            anchor=txt_anchor,
            justify=self._justify
        )

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        changed = False
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
            changed = True
        if "fg" in kwargs:
            self._fg = kwargs.pop("fg")
            changed = True
        if "foreground" in kwargs:
            self._fg = kwargs.pop("foreground")
            changed = True
        if "bg" in kwargs:
            bg_val = kwargs.pop("bg")
            super().configure(bg=bg_val)
        if "background" in kwargs:
            bg_val = kwargs.pop("background")
            super().configure(bg=bg_val)
        if "font" in kwargs:
            self._font = kwargs.pop("font")
            changed = True
        if "wraplength" in kwargs:
            self._wraplength = kwargs.pop("wraplength")
            changed = True
        if "stroke_color" in kwargs:
            self._stroke_color = kwargs.pop("stroke_color")
            changed = True
        if "stroke_width" in kwargs:
            self._stroke_width = kwargs.pop("stroke_width")
            changed = True
        if "anchor" in kwargs:
            self._anchor = kwargs.pop("anchor")
            changed = True
        if "justify" in kwargs:
            self._justify = kwargs.pop("justify")
            changed = True
        if kwargs:
            super().configure(**kwargs)
        if changed:
            self._redraw()

    def cget(self, key):
        if key in ("text",):
            return self._text
        if key in ("fg", "foreground"):
            return self._fg
        if key in ("font",):
            return self._font
        return super().cget(key)


# แมปปิ้งรูปภาพไอคอนโซนและเมือง (MediaWiki & Local Cache)
ZONE_ICONS_MAP = {
    # 🏙️ เมืองหลักและฮับเซฟโซน (Towns & Hubs)
    "Henesys": "https://media.maplestorywiki.net/yetidb/MapIcon_Henesys.png",
    "Ellinia": "https://media.maplestorywiki.net/yetidb/MapIcon_Ellinia.png",
    "Perion": "https://media.maplestorywiki.net/yetidb/MapIcon_Perion.png",
    "Kerning City": "https://media.maplestorywiki.net/yetidb/MapIcon_KerningCity.png",
    "Lith Harbor": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "Nautilus": "https://media.maplestorywiki.net/yetidb/MapIcon_Nautilus.png",
    "Sleepywood": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "Rien": "https://media.maplestorywiki.net/yetidb/MapIcon_Rien.png",
    "Ereve": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Ereve%29.png",
    "Partem": "https://media.maplestorywiki.net/yetidb/MapIcon_Partem.png",
    "Orbis": "https://media.maplestorywiki.net/yetidb/MapIcon_Orbis.png",
    "El Nath": "https://media.maplestorywiki.net/yetidb/MapIcon_ElNath.png",
    "Aquarium": "https://media.maplestorywiki.net/yetidb/MapIcon_AquaRoad.png",
    "Aqua Road": "https://media.maplestorywiki.net/yetidb/MapIcon_AquaRoad.png",
    "Ludibrium": "https://media.maplestorywiki.net/yetidb/MapIcon_Ludibrium.png",
    "Omega Sector": "https://media.maplestorywiki.net/yetidb/MapIcon_OmegaSector.png",
    "Korean Folk Town": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Ludus_Lake%29.png",
    "Leafre": "https://media.maplestorywiki.net/yetidb/MapIcon_Leafre.png",
    "Mu Lung": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Mu_Lung_Garden%29.png",
    "Herb Town": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Mu_Lung_Garden%29.png",
    "Ariant": "https://media.maplestorywiki.net/yetidb/MapIcon_Ariant.png",
    "Magatia": "https://media.maplestorywiki.net/yetidb/MapIcon_Magatia.png",
    "Edelstein": "https://media.maplestorywiki.net/yetidb/MapIcon_Edelstein.png",
    "Haven": "https://media.maplestorywiki.net/yetidb/MapIcon_Haven.png",
    "Pantheon": "https://media.maplestorywiki.net/yetidb/MapIcon_Pantheon.png",
    "Savage Terminal": "https://media.maplestorywiki.net/yetidb/MapIcon_SavageTerminal.png",
    "Ristonia": "https://media.maplestorywiki.net/yetidb/MapIcon_Ristonia.png",
    "Singapore": "https://media.maplestorywiki.net/yetidb/MapIcon_Singapore.png",
    "Malaysia": "https://media.maplestorywiki.net/yetidb/MapIcon_Malaysia.png",

    # 🌊 Arcane River เมืองและเซฟโซน
    "Nameless Town": "https://media.maplestorywiki.net/yetidb/MapIcon_Road_of_Vanishing.png",
    "Vanishing Journey": "https://media.maplestorywiki.net/yetidb/MapIcon_Road_of_Vanishing.png",
    "Lake of Oblivion": "https://media.maplestorywiki.net/yetidb/MapIcon_Road_of_Vanishing.png",
    "Extinction Zone": "https://media.maplestorywiki.net/yetidb/MapIcon_Road_of_Vanishing.png",
    "Cave of Repose": "https://media.maplestorywiki.net/yetidb/MapIcon_Road_of_Vanishing.png",
    
    "Reverse City": "https://media.maplestorywiki.net/yetidb/MapIcon_Reverse_City.png",
    "Surface": "https://media.maplestorywiki.net/yetidb/MapIcon_Reverse_City.png",
    "Underground": "https://media.maplestorywiki.net/yetidb/MapIcon_Reverse_City.png",
    
    "Chu Chu Village": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Chew Chew Island": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Five-Color Hill": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Illiard Fungos": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Skywhale Mountain": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Mushbud Forest": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    "Eree Valley": "https://media.maplestorywiki.net/yetidb/MapIcon_ChewChew.png",
    
    "Yum Yum Island": "https://media.maplestorywiki.net/yetidb/MapIcon_YumYum.png",
    
    "Lachelein": "https://media.maplestorywiki.net/yetidb/MapIcon_Lacheln.png",
    "Lachelein Alley": "https://media.maplestorywiki.net/yetidb/MapIcon_Lacheln.png",
    "Lachelein Clocktower": "https://media.maplestorywiki.net/yetidb/MapIcon_Lacheln.png",
    "Lachelein Street": "https://media.maplestorywiki.net/yetidb/MapIcon_Lacheln.png",
    
    "Spirit Tree": "https://media.maplestorywiki.net/yetidb/MapIcon_Arcana.png",
    "Arcana": "https://media.maplestorywiki.net/yetidb/MapIcon_Arcana.png",
    "Path to the Coral Forest": "https://media.maplestorywiki.net/yetidb/MapIcon_Arcana.png",
    "Near the Floral Flute": "https://media.maplestorywiki.net/yetidb/MapIcon_Arcana.png",
    "Cavernous Cavern": "https://media.maplestorywiki.net/yetidb/MapIcon_Arcana.png",
    
    "Trueffet Square": "https://media.maplestorywiki.net/yetidb/MapIcon_Morass.png",
    "Morass": "https://media.maplestorywiki.net/yetidb/MapIcon_Morass.png",
    "That Day in Trueffet": "https://media.maplestorywiki.net/yetidb/MapIcon_Morass.png",
    "Trueffet Street": "https://media.maplestorywiki.net/yetidb/MapIcon_Morass.png",
    "Research Lab": "https://media.maplestorywiki.net/yetidb/MapIcon_Morass.png",
    
    "Esfera": "https://media.maplestorywiki.net/yetidb/MapIcon_esfera.png",
    "Star-Swallowing Sea": "https://media.maplestorywiki.net/yetidb/MapIcon_esfera.png",
    "Radiant Temple": "https://media.maplestorywiki.net/yetidb/MapIcon_esfera.png",
    "Heart of the Forest": "https://media.maplestorywiki.net/yetidb/MapIcon_esfera.png",
    "Cernium": "https://media.maplestorywiki.net/yetidb/MapIcon_Cernium.png",
    
    # 🌲 Maple World อื่นๆ
    "Dark World Tree": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "Scrapyard": "https://media.maplestorywiki.net/yetidb/MapIcon_Haven.png",
    "Victoria Island": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "El Nath Mountains": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28El_Nath_Mts.%29.png",
    "Minar Forest": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Minar_Forest%29.png",
    "Nihal Desert": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Nihal_Desert%29.png",
    "Temple of Time": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Temple_of_Time%29.png",
    "ในเมือง": "https://media.maplestorywiki.net/yetidb/WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
}


def get_default_wallet():
    try:
        curr = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(curr))
        for fname in ["Primary_Wallet.txt", "MSU_Wallet.txt"]:
            res_file = os.path.join(root_dir, "AI_Resources", fname)
            if os.path.exists(res_file):
                with open(res_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("ADDRESS="):
                            val = line.strip().split("=", 1)[1].strip()
                            if val:
                                return val
    except:
        pass
    return DEFAULT_WALLET


DEFAULT_API_KEYS = [
    "gw_9300321ad25e8c9ee671b39b683681ed21befc8ff886fa982f049992417ee03a8f7f24b7a7dfcd789945c74bfff26452",
    "gw_91a3dc4dfa157a8971e67fb7e38d3add0fdd3f4dfc0caf21ac82fc29c650efee85c7920c8a113a09b7a4a670ba466fe9",
    "gw_2e28c1275962983782c1996afe9777f0fd2c232d9f49b880bc2ac9193d307ae0607cc6c5611568cfb5f157cfe90d93be",
    "gw_601054c06febe64bb1aac6bbd360599c8273827a81cf67479de827062c0824f3245b153d891624503b969e8187af721a",
    "gw_a7485d00ca42c9d6b744293e656529288967509c8f932770c78700462f7dd964c0e8c1af10219bf6d920ecbabe5b6a39"
]

def get_api_keys():
    keys = []
    try:
        curr = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(curr))
        res_file = os.path.join(root_dir, "AI_Resources", "MSU_API_Keys.txt")
        if os.path.exists(res_file):
            with open(res_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("KEY_") and "=" in line:
                        k = line.split("=", 1)[1].strip()
                        if k and k.startswith("gw_"):
                            keys.append(k)
    except:
        pass
    return keys if keys else DEFAULT_API_KEYS


def format_compact_number(num):
    try:
        n = float(num)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{n/1_000:.1f}K"
        return f"{n:,.0f}"
    except:
        return str(num)


def format_compact_stock(stock_str):
    """ย่อจำนวน Stock สำหรับแสดงในโหมดมินิ เช่น 42,390 NESO -> 42K"""
    if not stock_str or stock_str == "...":
        return "..."
    digits = re.sub(r'[^0-9]', '', str(stock_str))
    if not digits:
        return str(stock_str)[:6]
    n = int(digits)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


class TimerToolApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw() # ซ่อน root window
        
        self.trans_key = "#000001"
        self.bg_color = "#121418" # พื้นหลังคุมโทน MS แท้ๆ
        
        # ขนาดเริ่มต้น Default V.2 หน้าต่างหลักแนวนอน และ Vertical Sidebar
        self.v2_w = 460
        self.v2_h = 355
        self.sidebar_w = 210
        self.sidebar_h = 535
        self.full_w = 460
        self.full_h = 355
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
        
        # เริ่มการวนลูปนาฬิกา
        self.update_clock_loop()

    def load_layers_cache(self):
        """โหลดรายชื่อฟิลด์จาก cache ไฟล์ในเครื่องเพื่อให้เปิดได้ทันที"""
        if os.path.exists(LAYERS_CACHE_FILE):
            try:
                with open(LAYERS_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.layers_list = json.load(f)
            except Exception as e:
                print("Error loading layers cache:", e)
        # ถ้าไม่มี ให้ไป fetch ใน background
        if not self.layers_list:
            threading.Thread(target=self.refresh_layers_from_api, daemon=True).start()

    def get_current_api_key(self):
        if not self.api_keys:
            return ""
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_api_key(self):
        if self.api_keys:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)

    def refresh_layers_from_api(self):
        try:
            key = self.get_current_api_key()
            url = "https://openapi.msu.io/v1rc1/msn/layers/static"
            payload = {
                "layerDescs": [
                    {
                        "layerType": "LAYER_TYPE_FIELD"
                    }
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-nxopen-api-key": key,
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            static_datas = data.get("data", {}).get("staticDatas", [])
            fields = []
            for d in static_datas:
                if d.get("layerType") == "LAYER_TYPE_FIELD":
                    f_info = d.get("field", {})
                    fields.append({
                        "layerId": d.get("layerId"),
                        "layerName": f_info.get("layerName", f"Field #{d.get('layerId')}"),
                        "groupName": f_info.get("groupName", ""),
                        "minLevel": f_info.get("minRecommendedLevel", 0),
                        "maxLevel": f_info.get("maxRecommendedLevel", 0)
                    })
            if fields:
                self.layers_list = fields
                with open(LAYERS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(fields, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to refresh layers:", e)

    def get_zone_icon(self, map_name, size_h=24):
        """ค้นหาและดึงรูป Zone/Town Icon จาก cache หรือ CDN"""
        if not map_name:
            return None
            
        target_url = None
        zone_key = None
        
        # 1. เทียบจาก ZONE_ICONS_MAP
        for k, url in ZONE_ICONS_MAP.items():
            if k.lower() in map_name.lower() or map_name.lower() in k.lower():
                target_url = url
                zone_key = k.replace(" ", "_")
                break
                
        # 2. ถ้าไม่เจอ ลองหาไฟล์ใน ICONS_CACHE_DIR ตรงๆ
        if not zone_key:
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', map_name.replace(" ", "_"))
            if os.path.exists(ICONS_CACHE_DIR):
                for f in os.listdir(ICONS_CACHE_DIR):
                    if f.lower().endswith(".png") and clean_name.lower() in f.lower():
                        zone_key = f[:-4]
                        break
                        
        if not zone_key:
            if "เมือง" in map_name or "town" in map_name.lower():
                zone_key = "Default_Town"
            else:
                return None
            
        cache_id = f"{zone_key}_{size_h}"
        if cache_id in self.zone_photo_cache:
            return self.zone_photo_cache[cache_id]
            
        cache_path = os.path.join(ICONS_CACHE_DIR, f"{zone_key}.png")
        if os.path.exists(cache_path):
            try:
                img = Image.open(cache_path)
                orig_w, orig_h = img.size
                ratio = float(size_h) / orig_h if orig_h > 0 else 1.0
                new_w = max(size_h, int(orig_w * ratio))
                img = img.resize((new_w, size_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.zone_photo_cache[cache_id] = photo
                return photo
            except Exception:
                pass
                
        # ถ้ายังไม่มีรูปในเครื่อง ดาวน์โหลดใน Background Thread
        if target_url:
            threading.Thread(target=self._download_icon_async, args=(target_url, cache_path, zone_key), daemon=True).start()
        return None

    def _download_icon_async(self, url, save_path, zone_key):
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
                with open(save_path, "wb") as f:
                    f.write(data)
            def refresh_ui():
                if getattr(self, 'root', None) is not None and self.root.winfo_exists():
                    self.setup_ui_elements()
            self.root.after(0, refresh_ui)
        except Exception:
            pass

    def get_neso_coin_photo(self, size=30):
        cache_id = f"neso_coin_{size}"
        if not hasattr(self, 'zone_photo_cache'):
            self.zone_photo_cache = {}
        if cache_id in self.zone_photo_cache:
            return self.zone_photo_cache[cache_id]
        coin_path = os.path.join(ICONS_CACHE_DIR, "neso_coin.png")
        if os.path.exists(coin_path):
            try:
                img = Image.open(coin_path)
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.zone_photo_cache[cache_id] = photo
                return photo
            except Exception:
                pass
        return None

    def open_ocr_crop_tool(self):
        """(ระบบตั้งค่ากรอบ OCR แบบปรับเส้นอิสระ + ปุ่มบันทึก)"""
        self.play_alert(800, 100)
        self.crop_win = tk.Toplevel(self.root)
        self.crop_win.attributes("-fullscreen", True)
        self.crop_win.attributes("-alpha", 0.5)
        self.crop_win.config(bg="black")
        self.crop_win.attributes("-topmost", True)

        canvas = tk.Canvas(self.crop_win, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def cancel_crop(e=None):
            if getattr(self, 'crop_win', None) and self.crop_win.winfo_exists():
                self.crop_win.destroy()

        # 1. ค้นหาพิกัดหน้าต่างเกมเพื่ออ้างอิงตำแหน่ง
        game_rect = None
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        try:
            win32gui.EnumWindows(enum_cb, None)
            if hwnd:
                game_rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            pass

        # 2. คำนวณพิกัดเริ่มต้นของกรอบ
        sw = self.crop_win.winfo_screenwidth()
        sh = self.crop_win.winfo_screenheight()

        # ค่าเริ่มต้นถ้าไม่มีข้อมูลเดิม
        if game_rect:
            def_x1 = game_rect[0] + 8
            def_y1 = game_rect[1] + 32
        else:
            def_x1 = 100
            def_y1 = 100
        def_w = 270
        def_h = 80

        reg = getattr(self, 'custom_ocr_region', None)
        if isinstance(reg, dict):
            if game_rect:
                box_x1 = game_rect[0] + reg.get('x', 8)
                box_y1 = game_rect[1] + reg.get('y', 32)
            else:
                abs_c = reg.get('abs', None)
                if abs_c and len(abs_c) == 4:
                    box_x1, box_y1 = abs_c[0], abs_c[1]
                else:
                    box_x1 = reg.get('x', def_x1)
                    box_y1 = reg.get('y', def_y1)
            box_w = reg.get('w', def_w)
            box_h = reg.get('h', def_h)
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h
            
            # เส้นแบ่งไอคอนและเส้นแบ่งกลาง
            icon_w_saved = reg.get('icon_w', min(50, max(32, int(box_h * 0.5))))
            box_icon_x = box_x1 + icon_w_saved
            red_box = reg.get('red_box')
            if red_box and len(red_box) == 4:
                box_mid_y = box_y1 + red_box[3]
            else:
                box_mid_y = box_y1 + (box_h // 2)
        else:
            box_x1 = def_x1
            box_y1 = def_y1
            box_x2 = def_x1 + def_w
            box_y2 = def_y1 + def_h
            box_icon_x = box_x1 + 44
            box_mid_y = box_y1 + (def_h // 2)

        # ป้องกันค่าเพี้ยนออกนอกจอ
        box_x1 = max(0, min(box_x1, sw - 100))
        box_y1 = max(60, min(box_y1, sh - 60))
        box_x2 = max(box_x1 + 60, min(box_x2, sw - 10))
        box_y2 = max(box_y1 + 40, min(box_y2, sh - 10))
        box_icon_x = max(box_x1 + 20, min(box_icon_x, box_x2 - 30))
        box_mid_y = max(box_y1 + 15, min(box_mid_y, box_y2 - 15))

        active_drag = None
        drag_start_x = 0
        drag_start_y = 0
        orig_coords = {}

        # 3. ฟังก์ชันวาดเส้นไกด์ไลน์ (Interactive Guidelines)
        def redraw_guides():
            canvas.delete("guidelines")
            w = box_x2 - box_x1
            h = box_y2 - box_y1

            # 🟡 1. Master Header Frame (กรอบเหลือง)
            canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, outline="#facc15", width=2, tags="guidelines")
            # 🟢 หมุดตั้งต้นมุมบนซ้าย
            canvas.create_rectangle(box_x1 - 2, box_y1 - 2, box_x1 + 12, box_y1 + 12, fill="#22c55e", outline="#ffffff", width=1, tags="guidelines")

            # 🔘 2. กล่องไอคอนด้านซ้าย (Icon Box)
            canvas.create_rectangle(box_x1 + 2, box_y1 + 2, box_icon_x - 1, box_y2 - 2, outline="#eab308", width=1, dash=(3, 2), tags="guidelines")
            canvas.create_text(box_x1 + ((box_icon_x - box_x1) // 2), box_y1 + (h // 2), text="Icon", fill="#cbd5e1", font=("Segoe UI", 8, "bold"), tags="guidelines")

            # 🔴 3. กล่องสีแดง (Main Zone แถวบน เช่น Scrapyard)
            canvas.create_rectangle(box_icon_x + 2, box_y1 + 2, box_x2 - 2, box_mid_y - 1, outline="#ef4444", width=2, tags="guidelines")
            canvas.create_text(box_icon_x + 6, box_y1 + 3, text="🔴 Main Zone (โซนใหญ่)", fill="#ef4444", font=("Segoe UI", 7, "bold"), anchor="nw", tags="guidelines")

            # 🔵 4. กล่องสีฟ้า (Sub Map แถวล่าง เช่น Scrapyard Entrance)
            canvas.create_rectangle(box_icon_x + 2, box_mid_y + 1, box_x2 - 2, box_y2 - 2, outline="#38bdf8", width=2, tags="guidelines")
            canvas.create_text(box_icon_x + 6, box_mid_y + 3, text="🔵 Sub Map (จุดยืนจริง)", fill="#38bdf8", font=("Segoe UI", 7, "bold"), anchor="nw", tags="guidelines")

            # ↕️ 5. เส้นแบ่งกลาง (Mid Line Handle - ปรับระดับแบ่งแถว 1 กับ 2)
            canvas.create_line(box_icon_x, box_mid_y, box_x2, box_mid_y, fill="#ffffff", width=2, dash=(4, 2), tags="guidelines")
            canvas.create_oval(box_x2 - 12, box_mid_y - 4, box_x2 - 4, box_mid_y + 4, fill="#ffffff", outline="#0284c7", tags="guidelines")

            # ↔️ 6. เส้นแบ่งไอคอน (Icon Line Handle)
            canvas.create_line(box_icon_x, box_y1, box_icon_x, box_y2, fill="#eab308", width=2, dash=(4, 2), tags="guidelines")
            canvas.create_oval(box_icon_x - 4, box_y1 + 4, box_icon_x + 4, box_y1 + 12, fill="#eab308", outline="#ffffff", tags="guidelines")

            # 📏 ป้ายบอกขนาดและคำแนะนำ
            canvas.create_text(box_x1, max(50, box_y1 - 18), text=f"📍 Master Header: {w}x{h} px | ลากเส้นบน-ล่าง-กลาง เพื่อจัดระดับ", 
                               fill="#facc15", font=("Segoe UI", 9, "bold"), anchor="nw", tags="guidelines")

        # 4. ฟังก์ชันตรวจจับว่าเมาส์อยู่ใกล้เส้นไหน
        def get_hover_target(x, y):
            tol = 8 # ระยะความไวของเส้น
            # เส้นแบ่งกลาง
            if abs(y - box_mid_y) <= tol and (box_icon_x - 5 <= x <= box_x2 + 5):
                return 'mid'
            # ขอบบน
            if abs(y - box_y1) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'top'
            # ขอบล่าง
            if abs(y - box_y2) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'bottom'
            # เส้นแบ่งไอคอน
            if abs(x - box_icon_x) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'icon'
            # ขอบซ้าย
            if abs(x - box_x1) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'left'
            # ขอบขวา
            if abs(x - box_x2) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'right'
            # ในกรอบ (ย้ายตำแหน่งทั้งกรอบ)
            if (box_x1 < x < box_x2) and (box_y1 < y < box_y2):
                return 'move'
            return 'new'

        def on_mouse_motion(e):
            if active_drag:
                return
            tgt = get_hover_target(e.x, e.y)
            if tgt in ['top', 'bottom', 'mid']:
                canvas.config(cursor="size_ns")
            elif tgt in ['left', 'right', 'icon']:
                canvas.config(cursor="size_we")
            elif tgt == 'move':
                canvas.config(cursor="fleur")
            else:
                canvas.config(cursor="crosshair")

        def on_mouse_down(e):
            nonlocal active_drag, drag_start_x, drag_start_y, orig_coords
            drag_start_x = e.x
            drag_start_y = e.y
            active_drag = get_hover_target(e.x, e.y)
            orig_coords = {
                'x1': box_x1, 'y1': box_y1,
                'x2': box_x2, 'y2': box_y2,
                'icon_x': box_icon_x, 'mid_y': box_mid_y
            }

        def on_mouse_drag(e):
            nonlocal box_x1, box_y1, box_x2, box_y2, box_icon_x, box_mid_y
            if not active_drag:
                return

            dx = e.x - drag_start_x
            dy = e.y - drag_start_y

            if active_drag == 'top':
                # ลากเส้นขอบบน ขึ้น-ลง
                box_y1 = min(orig_coords['y1'] + dy, box_mid_y - 12)
            elif active_drag == 'bottom':
                # ลากเส้นขอบล่าง ขึ้น-ลง
                box_y2 = max(orig_coords['y2'] + dy, box_mid_y + 12)
            elif active_drag == 'mid':
                # ลากเส้นแบ่งกลาง ขึ้น-ลง (แบ่ง Main Zone กับ Sub Map)
                box_mid_y = max(box_y1 + 10, min(orig_coords['mid_y'] + dy, box_y2 - 10))
            elif active_drag == 'icon':
                # ลากเส้นแบ่งไอคอน ซ้าย-ขวา
                box_icon_x = max(box_x1 + 15, min(orig_coords['icon_x'] + dx, box_x2 - 30))
            elif active_drag == 'left':
                # ลากขอบซ้าย
                box_x1 = min(orig_coords['x1'] + dx, box_icon_x - 15)
            elif active_drag == 'right':
                # ลากขอบขวา
                box_x2 = max(orig_coords['x2'] + dx, box_icon_x + 30)
            elif active_drag == 'move':
                # ย้ายทั้งกรอบ
                box_x1 = orig_coords['x1'] + dx
                box_y1 = orig_coords['y1'] + dy
                box_x2 = orig_coords['x2'] + dx
                box_y2 = orig_coords['y2'] + dy
                box_icon_x = orig_coords['icon_x'] + dx
                box_mid_y = orig_coords['mid_y'] + dy
            elif active_drag == 'new':
                # วาดกรอบใหม่
                x1 = min(drag_start_x, e.x)
                y1 = min(drag_start_y, e.y)
                x2 = max(drag_start_x, e.x)
                y2 = max(drag_start_y, e.y)
                if (x2 - x1) >= 20 and (y2 - y1) >= 20:
                    box_x1, box_y1, box_x2, box_y2 = x1, y1, x2, y2
                    box_icon_x = box_x1 + min(50, max(30, int((y2 - y1) * 0.5)))
                    box_mid_y = box_y1 + ((y2 - y1) // 2)

            redraw_guides()

        def on_mouse_up(e):
            nonlocal active_drag
            active_drag = None
            on_mouse_motion(e)

        canvas.bind("<Motion>", on_mouse_motion)
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        # 5. ฟังก์ชันบันทึกพิกัดเมื่อกดปุ่ม [ บันทึก ]
        def save_and_close():
            w = box_x2 - box_x1
            h = box_y2 - box_y1
            if w > 20 and h > 20:
                rel_x = (box_x1 - game_rect[0]) if game_rect else box_x1
                rel_y = (box_y1 - game_rect[1]) if game_rect else box_y1
                icon_w = max(10, box_icon_x - box_x1)
                
                # พิกัดกล่องสีแดงและกล่องสีฟ้าสัมพัทธ์กับกรอบนอก
                rx1 = icon_w + 2
                ry1 = 2
                rx2 = w - 2
                ry2 = max(ry1 + 5, (box_mid_y - box_y1) - 1)

                bx1 = icon_w + 2
                by1 = min(h - 5, (box_mid_y - box_y1) + 1)
                bx2 = w - 2
                by2 = h - 2

                self.custom_ocr_region = {
                    'x': rel_x,
                    'y': rel_y,
                    'w': w,
                    'h': h,
                    'abs': [box_x1, box_y1, box_x2, box_y2],
                    'icon_w': icon_w,
                    'red_box': [rx1, ry1, rx2, ry2],
                    'blue_box': [bx1, by1, bx2, by2]
                }
                self.save_config()
                self.play_alert(1000, 150)
                self.crop_win.destroy()
                # สแกนทันทีหลังบันทึก
                self.auto_detect_map_async()
            else:
                self.crop_win.destroy()

        def reset_to_game():
            nonlocal box_x1, box_y1, box_x2, box_y2, box_icon_x, box_mid_y
            if game_rect:
                box_x1 = game_rect[0] + 8
                box_y1 = game_rect[1] + 32
            else:
                box_x1 = 100
                box_y1 = 100
            box_x2 = box_x1 + 270
            box_y2 = box_y1 + 80
            box_icon_x = box_x1 + 44
            box_mid_y = box_y1 + 40
            redraw_guides()

        # 6. แถบควบคุมลอยด้านบนจอ (Floating Control Bar)
        ctrl_frame = tk.Frame(self.crop_win, bg="#0f172a", bd=1, relief="solid", highlightbackground="#38bdf8", highlightthickness=1)
        ctrl_frame.place(relx=0.5, y=28, anchor="n")

        lbl_tip = tk.Label(ctrl_frame, text="🖱️ ลากเส้น [ ขอบบน / ขอบล่าง / เส้นแบ่งกลาง / เส้นไอคอน ] ขึ้น-ลง หรือ ซ้าย-ขวา ปรับให้ตรงตามต้องการ", 
                           font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a", padx=10, pady=6)
        lbl_tip.pack(side=tk.LEFT)

        btn_save = tk.Button(ctrl_frame, text="💾 บันทึกกรอบ", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#10b981", 
                             activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=12, pady=4,
                             command=save_and_close)
        btn_save.pack(side=tk.LEFT, padx=6, pady=4)

        btn_reset = tk.Button(ctrl_frame, text="🔄 รีเซ็ต", font=("Segoe UI", 9), fg="#e2e8f0", bg="#334155", 
                              activebackground="#475569", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                              command=reset_to_game)
        btn_reset.pack(side=tk.LEFT, padx=4, pady=4)

        btn_cancel = tk.Button(ctrl_frame, text="❌ ยกเลิก (ESC)", font=("Segoe UI", 9), fg="#f87171", bg="#1e293b", 
                               activebackground="#3d1b1b", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                               command=cancel_crop)
        btn_cancel.pack(side=tk.LEFT, padx=(4, 8), pady=4)

        # ผูกปุ่ม Esc และคลิกขวาเพื่อยกเลิก
        self.crop_win.bind("<Escape>", cancel_crop)
        canvas.bind("<Escape>", cancel_crop)
        canvas.bind("<ButtonPress-3>", cancel_crop)

        # วาดไกด์ไลน์ครั้งแรกทันที
        redraw_guides()
        self.crop_win.focus_force()
        canvas.focus_set()

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

    def select_layer_by_id(self, layer_id):
        for fld in self.layers_list:
            if fld.get("layerId") == layer_id:
                self.is_in_town = False
                self.has_no_drop = False
                self.current_town_name = ""
                self.detected_submap_name = ""
                self.selected_layer_id = fld.get("layerId")
                self.selected_layer_name = fld.get("layerName")
                self.selected_group_name = fld.get("groupName")
                self.save_config()
                self.setup_ui_elements()
                self.fetch_drop_data_async()
                self.log_cmd(f"เลือกแมพ: {self.selected_layer_name}")
                break


    def open_char_crop_tool(self):
        """(ระบบตั้งค่ากรอบ OCR สำหรับสแกนชื่อตัวละคร)"""
        self.play_alert(800, 100)
        self.char_crop_win = tk.Toplevel(self.root)
        self.char_crop_win.attributes("-fullscreen", True)
        self.char_crop_win.attributes("-alpha", 0.5)
        self.char_crop_win.config(bg="black")
        self.char_crop_win.attributes("-topmost", True)

        canvas = tk.Canvas(self.char_crop_win, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def cancel_crop(e=None):
            if getattr(self, 'char_crop_win', None) and self.char_crop_win.winfo_exists():
                self.char_crop_win.destroy()

        # 1. ค้นหาพิกัดหน้าต่างเกมเพื่ออ้างอิงตำแหน่ง
        game_rect = None
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        try:
            win32gui.EnumWindows(enum_cb, None)
            if hwnd:
                game_rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            pass

        sw = self.char_crop_win.winfo_screenwidth()
        sh = self.char_crop_win.winfo_screenheight()

        if game_rect:
            def_x1 = game_rect[0] + 70
            def_y1 = max(0, game_rect[3] - 70)
        else:
            def_x1 = 100
            def_y1 = sh - 150
        def_w = 140
        def_h = 32

        reg = getattr(self, 'custom_char_ocr_region', None)
        if isinstance(reg, dict):
            if game_rect:
                box_x1 = game_rect[0] + reg.get('x', 70)
                box_y1 = game_rect[1] + reg.get('y', game_rect[3] - game_rect[1] - 70)
            else:
                abs_c = reg.get('abs', None)
                if abs_c and len(abs_c) == 4:
                    box_x1, box_y1 = abs_c[0], abs_c[1]
                else:
                    box_x1 = reg.get('x', def_x1)
                    box_y1 = reg.get('y', def_y1)
            box_w = reg.get('w', def_w)
            box_h = reg.get('h', def_h)
            box_x2 = box_x1 + box_w
            box_y2 = box_y1 + box_h
        else:
            box_x1 = def_x1
            box_y1 = def_y1
            box_x2 = def_x1 + def_w
            box_y2 = def_y1 + def_h

        box_x1 = max(0, min(box_x1, sw - 80))
        box_y1 = max(0, min(box_y1, sh - 40))
        box_x2 = max(box_x1 + 40, min(box_x2, sw - 10))
        box_y2 = max(box_y1 + 15, min(box_y2, sh - 10))

        active_drag = None
        drag_start_x = 0
        drag_start_y = 0
        orig_coords = {}

        def redraw_guides():
            canvas.delete("char_guides")
            w = box_x2 - box_x1
            h = box_y2 - box_y1

            canvas.create_rectangle(box_x1, box_y1, box_x2, box_y2, outline="#ef4444", width=2, tags="char_guides")
            canvas.create_rectangle(box_x1 - 2, box_y1 - 2, box_x1 + 10, box_y1 + 10, fill="#ef4444", outline="#ffffff", width=1, tags="char_guides")
            canvas.create_rectangle(box_x2 - 10, box_y2 - 10, box_x2 + 2, box_y2 + 2, fill="#ef4444", outline="#ffffff", width=1, tags="char_guides")
            canvas.create_text(box_x1 + (w // 2), box_y1 + (h // 2), text="👤 ชื่อตัวละคร", fill="#fca5a5", font=("Segoe UI", 9, "bold"), tags="char_guides")
            canvas.create_text(box_x1, max(40, box_y1 - 18), text=f"👤 กรอบชื่อตัวละคร: {w}x{h} px (ครอบชื่อเหนือหลอดเลือด HP/MP)",
                               fill="#fca5a5", font=("Segoe UI", 9, "bold"), anchor="nw", tags="char_guides")

        def get_hover_target(x, y):
            tol = 8
            if abs(y - box_y1) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'top'
            if abs(y - box_y2) <= tol and (box_x1 - 5 <= x <= box_x2 + 5):
                return 'bottom'
            if abs(x - box_x1) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'left'
            if abs(x - box_x2) <= tol and (box_y1 - 5 <= y <= box_y2 + 5):
                return 'right'
            if (box_x1 < x < box_x2) and (box_y1 < y < box_y2):
                return 'move'
            return 'new'

        def on_mouse_motion(e):
            if active_drag:
                return
            tgt = get_hover_target(e.x, e.y)
            if tgt in ['top', 'bottom']:
                canvas.config(cursor="size_ns")
            elif tgt in ['left', 'right']:
                canvas.config(cursor="size_we")
            elif tgt == 'move':
                canvas.config(cursor="fleur")
            else:
                canvas.config(cursor="crosshair")

        def on_mouse_down(e):
            nonlocal active_drag, drag_start_x, drag_start_y, orig_coords
            drag_start_x = e.x
            drag_start_y = e.y
            active_drag = get_hover_target(e.x, e.y)
            orig_coords = {'x1': box_x1, 'y1': box_y1, 'x2': box_x2, 'y2': box_y2}

        def on_mouse_drag(e):
            nonlocal box_x1, box_y1, box_x2, box_y2
            if not active_drag:
                return
            dx = e.x - drag_start_x
            dy = e.y - drag_start_y

            if active_drag == 'top':
                box_y1 = min(orig_coords['y1'] + dy, box_y2 - 15)
            elif active_drag == 'bottom':
                box_y2 = max(orig_coords['y2'] + dy, box_y1 + 15)
            elif active_drag == 'left':
                box_x1 = min(orig_coords['x1'] + dx, box_x2 - 30)
            elif active_drag == 'right':
                box_x2 = max(orig_coords['x2'] + dx, box_x1 + 30)
            elif active_drag == 'move':
                box_x1 = orig_coords['x1'] + dx
                box_y1 = orig_coords['y1'] + dy
                box_x2 = orig_coords['x2'] + dx
                box_y2 = orig_coords['y2'] + dy
            elif active_drag == 'new':
                x1 = min(drag_start_x, e.x)
                y1 = min(drag_start_y, e.y)
                x2 = max(drag_start_x, e.x)
                y2 = max(drag_start_y, e.y)
                if (x2 - x1) >= 15 and (y2 - y1) >= 10:
                    box_x1, box_y1, box_x2, box_y2 = x1, y1, x2, y2

            redraw_guides()

        def on_mouse_up(e):
            nonlocal active_drag
            active_drag = None
            on_mouse_motion(e)

        canvas.bind("<Motion>", on_mouse_motion)
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        def save_and_close():
            w = box_x2 - box_x1
            h = box_y2 - box_y1
            if w > 10 and h > 10:
                rel_x = (box_x1 - game_rect[0]) if game_rect else box_x1
                rel_y = (box_y1 - game_rect[1]) if game_rect else box_y1
                self.custom_char_ocr_region = {
                    'x': rel_x,
                    'y': rel_y,
                    'w': w,
                    'h': h,
                    'abs': [box_x1, box_y1, box_x2, box_y2]
                }
                self.save_config()
                self.play_alert(1000, 150)
                self.char_crop_win.destroy()
                self.log_cmd(f"บันทึกกรอบตัวละคร: {w}x{h} px")
                self.auto_detect_character_async(silent=False)
            else:
                self.char_crop_win.destroy()

        def reset_to_game():
            nonlocal box_x1, box_y1, box_x2, box_y2
            if game_rect:
                box_x1 = game_rect[0] + 70
                box_y1 = max(0, game_rect[3] - 70)
            else:
                box_x1 = 100
                box_y1 = sh - 150
            box_x2 = box_x1 + 140
            box_y2 = box_y1 + 32
            redraw_guides()

        # แถบควบคุมลอย
        ctrl_frame = tk.Frame(self.char_crop_win, bg="#0f172a", bd=1, relief="solid", highlightbackground="#ef4444", highlightthickness=1)
        ctrl_frame.place(relx=0.5, y=28, anchor="n")

        lbl_tip = tk.Label(ctrl_frame, text="🖱️ ลากกรอบสีแดงครอบ 'ชื่อตัวละคร' เหนือหลอดเลือด HP/MP",
                           font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a", padx=10, pady=6)
        lbl_tip.pack(side=tk.LEFT)

        btn_save = tk.Button(ctrl_frame, text="💾 บันทึกกรอบตัวละคร", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#10b981",
                             activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=12, pady=4,
                             command=save_and_close)
        btn_save.pack(side=tk.LEFT, padx=6, pady=4)

        btn_reset = tk.Button(ctrl_frame, text="🔄 รีเซ็ต", font=("Segoe UI", 9), fg="#e2e8f0", bg="#334155",
                              activebackground="#475569", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                              command=reset_to_game)
        btn_reset.pack(side=tk.LEFT, padx=4, pady=4)

        btn_cancel = tk.Button(ctrl_frame, text="❌ ยกเลิก (ESC)", font=("Segoe UI", 9), fg="#f87171", bg="#1e293b",
                               activebackground="#3d1b1b", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=8, pady=4,
                               command=cancel_crop)
        btn_cancel.pack(side=tk.LEFT, padx=(4, 8), pady=4)

        self.char_crop_win.bind("<Escape>", cancel_crop)
        canvas.bind("<Escape>", cancel_crop)
        canvas.bind("<ButtonPress-3>", cancel_crop)

        redraw_guides()
        self.char_crop_win.focus_force()
        canvas.focus_set()

    def auto_detect_character_async(self, silent=False):
        threading.Thread(target=self._run_auto_detect_character, args=(silent,), daemon=True).start()

    def _fetch_account_characters(self):
        try:
            if not self.wallet_addr:
                return []
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/accounts/{self.wallet_addr}/characters"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "x-nxopen-api-key": key},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success"):
                    self.account_characters = res.get("data", {}).get("characters", [])
                    return self.account_characters
        except Exception as e:
            print("Fetch account characters error:", e)
        return []

    def _fetch_character_detail(self, asset_key, char_name, silent=False):
        try:
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/characters/{asset_key}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "x-nxopen-api-key": key},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("success"):
                    char = res.get("data", {}).get("character", {})
                    comm = char.get("common", {})
                    lvl = comm.get("level", 0)
                    job = comm.get("job", {}).get("jobName", "")
                    nesolet_raw = comm.get("nesolet", "0")
                    try:
                        nesolet_val = int(nesolet_raw) / (10**18)
                    except:
                        nesolet_val = 0.0

                    self.current_char_name = char_name
                    self.current_char_asset_key = asset_key
                    self.current_char_level = str(lvl)
                    self.current_char_job = job
                    self.current_char_nesolet_loaded = True
                    self.wallet_nesolet_str = f"{nesolet_val:,.1f}"
                    self.wallet_nesolet_compact = format_compact_number(nesolet_val)

                    if not silent:
                        self.log_cmd(f"✨ ตัวละคร: {char_name} (Lv.{lvl} {job})")
                        self.log_cmd(f"💰 Nesolet: {self.wallet_nesolet_str}")
                    self.save_config()
                    self.root.after(0, self.update_drop_ui)
        except Exception as e:
            if not silent:
                self.log_cmd(f"⚠️ รายละเอียดตัวละคร: {e}")

    def _auto_init_character(self):
        """กำหนดตัวละครอัตโนมัติจากกระเป๋า (เลือกตามชื่อที่จำไว้ หรือตัวละครเลเวลสูงสุด)"""
        try:
            chars = self._fetch_account_characters()
            if chars:
                target = None
                if getattr(self, 'current_char_name', ''):
                    target = next((c for c in chars if c.get('name', '').lower() == self.current_char_name.lower()), None)
                if not target:
                    target = max(chars, key=lambda c: c.get("data", {}).get("level", 0))
                if target:
                    a_key = target.get("assetKey")
                    c_name = target.get("name")
                    if a_key:
                        self.current_char_asset_key = a_key
                        self.current_char_name = c_name
                        self._fetch_character_detail(a_key, c_name, silent=True)
        except Exception as e:
            print("Auto init character error:", e)

    def _match_and_update_character(self, detected_name):
        if not getattr(self, 'account_characters', None):
            self._fetch_account_characters()

        chars = getattr(self, 'account_characters', [])
        if not chars:
            self.log_cmd("⚠️ ไม่พบรายชื่อตัวละครในกระเป๋า")
            return

        matched = None
        for c in chars:
            c_name = c.get('name', '')
            if c_name.lower() == detected_name.lower():
                matched = c
                break

        if not matched:
            for c in chars:
                c_name = c.get('name', '')
                if detected_name.lower() in c_name.lower() or c_name.lower() in detected_name.lower():
                    matched = c
                    break

        if not matched:
            names = [c.get('name', '') for c in chars]
            close = difflib.get_close_matches(detected_name, names, n=1, cutoff=0.5)
            if close:
                for c in chars:
                    if c.get('name') == close[0]:
                        matched = c
                        break

        if matched:
            asset_key = matched.get('assetKey')
            char_name = matched.get('name')
            self._fetch_character_detail(asset_key, char_name)
        else:
            self.log_cmd(f"⚠️ ไม่พบตัวละคร '{detected_name}' ในกระเป๋า")

    def _run_auto_detect_character(self, silent=False):
        if not hasattr(self, 'custom_char_ocr_region') or not self.custom_char_ocr_region:
            if not silent:
                self.log_cmd("⚠️ ยังไม่ได้ตั้งกรอบชื่อตัวละคร (กดปุ่ม 👤)")
            return

        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        if not hwnd:
            if not silent:
                self.log_cmd("⚠️ ไม่พบหน้าต่างเกม")
            return

        try:
            rect = win32gui.GetWindowRect(hwnd)
            reg = self.custom_char_ocr_region
            if isinstance(reg, dict):
                crop_x = rect[0] + reg.get('x', 0)
                crop_y = rect[1] + reg.get('y', 0)
                crop_w = reg.get('w', 140)
                crop_h = reg.get('h', 32)
            elif isinstance(reg, (list, tuple)) and len(reg) == 4:
                crop_x, crop_y = reg[0], reg[1]
                crop_w, crop_h = reg[2] - reg[0], reg[3] - reg[1]
            else:
                return

            with mss.mss() as sct:
                monitor = {"top": crop_y, "left": crop_x, "width": crop_w, "height": crop_h}
                sct_img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                up_w = pil_img.width * 2
                up_h = pil_img.height * 2
                up_img = pil_img.resize((up_w, up_h), Image.Resampling.BILINEAR)

                res = winocr.recognize_pil_sync(up_img, 'en')
                raw_text = res.get('text', '').strip() if res else ""
                clean_name = re.sub(r'[^a-zA-Z0-9]', '', raw_text)

                if not clean_name:
                    res_g = winocr.recognize_pil_sync(up_img.convert("L"), 'en')
                    raw_text = res_g.get('text', '').strip() if res_g else ""
                    clean_name = re.sub(r'[^a-zA-Z0-9]', '', raw_text)

                self.log_cmd(f"สแกนชื่อตัวละคร: '{clean_name or raw_text}'")
                if clean_name:
                    self._match_and_update_character(clean_name)
                else:
                    if not silent:
                        self.log_cmd("❌ ไม่พบชื่อในกรอบตัวละคร")
        except Exception as e:
            print("Char OCR error:", e)
            self.log_cmd(f"⚠️ สแกนตัวละครผิดพลาด: {e}")

    def auto_detect_map_async(self, silent=False):
        """กดปุ่ม 🔍 หรือรันอัตโนมัติเพื่อตรวจจับชื่อแมพแบบ Real-time"""
        threading.Thread(target=self._run_auto_detect_map, args=(silent,), daemon=True).start()

    def _run_auto_detect_map(self, silent=False):
        def set_btn_state(text, bg="#16202c", fg="#38bdf8"):
            if not silent and hasattr(self, 'btn_ocr') and self.btn_ocr and self.btn_ocr.winfo_exists():
                self.btn_ocr.config(text=text, bg=bg, fg=fg)
        
        if not silent:
            self.root.after(0, lambda: set_btn_state("⏳ Scan", bg="#0e2a38", fg="#38bdf8"))
            self.log_cmd("🔍 เริ่มตรวจจับแผนที่ในเกม...")
        
        # 1. ค้นหาหน้าต่างเกม MapleStory N (กรองไม่ให้จับ VS Code, IDE หรือ Terminal)
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                title = win32gui.GetWindowText(h)
                t_lower = title.lower()
                if "maplestory" in t_lower and not any(x in t_lower for x in ["visual studio", ".pyw", ".py", ".md", "antigravity", "cursor", "cmd.exe", "powershell"]):
                    hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        
        if not hwnd:
            if not silent:
                self.log_cmd("⚠️ ไม่พบหน้าต่างเกม MapleStory N")
                self.root.after(0, lambda: set_btn_state("❓ No Game", bg="#3d1b1b", fg="#f87171"))
                self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
            return

        # 2. จับภาพเฉพาะบริเวณชื่อแมพมุมซ้ายบน
        try:
            rect = win32gui.GetWindowRect(hwnd)
            win_w = rect[2] - rect[0]
            win_h = rect[3] - rect[1]
            
            if hasattr(self, 'custom_ocr_region') and self.custom_ocr_region:
                reg = self.custom_ocr_region
                if isinstance(reg, dict):
                    crop_x = rect[0] + reg.get('x', 0)
                    crop_y = rect[1] + reg.get('y', 0)
                    crop_w = reg.get('w', 300)
                    crop_h = reg.get('h', 85)
                elif isinstance(reg, (list, tuple)) and len(reg) == 4:
                    crop_x = reg[0]
                    crop_y = reg[1]
                    crop_w = reg[2] - reg[0]
                    crop_h = reg[3] - reg[1]
                else:
                    crop_x = rect[0] + 8
                    crop_y = rect[1] + 32
                    crop_w = min(420, max(300, win_w // 3))
                    crop_h = 85
            else:
                crop_x = rect[0] + 8
                crop_y = rect[1] + 32
                crop_w = min(420, max(300, win_w // 3))
                crop_h = 85
            
            with mss.mss() as sct:
                monitor = {"top": crop_y, "left": crop_x, "width": crop_w, "height": crop_h}
                sct_img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # -----------------------------------------------------
                # 🔍 Smart Icon Bypass OCR:
                # Mini Map ใน MapleStory N จะมีไอคอนโซนอยู่ด้านซ้ายสุด (~38-42px)
                # ด้านขวาของไอคอนจะเป็นข้อความ 2 บรรทัด:
                # - แถวที่ 1 (Main Zone): ชื่อโซนใหญ่ (ตรงกับ layerName ใน API)
                # - แถวที่ 2 (Sub Map): ชื่อสถานที่ย่อยที่กำลังยืนอยู่จริง
                # -----------------------------------------------------
                # -----------------------------------------------------
                # 🔍 Dual-Band Isolated OCR:
                # แยกอ่านอิสระ 2 กรอบตามคำสั่งผู้ใช้:
                # 🔴 ครึ่งบน (Top Frame): ชื่อโซนหลัก (Main Zone)
                # 🔵 ครึ่งล่าง (Bottom Frame): ชื่อแมพย่อย/จุดยืน (Sub Map)
                # -----------------------------------------------------
                reg_info = getattr(self, 'custom_ocr_region', None)
                red_box = reg_info.get('red_box') if isinstance(reg_info, dict) else None
                blue_box = reg_info.get('blue_box') if isinstance(reg_info, dict) else None

                raw_title = ""
                raw_sub = ""

                def clean_ocr_line(s):
                    # 1. ตัดอักขระพิเศษและอักขระเดี่ยวประเภทขอบเส้น (เช่น I, |, l, 1, !) ที่หัว-ท้าย
                    s = re.sub(r'^[Il|1!\s\-_~•\.:\(\)\[\]/\\;]+', '', s)
                    s = re.sub(r'[\s\-_\|~•\.:\(\)\[\]/\\;]+$', '', s)
                    # 2. ตัดคำซ้ำที่ติดกัน เช่น "Scrapyard Scrapyard Lot Scrapya" -> "Scrapyard Lot"
                    words = s.split()
                    dedup_words = []
                    for w in words:
                        clean_w = re.sub(r'[^a-zA-Z0-9]', '', w)
                        if not dedup_words or clean_w.lower() != re.sub(r'[^a-zA-Z0-9]', '', dedup_words[-1]).lower():
                            # ป้องกันเศษคำตัดท้ายที่ไม่สมบูรณ์ เช่น "Scrapya" ต่อท้าย "Scrapyard"
                            if dedup_words and len(clean_w) >= 3 and len(clean_w) < len(dedup_words[-1]) and dedup_words[-1].lower().startswith(clean_w.lower()):
                                continue
                            dedup_words.append(w)
                    return " ".join(dedup_words).strip()

                if red_box and blue_box and len(red_box) == 4 and len(blue_box) == 4:
                    rx1, ry1, rx2, ry2 = red_box
                    bx1, by1, bx2, by2 = blue_box
                    # ป้องกันไม่ให้พิกัดล้นขนาดรูปภาพ
                    rx1 = max(0, min(rx1, pil_img.width - 5))
                    rx2 = max(rx1 + 5, min(rx2, pil_img.width))
                    ry1 = max(0, min(ry1, pil_img.height - 5))
                    ry2 = max(ry1 + 5, min(ry2, pil_img.height))

                    bx1 = max(0, min(bx1, pil_img.width - 5))
                    bx2 = max(bx1 + 5, min(bx2, pil_img.width))
                    by1 = max(0, min(by1, pil_img.height - 5))
                    by2 = max(by1 + 5, min(by2, pil_img.height))

                    top_img = pil_img.crop((rx1, ry1, rx2, ry2))
                    bot_img = pil_img.crop((bx1, by1, bx2, by2))
                    ICON_OFFSET_X = rx1
                else:
                    # Fallback สัดส่วน Master Header
                    if pil_img.height >= 48:
                        top_bar_h = min(32, max(16, int(pil_img.height * 0.28)))
                        cy1 = top_bar_h
                        ch = pil_img.height - cy1
                    else:
                        top_bar_h = 0
                        cy1 = 0
                        ch = pil_img.height

                    ICON_OFFSET_X = min(50, max(32, int(ch * 0.82)))
                    mid_h = cy1 + (ch // 2)

                    top_img = pil_img.crop((ICON_OFFSET_X, cy1, pil_img.width, mid_h))
                    bot_img = pil_img.crop((ICON_OFFSET_X, mid_h, pil_img.width, pil_img.height))

                def recognize_with_upscale(img):
                    if not img or img.width < 5 or img.height < 5:
                        return "", []
                    # ขยายขนาด 2x เพื่อให้อ่านตัวอักษรขนาดเล็กได้คมชัด
                    up_w = img.width * 2
                    up_h = img.height * 2
                    up_img = img.resize((up_w, up_h), Image.Resampling.BILINEAR)
                    res = winocr.recognize_pil_sync(up_img, 'en')
                    lines = [clean_ocr_line(l.get('text', '')) for l in res.get('lines', []) if clean_ocr_line(l.get('text', ''))]
                    txt = clean_ocr_line(res.get('text', ''))
                    if not lines:
                        # ลองแบบ grayscale
                        res_g = winocr.recognize_pil_sync(up_img.convert("L"), 'en')
                        lines = [clean_ocr_line(l.get('text', '')) for l in res_g.get('lines', []) if clean_ocr_line(l.get('text', ''))]
                        txt = clean_ocr_line(res_g.get('text', ''))
                    return txt, lines

                # 1. ลองอ่านแยก 2 บรรทัดจากกล่องข้อความเต็ม (text_box_img) ด้วย line-aware OCR
                text_box_img = pil_img.crop((ICON_OFFSET_X, 0, pil_img.width, pil_img.height))
                full_txt, full_lines = recognize_with_upscale(text_box_img)

                if len(full_lines) >= 2:
                    raw_title = full_lines[0]
                    raw_sub = full_lines[1]
                else:
                    # 2. ถ้าได้บรรทัดเดียว ลองอ่านแยกจากกรอบ top_img และ bot_img
                    if top_img and bot_img and top_img.width > 10 and bot_img.width > 10:
                        _, top_lines = recognize_with_upscale(top_img)
                        _, bot_lines = recognize_with_upscale(bot_img)
                        if top_lines:
                            raw_title = top_lines[0]
                        if bot_lines:
                            raw_sub = bot_lines[0]

                    # 3. ถ้ายังได้บรรทัดเดียวหรือว่างเปล่า ให้ใช้ Smart Word Splitter แยก 2 บรรทัดอัตโนมัติ
                    base_str = raw_title if raw_title else full_txt
                    if base_str and not raw_sub:
                        # 3.1 ตรวจจับคีย์เวิร์ดเมือง/จุดยืนที่อยู่ท้ายข้อความ
                        for tw_kw in ["haven", "village", "town", "entrance", "shelter", "campsite", "square", "maze", "junction", "lot", "street"]:
                            match = re.search(r'\b(' + re.escape(tw_kw) + r'.*)$', base_str, re.IGNORECASE)
                            if match:
                                raw_title = base_str[:match.start()].strip()
                                raw_sub = match.group(1).strip()
                                break
                        
                        # 3.2 ตรวจจับคำซ้ำ เช่น "Black Heaven Black Heaven Maze 3"
                        if not raw_sub:
                            words = base_str.split()
                            if len(words) >= 4 and words[0].lower() == words[2].lower() and words[1].lower() == words[3].lower():
                                raw_title = f"{words[0]} {words[1]}"
                                raw_sub = " ".join(words[2:])
                            elif len(words) >= 2 and words[0].lower() == words[1].lower():
                                raw_title = words[0]
                                raw_sub = " ".join(words[1:])
                            else:
                                raw_title = base_str

                raw_text = f"{raw_title}\n{raw_sub}".strip()
                title_line = raw_title.lower()
                sub_line = raw_sub.lower()
                combined_text = (title_line + " " + sub_line).strip()
                print(f"[OCR-DualBand] Top (Main Zone)={repr(raw_title)} | Bot (Sub Map)={repr(raw_sub)}")
                if raw_title or raw_sub:
                    t_show = (raw_title[:15] + "..") if len(raw_title) > 15 else (raw_title if raw_title else "-")
                    s_show = (raw_sub[:15] + "..") if len(raw_sub) > 15 else (raw_sub if raw_sub else "-")
                    self.log_cmd(f"📷 OCR: [{t_show}] / [{s_show}]")
                else:
                    self.log_cmd("❌ OCR: ไม่พบข้อความในกรอบ")

                if not raw_title and not raw_sub:
                    if not silent:
                        self.root.after(0, lambda: set_btn_state("❌ No Match", bg="#3d1b1b", fg="#f87171"))
                        self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    return

                # =====================================================
                # 🏙️ Phase 0: Interception Check - ตรวจสอบ Town & Safe Zone ก่อนเสมอ!
                # ตรวจสอบทั้งบรรทัดย่อย (sub_line) และข้อความรวม (combined_text)
                # =====================================================
                TOWN_OCR_KEYWORDS = [
                    # คีย์เวิร์ดทั่วไปของเซฟโซน/เมือง (ดักจับทุกแมพในเกม)
                    "town", "village", "haven", "shelter", "campsite", "entrance", "safe zone",
                    "safe", "square", "lobby", "waiting room", "party room", "market", "station",
                    # Arcane River Towns & Camps
                    "nameless", "chu chu", "chew chew", "chewchew", "chu village", "chew village", "slurpy house",
                    "lachelein", "hotel lachelein", "main street", "arcana", "harp village",
                    "spirit tree", "morass", "trueffet", "esfera", "base camp",
                    "cernium", "burnium", "hotel arcus", "karrote", "odium",
                    # Victoria Island & Ossyria
                    "henesys", "ellinia", "perion", "kerning", "lith harbor", "nautilus",
                    "sleepywood", "orbis", "el nath", "aqua road", "aquarium", "ludibrium",
                    "leafre", "ariant", "magatia", "herb town", "mu lung", "korean folk",
                    "ereve", "elluel", "pantheon", "fox village", "savage terminal", "ristonia"
                ]

                detected_town = False
                detected_town_name = "ในเมือง"
                
                # ตรวจจากคีย์เวิร์ดเมือง: ดูจากทั้ง sub_line, title_line และ combined_text
                for town_kw in TOWN_OCR_KEYWORDS:
                    if town_kw in sub_line or town_kw in combined_text or town_kw in title_line:
                        detected_town = True
                        if "haven" in town_kw:
                            detected_town_name = "Haven"
                        elif "chu" in town_kw or "chew" in town_kw:
                            detected_town_name = "Chu Chu Village"
                        elif "entrance" in town_kw:
                            detected_town_name = "ทางเข้า / เซฟโซน"
                        else:
                            detected_town_name = town_kw.title()
                        print(f"[OCR-Town] Detected safe town: {detected_town_name} (from keyword '{town_kw}')")
                        break

                if detected_town:
                    is_same_town = silent and self.is_in_town and (self.last_ocr_map_str == f"town:{detected_town_name}")
                    def apply_town(t_name=detected_town_name, s_name=raw_sub, same=is_same_town):
                        self.is_in_town = True
                        self.has_no_drop = True
                        self.current_town_name = t_name
                        self.detected_submap_name = s_name if s_name else t_name
                        self.selected_layer_name = f"🏙️ {t_name}" if t_name != "ในเมือง" else "🏙️ ในเมือง"
                        self.last_ocr_map_str = f"town:{t_name}"
                        if not same:
                            self.log_cmd(f"🏙️ เข้าเมือง: {t_name}")
                        else:
                            self.log_cmd(f"🏙️ ปลอดภัย: {t_name}")
                        if same:
                            self.update_drop_ui()
                        else:
                            self.setup_ui_elements()
                        if not silent:
                            btn_txt = f"🏙️ {t_name[:6]}" if t_name != "ในเมือง" else "🏙️ Town"
                            set_btn_state(btn_txt, bg="#1e293b", fg="#94a3b8")
                            self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    self.root.after(0, apply_town)
                    return

                matched_item = None

                clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title_line).strip()
                clean_sub = re.sub(r'[^a-zA-Z0-9\s]', '', sub_line).strip()

                # =====================================================
                # 🗺️ Master Table: Global Sub-Map & Zone Alias ทั้งหมดใน MapleStory N
                # อ้างอิง layerId จริงจาก layers_cache.json ครอบคลุมทั้งโซนหลักและแมพย่อย
                # =====================================================
                GLOBAL_MAP_ALIASES = [
                    # --- Road of Vanishing / Arcane River (Arc. 30~100) ---
                    # 130002: "Extinction Zone"
                    (130002, ["weathered land of fire", "hidden fire zone", "extinction zone", "foot of the volcano",
                              "flame cliff", "fire river", "soul zone", "fire zone", "rocky area", "vanishing journey",
                              "extinction 1", "extinction 2", "extinction 3", "extinction"]),
                    # 130001: "Lake of Oblivion"
                    (130001, ["weathered land of happiness", "weathered land of rage", "weathered land of sadness",
                              "weathered land of joy", "cliff of rest", "lake of oblivion", "oblivion lake",
                              "restful rock", "vanishing lake", "oblivion"]),
                    # 130003: "Cave of Repose"
                    (130003, ["cave of repose", "below the cave", "hidden cave", "cave depths", "armas hideout",
                              "arma's hideout", "upper cave", "lower cave", "repose"]),
                    # 130004: "Underground" (Reverse City)
                    (130004, ["reverse city underground", "subway line 1", "subway line 2", "subway line 3",
                              "underground train", "tboys research lab", "t-boy's research lab", "subway track",
                              "underground", "subway", "train line", "t-boy"]),
                    # 130005: "Surface" (Reverse City)
                    (130005, ["reverse city surface", "surface 1", "surface 2", "surface 3", "hidden station",
                              "rooftop", "surface", "overpass"]),

                    # --- Chew Chew Island (Arc. 100~190) ---
                    # 131005: "Illiard Fungos"
                    (131005, ["slurpy forest depths", "slurpy forest", "illiard plains", "illiard fungos",
                              "one-a-bobber", "one a bobber", "bitty-bobber", "bitty bobber", "bobber 1", "bobber 2",
                              "slurpy", "fungos", "illiard"]),
                    # 131001: "Five-Color Hill"
                    (131001, ["five-color hill", "five color hill", "mottled forest 1", "mottled forest 2",
                              "mottled forest 3", "mottled forest", "colour hill", "hill path", "five-color", "five color", "mottled"]),
                    # 131002: "Eree Valley"
                    (131002, ["dealie-bobber forest", "dealie bobber forest", "eree valley 1", "eree valley 2",
                              "eree valley", "dealie-bobber", "dealie bobber", "dealie", "eree"]),
                    # 131003: "Skywhale Mountain"
                    (131003, ["skywhale mountain", "colossal root", "whale mountain", "skywhale peak",
                              "skywhale 1", "skywhale 2", "skywhale", "sky whale"]),
                    # 131004: "Mushbud Forest"
                    (131004, ["torrent zone 1", "torrent zone 2", "torrent zone 3", "torrent zone",
                              "mushbud forest", "mushbud 1", "mushbud 2", "mushbud"]),

                    # --- Lachelein (Arc. 190~240) ---
                    # 132001: "Lachelein Alley"
                    (132001, ["lachelein alleyway", "lachelein alley", "lachelein hideout", "backalley 1",
                              "backalley 2", "backalley 3", "backalley", "alley 1", "alley 2", "alley 3", "alleyway", "alley"]),
                    # 132002: "Lachelein Street"
                    (132002, ["occupied dance floor", "occupied dance", "theatre street", "victory plate",
                              "main street 1", "main street 2", "main street", "ballroom 1", "ballroom 2",
                              "ballroom 3", "ballroom", "lachelein street"]),
                    # 132003: "Lachelein Clocktower"
                    (132003, ["nightmare clocktower 1f", "nightmare clocktower 2f", "nightmare clocktower 3f",
                              "nightmare clocktower 4f", "nightmare clocktower 5f", "nightmare clocktower",
                              "lachelein clocktower", "clocktower 1f", "clocktower 2f", "clocktower 3f",
                              "clocktower 4f", "clocktower 5f", "clocktower 1", "clocktower 2", "clocktower 3",
                              "clocktower 4", "clocktower 5", "clocktower"]),

                    # --- Arcana (Arc. 280~360) ---
                    # 133001: "Near the Floral Flute"
                    (133001, ["between frost and lightning", "where fireflies dance", "forest of sunlight",
                              "forest of lightning", "forest of water", "forest of earth", "forest of frost",
                              "near the floral flute", "sun-drenched", "spirit tree", "spirit grove",
                              "floral flute", "fireflies", "flute"]),
                    # 133002: "Heart of the Forest"
                    (133002, ["grove of whispering", "tree of beginnings", "deep in the forest",
                              "heart of the forest", "heart of forest", "forest heart"]),
                    # 133003: "Cavernous Cavern"
                    (133003, ["deep in the cavern - lower path", "deep in the cavern - upper path",
                              "four-branch cave", "four branch cave", "cavern lower path", "cavern upper path",
                              "cavernous cavern", "deep cavern", "cavern lower", "cavern upper", "lower path", "upper path", "cavernous"]),

                    # --- Morass (Arc. 400~520) ---
                    # 134001: "Path to the Coral Forest"
                    (134001, ["path to the coral forest 1", "path to the coral forest 2", "path to the coral forest 3",
                              "path to the coral forest 4", "path to the coral forest 5", "path to the coral forest",
                              "path to the coral", "coral forest 1", "coral forest 2", "coral forest 3",
                              "coral forest 4", "coral forest 5", "coral forest", "coral path", "abandoned area"]),
                    # 134002: "Trueffet Street"
                    (134002, ["shadows of the swamp", "swamp of memory", "trueffet street", "bully boulevard",
                              "bully blvd 1", "bully blvd 2", "bully blvd 3", "bully blvd", "street 1", "street 2", "arpien"]),
                    # 134003: "Research Lab"
                    (134003, ["research laboratory", "research lab", "closed area", "laboratory 1", "laboratory 2", "laboratory", "lab"]),
                    # 134004: "That Day in Trueffet"
                    (134004, ["that day in trueffet 1", "that day in trueffet 2", "that day in trueffet 3",
                              "that day in trueffet 4", "that day in trueffet", "trueffet rampart", "that day 1",
                              "that day 2", "that day 3", "that day 4", "that day", "rampart", "castle wall"]),

                    # --- Esfera (Arc. 560~670) ---
                    # 135003: "Radiant Temple"
                    (135003, ["mirror light 1", "mirror light 2", "mirror light 3", "mirror light 4", "mirror light",
                              "living spring 1", "living spring 2", "living spring 3", "living spring",
                              "radiant temple", "temple of light", "mirror temple", "esfera temple"]),
                    # 136003: "Star-Swallowing Sea"
                    (136003, ["star-swallowing sea 1", "star-swallowing sea 2", "star-swallowing sea 3",
                              "star-swallowing sea", "deep mirror sea", "star-swallowing", "star swallowing",
                              "sea of tears", "esfera sea"]),

                    # --- Scrapyard & Black Heaven (Lv. 200~219) ---
                    # 122007: "Scrapyard, Black Heaven Inside 3"
                    (122007, ["black heaven junction 3", "black heaven inside 3", "black heaven inside 03", "scrapyard, black heaven inside 3",
                              "black heaven maze 7", "black heaven maze 6", "black heaven maze 5",
                              "maze 7", "maze 6", "maze 5", "junction 3", "inside 3", "inside 03", "deck 3", "bh inside 3", "bhi3"]),
                    # 122006: "Scrapyard, Black Heaven Inside 2"
                    (122006, ["black heaven junction 2", "black heaven inside 2", "black heaven inside 02", "scrapyard, black heaven inside 2",
                              "black heaven maze 4", "black heaven maze 3", "black heaven maze 2",
                              "maze 4", "maze 3", "maze 2", "junction 2", "inside 2", "inside 02", "deck 2", "bh inside 2", "bhi2"]),
                    # 122005: "Scrapyard, Black Heaven Inside 1"
                    (122005, ["black heaven junction 1", "black heaven inside 1", "black heaven inside 01", "scrapyard, black heaven inside 1",
                              "black heaven maze 1", "maze 1", "junction 1", "inside 1", "inside 01", "deck 1", "bh inside 1", "bhi1"]),
                    # 121002: "Scrapyard Skyline"
                    (121002, ["scrapyard skyline", "upper skyline", "skyline edge", "skyline 1", "skyline 2", "skyline"]),
                    # 121001: "Scrapyard"
                    (121001, ["scrapyard entrance", "scrapyard hill", "scrapyard lot", "scrapyard deck",
                              "scrapyard upper", "hillside 1", "hillside 2", "hillside", "scrapyard"]),

                    # --- Dark World Tree (Lv. 210~219) ---
                    # 122004: "Dark World Tree Top"
                    (122004, ["dark world tree top", "world tree top", "top branch", "upper stem", "dwt top", "tree top", "world tree 4"]),
                    # 122003: "Dark World Tree Mid Top"
                    (122003, ["dark world tree mid top", "world tree mid top", "upper left stem", "upper right stem",
                              "upper left", "upper right", "dwt mid top", "mid top", "world tree 3"]),
                    # 122002: "Dark World Tree Mid Bottom"
                    (122002, ["dark world tree mid bottom", "world tree mid bottom", "lower left stem", "lower right stem",
                              "lower left", "lower right", "dwt mid bottom", "mid bottom", "world tree 2"]),
                    # 122001: "Dark World Tree Bottom"
                    (122001, ["dark world tree bottom", "world tree bottom", "lower stem 1", "lower stem 2",
                              "lower stem 3", "lower stem", "tree bottom", "dwt bottom", "world tree 1"]),

                    # --- Twilight Perion / Fox Valley (Lv. 190~199) ---
                    # 120002: "Twilight Perion Excavation Area"
                    (120002, ["twilight perion excavation", "rough wilderness", "excavation area", "excavation site",
                              "wild cargo area", "wild cargo", "excavation 1", "excavation 2"]),
                    # 120001: "Twilight Perion"
                    (120001, ["deserted southern ridge", "twilight perion", "desolate hills", "perion ruins"]),
                    # 120003: "Fox Valley"
                    (120003, ["fox valley", "fox ridge", "fox tree", "fox forest"]),

                    # --- Kritias / Gate to the Future / Omega (Lv. 160~189) ---
                    # 118001: "Kritias"
                    (118001, ["ranheim", "kritias territory", "kritias northern", "kritias southern", "kritias"]),
                    # 117001: "Gate to the Future"
                    (117001, ["gate to the future", "henesys ruins", "dark ereve", "future henesys", "future perion", "future kerning"]),
                    # 117002: "Omega Sector"
                    (117002, ["omega sector", "boswell field", "command center", "robot zone", "hangar", "silo", "omega"]),

                    # --- Temple of Time / Kerning Tower (Lv. 140~169) ---
                    # 115001: "Temple of Time"
                    (115001, ["road of memory", "road of regret", "road of oblivion", "temple of time", "time temple"]),
                    # 115002: "Kerning Tower"
                    (115002, ["kerning square tower", "kerning tower floor", "kerning tower 2f", "kerning tower 3f",
                              "kerning tower 4f", "kerning tower 5f", "kerning tower 6f", "kerning tower",
                              "2f cafe", "2f café", "toy factory", "tower floor"]),

                    # --- Stone Colossus (Lv. 150~169) ---
                    # 116001: "Stone Colossus"
                    (116001, ["stone colossus", "stone golem", "colossus"]),

                    # --- Mu Lung / Korean Folk / Partem / Crimsonheart (Lv. 130~149) ---
                    # 114001: "Mu Lung Garden"
                    (114001, ["mu lung garden", "peach garden", "mu lung dojo", "snake area", "herb town", "mu lung"]),
                    # 114002: "Korean Folk Town"
                    (114002, ["korean folk town", "haunted house", "black mountain", "tiger forest", "korean folk", "folk town"]),
                    # 114003: "Dead Mine"
                    (114003, ["mine passage", "dead mine 1", "dead mine 2", "dead mine 3", "dead mine 4", "dead mine"]),
                    # 114004: "Golden Temple"
                    (114004, ["golden temple", "gold temple", "buddha"]),
                    # 114005: "Crimsonheart Castle"
                    (114005, ["crimsonheart castle", "crimsonheart", "crimson heart"]),
                    # 114006: "Partem"
                    (114006, ["partem ruins", "partem crater", "partem forest", "partem"]),

                    # --- Minar Forest / Dragon Forest (Lv. 120~159) ---
                    # 113001: "Minar Forest Dragon Forest"
                    (113001, ["minar forest dragon forest", "nest of dead dragon", "peak of the big horn", "peak of dragon",
                              "wyvern canyon", "wyvern valley", "dragon forest", "wyvern", "manon", "griffey"]),
                    # 113002: "Fantasy Theme World"
                    (113002, ["fantasy theme world", "fantasy theme park", "theme park", "fantasy world"]),

                    # --- Clocktower Bottom / Lion King (Lv. 110~139) ---
                    # 112001: "Clocktower Bottom Floor"
                    (112001, ["clocktower bottom floor", "warpped path of time", "forgotten path of time",
                              "path of time", "clocktower bottom", "clock tower bottom", "ludibrium clocktower"]),
                    # 112002: "Lion King's Castle"
                    (112002, ["lion king's castle", "lion king castle", "lionheart castle", "first tower",
                              "second tower", "third tower", "fourth tower", "fifth tower", "von leon", "lion king"]),

                    # --- Magatia / Heliseum / Ludibrium (Lv. 90~119) ---
                    # 110001: "Magatia"
                    (110001, ["alcadno research", "zenumist research", "magatia", "alcadno", "zenumist", "alchemy", "zern"]),
                    # 110002: "Ludibrium"
                    (110002, ["ludibrium", "toy world", "toy room", "eos tower", "helios tower", "ludi"]),
                    # 110003: "Ellin Forest"
                    (110003, ["deep fairy forest", "ancient forest", "ellin forest", "ellin"]),
                    # 110004: "Heliseum"
                    (110004, ["downtown black market", "heliseum", "beldar"]),

                    # --- Minar Forest / Aqua Road Deep / Tyrant (Lv. 100~119) ---
                    # 111001: "Minar Forest"
                    (111001, ["entrance to dragon forest", "dragon nest", "minar forest", "leafre", "beetle", "centipede"]),
                    # 111002: "Aqua Road Deep Sea"
                    (111002, ["mushroom coral hill", "aqua road deep sea", "deep sea gorge", "deep underwater",
                              "aqua dungeon", "deep sea", "submerged"]),
                    # 111003: "Heliseum Tyrant's Territory"
                    (111003, ["heliseum tyrant's territory", "tyrant's territory", "tyrant territory",
                              "tyrant's castle", "tyrant castle", "commander"]),

                    # --- Aqua Road / Sky Road / El Nath (Lv. 70~89) ---
                    # 108001: "Aqua Road"
                    (108001, ["crystal dunes", "aqua road", "aquarium", "seaweed"]),
                    # 108002: "Sky Road"
                    (108002, ["cloud park", "orbis tower", "sky road", "orbis"]),
                    # 108003: "El Nath Mountains"
                    (108003, ["el nath mountains", "sharp cliff", "snowfield", "cold field", "el nath"]),

                    # --- Nihal Desert / Verne Mine (Lv. 80~99) ---
                    # 109001: "Nihal Desert"
                    (109001, ["burning sands", "nihal desert", "ariant", "desert"]),
                    # 109002: "Verne Mine"
                    (109002, ["edelstein mine", "verne mine", "mine"]),

                    # --- Beginner Zones ---
                    # 107001: "Mushroom Castle"
                    (107001, ["mushroom castle", "mushroom shrine", "mushroom forest"]),
                    # 107002: "Sleepywood"
                    (107002, ["evil eye cave", "drakes chasm", "ant tunnel", "zombie dungeon", "sleepy wood", "sleepywood"]),
                    # 106001: "Perion"
                    (106001, ["warrior grounds", "rocky mountain", "wild boar land", "perion"]),
                    # 105001: "Kerning City"
                    (105001, ["kerning square", "sunset sky", "kerning subway", "kerning city", "kerning"]),
                    # 104001: "Gold Beach"
                    (104001, ["gold beach resort", "holiday resort", "gold beach", "beach"]),
                    # 104002: "Riena Strait"
                    (104002, ["riena strait", "riena", "ship"]),
                    # 104003: "Edelstein"
                    (104003, ["resistance hq", "edelstein"]),
                    # 104004: "Elodin"
                    (104004, ["elodin"]),
                    # 104005: "Ellinel"
                    (104005, ["ellinel fairy academy", "ellinel"]),
                    # 103001: "The Adventure Begins"
                    (103001, ["southperry beach", "the adventure begins", "adventure begins", "southperry", "amherst"]),
                    # 102001: "Prepare for Adventure"
                    (102001, ["prepare for adventure", "nautilus port"]),
                ]

                # =====================================================
                # 🎯 Phase 1: Sub-Map First Matching ผ่าน Global Aliases (ลำดับสำคัญสูงสุด!)
                # แถวล่าง (Sub Map) คือชื่อห้อง/สถานที่จริงที่เฉพาะเจาะจงที่สุด
                # =====================================================
                if clean_sub:
                    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
                        # เรียงคีย์เวิร์ดจากยาวไปสั้น เพื่อให้ได้คำที่เฉพาะเจาะจงที่สุดก่อน
                        for kw in sorted(kw_list, key=len, reverse=True):
                            if kw in sub_line:
                                matched_item = next((item for item in self.layers_list if item["layerId"] == target_lid), None)
                                if matched_item:
                                    print(f"[OCR-SubMap] Sub-map direct match: {matched_item['layerName']} (ID: {matched_item['layerId']}) via '{kw}'")
                                    break
                        if matched_item:
                            break

                # =====================================================
                # 🎯 Phase 2: Combined Text Matching ผ่าน Global Aliases
                # (กรณีที่ Sub-Map สั้น หรือคำระบุแมพกระจายอยู่ทั้งสองบรรทัด)
                # =====================================================
                if not matched_item:
                    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
                        for kw in sorted(kw_list, key=len, reverse=True):
                            if kw in combined_text:
                                matched_item = next((item for item in self.layers_list if item["layerId"] == target_lid), None)
                                if matched_item:
                                    print(f"[OCR-Alias] Combined match: {matched_item['layerName']} (ID: {matched_item['layerId']}) via '{kw}'")
                                    break
                        if matched_item:
                            break

                # =====================================================
                # 🎯 Phase 3: Exact Match 100% (คำตรงกันเป๊ะ ทั้ง Sub หรือ Combined)
                # ห้ามทำ clean_title in clean_lname เด็ดขาดเพื่อป้องกันชื่อสั้นชนชื่อยาว!
                # =====================================================
                if not matched_item:
                    for item in self.layers_list:
                        clean_lname = re.sub(r'[^a-zA-Z0-9\s]', '', item["layerName"].lower()).strip()
                        if clean_sub and clean_sub == clean_lname:
                            matched_item = item
                            print(f"[OCR-Exact] Sub-map exact match: {item['layerName']} (ID: {item['layerId']})")
                            break
                        if combined_text == clean_lname:
                            matched_item = item
                            print(f"[OCR-Exact] Combined exact match: {item['layerName']} (ID: {item['layerId']})")
                            break
                        if clean_title == clean_lname and not clean_sub:
                            matched_item = item
                            print(f"[OCR-Exact] Title exact match (solo): {item['layerName']} (ID: {item['layerId']})")
                            break

                # =====================================================
                # 🎯 Phase 4: Smart Zone Disambiguation (ป้องกันแมพที่มีหลาย Sub-Layer ซ้ำชื่อกัน)
                # =====================================================
                if not matched_item:
                    # 4.1 Black Heaven (Inside 1, 2, 3)
                    if "black heaven" in combined_text or "scrapyard" in combined_text:
                        if any(x in combined_text for x in ["inside 3", "junction 3", "maze 7", "maze 6", "maze 5", "deck 3"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122007), None)
                        elif any(x in combined_text for x in ["inside 2", "junction 2", "maze 4", "maze 3", "maze 2", "deck 2"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122006), None)
                        elif any(x in combined_text for x in ["inside 1", "junction 1", "maze 1", "deck 1"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122005), None)
                        elif "skyline" in combined_text:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 121002), None)
                        elif "scrapyard" in combined_text and not any(x in combined_text for x in ["inside", "junction", "maze", "deck"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 121001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Black Heaven/Scrapyard resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.2 Dark World Tree (Bottom, Mid Bottom, Mid Top, Top)
                    elif "dark world tree" in combined_text or "world tree" in combined_text or "dwt" in combined_text:
                        if any(x in combined_text for x in ["mid top", "upper left", "upper right", "upper stem", "mid-top"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122003), None)
                        elif any(x in combined_text for x in ["mid bottom", "lower left", "lower right", "mid-bottom", "mid bot"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122002), None)
                        elif any(x in combined_text for x in ["top branch", "tree top", "dwt top"]) or (clean_sub and "top" in clean_sub):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122004), None)
                        elif any(x in combined_text for x in ["bottom", "lower stem", "tree bottom", "dwt bottom"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 122001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Dark World Tree resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.3 Lachelein (Alley, Street, Clocktower)
                    elif "lachelein" in combined_text:
                        if any(x in combined_text for x in ["clocktower", "nightmare", "tower"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132003), None)
                        elif any(x in combined_text for x in ["street", "ballroom", "dance", "theatre", "plate"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132002), None)
                        elif any(x in combined_text for x in ["alley", "hideout", "alleyway", "backalley"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 132001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Lachelein resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.4 Twilight Perion (Main vs Excavation Area)
                    elif "twilight perion" in combined_text:
                        if any(x in combined_text for x in ["excavation", "wild cargo", "cargo", "wilderness"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 120002), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 120001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Twilight Perion resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.5 Minar Forest (Main vs Dragon Forest)
                    elif "minar forest" in combined_text or "leafre" in combined_text:
                        if any(x in combined_text for x in ["dragon", "wyvern", "nest", "peak", "manon", "griffey"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 113001), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Minar Forest resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.6 Aqua Road (Main vs Deep Sea)
                    elif "aqua road" in combined_text or "aquarium" in combined_text:
                        if any(x in combined_text for x in ["deep", "gorge", "underwater", "coral hill"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111002), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 108001), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Aqua Road resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                    # 4.7 Heliseum (Downtown vs Tyrant's Territory)
                    elif "heliseum" in combined_text:
                        if any(x in combined_text for x in ["tyrant", "castle", "commander"]):
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 111003), None)
                        else:
                            matched_item = next((it for it in self.layers_list if it["layerId"] == 110004), None)
                        if matched_item:
                            print(f"[OCR-Disambig] Heliseum resolved: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                # =====================================================
                # 🎯 Phase 5: Direct LayerName Substring (ทิศทางเดียว: clean_lname in OCR text)
                # ชื่อ Layer ใน API ต้องปรากฏอยู่ในข้อความที่ OCR อ่านได้ และเลือกชื่อที่ยาวที่สุด
                # =====================================================
                if not matched_item:
                    best_sub_item = None
                    max_sub_len = 0
                    for item in self.layers_list:
                        clean_lname = re.sub(r'[^a-zA-Z0-9\s]', '', item["layerName"].lower()).strip()
                        if len(clean_lname) >= 6 and (clean_lname in clean_sub or clean_lname in combined_text):
                            if len(clean_lname) > max_sub_len:
                                max_sub_len = len(clean_lname)
                                best_sub_item = item
                    if best_sub_item:
                        matched_item = best_sub_item
                        print(f"[OCR-Substring] LayerName found in OCR text: {matched_item['layerName']} (ID: {matched_item['layerId']})")

                # =====================================================
                # 🎯 Phase 6: Multi-Tier Distinctive Word Scoring (Fallback สุดท้าย)
                # =====================================================
                if not matched_item:
                    GENERIC_TERMS = {
                        "forest", "valley", "mountain", "mountains", "hill", "hills", "path", "road", "street",
                        "alley", "cave", "entrance", "outskirts", "area", "zone", "sea", "lake", "river",
                        "deep", "depths", "top", "bottom", "mid", "middle", "floor", "inside", "cliff",
                        "peak", "station", "closed", "hideout", "castle", "tower", "garden", "town", "ruins", "field"
                    }
                    raw_words = re.findall(r'[a-zA-Z0-9]+', combined_text)
                    distinctive_words = [w for w in raw_words if len(w) >= 3 and w not in GENERIC_TERMS]

                    best_score = 0
                    best_item = None
                    for item in self.layers_list:
                        lname = item["layerName"].lower()
                        gname = item.get("groupName", "").lower()
                        score = 0
                        for w in distinctive_words:
                            if w in lname:
                                score += len(w) * 3
                            elif w in gname:
                                score += len(w) * 1.5
                        
                        if score > 0:
                            sim = difflib.SequenceMatcher(None, title_line if title_line else combined_text, lname).ratio()
                            score += sim * 4.0

                        if score > best_score:
                            best_score = score
                            best_item = item

                    if best_score >= 8.0:
                        matched_item = best_item
                        print(f"[OCR-Scoring] Distinctive word match: {matched_item['layerName']} (ID: {matched_item['layerId']}) (Score: {best_score:.1f})")
                            
                # ถ้าเจอ Field แน่นอน ให้ใช้ Field ทันที!
                if matched_item:
                    target_item = matched_item
                    is_layer_changed = (self.selected_layer_id != target_item["layerId"]) or self.is_in_town
                    is_sub_changed = bool(raw_sub and raw_sub.strip() != getattr(self, 'detected_submap_name', '').strip())
                    
                    if not is_layer_changed and not is_sub_changed and silent:
                        # 🛡️ แมพและห้องเดิมเป๊ะ: ไม่แตะต้องชื่อแมพ ไม่เปลี่ยนค่าใดๆ ทั้งสิ้น แต่ยิงแค่ API ดรอปเรทอย่างเดียว!
                        sub_info = f" ({self.detected_submap_name})" if getattr(self, 'detected_submap_name', '') else ""
                        self.log_cmd(f"📍 แมพเดิม: {target_item['layerName']}{sub_info}")
                        self.fetch_drop_data_async()
                        return
                    elif not is_layer_changed and is_sub_changed and silent:
                        # 🚪 อยู่ในโซนเดิมแต่เปลี่ยนห้องย่อย! อัปเดตชื่อห้องทันที
                        def update_submap_only(s_name=raw_sub):
                            self.detected_submap_name = s_name.strip() if s_name else ""
                            self.save_config()
                            self.update_drop_ui()
                            self.log_cmd(f"🚪 เปลี่ยนห้อง: {self.detected_submap_name}")
                        self.root.after(0, update_submap_only)
                        self.fetch_drop_data_async()
                        return

                    # กรณีเปลี่ยนแมพจริง หรือผู้ใช้กดปุ่ม Scan เอง:
                    def apply_match(s_name=raw_sub):
                        self.is_in_town = False  # ออกจากเมืองแล้ว - เคลียร์ flag
                        self.current_town_name = ""
                        self.detected_submap_name = s_name.strip() if s_name else ""
                        self.selected_layer_id = target_item["layerId"]
                        self.selected_layer_name = target_item["layerName"]
                        self.selected_group_name = target_item["groupName"]
                        self.last_ocr_map_str = f"field:{target_item['layerId']}"
                        sub_info = f" ({self.detected_submap_name})" if self.detected_submap_name else ""
                        self.log_cmd(f"🎯 แมตช์แมพ: {target_item['layerName']}{sub_info}")
                        self.save_config()
                        self.fetch_drop_data_async()
                        self.setup_ui_elements()
                        if not silent:
                            set_btn_state("✅ Matched", bg="#103823", fg="#4ade80")
                            self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    
                    self.root.after(0, apply_match)
                    return



                # ลำดับที่ 3: ไม่ตรงทั้ง Field และ Town
                # 🛡️ หัวใจสำคัญ: ถ้าเป็นการ Auto-scan เบื้องหลัง (silent=True) ห้ามลบหรือเปลี่ยนแมพเดิมเด็ดขาด!
                if silent:
                    return

                # ผู้ใช้กดปุ่ม Scan Map เอง
                if raw_text and len(raw_text.strip()) >= 4:
                    def apply_fallback_town(s_name=raw_sub, t_text=raw_text.split('\n')[0].strip()):
                        self.is_in_town = True
                        self.has_no_drop = True
                        self.current_town_name = t_text if t_text else "ในเมือง"
                        self.detected_submap_name = s_name if s_name else t_text
                        self.selected_layer_name = f"🏙️ {self.current_town_name}"
                        self.setup_ui_elements()
                        set_btn_state("🏙️ Town", bg="#1e293b", fg="#94a3b8")
                        self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                    self.root.after(0, apply_fallback_town)
                else:
                    self.root.after(0, lambda: set_btn_state("❌ No Match", bg="#3d1b1b", fg="#f87171"))
                    self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
                
        except Exception as e:
            print("OCR Error:", e)
            if not silent:
                self.root.after(0, lambda: set_btn_state("⚠️ Error", bg="#3d1b1b", fg="#f87171"))
                self.root.after(1600, lambda: set_btn_state("🔍 Scan", bg="#16202c", fg="#38bdf8"))
        finally:
            # เคลียร์ตัวแปรและคืนหน่วยความจำทันที ไม่ค้างในแรม
            if 'sct' in locals():
                try:
                    sct.close()
                except Exception:
                    pass

    def fetch_drop_data_async(self):
        """ส่งคำขอไปยัง Official MSU OpenAPI เพื่อดึง % ดรอปและยอดกระเป๋าแบบ Background Thread"""
        if self.is_fetching:
            return
        self.is_fetching = True
        threading.Thread(target=self._fetch_drop_data_worker, daemon=True).start()

    def _fetch_nxpc_price_sync(self):
        try:
            now = time.time()
            if now - self.nxpc_last_fetch > 300: # 5 mins
                url = "https://api.coingecko.com/api/v3/simple/price?ids=nexpace&vs_currencies=usd,thb"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.nxpc_usd = data.get("nexpace", {}).get("usd", 0.0)
                    self.nxpc_thb = data.get("nexpace", {}).get("thb", 0.0)
                self.nxpc_last_fetch = now
        except Exception as e:
            print("Fetch NXPC price error:", e)

    def _fetch_wallet_neso_sync(self):
        """ดึงยอดเหรียญ NESO ในกระเป๋าผ่าน Official MSU OpenAPI"""
        self._fetch_nxpc_price_sync()
        try:
            if not self.wallet_addr:
                return
            key = self.get_current_api_key()
            url = f"https://openapi.msu.io/v1rc1/accounts/{self.wallet_addr}/neso"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                    "x-nxopen-api-key": key
                },
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                self.api_call_count += 1
                res = json.loads(resp.read().decode("utf-8"))
            if res.get("success"):
                onchain_raw = res.get("data", {}).get("onchainNeso", "0")
                onchain_val = int(onchain_raw) / (10**18)
                self.wallet_neso_str = f"{onchain_val:,.1f}"
                self.wallet_neso_compact = format_compact_number(onchain_val)
                
                if not getattr(self, 'current_char_nesolet_loaded', False):
                    offchain_raw = res.get("data", {}).get("offchainNeso", "0")
                    offchain_val = int(offchain_raw) / (10**18)
                    self.wallet_nesolet_str = f"{offchain_val:,.1f}"
                    self.wallet_nesolet_compact = format_compact_number(offchain_val)
        except Exception as e:
            print("Fetch wallet neso error:", e)

    def _fetch_drop_data_worker(self):
        try:
            # 🛡️ ถ้าอยู่ในเมือง: ข้าม Reward API ทั้งหมด แค่ดึงยอดกระเป๋าและอัปเดต UI
            if self.is_in_town:
                self.has_no_drop = True
                self.last_update_str = datetime.now().strftime("%H:%M:%S")
                self._fetch_wallet_neso_sync()
                self.root.after(0, self.update_drop_ui)
                return

            if not self.selected_layer_id:
                # ยังไม่มีการเลือกแมพ หรือกำลังรอตรวจจับในเกม
                self.neso_normal_rate = "รอแมพ"
                self.neso_normal_stock = "---"
                self.neso_boost_rate = "รอแมพ"
                self.neso_boost_mult = ""
                self.neso_boost_stock = "---"
                self.last_update_str = datetime.now().strftime("%H:%M:%S")
                self._fetch_wallet_neso_sync()
                self.root.after(0, self.update_drop_ui)
                return

            # Map server name to worldId: Fang=0, Ain=1, Errai=2
            w_id = getattr(self, 'world_id', 0)
            url = f"https://openapi.msu.io/v1rc1/msn/rewards/{w_id}"

            # รวบรวม Layers ในโซนเดียวกันทั้งหมดเพื่อหาแมพแนะนำ
            curr_item = next((it for it in self.layers_list if it.get("layerId") == self.selected_layer_id), None)
            if curr_item and curr_item.get("groupName"):
                self.selected_group_name = curr_item.get("groupName")

            all_query_layers = []
            if self.selected_layer_id:
                all_query_layers.append(int(self.selected_layer_id))

            if self.selected_group_name:
                zone_layers = [it for it in self.layers_list if it.get("groupName") == self.selected_group_name]
                for zl in zone_layers:
                    lid = int(zl["layerId"])
                    if lid not in all_query_layers:
                        all_query_layers.append(lid)

            # จำกัดไม่เกิน 15 layers เพื่อประสิทธิภาพ
            all_query_layers = all_query_layers[:15]

            payload = {
                "layerDescs": [{"layerId": lid} for lid in all_query_layers]
            }

            res = None
            # วนลูปสลับคีย์ถ้าติด Error หรือ Rate limit
            for attempt in range(len(self.api_keys)):
                key = self.get_current_api_key()
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Content-Type": "application/json",
                        "x-nxopen-api-key": key
                    },
                    method="POST"
                )
                try:
                    start_ping = time.time()
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        self.server_ping_ms = int((time.time() - start_ping) * 1000)
                        self.api_call_count += 1
                        res = json.loads(resp.read().decode("utf-8"))
                        if res.get("success"):
                            self.rotate_api_key() # หมุนเวียนคีย์เพื่อเฉลี่ยโหลด
                            break
                        else:
                            self.rotate_api_key()
                except Exception as ex:
                    print(f"Key attempt {attempt+1} failed: {ex}")
                    self.rotate_api_key()
                    if attempt == len(self.api_keys) - 1:
                        raise ex
            
            def _to_f(val):
                try:
                    return float(val)
                except:
                    return 0.0

            if res and res.get("success"):
                reward_infos = res.get("data", {}).get("rewardInformations", {}).get("rewardInformations", [])
                has_neso_item = False
                
                # ค้นหาข้อมูลของแมพปัจจุบันที่เลือกอยู่จริง ๆ (ตรงตาม layerId)
                target_reward_info = None
                for r_info in reward_infos:
                    f_info = r_info.get("fieldInformation", {})
                    if f_info.get("layerId") == int(self.selected_layer_id):
                        target_reward_info = f_info
                        break
                
                # ถ้าไม่เจอให้ fallback ไปตัวแรกถ้ามี
                if not target_reward_info and reward_infos:
                    target_reward_info = reward_infos[0].get("fieldInformation", {})

                if target_reward_info:
                    items = target_reward_info.get("items", [])
                    
                    # แยก NESO Normal และ NESO Boost
                    for itm in items:
                        if itm.get("key", {}).get("itemId") == 1:
                            has_neso_item = True
                            is_boost = itm.get("enableBoostOption", False)
                            drop_val = _to_f(itm.get("dropProb", {}).get("value", 0))
                            base_val = _to_f(itm.get("baseProb", {}).get("value", 0))
                            stock_val = _to_f(itm.get("currentStock", {}).get("value", 0))
                            min_qty = _to_f(itm.get("dropQuantityMin", {}).get("value", 0))
                            max_qty = _to_f(itm.get("dropQuantityMax", {}).get("value", 0))
                            chg_val = _to_f(itm.get("stockPerCharge", {}).get("value", 0))
                            
                            if is_boost:
                                mult = (drop_val / base_val) if base_val > 0 else 1.0
                                self.neso_boost_rate_f = drop_val
                                self.neso_boost_stock_f = stock_val
                                self.neso_boost_base_f = base_val
                                self.neso_boost_charge_f = chg_val
                                self.neso_boost_min_f = min_qty
                                self.neso_boost_max_f = max_qty
                                self.neso_boost_rate = f"{drop_val:.2f}%"
                                self.neso_boost_mult = f"x{mult:.1f}"
                                
                                sure_drop = int(drop_val // 100)
                                chance_drop = drop_val % 100
                                extra_rate = max(0.0, drop_val - base_val)
                                
                                # คำนวณช่วงตัวเลข NESO ที่แน่นอน (Per Drop & Expected Total)
                                self.neso_boost_sure_min = sure_drop * min_qty
                                self.neso_boost_sure_max = sure_drop * max_qty
                                self.neso_boost_extra_min = (chance_drop / 100.0) * min_qty
                                self.neso_boost_extra_max = (chance_drop / 100.0) * max_qty
                                self.neso_boost_total_min = (drop_val / 100.0) * min_qty
                                self.neso_boost_total_max = (drop_val / 100.0) * max_qty
                                
                                if sure_drop > 0:
                                    self.neso_boost_sure_txt = f"{self.neso_boost_sure_min:.2f} ~ {self.neso_boost_sure_max:.2f} NESO"
                                else:
                                    self.neso_boost_sure_txt = "0 NESO"
                                
                                self.neso_boost_extra_txt = f"{self.neso_boost_extra_min:.2f} ~ {self.neso_boost_extra_max:.2f} ({chance_drop:.2f}%)"
                                self.neso_boost_total_txt = f"{self.neso_boost_total_min:.2f} ~ {self.neso_boost_total_max:.2f} NESO"
                                self.neso_boost_breakdown_txt = f"{drop_val:.2f}% ({base_val:.0f}% + {extra_rate:.2f}%)"
                                self.neso_boost_stock = format_compact_number(stock_val)
                                self.neso_boost_charge = format_compact_number(chg_val)
                                self.neso_boost_detail = f"การันตี {sure_drop} + {chance_drop:.1f}%"
                            else:
                                self.neso_normal_rate_f = drop_val
                                self.neso_normal_stock_f = stock_val
                                self.neso_normal_rate = f"{drop_val:.1f}%"
                                self.neso_normal_stock = format_compact_number(stock_val)
                                self.neso_normal_drop_qty = format_compact_number((drop_val / 100.0) * stock_val)

                    if has_neso_item and (getattr(self, 'neso_normal_rate_f', 0) > 0 or getattr(self, 'neso_boost_rate_f', 0) > 0 or getattr(self, 'neso_boost_stock_f', 0) > 0):
                        self.has_no_drop = False
                    else:
                        self.has_no_drop = True
                        self.neso_normal_rate = "--"
                        self.neso_normal_stock = "0"
                        self.neso_normal_rate_f = 0.0
                        self.neso_normal_stock_f = 0.0
                        self.neso_boost_rate = "--"
                        self.neso_boost_rate_f = 0.0
                        self.neso_boost_stock_f = 0.0
                        self.neso_boost_stock = "0"
                        self.neso_boost_mult = ""
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
                        self.neso_boost_breakdown_txt = "--"
                        self.neso_boost_charge = "--"
                    self.last_update_str = datetime.now().strftime("%H:%M:%S")
                else:
                    self.has_no_drop = True
                    self.last_update_str = datetime.now().strftime("%H:%M:%S")
            else:
                self.has_no_drop = True
                self.last_update_str = datetime.now().strftime("%H:%M:%S")

            # ค้นหาแมพแนะนำในโซนที่มี % Boost สูงสุด (สำหรับโชว์ในกรอบแนะนำเท่านั้น ไม่เกี่ยวกับตารางคำนวณหลัก)
            if res and res.get("success"):
                best_rate = -1.0
                best_map_obj = None
                for r_info in reward_infos:
                    f_info = r_info.get("fieldInformation", {})
                    lid = f_info.get("layerId")
                    if lid:
                        for itm in f_info.get("items", []):
                            if itm.get("key", {}).get("itemId") == 1 and itm.get("enableBoostOption", False):
                                b_rate = _to_f(itm.get("dropProb", {}).get("value", 0))
                                b_stk = _to_f(itm.get("currentStock", {}).get("value", 0))
                                if b_rate > best_rate:
                                    layer_meta = next((l for l in self.layers_list if l["layerId"] == lid), None)
                                    lname = layer_meta.get("layerName", f"Field #{lid}") if layer_meta else f"Field #{lid}"
                                    best_rate = b_rate
                                    best_map_obj = {
                                        "layerId": lid,
                                        "layerName": lname,
                                        "rate": b_rate,
                                        "stock": b_stk
                                    }
                self.best_zone_map = best_map_obj
                if self.best_zone_map:
                    now_ts = time.time()
                    last_log_ts = getattr(self, 'last_hot_log_ts', 0)
                    last_logged_lid = getattr(self, 'last_hot_logged_lid', None)
                    if (now_ts - last_log_ts >= 15) or (last_logged_lid != self.best_zone_map['layerId']):
                        self.last_hot_log_ts = now_ts
                        self.last_hot_logged_lid = self.best_zone_map['layerId']
                        self.log_cmd(f"🔥 แนะนำในโซน: {self.best_zone_map['layerName']} ({self.best_zone_map['rate']:.1f}%)")
            else:
                self.best_zone_map = None

            # ดึงยอดกระเป๋าต่อเสมอ
            self._fetch_wallet_neso_sync()

            # แจ้ง UI อัปเดตข้อมูลบนหน้าจอ
            self.root.after(0, self.update_drop_ui)
        except Exception as e:
            print("Fetch drop data error:", e)
            if self.neso_boost_rate == "...":
                self.neso_boost_rate = "รอข้อมูล"
            if self.neso_boost_stock == "...":
                self.neso_boost_stock = "รอเซิร์ฟเวอร์"
            self.last_update_str = datetime.now().strftime("%H:%M:%S")
            # แม้กระทั่ง error ก็ดึงกระเป๋าและอัปเดต UI เสมอ
            self._fetch_wallet_neso_sync()
            self.root.after(0, self.update_drop_ui)
        finally:
            self.last_fetch_ts = time.time()
            self.is_fetching = False

    def format_compact_number(self, num):
        try:
            val = float(num)
            if val >= 1_000_000:
                return f"{val/1_000_000:.2f}M"
            elif val >= 10_000:
                return f"{val/1_000:.1f}k"
            else:
                return f"{int(val):,}"
        except:
            return str(num)

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
                if getattr(self, 'f_bot_action', None):
                    self.f_boost_info_left.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(3, 1), before=self.f_bot_action)
                else:
                    self.f_boost_info_left.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(3, 1))

            if getattr(self, 'f_hot_farm', None) and not self.f_hot_farm.winfo_ismapped():
                if getattr(self, 'f_cmd_box', None):
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

        ico_full = self.get_zone_icon(ico_key, size_h=22)
        ico_mini = self.get_zone_icon(ico_key, size_h=15)

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
        if getattr(self, 'lbl_hot_map', None) is not None and self.lbl_hot_map.winfo_exists():
            if self.best_zone_map:
                b_name = self.best_zone_map.get("layerName", "")
                if len(b_name) > 22:
                    b_name = b_name[:20] + ".."
                self.lbl_hot_map.config(text=f"🔥 {b_name}", fg="#fde047")
            else:
                self.lbl_hot_map.config(text="🔥 แนะนำในโซน...", fg="#94a3b8")

        if getattr(self, 'lbl_hot_rate', None) is not None and self.lbl_hot_rate.winfo_exists():
            if self.best_zone_map:
                self.lbl_hot_rate.config(text=f"{self.best_zone_map.get('rate', 0.0):.1f}%", fg="#4ade80")
            else:
                self.lbl_hot_rate.config(text="--%", fg="#64748b")

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
                    # จำการปรับขนาดแยกตามโหมด (V.2 แนวนอน และ Vertical Sidebar)
                    self.v2_w = max(245, cfg.get("v2_w", 460))
                    self.v2_h = max(200, cfg.get("v2_h", 355))
                    self.sidebar_w = max(160, cfg.get("sidebar_w", 210))
                    self.sidebar_h = max(520, cfg.get("sidebar_h", 535))
                    # บังคับเปิดครั้งแรก/เปิดใหม่ ให้เป็นหน้าต่างหลักปกติ (V.2 แนวนอน) เสมอตามคำสั่งผู้ใช้
                    self.full_w = self.v2_w
                    self.full_h = self.v2_h
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
                    self.is_mini = False # ดีฟอลต์เวลาเปิดโปรแกรมคือหน้าต่างหลักเสมอตามคำสั่ง
                    self.is_compact_folded = True # ดีฟอลต์หน้าต่างหลักปกติ V.2 พับแถบแดงล่างไว้
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
                    self.full_h = max(200, cur_h)
                    if cur_w <= 240:
                        self.sidebar_w = cur_w
                        self.sidebar_h = cur_h
                    else:
                        self.v2_w = cur_w
                        self.v2_h = cur_h
        except Exception:
            pass

        cfg = {
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "full_w": self.full_w,
            "full_h": self.full_h,
            "v2_w": getattr(self, 'v2_w', 460),
            "v2_h": getattr(self, 'v2_h', 355),
            "sidebar_w": getattr(self, 'sidebar_w', 210),
            "sidebar_h": getattr(self, 'sidebar_h', 535),
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
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        
        # 🔒 ฟิกลิมิตขั้นต่ำ ป้องกันการย่อจนตัวอักษรและปุ่มมุดหาย (รองรับ Vertical Sidebar แคบ 160px)
        if self.is_mini:
            new_w = max(460, self._start_w + dx)
            new_h = 64
            self.mini_w = new_w
            self.mini_h = new_h
        else:
            new_w = max(160, self._start_w + dx)
            new_h = max(200, self._start_h + dy)
            self.full_w = new_w
            self.full_h = new_h
            if new_w <= 240:
                self.sidebar_w = new_w
                self.sidebar_h = new_h
            else:
                self.v2_w = new_w
                self.v2_h = new_h
            
        # 🛡️ ล็อกพิกัด +{pos_x}+{pos_y} ตลอดการย่อขยาย หน้าต่างไม่ดิ้นหนีเมาส์เด็ดขาด!
        geom = f"{new_w}x{new_h}+{self.pos_x}+{self.pos_y}"
        self.win_bg.geometry(geom)
        self.win_fg.geometry(geom)
        try:
            self.win_bg.update_idletasks()
            self.win_fg.update_idletasks()
            if not self.is_mini:
                self.redraw_full_canvas()
                self.update_auto_scale_ui(new_w)
        except:
            pass
        self.win_fg.lift()

    def end_resize(self, event):
        """บันทึกขนาดหน้าต่างเมื่อปล่อยเมาส์จากการลากมุม (ลื่นไหล 60-120fps ตามหลักสากล)"""
        self.save_config()

    def redraw_full_canvas(self):
        """วาดวงแหวนและตัวเลขนับถอยหลัง ปรับขนาดตามหน้าต่างจริง (ลดลง 60% ตามสั่ง ไม่กินพื้นที่การ์ด)"""
        if not hasattr(self, 'canvas_full') or not self.canvas_full.winfo_exists():
            return
        remaining_seconds, total_seconds = self.calculate_remaining()
        mins = int(remaining_seconds) // 60
        secs = int(remaining_seconds) % 60
        countdown_str = f"{mins:02d}:{secs:02d}"

        if remaining_seconds <= 120:
            theme_color = "#ff4d4f" if self.pulse_state else "#ff7875"
        elif remaining_seconds <= 300:
            theme_color = "#f59e0b"
        else:
            theme_color = "#00f2fe"

        self.canvas_full.delete("all")
        cw = self.canvas_full.winfo_width()
        ch = self.canvas_full.winfo_height()
        if cw <= 1 or ch <= 1:
            cw = self.win_bg.winfo_width()
            ch = max(80, self.win_bg.winfo_height() - 250)
            
        cx = cw / 2
        cy = ch / 2
        # ขนาดวงแหวนตรงกลางสัดส่วนกระชับพอดีกับการ์ด Pool ซ้ายและขวา
        r = max(24, min(36, int(min(cw * 0.40, ch * 0.40))))
        
        # รางหลังวงแหวน
        self.canvas_full.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#1e293b", width=4)
        
        # วงแหวน Progress
        fraction = remaining_seconds / total_seconds
        extent = fraction * 360
        self.canvas_full.create_arc(cx - r, cy - r, cx + r, cy + r, 
                                   start=90, extent=extent, 
                                   outline=theme_color, width=4, style=tk.ARC)
        
        # ตัวเลขนับถอยหลัง 20 นาที สว่างจ้า คมชัด
        font_sz = max(11, int(r * 0.58))
        self.canvas_full.create_text(cx, cy, text=countdown_str, 
                                     font=("Consolas", font_sz, "bold"), fill="#ffffff")

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
            self.full_w = getattr(self, 'v2_w', 460)
            self.full_h = getattr(self, 'v2_h', 355)
            self.is_compact_folded = True
        else:
            # อยู่โหมดแนวนอน V.2 -> จำขนาด V.2 ล่าสุดไว้ แล้วสลับเป็น Vertical Sidebar
            self.v2_w = cur_w
            self.v2_h = cur_h
            self.full_w = max(160, getattr(self, 'sidebar_w', 210))
            self.full_h = max(520, getattr(self, 'sidebar_h', 535))
            self.is_compact_folded = True

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
                sure_prefix = "[แน่นอน] "
                extra_prefix = "[+1] "
                rate_prefix = "📊 "
            else:
                unit_neso = " NESO"
                sure_prefix = "[ดรอปแน่นอน] "
                extra_prefix = "[+1] "
                rate_prefix = "📊 ดรอป:"
        elif w >= 450:
            f_main_lbl = ("Segoe UI", 9, "bold")
            f_main_val = ("Consolas", 10, "bold")
            f_sub_lbl = ("Segoe UI", 7)
            f_sub_val = ("Consolas", 7, "bold")
            unit_neso = " NESO"
            sure_prefix = "[ดรอปแน่นอน] "
            extra_prefix = "[+1 ดรอป] "
            rate_prefix = "📊 อัตราดรอป:"
        elif w >= 390:
            f_main_lbl = ("Segoe UI", 8, "bold")
            f_main_val = ("Consolas", 9, "bold")
            f_sub_lbl = ("Segoe UI", 7)
            f_sub_val = ("Consolas", 7, "bold")
            unit_neso = " NESO"
            sure_prefix = "[ดรอปแน่นอน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 ดรอป:"
        elif w <= 240: # แคบพิเศษแบบแถบข้าง Vertical HUD
            f_main_lbl = ("Segoe UI", 7, "bold")
            f_main_val = ("Consolas", 7, "bold")
            f_sub_lbl = ("Segoe UI", 6)
            f_sub_val = ("Consolas", 6, "bold")
            unit_neso = " N"
            sure_prefix = "[แน่นอน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 "
        else: # แคบปานกลาง (< 390)
            f_main_lbl = ("Segoe UI", 7, "bold")
            f_main_val = ("Consolas", 8, "bold")
            f_sub_lbl = ("Segoe UI", 6)
            f_sub_val = ("Consolas", 6, "bold")
            unit_neso = " N"
            sure_prefix = "[แน่นอน] "
            extra_prefix = "[+1] "
            rate_prefix = "📊 ดรอป:"

        # คำนวณความกว้างสูงสุดสำหรับตัดบรรทัดแยกตามหมวด (Category-isolated auto-wrap)
        content_w = max(100, w - 24)

        # -------------------------------------------------------------
        # 🔴 ปรับขนาด Font กรอบสีแดงด้านบนตาม custom_font_size และความกว้างหน้าต่าง
        # -------------------------------------------------------------
        if c_fs and c_fs > 0:
            timer_sz = max(10, c_fs + 2)
            wal_sz = max(5, c_fs - 3)
            badge_sz = max(5, c_fs - 3)
        elif w <= 240:
            timer_sz = 13
            wal_sz = 6
            badge_sz = 7
        else:
            timer_sz = 15
            wal_sz = 7
            badge_sz = 7

        if hasattr(self, 'lbl_timer_text') and self.lbl_timer_text.winfo_exists():
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
        # 🟢 หมวด 1: อัปเดต Font และข้อความ Label แถว 1 (⚡ คาดหวัง)
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_exp_t') and self.lbl_exp_t.winfo_exists():
            self.lbl_exp_t.config(font=f_main_lbl)
        if hasattr(self, 'lbl_boost_expected') and self.lbl_boost_expected.winfo_exists():
            self.lbl_boost_expected.config(font=f_main_val, wraplength=content_w)
            if hasattr(self, 'neso_boost_total_min') and getattr(self, 'neso_boost_total_max', 0) > 0:
                self.lbl_boost_expected.config(text=f"{self.neso_boost_total_min:.2f} ~ {self.neso_boost_total_max:.2f}{unit_neso}")

        # Dynamic Line-Wrap สำหรับแถว 1: ถ้าจอแคบ (<= 240) หรือฟอนต์ใหญ่ (>= 10) ให้แยกเป็น 2 บรรทัด
        if hasattr(self, 'lbl_exp_t') and hasattr(self, 'lbl_boost_expected'):
            if self.lbl_exp_t.winfo_exists() and self.lbl_boost_expected.winfo_exists():
                if w <= 240 or (c_fs and c_fs >= 10):
                    self.lbl_exp_t.pack_configure(side=tk.TOP, anchor="w")
                    self.lbl_boost_expected.pack_configure(side=tk.TOP, anchor="w", padx=(6, 0))
                else:
                    self.lbl_exp_t.pack_configure(side=tk.LEFT, anchor="w")
                    self.lbl_boost_expected.pack_configure(side=tk.LEFT, anchor="w", padx=(4, 0))

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
                    self.f_sure_part1.pack_configure(side=tk.TOP, anchor="w")
                    self.f_sure_part2.pack_configure(side=tk.TOP, anchor="w", pady=(1, 0))
                    if hasattr(self, 'lbl_sure_p') and self.lbl_sure_p.winfo_exists():
                        self.lbl_sure_p.config(text="+ ")
                else:
                    self.f_sure_part1.pack_configure(side=tk.LEFT, anchor="w")
                    self.f_sure_part2.pack_configure(side=tk.LEFT, anchor="w", pady=(0, 0))
                    if hasattr(self, 'lbl_sure_p') and self.lbl_sure_p.winfo_exists():
                        self.lbl_sure_p.config(text=" + ")

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
                    self.f_rate_part1.pack_configure(side=tk.TOP, anchor="w")
                    self.f_rate_part2.pack_configure(side=tk.TOP, anchor="w", padx=(6, 0))
                else:
                    self.f_rate_part1.pack_configure(side=tk.LEFT, anchor="w")
                    self.f_rate_part2.pack_configure(side=tk.LEFT, anchor="w", padx=(2, 0))

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
                    self.f_stk_part1.pack_configure(side=tk.TOP, anchor="w")
                    self.f_stk_part2.pack_configure(side=tk.TOP, anchor="w", padx=(6, 0))
                else:
                    self.f_stk_part1.pack_configure(side=tk.LEFT, anchor="w")
                    self.f_stk_part2.pack_configure(side=tk.LEFT, anchor="w", padx=(2, 0))

        # -------------------------------------------------------------
        # 🟢 แถบ Hot Farm Recommender: ตัดบรรทัดและปรับฟอนต์ให้สมส่วน
        # -------------------------------------------------------------
        if hasattr(self, 'lbl_hot_map') and self.lbl_hot_map.winfo_exists():
            self.lbl_hot_map.config(font=f_sub_lbl, wraplength=max(70, w - 60))
        if hasattr(self, 'lbl_hot_rate') and self.lbl_hot_rate.winfo_exists():
            self.lbl_hot_rate.config(font=f_sub_val)

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
            fold_h = max(520, getattr(self, 'sidebar_h', 535)) if cur_w <= 240 else getattr(self, 'v2_h', 275)
            geom = f"{cur_w}x{fold_h}+{self.pos_x}+{self.pos_y}"
            self.win_bg.geometry(geom)
            self.win_fg.geometry(geom)
        else:
            # กางกลับมาครบทุกส่วน
            if hasattr(self, 'f_red_box') and self.f_red_box.winfo_exists():
                self.f_red_box.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=(1, 3))
            if hasattr(self, 'btn_fold_toggle') and self.btn_fold_toggle.winfo_exists():
                self.btn_fold_toggle.config(text="▼ พับเก็บแถบล่าง", bg="#161c28", fg="#64748b")
            full_h = max(580, getattr(self, 'sidebar_h', 535) + 60) if cur_w <= 240 else getattr(self, 'full_h', 355)
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
        self.root.destroy()
        os._exit(0)

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
        
        sizes = [("📱 แถบซ้าย", 170, 380), ("S เล็ก", 245, 385), ("M กลาง", 265, 410), ("L ใหญ่", 460, 355)]
        for label, sw, sh in sizes:
            btn_sz = tk.Label(sz_box, text=label, font=("Segoe UI", 7, "bold"), bg="#1e293b", fg="#e2e8f0", cursor="hand2", padx=6, pady=2)
            btn_sz.pack(side=tk.LEFT, padx=2)
            btn_sz.bind("<Button-1>", lambda e, w=sw, h=sh: [setattr(self, 'is_compact_folded', (w <= 240)), self.set_preset_size(w, h)])

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
            # 🔵 โหมดเต็ม FULL OVERLAY
            # =========================================================
            is_vert = (getattr(self, 'full_w', 170) <= 240)
            btn_w = 1 if is_vert else 2
            btn_padx = 0 if is_vert else 1

            # 1. แถบ Title Bar ด้านบนสุด
            top_bar = tk.Frame(self.main_container, bg="#121824", height=24)
            top_bar.pack(fill=tk.X, side=tk.TOP)
            top_bar.bind("<ButtonPress-1>", self.start_drag)
            top_bar.bind("<B1-Motion>", self.do_drag)
            top_bar.bind("<ButtonRelease-1>", self.end_drag)

            # ปุ่มชิดขวา (pack side=tk.RIGHT ก่อนตามกฎเหล็ก)
            btn_close = tk.Label(top_bar, text="✕", font=("Segoe UI", 9, "bold"), fg="#ff4d4f", bg="#121824", cursor="hand2", width=btn_w)
            btn_close.pack(side=tk.RIGHT, padx=btn_padx)
            btn_close.bind("<Button-1>", lambda e: self.close_app())

            btn_mini = tk.Label(top_bar, text="—", font=("Segoe UI", 9, "bold"), fg="#00f2fe", bg="#121824", cursor="hand2", width=btn_w)
            btn_mini.pack(side=tk.RIGHT, padx=btn_padx)
            btn_mini.bind("<Button-1>", lambda e: self.toggle_compact_fold())

            btn_cfg = tk.Label(top_bar, text="⚙", font=("Segoe UI", 9), fg="#94a3b8", bg="#121824", cursor="hand2", width=btn_w)
            btn_cfg.pack(side=tk.RIGHT, padx=btn_padx)
            btn_cfg.bind("<Button-1>", lambda e: self.open_settings())

            btn_alpha = tk.Label(top_bar, text="🌓", font=("Segoe UI", 9), fg="#38bdf8", bg="#121824", cursor="hand2", width=btn_w)
            btn_alpha.pack(side=tk.RIGHT, padx=btn_padx)
            btn_alpha.bind("<Button-1>", lambda e: self.cycle_opacity())
            btn_alpha.bind("<Enter>", lambda e: btn_alpha.config(fg="#ffffff"))
            btn_alpha.bind("<Leave>", lambda e: btn_alpha.config(fg="#38bdf8"))

            # ฝั่งซ้ายของ Title Bar: ปุ่มสลับโหมด V.2 <-> Vertical Sidebar (ออกแบบให้เป็นปุ่มกดชัดเจน มีกรอบและสีสันเด่น)
            title_text = "⇋ โหมด" if is_vert else "⇋ แถบข้าง"
            lbl_title = tk.Label(top_bar, text=title_text, font=("Segoe UI", 7, "bold"),
                                 fg="#00f2fe", bg="#16202c", relief="solid", bd=1,
                                 highlightbackground="#0284c7", highlightthickness=1,
                                 cursor="hand2", padx=4, pady=1)
            lbl_title.pack(side=tk.LEFT, padx=(3 if is_vert else 5, 2))
            lbl_title.bind("<Button-1>", lambda e: self.toggle_vertical_hud_mode())
            lbl_title.bind("<Enter>", lambda e: lbl_title.config(bg="#0284c7", fg="#ffffff"))
            lbl_title.bind("<Leave>", lambda e: lbl_title.config(bg="#16202c", fg="#00f2fe"))
            self.lbl_title = lbl_title

            srv_text = f"[{self.server_name[:1]}▾]" if is_vert else f"[{self.server_name}▾]"
            btn_srv_f = tk.Label(top_bar, text=srv_text, font=("Consolas", 8, "bold"), fg="#f59e0b", bg="#121824", cursor="hand2")
            btn_srv_f.pack(side=tk.LEFT, padx=1)
            btn_srv_f.bind("<Button-1>", lambda e, w=btn_srv_f: self.show_server_dropdown(w))

            mode_tag_f = ("ST" if self.mode == "ServerTime" else "MN") if is_vert else ("ServerTime" if self.mode == "ServerTime" else "Manual")
            lbl_m_f = tk.Label(top_bar, text=f"[{mode_tag_f}▾]", font=("Consolas", 8, "bold"), 
                               fg="#38ef7d" if self.mode == "ServerTime" else "#f59e0b", bg="#121824", cursor="hand2")
            lbl_m_f.pack(side=tk.LEFT, padx=1)
            lbl_m_f.bind("<Button-1>", lambda e, w=lbl_m_f: self.show_mode_dropdown(w))

            # 2. แถบ Map Banner ใต้ Title Bar (โปร่งใส + StrokeLabel คมชัด สไตล์ Game HUD)
            f_banner = tk.Frame(self.main_container, bg=self.trans_key, bd=0, cursor="hand2")
            f_banner.pack(side=tk.TOP, fill=tk.X, padx=4 if is_vert else 6, pady=(2 if is_vert else 3, 1))
            f_banner.bind("<Button-1>", lambda e: self.open_map_picker())

            # ปุ่มเลือกแมพชิดขวา (pack ก่อนฝั่งซ้ายตามกฎเหล็ก!)
            arr_txt = "▾" if is_vert else "เลือกแมพ ▾ "
            lbl_arr = StrokeLabel(f_banner, text=arr_txt, font=("Segoe UI", 7, "bold"),
                                  fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="e", cursor="hand2")
            lbl_arr.pack(side=tk.RIGHT, padx=2 if is_vert else 4)
            lbl_arr.bind("<Button-1>", lambda e: self.open_map_picker())
            self.lbl_arr = lbl_arr

            self.lbl_map_icon = tk.Label(f_banner, bg=self.trans_key, cursor="hand2")
            self.lbl_map_icon.pack(side=tk.LEFT, padx=(2, 2) if is_vert else (4, 2))
            self.lbl_map_icon.bind("<Button-1>", lambda e: self.open_map_picker())

            f_map_txts = tk.Frame(f_banner, bg=self.trans_key, cursor="hand2")
            f_map_txts.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=1)
            f_map_txts.bind("<Button-1>", lambda e: self.open_map_picker())

            # ใช้ค่าปัจจุบันแทน placeholder เพื่อป้องกัน UI กระพริบ
            _cur_main = self.selected_layer_name if self.selected_layer_name else "รอตรวจจับแมพ..."
            _cur_sub = f"📍 {self.detected_submap_name}" if getattr(self, 'detected_submap_name', '') else "📍 กด Scan Map หรือเลือกแมพ"
            wrap_len = 105 if is_vert else 0
            self.lbl_map_main = StrokeLabel(f_map_txts, text=_cur_main, font=("Segoe UI", 8, "bold"),
                                            fg="#e2e8f0", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="w", cursor="hand2", wraplength=wrap_len)
            self.lbl_map_main.pack(fill=tk.X)
            self.lbl_map_main.bind("<Button-1>", lambda e: self.open_map_picker())

            self.lbl_map_sub = StrokeLabel(f_map_txts, text=_cur_sub, font=("Segoe UI", 7),
                                           fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="w", cursor="hand2", wraplength=wrap_len)
            self.lbl_map_sub.pack(fill=tk.X)
            self.lbl_map_sub.bind("<Button-1>", lambda e: self.open_map_picker())

            self.btn_map = self.lbl_map_main

            # ---------------------------------------------------------
            # 🎯 กรอบ Pool Zone (เส้นขอบสีเหลืองตามผู้ใช้สั่ง)
            # ---------------------------------------------------------
            f_pool_zone = tk.Frame(self.main_container, bg=self.trans_key, bd=1, highlightbackground="#f59e0b", highlightthickness=1)
            f_pool_zone.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=(2, 4))
            f_pool_zone.bind("<ButtonPress-1>", self.start_drag)
            f_pool_zone.bind("<B1-Motion>", self.do_drag)
            f_pool_zone.bind("<ButtonRelease-1>", self.end_drag)

            # 1. Left / Top: Timer Zone
            if is_vert:
                f_timer_zone = tk.Frame(f_pool_zone, bg=self.trans_key, bd=0)
                f_timer_zone.pack(side=tk.TOP, fill=tk.X, padx=1, pady=(0, 1))
            else:
                f_timer_zone = tk.Frame(f_pool_zone, bg=self.trans_key, bd=0, width=108)
                f_timer_zone.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2), pady=0)
                f_timer_zone.pack_propagate(False)
            f_timer_zone.bind("<ButtonPress-1>", self.start_drag)
            f_timer_zone.bind("<B1-Motion>", self.do_drag)
            f_timer_zone.bind("<ButtonRelease-1>", self.end_drag)

            lbl_t_header = StrokeLabel(f_timer_zone, text="⏱️ 20m Cycle", font=("Segoe UI", 6 if is_vert else 7, "bold"),
                                       fg="#94a3b8", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="center")
            lbl_t_header.pack(pady=(1, 0) if is_vert else (2, 1))
            lbl_t_header.bind("<ButtonPress-1>", self.start_drag)
            lbl_t_header.bind("<B1-Motion>", self.do_drag)
            lbl_t_header.bind("<ButtonRelease-1>", self.end_drag)

            f_timer_box = tk.Frame(f_timer_zone, bg=self.trans_key, bd=0)
            f_timer_box.pack(fill=tk.X, padx=3 if is_vert else 5, pady=(0, 1) if is_vert else (0, 2))
            f_timer_box.bind("<ButtonPress-1>", self.start_drag)
            f_timer_box.bind("<B1-Motion>", self.do_drag)
            f_timer_box.bind("<ButtonRelease-1>", self.end_drag)

            timer_f_sz = 13 if is_vert else 15
            self.lbl_timer_text = StrokeLabel(f_timer_box, text="00:00", font=("Consolas", timer_f_sz, "bold"),
                                              fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=2, anchor="center")
            self.lbl_timer_text.pack(pady=0 if is_vert else 1)
            self.lbl_timer_text.bind("<ButtonPress-1>", self.start_drag)
            self.lbl_timer_text.bind("<B1-Motion>", self.do_drag)
            self.lbl_timer_text.bind("<ButtonRelease-1>", self.end_drag)

            # 🗺️ ปุ่มควบคุมแถวคู่: Scan Map และ Character OCR
            f_timer_btns = tk.Frame(f_timer_zone, bg=self.trans_key)
            f_timer_btns.pack(pady=(1, 1) if is_vert else (1, 2), padx=2 if is_vert else 3, fill=tk.X)

            self.btn_timer_scan = tk.Label(f_timer_btns, text="🔍 Map", font=("Segoe UI", 7, "bold"),
                                           fg="#38bdf8", bg="#16202c", relief="solid", bd=1, cursor="hand2", padx=2, pady=1)
            self.btn_timer_scan.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
            self.btn_timer_scan.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

            self.btn_char_ocr = tk.Label(f_timer_btns, text="👤 Char", font=("Segoe UI", 7, "bold"),
                                         fg="#a855f7", bg="#1e1b2e", relief="solid", bd=1, cursor="hand2", padx=2, pady=1)
            self.btn_char_ocr.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self.btn_char_ocr.bind("<Button-1>", lambda e: self.open_char_crop_tool())

            # Canvas เส้นเวลา
            tb_h = 3 if is_vert else 6
            self.canvas_timer_bar = tk.Canvas(f_timer_zone, bg="#050a12", height=tb_h, highlightthickness=0)
            self.canvas_timer_bar.pack(fill=tk.X, padx=3 if is_vert else 4, pady=(1, 1) if is_vert else (1, 3))
            self.canvas_timer_bar.bind("<ButtonPress-1>", self.start_drag)
            self.canvas_timer_bar.bind("<B1-Motion>", self.do_drag)
            self.canvas_timer_bar.bind("<ButtonRelease-1>", self.end_drag)

            # 💰 กล่องคู่กระเป๋า NESO & Nesolet วางใต้เส้นเวลาใน Timer Zone
            f_wal_container = tk.Frame(f_timer_zone, bg="#08101a")
            f_wal_container.pack(side=tk.TOP, fill=tk.X, padx=1 if is_vert else 2, pady=(1, 1) if is_vert else (2, 2))

            # กล่องกระเป๋า NESO (คลิกเปิด Modal ได้)
            f_wal_neso = tk.Frame(f_wal_container, bg="#1a1c29", bd=1, relief="solid", cursor="hand2")
            f_wal_neso.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 1))
            f_wal_neso.bind("<Button-1>", lambda e: self.open_wallet_inapp_modal())

            self.lbl_wallet_neso_val = tk.Label(f_wal_neso, text="...\nNESO", font=("Consolas", 6 if is_vert else 7, "bold"), fg="#c084fc", bg="#1a1c29", justify="center", padx=1 if is_vert else 2, pady=1 if is_vert else 2)
            self.lbl_wallet_neso_val.pack(anchor="center")
            self.lbl_wallet_neso_val.bind("<Button-1>", lambda e: self.open_wallet_inapp_modal())

            # กล่อง Nesolet
            f_wal_nesolet = tk.Frame(f_wal_container, bg="#231433", bd=1, relief="solid")
            f_wal_nesolet.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(1, 0))

            self.lbl_nesolet = tk.Label(f_wal_nesolet, text="...\nNesolet", font=("Consolas", 6 if is_vert else 7, "bold"), fg="#d8b4fe", bg="#231433", justify="center", padx=1 if is_vert else 2, pady=1 if is_vert else 2)
            self.lbl_nesolet.pack(anchor="center")

            # 🪙 กล่องเหรียญ NESO 2 กล่องมาเรียงคู่กันใต้ตัวจับเวลา (ตามรูปกรอบสีน้ำตาลในแถบเขียวทึบ)
            f_timer_badges = tk.Frame(f_timer_zone, bg="#08101a")
            f_timer_badges.pack(side=tk.TOP if is_vert else tk.BOTTOM, fill=tk.X, padx=1 if is_vert else 3, pady=(1, 1) if is_vert else (0, 3))
            f_timer_badges.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            coin_img = self.get_neso_coin_photo(size=18)

            # กล่อง 1: Normal Pool Badge
            c_norm_badge = tk.Frame(f_timer_badges, bg="#081d3d", bd=1, relief="solid",
                                    highlightbackground="#0084ff", highlightthickness=1, cursor="hand2")
            c_norm_badge.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
            c_norm_badge.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            if coin_img:
                lbl_cn_icon = tk.Label(c_norm_badge, image=coin_img, bg="#081d3d")
                lbl_cn_icon.image = coin_img
                lbl_cn_icon.pack(padx=2, pady=(1, 0))
                lbl_cn_icon.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            else:
                lbl_cn_icon = tk.Label(c_norm_badge, text="🪙", font=("Segoe UI", 9), bg="#081d3d")
                lbl_cn_icon.pack(padx=2, pady=(1, 0))
                lbl_cn_icon.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            _init_norm_stk = self.format_compact_number(getattr(self, 'neso_normal_stock_f', 0.0))
            self.lbl_neso_badge_norm_stock = tk.Label(c_norm_badge, text=f"{_init_norm_stk}", font=("Consolas", 7, "bold"), fg="#bbf246", bg="#081d3d")
            self.lbl_neso_badge_norm_stock.pack(padx=2, pady=(0, 1))
            self.lbl_neso_badge_norm_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # กล่อง 2: Boost Pool Badge
            c_boost_badge = tk.Frame(f_timer_badges, bg="#081d3d", bd=1, relief="solid",
                                     highlightbackground="#0084ff", highlightthickness=1, cursor="hand2")
            c_boost_badge.pack(side=tk.LEFT, expand=True, fill=tk.X)
            c_boost_badge.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            if coin_img:
                lbl_cb_icon = tk.Label(c_boost_badge, image=coin_img, bg="#081d3d")
                lbl_cb_icon.image = coin_img
                lbl_cb_icon.pack(padx=2, pady=(1, 0))
                lbl_cb_icon.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            else:
                lbl_cb_icon = tk.Label(c_boost_badge, text="🪙", font=("Segoe UI", 9), bg="#081d3d")
                lbl_cb_icon.pack(padx=2, pady=(1, 0))
                lbl_cb_icon.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            _init_boost_stk = getattr(self, 'neso_boost_stock', '--')
            self.lbl_neso_badge_stock = tk.Label(c_boost_badge, text=f"{_init_boost_stk}", font=("Consolas", 7, "bold"), fg="#bbf246", bg="#081d3d")
            self.lbl_neso_badge_stock.pack(padx=2, pady=(0, 1))
            self.lbl_neso_badge_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # 2. Boost Pool Container (Expanded & Rich Display)
            c_boost_container = tk.Frame(f_pool_zone, bg=self.trans_key)
            if is_vert:
                c_boost_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(2, 0))
            else:
                c_boost_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Top Green: แถบหัวข้อย้าย % รวมมาไว้ตรงกลาง
            c_boost_top = tk.Frame(c_boost_container, bg="#14532d", bd=1, relief="solid", 
                                   highlightbackground="#22c55e", highlightthickness=1, cursor="hand2")
            c_boost_top.pack(side=tk.TOP, fill=tk.X, pady=(0, 1))
            c_boost_top.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            lbl_flame = tk.Label(c_boost_top, text="💧 BOOST DROP!", font=("Segoe UI", 7, "bold"), fg="#38bdf8", bg="#14532d")
            lbl_flame.pack(side=tk.LEFT, padx=4, pady=2)
            lbl_flame.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_flame = lbl_flame

            self.lbl_boost_hdr_mult = tk.Label(c_boost_top, text="", font=("Consolas", 8, "bold"), fg="#86efac", bg="#14532d")
            self.lbl_boost_hdr_mult.pack(side=tk.RIGHT, padx=4, pady=2)
            self.lbl_boost_hdr_mult.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # % Boost รวม จัดกึ่งกลางแนวนอนและแนวตั้งเป๊ะๆ
            self.lbl_neso_boost_val = tk.Label(c_boost_top, text="รอข้อมูล", font=("Consolas", 10, "bold"), fg="#4ade80", bg="#14532d")
            self.lbl_neso_boost_val.place(relx=0.5, rely=0.5, anchor="center")
            self.lbl_neso_boost_val.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # Bottom: กล่องแสดงข้อมูล Boost + พื้นที่ว่างล่าง (Hot Farm Recommender + Mini CMD Box)
            c_boost_bot = tk.Frame(c_boost_container, bg=self.trans_key, bd=0, cursor="hand2")
            c_boost_bot.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
            c_boost_bot.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ---------------------------------------------------------
            # 1. ชั้นบน: ข้อมูล Boost 4 แถว (โปร่งใส + StrokeLabel คมชัด สไตล์ Game HUD)
            # ---------------------------------------------------------
            f_boost_info_left = tk.Frame(c_boost_bot, bg=self.trans_key, bd=0)
            f_boost_info_left.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(2, 2))
            f_boost_info_left.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_boost_info_left = f_boost_info_left

            # 🛡️ แผ่นป้าย Safe Zone (ร.1) แสดงแทนเมื่ออยู่ในเมืองหรือแมพไม่มีดรอป
            f_safe_zone_banner = tk.Frame(c_boost_bot, bg="#06090e", cursor="hand2")
            f_safe_zone_banner.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_safe_zone_banner = f_safe_zone_banner

            # การ์ดป้ายสี่เหลี่ยมสีขาว Safe Zone เด่นตรงกลาง (ตามรูป ร.1 ของผู้ใช้ สไตล์โมเดิร์นคลีน)
            f_sz_card = tk.Frame(f_safe_zone_banner, bg="#ffffff", bd=1, relief="solid",
                                 highlightbackground="#94a3b8", highlightthickness=1)
            f_sz_card.pack(expand=True, padx=4 if is_vert else 16, pady=(4 if is_vert else 8, 2 if is_vert else 3))
            f_sz_card.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            sz_title_f = ("Segoe UI", 10, "bold") if is_vert else ("Segoe UI", 13, "bold")
            self.lbl_sz_title = tk.Label(f_sz_card, text="Safe Zone", font=sz_title_f,
                                         fg="#0f172a", bg="#ffffff", padx=10 if is_vert else 26, pady=3 if is_vert else 5)
            self.lbl_sz_title.pack()
            self.lbl_sz_title.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ซับไตเติลและชื่อเมืองใต้ป้าย
            self.lbl_sz_desc = tk.Label(f_safe_zone_banner, text="[ จุดพักผ่อน • ปลอดภัยจากมอนสเตอร์ ]",
                                        font=("Segoe UI", 7), fg="#64748b", bg="#06090e")
            self.lbl_sz_desc.pack(pady=(0, 2))
            self.lbl_sz_desc.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            self.lbl_sz_town = tk.Label(f_safe_zone_banner, text="🏙️ จุดปลอดภัย",
                                        font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#06090e")
            self.lbl_sz_town.pack(pady=(0, 5))
            self.lbl_sz_town.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # แถว 1: ⚡ คาดว่าจะได้รับ: X ~ Y NESO (รองรับแยก 2 บรรทัดเมื่อจอแคบหรือฟอนต์ใหญ่)
            f_row_exp = tk.Frame(f_boost_info_left, bg=self.trans_key)
            f_row_exp.pack(fill=tk.X, padx=3 if is_vert else 5, pady=(1 if is_vert else 2, 1), anchor="w")
            f_row_exp.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_row_exp = f_row_exp

            exp_txt = "⚡ คาดหวัง:" if is_vert else "⚡ คาดว่าจะได้รับ:"
            exp_font = ("Segoe UI", 7, "bold") if is_vert else ("Segoe UI", 9, "bold")
            lbl_exp_t = StrokeLabel(f_row_exp, text=exp_txt, font=exp_font,
                                    fg="#fbbf24", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_exp_t.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w")
            lbl_exp_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_exp_t = lbl_exp_t

            val_font = ("Consolas", 7, "bold") if is_vert else ("Consolas", 10, "bold")
            self.lbl_boost_expected = StrokeLabel(f_row_exp, text=" --", font=val_font,
                                                  fg="#facc15", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_boost_expected.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w", padx=(6 if is_vert else 0, 0))
            self.lbl_boost_expected.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # แถว 2: Container รวมข้อมูลแน่นอน และ +1 ดรอป (รองรับตัดบรรทัดอัตโนมัติเมื่อโดนบีบแคบ)
            f_row_sure = tk.Frame(f_boost_info_left, bg=self.trans_key)
            f_row_sure.pack(fill=tk.X, padx=3 if is_vert else 5, pady=(1, 1), anchor="w")
            f_row_sure.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_row_sure = f_row_sure

            # ส่วนที่ 1: ดรอปแน่นอน
            f_sure_part1 = tk.Frame(f_row_sure, bg=self.trans_key)
            f_sure_part1.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w")
            f_sure_part1.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_sure_part1 = f_sure_part1

            sure_txt = "[แน่นอน] " if is_vert else "[ดรอปแน่นอน] "
            lbl_sure_t = StrokeLabel(f_sure_part1, text=sure_txt, font=exp_font,
                                     fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_sure_t.pack(side=tk.LEFT)
            lbl_sure_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_sure_t = lbl_sure_t

            self.lbl_boost_sure_val = StrokeLabel(f_sure_part1, text="--", font=val_font,
                                                  fg="#ffffff", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_boost_sure_val.pack(side=tk.LEFT)
            self.lbl_boost_sure_val.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ส่วนที่ 2: +1 ดรอป
            f_sure_part2 = tk.Frame(f_row_sure, bg=self.trans_key)
            f_sure_part2.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w", pady=(1, 0) if is_vert else (0, 0))
            f_sure_part2.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_sure_part2 = f_sure_part2

            plus_txt = "+ " if is_vert else " + "
            lbl_sure_p = StrokeLabel(f_sure_part2, text=plus_txt, font=exp_font,
                                     fg="#94a3b8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_sure_p.pack(side=tk.LEFT)
            lbl_sure_p.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_sure_p = lbl_sure_p

            extra_txt = "[+1] " if is_vert else "[+1 ดรอป] "
            lbl_extra_t = StrokeLabel(f_sure_part2, text=extra_txt, font=exp_font,
                                      fg="#4ade80", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_extra_t.pack(side=tk.LEFT)
            lbl_extra_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_extra_t = lbl_extra_t

            self.lbl_boost_sure_rate = StrokeLabel(f_sure_part2, text="--", font=val_font,
                                                   fg="#4ade80", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_boost_sure_rate.pack(side=tk.LEFT)
            self.lbl_boost_sure_rate.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # แถว 3: 📊 อัตราดรอป: 169.15% (50% + 119.15%)
            f_row_rate = tk.Frame(f_boost_info_left, bg=self.trans_key)
            f_row_rate.pack(fill=tk.X, padx=3 if is_vert else 5, pady=(1, 1), anchor="w")
            f_row_rate.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_row_rate = f_row_rate

            f_rate_part1 = tk.Frame(f_row_rate, bg=self.trans_key)
            f_rate_part1.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w")
            self.f_rate_part1 = f_rate_part1

            rate_lbl_txt = "📊 " if is_vert else "📊 อัตราดรอป:"
            lbl_rate_t = StrokeLabel(f_rate_part1, text=rate_lbl_txt, font=("Segoe UI", 6 if is_vert else 7),
                                     fg="#94a3b8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_rate_t.pack(side=tk.LEFT)
            lbl_rate_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_rate_t = lbl_rate_t

            self.lbl_boost_rate_total = StrokeLabel(f_rate_part1, text=" --%", font=("Consolas", 6 if is_vert else 7, "bold"),
                                                    fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_boost_rate_total.pack(side=tk.LEFT)
            self.lbl_boost_rate_total.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            f_rate_part2 = tk.Frame(f_row_rate, bg=self.trans_key)
            f_rate_part2.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w", padx=(6 if is_vert else 0, 0))
            self.f_rate_part2 = f_rate_part2

            self.lbl_boost_rate_breakdown = StrokeLabel(f_rate_part2, text=" (--% + --%)", font=("Consolas", 6 if is_vert else 7),
                                                        fg="#fb923c", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_boost_rate_breakdown.pack(side=tk.LEFT)
            self.lbl_boost_rate_breakdown.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # แถว 4: 📦 เหลือ: X NESO  |  ชาร์จ/รอบ: Y
            f_row_stk = tk.Frame(f_boost_info_left, bg=self.trans_key)
            f_row_stk.pack(fill=tk.X, padx=3 if is_vert else 5, pady=(1, 1), anchor="w")
            f_row_stk.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.f_row_stk = f_row_stk

            f_stk_part1 = tk.Frame(f_row_stk, bg=self.trans_key)
            f_stk_part1.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w")
            self.f_stk_part1 = f_stk_part1

            stk_lbl_txt = "📦 " if is_vert else "📦 เหลือ:"
            lbl_stk_t = StrokeLabel(f_stk_part1, text=stk_lbl_txt, font=("Segoe UI", 6 if is_vert else 7),
                                    fg="#94a3b8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_stk_t.pack(side=tk.LEFT)
            lbl_stk_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_stk_t = lbl_stk_t

            self.lbl_neso_boost_stock = StrokeLabel(f_stk_part1, text=" --- NESO", font=("Consolas", 6 if is_vert else 7, "bold"),
                                                    fg="#38ef7d", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_neso_boost_stock.pack(side=tk.LEFT)
            self.lbl_neso_boost_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            f_stk_part2 = tk.Frame(f_row_stk, bg=self.trans_key)
            f_stk_part2.pack(side=tk.TOP if is_vert else tk.LEFT, anchor="w", padx=(6 if is_vert else 0, 0))
            self.f_stk_part2 = f_stk_part2

            lbl_chg_t = StrokeLabel(f_stk_part2, text=" | +", font=("Segoe UI", 6 if is_vert else 7),
                                    fg="#64748b", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            lbl_chg_t.pack(side=tk.LEFT)
            lbl_chg_t.bind("<Button-1>", lambda e: self.fetch_drop_data_async())
            self.lbl_chg_t = lbl_chg_t

            self.lbl_neso_boost_charge = StrokeLabel(f_stk_part2, text="---", font=("Consolas", 6 if is_vert else 7, "bold"),
                                                     fg="#38bdf8", bg=self.trans_key, stroke_color="#000000", stroke_width=1)
            self.lbl_neso_boost_charge.pack(side=tk.LEFT)
            self.lbl_neso_boost_charge.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ---------------------------------------------------------
            # 2. พื้นที่ว่างขวาล่าง: แถบแนะนำแมพในโซน (แสดงผลอย่างเดียว) + กล่อง Mini CMD Box + Grip
            # (pack ชิดขอบล่างของ c_boost_bot เสมอ ป้องกันการตกขอบหรือหลุดหาย)
            # ---------------------------------------------------------
            f_bot_action = tk.Frame(c_boost_bot, bg=self.trans_key)
            f_bot_action.pack(side=tk.BOTTOM, fill=tk.X, padx=3 if is_vert else 5, pady=(1, 2))
            self.f_bot_action = f_bot_action

            # แถวบน: แถบแนะนำแมพในโซนที่ % สูงสุด (โปร่งใสตามคำสั่งผู้ใช้ + StrokeLabel คมชัด สไตล์ Game HUD)
            f_hot_farm = tk.Frame(f_bot_action, bg=self.trans_key, bd=0)
            f_hot_farm.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
            self.f_hot_farm = f_hot_farm

            self.lbl_hot_map = StrokeLabel(f_hot_farm, text="🔥 แนะนำในโซน...", font=("Segoe UI", 7, "bold"),
                                           fg="#fde047", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="w")
            self.lbl_hot_map.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=1)

            self.lbl_hot_rate = StrokeLabel(f_hot_farm, text="--%", font=("Consolas", 8, "bold"),
                                            fg="#4ade80", bg=self.trans_key, stroke_color="#000000", stroke_width=1, anchor="e")
            self.lbl_hot_rate.pack(side=tk.RIGHT, padx=2, pady=1)

            # Mini CMD Terminal Box แสดงการตรวจจับ OCR / ระบบ Real-time (กรอบเส้นหน้าต่างตามสั่ง + StrokeLabel)
            f_cmd_box = tk.Frame(f_bot_action, bg="#08101a", bd=1, relief="solid",
                                 highlightbackground="#1e293b", highlightthickness=1)
            f_cmd_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(1, 0))
            self.f_cmd_box = f_cmd_box

            # Grip ปรับขนาดมุมขวาล่างของกรอบ Pool (กรอบสีแดงขาว ล่าง ขวา ตามคำสั่งผู้ใช้!)
            self.grip_pool = tk.Label(f_cmd_box, text=" ◢ ", font=("Segoe UI", 8, "bold"),
                                      fg="#ffffff", bg="#dc2626", relief="solid", bd=1,
                                      highlightbackground="#ffffff", highlightthickness=1,
                                      cursor="size_nw_se", padx=2, pady=0)
            self.grip_pool.pack(side=tk.RIGHT, anchor="se")
            self.grip_pool.bind("<ButtonPress-1>", self.start_resize)
            self.grip_pool.bind("<B1-Motion>", self.do_resize)
            self.grip_pool.bind("<ButtonRelease-1>", self.end_resize)

            self.txt_cmd = StrokeLabel(f_cmd_box, text=">_ พร้อมทำงาน...", font=("Consolas", 6),
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

            # ---------------------------------------------------------
            # 🔴 กรอบแดงด้านล่างสุด (รวมส่วนอื่นๆ)
            # ---------------------------------------------------------
            f_red_box = tk.Frame(self.main_container, bg="#2a1616", bd=1, highlightbackground="#ef4444", highlightthickness=1)
            f_red_box.pack(side=tk.BOTTOM, fill=tk.X, padx=4 if is_vert else 6, pady=(1, 2))
            self.f_red_box = f_red_box

            # ---------------------------------------------------------
            # 🔵 แถบพับ/กาง หน้าต่างย่อแบบรูปที่ 1 (ซ่อนเฉพาะแถบแดงล่าง ข้อมูลบนครบถ้วน)
            # ---------------------------------------------------------
            f_fold_bar = tk.Frame(self.main_container, bg=self.trans_key)
            f_fold_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=4 if is_vert else 6, pady=(0, 2))

            # 🕹️ Grip ปรับขนาดมุมขวาล่างสุดของหน้าต่าง (กรอบสีแดงขาว ล่าง ขวา ตามคำสั่งผู้ใช้!)
            self.grip_fold = tk.Label(f_fold_bar, text=" ◢ ", font=("Segoe UI", 8, "bold"),
                                      fg="#ffffff", bg="#dc2626", relief="solid", bd=1,
                                      highlightbackground="#ffffff", highlightthickness=1,
                                      cursor="size_nw_se", padx=2, pady=0)
            self.grip_fold.pack(side=tk.RIGHT, padx=1)
            self.grip_fold.bind("<ButtonPress-1>", self.start_resize)
            self.grip_fold.bind("<B1-Motion>", self.do_resize)
            self.grip_fold.bind("<ButtonRelease-1>", self.end_resize)

            if is_vert:
                btn_fold_txt = "▲ แถบล่าง" if getattr(self, 'is_compact_folded', False) else "▼ พับล่าง"
                fold_pad_x = 4
            else:
                btn_fold_txt = "▲ กางแถบควบคุมล่าง" if getattr(self, 'is_compact_folded', False) else "▼ พับเก็บแถบล่าง"
                fold_pad_x = 8
            btn_fold_bg = "#2a1616" if getattr(self, 'is_compact_folded', False) else "#161c28"
            btn_fold_fg = "#fca5a5" if getattr(self, 'is_compact_folded', False) else "#64748b"

            self.btn_fold_toggle = tk.Label(f_fold_bar, text=btn_fold_txt, font=("Segoe UI", 6, "bold"),
                                           fg=btn_fold_fg, bg=btn_fold_bg, relief="solid", bd=1, cursor="hand2", padx=fold_pad_x, pady=1)
            self.btn_fold_toggle.pack(anchor="center")
            self.btn_fold_toggle.bind("<Button-1>", self.toggle_compact_fold)

            if getattr(self, 'is_compact_folded', False):
                self.f_red_box.pack_forget()

            # ชั้นบนของกรอบแดง: Real Time, Server Ping, NXPC Price
            row1 = tk.Frame(f_red_box, bg="#2a1616")
            row1.pack(fill=tk.X, padx=4, pady=(2, 1))

            self.lbl_real_time = tk.Label(row1, text="00:00:00", font=("Consolas", 10, "bold"), fg="#38bdf8", bg="#2a1616")
            self.lbl_real_time.pack(side=tk.LEFT)

            self.lbl_ping = tk.Label(row1, text="?? ms", font=("Consolas", 7, "bold"), fg="#94a3b8", bg="#2a1616", cursor="hand2")
            self.lbl_ping.pack(side=tk.RIGHT)
            self.lbl_ping.bind("<Button-1>", lambda e: self.reset_api_counter())
            tk.Label(row1, text="|", font=("Consolas", 7), fg="#4b5563", bg="#2a1616").pack(side=tk.RIGHT, padx=2)
            self.lbl_nxpc = tk.Label(row1, text="NXPC: $--", font=("Consolas", 7, "bold"), fg="#f59e0b", bg="#2a1616", cursor="hand2")
            self.lbl_nxpc.pack(side=tk.RIGHT)
            self.lbl_nxpc.bind("<Button-1>", lambda e: self.toggle_nxpc_currency())

            # ชั้นกลางของกรอบแดง: ปุ่ม Scan Map + Normal Drop Mini Box + กระเป๋า NESO & Nesolet
            row2 = tk.Frame(f_red_box, bg="#2a1616")
            row2.pack(fill=tk.X, padx=4, pady=2)

            # 1. ฝั่งซ้าย: ปุ่ม Scan Map + ปุ่มตั้งค่ากรอบ OCR
            f_left_btn = tk.Frame(row2, bg="#16202c", bd=1, relief="solid")
            f_left_btn.pack(side=tk.LEFT, fill=tk.Y)

            self.btn_ocr = tk.Label(f_left_btn, text="Scan Map", font=("Segoe UI", 7, "bold"), fg="#38bdf8", bg="#16202c", cursor="hand2", padx=5)
            self.btn_ocr.pack(side=tk.LEFT, fill=tk.Y)
            self.btn_ocr.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

            self.btn_ocr_cfg = tk.Label(f_left_btn, text="✂️", font=("Segoe UI", 7, "bold"), fg="#f472b6", bg="#231728", cursor="hand2", padx=5)
            self.btn_ocr_cfg.pack(side=tk.LEFT, fill=tk.Y, padx=(1, 0))
            self.btn_ocr_cfg.bind("<Button-1>", lambda e: self.open_ocr_crop_tool())

            # 3. ตรงกลาง: Normal Drop Mini Box (เอาแบบเรืองแสงสีฟ้าออก เปลี่ยนเป็นสไตล์เรียบเนียนเข้ากับโทนแดง)
            c_norm_mini = tk.Frame(row2, bg="#1a1111", bd=1, relief="solid", 
                                   highlightbackground="#3f2121", highlightthickness=1, cursor="hand2")
            c_norm_mini.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 4))
            c_norm_mini.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ชั้นบนของ mini box: Normal + Rate %
            f_cn_top = tk.Frame(c_norm_mini, bg="#1a1111")
            f_cn_top.pack(fill=tk.X, padx=4, pady=(1, 0))
            f_cn_top.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            lbl_cn_title = tk.Label(f_cn_top, text="Normal", font=("Segoe UI", 6, "bold"), fg="#78716c", bg="#1a1111")
            lbl_cn_title.pack(side=tk.LEFT)
            lbl_cn_title.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            self.lbl_neso_norm_val = tk.Label(f_cn_top, text="40.0%", font=("Consolas", 8, "bold"), fg="#f87171", bg="#1a1111")
            self.lbl_neso_norm_val.pack(side=tk.LEFT, padx=(3, 0))
            self.lbl_neso_norm_val.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ชั้นล่างของ mini box: Stock + Drop Val
            f_cn_bot = tk.Frame(c_norm_mini, bg="#1a1111")
            f_cn_bot.pack(fill=tk.X, padx=4, pady=(0, 1))
            f_cn_bot.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            self.lbl_neso_norm_stock = tk.Label(f_cn_bot, text="📦 0", font=("Consolas", 7), fg="#a8a29e", bg="#1a1111")
            self.lbl_neso_norm_stock.pack(side=tk.LEFT)
            self.lbl_neso_norm_stock.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            self.lbl_neso_norm_drop = tk.Label(f_cn_bot, text="= 0", font=("Consolas", 7), fg="#e2e8f0", bg="#1a1111")
            self.lbl_neso_norm_drop.pack(side=tk.LEFT, padx=(3, 0))
            self.lbl_neso_norm_drop.bind("<Button-1>", lambda e: self.fetch_drop_data_async())

            # ชั้นสถานะอัปเดต
            row3 = tk.Frame(f_red_box, bg="#2a1616")
            row3.pack(fill=tk.X, padx=4, pady=1)
            
            self.lbl_last_update = tk.Label(row3, text="🕒 รออัปเดต...", font=("Segoe UI", 7), fg="#94a3b8", bg="#2a1616", cursor="hand2")
            self.lbl_last_update.pack(side=tk.LEFT)
            self.lbl_last_update.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())
            
            self.lbl_poll_countdown = tk.Label(row3, text="🔄 60s", font=("Segoe UI", 7, "bold"), fg="#94a3b8", bg="#2a1616", cursor="hand2")
            self.lbl_poll_countdown.pack(side=tk.RIGHT)
            self.lbl_poll_countdown.bind("<Button-1>", lambda e: self.trigger_scan_and_refresh())

            # ชั้นล่างสุดของกรอบแดง: Bot bar (Scout, Reset, Pin, Sound, Grip)
            row4 = tk.Frame(f_red_box, bg="#2a1616")
            row4.pack(fill=tk.X, padx=2, pady=(1, 2))
            
            grip = tk.Label(row4, text=" ◢ ", font=("Segoe UI", 9, "bold"), fg="#ef4444", bg="#3a1c1c", cursor="size_nw_se", padx=2, pady=1, relief="groove", bd=1)
            grip.pack(side=tk.RIGHT)
            grip.bind("<ButtonPress-1>", self.start_resize)
            grip.bind("<B1-Motion>", self.do_resize)
            grip.bind("<ButtonRelease-1>", self.end_resize)

            btn_scout = tk.Label(row4, text="🎒 Scout", font=("Segoe UI", 7, "bold"), fg="#00f2fe", bg="#182230", cursor="hand2", padx=4, pady=1)
            btn_scout.pack(side=tk.RIGHT, padx=4)
            btn_scout.bind("<Button-1>", lambda e: self.open_wallet_explorer())

            def on_reset_refresh():
                if self.mode == "Manual":
                    self.reset_manual_timer()
                self.trigger_scan_and_refresh()

            btn_rst = tk.Label(row4, text="🔄 Refresh", font=("Segoe UI", 7, "bold"), fg="#38ef7d", bg="#182230", cursor="hand2", padx=4, pady=1)
            btn_rst.pack(side=tk.LEFT, padx=2)
            btn_rst.bind("<Button-1>", lambda e: on_reset_refresh())

            pin_col = "#38ef7d" if self.is_pinned else "#64748b"
            btn_pin = tk.Label(row4, text="📌", font=("Segoe UI", 7), fg=pin_col, bg="#182230", cursor="hand2", padx=3, pady=1)
            btn_pin.pack(side=tk.LEFT, padx=1)
            btn_pin.bind("<Button-1>", lambda e: self.toggle_pin())

            snd_col = "#38ef7d" if self.sound_enabled else "#64748b"
            snd_icon = "🔊" if self.sound_enabled else "🔇"
            btn_snd = tk.Label(row4, text=snd_icon, font=("Segoe UI", 7), fg=snd_col, bg="#182230", cursor="hand2", padx=3, pady=1)
            btn_snd.pack(side=tk.LEFT, padx=1)
            btn_snd.bind("<Button-1>", lambda e: self.toggle_sound())

            if self.mode == "Manual":
                play_text = "⏸ หยุด" if self.manual_running else "▶ เริ่ม"
                play_bg = "#f59e0b" if self.manual_running else "#38ef7d"
                btn_play = tk.Label(row4, text=play_text, font=("Segoe UI", 7, "bold"), bg=play_bg, fg="#000000", cursor="hand2", padx=6, pady=1)
                btn_play.pack(side=tk.LEFT, padx=10)
                btn_play.bind("<Button-1>", lambda e: self.toggle_manual_play())

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
        if getattr(self, 'lbl_nxpc', None) is not None and self.lbl_nxpc.winfo_exists():
            val_str = f"฿{self.nxpc_thb:.2f}" if self.show_nxpc_thb else f"${self.nxpc_usd:.4f}"
            self.lbl_nxpc.config(text=f"NXPC: {val_str}")

    def toggle_nxpc_currency(self):
        self.show_nxpc_thb = not self.show_nxpc_thb
        self._update_nxpc_label()

    def redraw_timer_bar(self):
        if not hasattr(self, 'canvas_timer') or not self.canvas_timer.winfo_exists():
            return
        self.canvas_timer.delete("all")
        w = self.canvas_timer.winfo_width()
        h = self.canvas_timer.winfo_height()
        rem, tot = self.calculate_remaining()
        
        # ถ้ารันอยู่ แสดงความคืบหน้าจากซ้ายไปขวา
        if tot > 0:
            progress = (tot - rem) / tot
        else:
            progress = 0
            
        bar_w = w * progress
        # พื้นหลังของ bar
        self.canvas_timer.create_rectangle(0, 0, w, h, fill="#0f172a", outline="")
        # หลอดเวลา
        self.canvas_timer.create_rectangle(0, 0, bar_w, h, fill="#38bdf8", outline="")

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
            
        target_interval = 6 if is_game_active else 12

        # 🔄 เช็ครอบรีเฟรชข้อมูล Drop
        elapsed_fetch = time.time() - self.last_fetch_ts
        poll_remain = max(0, int(target_interval - elapsed_fetch))
        if elapsed_fetch >= target_interval:
            self.fetch_drop_data_async()
            poll_remain = target_interval

        # อัปเดตตัวนับเวลารีเช็คตรงกรอบสีแดง
        if hasattr(self, 'lbl_poll_countdown') and self.lbl_poll_countdown and self.lbl_poll_countdown.winfo_exists():
            eco_tag = " [Eco]" if not is_game_active else ""
            if self.is_fetching:
                self.lbl_poll_countdown.config(text="⏳ กำลังดึง...", fg="#38bdf8")
            elif self.neso_boost_stock in ["...", "รอเซิร์ฟเวอร์"] or self.neso_boost_rate in ["...", "รอข้อมูล"]:
                self.lbl_poll_countdown.config(text=f"⏳ รอ ({poll_remain}s{eco_tag})", fg="#f59e0b")
            else:
                self.lbl_poll_countdown.config(text=f"🔄 {poll_remain}s{eco_tag}", fg="#94a3b8")

        # อัปเดตแถบเวลาแนวนอน
        if not self.is_mini and getattr(self, 'canvas_timer', None) is not None and self.canvas_timer.winfo_exists():
            self.redraw_timer_bar()

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

        # 🔍 Auto-Scan OCR เบื้องหลังความเร็วสูง (3.5s Active / 8s Eco)
        scan_interval = 3.5 if is_game_active else 8.0
        now_ts = time.time()
        if not hasattr(self, 'last_auto_scan_ts'):
            self.last_auto_scan_ts = now_ts
        if now_ts - self.last_auto_scan_ts >= scan_interval:
            self.last_auto_scan_ts = now_ts
            self.auto_detect_map_async(silent=True)

        # 🪙 ดึง Nesolet ประจำตัวละครเบื้องหลังทุก 20 วินาที (Silent ไม่รก Log)
        if not hasattr(self, 'last_nesolet_fetch_ts'):
            self.last_nesolet_fetch_ts = now_ts
        if now_ts - self.last_nesolet_fetch_ts >= 20.0:
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

            if getattr(self, 'lbl_timer_text', None) is not None and self.lbl_timer_text.winfo_exists():
                self.lbl_timer_text.config(text=countdown_str, fg=theme_color)

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
            if getattr(self, 'lbl_ping', None) is not None and self.lbl_ping.winfo_exists():
                ping_col = "#38ef7d" if self.server_ping_ms < 150 else "#f59e0b" if self.server_ping_ms < 300 else "#ef4444"
                calls = getattr(self, 'api_call_count', 0)
                self.lbl_ping.config(text=f"📶 {self.server_ping_ms}ms (Req:{calls})", fg=ping_col)
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
