"""One local v002 weight hypothesis; preserve geometry, UVs, source and search budget."""
from collections import Counter
from datetime import datetime,timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from ro_core_rig import assign,distance,curl_digits,pose
from ro_review_common import camera
OUT=ROOT/'assets/processed/ro-swordsman-combo-r005/v002-digit-weights'
QA=ROOT/'runs/qa/ro-swordsman-combo-r005/v002-digit-weights'
previous=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-contact-calibrated/calibration.json').read_text())
artifact=previous['artifact']; source=ROOT/artifact['path']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if OUT.exists() or QA.exists() or sha(source)!=artifact['sha256']: raise RuntimeError('Preserve local hypotheses and source')
phase=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text()); start=json.loads((ROOT/'runs/qa/ro-swordsman-combo-r005/v002-start.json').read_text())
now=datetime.now(timezone.utc)
if (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds'] or (now-datetime.fromisoformat(start['started_utc'])).total_seconds()>=phase['budget']['trial_seconds']: raise RuntimeError('Original budget exhausted')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
rig=bpy.data.objects['ARM_RO_Swordsman']; core=bpy.data.objects['SM_RO_core']; state=json.loads(rig['state_json']); original=copy.deepcopy(state)
coordinates=[tuple(v.co) for v in core.data.vertices]
uvs=[tuple(v.uv) for v in core.data.uv_layers.active.data]
polygons=[tuple(p.vertices) for p in core.data.polygons]
OUT.mkdir(parents=True); QA.mkdir(parents=True)
(QA/'rig-helper-used.py').write_bytes((ROOT/'scripts/ro_core_rig.py').read_bytes())

def views(folder,side,diagnostic=False):
    folder.mkdir(parents=True,exist_ok=True)
    hidden=[]
    if diagnostic:
        for ob in bpy.data.collections['COL_Character'].objects:
            if ob.type=='MESH' and ob not in (core,bpy.data.objects['SM_RO_sword']):
                hidden.append((ob,ob.hide_render)); ob.hide_render=True
    target=rig.pose.bones['hand.'+side].head.lerp(rig.pose.bones['hand.'+side].tail,.60)
    for name,offset in [('front',(.30,-1,.15)),('side',(1,.10,.1)),('back',(-.3,1,.12))]:
        camera((tuple(target+Vector(offset)),tuple(target),.28)); bpy.context.scene.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
    for ob,value in hidden: ob.hide_render=value

for side in ['R','L']:
    pose(rig,original,.89,(-.08 if side=='R' else .08,-.29,1.12),(0,-.1,.995),two_hands=False,active_side=side)
    views(QA/('before-'+side),side,True)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()

# Actual separate distal branches in the repaired, position-welded production core.
adj=[set() for v in core.data.vertices]
for e in core.data.edges:
    a,b=e.vertices; adj[a].add(b); adj[b].add(a)
labels={}; branch_counts={}
for side,sign in [('R',-1),('L',1)]:
    remaining={v.index for v in core.data.vertices if sign*v.co.x>.33 and v.co.z<.839}
    groups=[]
    while remaining:
        seed=remaining.pop(); group={seed}; queue=[seed]
        while queue:
            i=queue.pop()
            for j in adj[i]:
                if j in remaining: remaining.remove(j); group.add(j); queue.append(j)
        if len(group)>=5: groups.append(group)
    groups.sort(key=lambda g:sign*sum(core.data.vertices[i].co.x for i in g)/len(g))
    if len(groups)!=4: raise RuntimeError('Actual four distal branches not found')
    branch_counts[side]=[len(g) for g in groups]
    for finger,group in enumerate(groups,1):
        for index in group: labels[index]='finger'+str(finger)

def weights(v): return {core.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}
def branch_for(v,side):
    if v.index in labels: return labels[v.index]
    p=v.co; rest=state['rest']
    candidates=[('finger'+str(i),distance(p,rest[f'finger{i}.{side}_01'])) for i in range(1,5)]
    candidates+=[('thumb',min(distance(p,rest[f'thumb.{side}_01']),distance(p,rest[f'thumb.{side}_02'])))]
    return min(candidates,key=lambda x:x[1])[0]
before_bad=[]; modified=[]; semantic={}
for v in core.data.vertices:
    if abs(v.co.x)<=.34 or v.co.z>=.905: continue
    side='L' if v.co.x>0 else 'R'; branch=branch_for(v,side)
    if branch=='thumb': names=[f'thumb.{side}_01',f'thumb.{side}_02']
    else: names=[f'{branch}.{side}_01',f'{branch}.{side}_02']
    legal={'hand.'+side,*names}; current=weights(v)
    bad={n:w for n,w in current.items() if n not in legal}
    if bad: before_bad.append({'vertex':v.index,'branch':branch,'illegal_weights':bad})
    h,m=map(Vector,state['rest'][names[0]]); t=Vector(state['rest'][names[1]][1]); direction=(t-h).normalized()
    s=(v.co-h).dot(direction); middle=(m-h).dot(direction)
    hand=max(0,min(1,(.018-s)/.030))
    distal=max(0,min(1,(s-middle+.010)/.020))
    new={'hand.'+side:hand,names[0]:(1-hand)*(1-distal),names[1]:(1-hand)*distal}
    assign(core,v,new); modified.append(v.index); semantic[v.index]=legal
after_bad=[v.index for v in core.data.vertices if v.index in semantic and any(n not in semantic[v.index] for n in weights(v))]
if after_bad: raise RuntimeError('Sibling branch weight leakage remains')
state['digit_axis_method']='individual_centerline_cross_palm'
state['digit_weight_method']='actual distal graph branches; proximal centerline Voronoi; only hand plus own two digit joints, continuous root and joint blends, no cross-digit smoothing'
state['contact_search_evaluations_used']=previous['evaluations']; state['contact_search_maximum']=previous['maximum_evaluations']
rig['state_json']=json.dumps(state)
saved=copy.deepcopy(state); state.pop('finger_angles',None)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
for side in ['R','L']: curl_digits(rig,state,side,.30)
for side in ['R','L']: views(QA/('small-curl-'+side),side,True)
state=saved
for side in ['R','L']:
    pose(rig,state,.89,(-.08 if side=='R' else .08,-.29,1.12),(0,-.1,.995),two_hands=False,active_side=side)
    views(QA/('after-'+side),side,True); views(QA/('assembled-'+side),side,False)
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
if coordinates!=[tuple(v.co) for v in core.data.vertices] or uvs!=[tuple(v.uv) for v in core.data.uv_layers.active.data] or polygons!=[tuple(p.vertices) for p in core.data.polygons]: raise RuntimeError('Unexpected geometry/UV change')
invalid=[]
for v in core.data.vertices:
    values=list(weights(v).values())
    if not values or len(values)>4 or abs(sum(values)-1)>1e-5: invalid.append(v.index)
if invalid: raise RuntimeError('Invalid weights')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ro_digit_weights.blend'))
report={'trial':'v002','hypothesis':'sibling digit weights and a shared axis contribute to folding; local isolated branch weights and per-bone axes tested without further search',
        'source':artifact,'source_preserved':sha(source)==artifact['sha256'],'actual_distal_branch_vertices':branch_counts,'modified_weight_vertices':len(modified),'before_vertices_with_illegal_branch_weights':len(before_bad),'before_bad_examples':before_bad[:30],
        'after_illegal_branch_weights':after_bad,'invalid_weights':invalid,'geometry_and_uv_unchanged':True,'search_evaluations_prior_and_after':[previous['evaluations'],previous['evaluations']],
        'rig_accepted':False,'art_accepted':False,'artifact':{'path':(OUT/'ro_digit_weights.blend').relative_to(ROOT).as_posix(),'sha256':sha(OUT/'ro_digit_weights.blend')}}
(QA/'weights.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_DIGIT_WEIGHTS '+json.dumps({k:v for k,v in report.items() if k!='before_bad_examples'}))
