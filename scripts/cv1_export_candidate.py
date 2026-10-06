"""Export a character V1 candidate with a QA pose clip, and the Blender reference for runtime and readback checks.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_export_candidate.py -- \
       --contract <joint-range-contract.json> --rules <rules.json> --poses <poses.json> --motions <id,id,...> \
       --tag <name> --asset-dir <new assets dir> --qa-dir <new qa dir>
The QA clip holds one contract pose per frame (rest at frame 0, then each motion at the typical and the extreme
level), keyed on integer frames from 0 so the clip starts at t=0. Interaction states come from the motion's
contract entry. Two GLBs are written: runtime-owner (bones only; the corrective rules drive every morph) and
baked-owner (the same rules evaluated in Blender and keyed as morph weights). The reference stores the
Blender-evaluated position of every vertex with the rules applied, plus one two-action blend sample.
Integer frames only: consecutive frames are unrelated poses, so in-between times are not meaningful.
The BLEND is not saved; existing outputs are refused.
"""
from array import array
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math
from cv1_contract_pose import ContractPoser, pose_rel

parser = argparse.ArgumentParser()
for name in ("--contract", "--rules", "--poses", "--motions", "--tag", "--asset-dir", "--qa-dir"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
asset_dir, qa_dir = (ROOT / args.asset_dir).resolve(), (ROOT / args.qa_dir).resolve()
for folder in (asset_dir, qa_dir):
    if folder.exists():
        raise SystemExit(f"REFUSE_OVERWRITE {folder}")
    folder.mkdir(parents=True)
ID_ATTRIBUTE = "_CV1_ID"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    path = Path(path)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
poses = json.loads((ROOT / args.poses).read_text(encoding="utf-8"))
rules_math.validate_rules(rules)
source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
meshes = sorted((o for o in arm.children if o.type == "MESH"), key=lambda o: o.name)
assert all(o.matrix_world == arm.matrix_world for o in meshes) and arm.matrix_world.is_identity
poser = ContractPoser(arm, contract, poses)
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in arm.data.bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in arm.data.bones}
HELPERS = [h["bone"] for h in rules.get("helpers", [])]


def apply_helpers():
    """Helper bones follow their sources; the pose is read after every other bone is set."""
    bpy.context.view_layer.update()
    for name, quaternion in rules_math.helper_rotations(rules, pose_rel(arm), REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = quaternion
    bpy.context.view_layer.update()
state_keys = sorted({d["key"] for d in rules["drivers"].values() if d["type"] == "state"})

for obj in meshes:
    attribute = obj.data.attributes.new(ID_ATTRIBUTE, "FLOAT", "POINT")
    attribute.data.foreach_set("value", [float(i) for i in range(len(obj.data.vertices))])
arm.animation_data_clear()
for obj in meshes:
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0

# ---- QA clip: one contract pose per integer frame ----
frames = [{"frame": 0, "motion": None, "level": None, "state": {k: 0.0 for k in state_keys}}]
for motion_id in args.motions.split(","):
    for level_name, level in contract["levels"].items():
        frames.append({"frame": len(frames), "motion": motion_id, "level": level_name})
for row in frames:
    if row["motion"] is None:
        poser.reset()
    else:
        state = poser.apply(row["motion"], contract["levels"][row["level"]])
        row["state"] = {k: float(state.get(k, 0.0)) for k in state_keys}
    apply_helpers()
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=row["frame"])
        pb.keyframe_insert("location", frame=row["frame"])
        pb.keyframe_insert("scale", frame=row["frame"])
scene.frame_start, scene.frame_end = 0, len(frames) - 1
scene.render.fps = 60

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


def apply_rules(state, key_frame=None):
    pose = pose_rel(arm)
    weights = rules_math.evaluate(rules, pose, state)
    for (mesh_name, key_name), value in weights.items():
        block = bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name]
        block.value = value
        if key_frame is not None:
            block.keyframe_insert("value", frame=key_frame)
    bpy.context.view_layer.update()
    return {"drivers": rules_math.driver_values(rules, pose, state), "morph_weights": {f"{m}/{k}": v for (m, k), v in weights.items()}}


blob, blocks = array("d"), []


def record(label, **info):
    data = positions()
    blocks.append({"label": label, "offset_values": len(blob), "values": len(data), **info})
    blob.extend(data)


# ---- baked owner: the same rules evaluated here and keyed as morph weights; reference positions ----
for row in frames:
    scene.frame_set(row["frame"])
    info = apply_rules(row["state"], key_frame=row["frame"])
    record(f"all/frame-{row['frame']}", frame=row["frame"], time_s=row["frame"] / scene.render.fps, motion=row["motion"], level=row["level"], state=row["state"], **info)
baked_glb = export(asset_dir / f"{args.tag}_baked_owner.glb", export_morph_animation=True, export_image_format="NONE")

# ---- blend sample: rest and the last motion's typical frame at 0.5 / 0.5, as a mixer combines two paused actions ----
blend_target = next(row for row in reversed(frames) if row["level"] == "typical")
scene.frame_set(blend_target["frame"])
target_rotations = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}
arm.animation_data.action = None
for obj in meshes:
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
poser.reset()
for pb in arm.pose.bones:
    if pb.name not in HELPERS:
        pb.rotation_quaternion = pb.rotation_quaternion.slerp(target_rotations[pb.name], 0.5)
apply_helpers()
blend_state = {k: 0.5 * blend_target["state"][k] for k in state_keys}
info = apply_rules(blend_state)
record("blend/rest-and-frame", frames=[0, blend_target["frame"]], blend=0.5, state=blend_state, motion=blend_target["motion"], **info)

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
    "inputs": {"contract": artifact(ROOT / args.contract), "rules": artifact(ROOT / args.rules), "poses": artifact(ROOT / args.poses)},
    "glb": {"runtime_owner": runtime_glb, "baked_owner": baked_glb}, "export_settings": EXPORT,
    "id_attribute": ID_ATTRIBUTE, "fps": scene.render.fps, "frame_to_time": "frame / fps (first key at t=0)", "state_keys": state_keys,
    "coordinates": "Blender world metres, Z up, -Y front; glTF (x, y, z) = Blender (x, z, -y)",
    "binary": {**artifact(bin_path), "dtype": "float64 little-endian", "values_per_vertex": 3}, "mesh_layout": layout,
    "frames": frames, "blocks": blocks, "helper_bones": HELPERS,
    "helper_channels": "keyed in both GLBs at export; strip them from the runtime-owner GLB with scripts/cv1_strip_bone_channels.py so the evaluator is their only writer",
    "scope": "Integer-frame contract poses and one blend sample; not a gameplay clip.",
}
(qa_dir / "blender-reference.json").write_text(json.dumps(reference, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
assert reference["source_sha256_after"] == source["sha256"]
print("CV1_EXPORT_CANDIDATE " + json.dumps({"frames": len(frames), "blocks": len(blocks), "glb_bytes": [runtime_glb["bytes"], baked_glb["bytes"]],
                                            "morph_channels": len(rules["channels"]), "state_keys": state_keys}))
