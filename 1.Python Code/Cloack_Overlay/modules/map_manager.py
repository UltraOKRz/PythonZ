import os
import json
import re
import urllib.request
import threading
from PIL import Image, ImageTk
from modules.common import LAYERS_CACHE_FILE, ICONS_CACHE_DIR, ZONE_ICONS_MAP

MAP_MAPPING_DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "map_mapping_db.json")

def parse_zone_and_submap(layer_name):
    """
    แยกชื่อโซนหลัก (Zone/Region) และชื่อแมพย่อย (Sub-map) ออกจากกัน
    ตัวอย่าง:
      "Scrapyard, Black Heaven Inside 1" -> ("Scrapyard", "Black Heaven Inside 1")
      "Crimsonheart Castle"              -> ("Crimsonheart Castle", "")
      "Twilight Perion Excavation Area"  -> ("Twilight Perion", "Excavation Area")
    """
    if not layer_name:
        return "", ""
        
    raw = layer_name.strip()
    
    # 1. ถ้ามี comma คั่นชัดเจน
    if "," in raw:
        parts = [p.strip() for p in raw.split(",", 1)]
        return parts[0], parts[1]
        
    # 2. ตรวจสอบกลุ่มคำที่ต่อท้ายเป็นโซนย่อย
    known_zone_prefixes = [
        ("Twilight Perion", ["Excavation Area"]),
        ("Minar Forest", ["Dragon Forest"]),
        ("Aqua Road", ["Deep Sea"]),
        ("Heliseum", ["Tyrant's Territory"]),
        ("Clocktower", ["Bottom Floor"]),
        ("Lion King's Castle", []),
        ("Dark World Tree", ["Bottom", "Mid Bottom", "Mid Top", "Top"]),
        ("Lachelein", ["Alley", "Street", "Clocktower"]),
    ]
    
    for prefix, sub_patterns in known_zone_prefixes:
        if raw.startswith(prefix) and len(raw) > len(prefix):
            remainder = raw[len(prefix):].strip()
            return prefix, remainder

    return raw, ""


class MapManagerMixin:
    """Mixin จัดการข้อมูล Layers, แผนที่, แคช, รูปไอคอน Zone และการแยกส่วนชื่อแมพ"""
    
    def load_mapping_db(self):
        """โหลดฐานข้อมูล Mapping แท้ (73 Layers + Towns + Submaps) จาก MCP เพื่อเสริมความแม่นยำของ OCR"""
        self.map_mapping_db = {}
        if os.path.exists(MAP_MAPPING_DB_FILE):
            try:
                with open(MAP_MAPPING_DB_FILE, "r", encoding="utf-8") as f:
                    self.map_mapping_db = json.load(f)
            except Exception as e:
                print("Error loading map_mapping_db:", e)

    def load_layers_cache(self):
        """โหลดรายชื่อฟิลด์จาก cache ไฟล์ในเครื่องเพื่อให้เปิดได้ทันที"""
        self.load_mapping_db()
        if os.path.exists(LAYERS_CACHE_FILE):
            try:
                with open(LAYERS_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.layers_list = json.load(f)
            except Exception as e:
                print("Error loading layers cache:", e)
        # ถ้าไม่มี ให้ไป fetch ใน background
        if not getattr(self, 'layers_list', None):
            threading.Thread(target=self.refresh_layers_from_api, daemon=True).start()

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

    def select_layer_by_id(self, layer_id):
        """เปลี่ยนแมพปัจจุบันด้วย layerId พร้อมรีเฟรชหน้าต่างและข้อมูลดรอป"""
        for fld in getattr(self, 'layers_list', []):
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

    def get_parsed_current_map(self):
        """คืนค่า (Zone, Sub-map) ของแมพที่เลือกอยู่ปัจจุบัน"""
        return parse_zone_and_submap(getattr(self, 'selected_layer_name', ''))

    def get_zone_icon(self, map_name, size_h=24):
        """ค้นหาและดึงรูป Zone/Town Icon จาก cache หรือ CDN"""
        if not map_name:
            return None
            
        icon_filename = None
        
        # 1. ค้นหาจาก map_mapping_db ที่เราทำ Mapping ไว้เป๊ะๆ
        db = getattr(self, 'map_mapping_db', {})
        if db:
            # 1.1 เช็คจาก Towns
            for tname, tinfo in db.get('towns', {}).items():
                if tname.lower() in map_name.lower() or map_name.lower() in tname.lower():
                    icon_filename = tinfo.get('icon_file')
                    break
            # 1.2 เช็คจาก 73 Layers
            if not icon_filename:
                for lid, linfo in db.get('layers', {}).items():
                    lname = linfo.get('layer_name', '')
                    zname = linfo.get('zone_name', '')
                    if lname.lower() in map_name.lower() or zname.lower() in map_name.lower():
                        icon_filename = linfo.get('icon_file')
                        break
            # 1.3 เช็คจาก zone_icon_binding โดยตรง
            if not icon_filename:
                bindings = db.get('zone_icon_binding', {})
                for k, fname in bindings.items():
                    if k in map_name.lower() or map_name.lower() in k:
                        icon_filename = fname
                        break

        # 2. ถ้าไม่เจอ ลองหาไฟล์ใน ICONS_CACHE_DIR ตรงๆ
        if not icon_filename:
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', map_name.replace(" ", "_")).lower()
            if os.path.exists(ICONS_CACHE_DIR):
                for f in os.listdir(ICONS_CACHE_DIR):
                    if f.lower().endswith(".png") and (clean_name in f.lower() or f[:-4].lower() in clean_name):
                        icon_filename = f
                        break
                        
        if not icon_filename:
            if "เมือง" in map_name or "town" in map_name.lower():
                icon_filename = "MSTown.png"
            elif "dojo" in map_name.lower():
                icon_filename = "MuruengRaid.png"
            elif "monster" in map_name.lower() and "park" in map_name.lower():
                icon_filename = "MonsterPark.png"
            else:
                icon_filename = "None.png"
            
        cache_id = f"{icon_filename}_{size_h}"
        if not hasattr(self, 'zone_photo_cache'):
            self.zone_photo_cache = {}
            
        if cache_id in self.zone_photo_cache:
            return self.zone_photo_cache[cache_id]
            
        cache_path = os.path.join(ICONS_CACHE_DIR, icon_filename)
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
                
        return None

    def get_neso_coin_photo(self, size=30):
        cache_id = f"neso_coin_{size}"
        if not hasattr(self, 'zone_photo_cache'):
            self.zone_photo_cache = {}
        if cache_id in self.zone_photo_cache:
            return self.zone_photo_cache[cache_id]
            
        cache_path = os.path.join(ICONS_CACHE_DIR, "neso_coin.png")
        if os.path.exists(cache_path):
            try:
                img = Image.open(cache_path)
                orig_w, orig_h = img.size
                ratio = float(size) / orig_h if orig_h > 0 else 1.0
                new_w = max(size, int(orig_w * ratio))
                img = img.resize((new_w, size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.zone_photo_cache[cache_id] = photo
                return photo
            except Exception:
                pass
        return None
