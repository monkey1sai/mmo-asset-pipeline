"""Record the new A-pose source baseline, metric normalization only; no repairs."""
import argparse
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

p = argparse.ArgumentParser()
p.add_argument('--input', required=True)
p.add_argument('--sha256', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
source = (ROOT / a.input).resolve(strict=True)
if not source.is_relative_to(ROOT / 'assets/raw/ro-swordsman-combo/rodin-v002') or source.suffix.lower() != '.glb':
    raise ValueError('New authorized raw GLB only')
expected = hashlib.sha256(source.read_bytes()).hexdigest()
if expected != a.sha256:
    raise ValueError('Input hash mismatch')
out = ROOT / 'assets/processed/ro-swordsman-combo-r003/baseline'
qa = ROOT / 'runs/qa/ro-swordsman-combo-r003/baseline'
if out.exists() or qa.exists():
    raise ValueError('Baseline already exists; never overwrite or reset')
out.mkdir(parents=True)
qa.mkdir(parents=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not meshes:
    raise ValueError('No model meshes')
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
low = Vector(tuple(min(v[i] for v in points) for i in range(3)))
high = Vector(tuple(max(v[i] for v in points) for i in range(3)))
factor = 1.74 / (high.z - low.z)
center = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
stats = []
for index, ob in enumerate(meshes):
    world = ob.matrix_world.copy()
    for v in ob.data.vertices:
        v.co = (world @ v.co - center) * factor
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.name = 'SM_RO_APoseSource_' + str(index)
    ob.data.update()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    remaining = set(bm.verts)
    components = []
    while remaining:
        stack = [remaining.pop()]
        group = []
        while stack:
            vertex = stack.pop()
            group.append(vertex)
            for edge in vertex.link_edges:
                neighbor = edge.other_vert(vertex)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append({'vertices': len(group), 'min': [min(v.co[i] for v in group) for i in range(3)], 'max': [max(v.co[i] for v in group) for i in range(3)]})
    stats.append({'mesh': ob.name, 'vertices_uv_split': len(ob.data.vertices), 'triangles': sum(len(f.vertices)-2 for f in ob.data.polygons),
                  'source_polygons_by_size': {str(n): sum(len(f.vertices)==n for f in ob.data.polygons) for n in {len(f.vertices) for f in ob.data.polygons}},
                  'exact_seam_weld_vertices': len(bm.verts), 'nonmanifold_after_seam_weld': sum(not e.is_manifold for e in bm.edges),
                  'components_after_seam_weld': sorted(components, key=lambda x: -x['vertices']),
                  'uv_layers': len(ob.data.uv_layers), 'materials': [m.name for m in ob.data.materials if m]})
    bm.free()
bpy.ops.object.select_all(action='DESELECT')
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.gltf(filepath=str(out/'ro_source_baseline.glb'), export_format='GLB', use_selection=True, export_animations=False, export_yup=True)
stage()
render_views(qa)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'ro_source_baseline.blend'))
report = {'source': source.relative_to(ROOT).as_posix(), 'source_sha256': expected, 'tool': bpy.app.version_string,
          'normalization': {'height_m': 1.74, 'ground_z': 0, 'units': 'm', 'factor': factor, 'original_bounds': {'min': list(low), 'max': list(high)}},
          'mesh_stats': stats, 'bones': sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE'),
          'animations': len(bpy.data.actions), 'skill_effects': 0,
          'images': [{'name': i.name, 'size': list(i.size), 'packed': bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE'],
          'artifacts': {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in out.iterdir() if x.suffix in {'.blend','.glb'}},
          'acceptance': 'Not run: source baseline requires actual five-view review and no rig or animation is assumed.'}
(qa/'inspection.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
    raise RuntimeError('Raw source drift')
print('APOSE_BASELINE ' + json.dumps(report))
