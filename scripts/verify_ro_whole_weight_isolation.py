"""Additional isolation views and actual non-target displacement; no new candidate."""
from pathlib import Path
from datetime import datetime,timezone
import sys,bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
result=read(QA/'v001-vectors/result.json');folder=QA/'v001-isolation-verification';folder.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/result['artifact']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];common.reset(rig)
rest=common.geometry(ob);ww=common.weights(ob);bpy.data.objects['SM_RO_LocalActualSword'].hide_render=True
ob.data.materials.clear();ob.data.materials.append(common.material('r009IsolationGray',(.55,.55,.55)))
masks=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['semantic']
events=[]
for n in ['finger1','finger2','finger3','finger4']:
    for j in [1,2]:
        label=f'{n}-{j:02}-.30';params=[{'bone':f'{n}_{j:02}','angle':.30,'mode':'flexion'}]
        event,pts=common.actual(ob,rig,rest,label,params,ww)
        protected_other=[int(i) for i,row in masks.items() if row['branch'] not in [n,'thumb']]
        unwanted=max((pts[i]-Vector(rest['points'][i])).length for i in protected_other)
        event['other_finger_body_max_displacement_m']=unwanted
        events.append(event)
        common.render(folder,label,['palm','side'])
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':result['artifact'],'events':events,
     'source_unchanged':artifact(ROOT/result['artifact']['path'])==result['artifact'],'no_newcandidate':True,
     'limitation':'Sharedpalm/web motion intentionally permitted; measure protectedneighborfinger bodies separately.',
     'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R009_ISOLATION '+str(max(r['other_finger_body_max_displacement_m'] for r in events)))
