import json, re, difflib

layers = json.load(open('layers_cache.json', encoding='utf-8'))

GLOBAL_MAP_ALIASES = [
    # 130002: Extinction Zone
    (130002, ['weathered land of fire', 'hidden fire zone', 'extinction zone', 'flame cliff', 'fire river', 'foot of the volcano', 'soul zone', 'fire zone', 'extinction 1', 'extinction 2', 'extinction 3', 'extinction']),
    # 130001: Lake of Oblivion
    (130001, ['weathered land of happiness', 'weathered land of rage', 'weathered land of sadness', 'weathered land of joy', 'cliff of rest', 'lake of oblivion', 'oblivion lake', 'restful rock', 'oblivion']),
    # 130003: Cave of Repose
    (130003, ['cave of repose', 'below the cave', 'hidden cave', 'cave depths', 'armas hideout', "arma's hideout", 'upper cave', 'lower cave', 'repose']),
    # 130004: Underground
    (130004, ['reverse city underground', 'subway line 1', 'subway line 2', 'subway line 3', 'underground train', 'tboys research lab', "t-boy's research lab", 'subway track', 'underground', 'subway', 'train line']),
    # 130005: Surface
    (130005, ['reverse city surface', 'surface 1', 'surface 2', 'surface 3', 'hidden station', 'rooftop', 'surface', 'overpass']),
    # 131005: Illiard Fungos
    (131005, ['slurpy forest depths', 'slurpy forest', 'illiard fungos', 'illiard plains', 'one-a-bobber', 'one a bobber', 'bitty-bobber', 'bitty bobber', 'bobber 1', 'bobber 2', 'slurpy', 'fungos', 'illiard']),
    # 131001: Five-Color Hill
    (131001, ['five-color hill', 'five color hill', 'mottled forest 1', 'mottled forest 2', 'mottled forest 3', 'mottled forest', 'colour hill', 'hill path', 'mottled']),
    # 131002: Eree Valley
    (131002, ['dealie-bobber forest', 'dealie bobber forest', 'eree valley 1', 'eree valley 2', 'eree valley', 'dealie-bobber', 'dealie bobber', 'dealie', 'eree']),
    # 131003: Skywhale Mountain
    (131003, ['skywhale mountain', 'colossal root', 'whale mountain', 'skywhale peak', 'skywhale 1', 'skywhale 2', 'skywhale', 'sky whale']),
    # 131004: Mushbud Forest
    (131004, ['torrent zone 1', 'torrent zone 2', 'torrent zone 3', 'torrent zone', 'mushbud forest', 'mushbud 1', 'mushbud 2', 'mushbud']),
    # 132001: Lachelein Alley
    (132001, ['lachelein alleyway', 'lachelein alley', 'lachelein hideout', 'backalley 1', 'backalley 2', 'backalley 3', 'backalley', 'alley 1', 'alley 2', 'alley 3', 'alleyway', 'alley']),
    # 132002: Lachelein Street
    (132002, ['occupied dance floor', 'occupied dance', 'theatre street', 'victory plate', 'main street 1', 'main street 2', 'main street', 'ballroom 1', 'ballroom 2', 'ballroom 3', 'ballroom', 'lachelein street']),
    # 132003: Lachelein Clocktower
    (132003, ['nightmare clocktower 1f', 'nightmare clocktower 2f', 'nightmare clocktower 3f', 'nightmare clocktower 4f', 'nightmare clocktower 5f', 'nightmare clocktower', 'lachelein clocktower', 'clocktower 1f', 'clocktower 2f', 'clocktower 3f', 'clocktower 4f', 'clocktower 5f', 'clocktower 1', 'clocktower 2', 'clocktower 3', 'clocktower 4', 'clocktower 5', 'clocktower']),
    # 133001: Near the Floral Flute
    (133001, ['between frost and lightning', 'where fireflies dance', 'forest of sunlight', 'forest of lightning', 'forest of water', 'forest of earth', 'forest of frost', 'near the floral flute', 'sun-drenched', 'spirit tree', 'spirit grove', 'floral flute', 'fireflies', 'flute']),
    # 133002: Heart of the Forest
    (133002, ['grove of whispering', 'tree of beginnings', 'deep in the forest', 'heart of the forest', 'heart of forest', 'forest heart']),
    # 133003: Cavernous Cavern
    (133003, ['deep in the cavern - lower path', 'deep in the cavern - upper path', 'four-branch cave', 'four branch cave', 'cavern lower path', 'cavern upper path', 'cavernous cavern', 'deep cavern', 'cavern lower', 'cavern upper', 'lower path', 'upper path', 'cavernous']),
    # 134001: Path to the Coral Forest
    (134001, ['path to the coral forest 1', 'path to the coral forest 2', 'path to the coral forest 3', 'path to the coral forest 4', 'path to the coral forest 5', 'path to the coral forest', 'path to the coral', 'coral forest 1', 'coral forest 2', 'coral forest 3', 'coral forest 4', 'coral forest 5', 'coral forest', 'coral path', 'abandoned area']),
    # 134002: Trueffet Street
    (134002, ['shadows of the swamp', 'swamp of memory', 'trueffet street', 'bully boulevard', 'bully blvd 1', 'bully blvd 2', 'bully blvd 3', 'bully blvd', 'street 1', 'street 2', 'arpien']),
    # 134003: Research Lab
    (134003, ['research laboratory', 'research lab', 'closed area', 'laboratory 1', 'laboratory 2', 'laboratory', 'lab']),
    # 134004: That Day in Trueffet
    (134004, ['that day in trueffet 1', 'that day in trueffet 2', 'that day in trueffet 3', 'that day in trueffet 4', 'that day in trueffet', 'trueffet rampart', 'that day 1', 'that day 2', 'that day 3', 'that day 4', 'that day', 'rampart', 'castle wall']),
    # 135003: Radiant Temple
    (135003, ['mirror light 1', 'mirror light 2', 'mirror light 3', 'mirror light 4', 'mirror light', 'living spring 1', 'living spring 2', 'living spring 3', 'living spring', 'radiant temple', 'temple of light', 'mirror temple', 'esfera temple']),
    # 136003: Star-Swallowing Sea
    (136003, ['star-swallowing sea 1', 'star-swallowing sea 2', 'star-swallowing sea 3', 'star-swallowing sea', 'deep mirror sea', 'star-swallowing', 'star swallowing', 'sea of tears', 'esfera sea']),
    # 122007: Scrapyard, Black Heaven Inside 3
    (122007, ['black heaven junction 3', 'black heaven inside 3', 'scrapyard, black heaven inside 3', 'black heaven maze 3', 'black heaven deck 3', 'junction 3', 'inside 3', 'maze 3', 'deck 3', 'bh inside 3', 'bhi3']),
    # 122006: Scrapyard, Black Heaven Inside 2
    (122006, ['black heaven junction 2', 'black heaven inside 2', 'scrapyard, black heaven inside 2', 'black heaven maze 2', 'black heaven deck 2', 'junction 2', 'inside 2', 'maze 2', 'deck 2', 'bh inside 2', 'bhi2']),
    # 122005: Scrapyard, Black Heaven Inside 1
    (122005, ['black heaven junction 1', 'black heaven inside 1', 'scrapyard, black heaven inside 1', 'black heaven maze 1', 'black heaven deck 1', 'junction 1', 'inside 1', 'maze 1', 'deck 1', 'bh inside 1', 'bhi1']),
    # 121002: Scrapyard Skyline
    (121002, ['scrapyard skyline', 'upper skyline', 'skyline edge', 'skyline 1', 'skyline 2', 'skyline']),
    # 121001: Scrapyard
    (121001, ['scrapyard entrance', 'scrapyard hill', 'scrapyard lot', 'scrapyard deck', 'scrapyard upper', 'hillside 1', 'hillside 2', 'hillside', 'scrapyard']),
    # 122004: Dark World Tree Top
    (122004, ['dark world tree top', 'world tree top', 'top branch', 'upper stem', 'dwt top', 'tree top', 'world tree 4']),
    # 122003: Dark World Tree Mid Top
    (122003, ['dark world tree mid top', 'world tree mid top', 'upper left stem', 'upper right stem', 'upper left', 'upper right', 'dwt mid top', 'mid top', 'world tree 3']),
    # 122002: Dark World Tree Mid Bottom
    (122002, ['dark world tree mid bottom', 'world tree mid bottom', 'lower left stem', 'lower right stem', 'lower left', 'lower right', 'dwt mid bottom', 'mid bottom', 'world tree 2']),
    # 122001: Dark World Tree Bottom
    (122001, ['dark world tree bottom', 'world tree bottom', 'lower stem 1', 'lower stem 2', 'lower stem 3', 'lower stem', 'tree bottom', 'dwt bottom', 'world tree 1']),
    # 120002: Twilight Perion Excavation Area
    (120002, ['twilight perion excavation', 'rough wilderness', 'excavation area', 'excavation site', 'wild cargo area', 'wild cargo', 'excavation 1', 'excavation 2']),
    # 120001: Twilight Perion
    (120001, ['deserted southern ridge', 'twilight perion', 'desolate hills', 'perion ruins']),
    # 120003: Fox Valley
    (120003, ['fox valley', 'fox ridge', 'fox tree', 'fox forest']),
    # 113001: Minar Forest Dragon Forest
    (113001, ['minar forest dragon forest', 'nest of dead dragon', 'peak of the big horn', 'peak of dragon', 'wyvern canyon', 'wyvern valley', 'dragon forest', 'wyvern', 'manon', 'griffey']),
    # 111001: Minar Forest
    (111001, ['entrance to dragon forest', 'dragon nest', 'minar forest', 'leafre', 'beetle', 'centipede']),
    # 111002: Aqua Road Deep Sea
    (111002, ['mushroom coral hill', 'aqua road deep sea', 'deep sea gorge', 'deep underwater', 'aqua dungeon', 'deep sea', 'submerged']),
    # 108001: Aqua Road
    (108001, ['aqua road', 'aquarium', 'crystal dunes', 'seaweed']),
    # 111003: Heliseum Tyrant's Territory
    (111003, ["heliseum tyrant's territory", "tyrant's territory", 'tyrant territory', "tyrant's castle", 'tyrant castle', 'commander']),
    # 110004: Heliseum
    (110004, ['downtown black market', 'heliseum', 'beldar']),
]

def resolve(raw_title, raw_sub):
    title_line = raw_title.lower().strip()
    sub_line = raw_sub.lower().strip()
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title_line).strip()
    clean_sub = re.sub(r'[^a-zA-Z0-9\s]', '', sub_line).strip()
    combined_text = (clean_title + ' ' + clean_sub).strip()

    # Step 1: Sub-Map Matching ผ่าน GLOBAL_MAP_ALIASES (เฉพาะ sub_line ก่อน!)
    if clean_sub:
        for target_lid, kw_list in GLOBAL_MAP_ALIASES:
            for kw in sorted(kw_list, key=len, reverse=True):
                if kw in sub_line:
                    item = next((it for it in layers if it['layerId'] == target_lid), None)
                    if item:
                        return item['layerId']

    # Step 2: Combined Text Matching ผ่าน GLOBAL_MAP_ALIASES
    for target_lid, kw_list in GLOBAL_MAP_ALIASES:
        for kw in sorted(kw_list, key=len, reverse=True):
            if kw in combined_text:
                item = next((it for it in layers if it['layerId'] == target_lid), None)
                if item:
                    return item['layerId']

    # Step 3: Exact Match 100%
    for item in layers:
        clean_lname = re.sub(r'[^a-zA-Z0-9\s]', '', item['layerName'].lower()).strip()
        if clean_sub and clean_sub == clean_lname:
            return item['layerId']
        if combined_text == clean_lname:
            return item['layerId']
        if clean_title == clean_lname and not clean_sub:
            return item['layerId']

    # Step 4: Smart Zone Disambiguation
    if 'black heaven' in combined_text:
        if any(x in combined_text for x in ['3', 'inside 3', 'junction 3', 'maze 3', 'deck 3']):
            return 122007
        elif any(x in combined_text for x in ['2', 'inside 2', 'junction 2', 'maze 2', 'deck 2']):
            return 122006
        elif any(x in combined_text for x in ['1', 'inside 1', 'junction 1', 'maze 1', 'deck 1']):
            return 122005

    if 'dark world tree' in combined_text or 'world tree' in combined_text:
        if any(x in combined_text for x in ['mid top', 'upper', 'mid-top', '3']):
            return 122003
        elif any(x in combined_text for x in ['mid bottom', 'mid-bottom', 'mid bot', '2']):
            return 122002
        elif any(x in combined_text for x in ['top branch', 'tree top', 'top', '4']):
            return 122004
        elif any(x in combined_text for x in ['bottom', 'lower', '1']):
            return 122001

    if 'lachelein' in combined_text:
        if any(x in combined_text for x in ['clocktower', 'nightmare', 'tower']):
            return 132003
        elif any(x in combined_text for x in ['street', 'ballroom', 'dance', 'theatre', 'plate']):
            return 132002
        elif any(x in combined_text for x in ['alley', 'hideout', 'alleyway']):
            return 132001

    return None

test_cases = [
    ('Black Heaven', 'Black Heaven Junction 2', 122006),
    ('Black Heaven', 'Black Heaven Junction 1', 122005),
    ('Black Heaven', 'Black Heaven Junction 3', 122007),
    ('Black Heaven', 'Black Heaven Maze 2', 122006),
    ('Dark World Tree', 'Upper Left Stem', 122003),
    ('Dark World Tree', 'Lower Left Stem', 122002),
    ('Dark World Tree', 'Top Branch', 122004),
    ('Dark World Tree', 'Lower Stem 1', 122001),
    ('Lachelein', 'Nightmare Clocktower 2F', 132003),
    ('Lachelein', 'Main Street 1', 132002),
    ('Lachelein', 'Backalley 2', 132001),
    ('Arcana', 'Deep in the Cavern - Lower Path', 133003),
    ('Arcana', 'Forest of Earth', 133001),
    ('Morass', 'That Day in Trueffet 2', 134004),
    ('Morass', 'Path to the Coral Forest 1', 134001),
    ('Scrapyard', 'Scrapyard Hill', 121001),
    ('Scrapyard', 'Upper Skyline', 121002),
    ('Twilight Perion', 'Rough Wilderness', 120002),
    ('Extinction Zone', 'Weathered Land of Fire', 130002),
    ('Lake of Oblivion', 'Cliff of Rest', 130001),
]

all_passed = True
for title, sub, expected in test_cases:
    res = resolve(title, sub)
    status = 'PASS' if res == expected else f'FAIL (Got {res}, Expected {expected})'
    if res != expected:
        all_passed = False
    print(f'[{status}] Top: {title} | Bot: {sub} -> {res}')

print('ALL PASSED:', all_passed)
