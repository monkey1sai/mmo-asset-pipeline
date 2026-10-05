"""Two-hand pose search: keep both wrists high and forward enough that a 30 degree forward lean does not carry the hands into the coat."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_two_hand_pose.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--spacing-mm", type=float, default=112.0)',
      'parser.add_argument("--spacing-mm", type=float, default=112.0)\nparser.add_argument("--min-wrist-height", type=float, default=1.15)\nparser.add_argument("--min-wrist-forward", type=float, default=0.26)')
patch('''                    if max(right.translation.y, left.translation.y) > spine_y - 0.20 or right.translation.x > 0.05 or left.translation.x < -0.05:''',
      '''                    if max(right.translation.y, left.translation.y) > spine_y - args.min_wrist_forward or right.translation.x > 0.05 or left.translation.x < -0.05:
                        continue
                    if min(right.translation.z, left.translation.z) < args.min_wrist_height:''')
patch("for gz in (1.05, 1.12, 1.19, 1.26):", "for gz in (1.12, 1.19, 1.26, 1.33):")
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
