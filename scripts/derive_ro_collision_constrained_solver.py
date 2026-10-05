"""Recorded v004 derivation adding first-order collision halfspace constraints."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r009'
old=ROOT/'scripts/solve_ro_moving_target_contact.py';new=ROOT/'scripts/solve_ro_collision_constrained_contact.py';assert not new.exists()
s=old.read_text(encoding='utf-8').replace('v003-start.json','v004-start.json').replace('v003-moving-target','v004-collision-constraints').replace('right_hand_moving_target_contact.blend','right_hand_collision_constrained_contact.blend').replace('R009_MOVING_TARGET','R009_COLLISION_QP')
before='def evaluate(p,kind,ids=None,targets=None,full=False):'
after='''def active_proxy(points, triangles):
    sp,st,_=evaluated(weapon);tree=BVHTree.FromPolygons(sp,st,all_triangles=True)
    groups=[(i,) for i in range(len(points))]+[tuple(e) for e in rest['edges']]+[tuple(t) for t in triangles]
    rows=[]
    for group in groups:
        point=sum((points[i] for i in group),Vector())/len(group)
        hit,normal,face,gap=tree.find_nearest(point)
        if gap<start['proxy_neighborhood_m']:
            direction=point-hit
            if direction.length<1e-8:direction=normal
            direction.normalize()
            rows.append({'ids':group,'normal':list(direction),'gap_m':gap,'point':list(point),'weapon_triangle':face})
    return sorted(rows,key=lambda row:row['gap_m'])[:start['maximum_proxy_samples']]

def evaluate(p,kind,ids=None,targets=None,full=False):
    global last_points,last_triangles'''
assert s.count(before)==1;s=s.replace(before,after)
before='    row,splays,shift=apply(p);pts,tris,_=evaluated(ob);sp,st,_=evaluated(weapon)'
after=before+'\n    last_points,last_triangles=pts,tris'
assert s.count(before)==1;s=s.replace(before,after)
before='    columns=[]'
after='''    columns=[];sample_columns=[]
    base_points=[point.copy() for point in last_points]
    proxy=active_proxy(base_points,last_triangles)
    base_samples=[sum((base_points[i] for i in r['ids']),Vector())/len(r['ids']) for r in proxy]'''
assert s.count(before)==1;s=s.replace(before,after)
before='        columns.append((trial-residual)/(actual_step/scale[j]))'
after=before+'''
        moved=[sum((last_points[i] for i in r['ids']),Vector())/len(r['ids']) for r in proxy]
        shift_delta=Vector((0,0,0))
        if n.startswith('shift:'):shift_delta[int(n.split(':')[1])]=actual_step
        sample_columns.append(np.array([list((a-b-shift_delta)/(actual_step/scale[j])) for a,b in zip(moved,base_samples)]))'''
assert s.count(before)==1;s=s.replace(before,after)
before="    delta=-np.linalg.solve(J.T@J+np.eye(len(names))*start['damping'],J.T@residual)\n    delta=np.clip(delta,-start['max_normalized_step'],start['max_normalized_step']);accepted=False"
after='''    H=J.T@J+np.eye(len(names))*start['damping']
    inverse=np.linalg.inv(H);delta=-inverse@J.T@residual
    sampleJ=np.stack(sample_columns,axis=2)
    normals=np.array([r['normal'] for r in proxy])
    A=np.einsum('sc,scp->sp',normals,sampleJ)
    lower=np.maximum((lo-p)/scale,-start['max_normalized_step'])
    upper=np.minimum((hi-p)/scale,start['max_normalized_step'])
    allA=np.concatenate([A,np.eye(len(names)),-np.eye(len(names))])
    b=np.concatenate([np.array([start['proxy_clearance_m']-r['gap_m'] for r in proxy]),lower,-upper])
    for sweep in range(start['proxy_projection_sweeps']):
        for a,required in zip(allA,b):
            violation=required-float(a@delta)
            if violation>0:
                v=inverse@a;denominator=float(a@v)
                if denominator>1e-16:delta+=v*violation/denominator
        if float(np.max(b-allA@delta))<1e-7:break
    proxy_error=float(np.max(b-allA@delta))
    with (folder/'collision-constraint-observations.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'iteration':iteration,'proxy':proxy,'max_halfspace_violation_m':proxy_error,
         'normalized_delta':delta.tolist(),'projection_sweeps':sweep+1,'proxy_does_not_replace_final_collision_gate':True})+'\\n')
    if proxy_error>1e-5:stop='proxy_constraints_unsatisfied';break
    accepted=False'''
assert s.count(before)==1;s=s.replace(before,after)
with new.open('x',encoding='utf-8') as f:f.write(s)
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with (QA/'v004-solver-derivation.json').open('x',encoding='utf-8') as f:
    json.dump({'original':artifact(old),'derived':artifact(new),'method':'Hmetric projection ofcontactstep into active vertex/edge/triangle-centroid nearweapon halfspaces plus parameterbox; actual fullcollision andfixedpads remain final guards.',
              'old_code_preserved':True,'no_oldcandidate_reset':True},f,indent=2);f.write('\n')
print('R009_V004 solver derived')
