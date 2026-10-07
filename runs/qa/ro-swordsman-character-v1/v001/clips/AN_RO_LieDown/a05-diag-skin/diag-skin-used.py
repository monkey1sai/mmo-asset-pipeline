"""Diagnostic (report only): left-armpit triangles along a cast clip, with and without corrective morphs.

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
from cv1_soup import Soup, tri_area

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--rules", "--contract", "--tris", "--times", "--out"):
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


rows = []
for t in times:
    frame = math.floor(t)
    scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    states = interaction.states_at(config, t)
    state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
    zero_keys()
    bpy.context.view_layer.update()
    skin_only = measure()
    weights = rules_math.evaluate(rules, pose, state)
    for (mesh_name, key_name), value in weights.items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    full = measure()
    active = sorted(((v, k) for (m, k), v in weights.items() if m == "SM_RO_core" and v > 0.01), reverse=True)[:6]
    rows.append({"t": t, "with_correctives": full, "skin_only": skin_only, "active_core_channels": [[k, round(v, 3)] for v, k in active]})

summary = {}
for t in watch:
    key = str(t)
    worst = min(rows, key=lambda r: r["with_correctives"][key]["ratio"])
    summary[key] = {"rest_at": soup.centre(soup.rest, t), "dominant": sorted({soup.dominant[i] for i in soup.tris[t]}),
                    "worst_t": worst["t"], "worst_ratio": worst["with_correctives"][key]["ratio"], "skin_only_at_worst": worst["skin_only"][key]["ratio"],
                    "flipped_times_with_correctives": [r["t"] for r in rows if r["with_correctives"][key]["flipped"]],
                    "flipped_times_skin_only": [r["t"] for r in rows if r["skin_only"][key]["flipped"]],
                    "active_at_worst": worst["active_core_channels"]}
Path(args.out).write_text(json.dumps({"clip_blend": args.clip_blend, "rules": args.rules, "times": len(times), "summary": summary, "rows": rows}, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_DIAG_ARMPIT " + json.dumps(summary))
