"""Small actual baseline measurements; no model/global edits or acceptance claim."""
import hashlib
import json
from pathlib import Path
import struct
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006/baseline"
source = ROOT / "assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.blend"
destination = QA / "technical-measurements.json"
if destination.exists():
    raise RuntimeError("Preserve actual technical measurements")
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
rig = bpy.data.objects["ARM_RO_Swordsman"]
core = bpy.data.objects["SM_RO_core"]
points = [core.matrix_world @ v.co for v in core.data.vertices]
lower = [min(p[i] for p in points) for i in range(3)]
upper = [max(p[i] for p in points) for i in range(3)]
invalid = []
max_influences = 0
for ob in bpy.data.collections["COL_Character"].objects:
    if ob.type != "MESH":
        continue
    for v in ob.data.vertices:
        weights = [g.weight for g in v.groups if g.weight > 1e-8]
        max_influences = max(max_influences, len(weights))
        if len(weights) > 4 or abs(sum(weights) - 1) > 1e-5:
            invalid.append([ob.name, v.index, len(weights), sum(weights)])
glb = source.with_suffix(".glb").read_bytes()
length, kind = struct.unpack_from("<II", glb, 12)
assert kind == 0x4e4f534a
document = json.loads(glb[20:20 + length])
report = {
    "subject": {"path": source.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
    "core_rest_world_bounds": {"min": lower, "max": upper, "size": [upper[i] - lower[i] for i in range(3)]},
    "character_core_height_m": upper[2] - lower[2],
    "nominal_height_gate": abs((upper[2] - lower[2]) - 1.74) < .001,
    "rig_world_translation": list(rig.matrix_world.translation),
    "root_bone_head_rest": list(rig.data.bones["root"].head_local),
    "maximum_vertex_influences": max_influences, "invalid_weights": invalid,
    "bones": len(rig.data.bones), "root_bones": [b.name for b in rig.data.bones if b.parent is None],
    "all_mesh_armatures_bound": all(any(m.type == "ARMATURE" and m.object == rig for m in ob.modifiers)
        for ob in bpy.data.collections["COL_Character"].objects if ob.type == "MESH"),
    "exported_skins": len(document.get("skins", [])),
    "exported_joints": [len(skin["joints"]) for skin in document.get("skins", [])],
    "exported_animation_count": len(document.get("animations", [])),
    "external_images": [image["uri"] for image in document.get("images", []) if "uri" in image],
    "image_count": len(document.get("images", [])),
    "glb_fresh_roundtrip_performed": False, "deformation_accepted": False, "art_accepted": False,
    "exporter_warning": "More than one shader image node used for a texture; sampler behavior requires actual roundtrip inspection, not assumed harmless",
}
with destination.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
print("RO_HAND_TECHNICAL " + json.dumps(report))
