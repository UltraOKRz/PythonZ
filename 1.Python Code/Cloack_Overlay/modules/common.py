import tkinter as tk
import tkinter.font as tkfont
import os
import sys
import re

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_BASE_DIR, "cos_config.json")
LAYERS_CACHE_FILE = os.path.join(_BASE_DIR, "layers_cache.json")
ICONS_CACHE_DIR = os.path.join(_BASE_DIR, "icons_cache")
os.makedirs(ICONS_CACHE_DIR, exist_ok=True)

DEFAULT_WALLET = "0x69ca1eA12Be04DAFD27FB9164CB802878e846d16"


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
    "gw_a7485d00ca42c9d6b744293e656529288967509c8f932770c78700462f7dd964c0e8c1af10219bf6d920ecbabe5b6a39",
    "gw_cd6b168d8546323ae6649ddfaa4b03c81e1a24ac52905ffd49b779dd5fcaeb644bef268c57e56bf0a19e0da05b1b48b7",
    "gw_7661eda48ea3a8059a23fb45ed1728e37c7e1fe6c76ba90466f1c2f3ea7e9d77c758ad60fea977bdb09ffcd697958b91",
    "gw_d2afb1dead919243a7743afb04df9bbea29ba43564b827f6ddca863d8a9335b32864914e8fcb5381e2163c1ba8da87c5",
    "gw_350ecf515176ff9748e4d6cfe7a2e080b8e590d28623f5a0b80bbb4419632a9f5c62624fc6237c01aa748ab3dfa6b5b5",
    "gw_e9dfd537898b9f3eae6de931c72c6f6289324c84d4e8c62a20e62c3d5b13e4b63e256c4f22b2e00fbeaa5e51456c264d",
    "gw_135ac9163d45942b707fe5a372ea9fe091505079c7b9632f8673fce668bb4111c85f92e28a7f6cb9d4b84d318edd53bd",
    "gw_2e24cb3f4c2e1cea8d3faa3b9891ef248efdf409c9543605d22b82c2e9e2ef742812042a8bfd6b9e1b7272eb7240e0de",
    "gw_dd722cf9d7c7dad6817c27faf8036d9cc0572132148324e5a23777696285fcc9f6b9f29079810788f115aa5df3f77220",
    "gw_7a49af01ff1b10cb370ffd9da4a0ccfe0e88884013348ef9534e4d47c61c3fa375afa866ca337c75a7546915a2401c82",
    "gw_e22dd89c5aa1340d948b542cb0854e2c93755a89f60b41ebd0dbecf0503d146714fbbc507e06ba264171d60d46ce7e1d"
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
            return f"{n/1_000_000:.2f}M"
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
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


