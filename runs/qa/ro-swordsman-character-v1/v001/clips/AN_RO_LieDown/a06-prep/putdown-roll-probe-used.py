"""Probe (report only): at the put-down frame of a LieDown draft, the sword at its bed-socket place and blade direction
with different rolls about the blade; for each roll and swivel, the hinge arm solve (flexion, pronation, wrist split,
humeral turn) and the lowest point of the right glove and hand skin over the bed footprint against the bed top. Skinning only; nothing saved.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python putdown-roll-probe-used.py -- \
       <action .blend> <frame> <grip x,y,z> <blade x,y,z> <rolls comma> <swivels comma> <contract.json> <out.json>
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world, swing_twist
from cv1_contract_pose import ContractPoser

action_blend, frame, grip, blade, rolls, swivels, contract_path, out = sys.argv[sys.argv.index("--") + 1:]
grip = Vector([float(c) for c in grip.split(",")])
blade = Vector([float(c) for c in blade.split(",")]).normalized()
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = ["AN_RO_LieDown"]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(int(frame))
bpy.context.view_layer.update()
arm.animation_data.action = None
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
ik = ArmIK(arm, contract=contract)
hand_frame = ContractPoser(arm, contract).hands["R"]
hand0 = arm.data.bones["hand.R"].matrix_local.to_3x3()
palmar, radial = (hand0.inverted() @ hand_frame["palmar"]).normalized(), (hand0.inverted() @ hand_frame["radial"]).normalized()
saved = {n: (arm.pose.bones[n].rotation_quaternion.copy(), arm.pose.bones[n].location.copy()) for n in ("upper_arm.R", "lower_arm.R", "hand.R")}
meshes = [bpy.data.objects[n] for n in ("SM_RO_hand.R", "SM_RO_core", "SM_RO_bracer.R")]
groups = {m.name: {g.index: g.name for g in m.vertex_groups} for m in meshes}
HAND_PREFIX = ("hand.R", "finger", "thumb.R", "wrist_transition.R")


def hand_lowest():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    low = None
    for m in meshes:
        target = m.evaluated_get(depsgraph)
        mesh = target.to_mesh()
        for i, v in enumerate(mesh.vertices):
            src = m.data.vertices[i]
            if not src.groups:
                continue
            bone = groups[m.name][max(src.groups, key=lambda g: g.weight).group]
            if m.name == "SM_RO_core" and not (bone.startswith(HAND_PREFIX) and (".R" in bone)):
                continue
            if m.name == "SM_RO_bracer.R":
                continue
            p = target.matrix_world @ v.co
            if not (-1.0 <= p.x <= 1.0 and 0.20 <= p.y <= 1.10):
                continue  # only points over the bed footprint (bed centre (0, 0.65), 2.0 x 0.9) count against the bed top
            if low is None or p.z < low[0]:
                low = (p.z, m.name, bone)
        target.to_mesh_clear()
    return low


rows = []
for r in [float(x) for x in rolls.split(",")]:
    target = ik.hand_for_sword(sword_world(grip, blade, math.radians(r)))
    for s in [float(x) for x in swivels.split(",")]:
        for n, (q, loc) in saved.items():
            arm.pose.bones[n].rotation_quaternion, arm.pose.bones[n].location = q, loc
        bpy.context.view_layer.update()
        try:
            solved = ik.solve_hinge("R", target, s)
        except ValueError as error:
            rows.append({"roll": r, "swivel": s, "error": str(error)})
            continue
        lower = arm.pose.bones["lower_arm.R"].matrix.to_3x3()
        q = ((lower @ ik.hinge["R"]["hand"]).inverted() @ target.to_3x3()).to_quaternion()
        y = q @ Vector((0.0, 1.0, 0.0))
        low = hand_lowest() or (0.45 + 1.0, "none over the bed", "")
        rows.append({"roll": r, "swivel": s, "flexion": round(solved["flexion_deg"], 1), "pronation": round(solved["pronation_deg"], 1),
                     "wrist_flex": round(math.degrees(math.atan2(y.dot(palmar), y.y)), 1), "wrist_dev": round(math.degrees(math.atan2(y.dot(radial), y.y)), 1),
                     "humeral": round(solved["upper_twist_deg"], 1), "hand_lowest_above_top_mm": round((low[0] - 0.45) * 1e3, 1), "lowest_part": f"{low[1]}:{low[2]}"})
        print("CV1_PUTDOWN " + json.dumps(rows[-1]))
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
