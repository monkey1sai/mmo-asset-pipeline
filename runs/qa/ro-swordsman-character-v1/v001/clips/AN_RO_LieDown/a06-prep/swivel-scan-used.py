"""Hinge-solver swivel scan at chosen LieDown frames (report only; nothing is saved).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python swivel-scan-used.py -- \
       <action .blend> <spec.json> <frames comma list> <out.json>
The action (authored from the spec) gives the body pose at each frame (spine, clavicle and pelvis are FK, so the
shoulder does not depend on the arm solve); the hand target is rebuilt from the spec's sword keys the way
scripts/cv1_author_clip.py builds it. For every swivel from -150 to 150 degrees: hinge flexion, pronation, wrist swing,
the elbow point, the humeral turn (upper arm about its own axis against rest), and the wrist swing split into flexion (+palmar / -dorsal) and deviation (+radial / -ulnar) in the
contract hand frame (scripts/cv1_contract_pose.py).
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world, swing_twist
from cv1_contract_pose import ContractPoser

action_blend, spec_path, frames, out, contract_path = sys.argv[sys.argv.index("--") + 1:]
spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [spec["clip"]]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
ik = ArmIK(arm)
hand_frame = ContractPoser(arm, json.loads(Path(contract_path).read_text(encoding="utf-8"))).hands["R"]
hand0 = arm.data.bones["hand.R"].matrix_local.to_3x3()
palmar, radial = (hand0.inverted() @ hand_frame["palmar"]).normalized(), (hand0.inverted() @ hand_frame["radial"]).normalized()


def wrist_split(lower, target):
    """Tilt of the hand axis against the forearm-carried rest hand: flexion toward palmar, deviation toward radial."""
    q = ((lower @ ik.hinge["R"]["hand"]).inverted() @ target.to_3x3()).to_quaternion()
    y = q @ Vector((0.0, 1.0, 0.0))
    return math.degrees(math.atan2(y.dot(palmar), y.y)), math.degrees(math.atan2(y.dot(radial), y.y))


def keyed(keys, f):
    keys = sorted(keys, key=lambda k: k[0])
    if f <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0)
            s = t * t * (3 - 2 * t)
            return [a + (b - a) * s for a, b in zip(v0, v1)] if isinstance(v0, list) else v0 + (v1 - v0) * s
    return keys[-1][1]


def value(v, f):
    return v if isinstance(v, (int, float, list)) else keyed(v["keys"], f)


sword = spec["sword"]
rows = []
for f in [int(x) for x in frames.split(",")]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    grip, blade = Vector(value(sword["grip"], f)), Vector(value(sword["blade"], f)).normalized()
    pitch = math.radians(value(sword.get("pitch_deg", 0.0), f))
    if pitch:
        blade = (Quaternion(blade.cross(Vector((0, 0, 1))).normalized(), pitch) @ blade).normalized()
    target = ik.hand_for_sword(sword_world(grip, blade, math.radians(value(sword["roll_deg"], f))))
    shoulder = ik.shoulder("R")
    scan = []
    for s in range(-180, 181, 15):
        try:
            upper, lower, theta = ik.hinge_frames("R", target, s, shoulder)
        except ValueError as error:
            scan.append({"swivel": s, "error": str(error)})
            continue
        rel = ik.hand_relation("R", lower, target)
        elbow = shoulder + upper @ ik.hinge["R"]["elbow"]
        flex, dev = wrist_split(lower, target)
        clavicle = arm.pose.bones["upper_arm.R"].parent
        rest_local = clavicle.bone.matrix_local.to_3x3().inverted() @ arm.data.bones["upper_arm.R"].matrix_local.to_3x3()
        humeral = math.degrees(swing_twist((rest_local.inverted() @ (clavicle.matrix.to_3x3().inverted() @ upper)).to_quaternion(), Vector((0.0, 1.0, 0.0)))[0])
        scan.append({"swivel": s, "flexion": round(math.degrees(theta), 1), "pronation": round(rel["pronation_deg"], 1),
                     "swing": round(rel["wrist_swing_deg"], 1), "wrist_flex": round(flex, 1), "wrist_dev": round(dev, 1), "humeral": round(humeral, 1),
                     "elbow_m": [round(c, 3) for c in elbow]})
    rows.append({"frame": f, "shoulder_m": [round(c, 3) for c in shoulder], "wrist_m": [round(c, 3) for c in target.translation],
                 "spec_swivel": value(sword["swivel_deg"], f), "scan": scan})
Path(out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8", newline="\n")
for r in rows:
    print("CV1_SCAN", r["frame"], r["shoulder_m"], r["wrist_m"], "spec", round(r["spec_swivel"], 1))
    for c in r["scan"]:
        print("   ", json.dumps(c))
