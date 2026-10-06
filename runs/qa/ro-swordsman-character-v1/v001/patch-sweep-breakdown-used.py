"""Joint-range report: count new body intersections by mesh pair (reporting only; gates unchanged)."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_joint_range.py"
s = path.read_text(encoding="utf-8")
old = '''            "other_new_examples": ['''
new = '''            "other_new_by_mesh_pair": dict(sorted(__import__("collections").Counter("|".join(sorted((tri_mesh[a], tri_mesh[b]))) for a, b in other_new).items(), key=lambda kv: -kv[1])[:8]),
            "other_new_examples": ['''
assert s.count(old) == 1
path.write_text(s.replace(old, new), encoding="utf-8", newline=chr(10))
print("patched")
