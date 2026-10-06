"""Read-only diagnostics for failed radial fit, without creating another candidate."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-fit'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/processed/ro-swordsman-combo-r005/baseline/ro_batch_assembly_baseline.blend'), load_ui=False, use_scripts=False)
core, gear = bpy.data.objects['SM_RO_core'], bpy.data.objects['SM_RO_cuirass']
points = [v.co for v in core.data.vertices]
tree = BVHTree.FromPolygons(points, [list(p.vertices) for p in core.data.polygons])
cells = {}
for v in gear.data.vertices:
    point = v.co + Vector((0, .035, 0))
    origin = Vector((0, .05, point.z))
    radial = point - origin
    angle = math.atan2(radial.y, radial.x)
    cell = (int(math.floor(point.z / .025)), int(math.floor((angle + math.pi) / (2 * math.pi) * 72)) % 72)
    hit, normal, face, distance = tree.ray_cast(origin, radial.normalized(), .30)
    cells.setdefault(cell, []).append({'vertex': v.index, 'position': list(point), 'radius': radial.length,
                                      'body_radius': distance if hit is not None else None,
                                      'body_hit_position': list(hit) if hit is not None else None})
diagnostics = []
for cell, samples in cells.items():
    minimum = min(s['radius'] for s in samples)
    hits = [s for s in samples if s['body_radius'] is not None]
    maximum = max(hits, key=lambda s: s['body_radius']) if hits else None
    factor = (maximum['body_radius'] + .019) / minimum if maximum else 1
    diagnostics.append({'cell': cell, 'minimum_shell_radius': minimum, 'factor': factor,
                        'maximum_body_sample': maximum, 'minimum_shell_sample': min(samples, key=lambda s:s['radius'])})
report = {'classification': 'TEST_FAILURE', 'failed_attempts': [
    'KeyError budget.single_trial_seconds, corrected to existing trial_seconds',
    'Conservative radial displacement guard stopped cuirass fit before output'],
    'top_cells': sorted(diagnostics, key=lambda s:-s['factor'])[:12],
    'source_modified': False, 'candidate_clock_reset': False}
path = QA / 'failure-diagnostic.json'
if path.exists():
    raise RuntimeError('Preserve existing diagnostic')
path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
