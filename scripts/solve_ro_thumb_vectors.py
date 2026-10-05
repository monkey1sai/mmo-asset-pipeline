"""One registered complete-vector candidate; actual isolated joint tests."""
from datetime import datetime, timezone
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from ro_weight_vector_common import *
from weight_vector_solver import solve_vectors
from ro_core_rig import assign

clock=read(QA/'phase-start.json');start=read(QA/'v001-start.json');contract=read(QA/'local-contract.json')
folder=QA/'v001-vectors';out=ROOT/'assets/processed/ro-swordsman-combo-r008/v001-vectors'
assert not folder.exists() and not out.exists();folder.mkdir();out.mkdir(parents=True)
assert artifact(ROOT/start['source']['path'])==start['source']
assert artifact(QA/'local-contract.json')==start['contract']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/start['source']['path']),load_ui=False,use_scripts=False)
ob=bpy.data.objects['SM_RO_RightHand_Exterior'];rig=bpy.data.objects['ARM_RO_HandDiagnostic'];reset(rig)
rest=geometry(ob);original=weights(ob);points=[Vector(p) for p in rest['points']]
landmarks=[rig.data.bones[n].head_local.copy() for n in CHAIN[1:]]+[rig.data.bones['thumb_03'].tail_local.copy()]
lengths=[(b-a).length for a,b in zip(landmarks,landmarks[1:])]
def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def axial(p):
    rows=[];total=0
    for j,(a,b) in enumerate(zip(landmarks,landmarks[1:])):
        d=(b-a).normalized();s=(p-a).dot(d);clamp=max(0,min(lengths[j],s))
        rows.append(((p-a-d*clamp).length,total+(s if j==0 and s<0 or j==2 and s>lengths[j] else clamp)))
        total+=lengths[j]
    return min(rows)
targets=[];initial=[]
domain=set(contract['anatomical_domain_ids']);cap=set(contract['cap_rigid_ids']);protected=set(contract['fourfinger_protected_ids'])
for i,p in enumerate(points):
    radial,s=axial(p)
    root=smooth((s+.016)/.032)*smooth((.043-radial)/.027)
    j1=smooth((s-lengths[0]+.010)/.020);j2=smooth((s-sum(lengths[:2])+.006)/.012)
    target=[1-root,root*(1-j1),root*j1*(1-j2),root*j1*j2]
    targets.append(target)
    if i in domain:
        row=[original[i].get(n,0) for n in CHAIN]
        assert abs(sum(row)-1)<1e-5
        initial.append([x/sum(row) for x in row])
    else:
        # Domain touches only palm-side fourfinger roots; boundary is a hand anchor.
        # Actual original fourfinger vectors are never assigned/projected or changed.
        initial.append([1,0,0,0])
neighbors={i:[] for i in range(len(points))}
for a,b in rest['edges']:
    w=1/max((points[a]-points[b]).length,1e-6)
    neighbors[a].append((b,w));neighbors[b].append((a,w))
solved,convergence=solve_vectors(initial,targets,neighbors,domain,{i:[0,0,0,1] for i in cap})
for i in domain:
    assign(ob,ob.data.vertices[i],dict(zip(CHAIN,solved[i])))
actual_weights=weights(ob)
assert all(actual_weights[i]==original[i] for i in protected| (set(range(len(points)))-domain))
assert all(actual_weights[i]=={'thumb_03':1.} for i in cap)
assert geometry(ob)==rest
assert all(len(w)<=4 and abs(sum(w.values())-1)<1e-5 for w in actual_weights.values())
projection=max(max(abs(actual_weights[i].get(n,0)-solved[i][k]) for k,n in enumerate(CHAIN)) for i in domain)
save(folder/'weights.json',{'original':original,'target':targets,'final':actual_weights,'domain':sorted(domain),'cap':sorted(cap),
 'solver':convergence,'maximum_assign_pruning_float_error':projection,
 'fourfinger_geometry_UV_unchanged':True,'bone_positions_unchanged':True,
 'outside_chain_boundary_hand_projection_not_written':True})
saved=list(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(material('r008v001Gray',(.55,.55,.55)))
events=[];posed={}
for label,params in isolated_parameters():
    now=datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start['started_utc'])).total_seconds()<clock['budget']['trial_seconds']
    event,pts=actual(ob,rig,rest,label,params,actual_weights);events.append(event);posed[label]=pts
    if label in ['neutral','IP-+0.30','MCP-+0.30','CMC-+0.30','CMC-opposition-+0.15']:
        render(folder,label)
direction=[]
neutral=posed['neutral']
frozen_pads=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')['pads']['thumb']
for joint,name in [('IP','thumb_03'),('MCP','thumb_02'),('CMC','thumb_01')]:
    head=rig.data.bones[name].head_local.copy();axis=(rig.data.bones[name].tail_local-head).normalized()
    ids=[i for i in frozen_pads if (points[i]-head).dot(axis)>.005]
    assert ids
    for angle in [-.05,.05]:
        pts=posed[f'{joint}-{angle:+.2f}'];delta=sum((pts[i]-neutral[i] for i in ids),Vector())/len(ids)
        direction.append({'joint':joint,'angle':angle,'frozen_source_pad_ids':ids,'mean_delta':list(delta),'toward_palm_m':-delta.y,'expected_direction_pass':-delta.y*angle>0})
head=landmarks[0];axis=(landmarks[1]-head).normalized()
opp_ids=[i for i in frozen_pads if .01<(points[i]-head).dot(axis)<sum(lengths)-.002 and points[i].y<head.y]
assert opp_ids
for angle in [-.05,.05]:
    pts=posed[f'CMC-opposition-{angle:+.2f}'];delta=sum((pts[i]-neutral[i] for i in opp_ids),Vector())/len(opp_ids)
    direction.append({'joint':'CMC-pronation','angle':angle,'frozen_source_pad_ids':opp_ids,'mean_delta':list(delta),'toward_ulnar_m':-delta.x,'expected_direction_pass':-delta.x*angle>0})
reset(rig);ob.data.materials.clear()
for m in saved:ob.data.materials.append(m)
dest=out/'right_hand_vectors.blend';bpy.ops.wm.save_as_mainfile(filepath=str(dest))
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'source':start['source'],'artifact':artifact(dest),
 'events':events,'direction':direction,'direction_gate':all(r['expected_direction_pass'] for r in direction),
 'numeric_self_gate':all(not r['transverse_pairs'] and not r['degenerate_triangles'] for r in events),
 'weights':artifact(folder/'weights.json'),'isolated_visual_gate':'pending actual images','combined_visual_gate':'pending actual images',
 'material_gate':False,'known_crossisland_faces':16,'grip_started':False,'full_character_accepted':False,
 'maximum_fullvector_neighbor_L1':max(sum(abs(actual_weights[a].get(n,0)-actual_weights[b].get(n,0)) for n in CHAIN) for a,b in rest['edges']),
 'geometry_UV_bones_fourfinger_preserved':True,'new_credits':0,
 'views':[artifact(p) for p in sorted(folder.glob('*.png'))]}
save(folder/'result.json',report)
print('R008_VECTOR '+json.dumps({'numeric':report['numeric_self_gate'],'direction':report['direction_gate'],
 'events':[(r['label'],r['transverse_pairs'],r['maximum_edge_stretch'],r['maximum_absolute_edge_change_m']) for r in events]}))
