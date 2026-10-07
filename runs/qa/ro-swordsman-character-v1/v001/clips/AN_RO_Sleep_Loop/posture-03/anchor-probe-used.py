"""Probe (report only): in the Sleep a02 frame-0 pose, turn each coat tail about the axis from its bone head through
the centroid of that side's pelvis-support vertices (rest positions), so those vertices stay put while the flare
lifts; also the ankle dorsiflexion sweep with the heel and boot points. Skinning only, nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python anchor-probe-used.py -- \
       <action .blend> <contact-fixtures.json> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

action_blend, fixtures_path, out = sys.argv[sys.argv.index("--") + 1:]
fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))["fixtures"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = ["AN_RO_Sleep_Loop"]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
arm.animation_data.action = None
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers) and o.name != "SM_RO_sword"]
coat = bpy.data.objects["SM_RO_coat"]
groups = {g.index: g.name for g in coat.vertex_groups}


def dominant(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in obj.data.vertices]


DOM = {o.name: dominant(o) for o in skinned}
SETS = ("back", "pelvis", "head_back", "calf.L", "calf.R")
anchor = {}
for side in "LR":
    ids = [i for i in fixtures["bed_support.pelvis"]["ids"]["SM_RO_coat"] if any(groups[g.group] == f"coat.{side}" for g in coat.data.vertices[i].groups)]
    anchor[side] = sum((coat.data.vertices[i].co for i in ids), Vector()) / len(ids)
bones = arm.data.bones
axis_local = {side: (bones[f"coat.{side}"].matrix_local.to_3x3().inverted() @ (anchor[side] - bones[f"coat.{side}"].head_local)).normalized() for side in "LR"}


def measure():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = {}
    for obj in skinned:
        target = obj.evaluated_get(depsgraph)
        mesh = target.to_mesh()
        pts[obj.name] = [target.matrix_world @ v.co for v in mesh.vertices]
        target.to_mesh_clear()
    row = {k: min(pts[m][i].z for m, ids in fixtures[f"bed_support.{k}"]["ids"].items() for i in ids) for k in SETS}
    for side in "LR":
        coat_pts = [pts["SM_RO_coat"][i] for i, b in enumerate(DOM["SM_RO_coat"]) if b == f"coat.{side}"]
        low = min(coat_pts, key=lambda p: p.z)
        row[f"coat.{side}"] = low.z
        row[f"coat.{side}_lowest_at"] = [round(c, 3) for c in low]
        row[f"coat.{side}_y_range"] = [round(min(p.y for p in coat_pts), 3), round(max(p.y for p in coat_pts), 3)]
        row[f"foot.{side}"] = min(p.z for m in pts for i, p in enumerate(pts[m]) if DOM[m][i] in (f"foot.{side}", f"toe.{side}"))
    return {k: (round(v * 1e3, 1) if isinstance(v, float) else v) for k, v in row.items()}


base = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}
rows = {"anchor_rest_m": {s: [round(c, 4) for c in anchor[s]] for s in "LR"}, "axis_local": {s: [round(c, 4) for c in axis_local[s]] for s in "LR"}, "coat_about_anchor": []}
for deg in (-40, -30, -20, -10, 0, 10, 20, 30, 40, 50):
    for side in "LR":
        signed = deg if side == "L" else -deg  # mirror
        arm.pose.bones[f"coat.{side}"].rotation_quaternion = base[f"coat.{side}"] @ Quaternion(axis_local[side], math.radians(signed))
    bpy.context.view_layer.update()
    rows["coat_about_anchor"].append(dict(measure(), degrees_L=deg, degrees_R=-deg))
    print("CV1_ANCHOR " + json.dumps(rows["coat_about_anchor"][-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
