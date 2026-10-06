"""Bind the armour the body mesh carries to the separate armour piece's bone, so both move together.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_bind_core_to_armor.py -- \
       --spec <bind-spec.json> --tag <name> --out-dir <assets dir of the candidate>
The generated body (core) still contains its own copy of the shoulder armour, embedded in the separate pauldron.
Pulling it in left visible gaps and crumpled faces (see v001/c02-fit-compare.png), so instead the embedded copy is
weighted to the pauldron's bone: a core vertex is part of the copy when a ray from the covered joint toward it meets
the armour no further than `beyond_mm` before the vertex and no closer than `ratio_start` of the vertex distance.
Its share of the armour bone ramps from 0 to 1 across that band, is smoothed over a few rings, and the rest of its
weights are scaled down. At most four influences are kept. Geometry, shape keys and UVs are unchanged.
The input BLEND is not modified; a new BLEND is written and existing outputs are refused.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--spec", required=True)
parser.add_argument("--tag", required=True)
parser.add_argument("--out-dir", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")
spec = json.loads((ROOT / args.spec).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
core = bpy.data.objects[spec.get("body", "SM_RO_core")]
assert core.matrix_world.is_identity
points = [v.co.copy() for v in core.data.vertices]
neighbours = [set() for _ in points]
for edge in core.data.edges:
    a, b = edge.vertices
    neighbours[a].add(b)
    neighbours[b].add(a)


def anchor(text):
    name, where = text.split(":")
    bone = bones[name]
    return bone.head_local.copy() if where == "head" else bone.tail_local.copy() if where == "tail" else bone.head_local.lerp(bone.tail_local, float(where))


def closest_on_polyline(polyline, p):
    best = None
    for a, b in zip(polyline, polyline[1:]):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)) if ab.length_squared > 0 else 0.0
        q = a + ab * t
        if best is None or (p - q).length < (p - best).length:
            best = q
    return best


report = []
for piece in spec["pieces"]:
    armour = bpy.data.objects[piece["armor"]]
    mesh = armour.data
    mesh.calc_loop_triangles()
    shell = [armour.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(shell, [tuple(t.vertices) for t in mesh.loop_triangles], all_triangles=True)
    low = Vector(tuple(min(p[i] for p in shell) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in shell) for i in range(3)))
    margin, beyond, start = piece["margin_mm"] / 1000, piece.get("beyond_mm", 0) / 1000, piece.get("ratio_start", 0)
    polyline = [anchor(text) for text in piece["axis"]]
    share = {}
    for index, p in enumerate(points):
        if any(p[i] < low[i] - margin or p[i] > high[i] + margin for i in range(3)):
            continue
        if "near_mm" in piece:
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
        weight = smooth((ratio - start) / (1.0 - start))
        if weight > 0:
            share[index] = weight
    for _ in range(piece.get("smoothing_iterations", 2)):
        grown = dict(share)
        for index in {n for i in share for n in neighbours[i]} | set(share):
            ring = [share.get(n, 0.0) for n in neighbours[index]]
            if ring:
                grown[index] = 0.5 * share.get(index, 0.0) + 0.5 * sum(ring) / len(ring)
        share = {i: w for i, w in grown.items() if w > 1e-3}
    group = core.vertex_groups.get(piece["bone"]) or core.vertex_groups.new(name=piece["bone"])
    names = [g.name for g in core.vertex_groups]
    for index, weight in share.items():
        vertex = core.data.vertices[index]
        current = {names[g.group]: g.weight for g in vertex.groups if g.weight > 0}
        total = sum(current.values()) or 1.0
        mixed = {name: w / total * (1 - weight) for name, w in current.items()}
        mixed[piece["bone"]] = mixed.get(piece["bone"], 0.0) + weight
        kept = dict(sorted(mixed.items(), key=lambda item: -item[1])[:4])
        norm = sum(kept.values())
        for name in current:
            if name not in kept:
                core.vertex_groups[name].remove([index])
        for name, w in kept.items():
            core.vertex_groups[name].add([index], w / norm, "REPLACE")
    values = sorted(share.values())
    report.append({"armor": piece["armor"], "bone": piece["bone"], "vertices_bound": len(share), "fully_bound": sum(1 for w in values if w > 0.99),
                   "share_median": round(values[len(values) // 2], 3) if values else 0})

out_dir.mkdir(parents=True)
blend = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "source": source, "source_sha256_after": sha(ROOT / source["path"]),
           "spec": {"path": args.spec, "sha256": sha(ROOT / args.spec)}, "output": {"path": blend.relative_to(ROOT).as_posix(), "sha256": sha(blend)},
           "pieces": report, "geometry_shape_keys_uv_unchanged": True}
(out_dir / "bind-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_BIND_CORE " + json.dumps(report))
