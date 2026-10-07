"""Author a character V1 animation clip from a clip spec and write it as an action-only BLEND.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_author_clip.py -- \
       --spec <clip spec.json> --contract <joint-range-contract.json> --poses <poses.json> --rules <rules.json> \
       --out <new action .blend> --report <new report.json>
Procedural mode (loops): every frame 0..frames is keyed (frame `frames` equals frame 0), LINEAR between frames.
Keys mode (non-loop clips): every frame 0..frames-1 is keyed, LINEAR between frames; values follow key poses.
Per frame: rest -> named candidate poses (e.g. grasp.R) -> anatomical steps (same direction rules as the joint-range
contract, scripts/cv1_contract_pose.py) whose degrees may carry whole-cycle sine waves or key values -> optional sword
placement solved by analytic two-bone IK (scripts/cv1_arm_ik.py) with the verified grip. Key values ({"keys": [[frame,
value], ...]}) are eased with smoothstep between neighbouring keys, so a value never leaves the range of its two keys
(no overshoot past a key pose) and its speed is zero at every key. An optional "pelvis" block places the pelvis in
armature space before the steps: "location_m" (the pelvis head; rest head when omitted) and "rotation", a list of
world-axis turns applied in order to the rest orientation; the pelvis is then keyed on location and rotation, as the
locomotion author keys it. Named poses may carry a "weight" value (slerp from the bone's current rotation: rest, or an
earlier pose in the list), e.g. a grip that opens.
IK channels blend with the FK pose by a weight value (slerp of the local rotations, 0 = steps only, 1 = IK):
"sword" (right arm, optional "ik_weight", default 1) and "legs_ik" ({"weight", "pole_yaw_deg", "L"/"R": {"ankle_m",
"foot_turn_deg"}}: two-bone leg IK with the foot flat at its rest orientation turned about Z). Both IK solvers use
world-fixed pole directions, meant for an upright torso (standing, sitting). The sword block's optional "ik" picks the
arm solver: "swing" (default, the solver every earlier clip used) or "hinge" (ArmIK.solve_hinge: same elbow point, the
elbow bends only about the contract flexion axis and forearm rotation goes to the hand); with "hinge", an optional
"hand_relax" value (0..1) turns the hand toward its rest relation to the forearm (a hand that has let go of the grip,
wrist point unchanged). Helper bones are never keyed;
the runtime rule drives them. The foundation BLEND is not saved; the output holds only the new action.
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
from cv1_arm_ik import ArmIK, LegIK, sword_world
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
loop = spec.get("loop")
if spec.get("schema_version") != 1 or spec.get("fps") != 60 or (spec.get("mode"), loop) not in (("procedural", True), ("keys", False)):
    raise SystemExit("SPEC_UNSUPPORTED (60 fps procedural loops or keyed non-loop clips only)")
frames = int(spec["frames"])
# A loop is keyed through its closing frame (equal to frame 0); a non-loop clip has frames 0..frames-1.
key_frames = range(frames + 1) if loop else range(frames)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
poser = ContractPoser(arm, contract, poses)
ik = ArmIK(arm, contract=contract)  # the hinge solver takes its flexion and pronation extremes from the contract
helpers = {h["bone"] for h in rules.get("helpers", [])}


def keyed(keys, f):
    """Smoothstep between neighbouring [frame, value] keys; held flat before the first and after the last key."""
    keys = sorted(keys, key=lambda k: k[0])
    if f <= keys[0][0]:
        return keys[0][1]
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0)
            s = t * t * (3 - 2 * t)
            if isinstance(v0, list):
                return [a + (b - a) * s for a, b in zip(v0, v1)]
            return v0 + (v1 - v0) * s
    return keys[-1][1]


def wave(value, f):
    """A number, or {"base": b | "keys": [[frame, b], ...], "waves": [[amplitude, cycles per clip, phase in cycles], ...]}."""
    if isinstance(value, (int, float)):
        return float(value)
    total = float(keyed(value["keys"], f)) if "keys" in value else float(value.get("base", 0.0))
    for amplitude, cycles, phase in value.get("waves", []):
        if loop and int(cycles) != cycles:
            raise SystemExit("LOOP_WAVES_NEED_WHOLE_CYCLES")
        total += amplitude * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return total


def wave_vector(value, f):
    if isinstance(value, list):
        return Vector(value)
    out = Vector(keyed(value["keys"], f)) if "keys" in value else Vector(value["base"])
    for vector, cycles, phase in value.get("waves", []):
        if loop and int(cycles) != cycles:
            raise SystemExit("LOOP_WAVES_NEED_WHOLE_CYCLES")
        out += Vector(vector) * math.sin(2 * math.pi * (cycles * f / frames + phase))
    return out


def pose_entries():
    """Named poses with their weight value: a plain name means the full pose."""
    for item in spec.get("poses", []):
        yield (item, 1.0) if isinstance(item, str) else (item["name"], item["weight"])


legs_spec = spec.get("legs_ik")
# Reach limit of the leg solver (share of the full leg length); a standing start needs nearly straight legs.
leg_ik = LegIK(arm, reach=float((legs_spec or {}).get("reach", 0.995)))
LEG_CHAIN = {side: [f"{name}.{side}" for name in ("upper_leg", "lower_leg", "foot")] for side in "LR"}
ARM_CHAIN = ["upper_arm.R", "lower_arm.R", "hand.R"]
touched = set()
for name, _ in pose_entries():
    touched |= set(poses[name])
touched |= {s["bone"] for s in spec.get("steps", [])}
if legs_spec:
    touched |= set(LEG_CHAIN["L"]) | set(LEG_CHAIN["R"])
pelvis_spec = spec.get("pelvis")
WORLD_AXES = {"x": Vector((1.0, 0.0, 0.0)), "y": Vector((0.0, 1.0, 0.0)), "z": Vector((0.0, 0.0, 1.0))}
pelvis_head, pelvis_rest = arm.data.bones["pelvis"].head_local.copy(), arm.data.bones["pelvis"].matrix_local.to_3x3()
if pelvis_spec:
    if "pelvis" in touched:
        raise SystemExit("PELVIS_PLACED_BY_ITS_BLOCK_NOT_BY_STEPS")
    touched.add("pelvis")
sword = spec.get("sword")
if sword:
    touched |= {"upper_arm.R", "lower_arm.R", "hand.R"}
if touched & helpers:
    raise SystemExit(f"HELPER_BONES_ARE_EVALUATOR_OWNED {sorted(touched & helpers)}")
missing = sorted(touched - set(arm.pose.bones.keys()))
if missing:
    raise SystemExit(f"MISSING_BONES {missing}")


def place_pelvis(f):
    """Pelvis head at location_m with the listed world-axis turns applied to its rest orientation (armature space)."""
    if not pelvis_spec:
        return
    turn = Quaternion()
    for item in pelvis_spec.get("rotation", []):
        turn = Quaternion(WORLD_AXES[item["axis"]], math.radians(wave(item["degrees"], f))) @ turn
    place = wave_vector(pelvis_spec["location_m"], f) if "location_m" in pelvis_spec else pelvis_head
    pb = arm.pose.bones["pelvis"]
    pb.rotation_mode = "QUATERNION"
    pb.matrix = Matrix.Translation(place) @ (turn.to_matrix() @ pelvis_rest).to_4x4()


def blend_ik(chain, weight, solve):
    """Solve IK on top of the FK pose, then keep slerp(FK, IK, weight) of each chain bone's local rotation."""
    fk = {bone: arm.pose.bones[bone].rotation_quaternion.copy() for bone in chain}
    result = solve()
    if weight < 1.0:
        for bone in chain:
            pb = arm.pose.bones[bone]
            pb.rotation_quaternion = fk[bone].slerp(pb.rotation_quaternion, weight)
        bpy.context.view_layer.update()
    return result


def pose_frame(f, roll=None, swivel=None):
    poser.reset()
    for name, weight in pose_entries():
        w = wave(weight, f)
        for bone, quaternion in poses[name].items():
            # A partial pose blends from the rotation the bone already has (an earlier pose in the list), not from rest: a
            # second pose at weight 0 must leave the first one in place (combo a02: two_hand_chop at 0 undid grasp.R).
            pb = arm.pose.bones[bone]
            pb.rotation_quaternion = Quaternion(quaternion) if w >= 1.0 else pb.rotation_quaternion.slerp(Quaternion(quaternion), w)
    place_pelvis(f)
    bpy.context.view_layer.update()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        degrees = wave(step["degrees"], f)
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=degrees), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    solved = {}
    if legs_spec and (w := wave(legs_spec["weight"], f)) > 0.0:
        for side in "LR":
            target = Matrix.Translation(wave_vector(legs_spec[side]["ankle_m"], f)) @ \
                (Quaternion(Vector((0.0, 0.0, 1.0)), math.radians(wave(legs_spec[side].get("foot_turn_deg", 0.0), f))).to_matrix() @ leg_ik.foot_rest[side].to_3x3()).to_4x4()
            try:
                solved[f"leg.{side}"] = blend_ik(LEG_CHAIN[side], w, lambda: leg_ik.solve(side, target, wave(legs_spec.get("pole_yaw_deg", 0.0), f)))
            except ValueError as error:
                raise SystemExit(f"{error} at frame {f} (legs_ik weight {w:.3f})")
    if not sword or (w := wave(sword.get("ik_weight", 1.0), f)) <= 0.0:
        return solved or None
    grip = wave_vector(sword["grip"], f)
    blade = wave_vector(sword["blade"], f).normalized()
    pitch = math.radians(wave(sword.get("pitch_deg", 0.0), f))
    if pitch:
        blade = (Quaternion(blade.cross(Vector((0, 0, 1))).normalized(), pitch) @ blade).normalized()
    roll_value = wave(roll_spec, f) if roll_spec is not None else roll
    swivel_value = wave(swivel_spec, f) if swivel_spec is not None else swivel
    target = ik.hand_for_sword(sword_world(grip, blade, math.radians(roll_value)))
    relax = wave(sword.get("hand_relax", 0.0), f)
    try:
        solved["arm.R"] = blend_ik(ARM_CHAIN, w, (lambda: ik.solve_hinge("R", target, swivel_value, relax)) if hinge else (lambda: ik.solve("R", target, swivel_value)))
    except ValueError as error:
        raise SystemExit(f"{error} at frame {f} (sword ik_weight {w:.3f}, wrist {(target.translation - ik.shoulder('R')).length:.4f} m from the shoulder)")
    return solved


if (sword or {}).get("ik", "swing") not in ("swing", "hinge"):
    raise SystemExit(f"SWORD_IK_UNKNOWN {sword['ik']} (swing or hinge)")
hinge = (sword or {}).get("ik") == "hinge"
if sword and "hand_relax" in sword and not hinge:
    raise SystemExit("HAND_RELAX_NEEDS_HINGE_IK")


def wrist_bend(target, swivel_value):
    """Wrist bend of the chosen solver at this swivel; None when it cannot reach."""
    if hinge:
        try:
            return ik.hand_relation("R", ik.hinge_frames("R", target, swivel_value)[1], target)["wrist_bend_deg"]
        except ValueError:
            return None
    elbow = ik.elbow_of("R", target.translation, math.radians(swivel_value))
    return None if elbow is None else ik.wrist_bend_deg("R", target, elbow)


# Roll about the blade and elbow swivel: given in the spec (numbers or key values), or chosen once at frame 0 for the
# least wrist bend and then held (no popping).
roll_spec, swivel_spec = (sword or {}).get("roll_deg"), (sword or {}).get("swivel_deg")
roll, swivel, choice = None, None, None
if sword and (roll_spec is None or swivel_spec is None):
    poser.reset()
    place_pelvis(0)
    bpy.context.view_layer.update()
    for step in spec.get("steps", []):
        pb = arm.pose.bones[step["bone"]]
        pb.rotation_quaternion = pb.rotation_quaternion @ poser.step_rotation(dict(step, degrees=wave(step["degrees"], 0)), step.get("side"), 1.0)
    bpy.context.view_layer.update()
    grip0, blade0 = wave_vector(sword["grip"], 0), wave_vector(sword["blade"], 0).normalized()
    roll, swivel = (wave(roll_spec, 0) if roll_spec is not None else None), (wave(swivel_spec, 0) if swivel_spec is not None else None)
    options = []
    for r in ([roll] if roll is not None else range(0, 360, 5)):
        target = ik.hand_for_sword(sword_world(grip0, blade0, math.radians(r)))
        if swivel is not None:
            if (bend := wrist_bend(target, swivel)) is not None:
                options.append((bend, r, swivel))
        else:
            best = ik.best_hinge_swivel("R", target) if hinge else ik.best_swivel("R", target)
            if best is not None:
                options.append((best[0], r, best[1]))
    if not options:
        raise SystemExit("SWORD_GRIP_OUT_OF_REACH")
    bend, roll, swivel = min(options)
    choice = {"roll_deg": roll, "swivel_deg": swivel, "wrist_bend_deg_at_frame0": round(bend, 2), "searched": len(options)}

action = bpy.data.actions.new(spec["clip"])
arm.animation_data_create()
arm.animation_data.action = action
solves, arm_frames = [], []
for f in key_frames:
    solved = pose_frame(f, roll, swivel)
    if solved:
        solves.append(solved)
        if "arm.R" in solved:
            arm_frames.append(dict({k: (round(v, 3) if isinstance(v, float) else v) for k, v in solved["arm.R"].items()}, frame=f))
    for bone in sorted(touched):
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.keyframe_insert("rotation_quaternion", frame=f, group=bone)
        if bone == "pelvis" and pelvis_spec:
            pb.keyframe_insert("location", frame=f, group=bone)
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
    "clip": spec["clip"], "frames": frames, "mode": spec["mode"], "loop": loop, "keyed_frames": [key_frames[0], key_frames[-1]], "interpolation": "LINEAR",
    "animated_bones": sorted(touched),
    "helper_bones_not_keyed": sorted(helpers), "sword_solution": choice,
    "ik": {"frames_with_arm_ik": len(arms := [s["arm.R"] for s in solves if "arm.R" in s]),
           "max_wrist_error_mm": max((s["wrist_error_mm"] for s in arms), default=None),
           "wrist_bend_deg_range": [min((s["wrist_bend_deg"] for s in arms), default=None), max((s["wrist_bend_deg"] for s in arms), default=None)],
           "elbow_angle_deg_range": [min((s["elbow_angle_deg"] for s in arms), default=None), max((s["elbow_angle_deg"] for s in arms), default=None)],
           "arm_solver": "hinge" if hinge else "swing",
           **({"flexion_deg_range": [min(s["flexion_deg"] for s in arms), max(s["flexion_deg"] for s in arms)],
               "pronation_deg_range": [min(s["pronation_deg"] for s in arms), max(s["pronation_deg"] for s in arms)],
               "wrist_swing_deg_range": [min(s["wrist_swing_deg"] for s in arms), max(s["wrist_swing_deg"] for s in arms)],
               "pronation_over_contract_frames": sum(s["pronation_over_contract"] for s in arms), "pronation_limit_deg": ik.pronation_max_deg,
               "upper_twist_deg_range": [min(s["upper_twist_deg"] for s in arms), max(s["upper_twist_deg"] for s in arms)],
               "upper_swing_deg_range": [min(s["upper_swing_deg"] for s in arms), max(s["upper_swing_deg"] for s in arms)],
               "max_lower_frame_error_deg": max(s["lower_frame_error_deg"] for s in arms)} if hinge and arms else {}),
           "frames_with_leg_ik": len(legs := [s[k] for s in solves for k in ("leg.L", "leg.R") if k in s]),
           "max_ankle_error_mm": max((s["ankle_error_mm"] for s in legs), default=None),
           "knee_angle_deg_range": [min((s["knee_angle_deg"] for s in legs), default=None), max((s["knee_angle_deg"] for s in legs), default=None)]},
    # Per keyed frame, the arm solve before the FK/IK weight blend (the keyed pose is the blend when ik_weight < 1).
    "arm_ik_frames": arm_frames if hinge else None,
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_AUTHOR_CLIP " + json.dumps({k: report[k] for k in ("clip", "frames", "sword_solution", "ik")}))
