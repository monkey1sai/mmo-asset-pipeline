"""Fresh r010 baseline and full fixed-pad normal audit, no shape edits."""
from datetime import datetime, timezone
from pathlib import Path
import json, sys, shutil
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated, contacts
from ro_review_common import render_views

QA = ROOT / 'runs/qa/ro-swordsman-combo-r010'
OLD = ROOT / 'runs/qa/ro-swordsman-combo-r009'
read, save, artifact = common.read, common.save, common.artifact
clock = read(QA / 'phase-start.json')
folder = QA / 'baseline'
folder.mkdir()
out = ROOT / 'assets/processed/ro-swordsman-combo-r010/baseline'
out.mkdir(parents=True)
source = ROOT / clock['local_source']['path']
assert artifact(source) == clock['local_source']
dest = out / 'right_hand_grasp_design_baseline.blend'
shutil.copyfile(source, dest)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects['SM_RO_RightHand_Exterior']
rig = bpy.data.objects['ARM_RO_HandDiagnostic']
weapon = bpy.data.objects['SM_RO_LocalActualSword']
rest, ww = common.geometry(ob), common.weights(ob)
masks = read(ROOT / 'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')
params = read(OLD / 'v004-collision-constraints/result.json')
self_report, points = grip.capture(ob, rig, rest, 'r010-saved-baseline', params['controls'], ww)
contact = contacts(ob, weapon, rig, masks['pads'], 'r010-saved-baseline', {'exact_saved_pose': True})
sp, st, _ = evaluated(weapon)
root = rig.pose.bones['sword'].head
axis = (rig.pose.bones['sword'].tail-root).normalized()
handle_triangles = [t for t in st if -.112 <= (sum((sp[i] for i in t), Vector())/3-root).dot(axis) <= .085]
handle = BVHTree.FromPolygons(sp, handle_triangles, all_triangles=True)
ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
me = ev.to_mesh()
normal = [v.normal.copy() for v in me.vertices]
ev.to_mesh_clear()
rows = {}
for branch, ids in masks['pads'].items():
    samples = []
    for i in ids:
        hit, hn, face, gap = handle.find_nearest(points[i])
        toward = hit-points[i]
        samples.append({'id': i, 'semantic': masks['semantic'].get(str(i)), 'point': list(points[i]),
            'normal': list(normal[i]), 'gap_m': gap, 'nearest_handle': list(hit),
            'normal_dot_toward_handle': normal[i].dot(toward.normalized()) if toward.length else None,
            'rest_palm_side_y': rest['points'][i][1]})
    rows[branch] = {'all_fixed_pad_samples': samples,
        'outward_toward_handle_count': sum(r['normal_dot_toward_handle'] is not None and r['normal_dot_toward_handle'] > .25 for r in samples),
        'opposed_normal_count': sum(r['normal_dot_toward_handle'] is not None and r['normal_dot_toward_handle'] < -.25 for r in samples),
        'third_nearest_gap_m': sorted(r['gap_m'] for r in samples)[2]}
save(folder / 'pad-normal-audit.json', {'source': clock['local_source'], 'original_masks': artifact(ROOT / 'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json'),
    'pads_unchanged': True, 'normal_reference': 'actual evaluated vertex normals; boundary averaging limits anatomical inference', 'digits': rows})
save(folder / 'mesh-and-weights.json', {'geometry': rest, 'weights': ww,
    'bones': {b.name: {'head': list(b.head_local), 'tail': list(b.tail_local), 'parent': b.parent.name if b.parent else None} for b in rig.data.bones},
    'modifiers': [{'name': m.name, 'type': m.type, 'preserve_volume': m.use_deform_preserve_volume if m.type == 'ARMATURE' else None} for m in ob.modifiers]})
save(folder / 'posed-points.json', {'points': [list(p) for p in points]})
ob.data.materials.clear()
ob.data.materials.append(common.material('r010BaselineGray', (.55, .55, .55)))
common.render(folder, 'saved-grip')
save(folder / 'local-baseline.json', {'observed_utc': datetime.now(timezone.utc).isoformat(), 'artifact': artifact(dest),
    'self': self_report, 'contact': contact, 'params_source': artifact(OLD / 'v004-collision-constraints/result.json'),
    'audit': artifact(folder / 'pad-normal-audit.json'), 'source_unchanged': artifact(source) == clock['local_source'],
    'new_credits': 0, 'numeric_function_gate': False, 'views': [artifact(p) for p in sorted(folder.glob('*.png'))]})
full = ROOT / clock['whole_source']['path']
bpy.ops.wm.open_mainfile(filepath=str(full), load_ui=False, use_scripts=False)
for suffix in ['.blend', '.glb']:
    shutil.copyfile(full.with_suffix(suffix), out / ('ro_whole_baseline'+suffix))
render_views(folder, frame=1)
save(folder / 'whole-baseline.json', {'source': clock['whole_source'], 'fresh_views': True,
    'artifacts': [artifact(p) for p in sorted(out.glob('ro_whole_baseline.*'))], 'verdict': 'NO_SHIP', 'complete300_ornewgrip': False})
print(json.dumps({'baseline': 'NO_SHIP', 'contacts': {n: r['within_2mm'] for n, r in contact['pad_contacts'].items()},
    'pad_normals': {n: {'toward': r['outward_toward_handle_count'], 'opposed': r['opposed_normal_count'], 'third_mm': r['third_nearest_gap_m']*1000} for n,r in rows.items()}}))
