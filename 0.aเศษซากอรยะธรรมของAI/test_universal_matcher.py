import sys
import json
import re
import difflib

# โหลด layers_cache.json
with open(r'1.Python Code\Cloack_Overlay\layers_cache.json', 'r', encoding='utf-8') as f:
    layers_list = json.load(f)

GLOBAL_MAP_ALIASES = [
    # 1. Chew Chew Island (Arc. 100 ~ 190)
    (131005, ["slurpy", "one-a-bobber", "one a bobber", "bitty-bobber", "bitty bobber", "illiard fungos", "illiard plains", "illiard", "bobber 2", "bobber 1", "slurpy forest"]),
    (131001, ["five-color", "five color", "hill path", "mottled forest", "mottled"]),
    (131002, ["eree valley", "eree", "dealie-bobber", "dealie bobber", "dealie"]),
    (131003, ["skywhale", "sky whale", "colossal root", "whale mountain"]),
    (131004, ["mushbud", "torrent zone", "mushbud forest"]),
    
    # 2. Scrapyard & Black Heaven (Lv. 200 ~ 219)
    (122007, ["junction 3", "maze 3", "inside 3", "black heaven inside 3", "haven inside 3"]),
    (122006, ["junction 2", "maze 2", "inside 2", "black heaven inside 2", "haven inside 2"]),
    (122005, ["junction 1", "maze 1", "inside 1", "black heaven inside 1", "haven inside 1"]),
    (121002, ["skyline edge", "skyline 1", "skyline 2", "skyline"]),
    (121001, ["scrapyard", "scrap yard", "scrapyard entrance"]),

    # 3. Dark World Tree (Lv. 210 ~ 219)
    (122001, ["abandoned campsite", "campsite", "tree bottom", "lower stem", "dwt bottom"]),
    (122002, ["mid bottom", "lower left", "lower right"]),
    (122003, ["mid top", "upper left", "upper right"]),
    (122004, ["tree top", "top branch", "dwt top"]),

    # 4. Road of Vanishing (Arc. 30 ~ 100)
    (130001, ["lake of oblivion", "oblivion", "vanishing lake", "restful rock"]),
    (130002, ["extinction zone", "extinction", "fire river", "rocky area"]),
    (130003, ["cave of repose", "repose", "hidden cave", "below the cave"]),

    # 5. Reverse City (Arc. 30 ~ 100)
    (130004, ["underground", "subway", "train line", "t-boy"]),
    (130005, ["surface", "hidden station", "rooftop"]),

    # 6. Lachelein (Arc. 190 ~ 240)
    (132001, ["lachelein alley", "backalley", "alley 1", "alley 2", "alley 3", "lachelein hideout"]),
    (132002, ["lachelein street", "ballroom", "victory plate", "occupied dance"]),
    (132003, ["lachelein clocktower", "nightmare clocktower", "clocktower 1", "clocktower 2", "clocktower 3", "clocktower 4", "clocktower 5", "clocktower"]),

    # 7. Arcana (Arc. 280 ~ 360)
    (133001, ["floral flute", "flute", "spirit tree", "spirit grove", "clearing"]),
    (133002, ["heart of the forest", "heart of forest", "deep in the forest"]),
    (133003, ["cavernous cavern", "cavernous", "lower path", "upper path", "deep cavern"]),

    # 8. Morass (Arc. 400 ~ 520)
    (134001, ["coral forest", "path to the coral", "coral"]),
    (134002, ["trueffet street", "street 1", "street 2"]),
    (134003, ["research lab", "closed area", "laboratory", "lab"]),
    (134004, ["that day in trueffet", "that day", "rampart", "castle wall"]),

    # 9. Esfera (Arc. 560 ~ 670)
    (135003, ["radiant temple", "temple of light", "mirror temple"]),
    (136003, ["star-swallowing", "star swallowing", "sea of tears"]),

    # 10. Maple World & Legacy Areas
    (120001, ["twilight perion", "desolate hills"]),
    (120002, ["excavation area", "excavation site", "wild cargo"]),
    (120003, ["fox valley", "fox ridge", "fox tree"]),
    (118001, ["kritias", "ranheim"]),
    (117001, ["gate to the future", "henesys ruins", "dark ereve"]),
    (117002, ["omega sector", "silo", "hangar", "command center"]),
    (115001, ["temple of time", "road of memory", "road of regret", "road of oblivion"]),
    (115002, ["kerning tower", "kerning floor"]),
    (116001, ["stone colossus", "colossus"]),
    (114001, ["mu lung garden", "mu lung", "herb town"]),
    (114002, ["korean folk town", "folk town"]),
    (114003, ["dead mine"]),
    (114004, ["golden temple"]),
    (114005, ["crimsonheart"]),
    (114006, ["partem"]),
    (113001, ["dragon forest", "wyvern", "nest of dead dragon", "peak of dragon"]),
    (111001, ["minar forest", "leafre", "beetle", "centipede"]),
]

def match_map(raw_text):
    raw_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    title_line = raw_lines[0].lower() if len(raw_lines) > 0 else ""
    sub_line = raw_lines[1].lower() if len(raw_lines) > 1 else ""
    combined_text = (title_line + " " + sub_line + " " + raw_text.replace("\n", " ")).lower()

    matched_item = None
    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
        for kw in kw_list:
            if kw in combined_text or (title_line and kw in title_line) or (sub_line and kw in sub_line):
                matched_item = next((item for item in layers_list if item["layerId"] == target_lid), None)
                if matched_item:
                    break
        if matched_item:
            break

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
        for item in layers_list:
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

    return matched_item

# รันเคสทดสอบจริง
test_cases = [
    ("Slurpy Forest\nOne-a-Bobber Forest 2", 131005, "Illiard Fungos (Chu Chu / Slurpy)"),
    ("Five-Color Hill\nMottled Forest 1", 131001, "Five-Color Hill"),
    ("Scrapyard\nBlack Heaven Junction 3", 122007, "Inside 3"),
    ("Dark World Tree\nAbandoned Campsite", 122001, "DWT Bottom"),
    ("Lachelein\nClocktower of Nightmares 1st Floor", 132003, "Lachelein Clocktower"),
    ("Arcana\nCavernous Cavern Lower Path", 133003, "Cavernous Cavern"),
    ("Minar Forest\nDragon Forest 1", 113001, "Dragon Forest"),
]

print("=== Running Universal Matcher Test ===")
all_pass = True
for ocr_input, expected_id, label in test_cases:
    m = match_map(ocr_input)
    actual_id = m["layerId"] if m else None
    actual_name = m["layerName"] if m else "None"
    status = "PASS" if actual_id == expected_id else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"[{status}] Input: {ocr_input.replace(chr(10), ' | ')} -> Result: {actual_id} ({actual_name}) [Expected: {expected_id}]")

print(f"\nOverall Result: {'ALL TESTS PASSED! 100%' if all_pass else 'SOME TESTS FAILED!'}")
