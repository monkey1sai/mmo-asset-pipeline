"""v001 intermediate: bounded affine equipment fitting, no body deletion."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import render_views

SOURCE = ROOT / 'assets/processed/ro-swordsman-combo-r005/baseline/ro_batch_assembly_baseline.blend'
SOURCE_SHA = 'b5bc06eadb42d5a33b573448a90442cc24382a7875fa923aefa716c22987b57f'
OUT = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-fit-affine'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-fit-affine'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def affine(ob, center, scale, translation):
    center, translation = Vector(center), Vector(translation)
    for vertex in ob.data.vertices:
        delta = vertex.co - center
        vertex.co = center + Vector([delta[i] * scale[i] for i in range(3)]) + translation
    ob.data.update()
    return {'scale': scale, 'center': list(center), 'translation_m': list(translation),
            'determinant': math.prod(scale), 'thickness_distance_scale_bounds': [min(scale), max(scale)],
            'topology_uv_preserved': True, 'surface_clearance_accepted': False}


if OUT.exists() or QA.exists() or sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError('Preserve source and existing diagnostic')
start = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-start.json').read_text())
phase = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
now = datetime.now(timezone.utc)
trial_elapsed = (now - datetime.fromisoformat(start['started_utc'])).total_seconds()
phase_elapsed = (now - datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()
if trial_elapsed >= phase['budget']['trial_seconds'] or phase_elapsed >= phase['budget']['total_seconds']:
    raise RuntimeError('Preserved experiment clock exhausted')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
core = bpy.data.objects['SM_RO_core']
core_coordinates = [v.co.copy() for v in core.data.vertices]
report = {}
report['cuirass'] = affine(bpy.data.objects['SM_RO_cuirass'], (0, .015, 1.186),
                           (1.10, 1.26, 1.08), (0, .035, .025))
report['coat'] = affine(bpy.data.objects['SM_RO_coat'], (0, .01, .86),
                        (1.18, 1.25, 1), (0, .035, 0))
for side, sign in (('R', -1), ('L', 1)):
    ob = bpy.data.objects['SM_RO_bracer.' + side]
    old_center = Vector((sign * .375, -.04, 1.025))
    old_axis = Matrix.Rotation(math.radians(-7 * -sign), 3, 'Y') @ Vector((0, 0, 1))
    new_center = Vector((sign * .381, .06, 1.04))
    new_axis = Vector((-sign * .107, 0, .20)).normalized()
    rotation = old_axis.rotation_difference(new_axis).to_matrix()
    for v in ob.data.vertices:
        v.co = new_center + rotation @ ((v.co - old_center) * 1.08)
    ob.data.update()
    report['bracer.' + side] = {'translation_m': list(new_center - old_center),
        'rotation': [list(row) for row in rotation], 'uniform_scale': 1.08,
        'topology_uv_preserved': True, 'thickness_scale': 1.08}
meshes = list(bpy.data.collections['COL_Character'].objects)
triangles = sum(len(p.vertices) - 2 for ob in meshes for p in ob.data.polygons)
if triangles != 55488 or any(v.co != core_coordinates[v.index] for v in core.data.vertices):
    raise RuntimeError('Source/body topology preservation failed')
bpy.ops.object.select_all(action='DESELECT')
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = core
bpy.ops.export_scene.gltf(filepath=str(OUT / 'ro_equipment_fit.glb'), export_format='GLB',
                          use_selection=True, export_animations=False, export_yup=True)
render_views(QA)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ro_equipment_fit.blend'))
report.update({'candidate': 'v001', 'stage': 'affine volume-fit diagnostic, not full candidate acceptance',
    'method': 'Positive determinant whole-object affine transforms; preserves connectivity/openings and prevents local wall inversion. Actual clearance requires visual/function tests.',
    'supersedes_failed_method_record': 'runs/qa/ro-swordsman-combo-r005/v001-fit/failure-diagnostic.json',
    'source_sha256': SOURCE_SHA, 'triangles': triangles, 'bones': 0, 'animations': 0,
    'body_faces_removed': 0, 'source_preserved': sha(SOURCE) == SOURCE_SHA,
    'elapsed_trial_seconds': trial_elapsed, 'elapsed_phase_seconds': phase_elapsed,
    'artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p),
                   'bytes': p.stat().st_size} for p in OUT.iterdir()]})
(QA / 'fit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('RO_VOLUME_FIT ' + json.dumps(report))
