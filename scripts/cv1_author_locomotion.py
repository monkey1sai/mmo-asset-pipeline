"""Author an in-place locomotion loop (walk, run) for character V1 and write it as an action-only BLEND.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_author_locomotion.py -- \
       --spec <clip spec.json> --contract <joint-range-contract.json> --poses <poses.json> --rules <rules.json> \
       --fixtures <contact-fixtures.json> --out <new action .blend> --report <new report.json>
Every frame 0..frames is keyed (frame `frames` closes the loop and equals frame 0), linear between frames:
rest -> named candidate poses (grip) -> pelvis (height fitted to the legs' reach, bob, sway, yaw, roll;
scripts/cv1_gait.py) -> anatomical steps with whole-cycle waves (spine, head, left arm; same direction rules as the
joint-range contract) -> both legs by two-bone IK onto the gait's foot targets (flat in stance, heel or toe pivot in
swing) -> the sword arm by two-bone IK with the Idle grip, following the chest. Helper bones are never keyed.
The foundation BLEND is not saved; the output holds only the new action.
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
import cv1_gait as gait_math
from cv1_arm_ik import ArmIK, LegIK, sword_world
from cv1_contract_pose import ContractPoser

parser = argparse.ArgumentParser()
for name in ("--spec", "--contract", "--poses", "--rules", "--fixtures", "--out", "--report"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out, report_path = (ROOT / args.out).resolve(), (ROOT / args.report).resolve()
for path in (out, report_path):
    if path.exists():
        raise SystemExit(f"REFUSE_OVERWRITE {path}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


spec, contract, poses, rules, fixtures = (load(p) for p in (args.spec, args.contract, args.poses, args.rules, args.fixtures))
if spec.get("schema_version") != 1 or spec.get("mode") != "locomotion" or not spec.get("loop") or spec.get("fps") != 60:
    raise SystemExit("SPEC_UNSUPPORTED (locomotion 60 fps loops only)")
frames, gait = int(spec["frames"]), spec["gait"]
cycle_seconds = frames / spec["fps"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
poser, arm_ik, leg_ik = ContractPoser(arm, contract, poses), ArmIK(arm), LegIK(arm)
helpers = {h["bone"] for h in rules.get("helpers", [])}
FORWARD, UP = Vector(contract["axes"]["forward"]), Vector(contract["axes"]["up"])


def wave(value, f):
    if isinstance(value, (int, float)):
        return float(value)
    total = float(value.get("base", 0.0))
    for amplitude, cycles, phase in value.get("waves", []):
        if int(cycles) != cycles:
            raise SystemExit("LOOP_WAVES_NEED_WHOLE_CYCLES")
        total += amplitude * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return total


# ---- foot pivots from the rest mesh: toe = front-most sole point, heel = rear-most low point of the foot ----
pivots = {}
for side in ("L", "R"):
    ids = fixtures["fixtures"][f"sole_set.{side}"]["ids"]
    sole = [bpy.data.objects[mesh].matrix_world @ bpy.data.objects[mesh].data.vertices[i].co for mesh, members in ids.items() for i in members]
    lowest = min(p.z for p in sole)
    toe = max(sole, key=lambda p: p.dot(FORWARD))
    core = bpy.data.objects["SM_RO_core"]
    names = [g.name for g in core.vertex_groups]
    region = [core.matrix_world @ v.co for v in core.data.vertices
              if sum(g.weight for g in v.groups if names[g.group] in (f"foot.{side}", f"toe.{side}")) >= 0.5]
    heel = max((p for p in region if p.z <= lowest + 0.03), key=lambda p: -p.dot(FORWARD))
    pivots[side] = {"toe": toe.copy(), "heel": heel.copy()}

ankle_rest = {side: bones[f"foot.{side}"].head_local.copy() for side in ("L", "R")}
foot_rotation = {side: bones[f"foot.{side}"].matrix_local.to_3x3() for side in ("L", "R")}
pelvis_head, pelvis_rotation = bones["pelvis"].head_local.copy(), bones["pelvis"].matrix_local.to_3x3()
lateral = UP.cross(FORWARD).normalized()  # axis of foot pitch


def foot_target(side, f):
    state = gait_math.foot_state(gait_math.foot_phase(f, side, gait, frames), gait, cycle_seconds)
    # step_out_m widens the stance: each foot sits further out from the midline (a little hip abduction).
    outward = Vector(contract["axes"]["left"]) * (1.0 if side == "L" else -1.0) * gait.get("step_out_m", 0.0)
    shift = FORWARD * state["forward"] + UP * state["lift"] + outward
    # toe_out_deg turns the foot outward about the vertical through the ankle (the knee follows, see LegIK pole_yaw_deg).
    yaw = math.radians(gait.get("toe_out_deg", 0.0) * (1.0 if side == "L" else -1.0))
    turn_out = Matrix.Rotation(yaw, 3, UP)
    matrix = Matrix.Translation(ankle_rest[side] + shift) @ (turn_out @ foot_rotation[side]).to_4x4()
    if state["pitch"]:
        pivot = ankle_rest[side] + turn_out @ (pivots[side]["toe" if state["pitch"] > 0 else "heel"] - ankle_rest[side]) + shift
        # About lateral = up x forward, + pitch lifts the points behind the pivot (heel up); - lifts the points in front of it (toes up).
        turn = Matrix.Rotation(math.radians(state["pitch"]), 4, lateral)
        matrix = Matrix.Translation(pivot) @ turn @ Matrix.Translation(-pivot) @ matrix
    return matrix, state


def pelvis_rotation_at(f):
    motion = gait_math.pelvis_motion(f / frames, gait)
    return Matrix.Rotation(math.radians(motion["yaw"]), 3, UP) @ Matrix.Rotation(math.radians(motion["roll"]), 3, -FORWARD), motion


def reach_limit(f):
    """Largest pelvis height offset that keeps both ankle targets within leg reach at frame f."""
    rotation, motion = pelvis_rotation_at(f)
    best = math.inf
    for side in ("L", "R"):
        ankle = foot_target(side, f)[0].translation
        hip = pelvis_head + Vector((motion["sway"], 0.0, 0.0)) + rotation @ (leg_ik.hip_rest[side] - pelvis_head)
        radius = leg_ik.max_length(side) * (1 - 1e-4)
        flat = (hip.x - ankle.x) ** 2 + (hip.y - ankle.y) ** 2
        if flat >= radius * radius:
            raise SystemExit(f"FOOT_TARGET_OUT_OF_REACH {side} frame {f}")
        best = min(best, ankle.z - hip.z + math.sqrt(radius * radius - flat))
    return best


heights, centre = gait_math.pelvis_heights(frames, gait, reach_limit)

touched = {"pelvis"} | {f"{name}.{side}" for name in ("upper_leg", "lower_leg", "foot") for side in ("L", "R")}
for name in spec.get("poses", []):
    touched |= set(poses[name])
touched |= {s["bone"] for s in spec.get("steps", [])}
sword = spec["sword"]
touched |= {"upper_arm.R", "lower_arm.R", "hand.R"}
if touched & helpers:
    raise SystemExit(f"HELPER_BONES_ARE_EVALUATOR_OWNED {sorted(touched & helpers)}")
follow_rest = bones[sword["follow_bone"]].matrix_local.copy()
hand_rest_target = arm_ik.hand_for_sword(sword_world(Vector(sword["grip"]), Vector(sword["blade"]).normalized(), math.radians(sword["roll_deg"])))


def pose_frame(f):
    poser.reset()
    for name in spec.get("poses", []):
        for bone, quaternion in poses[name].items():
            arm.pose.bones[bone].rotation_quaternion = Quaternion(quaternion)
    rotation, motion = pelvis_rotation_at(f)
    pelvis = arm.pose.bones["pelvis"]
    pelvis.matrix = Matrix.Translation(pelvis_head + Vector((motion["sway"], 0.0, heights[f]))) @ (rotation @ pelvis_rotation).to_4x4()
    bpy.context.view_layer.update()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=wave(step["degrees"], f)), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    legs = {}
    for side in ("L", "R"):
        matrix, state = foot_target(side, f)
        legs[side] = {**leg_ik.solve(side, matrix, gait.get("toe_out_deg", 0.0)), "stance": state["stance"]}
    follow = arm.pose.bones[sword["follow_bone"]].matrix @ follow_rest.inverted()
    shoulder = arm_ik.shoulder("R")
    swing = Matrix.Translation(shoulder) @ Matrix.Rotation(math.radians(wave(sword.get("swing_deg", 0.0), f)), 4, lateral) @ Matrix.Translation(-shoulder)
    hand = arm_ik.solve("R", swing @ follow @ hand_rest_target, sword["swivel_deg"])
    return legs, hand


action = bpy.data.actions.new(spec["clip"])
arm.animation_data_create()
arm.animation_data.action = action
rows = []
for f in range(frames + 1):
    legs, hand = pose_frame(f)
    rows.append({"frame": f, "pelvis_height_offset_m": heights[f], "legs": legs, "wrist_bend_deg": hand["wrist_bend_deg"], "wrist_error_mm": hand["wrist_error_mm"]})
    for bone in sorted(touched):
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.keyframe_insert("rotation_quaternion", frame=f, group=bone)
    arm.pose.bones["pelvis"].keyframe_insert("location", frame=f, group="pelvis")
for curve in action.fcurves:
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"
arm.animation_data.action = None
action.use_fake_user = True
out.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(out), {action}, fake_user=True)
# The spec used for this attempt travels with it (the working spec file is edited between attempts).
with open(out.parent / "clip-spec.json", "x", encoding="utf-8", newline=chr(10)) as handle:
    json.dump(spec, handle, ensure_ascii=False, indent=1)
    handle.write(chr(10))
knees = [r["legs"][s]["knee_angle_deg"] for r in rows for s in ("L", "R")]
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
    "gait_module_sha256": sha(ROOT / "scripts/cv1_gait.py"), "ik_module_sha256": sha(ROOT / "scripts/cv1_arm_ik.py"),
    "foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
    "spec": {"path": args.spec, "sha256": sha(ROOT / args.spec)}, "contract": {"path": args.contract, "sha256": sha(ROOT / args.contract)},
    "poses": {"path": args.poses, "sha256": sha(ROOT / args.poses)}, "rules": {"path": args.rules, "sha256": sha(ROOT / args.rules)},
    "fixtures": {"path": args.fixtures, "sha256": sha(ROOT / args.fixtures)},
    "output": {"path": out.relative_to(ROOT).as_posix(), "sha256": sha(out), "action": action.name, "fcurves": len(action.fcurves)},
    "clip": spec["clip"], "frames": frames, "keyed_frames": [0, frames], "interpolation": "LINEAR", "animated_bones": sorted(touched),
    "helper_bones_not_keyed": sorted(helpers),
    "stance_windows": {side: gait_math.stance_window(gait, side, frames) for side in ("L", "R")},
    "pelvis": {"centre_offset_m": centre, "height_offset_range_m": [min(heights), max(heights)]},
    "pivots": {side: {k: [round(c, 4) for c in v] for k, v in p.items()} for side, p in pivots.items()},
    "ik": {"max_ankle_error_mm": max(r["legs"][s]["ankle_error_mm"] for r in rows for s in ("L", "R")), "knee_angle_deg_range": [min(knees), max(knees)],
           "max_wrist_error_mm": max(r["wrist_error_mm"] for r in rows), "wrist_bend_deg_range": [min(r["wrist_bend_deg"] for r in rows), max(r["wrist_bend_deg"] for r in rows)]},
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_AUTHOR_LOCOMOTION " + json.dumps({k: report[k] for k in ("clip", "frames", "stance_windows", "pelvis", "ik")}))
