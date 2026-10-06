"""Freeze support domains from rest geometry and actual bones before any repair."""
from datetime import datetime, timezone
from pathlib import Path
import sys, copy, json
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ro_weight_vector_common as common
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read,save,artifact=common.read,common.save,common.artifact
clock=read(QA/'phase-start.json');baseline=read(QA/'baseline/mesh-and-weights.json')
oldcontract=read(ROOT/'runs/qa/ro-swordsman-combo-r008/local-contract.json')
masks=read(ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json')
points=[Vector(p) for p in baseline['geometry']['points']]
protected=set(oldcontract['anatomical_domain_ids']);bone=baseline['bone_points']
chains={n:[Vector(bone[f'{n}_{i:02}']['head']) for i in range(1,4)]+[Vector(bone[f'{n}_03']['tail'])] for n in ['finger1','finger2','finger3','finger4']}

def axial(p,chain):
    rows=[];total=0
    for j,(a,b) in enumerate(zip(chain,chain[1:])):
        d=(b-a).normalized();length=(b-a).length;s=(p-a).dot(d);clamp=max(0,min(length,s))
        rows.append(((p-a-d*clamp).length,total+(s if j==0 and s<0 or j==2 and s>length else clamp)))
        total+=length
    return min(rows)

support={};semantic={};caps={n:[] for n in chains};unclassified={};coordinates={}
for i,p in enumerate(points):
    coords={n:axial(p,chain) for n,chain in chains.items()};coordinates[i]={n:{'radial_m':r,'axial_m':s} for n,(r,s) in coords.items()}
    prior=masks['semantic'].get(str(i))
    if i in protected:
        unclassified[i]='protected_thumb' if prior is None else 'protected_thumb_semantic'
        continue
    if prior is not None and prior['branch']!='thumb':
        n=prior['branch'];semantic[i]={'role':'finger_body','branch':n};support[i]=['hand']+[f'{n}_{j:02}' for j in range(1,4)]
        chain=chains[n];axis=(chain[3]-chain[2]).normalized()
        if (p-chain[2]).dot(axis)>.65*(chain[3]-chain[2]).length:caps[n].append(i)
    else:
        eligible=sorted((r,n) for n,(r,s) in coords.items() if -.024<s<.010 and r<.024 and p.z>.165)
        if eligible:
            names=[n for _,n in eligible[:2]];semantic[i]={'role':'palm_root_or_web','branches':names}
            support[i]=['hand']+[n+'_01' for n in names];unclassified[i]='palm_root_or_web'
        else:unclassified[i]='protected_central_palm_or_wrist'
assert all(len(ids)>=3 for ids in caps.values())
assert all(i in support for i in [277,278,372,388])
assert not set(support)&protected
now=datetime.now(timezone.utc)
contract={'created_utc':now.isoformat(),'source':clock['local_source'],'baseline_geometry_weights':artifact(QA/'baseline/mesh-and-weights.json'),
 'method':'Simultaneous full16bone vector solve with immutable perpoint allowed support; every iteration projects illegal neighbor influences; no sequential branch overwrite.',
 'supports':support,'semantic_roles':semantic,'unclassified_assignments':unclassified,'rest_branch_coordinates':coordinates,
 'thumb_protected_ids':sorted(protected),'thumb_cap_ids':oldcontract['cap_rigid_ids'],'fourfinger_rigid_caps':caps,
 'new_domain_thumb_overlap':[],'bones_and_geometry_UV_fixed_for_v001':True,'actual_sword_unscaled':True,'rig_and_objects_must_be_identity':True,
 'support_rule':'Body hand+ownthreebones; rest-space unclassified root/web (-24mm<axial<10mm,radial<24mm,Z>165mm) hand+nearest up to2proximalbones; centralpalm/wrist andthumb fixed.',
 'cap_rule':'Prior anatomicalbranch AND DIPaxis >65percent of terminalbone length. Not chosen by prior weight.',
 'target_halfwidths_m':[.016,.010,.006],'solver':{'iterations':600,'relaxation':.7,'fidelity':.35},
 'static_grip':'Keep r008savedactualbasis andsameactualsword for weight A/B; no new contact search in v001.',
 'shape_trigger':{'min_ratio':.25,'max_ratio':3,'purpose':'conservative stop/visual inspection; not volume or art PASS'},
 'functional_gate':'Fixed5pads each>=3pointswithin2mm, unknowninside0, transverse_self/sword0, finite maxpenetration<=1mm, actualgrayvisualshape required.',
 'interval_sword_attachment':'Static local test only until actualweapon followrig relationship is separately built and verified.',
 'whole_spec_unchanged':True,'whole300_left_materials_VFX_animatedGLB':'separate prerequisites and acceptance'}
save(QA/'local-contract.json',contract)
request=read(ROOT/'requests/ro-swordsman-combo-r009.json');oldtrial=read(ROOT/'runs/qa/ro-swordsman-combo-r008/quality-ledger.json')['trials'][0]
trial=copy.deepcopy(oldtrial);trial.update(started_utc=clock['baseline_started_utc'],ended_utc=now.isoformat(),elapsed_seconds=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),reviewer='Coordinator freshwhole views andactualsaved localbaseline; originalfailedfullscope scores preserved')
trial['previews']={n:artifact(QA/'baseline'/f'{n}.png') for n in request['quality']['protocol']['views']}
evidence=trial['evidence'];whole=read(QA/'baseline/whole-baseline.json')
evidence.update(request_id=request['id'],request_sha256=workbench.request_sha256(request),deliverables=whole['artifacts'],subject_artifacts=whole['artifacts'],local_gate_contract=artifact(QA/'local-contract.json'))
evidence.pop('quality_ledger',None)
for row in evidence['checks'].values():row['artifacts']+=[artifact(QA/'baseline/whole-baseline.json'),artifact(QA/'baseline/local-baseline.json')]
ledger={'schema_version':1,'request_id':request['id'],'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'local_gate_contract':artifact(QA/'local-contract.json'),'trials':[trial],'phase_history':request['phase_history']}
comparison=workbench.compare_quality(request,ledger,ROOT);assert not comparison['blockers'],comparison
save(QA/'quality-ledger.json',ledger);save(QA/'comparison-baseline.json',comparison)
save(QA/'v001-start.json',{'id':'v001','started_utc':now.isoformat(),'source':clock['local_source'],'contract':artifact(QA/'local-contract.json'),'budget':clock['budget'],
 'hypothesis':'Fourfinger completechain +sharedroot legalvector gradients reduce original hard-weight collapse without changing sourcegeometry/bones orselectedgrip.',
 'change':'600 fixed simultaneous projected graph iterations; fixed anatomical caps,16/10/6mm targethalfwidths; protected203thumb points, unchanged actualweapon andcontrols.',
 'new_credits':0,'candidate_limit':4,'previous_candidates_used':0})
print('R009_CONTRACT '+json.dumps({'domain':len(support),'caps':{n:len(ids) for n,ids in caps.items()},'unclassified':{role:list(unclassified.values()).count(role) for role in set(unclassified.values())},'candidate':'v001'}))
