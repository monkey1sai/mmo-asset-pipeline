"""Probe (report only): where the lowest foot point is in the Sleep a02 frame-0 pose, and how it moves when the foot
swings toward up (dorsiflexion, contract direction) or down, with the leg pose unchanged.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python foot-probe-used.py -- <action .blend> <out.json>
The lowest point of every vertex whose dominant bone is foot.X or toe.X is reported in world space and in the foot
bone's rest frame (its offset from the ankle along the foot, across it, and along the rest up axis).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
action_blend, out = sys.argv[sys.argv.index("--") + 1:]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = ["AN_RO_Sleep_Loop"]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
arm.animation_data.action = None  # keep the evaluated frame-0 pose as the pose-bone values
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers) and o.name != "SM_RO_sword"]


def dominant(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in obj.data.vertices]


DOM = {o.name: dominant(o) for o in skinned}
rows = []
base = {side: arm.pose.bones[f"foot.{side}"].rotation_quaternion.copy() for side in "LR"}
for side in "LR":
    bone = arm.data.bones[f"foot.{side}"]
    axis_local = bone.matrix_local.to_3x3().inverted() @ (bone.tail_local - bone.head_local).normalized().cross(Vector((0, 0, 1))).normalized()
    for deg in (-30, -20, -10, 0, 10, 20, 25):
        pb = arm.pose.bones[f"foot.{side}"]
        pb.rotation_quaternion = base[side] @ Quaternion(axis_local, math.radians(deg))
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        low = None
        for obj in skinned:
            target = obj.evaluated_get(depsgraph)
            mesh = target.to_mesh()
            for i, v in enumerate(mesh.vertices):
                if DOM[obj.name][i] in (f"foot.{side}", f"toe.{side}"):
                    p = target.matrix_world @ v.co
                    if low is None or p.z < low[0].z:
                        low = (p, obj.name, i, DOM[obj.name][i])
            target.to_mesh_clear()
        p = low[0]
        rest = bone.matrix_local.inverted() @ (arm.matrix_world.inverted() @ p)  # in the foot's rest frame, if the foot were at rest
        posed = arm.pose.bones[f"foot.{side}"].matrix.inverted() @ (arm.matrix_world.inverted() @ p)
        rows.append({"side": side, "swing_up_deg": deg, "lowest_z_m": round(p.z, 4), "mesh": low[1], "vertex": low[2], "dominant": low[3],
                     "in_posed_foot_frame_m": [round(c, 4) for c in posed]})
        pb.rotation_quaternion = base[side]
        bpy.context.view_layer.update()
        print("CV1_FOOT " + json.dumps(rows[-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
