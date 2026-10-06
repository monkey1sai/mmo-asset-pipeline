"""Bounded coupled finite-difference IK on actual skinned points, guarded proposals."""
from datetime import datetime,timezone
from pathlib import Path
import sys,time,hashlib,json,bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import ro_actual_grip_common as grip
from ro_hand_gate import evaluated,contacts
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
start=read(QA/'v003-start.json');clock=read(QA/'phase-start.json');folder=QA/'v003-moving-target';out=ROOT/'assets/processed/ro-swordsman-combo-r009/v003-moving-target'
folder.mkdir();out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];weapon=bpy.data.objects['SM_RO_LocalActualSword']
rest=common.geometry(ob);ww=common.weights(ob);weapon_data=read(ROOT/start['weapon']['path']);pads=read(ROOT/start['pads_source'])['pads']
names=list(start['bounds']);lo=np.array([start['bounds'][n][0] for n in names]);hi=np.array([start['bounds'][n][1] for n in names])
scale=np.array([.03 if n.startswith('shift:') else 1 for n in names])
initial={n:start['initial_controls'][n.split(':')[0]][int(n.split(':')[1])] for n in names if ':' in n and not n.startswith(('shift:','splay:'))}
initial.update({'splay:'+n:v for n,v in start['initial_splays'].items()});initial['pronation']=start['initial_controls']['pronation'];initial.update({'shift:'+str(i):v for i,v in enumerate(start['initial_shift'])})
p=np.clip(np.array([initial[n] for n in names]),lo,hi);events=[];begin=time.monotonic();stop='maximum_iterations';best=None

def apply(p):
    values=dict(zip(names,p));row={n:[float(values[n+':'+str(i)]) for i in range(3)] for n in ['finger1','finger2','finger3','finger4','thumb']};row['pronation']=float(values['pronation'])
    splays={n:float(values['splay:'+n]) for n in ['finger1','finger2','finger3','finger4']};shift=[float(values['shift:'+str(i)]) for i in range(3)]
    grip.place_weapon(weapon,rig,weapon_data,shift);grip.controls(rig,row,splays,splay_first=True)
    return row,splays,shift

def budget():
    now=datetime.now(timezone.utc)
    return len(events)<start['maximum_evaluations'] and time.monotonic()-begin<start['max_solver_seconds'] and (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']

def evaluate(p,kind,ids=None,targets=None,full=False):
    row,splays,shift=apply(p);pts,tris,_=evaluated(ob);sp,st,_=evaluated(weapon)
    root=rig.pose.bones['sword'].head;axis=(rig.pose.bones['sword'].tail-root).normalized()
    selected=[t for t in st if -.112<=(sum((sp[j] for j in t),Vector())/3-root).dot(axis)<=.085]
    tree=BVHTree.FromPolygons(sp,selected,all_triangles=True)
    gaps={n:sorted((tree.find_nearest(pts[i])[3],i) for i in mask) for n,mask in pads.items()}
    chosen=[i for n in pads for _,i in gaps[n][:3]]
    target_positions=[]
    for i in chosen:
        hit,normal,face,distance=tree.find_nearest(pts[i]);direction=pts[i]-hit
        direction=direction.normalized() if direction.length>1e-8 else normal
        target_positions.append(hit+direction*start['point_target_distance_m'])
    moving_targets = [target + Vector(shift) - guide_shift for target in targets] if targets is not None else target_positions
    residual=np.array([component for i,target in zip(ids or chosen, moving_targets) for component in pts[i]-target])
    score=(max(rows[2][0] for rows in gaps.values()),sum(rows[2][0] for rows in gaps.values()))
    event={'index':len(events),'observed_utc':datetime.now(timezone.utc).isoformat(),'kind':kind,'parameters':[float(x) for x in p],
           'third_pad_gaps_m':{n:rows[2][0] for n,rows in gaps.items()},'guide_ids':ids if ids is not None else chosen,
           'recomputed_near_ids':chosen,'linearization_targets':[list(target) for target in moving_targets],
           'positions_sha256':hashlib.sha256(json.dumps([list(point) for point in pts]).encode()).hexdigest(),'collision_test':'not_run_derivative' if not full else 'actual_full',
           'score':score}
    valid=False
    if full:
        self_report,_=grip.capture(ob,rig,rest,kind,row,ww);contact=contacts(ob,weapon,rig,pads,kind,{'row':row,'splays':splays,'shift':shift})
        valid=not self_report['transverse_pairs'] and not self_report['degenerate_triangles'] and not contact['transverse_crossings_count'] and not contact['unknown_inside'] and contact['maximum_penetration_m']<=.001 and self_report['minimum_edge_ratio']>=.25 and self_report['maximum_edge_stretch']<=3
        event.update(admissible=valid,self_pairs=self_report['transverse_pairs'],sword_pairs=contact['transverse_crossings_count'],depth_m=contact['maximum_penetration_m'],minratio=self_report['minimum_edge_ratio'],maxratio=self_report['maximum_edge_stretch'],contacts={n:v['within_2mm'] for n,v in contact['pad_contacts'].items()},static_numeric_gate=valid and contact['surface_gate_pass'])
    events.append(event)
    with (folder/'evaluations.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
    return residual,chosen,target_positions,event

_,_,_,best=evaluate(p,'initial',full=True);assert best['admissible']
preflight_residual,preflight_ids,preflight_targets,_=evaluate(p,'translation-preflight-base')
guide_shift=Vector([float(p[names.index('shift:'+str(i))]) for i in range(3)])
preflight_points,_,_=evaluated(ob)
save(folder/'translation-preflight-points.json',{'points':[list(v) for v in preflight_points],
     'ids':preflight_ids,'targets':[list(v) for v in preflight_targets],'shift':list(guide_shift)})
preflight_checks=[]
for axis in range(3):
    j=names.index('shift:'+str(axis))
    for sign in [-1,1]:
        test=p.copy();test[j]=np.clip(p[j]+sign*.0002,lo[j],hi[j]);step=test[j]-p[j]
        assert abs(step)>1e-8
        residual,_,_,event=evaluate(test,'translation-preflight-signed',preflight_ids,preflight_targets)
        expected=np.zeros((len(preflight_ids),3));expected[:,axis]=-step
        error=float(np.max(np.abs((residual-preflight_residual).reshape(-1,3)-expected)))
        current,_,_=evaluated(ob);point_delta=max((a-b).length for a,b in zip(current,preflight_points))
        assert error<1e-7 and point_delta<1e-7, 'MOVING_TARGET_SIGNED_TRANSLATION_PREFLIGHT_FAIL'
        preflight_checks.append({'axis':axis,'sign':sign,'actual_step_m':float(step),'maximum_residual_error_m':error,'maximum_handpoint_change_m':point_delta})
save(folder/'translation-preflight.json',{'checks':preflight_checks,'pass':True,'tolerance_m':1e-7,'fixed_ids':preflight_ids})
for iteration in range(start['maximum_iterations']):
    if not budget():stop='evaluation_or_time_budget';break
    residual,ids,targets,base=evaluate(p,'jacobian-base')
    guide_shift=Vector([float(p[names.index('shift:'+str(i))]) for i in range(3)])
    columns=[]
    for j,n in enumerate(names):
        if not budget():stop='evaluation_or_time_budget';break
        step=start['finite_steps']['shift' if n.startswith('shift:') else 'curl'];test=p.copy();test[j]=min(hi[j],test[j]+step)
        if test[j]==p[j]:test[j]=max(lo[j],p[j]-step)
        actual_step=test[j]-p[j]
        trial,_,_,event=evaluate(test,'derivative',ids,targets)
        columns.append((trial-residual)/(actual_step/scale[j]))
    if len(columns)!=len(names):break
    J=np.stack(columns,axis=1)
    for axis in range(3):
        column=J[:,names.index('shift:'+str(axis))].reshape(-1,3)
        expected=np.zeros_like(column);expected[:,axis]=-.03
        assert np.max(np.abs(column-expected))<1e-5, 'WEAPON_TRANSLATION_JACOBIAN_INCORRECT'
    with (folder/'jacobian-observations.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'iteration':iteration,'fixed_ids':ids,'targets':[list(v) for v in targets],
          'column_norms':np.linalg.norm(J,axis=0).tolist(),'translation_column_max_errors':
          [float(np.max(np.abs(J[:,names.index('shift:'+str(axis))].reshape(-1,3)-np.eye(3)[axis]*(-.03)))) for axis in range(3)],
          'base_residual':residual.tolist(),'predicted_delta':(-J.T@residual).tolist()})+'\n')
    delta=-np.linalg.solve(J.T@J+np.eye(len(names))*start['damping'],J.T@residual)
    delta=np.clip(delta,-start['max_normalized_step'],start['max_normalized_step']);accepted=False
    for factor in start['line_search_factors']:
        if not budget():stop='evaluation_or_time_budget';break
        test=np.clip(p+delta*scale*factor,lo,hi);_,_,_,event=evaluate(test,'line-proposal',full=True)
        if event['admissible'] and tuple(event['score'])<tuple(best['score']):p=test;best=event;accepted=True;break
    if best.get('static_numeric_gate'):stop='static_numeric_gate';break
    if not accepted:stop='bounded_line_search_stalled';break
row,splays,shift=apply(p);self_report,pts=grip.capture(ob,rig,rest,'saved-best',row,ww);contact=contacts(ob,weapon,rig,pads,'saved-best',{'row':row,'splays':splays,'shift':shift})
saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(common.material('r009CoupledGray',(.55,.55,.55)));common.render(folder,'saved-best')
ob.data.materials.clear()
for m in saved:ob.data.materials.append(m)
assert common.geometry(ob)==rest and common.weights(ob)==ww
save(folder/'posed-points.json',{'points':[list(point) for point in pts]})
dest=out/'right_hand_moving_target_contact.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
save(folder/'result.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),
 'evaluations':artifact(folder/'evaluations.jsonl'),'actual_evaluations':len(events),'full_tested_proposals':sum(e['collision_test']=='actual_full' for e in events),
 'derivative_probes_not_function_tested':sum(e['collision_test']!='actual_full' for e in events),'stop':stop,'elapsed_solver_seconds':time.monotonic()-begin,
 'best':best,'controls':row,'splays':splays,'weapon_shift':shift,'final_self':self_report,'final_contact':contact,
 'geometry_UV_weights_bones_preserved':True,'actualweapon_unscaled':True,'new_credits':0,'static_numeric_gate':best.get('static_numeric_gate',False),
 'raw_points':artifact(folder/'posed-points.json'),'views':[artifact(p) for p in sorted(folder.glob('*.png'))]})
print('R009_MOVING_TARGET '+json.dumps({'evals':len(events),'full':sum(e['collision_test']=='actual_full' for e in events),'stop':stop,'bestscore':best['score'],'contacts':{n:r['within_2mm'] for n,r in contact['pad_contacts'].items()}}))
