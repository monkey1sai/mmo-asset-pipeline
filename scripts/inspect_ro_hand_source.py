"""Inspect one downloaded generated glove; preserve source and explicit unknown gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_ro_batch_source import bound_source, components
from ro_review_common import stage, camera

OP = "ro-hand-source-20261003-001"
QA = ROOT / "runs/qa/ro-swordsman-combo-r006/hand-source"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r006/hand-source"
if QA.exists() or OUT.exists():
    raise RuntimeError("Preserve prior inspection")
journal = json.loads((ROOT / f"runs/hyper3d/operations/{OP}.json").read_text())
assert journal["state"] == "downloaded"
source, source_sha = bound_source(ROOT, ROOT / "assets/raw/ro-swordsman-combo/rodin-v006/right-glove", journal["downloads"])
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if len(meshes) != 1:
    raise RuntimeError("Expected one glove; preserve and inspect output contract")
ob = meshes[0]
points = [ob.matrix_world @ v.co for v in ob.data.vertices]
lo = Vector([min(v[i] for v in points) for i in range(3)])
hi = Vector([max(v[i] for v in points) for i in range(3)])
if hi.z - lo.z < 1e-6:
    raise RuntimeError("Unexpected zero height")
factor = .195 / (hi.z - lo.z)
origin = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
matrix = ob.matrix_world.copy()
for v in ob.data.vertices:
    v.co = (matrix @ v.co - origin) * factor
ob.parent = None
ob.matrix_world = Matrix.Identity(4)
ob.name = "SM_RO_RightGlove_Source"
ob.data.update()
ob.data.calc_loop_triangles()
diagnostic = bmesh.new()
diagnostic.from_mesh(ob.data)
bmesh.ops.remove_doubles(diagnostic, verts=list(diagnostic.verts), dist=1e-6)
stats = {"vertices": len(ob.data.vertices), "triangles": len(ob.data.loop_triangles),
    "polygon_sides": {str(n): sum(len(p.vertices) == n for p in ob.data.polygons) for n in [3, 4]},
    "welded_vertices": len(diagnostic.verts), "weld_boundary_edges": sum(e.is_boundary for e in diagnostic.edges),
    "weld_nonmanifold_edges": sum(not e.is_manifold for e in diagnostic.edges),
    "components": [{k:v for k,v in c.items() if k != "polygon_indices"} for c in components(ob.data)],
    "uv_layers": [u.name for u in ob.data.uv_layers], "materials": [m.name for m in ob.data.materials],
    "normalized_height_m": .195, "source_min": list(lo), "source_max": list(hi), "factor": factor}
diagnostic.free()
for image in bpy.data.images:
    if image.type == "IMAGE" and image.size[0] and not image.packed_file:
        image.pack()
stats["images"] = [{"name": i.name, "dimensions": list(i.size), "packed": bool(i.packed_file)} for i in bpy.data.images if i.type == "IMAGE"]
QA.mkdir(parents=True)
OUT.mkdir(parents=True)
stage()
scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
target = Vector((0, 0, .095))
views = {"front": (0,-1,.12), "back": (0,1,.12), "right": (1,0,.12),
         "left": (-1,0,.12), "three-quarter": (.6,-1,.3), "cuff": (0,-.25,-.7)}
for name, location in views.items():
    camera((location, tuple(target), .29))
    scene.render.filepath = str(QA / (name + ".png"))
    bpy.ops.render.render(write_still=True)
bpy.context.scene.camera.location = (0,-1,.12)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "right_glove_source.blend"))
report = {"observed_utc": datetime.now(timezone.utc).isoformat(), "tool": bpy.app.version_string,
    "operation_id": OP, "consumed_credits": journal["consumed_credits"],
    "source": {"path": source.relative_to(ROOT).as_posix(), "sha256": source_sha},
    "stats": stats, "visual_review": "pending", "rig_accepted": False,
    "deformation_accepted": False, "contact_accepted": False,
    "topology_note": "GLB stores triangles; generated Quad request alone does not prove production edge flow",
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                  for p in sorted(OUT.iterdir()) + sorted(QA.glob("*.png"))]}
(QA / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
print("RO_GLOVE_SOURCE " + json.dumps(stats))
