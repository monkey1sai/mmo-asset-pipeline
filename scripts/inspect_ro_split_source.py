"""Read one downloaded part into an exclusive normalized inspection master."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_review_common import stage

HEIGHTS = {"core": 1.74, "cuirass": .40, "pauldron": .27,
           "bracer": .29, "coat": .62, "sword": 1.07}
parser = argparse.ArgumentParser()
parser.add_argument("--part", choices=HEIGHTS, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
part = args.part
operation = f"ro-split-{part}-20261003-001"
journal_path = ROOT / "runs/hyper3d/operations" / f"{operation}.json"
journal = json.loads(journal_path.read_text(encoding="utf-8"))
if journal["state"] != "downloaded" or journal["operation_id"] != operation:
    raise RuntimeError("Only the bound completed download is eligible")
raw_dir = ROOT / f"assets/raw/ro-swordsman-combo/rodin-v003/{part}"
models = [raw_dir / x["name"] for x in journal["downloads"] if x["name"].lower().endswith(".glb")]
if len(models) != 1:
    raise RuntimeError("Expected exactly one downloaded GLB; inspect any changed output contract")
source = models[0].resolve(strict=True)
expected = next(x["sha256"] for x in journal["downloads"] if x["name"] == source.name)
if not source.is_relative_to(raw_dir.resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise RuntimeError("Raw hash/path mismatch")
out = ROOT / f"assets/processed/ro-swordsman-combo-r004/sources/{part}"
qa = ROOT / f"runs/qa/ro-swordsman-combo-r004/sources/{part}"
if out.exists() or qa.exists():
    raise RuntimeError("Existing source inspection must be preserved")
out.mkdir(parents=True)
qa.mkdir(parents=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
if not points:
    raise RuntimeError("Downloaded model has no mesh")
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
if high.z - low.z <= 1e-6:
    raise RuntimeError("Unexpected flat vertical bounds; orientation requires review")
factor = HEIGHTS[part] / (high.z - low.z)
center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
stats = []
for index, ob in enumerate(meshes):
    world = ob.matrix_world.copy()
    for v in ob.data.vertices:
        v.co = (world @ v.co - center) * factor
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.name = f"SM_RO_{part}_{index}"
    ob.data.update()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    remaining = set(bm.verts)
    components = []
    while remaining:
        stack = [remaining.pop()]
        comp = []
        while stack:
            vertex = stack.pop()
            comp.append(vertex)
            for edge in vertex.link_edges:
                neighbor = edge.other_vert(vertex)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append({"vertices": len(comp),
            "min": [min(v.co[i] for v in comp) for i in range(3)],
            "max": [max(v.co[i] for v in comp) for i in range(3)]})
    stats.append({"name": ob.name, "vertices": len(ob.data.vertices),
        "triangles": sum(len(f.vertices) - 2 for f in ob.data.polygons),
        "nonmanifold_after_diagnostic_weld": sum(not e.is_manifold for e in bm.edges),
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "components": sorted(components, key=lambda x: -x["vertices"]),
        "uv_layers": len(ob.data.uv_layers), "materials": [m.name for m in ob.data.materials if m]})
    bm.free()
for image in bpy.data.images:
    if image.type == "IMAGE" and image.size[0] and not image.packed_file:
        image.pack()
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.gltf(filepath=str(out / f"{part}_source.glb"), export_format="GLB",
    use_selection=True, export_animations=False, export_yup=True)
stage()
scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
height = HEIGHTS[part]
target = Vector((0, 0, height * .52))
radius = max(height * 2.4, .7)
views = {"front": (0, -radius, height * .65), "side": (radius, 0, height * .65),
    "back": (0, radius, height * .65), "three-quarter": (radius * .7, -radius, height * .8),
    "detail": (radius * .35, -radius, height * .9)}
for name, location in views.items():
    cam = scene.camera
    cam.location = location
    aim = target if name != "detail" else Vector((0, 0, height * .76))
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = height * (1.35 if name != "detail" else .65)
    scene.render.filepath = str(qa / f"{name}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{part}_source.blend"))
report = {"operation_id": operation, "source": source.relative_to(ROOT).as_posix(),
    "source_sha256": expected, "tool": bpy.app.version_string,
    "normalization": {"height_planning_m": height, "factor": factor, "original_min": list(low), "original_max": list(high),
        "note": "Whole-object scale only; part orientation and fit still require actual assembly review."},
    "mesh_stats": stats, "images": [{"name": x.name, "size": list(x.size), "packed": bool(x.packed_file)} for x in bpy.data.images if x.type == "IMAGE"],
    "bones": sum(len(o.data.bones) for o in bpy.data.objects if o.type == "ARMATURE"),
    "animations": len(bpy.data.actions), "acceptance": "Source inspection only; no automatic art, rig or final delivery pass",
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir() if p.suffix in {".blend", ".glb"}]}
(qa / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise RuntimeError("Raw source changed")
print("RO_SPLIT_SOURCE " + json.dumps({"part": part, "triangles": sum(x["triangles"] for x in stats), "report": str(qa / "inspection.json")}))
