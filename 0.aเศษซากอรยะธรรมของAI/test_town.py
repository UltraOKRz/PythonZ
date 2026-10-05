town_kws = [
    'henesys', 'ellinia', 'kerning', 'lith harbor', 'perion',
    'sleepywood', 'sleepy wood', 'elluel', 'ludibrium town', 'orbis town',
    'nameless town', 'morass town', 'esfera town', 'sellas',
    'lachelein town', 'arcana town',
    'trueffet', 'trueffet square',
    'henesys hub', 'hub', 'town square', 'market', 'bazaar',
    'central town', 'main town', 'refuge', 'safe zone',
    'hideaway', 'hideout', 'camp',
    'lobby', 'waiting room', 'party room',
    'herb town', 'zipangu', 'amoria',
]

test_should_town = [
    'henesys market',
    'Kerning City Town Square',
    'Ludibrium Town Center',
    'Arcana Town',
    'Safe Zone',
    'Waiting Room',
    'Henesys Hub',
    'Trueffet Square',
]

test_not_town = [
    'Slurpy Forest',
    'One-a-Bobber Forest 2',
    'Lachelein Alley',
    'Dark World Tree Bottom',
    'Lake of Oblivion',
    'Arcana Floral Flute',
    'Mushbud Forest',
    'Minar Forest Dragon Forest',
    'Five-Color Hill',
    'Eree Valley',
]

print('=== Should be TOWN ===')
ok = 0
for t in test_should_town:
    found = any(kw in t.lower() for kw in town_kws)
    status = 'TOWN-OK' if found else 'MISS!!'
    if found:
        ok += 1
    print(f'  {status}: {t}')
print(f'  -> {ok}/{len(test_should_town)} passed')

print()
print('=== Should be FIELD (not town) ===')
ok2 = 0
for t in test_not_town:
    found = any(kw in t.lower() for kw in town_kws)
    status = 'FALSE-POS!!' if found else 'FIELD-OK'
    if not found:
        ok2 += 1
    print(f'  {status}: {t}')
print(f'  -> {ok2}/{len(test_not_town)} passed')
