"""Toe weights only within a radius of the toe bone's axis, so straps and buckles beside the boot stay with the foot."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_v001_assemble.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--left-bracer"', 'parser.add_argument("--toe-radius-mm", type=float, default=1000.0)\nparser.add_argument("--left-bracer"')
patch('''            if foot_weight > 0 and ahead > -span / 2:''',
      '''            offset = v.co - toe_bone.head_local
            beside = (offset - direction * offset.dot(direction)).length
            if foot_weight > 0 and ahead > -span / 2 and beside <= args.toe_radius_mm / 1000:''')
patch('''    toes = {"applied": True, "blend_mm": args.toe_blend_mm}''', '''    toes = {"applied": True, "blend_mm": args.toe_blend_mm, "radius_mm": args.toe_radius_mm}''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
