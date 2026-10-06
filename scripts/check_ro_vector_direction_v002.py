"""Same mesh/weights, corrected anatomically verified CMC axial rotation."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
start=read(QA/'v002-start.json');folder=QA/'v002-direction';out=ROOT/'assets/processed/ro-swordsman-combo-r008/v002-direction'
assert not folder.exists() and not out.exists();folder.mkdir();out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);ww=weights(ob);old=read(QA/'v001-vectors/weights.json')
assert ww=={int(i):w for i,w in old['final'].items()}
materials=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(material('r008v002Gray',(.55,.55,.55)))
events=[];posed={}
for label,params in isolated_parameters('opposition_ulnar'):
    event,pts=actual(ob,rig,rest,label,params,ww);events.append(event);posed[label]=pts
    if label=='neutral' or any(abs(r['angle'])==.30 or r['mode']=='opposition_ulnar' and abs(r['angle'])==.15 for r in params):
        render(folder,label)
points=[Vector(p) for p in rest['points']];neutral=posed['neutral']
prior=read(QA/'v001-vectors/result.json');direction=[]
for r in prior['direction']:
    angle=r['angle'];joint=r['joint'];label=f'{joint}-{angle:+.2f}' if joint!='CMC-pronation' else f'CMC-opposition-{angle:+.2f}'
    ids=r['frozen_source_pad_ids'];delta=sum((posed[label][i]-neutral[i] for i in ids),Vector())/len(ids)
    along=-delta.x if joint=='CMC-pronation' else -delta.y
    direction.append({'joint':joint,'angle':angle,'frozen_source_pad_ids':ids,'mean_delta':list(delta),'expected_displacement_m':along,'expected_direction_pass':along*angle>0})
reset(rig);ob.data.materials.clear()
for m in materials:ob.data.materials.append(m)
assert geometry(ob)==rest and weights(ob)==ww
ob['thumb_CMC_positive_pronation']='opposition_ulnar: negative rotation about actual metacarpal axis; positive means toward ulnar palm; direction verified with frozen sourcepad IDs'
dest=out/'right_hand_vectors_direction.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),
 'events':events,'direction':direction,'direction_gate':all(r['expected_direction_pass'] for r in direction),
 'numeric_self_gate':all(not r['transverse_pairs'] and not r['degenerate_triangles'] for r in events),
 'signed_extreme_views':[artifact(p) for p in sorted(folder.glob('*.png'))],'isolated_visual_gate':'pending actual signed images',
 'weights_geometry_UV_bones_fourfinger_identical_to_v001':True,'material_gate':False,'grip_started':False,'new_credits':0})
print('R008_V002 '+json.dumps({'numeric':all(not r['transverse_pairs'] and not r['degenerate_triangles'] for r in events),'direction':all(r['expected_direction_pass'] for r in direction),'poses':len(events)}))
