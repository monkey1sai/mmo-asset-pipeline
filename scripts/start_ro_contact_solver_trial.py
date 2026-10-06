"""Register last candidate: bounded actual-contact optimization; no asset constraint change."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r008'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r008.json');ledger=read(QA/'quality-ledger.json')
start=read(QA/'v003-start.json');result=read(QA/'v003-digit-control/result.json');assert len(ledger['trials'])==3 and not result['functional_surface_gate']
now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: actualsword cuts allfixedtemplategrasps; handselffailpersists',
 'cases':[{ 'label':r['label'],'self_pairs':r['self']['transverse_pairs'],'sword_pairs':r['contact']['transverse_crossings_count'],'penetration_m':r['contact']['maximum_penetration_m']} for r in result['events']],
 'littlefinger_isolated_counts':[r['transverse_pairs'] for r in result['littlefinger_isolated']],
 'next_hypothesis':'Frozenconstraints not provenimpossible; littlefinger3isolateddifferentPIP/DIPposes0cross. Correctcontrolledsplayorder andboundedactualcontactsolve.',
 'numeric_contact_near_is_not_holding':'Existing nearby sourcepads coincide withlargecutting; no contactPASS.',
 'material_FAIL':16,'whole_scores_changed':False,'new_credits':0}
save(QA/'v003-review.json',review)
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],
 'reviewer':'Coordinator actualsword contacts andfinitegraytemplates','hypothesis':start['hypothesis'],'change':start['change'],
 'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v003-review.json'),artifact(QA/'v003-digit-control/result.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v004.json',read(QA/'quality-ledger.json'))
comparison=workbench.compare_quality(request,ledger,ROOT);assert not comparison['blockers'],comparison
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v003.json',comparison)
bounds={}
for branch in ['finger1','finger2','finger3','finger4','thumb']:
    triples=[[.15,.50],[.60,1.4],[.30,1.05]] if branch=='finger1' else [[.10,.45],[.30,1.10],[.10,.65]] if branch=='thumb' else [[.35,1.05],[.60,1.60],[.40,1.10]]
    for i,b in enumerate(triples):bounds[branch+':'+str(i)]=b
for branch in ['finger1','finger2','finger3','finger4']:bounds['splay:'+branch]=[-.15,.15]
bounds.update(pronation=[.20,.90],**{'shift:0':[-.012,.012],'shift:1':[-.045,-.018],'shift:2':[-.035,.005]})
plan={'id':'v004','started_utc':now.isoformat(),'source':read(QA/'v002-direction/result.json')['artifact'],
 'previous_pose_source':result['artifact'],'weapon':start['weapon'],'budget':clock['budget'],
 'hypothesis':'Collisionconstrained actualcontactsolver withindependentcurl andsplay-beforecurl canformvalidfixed-sourcegrasp.',
 'change':'Onlyposevariables, splay-beforecurlcomposition, onerigidweapontranslation. Same mesh/UV/weights/boneheads, no siblingweights/correctives/rescale.',
 'bounds':bounds,'initial_controls':result['selected_controls'],'initial_splays':start['splay_radians'],'initial_shift':[0,-.033,-.024],
 'maximum_evaluations':480,'max_solver_seconds':1800,'steps':[{'curl':.10,'splay':.045,'shift':.005},{'curl':.05,'splay':.0225,'shift':.0025},{'curl':.025,'splay':.01125,'shift':.00125}],
 'fixed_sweeps_per_step':3,'adaptive_seed_restart':False,
 'objective':'Hardactualself/swordcross,unknown,depth thenworstperdigitthirdpadgap; no padresampling, no creditforsomefingersoffsetothers. Overall functiongate still requiresall originalconstraints plusvisualopposition.',
 'finaltests':'Fullsavedbest allpairs/inside/contact/image; ifstaticgatepass fixedweaponapproach->grip61actual+60half samples; onlythenUV andwholeassembly.',
 'candidate_limit':4,'previous_candidates_used':3,'new_credits':0}
save(QA/'v004-start.json',plan)
print('R008_V004 lastboundedcandidate registered')
