"""Fresh Blender restart of saved v004; no reset pose, no model edits."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_actual_grip_common import *
result=read(QA/'v004-contact-solver/result.json');source=ROOT/result['artifact']['path']
assert artifact(source)==result['artifact']
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];weapon=bpy.data.objects['SM_RO_LocalActualSword'];bpy.context.view_layer.update()
rest=geometry(ob);ww=weights(ob);frozen=read(QA/'source-probe/mesh-and-weights.json')
assert rest==frozen['geometry']
expected={int(i):w for i,w in read(QA/'v001-vectors/weights.json')['final'].items()}
assert ww==expected
for n,row in frozen['bone_points'].items():
    assert list(rig.data.bones[n].head_local)==row['head'] and list(rig.data.bones[n].tail_local)==row['tail']
# All sixteen original heads/tails, not justthumb, are checked fromthe actualv002 source datablock.
with bpy.data.libraries.load(str(ROOT/result['source']['path']),link=False) as (src,dst):dst.objects=['ARM_RO_HandDiagnostic']
guide=dst.objects[0]
for b in guide.data.bones:
    now=rig.data.bones[b.name]
    assert list(now.head_local)==list(b.head_local) and list(now.tail_local)==list(b.tail_local)
bpy.data.objects.remove(guide,do_unlink=True)
data=read(ROOT/read(QA/'v004-start.json')['weapon']['path']);delta=Vector(result['weapon_shift'])
assert len(weapon.data.vertices)==len(data['vertices']) and [list(p.vertices) for p in weapon.data.polygons]==data['triangles']
max_weapon_error=max((v.co-Vector(p)-delta).length for v,p in zip(weapon.data.vertices,data['vertices']))
assert max_weapon_error<1e-7
self_report,_=capture(ob,rig,rest,'fresh-saved-readback',result['controls'],ww)
pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']
contact=contacts(ob,weapon,rig,pads,'fresh-saved-readback',{'saved_artifact':result['artifact'],'no_search_or_repose':True})
assert self_report['transverse_pairs']==result['final_self']['transverse_pairs']
assert contact['transverse_crossings_count']==result['final_contact']['transverse_crossings_count']
assert {n:r['within_2mm'] for n,r in contact['pad_contacts'].items()}==result['best']['each_digit_contacts']
assert not contact['surface_gate_pass']
save(QA/'fresh-saved-verification.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'artifact':result['artifact'],
 'fresh_blender_process':True,'geometry_faces_UV_source_attributes_exact':True,'weights_exact':True,
 'sixteen_original_bone_heads_tails_exact':True,'weapon_originaltriangles_unscaled':True,'max_weapon_transform_error_m':max_weapon_error,
 'self':self_report,'contact':contact,'source_file_unchanged':artifact(source)==result['artifact'],
 'static_function_gate':False,'animation_or_delivery_verified':False,
 'point_fingerprint_equal':self_report['positions_sha256']==result['final_self']['positions_sha256']})
print('R008_FRESH '+json.dumps({'self':self_report['transverse_pairs'],'sword':contact['transverse_crossings_count'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},'still_FAIL':True}))
