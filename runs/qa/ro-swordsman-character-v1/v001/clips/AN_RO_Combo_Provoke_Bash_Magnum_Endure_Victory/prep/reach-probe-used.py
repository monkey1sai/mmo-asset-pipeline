"""Reach probe for a keyed clip spec (Blender side, diagnostic only; nothing is saved).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python reach-probe-used.py -- <spec.json> <contract.json> <poses.json> <out.json>
For every frame: the FK pose of the spec (named poses, pelvis block, steps; no IK), the right shoulder, the sword IK wrist target
(scripts/cv1_arm_ik.py: hand_for_sword of sword_world(grip, blade+pitch, roll)), the shoulder-wrist distance against the arm length,
and the hip-ankle distances of the leg IK targets against the leg length. Frames over the limits are listed first.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, LegIK, sword_world  # noqa: E402
from cv1_contract_pose import ContractPoser  # noqa: E402

spec_path, contract_path, poses_path, out_path = sys.argv[sys.argv.index("--") + 1:][:4]
spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
poses = json.loads(Path(poses_path).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser, ik, leg_ik = ContractPoser(arm, contract, poses), ArmIK(arm, contract=contract), LegIK(arm, reach=1.0)
frames, loop = int(spec["frames"]), spec.get("loop")


def keyed(keys, f):
    keys = sorted(keys, key=lambda x: x[0])
    if f <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0); s = t * t * (3 - 2 * t)
            return [a + (b - a) * s for a, b in zip(v0, v1)] if isinstance(v0, list) else v0 + (v1 - v0) * s
    return keys[-1][1]


def wave(value, f):
    if isinstance(value, (int, float)):
        return float(value)
    total = float(keyed(value["keys"], f)) if "keys" in value else float(value.get("base", 0.0))
    for amplitude, cycles, phase in value.get("waves", []):
        total += amplitude * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return total


def wave_vector(value, f):
    if isinstance(value, list):
        return Vector(value)
    out = Vector(keyed(value["keys"], f)) if "keys" in value else Vector(value["base"])
    for vector, cycles, phase in value.get("waves", []):
        out += Vector(vector) * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return out


WORLD_AXES = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
pelvis_head, pelvis_rest = arm.data.bones["pelvis"].head_local.copy(), arm.data.bones["pelvis"].matrix_local.to_3x3()
arm_length = sum((arm.data.bones[b].head_local - arm.data.bones[a].head_local).length for a, b in (("upper_arm.R", "lower_arm.R"), ("lower_arm.R", "hand.R")))
rows, over = [], []
for f in range(frames):
    poser.reset()
    for item in spec.get("poses", []):
        name, w = (item, 1.0) if isinstance(item, str) else (item["name"], wave(item["weight"], f))
        for bone, q in poses[name].items():
            arm.pose.bones[bone].rotation_quaternion = Quaternion(q) if w >= 1.0 else Quaternion().slerp(Quaternion(q), w)
    if spec.get("pelvis"):
        turn = Quaternion()
        for item in spec["pelvis"].get("rotation", []):
            turn = Quaternion(WORLD_AXES[item["axis"]], math.radians(wave(item["degrees"], f))) @ turn
        place = wave_vector(spec["pelvis"]["location_m"], f) if "location_m" in spec["pelvis"] else pelvis_head
        pb = arm.pose.bones["pelvis"]; pb.rotation_mode = "QUATERNION"
        pb.matrix = Matrix.Translation(place) @ (turn.to_matrix() @ pelvis_rest).to_4x4()
    bpy.context.view_layer.update()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=wave(step["degrees"], f)), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    row = {"frame": f}
    sword = spec.get("sword")
    if sword and wave(sword.get("ik_weight", 1.0), f) > 0:
        grip, blade = wave_vector(sword["grip"], f), wave_vector(sword["blade"], f).normalized()
        pitch = math.radians(wave(sword.get("pitch_deg", 0.0), f))
        if pitch:
            blade = (Quaternion(blade.cross(Vector((0, 0, 1))).normalized(), pitch) @ blade).normalized()
        target = ik.hand_for_sword(sword_world(grip, blade, math.radians(wave(sword.get("roll_deg", 0.0), f))))
        shoulder = ik.shoulder("R")
        row.update({"shoulder": [round(c, 4) for c in shoulder], "grip": [round(c, 4) for c in grip], "wrist_target": [round(c, 4) for c in target.translation],
                    "grip_from_shoulder_m": round((grip - shoulder).length, 4), "wrist_from_shoulder_m": round((target.translation - shoulder).length, 4),
                    "arm_length_m": round(arm_length, 4)})
        if row["wrist_from_shoulder_m"] > arm_length * 0.995:
            over.append({"frame": f, "wrist_from_shoulder_m": row["wrist_from_shoulder_m"], "kind": "arm"})
    legs = spec.get("legs_ik")
    if legs and wave(legs["weight"], f) > 0:
        for side in "LR":
            ankle = wave_vector(legs[side]["ankle_m"], f)
            d = (ankle - leg_ik.hip(side)).length
            row[f"hip_ankle_{side}_m"] = round(d, 4)
            if d > leg_ik.max_length(side):
                over.append({"frame": f, "side": side, "hip_ankle_m": round(d, 4), "leg_length_m": round(leg_ik.max_length(side), 4), "kind": "leg"})
    rows.append(row)
Path(out_path).write_text(json.dumps({"spec": spec_path, "arm_length_m": arm_length, "leg_length_m": {s: leg_ik.max_length(s) for s in "LR"}, "over": over, "frames": rows},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_REACH_PROBE " + json.dumps({"frames": frames, "over": len(over), "first": over[:6]}))
