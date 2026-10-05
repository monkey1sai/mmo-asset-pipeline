"""Actual saved baseline, bone/weight diagnosis and raw posed points; no repair."""
from datetime import datetime, timezone
from pathlib import Path
import sys, json, shutil
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import contacts
from ro_review_common import render_views

QA = ROOT / 'runs/qa/ro-swordsman-combo-r009'
read, save, artifact = common.read, common.save, common.artifact
clock = read(QA / 'phase-start.json')
folder = QA / 'baseline'; folder.mkdir()
out = ROOT / 'assets/processed/ro-swordsman-combo-r009/baseline'; out.mkdir(parents=True)
source = ROOT / clock['local_source']['path']
assert artifact(source) == clock['local_source']
dest = out / 'right_hand_whole_calibration_baseline.blend'
shutil.copyfile(source, dest)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects['SM_RO_RightHand_Exterior']; rig = bpy.data.objects['ARM_RO_HandDiagnostic']; sword = bpy.data.objects['SM_RO_LocalActualSword']
rest = common.geometry(ob); ww = common.weights(ob)
masks = read(ROOT / 'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')
params = read(ROOT / 'runs/qa/ro-swordsman-combo-r008/v004-contact-solver/result.json')['controls']
self_report, pts = grip.capture(ob, rig, rest, 'r009-saved-baseline', params, ww)
contact = contacts(ob, sword, rig, masks['pads'], 'r009-saved-baseline', {'exact_saved_pose': True})
bones = {b.name: {'head': list(b.head_local), 'tail': list(b.tail_local), 'parent': b.parent.name if b.parent else None}
         for b in rig.data.bones}
save(folder / 'mesh-and-weights.json', {'geometry': rest, 'weights': ww, 'bone_points': bones})
save(folder / 'actual-posed-points.json', {'points': [list(p) for p in pts], 'source_id_verified': True,
                                        'purpose': 'Archive actual ID-aligned coordinates for later fresh-process tolerance comparison.'})
edges = []
for pair in [(277, 278), (372, 388)]:
    a,b=pair; names=set(ww[a])|set(ww[b])
    base=(Vector(rest['points'][a])-Vector(rest['points'][b])).length
    edges.append({'edge': pair, 'rest_m': base, 'posed_m': (pts[a]-pts[b]).length,
                  'weights': [ww[a],ww[b]], 'full_bone_L1': sum(abs(ww[a].get(n,0)-ww[b].get(n,0)) for n in names),
                  'rest_points': [rest['points'][a],rest['points'][b]]})
saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(common.material('r009BaselineGray',(.55,.55,.55)))
common.render(folder,'saved-grip')
marker=common.line_object('r009FrozenBadEdges',[[pts[a],pts[b]] for a,b in [(277,278),(372,388)]],(1,.03,.02),.0006)
common.render(folder,'marked-compression',['palm','side'])
bpy.data.objects.remove(marker,do_unlink=True)
common.reset(rig)
save(folder/'neutral-points.json',{'points':[list(v.co) for v in ob.data.vertices]})
common.render(folder,'neutral',['palm','side'])
joint_rows=[]
for branch in ['finger1','finger2','finger3','finger4']:
    ids=[int(i) for i,row in masks['semantic'].items() if row['branch']==branch]
    for joint in range(1,4):
        b=rig.data.bones[f'{branch}_{joint:02}'];head=b.head_local;axis=(b.tail_local-head).normalized()
        nearby=sorted(ids,key=lambda i:abs((Vector(rest['points'][i])-head).dot(axis)))[:12]
        joint_rows.append({'bone':b.name,'head':list(head),'tail':list(b.tail_local),
                           'nearby_source_ids':nearby,'nearby_points':[rest['points'][i] for i in nearby]})
save(folder/'local-baseline.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),
    'source':clock['local_source'],'artifact':artifact(dest),'raw_posed_points':artifact(folder/'actual-posed-points.json'),
    'geometry_weights':artifact(folder/'mesh-and-weights.json'),'self':self_report,'contact':contact,
    'frozen_problem_edges':edges,'joint_readback':joint_rows,'basis':self_report['actual_basis'],
    'source_unchanged':artifact(source)==clock['local_source'],'numeric_function_gate':False,
    'new_credits':0,'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
full=ROOT/clock['whole_source']['path']
bpy.ops.wm.open_mainfile(filepath=str(full),load_ui=False,use_scripts=False)
for suffix in ['.blend','.glb']:
    shutil.copyfile(full.with_suffix(suffix),out/('ro_whole_baseline'+suffix))
render_views(folder,frame=1)
save(folder/'whole-baseline.json',{'source':clock['whole_source'],'fresh_views':True,
     'artifacts':[artifact(p) for p in sorted(out.glob('ro_whole_baseline.*'))],
     'complete300_ornewgrip':False,'verdict':'NO_SHIP','old_art_scores_unchanged':True})
print('R009_BASELINE '+json.dumps({'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],
     'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'min_edge_ratio':self_report['minimum_edge_ratio']}))
