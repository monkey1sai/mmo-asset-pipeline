"""v001 source preparation: separate cuff lining, retain exterior UV, correct PBR.

Creates a new editable source specimen only; no rig or motion acceptance.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_hand_gate import segment_hit
from ro_review_common import camera

BASE = ROOT / "runs/qa/ro-swordsman-combo-r007"
QA = BASE / "v001-source-preparation"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r007/v001-source-preparation"
source = ROOT / "assets/processed/ro-swordsman-combo-r007/hand-source/right_hand_native_source.blend"
inspection = json.loads((BASE / "hand-source/inspection.json").read_text())
source_item = next(x for x in inspection["artifacts"] if x["path"].endswith(".blend"))
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_item["sha256"]
assert not QA.exists() and not OUT.exists()
start = json.loads((BASE / "v001-start.json").read_text())
clock = json.loads((BASE / "phase-start.json").read_text())
now = datetime.now(timezone.utc)
assert (now - datetime.fromisoformat(start["started_utc"])).total_seconds() < clock["budget"]["trial_seconds"]
assert (now - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds() < clock["budget"]["total_seconds"]
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects["SM_RO_RightHand_Native_00"]
raw = ROOT / "assets/raw/ro-swordsman-combo/rodin-v007/right-hand"
journal = json.loads((ROOT / "runs/hyper3d/operations/ro-hand-structure-20261003-001.json").read_text())
diffuse = next(i for i in journal["downloads"] if i["path"].endswith("texture_diffuse.png"))
assert hashlib.sha256((ROOT / diffuse["path"]).read_bytes()).hexdigest() == diffuse["sha256"]
shader = ob.data.materials[0].node_tree.nodes.get("Principled BSDF")
base_node = shader.inputs["Base Color"].links[0].from_node
base_node.image = bpy.data.images.load(str(raw / "texture_diffuse.png"), check_existing=True)
base_node.image.colorspace_settings.name = "sRGB"
base_node.image.pack()

# Identity survives selection/cut; UV checks below read actual BMesh output.
bm = bmesh.new(); bm.from_mesh(ob.data)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
v_id = bm.verts.layers.int.new("native_source_id")
f_id = bm.faces.layers.int.new("native_face_id")
uv = bm.loops.layers.uv.active
original_uv = {}
for v in bm.verts:
    v[v_id] = v.index + 1  # New cut vertices default to0, not a false original ID.
for f in bm.faces:
    f[f_id] = f.index + 1
    original_uv[f[f_id]] = {loop.vert[v_id]: tuple(loop[uv].uv) for loop in f.loops}
before_vertices = len(bm.verts); before_faces = len(bm.faces)
preexisting_verts = set(bm.verts)
wrist_source_z = .095
scale = .185 / (.265 - wrist_source_z)
cut_z = wrist_source_z - .080 / scale
result = bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
    dist=1e-7, plane_co=Vector((0, 0, cut_z)), plane_no=Vector((0, 0, 1)),
    clear_inner=True, clear_outer=False)
for v in bm.verts:
    if v not in preexisting_verts:
        v[v_id] = 0
remaining = set(bm.verts); components = []
while remaining:
    stack = [next(iter(remaining))]; vertices = set()
    while stack:
        v = stack.pop()
        if v not in remaining:
            continue
        remaining.remove(v); vertices.add(v)
        stack.extend(e.other_vert(v) for e in v.link_edges)
    components.append(vertices)
assert len(components) == 2, "Expected actual lining to separate after rim cut; preserve source otherwise"
outer = max(components, key=lambda c: max(v.co.z for v in c))
assert max(v.co.z for v in outer) > .25
lining = set(bm.verts) - outer
lining_max_z = max(v.co.z for v in lining)
assert lining_max_z < .13, "Lining selection must not remove fingers/palm exterior"
removed_lining_ids = sorted(v[v_id] - 1 for v in lining if v[v_id])
removed_lining_vertices = len(lining)
bmesh.ops.delete(bm, geom=list(lining), context="VERTS")
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
boundary = [e for e in bm.edges if e.is_boundary]
boundary_vertices = {v for e in boundary for v in e.verts}
assert all(sum(e.is_boundary for e in v.link_edges) == 2 for v in boundary_vertices)
ordered = []
current = min(boundary_vertices, key=lambda v: tuple(v.co)); previous = None
while current not in ordered:
    ordered.append(current)
    next_vertices = [e.other_vert(current) for e in current.link_edges if e.is_boundary and e.other_vert(current) != previous]
    nxt = next_vertices[0]
    previous, current = current, nxt
assert current == ordered[0] and len(ordered) == len(boundary_vertices)
assert all(abs(v.co.z - cut_z) < 2e-6 for v in boundary_vertices)

preserved_faces = []; cut_faces = []
for f in bm.faces:
    ids = [loop.vert[v_id] for loop in f.loops]
    if f[f_id] in original_uv and all(ids) and set(ids) == set(original_uv[f[f_id]]):
        for loop in f.loops:
            old = original_uv[f[f_id]][loop.vert[v_id]]
            assert (Vector(old) - loop[uv].uv).length < 1e-7
        preserved_faces.append(f[f_id] - 1)
    else:
        cut_faces.append(f[f_id] - 1)
for v in bm.verts:
    v.co *= scale
bm.normal_update()
bm.verts.index_update(); bm.faces.index_update()
mapping = [{"index": v.index, "native_source_id": v[v_id] - 1 if v[v_id] else None} for v in bm.verts]
boundary_ids = [v.index for v in ordered]
bm.to_mesh(ob.data); bm.free(); ob.data.update()
ob.name = "SM_RO_RightHand_Exterior"
tag = ob.data.attributes.get("r007_original_point_id") or ob.data.attributes.new("r007_original_point_id", "INT", "POINT")
for v, item in zip(ob.data.vertices, tag.data):
    item.value = v.index
mesh = ob.data; mesh.calc_loop_triangles()
points = [v.co.copy() for v in mesh.vertices]
triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
crossings = []
for i, j in tree.overlap(tree):
    if i >= j or set(triangles[i]) & set(triangles[j]):
        continue
    a = [points[k] for k in triangles[i]]; b = [points[k] for k in triangles[j]]
    if any(segment_hit(left[k], left[(k + 1) % 3], right) is not None
           for left, right in [(a, b), (b, a)] for k in range(3)):
        crossings.append([i, j])
QA.mkdir(); OUT.mkdir(parents=True)
for stage_ob in bpy.data.collections["COL_ReviewStage"].objects:
    if stage_ob.type == "MESH":
        stage_ob.hide_render = True  # Cuff view must not be blocked by floor.
target = (0, 0, .155)
for name, loc in {"front": (0, -1, .16), "back": (0, 1, .16),
                  "three-quarter": (.6, -1, .36), "bottom": (0, -.05, -.7)}.items():
    camera((loc, target, .35))
    bpy.context.scene.render.filepath = str(QA / (name + ".png"))
    bpy.ops.render.render(write_still=True)
camera(((.6, -1, .36), target, .35))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "right_hand_exterior.blend"))
report = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "trial": "v001",
    "source": source_item, "source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == source_item["sha256"],
    "material_correction": {"old_diagnostic_base_color": "texture_pbr.png", "new_base_color": diffuse,
        "color_space": "sRGB", "packed": True, "old_diagnostic_retained": True},
    "actual_source_double_layer_confirmed": True, "cut_source_z": cut_z,
    "component_count_after_cut_before_removal": len(components),
    "removed_lining_vertices": removed_lining_vertices, "removed_lining_source_ids": removed_lining_ids,
    "lining_source_max_z": lining_max_z, "single_ordered_boundary_loop": True,
    "boundary_vertices": boundary_ids, "boundary_edges": len(boundary),
    "source_wrist_plane_z": wrist_source_z, "uniform_scale": scale,
    "planned_wrist_to_top_m": .185, "planned_forearm_m": .080,
    "wrist_bone_center_verified": False, "fitted_to_character": False,
    "original_vertices": before_vertices, "original_faces": before_faces,
    "actual_vertices": len(mesh.vertices), "actual_polygons": len(mesh.polygons), "actual_triangles": len(triangles),
    "uv_actual_readback": {"unchanged_native_faces": preserved_faces, "cut_faces": cut_faces,
        "tolerance": 1e-7, "protected_face_corner_UV_pass": True},
    "vertex_mapping": mapping, "neutral_transverse_self_pairs": len(crossings),
    "neutral_crossing_pairs": crossings, "rig_created": False, "art_accepted": False,
    "limitations": ["Declared wrist plane is based on measured narrow source section; bone center still needs locating",
                    "Transverse self test excludes coplanar/tangential and adjacent folds; inspect actual views",
                    "No wrist/core fitting, thumb opposition or skin deformation acceptance yet"],
    "artifact": {"path": (OUT / "right_hand_exterior.blend").relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256((OUT / "right_hand_exterior.blend").read_bytes()).hexdigest()},
}
(QA / "preparation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("RO_EXTERIOR " + json.dumps({"triangles": len(triangles), "lining_removed": removed_lining_vertices,
    "boundary_edges": len(boundary), "neutral_self_pairs": len(crossings), "UV_readback": True}))
