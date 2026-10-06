"""Diagnostic (report only): is the right elbow a hinge in these clips? lower_arm.R rest-relative local rotation split into
twist about the forearm axis and swing; the swing axis is compared with the contract flexion axis (body right, in the
lower arm's rest frame). Same for the knees (flexion axis: body left, contract knee-flexion)."""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector
ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
contract = json.loads((ROOT / "runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json").read_text(encoding="utf-8"))
axes = {k: Vector(v) for k, v in contract["axes"].items()}
B = arm.data.bones
def rel(name):
    pb = arm.pose.bones[name]
    rest_local = B[name].parent.matrix_local.inverted() @ B[name].matrix_local
    local = pb.parent.matrix.inverted() @ pb.matrix
    return (rest_local.inverted() @ local).to_quaternion()
def split(q, axis):  # swing-twist about axis (unit, local)
    p = Vector((q.x, q.y, q.z)); proj = axis * p.dot(axis)
    twist = Quaternion((q.w, proj.x, proj.y, proj.z)).normalized()
    swing = q @ twist.inverted()
    return twist, swing
def hinge_report(bone, flex_world_axis):
    q = rel(bone)
    along = Vector((0, 1, 0))
    twist, swing = split(q, along)
    tw = math.degrees(2 * math.atan2(Vector((twist.x, twist.y, twist.z)).length, twist.w)); tw = tw - 360 if tw > 180 else tw
    hinge_local = (B[bone].matrix_local.to_3x3().inverted() @ flex_world_axis).normalized()
    sw_angle = math.degrees(swing.angle)
    sw_axis = Vector((swing.x, swing.y, swing.z))
    off = None if sw_axis.length < 1e-6 or sw_angle < 2 else math.degrees(min(sw_axis.normalized().angle(hinge_local), sw_axis.normalized().angle(-hinge_local)))
    return {"bend_deg": round(sw_angle, 1), "twist_deg": round(tw, 1), "bend_axis_off_hinge_deg": None if off is None else round(off, 1)}
rows = []
for clip, att, times in (("AN_RO_LieDown", "a05", (30, 34, 36, 38, 39, 40, 41, 42, 44, 46)), ("AN_RO_Cast_OpenPalm", "a04", (0, 20, 34)), ("AN_RO_Idle_Sword", "a03", (0, 60))):
    with bpy.data.libraries.load(str(ROOT / f"assets/processed/ro-swordsman-character-v1/v001/clips/{clip}/{att}/{clip}.blend"), link=False) as (s, d):
        d.actions = [clip]
    arm.animation_data_create(); arm.animation_data.action = bpy.data.actions[clip]
    for t in times:
        bpy.context.scene.frame_set(int(t)); bpy.context.view_layer.update()
        row = {"clip": clip, "t": t, "elbow_R": hinge_report("lower_arm.R", -axes["left"]), "elbow_L": hinge_report("lower_arm.L", -axes["left"])}
        if clip == "AN_RO_LieDown":
            row["knee_L"] = hinge_report("lower_leg.L", axes["left"]); row["knee_R"] = hinge_report("lower_leg.R", axes["left"])
        rows.append(row); print("HINGE " + json.dumps(row))
Path(sys.argv[sys.argv.index("--") + 1]).write_text(json.dumps(rows, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
