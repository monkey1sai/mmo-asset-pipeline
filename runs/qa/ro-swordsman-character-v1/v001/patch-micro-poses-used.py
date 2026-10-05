"""Core micro-correctives: support contract motions that start from a candidate-supplied pose."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_core_microcorrectives.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--area-ratio", type=float, default=0.08)', 'parser.add_argument("--area-ratio", type=float, default=0.08)\nparser.add_argument("--poses")')
patch('sites = json.loads((ROOT / args.sites).read_text(encoding="utf-8"))',
      'sites = json.loads((ROOT / args.sites).read_text(encoding="utf-8"))\nposes = json.loads((ROOT / args.poses).read_text(encoding="utf-8")) if args.poses else {}')
patch('''    motion = motions[motion_id]
    reset()
''', '''    motion = motions[motion_id]
    reset()
    if motion.get("requires_pose"):
        for name, quaternion in poses[motion["requires_pose"]].items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
