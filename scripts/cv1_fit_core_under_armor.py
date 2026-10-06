"""Pull the body mesh in under separate armour pieces, so the pieces can move without dragging embedded geometry.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_fit_core_under_armor.py -- \
       --spec <fit-spec.json> --tag <name> --out-dir <assets dir of the candidate>
For each armour piece, every core vertex near it is looked at from the closest point of a short bone polyline (the
joint the piece covers). If a ray from there toward the vertex meets the armour before reaching the vertex, the vertex
is pulled back along the ray to sit `clearance_mm` inside that first armour surface. Vertices whose ray misses the
armour are not moved, except for a short smoothing band around the moved region. Basis and every shape key move by the
same offset, so existing correctives keep their deltas. Weights, topology and UVs are unchanged.
The input BLEND is not modified; a new BLEND is written and existing outputs are refused.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import statistics
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


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
bones = arm.data.bones
core = bpy.data.objects[spec.get("body", "SM_RO_core")]
assert core.matrix_world.is_identity
basis = [v.co.copy() for v in core.data.vertices]
neighbours = [set() for _ in basis]
for edge in core.data.edges:
    a, b = edge.vertices
    neighbours[a].add(b)
    neighbours[b].add(a)


def point(text):
    name, where = text.split(":")
    bone = bones[name]
    if where == "head":
        return bone.head_local.copy()
    if where == "tail":
        return bone.tail_local.copy()
    return bone.head_local.lerp(bone.tail_local, float(where))


def closest_on_polyline(polyline, p):
    best = None
    for a, b in zip(polyline, polyline[1:]):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)) if ab.length_squared > 0 else 0.0
        q = a + ab * t
        if best is None or (p - q).length < (p - best).length:
            best = q
    return best


offsets, report = {}, []
for piece in spec["pieces"]:
    armour = bpy.data.objects[piece["armor"]]
    mesh = armour.data
    mesh.calc_loop_triangles()
    points = [armour.matrix_world @ v.co for v in mesh.vertices]
    tree = BVHTree.FromPolygons(points, [tuple(t.vertices) for t in mesh.loop_triangles], all_triangles=True)
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    margin = piece["margin_mm"] / 1000
    clearance = piece["clearance_mm"] / 1000
    polyline = [point(text) for text in piece["axis"]]
    moved = []
    for index, p in enumerate(basis):
        if any(p[i] < low[i] - margin or p[i] > high[i] + margin for i in range(3)):
            continue
        origin = closest_on_polyline(polyline, p)
        ray = p - origin
        if ray.length < 1e-6:
            continue
        hit, _, _, distance = tree.ray_cast(origin, ray.normalized(), ray.length + clearance)
        if hit is None:
            continue
        limit = max(distance - clearance, 0.0)
        if ray.length > limit:
            offset = ray.normalized() * (limit - ray.length)
            if index not in offsets or offset.length > offsets[index].length:
                offsets[index] = offset
            moved.append(offset.length)
    report.append({"armor": piece["armor"], "axis": piece["axis"], "clearance_mm": piece["clearance_mm"], "vertices_pulled": len(moved),
                   "pull_mm_median": round(statistics.median(moved) * 1e3, 2) if moved else 0, "pull_mm_max": round(max(moved) * 1e3, 2) if moved else 0})

# Smoothing band: vertices next to the pulled region take part of their neighbours' offset, fading out over a few rings.
pulled = set(offsets)
band, frontier = {}, set(pulled)
for ring in range(spec.get("smoothing_rings", 3)):
    frontier = {n for i in frontier for n in neighbours[i]} - pulled - set(band)
    for index in frontier:
        near = [offsets.get(n, band.get(n)) for n in neighbours[index] if n in offsets or n in band]
        if near:
            band[index] = sum(near, Vector()) / len(near) * spec.get("smoothing_falloff", 0.5)
offsets.update(band)

keys = core.data.shape_keys.key_blocks if core.data.shape_keys else []
for index, offset in offsets.items():
    core.data.vertices[index].co = basis[index] + offset
    for key in keys:
        key.data[index].co = key.data[index].co + offset
core.data.update()
out_dir.mkdir(parents=True)
blend = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "source": source, "source_sha256_after": sha(ROOT / source["path"]),
           "spec": {"path": args.spec, "sha256": sha(ROOT / args.spec)}, "output": {"path": blend.relative_to(ROOT).as_posix(), "sha256": sha(blend)},
           "pieces": report, "vertices_pulled": len(pulled), "smoothing_band_vertices": len(band),
           "basis_and_keys_moved_together": True, "weights_topology_uv_unchanged": True,
           "scope": "Geometry under the armour only; whatever the armour exposes when it moves is now a fitted body surface carrying the old texture."}
(out_dir / "fit-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_FIT_CORE " + json.dumps({"pieces": report, "band": len(band)}))
