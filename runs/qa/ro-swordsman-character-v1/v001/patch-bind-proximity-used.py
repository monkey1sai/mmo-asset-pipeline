"""Binding by proximity: a core vertex within near_mm of the armour surface gets the armour bone fully, fading to zero at far_mm."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_bind_core_to_armor.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('''        origin = closest_on_polyline(polyline, p)
        ray = p - origin
        if ray.length < 1e-6:
            continue
        hit, _, _, distance = tree.ray_cast(origin, ray.normalized(), ray.length + margin)
        if hit is None or ray.length - distance > beyond:
            continue
        ratio = ray.length / max(distance, 1e-6)
        weight = smooth((ratio - start) / (1.0 - start))''', '''        if "near_mm" in piece:
            # Proximity: the embedded copy lies within a few centimetres of the armour surface, inside or outside it.
            _, _, _, gap = tree.find_nearest(p)
            weight = 1.0 - smooth((gap * 1000 - piece["near_mm"]) / (piece["far_mm"] - piece["near_mm"]))
            if weight > 0:
                share[index] = weight
            continue
        origin = closest_on_polyline(polyline, p)
        ray = p - origin
        if ray.length < 1e-6:
            continue
        hit, _, _, distance = tree.ray_cast(origin, ray.normalized(), ray.length + margin)
        if hit is None or ray.length - distance > beyond:
            continue
        ratio = ray.length / max(distance, 1e-6)
        weight = smooth((ratio - start) / (1.0 - start))''')
patch('''    margin, beyond, start = piece["margin_mm"] / 1000, piece["beyond_mm"] / 1000, piece["ratio_start"]''',
      '''    margin, beyond, start = piece["margin_mm"] / 1000, piece.get("beyond_mm", 0) / 1000, piece.get("ratio_start", 0)''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
