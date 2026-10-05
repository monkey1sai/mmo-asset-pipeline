"""Fresh-process actual point tolerance and protected-source verification."""
from pathlib import Path
from datetime import datetime,timezone
import sys,math,bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated,contacts
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
clock=read(QA/'phase-start.json');baseline=read(QA/'baseline/mesh-and-weights.json');contract=read(QA/'local-contract.json')
result=read(QA/'v004-collision-constraints/result.json');expected=read(ROOT/result['raw_points']['path'])['points']
assert artifact(ROOT/result['artifact']['path'])==result['artifact']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];sword=bpy.data.objects['SM_RO_LocalActualSword']
assert common.geometry(ob)==baseline['geometry']
weights=common.weights(ob);expected_weights={int(i):r for i,r in read(QA/'v001-vectors/weights.json')['final'].items()};assert weights==expected_weights
for n,row in baseline['bone_points'].items():
    if n=='sword':continue
    b=rig.data.bones[n];assert list(b.head_local)==row['head'] and list(b.tail_local)==row['tail'] and (b.parent.name if b.parent else None)==row['parent']
assert all(weights[i]==baseline['weights'][str(i)] for i in contract['thumb_protected_ids'])
assert all(abs(rig.matrix_world[i][j]-(1 if i==j else 0))<1e-8 for i in range(4) for j in range(4))
actual,tris,edges=evaluated(ob);deltas=[(p-Vector(q)).length for p,q in zip(actual,expected)];assert len(actual)==len(expected)==904
maximum=max(deltas);rms=math.sqrt(sum(d*d for d in deltas)/len(deltas));assert maximum<1e-6
weapon_data=read(ROOT/read(QA/'v004-start.json')['weapon']['path']);shift=Vector(result['weapon_shift'])
assert [list(p.vertices) for p in sword.data.polygons]==weapon_data['triangles']
weapon_error=max((v.co-Vector(p)-shift).length for v,p in zip(sword.data.vertices,weapon_data['vertices']));assert weapon_error<1e-7
self_report,_=grip.capture(ob,rig,baseline['geometry'],'fresh-v004',result['controls'],weights)
pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']
contact=contacts(ob,sword,rig,pads,'fresh-v004',{'saved_readback':True,'no_newsearch':True})
counts={n:r['within_2mm'] for n,r in contact['pad_contacts'].items()};assert counts=={'finger1':3,'finger2':1,'finger3':3,'finger4':0,'thumb':3}
assert self_report['transverse_pairs']==contact['transverse_crossings_count']==0
for item in clock['protected_history']:assert artifact(ROOT/item['path'])==item
save(QA/'fresh-saved-verification.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':result['artifact'],
 'geometry_faces_UV_sourceattributes_exact':True,'weights_matchv001_exact':True,'thumb203_exact':True,'original16boneheads_tails_parent_exact':True,
 'rig_identity':True,'raw_actual_saved_point_count':904,'max_saved_fresh_point_delta_m':maximum,'rms_saved_fresh_point_delta_m':rms,
 'position_tolerance_m':1e-6,'posed_points_within_tolerance':True,'weapon_originaltriangles_unscaled':True,'max_weapon_shift_float_error_m':weapon_error,
 'self':self_report,'contact':contact,'original183historyfiles_unchanged':True,'model_file_unchanged':artifact(ROOT/result['artifact']['path'])==result['artifact'],
 'function_gate':False,'full_character_oranimation_ready':False,'new_credits':0})
print('R009_FRESH '+str({'max_point_delta_m':maximum,'rms_m':rms,'contacts':counts,'still_FAIL':True}))
