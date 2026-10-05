"""v001 fit dependency: tailor covered clothing and align measured bracer axes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import render_views
SOURCE = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-fit-affine/ro_equipment_fit.blend'
SOURCE_SHA = '6ae3d5adbcfa861340a1f3bedb8579c7f00b64d787fa72d411af39ef08d76457'
OUT = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-fit-tailored'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-fit-tailored'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if OUT.exists() or QA.exists() or sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError('Preserve earlier versions')
start = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-start.json').read_text())
phase = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
now = datetime.now(timezone.utc)
trial_elapsed = (now - datetime.fromisoformat(start['started_utc'])).total_seconds()
phase_elapsed = (now - datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()
if trial_elapsed >= phase['budget']['trial_seconds'] or phase_elapsed >= phase['budget']['total_seconds']:
    raise RuntimeError('Experiment clock exhausted')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
core = bpy.data.objects['SM_RO_core']
report = {}
for side, sign in [('R', -1), ('L', 1)]:
    ob = bpy.data.objects['SM_RO_bracer.' + side]
    array = np.array([list(v.co) for v in ob.data.vertices])
    center = array.mean(axis=0)
    values, axes = np.linalg.eigh(np.cov((array - center).T))
    native_axis = Vector(axes[:, np.argmax(values)])
    if native_axis.z < 0:
        native_axis = -native_axis
    desired_axis = Vector((-sign * .107, 0, .20)).normalized()
    rotation = native_axis.rotation_difference(desired_axis).to_matrix()
    measured = [v.co for v in core.data.vertices if abs(v.co.z - 1.04) < .009 and .33 < sign * v.co.x < .45]
    if not measured:
        raise RuntimeError('Missing actual forearm section')
    destination = Vector([(min(p[i] for p in measured) + max(p[i] for p in measured)) / 2 for i in range(3)])
    for v in ob.data.vertices:
        v.co = destination + rotation @ (v.co - Vector(center))
    ob.data.update()
    report['bracer.' + side] = {'measured_center_m': list(destination),
        'native_principal_axis': list(native_axis), 'aligned_axis': list(desired_axis),
        'thickness_distance_preserved': True}

# Fit only clothing covered by actual armor/skirt ray intersections. Keep all faces,
# digits, head, neck and arm volumes. This is tailoring, not hidden-body deletion.
before = [v.co.copy() for v in core.data.vertices]
for name, low, high, max_x in [('cuirass', .975, 1.415, .225), ('coat', .805, .975, .285)]:
    shell = bpy.data.objects['SM_RO_' + name]
    shell_tree = BVHTree.FromPolygons([v.co for v in shell.data.vertices], [list(p.vertices) for p in shell.data.polygons])
    changed, maximum, unresolved = [], 0, 0
    for vertex in core.data.vertices:
        x, y, z = vertex.co
        if not low < z < high or abs(x) > max_x:
            continue
        origin = Vector((0, .05, z))
        radial = vertex.co - origin
        if radial.length < .01:
            continue
        direction = radial.normalized()
        hit, normal, face, distance = shell_tree.ray_cast(origin, direction, .42)
        if hit is None:
            unresolved += 1
            continue
        target_radius = max(.04, distance - .009)
        if radial.length <= target_radius:
            continue
        delta = radial.length - target_radius
        if delta > .065:
            unresolved += 1
            continue
        vertex.co = origin + direction * target_radius
        changed.append(vertex.index)
        maximum = max(maximum, delta)
    report['covered_cloth_' + name] = {'vertex_ids': changed, 'vertex_count': len(changed),
        'max_displacement_m': maximum, 'unresolved_or_uncovered_vertices': unresolved,
        'scope_m': [low, high, max_x], 'body_faces_deleted': 0, 'clearance_request_m': .009}
core.data.update()
meshes = list(bpy.data.collections['COL_Character'].objects)
triangles = sum(len(p.vertices) - 2 for ob in meshes for p in ob.data.polygons)
if triangles != 55488:
    raise RuntimeError('Unexpected topology change')
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = core
bpy.ops.export_scene.gltf(filepath=str(OUT / 'ro_tailored_fit.glb'), export_format='GLB', use_selection=True,
                          export_animations=False, export_yup=True)
render_views(QA)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ro_tailored_fit.blend'))
report.update({'candidate': 'v001', 'stage': 'fit dependency; no rig/animation acceptance',
    'source_sha256': SOURCE_SHA, 'source_preserved': sha(SOURCE) == SOURCE_SHA,
    'triangles': triangles, 'bones': 0, 'animations': 0,
    'elapsed_trial_seconds': trial_elapsed, 'elapsed_phase_seconds': phase_elapsed,
    'artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in OUT.iterdir()]})
(QA / 'tailoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('RO_TAILORING ' + json.dumps({k: v for k, v in report.items() if not k.startswith('covered_')}))
