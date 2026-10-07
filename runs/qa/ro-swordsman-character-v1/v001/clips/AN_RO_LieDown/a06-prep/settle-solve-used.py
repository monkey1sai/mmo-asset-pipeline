"""Design solve (report only): per frame, the smallest extra contract step on a coat bone that keeps that bone's coat
vertices over the bed footprint at least a margin above the bed top.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python settle-solve-used.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --rules <rules.json> --contract <contract.json> \
       --frames f,f,... --steps <json list of {"bone", "kind", "toward"}> --max-deg 120 --margin-m 0.003 --out <report.json>
Each frame is evaluated as scripts/cv1_clip_check.py evaluates a sample (action, bed socket after the event, helpers,
interaction states, correctives); the step is added on top of the bone's evaluated rotation and bisected. A bone whose
vertices already clear the bed needs 0. Nothing is saved.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--rules", "--contract", "--frames", "--steps", "--out"):
    parser.add_argument(name, required=True)
parser.add_argument("--max-deg", type=float, default=120.0)
parser.add_argument("--margin-m", type=float, default=0.003)
parser.add_argument("--profile", default="", help="comma list of angles: report the lowest vertex at each instead of solving")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
config = interaction.load(ROOT / args.interaction)
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
steps = json.loads(args.steps)
bed = config["bed"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
poser = ContractPoser(arm, contract, {})
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (src, dst):
    dst.actions = [config["clip"]]
action = dst.actions[0]
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
coat = bpy.data.objects["SM_RO_coat"]
names = {g.index: g.name for g in coat.vertex_groups}
dominant = [names[max(v.groups, key=lambda g: g.weight).group] if v.groups else None for v in coat.data.vertices]
SOCKET = config.get("sword_socket")
BED_SOCKET = (Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()) if SOCKET else None
cx, cy = bed["centre_m"]
half_l, half_w, top = bed["size_m"][0] / 2, bed["size_m"][1] / 2, bed["top_z_m"]


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def evaluate(t):
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0
    arm.animation_data_create()
    arm.animation_data.action = action
    frame = math.floor(t)
    bpy.context.scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    if SOCKET and interaction.socket_at(config, t) == "bed":
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ BED_SOCKET
        bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    states = interaction.states_at(config, t)
    state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    arm.animation_data.action = None  # freeze the evaluated pose for the solve


def lowest(bone, where=False):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = coat.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    low, at = None, None
    for i, v in enumerate(mesh.vertices):
        if dominant[i] != bone:
            continue
        p = target.matrix_world @ v.co
        if abs(p.x - cx) <= half_l and abs(p.y - cy) <= half_w and (low is None or p.z < low):
            low, at = p.z, (i, p.copy())
    target.to_mesh_clear()
    if where:
        return low, at
    return low


rows = []
for t in [float(x) for x in args.frames.split(",")]:
    evaluate(t)
    row = {"t": t}
    for step in steps:
        pb = arm.pose.bones[step["bone"]]
        base = pb.rotation_quaternion.copy()

        def set_deg(deg):
            pb.rotation_quaternion = base @ poser.step_rotation(dict(step, degrees=deg), step.get("side"), 1.0)
            bpy.context.view_layer.update()
            return lowest(step["bone"])

        if args.profile:
            prof = []
            for deg in [float(x) for x in args.profile.split(",")]:
                set_deg(deg)
                value, at = lowest(step["bone"], where=True)
                prof.append({"deg": deg, "lowest_above_top_mm": None if value is None else round((value - top) * 1e3, 1),
                             "world_m": None if at is None else [round(c, 3) for c in at[1]], "rest_m": None if at is None else [round(c, 3) for c in coat.data.vertices[at[0]].co]})
            row[step["bone"]] = prof
            pb.rotation_quaternion = base
            bpy.context.view_layer.update()
            continue
        low0 = set_deg(0.0)
        if low0 is None or low0 >= top + args.margin_m:
            row[step["bone"]] = {"deg": 0.0, "lowest_above_top_mm": None if low0 is None else round((low0 - top) * 1e3, 1)}
        else:
            lo, hi = 0.0, args.max_deg
            low_hi = set_deg(hi)
            if low_hi is not None and low_hi < top + args.margin_m:
                row[step["bone"]] = {"deg": None, "at_max_lowest_above_top_mm": round((low_hi - top) * 1e3, 1)}
            else:
                for _ in range(24):
                    mid = (lo + hi) / 2
                    value = set_deg(mid)
                    if value is not None and value < top + args.margin_m:
                        lo = mid
                    else:
                        hi = mid
                row[step["bone"]] = {"deg": round(hi, 2), "start_lowest_above_top_mm": round((low0 - top) * 1e3, 1)}
        pb.rotation_quaternion = base
        bpy.context.view_layer.update()
    rows.append(row)
    print("CV1_SETTLE " + json.dumps(row))
Path(args.out).write_text(json.dumps({"steps": steps, "margin_m": args.margin_m, "rows": rows}, indent=1) + "\n", encoding="utf-8", newline="\n")
