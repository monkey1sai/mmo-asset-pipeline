"""Add the dominant bones of intersecting hand triangles to the joint-range report (reporting only; gates unchanged)."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_joint_range.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch("tris, tri_mesh, edges, hand_weight, bone_vertices = [], [], [], [], {}", "tris, tri_mesh, edges, hand_weight, bone_vertices, dominant = [], [], [], [], {}, []")
patch("        hand_weight.append(total)\n", "        hand_weight.append(total)\n        dominant.append(max(((g.weight, names[g.group]) for g in v.groups), default=(0, None))[1])\n")
patch('''    examples = [{"meshes": [tri_mesh[a], tri_mesh[b]], "at": [round(c, 4) for c in sum((points[i] for i in tris[a]), Vector()) / 3]} for a, b in (hand_self + hand_other_new)[:5]]''',
      '''    examples = [{"meshes": [tri_mesh[a], tri_mesh[b]], "bones": [sorted({dominant[i] for i in tris[a]}), sorted({dominant[i] for i in tris[b]})],
                 "at": [round(c, 4) for c in sum((points[i] for i in tris[a]), Vector()) / 3]} for a, b in (hand_self + hand_other_new)[:8]]''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
