"""Inspect downloaded native OBJ hand before rigging; retain original polygons.

Run in factory-startup Blender with autoexec disabled. No private/API/global
access, source overwrite, modifiers, rigging, or shape corrections.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inspect_ro_batch_source import components
from ro_review_common import stage, camera, material

OP = "ro-hand-structure-20261003-001"
RAW = ROOT / "assets/raw/ro-swordsman-combo/rodin-v007/right-hand"
QA = ROOT / "runs/qa/ro-swordsman-combo-r007/hand-source"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r007/hand-source"
assert not QA.exists() and not OUT.exists(), "Preserve completed inspections"
journal = json.loads((ROOT / f"runs/hyper3d/operations/{OP}.json").read_text())
assert journal["state"] == "downloaded"
bound = {}
for item in journal["downloads"]:
    p = (ROOT / item["path"]).resolve(strict=True)
    assert p.is_relative_to(RAW.resolve())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
    assert p.stat().st_size == item["bytes"]
    bound[p] = item
objects = [p for p in bound if p.suffix.lower() == ".obj"]
assert len(objects) == 1, "Inspect changed native-output package before import"
source = objects[0]
text = source.read_text(encoding="utf-8-sig")
native_faces = [line.split()[1:] for line in text.splitlines() if line.startswith("f ")]
native_hist = Counter(map(len, native_faces))
assert native_faces and all(n >= 3 for n in native_hist)


def dependency(parent, name):
    candidate = (parent / name).resolve(strict=True)
    assert candidate.is_relative_to(RAW.resolve()) and candidate in bound, name
    return candidate


mtls = []
for line in text.splitlines():
    if line.startswith("mtllib "):
        names = shlex.split(line[7:], posix=True)
        assert names, "Missing material library name"
        mtls.extend(dependency(source.parent, n) for n in names)
dependencies = []
for mtl in mtls:
    for line in mtl.read_text(encoding="utf-8-sig").splitlines():
        key = line.split(maxsplit=1)[0] if line.strip() else ""
        if key.lower().startswith("map_") or key.lower() in {"bump", "disp", "norm"}:
            fields = shlex.split(line, posix=True)
            assert len(fields) >= 2
            dependencies.append(dependency(mtl.parent, fields[-1]))
QA.mkdir(parents=True)
OUT.mkdir(parents=True)
started = datetime.now(timezone.utc)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
import_operator = bpy.ops.wm.obj_import.get_rna_type()
default_axes = {n: import_operator.properties[n].default for n in ["forward_axis", "up_axis"]}
bpy.ops.wm.obj_import(filepath=str(source), forward_axis="NEGATIVE_Z", up_axis="Y")
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert meshes
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
lo = Vector([min(p[i] for p in points) for i in range(3)])
hi = Vector([max(p[i] for p in points) for i in range(3)])
extent = hi - lo
assert extent.z > 1e-6
factor = .265 / extent.z
origin = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
mesh_stats = []
topology = []
for index, ob in enumerate(meshes):
    native_world = ob.matrix_world.copy()
    for v in ob.data.vertices:
        v.co = (native_world @ v.co - origin) * factor
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.name = f"SM_RO_RightHand_Native_{index:02d}"
    ob.data.update()
    ob.data.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    stats = {
        "object": ob.name, "vertices": len(ob.data.vertices), "polygons": len(ob.data.polygons),
        "triangles": len(ob.data.loop_triangles),
        "polygon_sides": dict(Counter(len(p.vertices) for p in ob.data.polygons)),
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "nonmanifold_edges_including_boundary": sum(not e.is_manifold for e in bm.edges),
        "vertex_valence_histogram": dict(Counter(len(v.link_edges) for v in bm.verts)),
        "non_four_valence_vertex_ids": [v.index for v in bm.verts if len(v.link_edges) != 4],
        "components": [{k: v for k, v in c.items() if k != "polygon_indices"} for c in components(ob.data)],
        "uv_layers": [layer.name for layer in ob.data.uv_layers],
        "materials": [m.name if m else None for m in ob.data.materials],
    }
    bm.free()
    mesh_stats.append(stats)
    topology.append({"object": ob.name, "vertices": [list(v.co) for v in ob.data.vertices],
        "polygons": [{"id": p.index, "vertices": list(p.vertices), "material": p.material_index} for p in ob.data.polygons],
        "uv_per_corner": [{"name": layer.name, "uv": [list(x.uv) for x in layer.data]} for layer in ob.data.uv_layers]})
assert sum(len(ob.data.polygons) for ob in meshes) == len(native_faces), "Importer polygon-count mismatch"
# This actual native OBJ package has no MTL/usemtl. Reconstruct an explicit
# artist PBR setup from separately delivered maps; never alter raw downloads.
material_binding = None
if not mtls:
    assert all(ob.data.uv_layers for ob in meshes), "Missing source UV for separate maps"
    pbr = bpy.data.materials.new("M_RO_Hand_SourcePBR_Explicit")
    pbr.use_nodes = True
    nodes, links = pbr.node_tree.nodes, pbr.node_tree.links
    shader = nodes.get("Principled BSDF")
    bindings = {"Base Color": "texture_pbr.png", "Metallic": "texture_metallic.png",
                "Roughness": "texture_roughness.png", "Normal": "texture_normal.png"}
    for socket, name in bindings.items():
        image_path = dependency(RAW, name)
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(image_path), check_existing=True)
        if socket != "Base Color":
            node.image.colorspace_settings.name = "Non-Color"
        if socket == "Normal":
            normal = nodes.new("ShaderNodeNormalMap")
            links.new(node.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], shader.inputs["Normal"])
        else:
            links.new(node.outputs["Color"], shader.inputs[socket])
    for ob in meshes:
        ob.data.materials.clear()
        ob.data.materials.append(pbr)
        for polygon in ob.data.polygons:
            polygon.material_index = 0
    material_binding = {"raw_MTL_present": False, "raw_usemtl_present": False,
        "artist_PBR_reconstructed": True, "map_bindings": bindings,
        "original_material_graph_equivalence_claimed": False,
        "reason": "Actual API OBJ package supplies UV and separate maps without MTL; color map choice still subject to visual review"}
for image in bpy.data.images:
    if image.type == "IMAGE" and image.size[0] and not image.packed_file:
        image.pack()
image_stats = [{"name": i.name, "dimensions": list(i.size), "packed": bool(i.packed_file)}
               for i in bpy.data.images if i.type == "IMAGE"]
assert image_stats and all(i["packed"] for i in image_stats)
(QA / "native-topology.json").write_text(json.dumps(topology, indent=2) + "\n", encoding="utf-8")
stage()
scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
target = (0, 0, .1325)
views = {"front": (0, -1, .145), "back": (0, 1, .145), "right": (1, 0, .145),
         "left": (-1, 0, .145), "three-quarter": (.65, -1, .35),
         "cuff": (0, -.20, -.65)}
for name, location in views.items():
    camera((location, target, .33))
    scene.render.filepath = str(QA / (name + ".png"))
    bpy.ops.render.render(write_still=True)
camera((views["three-quarter"], target, .33))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "right_hand_native_source.blend"))
# Gray and wire diagnostics in memory only; material source BLEND remains intact.
gray = material("DiagnosticGray", (.55, .55, .55), rough=.65)
saved = [(ob, list(ob.data.materials), [p.material_index for p in ob.data.polygons]) for ob in meshes]
for ob in meshes:
    ob.data.materials.clear()
    ob.data.materials.append(gray)
    for polygon in ob.data.polygons:
        polygon.material_index = 0
for name in ["front", "back", "three-quarter"]:
    camera((views[name], target, .33))
    scene.render.filepath = str(QA / ("gray-" + name + ".png"))
    bpy.ops.render.render(write_still=True)
wire = material("DiagnosticWire", (.005, .007, .009), rough=1)
for ob in meshes:
    ob.data.materials.append(wire)
    mod = ob.modifiers.new("NativePolygonWireDiagnostic", "WIREFRAME")
    mod.thickness = .00028
    mod.use_replace = False
    mod.material_offset = 1
for name in ["front", "back", "three-quarter"]:
    camera((views[name], target, .33))
    scene.render.filepath = str(QA / ("wire-" + name + ".png"))
    bpy.ops.render.render(write_still=True)
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "started_utc": started.isoformat(),
    "tool": bpy.app.version_string, "operation_id": OP, "consumed_credits": journal["consumed_credits"],
    "source": bound[source], "download_dependencies_verified": [bound[p] for p in set(mtls + dependencies)],
    "native_OBJ_polygon_sides": dict(native_hist), "native_OBJ_polygons": len(native_faces),
    "imported_native_face_count_preserved": True, "importer_default_axes": default_axes,
    "explicit_import_axes": {"forward_axis": "NEGATIVE_Z", "up_axis": "Y"},
    "source_bounds_after_axis_import": {"min": list(lo), "max": list(hi)},
    "display_normalization": {"total_extent_z_m": .265, "scale": factor,
        "hand_length_185mm_or_forearm_80mm_verified": False, "purpose": "Source visualization only; locate actual wrist before fitting"},
    "mesh_stats": mesh_stats, "images": image_stats, "source_geometry_corrections": 0,
    "material_binding": material_binding,
    "rig_created": False, "anatomy_art_review": "pending", "animation_topology_accepted": False,
    "rig_accepted": False, "deformation_accepted": False, "contact_accepted": False,
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(OUT.iterdir()) + sorted(QA.glob("*.png")) + [QA / "native-topology.json"]],
    "limitations": ["Quad count/closed manifold alone does not establish useful joint loops",
                    "No rig or posed skin exists yet; source render is not animation acceptance"],
}
for p, item in bound.items():
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
(QA / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("RO_NATIVE_HAND " + json.dumps({"meshes": len(meshes), "native_polygons": len(native_faces),
    "polygon_sides": dict(native_hist), "triangles": sum(s["triangles"] for s in mesh_stats), "images": image_stats}))
