"""Request-specific spec for cl-barracks-set-v1: the Web castle's barracks, brazier and wreck (changshan-longdan
src/world/castle.ts buildBarracks / roof / buildBraziers / buildWrecks) expressed as boxes relative to each asset's
ground centre. Run: python make_spec.py  -> spec.json next to this file. The wreck scatter uses a fixed mulberry32
seed so the layout is reproducible (it is not the Web's draw order)."""
import json
import math
import os

# layout.ts
BARRACKS_W, BARRACKS_D = 13.0, 15.0  # x, z
BARRACKS_ROOF_PADDING = 1.6
ROOF_TRIM_PADDING = 0.5
ROOF_CORNER_OFFSET = 0.15
ROOF_CORNER_SIZE = 0.55

# castle.ts palette (sRGB hex)
P = {
    'stone': '#8b8074', 'stoneDark': '#62594f', 'stoneLight': '#a59a8a', 'wood': '#4a2e21', 'woodLight': '#6f4a33',
    'roof': '#3a4350', 'roofDark': '#2b3139', 'gold': '#c29a45', 'plaster': '#cdbfa8', 'iron': '#35343a', 'char': '#1d1916',
}
GLOW_COALS = [4.5, 1.6, 0.35]
GLOW_EMBER = [2.4, 0.7, 0.12]


def box(c, s, color, rot_y=0.0):
    return {'c': [round(v, 4) for v in c], 's': [round(v, 4) for v in s], 'color': color, 'rot_y': round(rot_y, 4)}


def span(x0, y0, z0, x1, y1, z1, color):
    return box([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], [abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)], color)


def darker(hex_color, k=0.84):
    v = hex_color.lstrip('#')
    return '#' + ''.join(f"{int(int(v[i:i + 2], 16) * k):02x}" for i in (0, 2, 4))


def barracks_body():
    # Rect centred on the origin: minX = -6.5, maxX = 6.5, minZ = -7.5, maxZ = 7.5 (castle.ts buildBarracks).
    min_x, max_x, min_z, max_z = -BARRACKS_W / 2, BARRACKS_W / 2, -BARRACKS_D / 2, BARRACKS_D / 2
    cz = 0.0
    wall_h = 4.4
    boxes = [span(min_x + 0.3, 0, min_z + 0.3, max_x - 0.3, 0.4, max_z - 0.3, P['stoneDark']),
             span(min_x + 0.6, 0.4, min_z + 0.6, max_x - 0.6, wall_h, max_z - 0.6, P['plaster'])]
    z = min_z + 0.6
    step = (max_z - min_z - 1.2) / 4
    while z <= max_z - 0.5 + 1e-9:
        for x in (min_x + 0.6, max_x - 0.6):
            boxes.append(box([x, wall_h / 2 + 0.2, z], [0.42, wall_h - 0.4, 0.42], P['wood']))
        z += step
    for z in (min_z + 0.6, max_z - 0.6):
        boxes.append(box([0.0, wall_h / 2 + 0.2, z], [0.42, wall_h - 0.4, 0.42], P['wood']))
    boxes.append(span(min_x + 0.3, wall_h - 0.1, min_z + 0.3, max_x - 0.3, wall_h + 0.35, max_z - 0.3, P['wood']))
    # The door faces the castle interior: for the east barracks (minX > 0 in the castle) it sits on the minX side.
    door_x = min_x + 0.55
    boxes.append(box([door_x, 1.6, cz], [0.15, 3.0, 2.2], P['wood']))
    for dz in (-4, 4):
        boxes.append(box([door_x, 2.4, cz + dz], [0.12, 1.2, 1.8], P['woodLight']))
    return boxes


def roof(cx, y, cz, w, d, layers, color, trim, along_z=True):
    def sx(a, c):
        return c if along_z else a

    def sz(a, c):
        return a if along_z else c

    boxes = [box([cx, y + 0.12, cz], [sx(w + ROOF_TRIM_PADDING, d + ROOF_TRIM_PADDING), 0.24, sz(w + ROOF_TRIM_PADDING, d + ROOF_TRIM_PADDING)], trim)]
    h = 0.42
    dark = darker(color)
    for i in range(layers):
        ld = d * (1 - i / layers)
        lw = w - (d - ld)
        boxes.append(box([cx, y + 0.24 + h * (i + 0.5), cz], [sx(lw, ld), h, sz(lw, ld)], color if i % 2 == 0 else dark))
    ridge_y = y + 0.24 + h * layers + 0.2
    ridge = max(1.0, w - d + 1.2)
    boxes.append(box([cx, ridge_y, cz], [sx(ridge, 0.5), 0.4, sz(ridge, 0.5)], P['roofDark']))
    for s in (-1, 1):
        boxes.append(box([cx if along_z else cx + s * ridge / 2, ridge_y + 0.35, cz + s * ridge / 2 if along_z else cz], [0.4, 0.7, 0.4], trim))
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            boxes.append(box([cx + s1 * (sx(w, d) / 2 + ROOF_CORNER_OFFSET), y + 0.45, cz + s2 * (sz(w, d) / 2 + ROOF_CORNER_OFFSET)],
                             [ROOF_CORNER_SIZE, 0.35, ROOF_CORNER_SIZE], color))
    return boxes


def barracks_roof():
    wall_h = 4.4
    # castle.ts: roof(cx, wallH + 0.35, cz, depth + padding, width + padding, 4, roof, gold, alongZ=true)
    return roof(0.0, wall_h + 0.35, 0.0, BARRACKS_D + BARRACKS_ROOF_PADDING, BARRACKS_W + BARRACKS_ROOF_PADDING, 4, P['roof'], P['gold'], True)


def brazier():
    body = [box([0, 0.5, 0], [0.8, 1.0, 0.8], P['stoneDark']), box([0, 1.12, 0], [1.15, 0.26, 1.15], P['iron'])]
    coals = [box([0, 1.28, 0], [0.85, 0.08, 0.85], '#ffb36b')]
    return body, coals


def mulberry32(seed):
    a = seed & 0xffffffff

    def rng():
        nonlocal a
        a = (a + 0x6d2b79f5) & 0xffffffff
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xffffffff
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & 0xffffffff)) & 0xffffffff
        return ((t ^ (t >> 14)) & 0xffffffff) / 4294967296
    return rng


def wreck():
    rng = mulberry32(2026)
    debris, embers = [], []
    for _ in range(14):
        long = rng() < 0.6
        debris.append(box([(rng() - 0.5) * 3.4, 0.2 + rng() * 0.9, (rng() - 0.5) * 3.4],
                          [0.3 if long else 0.8, 0.3 + rng() * 0.3, 2 + rng() * 1.2 if long else 0.8],
                          P['char'] if rng() < 0.5 else P['wood'], rng() * math.tau))
    for _ in range(10):
        embers.append(box([(rng() - 0.5) * 3, 0.08 + rng() * 0.4, (rng() - 0.5) * 3], [0.25, 0.12, 0.25], '#ff9a3c', rng() * math.tau))
    return debris, embers


def main():
    body, coals = brazier()
    debris, embers = wreck()
    spec = {
        'request_id': 'cl-barracks-set-v1',
        'source': 'changshan-longdan src/world/castle.ts (buildBarracks, roof, buildBraziers, buildWrecks) and layout.ts',
        'assets': [
            {'id': 'cl-barracks', 'parts': [{'name': 'barracks-body', 'boxes': barracks_body()}, {'name': 'barracks-roof', 'boxes': barracks_roof()}]},
            {'id': 'cl-brazier', 'parts': [{'name': 'brazier-body', 'boxes': body}, {'name': 'brazier-coals', 'emissive': GLOW_COALS, 'boxes': coals}]},
            {'id': 'cl-wreck', 'parts': [{'name': 'wreck-debris', 'boxes': debris}, {'name': 'wreck-embers', 'emissive': GLOW_EMBER, 'boxes': embers}]},
        ],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spec.json')
    with open(out, 'w', encoding='utf-8') as handle:
        json.dump(spec, handle, ensure_ascii=False, indent=1)
    print('spec', out, 'boxes', sum(len(p['boxes']) for a in spec['assets'] for p in a['parts']))


if __name__ == '__main__':
    main()
