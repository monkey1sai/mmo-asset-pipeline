"""Export one character V1 animation clip and its Blender reference for the runtime closed loop.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_export_clip.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --registry <interaction-registry.json> \
       --rules <rules.json> --tag <name> --asset-dir <new assets dir> --qa-dir <new qa dir> [--every 6] [--half 0,30,60,90]
Two GLBs, as scripts/cv1_export_candidate.py writes them for the QA pose clip: runtime-owner (bones only; strip the
helper bone channels afterwards with scripts/cv1_strip_bone_channels.py) and baked-owner (helpers keyed and the
rules evaluated here and keyed as morph weights on integer frames). The clip starts at t=0 (first key at frame 0); a loop clip ends with a closing key at frame `frames` equal to frame 0.
The reference stores the Blender-evaluated position of every vertex at integer frames every --every frames and at
the --half half frames (runtime-owner only: the baked variant holds weights on integer frames), with the interaction
states from the registered windows, plus one blend sample of two paused poses of the clip at 0.5 / 0.5.
The BLEND is not saved; existing outputs are refused.
"""
from array import array
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
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_contract_pose import pose_rel

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--registry", "--rules", "--tag", "--asset-dir", "--qa-dir"):
    parser.add_argument(name, required=True)
parser.add_argument("--every", type=int, default=6)
parser.add_argument("--half", default="")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
asset_dir, qa_dir = (ROOT / args.asset_dir).resolve(), (ROOT / args.qa_dir).resolve()
for folder in (asset_dir, qa_dir):
    if folder.exists():
        raise SystemExit(f"REFUSE_OVERWRITE {folder}")
ID_ATTRIBUTE = "_CV1_ID"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    path = Path(path)
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


config, registry_entry = interaction.registered(ROOT / args.registry, ROOT / args.interaction)
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
rules_math.validate_rules(rules)
source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
scene = bpy.context.scene
scene.render.fps = config["fps"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
meshes = sorted((o for o in arm.children if o.type == "MESH"), key=lambda o: o.name)
assert all(o.matrix_world == arm.matrix_world for o in meshes) and arm.matrix_world.is_identity
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in arm.data.bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in arm.data.bones}
HELPERS = [h["bone"] for h in rules.get("helpers", [])]
state_keys = sorted({d["key"] for d in rules["drivers"].values() if d["type"] == "state"})
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (src, dst):
    if config["clip"] not in src.actions:
        raise SystemExit(f"ACTION_NOT_IN_FILE {config['clip']}")
    dst.actions = [config["clip"]]
clip_action = bpy.data.actions[config["clip"]]
keyed = sorted({c.data_path.split('"')[1] for c in clip_action.fcurves if c.data_path.startswith("pose.bones")})
if set(keyed) & set(HELPERS):
    raise SystemExit("HELPER_BONES_KEYED")
if min(p.co.x for c in clip_action.fcurves for p in c.keyframe_points) != 0:
    raise SystemExit("CLIP_MUST_START_AT_FRAME_0")
# Loop clips carry a closing key at frame `frames` equal to frame 0, so the runtime wraps without a jump.
last = config["frames"] if config["loop"] else config["frames"] - 1

for obj in meshes:
    attribute = obj.data.attributes.new(ID_ATTRIBUTE, "FLOAT", "POINT")
    attribute.data.foreach_set("value", [float(i) for i in range(len(obj.data.vertices))])
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0
arm.animation_data_create()


def state_at(t):
    states = interaction.states_at(config, t)
    return {k: float(states.get(k, 0.0)) for k in state_keys}


def apply_helpers():
    bpy.context.view_layer.update()
    pose = pose_rel(arm)
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = quaternion
        pose[name] = quaternion
    bpy.context.view_layer.update()
    return pose


SOCKET = config.get("sword_socket")
BED_SOCKET = (Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()) if SOCKET else None
SWORD_KEYED = any(c.data_path.startswith('pose.bones["sword"]') for c in clip_action.fcurves)
if SOCKET and SWORD_KEYED:
    raise SystemExit("SOCKETED_CLIP_KEYS_SWORD (a socketed clip's sword follows its socket: hand.R's rest attachment or the bed transform; the exporter strips the channel)")
if SOCKET and arm.pose.bones["sword"].rotation_mode != "QUATERNION":
    raise SystemExit("SWORD_ROTATION_MODE_NOT_QUATERNION (the hand-socket reset writes rotation_quaternion)")


def place_sword(t):
    """Socket switch (mixer -> sockets -> helpers -> correctives): on the bed socket the sword bone holds its fixed world
    transform; on the hand socket it returns to its rest attachment to hand.R (a socketed clip does not key the sword,
    refused above, and frame_set leaves an unkeyed bone alone, so an earlier bed placement would carry over: GetUp
    samples the bed first)."""
    if SOCKET and interaction.socket_at(config, t) == "bed":
        bpy.context.view_layer.update()
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ BED_SOCKET
    elif SOCKET:
        sword = arm.pose.bones["sword"]
        sword.location, sword.rotation_quaternion, sword.scale = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0)


def go(t):
    frame = math.floor(t)
    scene.frame_set(frame, subframe=t - frame)
    place_sword(t)
    return apply_helpers()


# Working action: the clip's keys plus every bone (helpers from their rule) keyed on each integer frame 0..last,
# so the exporter writes the clip unchanged and the helpers carry their evaluated value in the baked variant.
arm.animation_data.action = clip_action
poses, matrices = {}, {}
for f in range(last + 1):
    go(f)
    # Location and scale travel with the rotation: the pelvis carries the clip's root motion (bob, sway, lying down).
    poses[f] = {pb.name: (tuple(pb.rotation_quaternion), tuple(pb.location), tuple(pb.scale)) for pb in arm.pose.bones}
    matrices[f] = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
work = bpy.data.actions.new(config["clip"] + "__export")
arm.animation_data.action = work
for f in range(last + 1):
    for pb in arm.pose.bones:
        rotation, location, scale = poses[f][pb.name]
        pb.rotation_quaternion, pb.location, pb.scale = Quaternion(rotation), location, scale
        pb.keyframe_insert("rotation_quaternion", frame=f)
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("scale", frame=f)
for curve in work.fcurves:
    # Same interpolation as the authored clip and as the runtime between sampled keys (linear); Bezier would ease
    # in and out of the first and last keys, and half-frame samples would no longer match the runtime.
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"
work.name = config["clip"]
clip_action.name = config["clip"] + "__source"
scene.frame_start, scene.frame_end = 0, last
# Self-check: the working action must reproduce every bone of the clip (plus helpers) on every integer frame.
worst = 0.0
for f in range(last + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    for pb in arm.pose.bones:
        if pb.name in HELPERS:
            continue
        worst = max(worst, max(abs(a - b) for row_a, row_b in zip(pb.matrix, matrices[f][pb.name]) for a, b in zip(row_a, row_b)))
if worst > 1e-6:
    raise SystemExit(f"EXPORT_ACTION_DIFFERS_FROM_CLIP {worst}")

EXPORT = dict(export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_skins=True, export_all_influences=False,
              export_def_bones=False, export_rest_position_armature=True, export_morph=True, export_morph_normal=True,
              export_animations=True, export_animation_mode="SCENE", export_anim_scene_split_object=False, export_force_sampling=True,
              export_frame_range=True, export_frame_step=1, export_optimize_animation_size=False, export_attributes=True, export_anim_slide_to_zero=False)


def export(path, **extra):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes + [arm]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    scene.frame_set(0)
    bpy.ops.export_scene.gltf(filepath=str(path), **EXPORT, **extra)
    return artifact(path)


asset_dir.mkdir(parents=True)
qa_dir.mkdir(parents=True)
runtime_glb = export(asset_dir / f"{args.tag}_runtime_owner.glb", export_morph_animation=False)


def positions():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    data = array("d")
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        assert len(mesh.vertices) == len(obj.data.vertices)
        for vertex in mesh.vertices:
            data.extend(evaluated.matrix_world @ vertex.co)
        evaluated.to_mesh_clear()
    return data


def apply_rules(pose, state, key_frame=None):
    weights = rules_math.evaluate(rules, pose, state)
    for (mesh_name, key_name), value in weights.items():
        block = bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name]
        block.value = value
        if key_frame is not None:
            block.keyframe_insert("value", frame=key_frame)
    bpy.context.view_layer.update()
    return {"drivers": rules_math.driver_values(rules, pose, state), "morph_weights": {f"{m}/{k}": v for (m, k), v in weights.items()}}


blob, blocks, frames = array("d"), [], []


def record(label, **info):
    data = positions()
    blocks.append({"label": label, "offset_values": len(blob), "values": len(data), **info})
    blob.extend(data)


# ---- baked owner: rules evaluated on every integer frame and keyed; reference blocks on the sampled times ----
sampled = set(range(0, last + 1, args.every)) | {last}
half = sorted(float(h) + 0.5 for h in args.half.split(",") if h.strip())
for f in range(last + 1):
    pose = go(f)
    state = state_at(f)
    info = apply_rules(pose, state, key_frame=f)
    if f in sampled:
        frames.append({"frame": f, "state": state, "baked_sample": True})
        record(f"all/frame-{f}", frame=f, time_s=f / scene.render.fps, motion=config["clip"], level=None, state=state, baked_sample=True, **info)
baked_glb = export(asset_dir / f"{args.tag}_baked_owner.glb", export_morph_animation=True, export_image_format="NONE")
for obj in meshes:
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
for t in half:
    pose = go(t)
    state = state_at(t)
    info = apply_rules(pose, state)
    frames.append({"frame": t, "state": state, "baked_sample": False})
    record(f"all/frame-{t}", frame=t, time_s=t / scene.render.fps, motion=config["clip"], level=None, state=state, baked_sample=False, **info)

# ---- blend sample: two paused poses of the clip at 0.5 / 0.5, as a mixer combines two paused actions ----
frame_a, frame_b = 0, (last + 1) // 2
if SOCKET:
    # Both blended frames in the same socket, so the runtime places the sword the same way (no blend across a switch).
    while frame_b > 1 and interaction.socket_at(config, frame_b) != interaction.socket_at(config, frame_a):
        frame_b -= 1
arm.animation_data.action = None
for pb in arm.pose.bones:
    if pb.name not in HELPERS:
        (rot_a, loc_a, scale_a), (rot_b, loc_b, scale_b) = poses[frame_a][pb.name], poses[frame_b][pb.name]
        # A mixer slerps quaternions and blends translation and scale linearly.
        pb.rotation_quaternion = Quaternion(rot_a).slerp(Quaternion(rot_b), 0.5)
        pb.location = [(a + b) / 2 for a, b in zip(loc_a, loc_b)]
        pb.scale = [(a + b) / 2 for a, b in zip(scale_a, scale_b)]
place_sword(frame_a)
pose = apply_helpers()
blend_state = {k: 0.5 * state_at(frame_a)[k] + 0.5 * state_at(frame_b)[k] for k in state_keys}
info = apply_rules(pose, blend_state)
record("blend/frame-and-frame", frames=[frame_a, frame_b], blend=0.5, state=blend_state, motion=config["clip"], **info)

bin_path = qa_dir / "blender-reference.f64.bin"
bin_path.write_bytes(blob.tobytes())
offset, layout = 0, []
for obj in meshes:
    layout.append({"name": obj.name, "vertices": len(obj.data.vertices), "offset_values_in_block": offset,
                   "morphs": [k.name for k in obj.data.shape_keys.key_blocks[1:]] if obj.data.shape_keys else []})
    offset += 3 * len(obj.data.vertices)
reference = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
    "source": source, "source_saved": False, "source_sha256_after": sha(ROOT / source["path"]),
    "inputs": {"clip_blend": artifact(ROOT / args.clip_blend), "interaction": artifact(ROOT / args.interaction), "registry_entry": registry_entry,
               "rules": artifact(ROOT / args.rules)},
    "glb": {"runtime_owner": runtime_glb, "baked_owner": baked_glb}, "export_settings": EXPORT,
    "id_attribute": ID_ATTRIBUTE, "fps": scene.render.fps, "frame_to_time": "frame / fps (first key at t=0)", "state_keys": state_keys,
    "coordinates": "Blender world metres, Z up, -Y front; glTF (x, y, z) = Blender (x, z, -y)",
    "binary": {**artifact(bin_path), "dtype": "float64 little-endian", "values_per_vertex": 3}, "mesh_layout": layout,
    "frames": frames, "blocks": blocks, "helper_bones": HELPERS, "clip": config["clip"], "clip_frames": config["frames"], "loop": config["loop"],
    "helper_channels": "keyed in both GLBs at export; strip them from the runtime-owner GLB with scripts/cv1_strip_bone_channels.py so the evaluator is their only writer",
    "sword_socket": None if not SOCKET else {
        "initial": SOCKET["initial"], "bed_socket": SOCKET["bed_socket"],
        "switches": [dict(s, frame=next(e["frame"] for e in config["events"] if e["name"] == s["event"])) for s in SOCKET["switches"]],
        "bed_socket_matrix_blender": [list(row) for row in BED_SOCKET],
        "sword_rest_matrix_blender": [list(row) for row in arm.matrix_world @ arm.data.bones["sword"].matrix_local],
        "blend_frames": [frame_a, frame_b],
        "channel": "sword bone keyed in both GLBs at export; strip it from the runtime-owner GLB so the runtime places the sword from the socket events (mixer -> sockets -> helpers -> correctives)"},
    "scope": "Sampled times of one clip (integer frames every --every frames and the listed half frames) and one blend sample; only these times are claimed.",
}
(qa_dir / "blender-reference.json").write_text(json.dumps(reference, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
assert reference["source_sha256_after"] == source["sha256"]
print("CV1_EXPORT_CLIP " + json.dumps({"clip": config["clip"], "blocks": len(blocks), "glb_bytes": [runtime_glb["bytes"], baked_glb["bytes"]], "half_frames": half}))
