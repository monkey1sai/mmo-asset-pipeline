"""v003: finite independent controls, littlefinger isolation and actual sword."""
from datetime import datetime,timezone
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_actual_grip_common import *
start=read(QA/'v003-start.json');folder=QA/'v003-digit-control';out=ROOT/'assets/processed/ro-swordsman-combo-r008/v003-digit-control'
assert not folder.exists() and not out.exists();folder.mkdir();out.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);ww=weights(ob);saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(material('r008ControlGray',(.55,.55,.55)))
isolated=[]
for index,angles in enumerate(start['littlefinger_isolated_cases']):
    params=[{'bone':f'finger1_{i:02}','angle':a,'mode':'flexion'} for i,a in enumerate(angles,1)]
    event,_=actual(ob,rig,rest,f'little-isolated{index}',params,ww);isolated.append(event)
    if event['transverse_pairs']:render(folder,f'little-isolated{index}',['palm','side'])
data=read(ROOT/start['weapon']['path']);weapon=add_weapon(rig,data,start['weapon_shifts'][0]['translation'])
pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']
events=[];best=None
for shift in start['weapon_shifts']:
    place_weapon(weapon,rig,data,shift['translation'])
    for row in start['templates']:
        label=row['id']+'-'+shift['id'];controls(rig,row,start['splay_radians'])
        event,pts=capture(ob,rig,rest,label,row,ww)
        contact=contacts(ob,weapon,rig,pads,label,{'controls':row,'splays':start['splay_radians'],'weapon_shift':shift})
        value=score(contact,event);events.append({'label':label,'controls':row,'shift':shift,'self':event,'contact':contact,'score':value})
        render(folder,label,['palm','side'])
        if best is None or value<best['score']:best=events[-1]
controls(rig,best['controls'],start['splay_radians']);place_weapon(weapon,rig,data,best['shift']['translation'])
render(folder,'selected',['palm','side','back'])
assert geometry(ob)==rest and weights(ob)==ww
ob.data.materials.clear()
for m in saved:ob.data.materials.append(m)
dest=out/'right_hand_actual_sword_control.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),
 'littlefinger_isolated':isolated,'events':events,'selected':best['label'],'selected_controls':best['controls'],'selected_shift':best['shift'],
 'functional_surface_gate':best['contact']['surface_gate_pass'] and not best['self']['transverse_pairs'],
 'material_gate':False,'whole_character_accepted':False,'weights_geometry_UV_preserved':True,'new_credits':0,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R008_DIGIT '+json.dumps({'little':[r['transverse_pairs'] for r in isolated],
 'cases':[(r['label'],r['self']['transverse_pairs'],r['contact']['transverse_crossings_count'],r['contact']['maximum_penetration_m'],[v['within_2mm'] for v in r['contact']['pad_contacts'].values()]) for r in events],
 'selected':best['label'],'gate':best['contact']['surface_gate_pass'] and not best['self']['transverse_pairs']}))
