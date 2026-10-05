"""Inspect the authorized single core and compare unchanged source cores in one studio."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import stage, render_views
from inspect_ro_batch_source import bound_source, components

OP = 'ro-core-fallback-20261003-001'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/core-source-comparison'
OUT = ROOT / 'assets/processed/ro-swordsman-combo-r005/core-source-comparison'
OLD = ROOT / 'assets/processed/ro-swordsman-combo-r005/source-parts/source_parts.blend'
OLD_SHA = 'a837d63b9a1f53e48c448001dc2ee89b47aa21de7ce6154135ebf122aee19928'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def bounds(ob):
    points = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return Vector([min(v[i] for v in points) for i in range(3)]), Vector([max(v[i] for v in points) for i in range(3)])

def normalize(ob):
    lo, hi = bounds(ob)
    factor = 1.74 / (hi.z - lo.z)
    center = Vector(((lo.x + hi.x)/2, (lo.y + hi.y)/2, lo.z))
    matrix = ob.matrix_world.copy()
    for v in ob.data.vertices:
        v.co = (matrix @ v.co - center) * factor
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()
    return {'factor': factor, 'original_min': list(lo), 'original_max': list(hi), 'height_m': 1.74}

if QA.exists() or OUT.exists() or sha(OLD) != OLD_SHA:
    raise RuntimeError('Preserve old sources and previous inspection')
journal = json.loads((ROOT / f'runs/hyper3d/operations/{OP}.json').read_text(encoding='utf-8'))
if journal['state'] != 'downloaded':
    raise RuntimeError('Only completed local downloads can be inspected')
raw, raw_sha = bound_source(ROOT, ROOT / 'assets/raw/ro-swordsman-combo/rodin-v005/core', journal['downloads'])
phase = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text(encoding='utf-8'))
if (datetime.now(timezone.utc)-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds() >= phase['budget']['total_seconds']:
    raise RuntimeError('Original total budget exhausted')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(raw), disable_bone_shape=True)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if len(meshes) != 1:
    raise RuntimeError('Unexpected multi-mesh core; inspect explicitly')
new = meshes[0]
new.name = 'SM_RO_Core_Fallback_Source'
normalization_new = normalize(new)
with bpy.data.libraries.load(str(OLD), link=False) as (src, dst):
    dst.objects = ['SM_RO_core']
old = dst.objects[0]
bpy.context.scene.collection.objects.link(old)
old.name = 'SM_RO_Core_Batch_Source'
normalization_old = normalize(old)
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
for image in bpy.data.images:
    if image.type == 'IMAGE' and image.size[0] and not image.packed_file:
        image.pack()
stage()
reports = {}
for name, ob, norm in [('new', new, normalization_new), ('old', old, normalization_old)]:
    new.hide_render, old.hide_render = ob != new, ob != old
    render_views(QA / name)
    lo, hi = bounds(ob)
    diagnostic = bmesh.new(); diagnostic.from_mesh(ob.data)
    bmesh.ops.remove_doubles(diagnostic, verts=list(diagnostic.verts), dist=1e-6)
    reports[name] = {'normalization': norm, 'vertices': len(ob.data.vertices),
        'triangles': sum(len(f.vertices)-2 for f in ob.data.polygons),
        'bounds_m': {'min': list(lo), 'max': list(hi)},
        'diagnostic_components': [{k:v for k,v in g.items() if k != 'polygon_indices'} for g in components(ob.data)],
        'diagnostic_weld_vertices': len(diagnostic.verts),
        'boundary_edges_after_diagnostic_weld': sum(e.is_boundary for e in diagnostic.edges),
        'nonmanifold_edges_after_diagnostic_weld': sum(not e.is_manifold for e in diagnostic.edges),
        'materials': [m.name for m in ob.data.materials if m], 'uv_layers': len(ob.data.uv_layers)}
    diagnostic.free()
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=str(OUT / (name+'_core.glb')), export_format='GLB', use_selection=True, export_animations=False)
new.hide_render = old.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'source_comparison.blend'))
report = {'operation_id': OP, 'source': raw.relative_to(ROOT).as_posix(), 'source_sha256': raw_sha,
    'old_master_sha256': OLD_SHA, 'tool': bpy.app.version_string, 'cores': reports,
    'fixed_studio': 'ro_review_common.py; same 1.74m normalized height, five cameras, 1280px, AgX, lighting',
    'whole_character_triangle_limit': 60000, 'reused_equipment_triangles': 43852,
    'replacement_core_limit': 16148, 'replacement_triangle_gate': reports['new']['triangles'] <= 16148,
    'visual_comparison_pending': True, 'rig_accepted': False, 'animation_accepted': False, 'delivered': False,
    'artifacts': [{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.iterdir())]}
(QA / 'inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert sha(OLD) == OLD_SHA and sha(raw) == raw_sha
print('RO_CORE_SOURCE ' + json.dumps({'new_triangles':reports['new']['triangles'], 'old_triangles':reports['old']['triangles'], 'triangle_gate':report['replacement_triangle_gate'], 'report':str(QA / 'inspection.json')}))
