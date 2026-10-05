"""v001 intermediate: fit equipment volumes without removing body/source faces."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import render_views

SOURCE = ROOT / 'assets/processed/ro-swordsman-combo-r005/baseline/ro_batch_assembly_baseline.blend'
SOURCE_SHA = 'b5bc06eadb42d5a33b573448a90442cc24382a7875fa923aefa716c22987b57f'
OUT = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-fit'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-fit'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def body_tree(core, lower=False):
    points = [v.co.copy() for v in core.data.vertices]
    faces = [list(p.vertices) for p in core.data.polygons
             if not lower or all(abs(points[i].x) < .32 and points[i].z < 1.01 for i in p.vertices)]
    return BVHTree.FromPolygons(points, faces, all_triangles=False)


def body_radius(tree, origin, direction, farthest, limit):
    cursor = origin.copy()
    hits = []
    for _ in range(12):
        hit, normal, face, distance = tree.ray_cast(cursor, direction, limit)
        if hit is None:
            break
        radius = (hit - origin).dot(direction)
        if radius > limit:
            break
        hits.append(radius)
        if not farthest:
            break
        cursor = hit + direction * .00002
    return max(hits) if hits else None


def fit_radial(ob, tree, origin, axis=(0, 0, 1), clearance=.015, farthest=False, limit=.35):
    """Scale both sides of each local shell cell together; preserve shell thickness."""
    origin, axis = Vector(origin), Vector(axis).normalized()
    basis_u = Vector((0, 1, 0)).cross(axis).normalized()
    basis_v = axis.cross(basis_u).normalized()
    samples, cells = [], {}
    for v in ob.data.vertices:
        delta = v.co - origin
        height = delta.dot(axis)
        radial = delta - axis * height
        radius = radial.length
        angle = math.atan2(radial.dot(basis_v), radial.dot(basis_u))
        cell = (int(math.floor(height / .025)), int(math.floor((angle + math.pi) / (2 * math.pi) * 72)) % 72)
        direction = radial.normalized()
        required = body_radius(tree, origin + axis * height, direction, farthest, limit)
        sample = (v.index, height, radial, radius, cell, required)
        samples.append(sample)
        cells.setdefault(cell, []).append(sample)
    factors = {}
    for cell, group in cells.items():
        minimum = min(s[3] for s in group)
        required = max((s[5] for s in group if s[5] is not None), default=0)
        factors[cell] = max(1, (required + clearance) / max(minimum, .01)) if required else 1
    # Neighbor maxima give a conservative smooth cage instead of independently collapsing walls.
    smoothed = {}
    for cell in factors:
        z, a = cell
        smoothed[cell] = max(factors.get((z + dz, (a + da) % 72), 1)
                             for dz in (-1, 0, 1) for da in (-1, 0, 1))
    if max(smoothed.values(), default=1) > 2.5:
        raise RuntimeError(f'{ob.name}: local fit displacement exceeds diagnostic limit')
    maximum_displacement = 0
    for index, height, radial, radius, cell, required in samples:
        displacement = radial * (smoothed[cell] - 1)
        ob.data.vertices[index].co += displacement
        maximum_displacement = max(maximum_displacement, displacement.length)
    ob.data.update()
    return {'max_radial_scale': max(smoothed.values(), default=1),
            'max_displacement_m': maximum_displacement, 'clearance_m': clearance,
            'body_hit_vertices': sum(s[5] is not None for s in samples),
            'vertices': len(samples), 'faces_removed': 0, 'uv_topology_unchanged': True}


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
tree = body_tree(core)
lower_tree = body_tree(core, lower=True)
report = {}
for name in ('cuirass', 'coat'):
    ob = bpy.data.objects['SM_RO_' + name]
    # Match the body axis, measured from torso cross sections rather than full-board bounds.
    for v in ob.data.vertices:
        v.co.y += .035
    report[name] = fit_radial(ob, lower_tree if name == 'coat' else tree,
                             (0, .05, 0), farthest=name == 'coat', clearance=.019,
                             limit=.32 if name == 'coat' else .30)
for side, sign in (('R', -1), ('L', 1)):
    ob = bpy.data.objects['SM_RO_bracer.' + side]
    old_center = Vector((sign * .375, -.04, 1.025))
    old_axis = Matrix.Rotation(math.radians(-7 * -sign), 3, 'Y') @ Vector((0, 0, 1))
    new_center = Vector((sign * .381, .05, 1.04))
    new_axis = Vector((-sign * .107, 0, .20)).normalized()
    rotation = old_axis.rotation_difference(new_axis).to_matrix()
    for v in ob.data.vertices:
        v.co = new_center + rotation @ (v.co - old_center)
    report['bracer.' + side] = fit_radial(ob, tree, new_center, new_axis,
                                        clearance=.012, limit=.14)
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
report.update({'candidate': 'v001', 'stage': 'volume-fit diagnostic, not full candidate acceptance',
               'source_sha256': SOURCE_SHA, 'triangles': triangles, 'bones': 0, 'animations': 0,
               'body_faces_removed': 0, 'source_preserved': sha(SOURCE) == SOURCE_SHA,
               'elapsed_trial_seconds': trial_elapsed, 'elapsed_phase_seconds': phase_elapsed,
               'artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p),
                              'bytes': p.stat().st_size} for p in OUT.iterdir()]})
(QA / 'fit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('RO_VOLUME_FIT ' + json.dumps(report))
