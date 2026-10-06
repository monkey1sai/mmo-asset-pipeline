"""Author the two-hand sword grip pose for a character V1 candidate by analytic two-bone IK.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_two_hand_pose.py -- \
       --poses-in <poses.json> --out <new poses.json> [--spacing-mm N]
The right hand keeps its verified grasp (finger pose and weapon socket). The sword is placed in front of the
chest; a small grid of grip points, blade pitches and rolls about the blade is searched for the placement
that rotates both wrists least (bend and twist) while both wrists stay in reach and clear of the torso. The left hand is the
mirror image of the right hand through a plane containing the hilt axis, moved along the hilt toward the
pommel. Only pose data is written; the BLEND is not saved.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--poses-in", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--spacing-mm", type=float, default=112.0)
parser.add_argument("--twist-share", type=float, default=0.5, help="share of the hand twist about the forearm taken by the cuff carrier bone")
parser.add_argument("--min-wrist-height", type=float, default=1.15)
parser.add_argument("--min-wrist-forward", type=float, default=0.26)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
poses = json.loads((ROOT / args.poses_in).read_text(encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones

# Hilt extent along the sword bone, from the mesh that is bound to it.
sword_bone = bones["sword"]
sword_axis = (sword_bone.tail_local - sword_bone.head_local).normalized()
sword = bpy.data.objects["SM_RO_sword"]
pommel = -min((v.co - sword_bone.head_local).dot(sword_axis) for v in sword.data.vertices)
spacing = min(args.spacing_mm / 1000, max(0.0, pommel - 0.02))


def palmar_rest():
    wrist = bones["hand.R"].head_local
    mcp = {i: bones[f"finger{i}.R_01"].head_local for i in (1, 2, 3, 4)}
    thumb = bones["thumb.R_01"].head_local
    index, pinky = (4, 1) if (mcp[4] - thumb).length < (mcp[1] - thumb).length else (1, 4)
    direction = (sum(mcp.values(), Vector()) / 4 - wrist).normalized()
    across = mcp[index] - mcp[pinky]
    radial = (across - direction * across.dot(direction)).normalized()
    return radial.cross(direction).normalized()


hand_rest = bones["hand.R"].matrix_local
sword_relative = hand_rest.inverted() @ sword_bone.matrix_local
palm_local = hand_rest.to_3x3().inverted() @ palmar_rest()
shoulder = {side: bones[f"upper_arm.{side}"].head_local.copy() for side in "RL"}
length = {side: ((bones[f"lower_arm.{side}"].head_local - bones[f"upper_arm.{side}"].head_local).length,
                 (bones[f"hand.{side}"].head_local - bones[f"lower_arm.{side}"].head_local).length) for side in "RL"}
reach = sum(length["R"])
spine_y = bones["spine_02"].head_local.y


def sword_world(grip, blade, roll):
    """Sword bone matrix with its origin on the grip point, its axis on the blade direction and a roll about that axis."""
    side = blade.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(blade).normalized()
    x_axis = side * math.cos(roll) + up * math.sin(roll)
    z_axis = x_axis.cross(blade).normalized()
    return Matrix.Translation(grip) @ Matrix((x_axis, blade, z_axis)).transposed().to_4x4()


def left_hand(right_matrix, grip, blade):
    normal = right_matrix.to_3x3() @ palm_local
    normal = (normal - blade * normal.dot(blade)).normalized()
    reflect = Matrix.Identity(3) - 2 * Matrix([[normal[i] * normal[j] for j in range(3)] for i in range(3)])
    mirror = Matrix.Translation(grip) @ reflect.to_4x4() @ Matrix.Translation(-grip)
    return Matrix.Translation(-blade * spacing) @ mirror @ right_matrix @ Matrix.Diagonal((-1, 1, 1, 1))


def elbow_of(side, wrist, swivel=0.0):
    """Elbow of the two-bone solution, below and outside the shoulder-wrist line, turned by swivel about that line; None when out of reach."""
    l1, l2 = length[side]
    line = wrist - shoulder[side]
    d = line.length
    if d > (l1 + l2) * 0.97 or d < abs(l1 - l2) * 1.05:
        return None
    direction = line / d
    a1 = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a1 * a1))
    out_side = Vector((1, 0, 0)) if side == "L" else Vector((-1, 0, 0))
    pole = Vector((0, 0, -1)) + out_side * 0.6 + Vector((0, 0.3, 0))
    pole = (pole - direction * pole.dot(direction)).normalized()
    pole = Matrix.Rotation(swivel if side == "R" else -swivel, 3, direction) @ pole
    return shoulder[side] + direction * a1 + pole * h


REST = {side: {name: bones[f"{name}.{side}"].matrix_local.to_3x3() for name in ("upper_arm", "lower_arm", "hand")} for side in "RL"}


def wrist_rotation(side, target, elbow):
    """Angle of the hand's rotation away from its rest relation to the forearm, after the two arm bones swing to the elbow and wrist."""
    upper_swing = REST[side]["upper_arm"].col[1].rotation_difference((elbow - shoulder[side]).normalized()).to_matrix()
    lower_swing = (upper_swing @ REST[side]["lower_arm"].col[1]).rotation_difference((target.translation - elbow).normalized()).to_matrix()
    carried = lower_swing @ upper_swing @ REST[side]["hand"]
    return math.degrees((carried.inverted() @ target.to_3x3()).to_quaternion().angle)


best = None
SWIVELS = [math.radians(a) for a in (-40, -20, 0, 20, 40)]
for gx in (-0.04, 0.0, 0.04):
    for gy in (-0.26, -0.30, -0.34, -0.38):
        for gz in (1.12, 1.19, 1.26, 1.33):
            for pitch in (20, 35, 50, 65):
                grip = Vector((gx, gy, gz))
                blade = Vector((0, -math.cos(math.radians(pitch)), math.sin(math.radians(pitch))))
                for step in range(72):
                    right = sword_world(grip, blade, math.radians(step * 5)) @ sword_relative.inverted()
                    left = left_hand(right, grip, blade)
                    # Both wrists in front of and above the belt, each on its own side or at the midline.
                    if max(right.translation.y, left.translation.y) > spine_y - args.min_wrist_forward or right.translation.x > 0.05 or left.translation.x < -0.05:
                        continue
                    if min(right.translation.z, left.translation.z) < args.min_wrist_height:
                        continue
                    choice = {}
                    for side, target in (("R", right), ("L", left)):
                        options = [(wrist_rotation(side, target, elbow), swivel) for swivel in SWIVELS if (elbow := elbow_of(side, target.translation, swivel)) is not None]
                        if options:
                            choice[side] = min(options)
                    if len(choice) < 2:
                        continue
                    bend = {side: choice[side][0] for side in "RL"}
                    score = max(bend.values()) + 0.25 * sum(bend.values())
                    if best is None or score < best[0]:
                        best = (score, grip, blade, step * 5, pitch, right, left, bend, {side: choice[side][1] for side in "RL"})
if best is None:
    raise SystemExit("NO_REACHABLE_TWO_HAND_GRIP")
_, grip, blade, roll_deg, pitch, right_target, left_target, bend, swivel = best


def reset():
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    bpy.context.view_layer.update()


def solve(side, target):
    upper, lower, hand = (arm.pose.bones[f"{name}.{side}"] for name in ("upper_arm", "lower_arm", "hand"))
    root, wrist, elbow = shoulder[side], target.translation, elbow_of(side, target.translation, swivel[side])
    for pose_bone, start, end in ((upper, root, elbow), (lower, elbow, wrist)):
        current = pose_bone.matrix.copy()
        swing = (current.to_3x3().col[1]).rotation_difference((end - start).normalized()).to_matrix()
        pose_bone.matrix = Matrix.Translation(start) @ (swing @ current.to_3x3()).to_4x4()
        pose_bone.location = (0, 0, 0)
        bpy.context.view_layer.update()
    # Twist of the hand about the forearm, measured from where the hand would sit if it only followed the forearm.
    forearm = (wrist - elbow).normalized()
    relative = (target.to_3x3() @ hand.matrix.to_3x3().inverted()).to_quaternion()
    twist = 2 * math.atan2(Vector((relative.x, relative.y, relative.z)).dot(forearm), relative.w)
    twist = (twist + math.pi) % (2 * math.pi) - math.pi
    carrier = arm.pose.bones[f"wrist_transition.{side}_twist"]
    carrier.matrix = Matrix.Translation(carrier.matrix.translation) @ (Matrix.Rotation(twist * args.twist_share, 3, forearm) @ carrier.matrix.to_3x3()).to_4x4()
    carrier.location = (0, 0, 0)
    bpy.context.view_layer.update()
    hand.matrix = target
    hand.location = (0, 0, 0)
    bpy.context.view_layer.update()
    return {"wrist": [round(c, 4) for c in wrist], "elbow": [round(c, 4) for c in elbow], "wrist_error_mm": round((hand.matrix.translation - wrist).length * 1e3, 3),
            "elbow_angle_deg": round(math.degrees((root - elbow).angle(wrist - elbow)), 1), "wrist_rotation_deg": round(bend[side], 1), "twist_about_forearm_deg": round(math.degrees(twist), 1), "twist_share_on_cuff_carrier": args.twist_share, "elbow_swivel_deg": round(math.degrees(swivel[side]), 1)}


reset()
solved = {"R": solve("R", right_target), "L": solve("L", left_target)}
arms = {name: list(arm.pose.bones[name].rotation_quaternion) for side in "RL" for name in (f"upper_arm.{side}", f"lower_arm.{side}")}
pose = dict(arms)
pose.update({f"{name}.{side}": list(arm.pose.bones[f"{name}.{side}"].rotation_quaternion) for side in "RL" for name in ("hand",)})
pose.update({f"wrist_transition.{side}_twist": list(arm.pose.bones[f"wrist_transition.{side}_twist"].rotation_quaternion) for side in "RL"})
pose.update(poses["grasp.R"])
pose.update(poses["grasp.L"])
poses["two_hand_chop"] = pose
poses["two_hand_chop_arms"] = arms
poses["two_hand_chop_source"] = {
    "method": "grid search over grip point, blade pitch and roll for least wrist bend; analytic two-bone IK; right hand keeps the r010 grasp and weapon socket, "
              "left hand is its mirror through a plane containing the hilt axis",
    "grip_point": [round(c, 4) for c in grip], "blade_pitch_deg": pitch, "roll_deg": roll_deg, "hand_spacing_mm": round(spacing * 1e3, 1),
    "pommel_from_grip_mm": round(pommel * 1e3, 1), "arm_reach_mm": round(reach * 1e3, 1), "solve": solved,
    "sword_grip_error_mm": round((arm.pose.bones["sword"].matrix.translation - grip).length * 1e3, 3),
    "candidate": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix()}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(poses, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_TWO_HAND_POSE", json.dumps(poses["two_hand_chop_source"]))
