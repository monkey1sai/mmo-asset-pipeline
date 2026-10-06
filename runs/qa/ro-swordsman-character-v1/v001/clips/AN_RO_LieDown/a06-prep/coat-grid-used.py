"""Probe (report only): at one clip frame, a grid of extra coat-tail steps (swing toward back, then toward out) on one
tail; for each pair, the lowest point of that tail's vertices over the bed footprint and where it is (rest position).
Evaluation as scripts/cv1_clip_check.py (action, socket, helpers, states, correctives); nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-grid-used.py -- \
       <action .blend> <interaction.json> <rules.json> <contract.json> <frame> <side L|R> <back degs> <out degs> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser

action_blend, interaction_path, rules_path, contract_path, frame, side, backs, outs, out = sys.argv[sys.argv.index("--") + 1:]
config = interaction.load(Path(interaction_path))
rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
bed = config["bed"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
poser = ContractPoser(arm, contract, {})
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [config["clip"]]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
t = float(frame)
bpy.context.scene.frame_set(math.floor(t), subframe=t - math.floor(t))
bpy.context.view_layer.update()
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


pose = pose_rel()
for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
    arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
bpy.context.view_layer.update()
arm.animation_data.action = None
coat = bpy.data.objects["SM_RO_coat"]
names = {g.index: g.name for g in coat.vertex_groups}
dominant = [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in coat.data.vertices]
cx, cy = bed["centre_m"]
half_l, half_w, top = bed["size_m"][0] / 2, bed["size_m"][1] / 2, bed["top_z_m"]
pb = arm.pose.bones[f"coat.{side}"]
base = pb.rotation_quaternion.copy()
rows = []
for b in [float(x) for x in backs.split(",")]:
    for o in [float(x) for x in outs.split(",")]:
        pb.rotation_quaternion = base @ poser.step_rotation({"bone": pb.name, "kind": "swing", "toward": "back", "degrees": b}, side, 1.0) \
            @ poser.step_rotation({"bone": pb.name, "kind": "swing", "toward": "out", "degrees": o}, side, 1.0)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        target = coat.evaluated_get(depsgraph)
        mesh = target.to_mesh()
        low = None
        for i, v in enumerate(mesh.vertices):
            if dominant[i] != pb.name:
                continue
            p = target.matrix_world @ v.co
            if abs(p.x - cx) <= half_l and abs(p.y - cy) <= half_w and (low is None or p.z < low[0]):
                low = (p.z, i)
        target.to_mesh_clear()
        rows.append({"back": b, "out": o, "lowest_above_top_mm": None if low is None else round((low[0] - top) * 1e3, 1),
                     "rest_m": None if low is None else [round(c, 3) for c in coat.data.vertices[low[1]].co]})
        print("CV1_GRID " + json.dumps(rows[-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
