"""Author a character V1 animation clip from a clip spec and write it as an action-only BLEND.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_author_clip.py -- \
       --spec <clip spec.json> --contract <joint-range-contract.json> --poses <poses.json> --rules <rules.json> \
       --out <new action .blend> --report <new report.json>
Procedural mode (loops): every frame 0..frames is keyed (frame `frames` equals frame 0), LINEAR between frames.
Per frame: rest -> named candidate poses (e.g. grasp.R) -> anatomical steps (same direction rules as the joint-range
contract, scripts/cv1_contract_pose.py) whose degrees may carry whole-cycle sine waves -> optional sword placement
solved by analytic two-bone IK (scripts/cv1_arm_ik.py) with the verified grip. Helper bones are never keyed; the
runtime rule drives them. The foundation BLEND is not saved; the output holds only the new action.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, sword_world
from cv1_contract_pose import ContractPoser

parser = argparse.ArgumentParser()
for name in ("--spec", "--contract", "--poses", "--rules", "--out", "--report"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out, report_path = (ROOT / args.out).resolve(), (ROOT / args.report).resolve()
for path in (out, report_path):
    if path.exists():
        raise SystemExit(f"REFUSE_OVERWRITE {path}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


spec = json.loads((ROOT / args.spec).read_text(encoding="utf-8"))
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
if spec.get("schema_version") != 1 or spec.get("mode") != "procedural" or not spec.get("loop") or spec.get("fps") != 60:
    raise SystemExit("SPEC_UNSUPPORTED (procedural 60 fps loops only)")
frames = int(spec["frames"])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, poses)
ik = ArmIK(arm)
helpers = {h["bone"] for h in rules.get("helpers", [])}


def wave(value, f):
    """A number, or {"base": b, "waves": [[amplitude, whole cycles per clip, phase in cycles], ...]}."""
    if isinstance(value, (int, float)):
        return float(value)
    total = float(value.get("base", 0.0))
    for amplitude, cycles, phase in value.get("waves", []):
        if int(cycles) != cycles:
            raise SystemExit("LOOP_WAVES_NEED_WHOLE_CYCLES")
        total += amplitude * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return total


def wave_vector(value, f):
    if isinstance(value, list):
        return Vector(value)
    out = Vector(value["base"])
    for vector, cycles, phase in value.get("waves", []):
        out += Vector(vector) * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return out


touched = set()
for name in spec.get("poses", []):
    touched |= set(poses[name])
touched |= {s["bone"] for s in spec.get("steps", [])}
sword = spec.get("sword")
if sword:
    touched |= {"upper_arm.R", "lower_arm.R", "hand.R"}
if touched & helpers:
    raise SystemExit(f"HELPER_BONES_ARE_EVALUATOR_OWNED {sorted(touched & helpers)}")
missing = sorted(touched - set(arm.pose.bones.keys()))
if missing:
    raise SystemExit(f"MISSING_BONES {missing}")


def pose_frame(f, roll=None, swivel=None):
    poser.reset()
    for name in spec.get("poses", []):
        for bone, quaternion in poses[name].items():
            arm.pose.bones[bone].rotation_quaternion = Quaternion(quaternion)
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        degrees = wave(step["degrees"], f)
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=degrees), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    if not sword:
        return None
    grip = wave_vector(sword["grip"], f)
    blade = Vector(sword["blade"]).normalized()
    pitch = math.radians(wave(sword.get("pitch_deg", 0.0), f))
    if pitch:
        blade = (Quaternion(blade.cross(Vector((0, 0, 1))).normalized(), pitch) @ blade).normalized()
    target = ik.hand_for_sword(sword_world(grip, blade, math.radians(roll)))
    return ik.solve("R", target, swivel)


# Roll about the blade and elbow swivel: chosen once at frame 0 for the least wrist bend, then held (no popping).
roll, swivel, choice = spec.get("sword", {}).get("roll_deg"), spec.get("sword", {}).get("swivel_deg"), None
if sword:
    poser.reset()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=wave(step["degrees"], 0)), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    grip0, blade0 = wave_vector(sword["grip"], 0), Vector(sword["blade"]).normalized()
    options = []
    for r in ([roll] if roll is not None else range(0, 360, 5)):
        target = ik.hand_for_sword(sword_world(grip0, blade0, math.radians(r)))
        if swivel is not None:
            elbow = ik.elbow_of("R", target.translation, math.radians(swivel))
            if elbow is not None:
                options.append((ik.wrist_bend_deg("R", target, elbow), r, swivel))
        else:
            best = ik.best_swivel("R", target)
            if best is not None:
                options.append((best[0], r, best[1]))
    if not options:
        raise SystemExit("SWORD_GRIP_OUT_OF_REACH")
    bend, roll, swivel = min(options)
    choice = {"roll_deg": roll, "swivel_deg": swivel, "wrist_bend_deg_at_frame0": round(bend, 2), "searched": len(options)}

action = bpy.data.actions.new(spec["clip"])
arm.animation_data_create()
arm.animation_data.action = action
solves = []
for f in range(frames + 1):
    solved = pose_frame(f, roll, swivel)
    if solved:
        solves.append(solved)
    for bone in sorted(touched):
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.keyframe_insert("rotation_quaternion", frame=f, group=bone)
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
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
    "foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
    "spec": {"path": args.spec, "sha256": sha(ROOT / args.spec)}, "contract": {"path": args.contract, "sha256": sha(ROOT / args.contract)},
    "poses": {"path": args.poses, "sha256": sha(ROOT / args.poses)}, "rules": {"path": args.rules, "sha256": sha(ROOT / args.rules)},
    "output": {"path": out.relative_to(ROOT).as_posix(), "sha256": sha(out), "action": action.name, "fcurves": len(action.fcurves)},
    "clip": spec["clip"], "frames": frames, "keyed_frames": [0, frames], "interpolation": "LINEAR", "animated_bones": sorted(touched),
    "helper_bones_not_keyed": sorted(helpers), "sword_solution": choice,
    "ik": {"max_wrist_error_mm": max((s["wrist_error_mm"] for s in solves), default=None),
           "wrist_bend_deg_range": [min((s["wrist_bend_deg"] for s in solves), default=None), max((s["wrist_bend_deg"] for s in solves), default=None)],
           "elbow_angle_deg_range": [min((s["elbow_angle_deg"] for s in solves), default=None), max((s["elbow_angle_deg"] for s in solves), default=None)]},
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_AUTHOR_CLIP " + json.dumps({k: report[k] for k in ("clip", "frames", "sword_solution", "ik")}))
