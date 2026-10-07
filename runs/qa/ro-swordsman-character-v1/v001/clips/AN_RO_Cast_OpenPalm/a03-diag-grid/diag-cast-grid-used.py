"""Diagnostic (report only): left-armpit fold map over upper_arm.L abduction x flexion at one clip frame.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python diag_cast_armpit.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --rules <rules.json> --contract <contract.json> \
       --tris 27505,21474,21489 --times 0:20:0.25,60:89:0.25 --out <report.json>
Each time is evaluated the way scripts/cv1_clip_check.py does (action, helpers, interaction states, correctives from
the final pose). For every listed soup triangle it records the area ratio to rest, whether it faces against its rest
neighbours (flip), and the same ratio with every corrective morph at zero (skinning and helpers only). The active
corrective channels near the worst time are listed. Nothing is saved to the BLEND.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Quaternion

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser
from cv1_soup import Soup, tri_area

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--rules", "--contract", "--tris", "--times", "--out", "--frame", "--abduction", "--flexion"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
config = interaction.load(ROOT / args.interaction)
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
limits = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))["limits"]
watch = [int(t) for t in args.tris.split(",")]
times = []
for part in args.times.split(","):
    a, b, step = (float(x) for x in part.split(":"))
    n = int(round((b - a) / step))
    times += [a + i * step for i in range(n + 1)]

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (source, target):
    target.actions = [config["clip"]]
action = bpy.data.actions[config["clip"]]
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]


def zero_keys():
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0


arm.animation_data_create()
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
zero_keys()
bpy.context.view_layer.update()
soup = Soup(meshes, limits)
soup.set_rest()
arm.animation_data.action = action


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def measure():
    points = soup.evaluated_points()
    agreement = soup.normal_agreement(points)
    out = {}
    for t in watch:
        out[str(t)] = {"ratio": round(tri_area(points, soup.tris[t]) / soup.rest_area[t], 4),
                       "flipped": bool(agreement[t] is not None and soup.rest_agreement[t] is not None and soup.rest_agreement[t] > 0.5 and agreement[t] < 0.0)}
    return out



contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
poser = ContractPoser(arm, contract, {})
base_t = float(args.frame)
grid = []
for a in [float(x) for x in args.abduction.split(",")]:
    for f in [float(x) for x in args.flexion.split(",")]:
        frame = math.floor(base_t)
        scene.frame_set(frame, subframe=base_t - frame)
        arm.animation_data.action = None  # hold the clip pose, then override the left upper arm
        pb = arm.pose.bones["upper_arm.L"]
        q = Quaternion((1, 0, 0, 0))
        q = q @ poser.step_rotation({"bone": "upper_arm.L", "kind": "twist", "about": "forward", "degrees": a}, "L", 1.0)
        q = q @ poser.step_rotation({"bone": "upper_arm.L", "kind": "twist", "about": "right", "degrees": f}, "L", 1.0)
        pb.rotation_quaternion = q
        bpy.context.view_layer.update()
        pose = pose_rel()
        for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
            arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
            pose[name] = quaternion
        bpy.context.view_layer.update()
        states = interaction.states_at(config, base_t)
        state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
        zero_keys()
        for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
            bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
        bpy.context.view_layer.update()
        points = soup.evaluated_points()
        m = soup.measure(points)
        w = measure()
        grid.append({"abduction": a, "flexion": f, "collapsed": m["collapsed_triangles"], "min_ratio": round(m["min_triangle_area_ratio"], 4),
                     "collapsed_tris": [e["triangle"] for e in m["collapsed_examples"]], "flips": m["flipped_triangles"], "watch": w})
        arm.animation_data.action = action
Path(args.out).write_text(json.dumps({"clip_blend": args.clip_blend, "frame": base_t, "grid": grid}, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
for row in grid:
    print("G a=%5.1f f=%5.1f collapsed=%d min=%.4f tris=%s flips=%d 21489=%.3f%s" % (row["abduction"], row["flexion"], row["collapsed"], row["min_ratio"], row["collapsed_tris"][:3], row["flips"], row["watch"]["21489"]["ratio"], " FLIP" if row["watch"]["21489"]["flipped"] else ""))
