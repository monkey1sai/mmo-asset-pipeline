"""Solve a supine posture on the bed proxy so the five bed-support sets rest on its top plane (Blender side).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_bed_posture.py -- \
       --contract <joint-range-contract.json> --rules <rules.json> --fixtures <contact-fixtures.json> \
       --base <base.json> --out <new result.json>
--base holds the fixed part of the pose: {"steps": [...]} (contract step vocabulary, e.g. relaxed fingers) and
optionally {"rest_hands_on_bed": true}, {"arm_includes_forearm": true}, {"pelvis_tilt_deg": t} and
{"feet": {"dorsiflexion_deg": d or {"L": dl, "R": dr}, "heel_allowance_m": a}}. The body lies on its back (pelvis turned -90 degrees about
world X, head towards +Y; pelvis_tilt_deg adds a posterior tilt, i.e. a further -t about X, which lifts the coat tails
hanging from the pelvis); then, repeated until stable, bisection solves in order
  spine_02 swing toward back  -> the back set level with the pelvis set,
  neck and head swing toward back (half each) -> the back-of-head set level with the pelvis set,
  each upper leg swing toward back -> that calf set level with the pelvis set (with "feet": the lower of the calf set
             and the lowest foot point raised by heel_allowance_m, each foot dorsiflexed by the fixed angle first),
  (rest_hands_on_bed) each upper arm twist about right -> the lowest hand point 3 mm above the pelvis set (with
             arm_includes_forearm: the lowest point below the elbow, i.e. every vertex whose dominant bone is the lower
             arm, hand, wrist, thumb or fingers of that side, bracer and glove included);
then the pelvis height puts the lowest support point 1 mm above the bed top. Positions come from the evaluated mesh
with helpers and corrective morphs as in scripts/cv1_clip_check.py (interaction states zero: no grasp while lying).
The result also reports the lowest point of the whole body (every skinned mesh but the sword) and its dominant bone.
The posture is relative to the pelvis; bed placement and body yaw are per-clip setup. The BLEND is never saved.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser

parser = argparse.ArgumentParser()
for name in ("--contract", "--rules", "--fixtures", "--base", "--out"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_path = (ROOT / args.out).resolve()
if out_path.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_path}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))["fixtures"]
base = json.loads((ROOT / args.base).read_text(encoding="utf-8"))
TOP = 0.45
SETS = ("back", "pelvis", "head_back", "calf.L", "calf.R")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, {})
bones = arm.data.bones
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
pelvis_head, pelvis_rest = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
SUPINE = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(-90.0 - float(base.get("pelvis_tilt_deg", 0.0))))
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
EXCLUDED = set(contract["limits"]["excluded_meshes"])


def dominant_bones(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in obj.data.vertices]


DOMINANT = {o.name: dominant_bones(o) for o in skinned if o.name not in EXCLUDED}


def part_points(side, part):
    """(mesh, vertex) pairs below the elbow of one arm, of one coat tail, or of one foot, by dominant bone."""
    def wanted(bone):
        if bone is None:
            return False
        if part == "arm":
            return bone.startswith((f"lower_arm.{side}", f"hand.{side}", f"wrist_transition.{side}", f"thumb.{side}")) or \
                (bone.startswith("finger") and bone.split(".")[1].startswith(side))
        if part == "coat":
            return bone == f"coat.{side}"
        return bone in (f"foot.{side}", f"toe.{side}")
    return [(mesh, i) for mesh, bones_of in DOMINANT.items() for i, bone in enumerate(bones_of) if wanted(bone)]


PARTS = {f"{part}.{side}": part_points(side, part) for side in ("L", "R") for part in ("arm", "coat", "foot")}


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def apply(angles, lift=0.0):
    """Rest -> supine pelvis (lifted by `lift` along Z) -> base steps -> solved steps -> helpers -> correctives."""
    poser.reset()
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0
    pb = arm.pose.bones["pelvis"]
    pb.rotation_mode = "QUATERNION"
    pb.matrix = Matrix.Translation(pelvis_head + Vector((0.0, 0.0, lift))) @ (SUPINE.to_matrix() @ pelvis_rest).to_4x4()
    bpy.context.view_layer.update()
    steps = list(base.get("steps", [])) + solved_steps(angles)
    for step in steps:
        bone = arm.pose.bones[step["bone"]]
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = bone.rotation_quaternion @ poser.step_rotation(step, step.get("side"), 1.0)
    bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    state = {d["key"]: 0.0 for d in rules["drivers"].values() if d["type"] == "state"}
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    return steps


def solved_steps(a):
    steps = [{"bone": "spine_02", "kind": "swing", "toward": "back", "degrees": a["spine"]},
             {"bone": "neck", "kind": "swing", "toward": "back", "degrees": a["head"] / 2},
             {"bone": "head", "kind": "swing", "toward": "back", "degrees": a["head"] / 2}]
    for side in ("L", "R"):
        steps.append({"bone": f"upper_leg.{side}", "kind": "swing", "toward": "back", "degrees": a[f"hip.{side}"], "side": side})
        if base.get("rest_hands_on_bed"):
            steps.append({"bone": f"upper_arm.{side}", "kind": "twist", "about": "right", "degrees": a[f"arm.{side}"], "side": side})
        if base.get("feet"):
            ankle = base["feet"]["dorsiflexion_deg"]
            steps.append({"bone": f"foot.{side}", "kind": "swing", "toward": "up", "degrees": ankle[side] if isinstance(ankle, dict) else ankle, "side": side})
    return steps


def lowest():
    """Lowest world Z of every support set and of each hand mesh."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cache = {}

    def points(mesh_name):
        if mesh_name not in cache:
            obj = bpy.data.objects[mesh_name]
            target = obj.evaluated_get(depsgraph)
            mesh = target.to_mesh()
            cache[mesh_name] = [target.matrix_world @ v.co for v in mesh.vertices]
            target.to_mesh_clear()
        return cache[mesh_name]

    out = {key: min(points(mesh)[i].z for mesh, ids in fixtures[f"bed_support.{key}"]["ids"].items() for i in ids) for key in SETS}
    for side in ("L", "R"):
        out[f"hand.{side}"] = min(p.z for p in points(f"SM_RO_hand.{side}"))
    for key, members in PARTS.items():
        out[key] = min(points(mesh)[i].z for mesh, i in members)
    low = min(((points(mesh)[i].z, mesh, bone) for mesh, bones_of in DOMINANT.items() for i, bone in enumerate(bones_of)), key=lambda x: x[0])
    out["body"], out["body_lowest"] = low[0], {"mesh": low[1], "dominant": low[2]}
    return out


def bisect(angles, key, measure, low, high, target=0.0, steps=26):
    """Find angles[key] in [low, high] with measure() == target; measure decreases as the angle grows."""
    def value(x):
        angles[key] = x
        apply(angles)
        return measure(lowest()) - target
    f_low, f_high = value(low), value(high)
    if f_low < 0 or f_high > 0:
        angles[key] = low if abs(f_low) < abs(f_high) else high
        return {"key": key, "bracketed": False, "f_low_m": f_low, "f_high_m": f_high}
    for _ in range(steps):
        mid = (low + high) / 2
        if value(mid) > 0:
            low = mid
        else:
            high = mid
    angles[key] = (low + high) / 2
    return {"key": key, "bracketed": True, "degrees": angles[key]}


angles = {"spine": 0.0, "head": 0.0, "hip.L": 0.0, "hip.R": 0.0, "arm.L": 0.0, "arm.R": 0.0}
HEEL = base.get("feet", {}).get("heel_allowance_m")
TILT = abs(float(base.get("pelvis_tilt_deg", 0.0)))  # widens the spine and hip brackets only when the pelvis is tilted
ARM_KEY = "arm.{}" if base.get("arm_includes_forearm") else "hand.{}"
log = []
for round_index in range(4):
    entries = [bisect(angles, "spine", lambda z: z["back"] - z["pelvis"], -20.0 - TILT, 20.0),
               bisect(angles, "head", lambda z: z["head_back"] - z["pelvis"], -20.0, 45.0)]
    for side in ("L", "R"):
        if HEEL is None:
            entries.append(bisect(angles, f"hip.{side}", lambda z, s=side: z[f"calf.{s}"] - z["pelvis"], -15.0, 30.0 + TILT))
        else:
            entries.append(bisect(angles, f"hip.{side}", lambda z, s=side: min(z[f"calf.{s}"], z[f"foot.{s}"] + HEEL) - z["pelvis"], -15.0, 30.0 + TILT))
        if base.get("rest_hands_on_bed"):
            # Extension (negative twist about right) lowers the hand; the hand stops 3 mm above the support plane.
            entries.append(bisect(angles, f"arm.{side}", lambda z, s=side: -(z[ARM_KEY.format(s)] - z["pelvis"] - 0.003), -60.0, 30.0))
    log.append({"round": round_index, "entries": entries})
apply(angles)
before = lowest()
lift = TOP + 0.001 - min(before[k] for k in SETS)
apply(angles, lift)
after = lowest()
result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
    "foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
    "inputs": {name: {"path": getattr(args, name), "sha256": sha(ROOT / getattr(args, name))} for name in ("contract", "rules", "fixtures", "base")},
    "bed_top_z_m": TOP, "pelvis": {"turn": {"axis": "x", "degrees": -90.0 - float(base.get("pelvis_tilt_deg", 0.0))}, "head_rest_m": list(pelvis_head), "lift_m": lift,
                                    "location_m": list(pelvis_head + Vector((0.0, 0.0, lift)))},
    "angles_deg": angles, "solved_steps": solved_steps(angles), "rounds": log,
    "support_lowest_above_top_mm": {k: round((after[k] - TOP) * 1e3, 3) for k in SETS},
    "hands_lowest_above_top_mm": {s: round((after[f"hand.{s}"] - TOP) * 1e3, 3) for s in ("L", "R")},
    "parts_lowest_above_top_mm": {k: round((after[k] - TOP) * 1e3, 3) for k in PARTS},
    "body_lowest_above_top_mm": round((after["body"] - TOP) * 1e3, 3), "body_lowest": after["body_lowest"],
    "scope": "Supine posture relative to the pelvis with the head towards +Y; yaw and bed placement are applied per clip.",
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_BED_POSTURE " + json.dumps({"angles_deg": {k: round(v, 3) for k, v in angles.items()}, "lift_m": round(lift, 5),
                                        "support_mm": result["support_lowest_above_top_mm"], "hands_mm": result["hands_lowest_above_top_mm"],
                                        "parts_mm": result["parts_lowest_above_top_mm"], "body_mm": result["body_lowest_above_top_mm"], "body_lowest": result["body_lowest"]}))
