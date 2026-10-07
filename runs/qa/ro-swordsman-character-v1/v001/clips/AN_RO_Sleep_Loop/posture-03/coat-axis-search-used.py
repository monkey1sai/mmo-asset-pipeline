"""Search (report only): in the Sleep a02 frame-0 pose, extra rotations of one coat tail about many axes through its
bone head (bone-local axis directions on a sphere grid, several angles). For each: the lowest point of that tail, the
lowest of that side's pelvis-support vertices (they carry about 0.4 coat weight), and the tail's lowest world Y (the
sword lies at y 0.32 on the left). Skinning only, nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-axis-search-used.py -- \
       <action .blend> <contact-fixtures.json> <side L|R> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

action_blend, fixtures_path, side, out = sys.argv[sys.argv.index("--") + 1:]
fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))["fixtures"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = ["AN_RO_Sleep_Loop"]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
arm.animation_data.action = None
coat = bpy.data.objects["SM_RO_coat"]
groups = {g.index: g.name for g in coat.vertex_groups}
dominant = [groups[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in coat.data.vertices]
tail_ids = [i for i, b in enumerate(dominant) if b == f"coat.{side}"]
pelvis_ids = [i for i in fixtures["bed_support.pelvis"]["ids"]["SM_RO_coat"] if any(groups[g.group] == f"coat.{side}" for g in coat.data.vertices[i].groups)]
pb = arm.pose.bones[f"coat.{side}"]
base = pb.rotation_quaternion.copy()


def measure():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = coat.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    pts = [target.matrix_world @ v.co for v in mesh.vertices]
    target.to_mesh_clear()
    tail = [pts[i] for i in tail_ids]
    return {"tail_low_mm": round(min(p.z for p in tail) * 1e3, 1), "pelvis_low_mm": round(min(pts[i].z for i in pelvis_ids) * 1e3, 1),
            "tail_min_y": round(min(p.y for p in tail), 3), "tail_max_y": round(max(p.y for p in tail), 3)}


reference = measure()
rows = []
directions = []
for i in range(-2, 3):
    for j in range(-2, 3):
        for k in range(-2, 3):
            v = Vector((i, j, k))
            if v.length > 0 and math.gcd(math.gcd(abs(i), abs(j)), abs(k)) == 1:
                directions.append(v.normalized())
for axis in directions:
    for deg in (10, 20, 30, 40):
        pb.rotation_quaternion = base @ Quaternion(axis, math.radians(deg))
        bpy.context.view_layer.update()
        row = measure()
        row.update({"axis_local": [round(c, 3) for c in axis], "degrees": deg})
        rows.append(row)
pb.rotation_quaternion = base
feasible = [r for r in rows if abs(r["pelvis_low_mm"] - reference["pelvis_low_mm"]) <= 3.0]
feasible.sort(key=lambda r: -r["tail_low_mm"])
Path(out).write_text(json.dumps({"side": side, "reference": reference, "best_with_pelvis_within_3mm": feasible[:25], "rows": rows}, indent=1) + "\n",
                     encoding="utf-8", newline="\n")
print("CV1_COAT_SEARCH " + json.dumps({"side": side, "reference": reference, "top": feasible[:12]}))
