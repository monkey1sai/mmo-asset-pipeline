"""P1 closed loop: export the real whole character and its Blender-evaluated reference.

Run: blender -b --factory-startup --disable-autoexec <ro_whole_baseline.blend> --python scripts/cv1_p1_export_reference.py
The source BLEND is never saved; every edit below lives in memory only. Outputs are new files and
existing ones are not overwritten.
"""
from array import array
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math

QA = ROOT / "runs/qa/ro-swordsman-character-v1/p1"
OUT = ROOT / "assets/processed/ro-swordsman-character-v1/p1-closed-loop"
START = json.loads((QA / "phase-start.json").read_text(encoding="utf-8"))
ARMATURE = "ARM_RO_Swordsman"
ID_ATTRIBUTE = "_CV1_ID"
WRIST_KEYS = [("WristVolume_025", 0.0, 0.25, 0.5), ("WristVolume_050", 0.25, 0.5, 0.75),
              ("WristVolume_075", 0.5, 0.75, 1.0), ("WristVolume_100", 0.75, 1.0, None)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    path = Path(path)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def new_file(path):
    if Path(path).exists():
        raise SystemExit(f"REFUSE_OVERWRITE {path}")
    return Path(path)


assert Path(bpy.data.filepath).resolve() == (ROOT / START["source"]["path"]).resolve(), bpy.data.filepath
assert sha(bpy.data.filepath) == START["source"]["sha256"]
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
arm = bpy.data.objects[ARMATURE]
meshes = sorted((o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm), key=lambda o: o.name)
assert len(meshes) == 10 and all(o.matrix_world == arm.matrix_world for o in meshes)
for obj in meshes:
    attr = obj.data.attributes.new(ID_ATTRIBUTE, "FLOAT", "POINT")
    attr.data.foreach_set("value", [float(i) for i in range(len(obj.data.vertices))])


def set_frame(frame):
    whole = math.floor(frame)
    scene.frame_set(whole, subframe=frame - whole)


def rest_local(bone):
    return bone.parent.matrix_local.inverted() @ bone.matrix_local if bone.parent else bone.matrix_local.copy()


def pose_rel():
    """Rest-relative local rotation of every bone from evaluated pose matrices, (w, x, y, z)."""
    out = {}
    for pb in arm.pose.bones:
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix.copy()
        out[pb.name] = tuple((rest_local(pb.bone).inverted() @ local).to_quaternion())
    return out


def positions():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    data = array("d")
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        assert len(mesh.vertices) == len(obj.data.vertices)
        world = evaluated.matrix_world
        for vertex in mesh.vertices:
            data.extend(world @ vertex.co)
        evaluated.to_mesh_clear()
    return data


def key_values():
    return {f"{o.name}/{k.name}": k.value for o in meshes if o.data.shape_keys for k in o.data.shape_keys.key_blocks[1:]}


# Probe rules. The target is the authored frame-61 pose, as pre-registered.
set_frame(61)
target = pose_rel()["hand.R"]
rules = {
    "schema_version": 1, "id": "ro-swordsman-character-v1-p1-probe", "status": "probe_for_wiring_only_not_accepted_corrective",
    "quaternion_convention": "wxyz; rest-relative local rotation of the bone; Blender bone-local axes",
    "drivers": {
        "wrist_progress.R": {"type": "rotation_difference", "bone": "hand.R", "target_quaternion_wxyz": list(target),
                             "target_source": "authored action RO_WristGrip_Prototype_61f frame 61"},
        "grasp.R": {"type": "state", "key": "grasp.R"},
    },
    "channels": [{"mesh": "SM_RO_WristLoft.R", "morph": name, "owner": "runtime_evaluator", "kind": "body_pose", "driver": "wrist_progress.R",
                  "curve": {"type": "hat", "prev": prev, "at": at, "next": nxt}} for name, prev, at, nxt in WRIST_KEYS]
    + [{"mesh": "SM_RO_glove.R", "morph": "GripContact_R", "owner": "runtime_evaluator", "kind": "contact_state", "driver": "grasp.R", "curve": {"type": "linear"}}],
}
rules_math.validate_rules(rules)
rules_path = new_file(OUT / "p1-probe-rules.json")
rules_path.write_text(json.dumps(rules, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

# Does the pose rule reproduce the authored time curves?
fidelity = []
for frame in range(1, 62):
    set_frame(frame)
    authored = key_values()
    computed = rules_math.evaluate(rules, pose_rel(), {"grasp.R": authored["SM_RO_glove.R/GripContact_R"]})
    fidelity.append({"frame": frame, "max_abs_difference": max(abs(computed[(m, k)] - authored[f"{m}/{k}"]) for m, k in computed)})
rule_fidelity_max = max(row["max_abs_difference"] for row in fidelity)

EXPORT = dict(export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_skins=True, export_all_influences=False,
              export_def_bones=False, export_rest_position_armature=True, export_morph=True, export_morph_normal=True,
              export_animations=True, export_animation_mode="SCENE", export_anim_scene_split_object=False, export_force_sampling=True,
              export_frame_range=True, export_frame_step=1, export_optimize_animation_size=False, export_attributes=True)
available = bpy.ops.export_scene.gltf.get_rna_type().properties
assert all(name in available for name in EXPORT), [name for name in EXPORT if name not in available]


def export(path, **extra):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes + [arm]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    set_frame(1)
    bpy.ops.export_scene.gltf(filepath=str(new_file(path)), **EXPORT, **extra)
    return artifact(path)


SAMPLES = START["preregistered"]["samples"]
bin_path = new_file(QA / "blender-reference.f64.bin")
blob = array("d")
blocks = []


def record(label, **info):
    data = positions()
    blocks.append({"label": label, "offset_values": len(blob), "values": len(data), **info})
    blob.extend(data)


# Baked owner: authored time curves stay in the clip; images omitted to keep this variant small.
baked_glb = export(OUT / "ro_character_p1_baked_owner.glb", export_morph_animation=True, export_image_format="NONE")
for sample in SAMPLES:
    set_frame(sample["frame"])
    record(f"baked/frame-{sample['frame']}", mode="baked_owner", frame=sample["frame"], time_s=(sample["frame"] - 1) / scene.render.fps, morph_weights=key_values())

# Runtime owner: remove the morph time curves so the clip carries bones only.
for obj in meshes:
    if obj.data.shape_keys:
        obj.data.shape_keys.animation_data_clear()
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0.0
runtime_glb = export(OUT / "ro_character_p1_runtime_owner.glb", export_morph_animation=False)


def apply_rules(state):
    pose = pose_rel()
    weights = rules_math.evaluate(rules, pose, state)
    for (mesh_name, key_name), value in weights.items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    return {"drivers": rules_math.driver_values(rules, pose, state), "morph_weights": {f"{m}/{k}": v for (m, k), v in weights.items()},
            "hand.R_rel_wxyz": list(pose["hand.R"])}


for sample in SAMPLES:
    set_frame(sample["frame"])
    info = apply_rules({"grasp.R": sample["grasp"]})
    record(f"runtime/frame-{sample['frame']}", mode="runtime_owner", frame=sample["frame"], time_s=(sample["frame"] - 1) / scene.render.fps, grasp=sample["grasp"], **info)

# Renders at p = 0, partial, 1 from one fixed orthographic camera on the right wrist.
RENDER_FRAMES = [1, 31, 61]
focus = [bpy.data.objects["SM_RO_glove.R"], bpy.data.objects["SM_RO_WristLoft.R"]]
low, high = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for frame in RENDER_FRAMES:
    set_frame(frame)
    apply_rules({"grasp.R": 1.0})
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in focus:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            for axis in range(3):
                low[axis], high[axis] = min(low[axis], vertex.co[axis]), max(high[axis], vertex.co[axis])
        evaluated.to_mesh_clear()
center = (low + high) / 2
direction = Vector((-0.8, -1.0, 0.5)).normalized()
camera = bpy.data.objects["ReviewCamera"]
camera.data.type = "ORTHO"
camera.data.ortho_scale = round((high - low).length * 1.5, 4)
camera.location = center + direction * 2.0
camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
camera.data.clip_start, camera.data.clip_end = 0.05, 10.0
scene.camera = camera
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.62, 0.62, 0.62)
scene.render.resolution_x = scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
bpy.data.objects["Plane"].hide_render = True
bpy.data.objects["SM_RO_sword"].hide_render = False
renders = []
for frame in RENDER_FRAMES:
    set_frame(frame)
    info = apply_rules({"grasp.R": 1.0})
    target_png = new_file(QA / f"blender-wrist-frame-{frame:03d}.png")
    scene.render.filepath = str(target_png)
    bpy.ops.render.render(write_still=True)
    renders.append({"frame": frame, "grasp": 1.0, **info, "image": artifact(target_png)})

# Blend sample: per-bone slerp/lerp of the frame-1 and frame-61 poses at 0.5, the way a mixer combines two paused actions.
def capture():
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones}


set_frame(1)
pose_a = capture()
set_frame(61)
pose_b = capture()
arm.animation_data.action = None
for pb in arm.pose.bones:
    (la, qa, sa), (lb, qb, sb) = pose_a[pb.name], pose_b[pb.name]
    pb.location, pb.rotation_quaternion, pb.scale = la.lerp(lb, 0.5), qa.slerp(qb, 0.5), sa.lerp(sb, 0.5)
bpy.context.view_layer.update()
info = apply_rules({"grasp.R": 0.5})
record("runtime/blend-1-61-0.5", mode="runtime_owner_blend", frames=[1, 61], blend=0.5, grasp=0.5, **info)

bin_path.write_bytes(blob.tobytes())
offset, layout = 0, []
for obj in meshes:
    layout.append({"name": obj.name, "vertices": len(obj.data.vertices), "offset_values_in_block": offset,
                   "morphs": [k.name for k in obj.data.shape_keys.key_blocks[1:]] if obj.data.shape_keys else []})
    offset += 3 * len(obj.data.vertices)
index = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "blender_hash": bpy.app.build_hash.decode(),
    "source": START["source"], "source_saved": False, "source_sha256_after": sha(bpy.data.filepath),
    "phase_start": artifact(QA / "phase-start.json"), "rules": artifact(rules_path),
    "glb": {"runtime_owner": runtime_glb, "baked_owner": baked_glb}, "export_settings": {**EXPORT, "baked_owner_extra": {"export_morph_animation": True, "export_image_format": "NONE"},
                                                                                     "runtime_owner_extra": {"export_morph_animation": False}},
    "id_attribute": ID_ATTRIBUTE, "fps": scene.render.fps, "frame_to_time": "(frame - 1) / fps",
    "coordinates": "Blender world metres, Z up, -Y front; glTF (x, y, z) = Blender (x, z, -y)",
    "binary": {**artifact(bin_path), "dtype": "float64 little-endian", "values_per_vertex": 3}, "mesh_layout": layout, "blocks": blocks,
    "rule_fidelity": {"frames": 61, "max_abs_difference": rule_fidelity_max, "limit": 1e-3, "pass": rule_fidelity_max <= 1e-3, "worst": max(fidelity, key=lambda r: r["max_abs_difference"])},
    "rest_local_wxyz": {name: list(rest_local(arm.data.bones[name]).to_quaternion()) for name in ("lower_arm.R", "hand.R")},
    "camera": {"type": "ORTHO", "ortho_scale": camera.data.ortho_scale, "location": list(camera.location), "look_at": list(center), "resolution": 960},
    "renders": renders,
}
(new_file(QA / "blender-reference.json")).write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
assert index["source_sha256_after"] == START["source"]["sha256"]
print("CV1_P1_REFERENCE " + json.dumps({"rule_fidelity_max": rule_fidelity_max, "blocks": len(blocks), "glb": [runtime_glb["bytes"], baked_glb["bytes"]]}))
