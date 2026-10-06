"""Probe (report only): in the Sleep a02 frame-0 pose, how the support sets and the coat tails move when both coat
tails swing toward forward (contract direction, on top of the pose), and how the feet move with knee flexion
(lower_leg twist about left, contract direction). Skinning only (no correctives), nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python coat-probe-used.py -- \
       <action .blend> <contact-fixtures.json> <contract.json> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_contract_pose import ContractPoser

action_blend, fixtures_path, contract_path, out = sys.argv[sys.argv.index("--") + 1:]
fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))["fixtures"]
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {})
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = ["AN_RO_Sleep_Loop"]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
arm.animation_data.action = None
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers) and o.name != "SM_RO_sword"]


def dominant(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in obj.data.vertices]


DOM = {o.name: dominant(o) for o in skinned}
SETS = ("back", "pelvis", "head_back", "calf.L", "calf.R")
pelvis_set_weights = []
coat = bpy.data.objects["SM_RO_coat"]
groups = {g.index: g.name for g in coat.vertex_groups}
for i in fixtures["bed_support.pelvis"]["ids"].get("SM_RO_coat", []):
    pelvis_set_weights.append({groups[g.group]: round(g.weight, 3) for g in coat.data.vertices[i].groups})


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
        row[f"coat.{side}"] = min(pts["SM_RO_coat"][i].z for i, b in enumerate(DOM["SM_RO_coat"]) if b == f"coat.{side}")
        row[f"foot.{side}"] = min(p.z for m in pts for i, p in enumerate(pts[m]) if DOM[m][i] in (f"foot.{side}", f"toe.{side}"))
    return {k: round(v * 1e3, 1) for k, v in row.items()}


base = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}
rows = {"pelvis_set_weights": pelvis_set_weights, "coat_forward": [], "knee_flexion": []}
for deg in (0, 5, 10, 15, 20, 25, 30):
    for side in "LR":
        pb = arm.pose.bones[f"coat.{side}"]
        pb.rotation_quaternion = base[pb.name] @ poser.step_rotation({"bone": f"coat.{side}", "kind": "swing", "toward": "forward", "degrees": deg}, side, 1.0)
    bpy.context.view_layer.update()
    rows["coat_forward"].append(dict(measure(), degrees=deg))
    print("CV1_COAT " + json.dumps(rows["coat_forward"][-1]))
for side in "LR":
    arm.pose.bones[f"coat.{side}"].rotation_quaternion = base[f"coat.{side}"]
for deg in (0, 2, 4, 6, 8, 10):
    for side in "LR":
        pb = arm.pose.bones[f"lower_leg.{side}"]
        pb.rotation_quaternion = base[pb.name] @ poser.step_rotation({"bone": f"lower_leg.{side}", "kind": "twist", "about": "left", "degrees": deg}, side, 1.0)
    bpy.context.view_layer.update()
    rows["knee_flexion"].append(dict(measure(), degrees=deg))
    print("CV1_KNEE " + json.dumps(rows["knee_flexion"][-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_PELVIS_SET_WEIGHTS " + json.dumps(pelvis_set_weights))
