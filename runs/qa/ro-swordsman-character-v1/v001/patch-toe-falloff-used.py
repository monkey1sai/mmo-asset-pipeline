"""Toe weights fade out sideways over 35 mm beyond the radius instead of stopping at a hard edge (the hard edge stretched boundary edges past 3x)."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_v001_assemble.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('''            if foot_weight > 0 and ahead > -span / 2 and beside <= args.toe_radius_mm / 1000:
                t = min(1.0, (ahead + span / 2) / span)
                share = foot_weight * t * t * (3 - 2 * t)''',
      '''            side = min(1.0, max(0.0, (beside - args.toe_radius_mm / 1000) / 0.035))
            sideways = 1.0 - side * side * (3 - 2 * side)
            if foot_weight > 0 and ahead > -span / 2 and sideways > 0:
                t = min(1.0, (ahead + span / 2) / span)
                share = foot_weight * t * t * (3 - 2 * t) * sideways''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
