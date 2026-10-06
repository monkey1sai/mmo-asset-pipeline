"""Tooling for faster iteration inside candidate v001 (reporting and options only; no gate changes).

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-tools-2-used.py
- cv1_joint_range.py: --only <ids> for partial diagnostic runs (flagged partial, never a gate pass) and examples of
  new intersections away from the hands.
- cv1_v001_assemble.py: --rigid-core makes the three vertices of a folding core triangle share one weight set,
  a three-vertex alternative to regional smoothing.
- cv1_hand_correctives.py: the fist residual also restores a minimum area to triangles that fold flat.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:70])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_joint_range.py", [
    ('parser.add_argument("--no-render", action="store_true")',
     'parser.add_argument("--no-render", action="store_true")' + NL + 'parser.add_argument("--only", help="comma-separated motion ids; diagnostic run, never a gate pass")'),
    ('results, neutral_tiles = [], {}' + NL + 'for motion in contract["motions"]:',
     'results, neutral_tiles = [], {}' + NL + 'only = set(args.only.split(",")) if args.only else None' + NL + 'for motion in contract["motions"]:' + NL
     + '    if only is not None and motion["id"] not in only:' + NL + '        continue'),
    ('''    hand_other_new = [p for p in hand_other if p not in rest_pairs]''',
     '''    hand_other_new = [p for p in hand_other if p not in rest_pairs]
    other_new = [p for p in other if p not in rest_pairs]'''),
    ('''"other_pairs": len(other), "other_new_pairs": sum(1 for p in other if p not in rest_pairs),''',
     '''"other_pairs": len(other), "other_new_pairs": len(other_new),
            "other_new_examples": [{"meshes": [tri_mesh[a], tri_mesh[b]], "at": [round(c, 4) for c in sum((points[i] for i in tris[a]), Vector()) / 3]} for a, b in other_new[:4]],'''),
    ('''    "calibration_run": ceilings is None,''', '''    "calibration_run": ceilings is None, "partial_run": sorted(only) if only is not None else None,'''),
    ('''    "numeric_gate_pass": all(r["pass"] for r in results) and all(rest_gate.values()),''',
     '''    "numeric_gate_pass": only is None and all(r["pass"] for r in results) and all(rest_gate.values()),'''),
])
patch("scripts/cv1_v001_assemble.py", [
    ('parser.add_argument("--relax-radius-mm", type=float, default=35.0)',
     'parser.add_argument("--relax-radius-mm", type=float, default=35.0)' + NL
     + 'parser.add_argument("--rigid-core", help="x,y,z;x,y,z rest centroids of core triangles whose three vertices get one shared weight set")'),
    ('''# ---- toes: the front of each boot follows the toe bone''',
     '''# ---- single folding triangles: give the three vertices one weight set so the triangle moves as a piece ----
rigid = {"applied": False}
if args.rigid_core:
    core.data.calc_loop_triangles()
    group_count = len(core.vertex_groups)
    sites = []
    for item in args.rigid_core.split(";"):
        centre = Vector(tuple(float(c) for c in item.split(",")))
        triangle = min(core.data.loop_triangles, key=lambda t: (t.center - centre).length)
        if (triangle.center - centre).length > 0.003:
            raise SystemExit(f"RIGID_CORE_TRIANGLE_NOT_FOUND {item}")
        mean = [0.0] * group_count
        for index in triangle.vertices:
            for g in core.data.vertices[index].groups:
                mean[g.group] += g.weight / 3
        top = sorted(range(group_count), key=lambda g: -mean[g])[:4]
        total = sum(mean[g] for g in top)
        for index in triangle.vertices:
            for g in range(group_count):
                if g in top and mean[g] / total > 1e-4:
                    core.vertex_groups[g].add([index], mean[g] / total, "REPLACE")
                else:
                    core.vertex_groups[g].remove([index])
        sites.append({"centre": [round(c, 4) for c in centre], "vertices": list(triangle.vertices)})
    rigid = {"applied": True, "sites": sites}

# ---- toes: the front of each boot follows the toe bone'''),
    ('"left_bracer": left_bracer, "core_relax": relax,', '"left_bracer": left_bracer, "core_relax": relax, "core_rigid_triangles": rigid,'),
])
patch("scripts/cv1_hand_correctives.py", [
    ('''relaxed, before, after = relax(points, region)
matrices = skin_matrices()
fist_key = right.shape_key_add(name="SKC_fist.R", from_mix=False)''',
     '''relaxed, before, after = relax(points, region)
# Triangles that fold flat at the full fist get a minimum area back: the vertex opposite the longest edge moves away from that edge.
rest_area = [(basis[b] - basis[a]).cross(basis[c] - basis[a]).length / 2 for a, b, c in tris]
area_fixed = set()
for _ in range(40):
    flat = [k for k, (a, b, c) in enumerate(tris) if rest_area[k] > 1e-10 and (relaxed[b] - relaxed[a]).cross(relaxed[c] - relaxed[a]).length / 2 < 0.10 * rest_area[k]]
    if not flat:
        break
    for k in flat:
        corners = list(tris[k])
        base = list(max(((corners[i], corners[j]) for i in range(3) for j in range(i + 1, 3)), key=lambda e: (relaxed[e[0]] - relaxed[e[1]]).length))
        apex = next(v for v in corners if v not in base)
        edge = (relaxed[base[1]] - relaxed[base[0]]).normalized()
        offset = relaxed[apex] - relaxed[base[0]]
        away = offset - edge * offset.dot(edge)
        if away.length < 1e-7:
            away = (basis[apex] - basis[base[0]]) - (basis[base[1]] - basis[base[0]]).normalized() * (basis[apex] - basis[base[0]]).dot((basis[base[1]] - basis[base[0]]).normalized())
        relaxed[apex] += away.normalized() * 0.0002
        area_fixed.add(k)
region |= {v for k in area_fixed for v in tris[k]}
matrices = skin_matrices()
fist_key = right.shape_key_add(name="SKC_fist.R", from_mix=False)'''),
    ('''stage3 = {"vertices_moved": moved,''', '''stage3 = {"vertices_moved": moved, "flat_triangles_given_area": len(area_fixed),'''),
])
print("patched")
