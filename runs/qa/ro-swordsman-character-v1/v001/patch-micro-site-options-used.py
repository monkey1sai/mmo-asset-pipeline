"""Core micro-correctives: per-site area target and choice of the vertex to move."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_core_microcorrectives.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('''    apex = next(v for v in corners if v not in base)
    start = posed[apex].copy()
    for _ in range(400):
        if area() / rest_area >= args.area_ratio:
            break''', '''    apex = next(v for v in corners if v not in base)
    if "move_corner" in site:
        apex = corners[site["move_corner"]]
        base = [v for v in corners if v != apex]
    goal = site.get("area_ratio", args.area_ratio)
    start = posed[apex].copy()
    for _ in range(400):
        if area() / rest_area >= goal:
            break''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
