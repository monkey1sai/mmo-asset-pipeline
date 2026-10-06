"""Extract the six visually identified source components without geometry welding."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_review_common import stage

SOURCE = ROOT / "assets/processed/ro-swordsman-combo-r005/batch-source/batch_source.blend"
EXPECTED = "515ac7758d1e928c3c4543fbfcaad16227e720e281e8a3885f2694bd9e559fc9"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r005/source-parts"
QA = ROOT / "runs/qa/ro-swordsman-combo-r005/source-parts"
MAPPING = {0: "coat", 1: "core", 2: "cuirass", 3: "pauldron", 4: "bracer", 5: "sword"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if OUT.exists() or QA.exists() or sha(SOURCE) != EXPECTED:
    raise RuntimeError("Source drift or existing extraction; preserve artifacts")
mapping = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r005/batch-source/component-polygon-map.json").read_text(encoding="utf-8"))
if len(mapping) != 1 or len(mapping[0]["components"]) != 6:
    raise RuntimeError("Reinspect unexpected component contract")
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
source = bpy.data.objects[mapping[0]["mesh"]]
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
parts = {}
reports = []
for group in mapping[0]["components"]:
    part = MAPPING[group["id"]]
    ob = source.copy()
    ob.data = source.data.copy()
    bpy.context.scene.collection.objects.link(ob)
    ob.name = "SM_RO_" + part
    keep = set(group["polygon_indices"])
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
    unused = [v for v in bm.verts if not v.link_faces]
    if unused:
        bmesh.ops.delete(bm, geom=unused, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    lo = Vector([min(v.co[i] for v in ob.data.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in ob.data.vertices) for i in range(3)])
    origin = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for v in ob.data.vertices:
        v.co -= origin
    ob.location = origin
    ob["source_component_id"] = group["id"]
    ob["source_master_sha256"] = EXPECTED
    parts[part] = ob
    triangles = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if triangles != group["triangles"]:
        raise RuntimeError("Extraction changed component faces")
    diagnostic = bmesh.new()
    diagnostic.from_mesh(ob.data)
    bmesh.ops.remove_doubles(diagnostic, verts=list(diagnostic.verts), dist=1e-6)
    reports.append({"part": part, "component_id": group["id"], "triangles": triangles,
        "dimensions_source_m": list(hi - lo), "source_origin": list(origin),
        "boundary_edges_after_diagnostic_weld": sum(e.is_boundary for e in diagnostic.edges),
        "nonmanifold_edges_after_diagnostic_weld": sum(not e.is_manifold for e in diagnostic.edges),
        "uv_layers": len(ob.data.uv_layers), "semantic_identification": "Observed front/back/3Q source images and component positions; not anatomy/fit acceptance."})
    diagnostic.free()
bpy.data.objects.remove(source, do_unlink=True)
meshes = list(parts.values())
for image in bpy.data.images:
    if image.type == "IMAGE" and image.size[0] and not image.packed_file:
        image.pack()
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts["core"]
bpy.ops.export_scene.gltf(filepath=str(OUT / "source_parts.glb"), export_format="GLB",
    use_selection=True, export_animations=False, export_yup=True)
scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
cam = scene.camera
for part, ob in parts.items():
    folder = QA / part
    folder.mkdir()
    for other in meshes:
        other.hide_render = other != ob
    height = ob.dimensions.z
    center = ob.location + Vector((0, 0, height * .5))
    extent = max(ob.dimensions)
    radius = max(2.0, extent * 2.5)
    for name, offset in {"front": (0, -radius, 0), "side": (radius, 0, 0),
            "back": (0, radius, 0), "three-quarter": (radius * .6, -radius, height * .2)}.items():
        cam.location = center + Vector(offset)
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = extent * 1.35
        scene.render.filepath = str(folder / (name + ".png"))
        bpy.ops.render.render(write_still=True)
core = parts["core"]
for other in meshes:
    other.hide_render = other != core
for side, x in (("R", -.43), ("L", .43)):
    target = core.location + Vector((x, -.08, .86))
    for view, offset in {"front": (0, -2, 0), "three-quarter": ((-.8 if side == "R" else .8), -2, .15)}.items():
        cam.location = target + Vector(offset)
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = .36
        scene.render.filepath = str(QA / "core" / ("hand_" + side + "_" + view + ".png"))
        bpy.ops.render.render(write_still=True)
for ob in meshes:
    ob.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "source_parts.blend"))
report = {"source": SOURCE.relative_to(ROOT).as_posix(), "source_sha256": EXPECTED,
    "parts": reports, "triangles": sum(x["triangles"] for x in reports),
    "six_editable_source_objects": True, "source_geometry_faces_preserved": True,
    "display_scale_only": True, "fit_anatomy_rig_animation_accepted": False,
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(OUT.iterdir())]}
(QA / "extraction.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if sha(SOURCE) != EXPECTED:
    raise RuntimeError("Source changed")
print("RO_BATCH_PARTS " + json.dumps({"triangles": report["triangles"], "parts": len(parts), "report": str(QA / "extraction.json")}))
