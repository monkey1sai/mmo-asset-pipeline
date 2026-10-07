"""Probe (report only): the coat triangles with the smallest area ratio (posed against rest) in a clip frame with the
coat lying key at a given weight, with each corner's rest position, key offset and evaluated normal, plus flips
(posed normal against the rest-normal agreement of neighbours is not computed; a flip here is a posed normal that
turned more than 90 degrees from the same triangle's normal at weight 0 in the same pose).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python worst-coat-tris-used.py -- \
       <action .blend> <action name> <frame> <key weight> <out.json>
Skinning and the coat key only (no other correctives), nothing saved.
"""
import json
import math
import sys
from pathlib import Path

import bpy

action_blend, action_name, frame, weight, out = sys.argv[sys.argv.index("--") + 1:]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [action_name]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(int(frame))
coat = bpy.data.objects["SM_RO_coat"]
key = coat.data.shape_keys.key_blocks["SKC_coat_lying"]
basis = coat.data.shape_keys.key_blocks["Basis"]
coat.data.calc_loop_triangles()
tris = [tuple(t.vertices) for t in coat.data.loop_triangles]
rest = [v.co.copy() for v in coat.data.vertices]


def evaluated(value):
    key.value = value
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = coat.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    points = [target.matrix_world @ v.co for v in mesh.vertices]
    target.to_mesh_clear()
    return points


def normal(points, t):
    a, b, c = (points[k] for k in t)
    return (b - a).cross(c - a)


plain, keyed = evaluated(0.0), evaluated(float(weight))
rows, flips = [], []
for k, t in enumerate(tris):
    rest_area = normal(rest, t).length / 2
    if rest_area < 1e-10:
        continue
    ratio = normal(keyed, t).length / 2 / rest_area
    n0, n1 = normal(plain, t), normal(keyed, t)
    if n0.length > 1e-12 and n1.length > 1e-12 and n0.normalized().dot(n1.normalized()) < 0:
        flips.append(k)
    rows.append((ratio, k))
rows.sort()
report = {"frame": int(frame), "weight": float(weight), "flipped_vs_weight0": len(flips), "worst": []}
for ratio, k in rows[:12]:
    t = tris[k]
    report["worst"].append({"triangle": k, "ratio": round(ratio, 4), "corners": [
        {"vertex": i, "rest_m": [round(c, 4) for c in rest[i]], "key_offset_mm": [round(c * 1e3, 1) for c in (key.data[i].co - basis.data[i].co)],
         "posed_m": [round(c, 4) for c in keyed[i]]} for i in t]})
report["flipped_examples"] = [{"triangle": k, "rest_centre_m": [round(sum(rest[i][c] for i in tris[k]) / 3, 4) for c in range(3)],
                               "key_offset_y_mm": [round((key.data[i].co.y - basis.data[i].co.y) * 1e3, 1) for i in tris[k]]} for k in flips[:40]]
Path(out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_WORST " + json.dumps({"flipped": len(flips), "ratios": [r["ratio"] for r in report["worst"]]}))
