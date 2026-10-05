import os
import sys
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')

ICONS_CACHE_DIR = r"c:\Users\PythonX\Documents\ฟิวเจอร์ โพสิิชั่น\1.Python Code\Cloack_Overlay\icons_cache"
os.makedirs(ICONS_CACHE_DIR, exist_ok=True)

# รายชื่อไอคอนเมืองและแมพที่ไม่มีดรอปเรททั้งหมดที่พร้อมดาวน์โหลด
# Key คือชื่อไฟล์ที่จะเซฟใน icons_cache, Value คือชื่อไฟล์บน yetidb CDN
CDN_BASE = "https://media.maplestorywiki.net/yetidb/"

TOWN_ICONS = {
    # Victoria Island Towns
    "Henesys.png": "MapIcon_Henesys.png",
    "Ellinia.png": "MapIcon_Ellinia.png",
    "Perion.png": "MapIcon_Perion.png",
    "Kerning_City.png": "MapIcon_KerningCity.png",
    "Lith_Harbor.png": "WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "Nautilus.png": "MapIcon_Nautilus.png",
    "Sleepywood.png": "WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png",
    "Rien.png": "MapIcon_Rien.png",
    "Ereve.png": "WorldMapLink_%28Maple_World%29-%28Ereve%29.png",
    "Partem.png": "MapIcon_Partem.png",
    
    # Ossyria Towns
    "Orbis.png": "MapIcon_Orbis.png",
    "El_Nath.png": "MapIcon_ElNath.png",
    "Ludibrium.png": "MapIcon_Ludibrium.png",
    "Aqua_Road.png": "MapIcon_AquaRoad.png",
    "Aquarium.png": "MapIcon_AquaRoad.png",
    "Omega_Sector.png": "MapIcon_OmegaSector.png",
    "Korean_Folk_Town.png": "WorldMapLink_%28Maple_World%29-%28Ludus_Lake%29.png",
    "Leafre.png": "MapIcon_Leafre.png",
    "Mu_Lung.png": "WorldMapLink_%28Maple_World%29-%28Mu_Lung_Garden%29.png",
    "Herb_Town.png": "WorldMapLink_%28Maple_World%29-%28Mu_Lung_Garden%29.png",
    "Ariant.png": "MapIcon_Ariant.png",
    "Magatia.png": "MapIcon_Magatia.png",
    "Edelstein.png": "MapIcon_Edelstein.png",
    
    # Regional / Special Towns & Hubs
    "Singapore.png": "MapIcon_Singapore.png",
    "Malaysia.png": "MapIcon_Malaysia.png",
    "Haven.png": "MapIcon_Haven.png",
    "Scrapyard_Hub.png": "MapIcon_Haven.png",
    "Dark_World_Tree_Camp.png": "Dark_World_Tree.png",
    "Pantheon.png": "MapIcon_Pantheon.png",
    "Savage_Terminal.png": "MapIcon_SavageTerminal.png",
    "Ristonia.png": "MapIcon_Ristonia.png",
    
    # Arcane River Towns (Safe Zones / No Drop Rate)
    "Vanishing_Journey_Town.png": "MapIcon_Road_of_Vanishing.png",
    "Nameless_Town.png": "MapIcon_Road_of_Vanishing.png",
    "Reverse_City_Station.png": "MapIcon_Reverse_City.png",
    "Chu_Chu_Village.png": "MapIcon_ChewChew.png",
    "Chew_Chew_Village.png": "MapIcon_ChewChew.png",
    "Yum_Yum_Village.png": "MapIcon_YumYum.png",
    "Lachelein_Town.png": "MapIcon_Lacheln.png",
    "Spirit_Tree.png": "MapIcon_Arcana.png",
    "Arcana_Town.png": "MapIcon_Arcana.png",
    "Trueffet_Square.png": "MapIcon_Morass.png",
    "Morass_Camp.png": "MapIcon_Morass.png",
    "Esfera_Base_Camp.png": "MapIcon_esfera.png",
    "Cernium_Square.png": "MapIcon_Cernium.png",
    
    # Generic Town Fallback
    "Default_Town.png": "WorldMapLink_%28Maple_World%29-%28Victoria_Island%29.png"
}

print(f"กำลังดาวน์โหลดไอคอนเมืองทั้งหมด {len(TOWN_ICONS)} รายการ...")

success_count = 0
for local_name, cdn_file in TOWN_ICONS.items():
    save_path = os.path.join(ICONS_CACHE_DIR, local_name)
    if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
        success_count += 1
        continue
        
    url = CDN_BASE + cdn_file
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            with open(save_path, "wb") as f:
                f.write(data)
            success_count += 1
            print(f"✅ บันทึกสำเร็จ: {local_name} ({len(data)} bytes)")
    except Exception as e:
        print(f"❌ โหลดไม่สำเร็จ ({local_name}): {e}")

print(f"\nดาวน์โหลดและแคชไอคอนเมืองเสร็จสิ้น: {success_count}/{len(TOWN_ICONS)} ไฟล์")
