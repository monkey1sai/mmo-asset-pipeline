"""One deterministic bounded coordinate solve; all probes are actual skin/sword."""
from datetime import datetime,timezone
import time
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ro_actual_grip_common import *
from ro_hand_gate import evaluated
start=read(QA/'v004-start.json');clock=read(QA/'phase-start.json');folder=QA/'v004-contact-solver';out=ROOT/'assets/processed/ro-swordsman-combo-r008/v004-contact-solver'
assert not folder.exists() and not out.exists();folder.mkdir();out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);ww=weights(ob);weapon_data=read(ROOT/start['weapon']['path']);weapon=add_weapon(rig,weapon_data,start['initial_shift'])
pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']
parameters={branch+':'+str(i):value for branch in ['finger1','finger2','finger3','finger4','thumb'] for i,value in enumerate(start['initial_controls'][branch])}
parameters.update({'splay:'+n:a for n,a in start['initial_splays'].items()});parameters['pronation']=start['initial_controls']['pronation']
parameters.update({'shift:'+str(i):v for i,v in enumerate(start['initial_shift'])})
for n,(lo,hi) in start['bounds'].items():parameters[n]=max(lo,min(hi,parameters[n]))
events=[];begin=time.monotonic();best=None;stop='fixedschedule_completed'
def decode(p):
    row={n:[p[n+':'+str(i)] for i in range(3)] for n in ['finger1','finger2','finger3','finger4','thumb']};row['pronation']=p['pronation']
    return row,{n:p['splay:'+n] for n in ['finger1','finger2','finger3','finger4']},[p['shift:'+str(i)] for i in range(3)]
def evaluate(p):
    global best
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
    row,splays,shift=decode(p);place_weapon(weapon,rig,weapon_data,shift);controls(rig,row,splays,splay_first=True)
    self_report,pts=capture(ob,rig,rest,'search'+str(len(events)),row,ww)
    contact=contacts(ob,weapon,rig,pads,'search'+str(len(events)),{'controls':row,'splays':splays,'shift':shift,'splay_first':True})
    sp,st,_=evaluated(weapon);root=rig.pose.bones['sword'].head;axis=(rig.pose.bones['sword'].tail-root).normalized()
    ids=[i for i,t in enumerate(st) if -.112<=(sum((sp[j] for j in t),Vector())/3-root).dot(axis)<=.085]
    tree=BVHTree.FromPolygons(sp,[st[i] for i in ids],all_triangles=True)
    third={n:sorted(tree.find_nearest(pts[i])[3] for i in mask)[2] for n,mask in pads.items()}
    value=(self_report['transverse_pairs'],contact['transverse_crossings_count'],len(contact['unknown_inside']),
           max(0,contact['maximum_penetration_m']-.001),max(third.values()),sum(third.values()))
    event={'index':len(events),'observed_utc':now.isoformat(),'parameters':p.copy(),'score':value,
     'self_pairs':self_report['transverse_pairs'],'sword_pairs':contact['transverse_crossings_count'],
     'unknown':len(contact['unknown_inside']),'maximum_penetration_m':contact['maximum_penetration_m'],
     'third_pad_gap_m':third,'each_digit_contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()},
     'static_numeric_gate':contact['surface_gate_pass'] and not self_report['transverse_pairs'] and not self_report['degenerate_triangles'],
     'positions_fingerprint':self_report['positions_sha256']}
    events.append(event)
    with (folder/'evaluations.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    if best is None or value<best['score']:best=event
    return event
evaluate(parameters)
# Placement first removes known initial wholehandlepenetration; then branchcurl and splay.
order=['shift:1','shift:2','shift:0']+[n for n in start['bounds'] if not n.startswith('shift:')]
for level,steps in enumerate(start['steps']):
    for sweep in range(start['fixed_sweeps_per_step']):
        for name in order:
            for sign in [-1,1]:
                if len(events)>=start['maximum_evaluations'] or time.monotonic()-begin>start['max_solver_seconds']:
                    stop='evaluation_or_time_budget';break
                step=steps['shift' if name.startswith('shift:') else 'splay' if name.startswith('splay:') else 'curl']
                test=best['parameters'].copy();lo,hi=start['bounds'][name];test[name]=max(lo,min(hi,test[name]+sign*step))
                if test==best['parameters']:continue
                evaluate(test)
            if stop!='fixedschedule_completed':break
        if stop!='fixedschedule_completed':break
    if stop!='fixedschedule_completed':break
row,splays,shift=decode(best['parameters']);place_weapon(weapon,rig,weapon_data,shift);controls(rig,row,splays,splay_first=True)
self_report,pts=capture(ob,rig,rest,'saved-best',row,ww);contact=contacts(ob,weapon,rig,pads,'saved-best',{'controls':row,'splays':splays,'shift':shift,'splay_first':True})
saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(material('r008SolverGray',(.55,.55,.55)));render(folder,'saved-best')
ob.data.materials.clear()
for m in saved:ob.data.materials.append(m)
assert geometry(ob)==rest and weights(ob)==ww
dest=out/'right_hand_actual_sword_best.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),
 'actual_evaluations':len(events),'maximum_evaluations':start['maximum_evaluations'],'elapsed_solver_seconds':time.monotonic()-begin,
 'stop':stop,'best':best,'controls':row,'splays':splays,'weapon_shift':shift,
 'final_self':self_report,'final_contact':contact,'static_numeric_gate':best['static_numeric_gate'],
 'geometry_UV_weights16bonepositions_preserved':True,'weapon_unscaled':True,'material_gate':False,
 'interval_test_started':False,'whole_character_accepted':False,'new_credits':0,
 'evaluations':artifact(folder/'evaluations.jsonl'),'views':[artifact(p) for p in sorted(folder.glob('*.png'))]}
save(folder/'result.json',report)
print('R008_SOLVER '+json.dumps({'evaluations':len(events),'bestscore':best['score'],'contacts':best['each_digit_contacts'],'gate':best['static_numeric_gate'],'shift':shift}))
