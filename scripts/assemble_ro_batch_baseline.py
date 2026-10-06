"""Fit source pieces into one neutral assembly baseline, preserving all sources."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_review_common import render_views

SOURCE = ROOT / "assets/processed/ro-swordsman-combo-r005/source-parts/source_parts.blend"
SOURCE_SHA = "a837d63b9a1f53e48c448001dc2ee89b47aa21de7ce6154135ebf122aee19928"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r005/baseline"
QA = ROOT / "runs/qa/ro-swordsman-combo-r005/baseline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(ob, scale, anchor, destination, rotation=None):
    rotation = rotation or Matrix.Identity(3)
    for v in ob.data.vertices:
        p = v.co - Vector(anchor)
        v.co = rotation @ Vector([p[i] * scale[i] for i in range(3)]) + Vector(destination)
    ob.location = (0, 0, 0)
    ob.data.update()
    ob["fit_scale"] = list(scale)
    ob["fit_anchor"] = list(anchor)
    ob["fit_destination"] = list(destination)


def mirror(source, name):
    ob = source.copy()
    ob.data = source.data.copy()
    bpy.context.scene.collection.objects.link(ob)
    ob.name = name
    for v in ob.data.vertices:
        v.co.x = -v.co.x
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    ob["mirrored_from"] = source.name
    return ob


if OUT.exists() or QA.exists() or sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError("Preserve source/existing baseline; do not reset")
clock = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r005/phase-accounting.json").read_text(encoding="utf-8"))
elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()
if elapsed >= clock["budget"]["total_seconds"]:
    raise RuntimeError("Original phase budget exhausted")
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
scene = bpy.context.scene
parts = {part: bpy.data.objects["SM_RO_" + part] for part in ("core", "cuirass", "pauldron", "bracer", "coat", "sword")}
core = parts["core"]
core.location = (0, 0, 0)
core["planning_height_m"] = 1.74
fit(parts["cuirass"], (.62, .45, .62), (0, 0, 0), (0, .015, .94))
fit(parts["coat"], (.70, .75, .63), (0, 0, 0), (0, .01, .46))
pauldron = parts["pauldron"]
pauldron.name = "SM_RO_pauldron.R"
fit(pauldron, (.40, .40, .40), (.03, 0, .45), (-.232, .015, 1.34), Matrix.Rotation(math.radians(15), 3, "Y"))
bracer = parts["bracer"]
bracer.name = "SM_RO_bracer.R"
fit(bracer, (.32, .35, .32), (0, 0, .315), (-.375, -.04, 1.025), Matrix.Rotation(math.radians(-7), 3, "Y"))
left_pauldron = mirror(pauldron, "SM_RO_pauldron.L")
left_bracer = mirror(bracer, "SM_RO_bracer.L")
sword = parts["sword"]
# Measure the actual widest guard section rather than assume the sheet's grip ratio.
max_x = max(abs(v.co.x) for v in sword.data.vertices)
guard_zs = sorted(v.co.z for v in sword.data.vertices if abs(v.co.x) > max_x * .9)
guard = guard_zs[len(guard_zs) // 2]
height = max(v.co.z for v in sword.data.vertices)
for v in sword.data.vertices:
    v.co.x *= .19 / (2 * max_x)
    v.co.y *= .22
    v.co.z = v.co.z * .24 / guard if v.co.z <= guard else .24 + (v.co.z - guard) * .83 / (height - guard)
grip_anchor = Vector((0, 0, .135))
direction = Vector((-.2, -.6, -.775)).normalized()
rotation = Vector((0, 0, 1)).rotation_difference(direction).to_matrix()
fit(sword, (1, 1, 1), grip_anchor, (-.435, -.105, .86), rotation)
sword["grip_anchor_world"] = [-.435, -.105, .86]
sword["planning_length_m"] = 1.07
sword["guard_source_z"] = guard
char = bpy.data.collections.new("COL_Character")
scene.collection.children.link(char)
meshes = list(parts.values()) + [left_pauldron, left_bracer]
for ob in meshes:
    for collection in list(ob.users_collection):
        collection.objects.unlink(ob)
    char.objects.link(ob)
    ob.hide_render = False
    ob["source_parts_sha256"] = SOURCE_SHA
triangles = sum(len(p.vertices) - 2 for ob in meshes for p in ob.data.polygons)
if triangles > 60000:
    raise RuntimeError("Assembled source exceeds unchanged triangle budget")
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = core
bpy.ops.export_scene.gltf(filepath=str(OUT / "ro_batch_assembly_baseline.glb"), export_format="GLB",
    use_selection=True, export_animations=False, export_yup=True)
render_views(QA)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "ro_batch_assembly_baseline.blend"))
sections = {}
for name, z in (("waist", .95), ("chest", 1.22), ("shoulder", 1.32), ("elbow", 1.10), ("wrist", .93), ("palm", .86), ("fingers", .79)):
    points = [v.co for v in core.data.vertices if abs(v.co.z - z) < .012]
    if points:
        sections[name] = {"min": [min(v[i] for v in points) for i in range(3)],
            "max": [max(v[i] for v in points) for i in range(3)], "vertices": len(points)}
report = {"source_sha256": SOURCE_SHA, "triangles": triangles, "object_count": len(meshes),
    "character_height_m": core.dimensions.z, "bone_count": 0, "animations": 0,
    "elapsed_from_original_phase_start_seconds": elapsed, "phase_clock_reset": False,
    "hand_sections": sections, "sword_length_planning_m": 1.07,
    "art_rig_animation_acceptance": "Not accepted; neutral fit baseline must be reviewed before rig and revisions.",
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
        "sha256": sha(p)} for p in sorted(OUT.iterdir())]}
(QA / "assembly.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError("Source changed")
print("RO_BATCH_BASELINE " + json.dumps({"triangles": triangles, "objects": len(meshes), "report": str(QA / "assembly.json")}))
