"""Close v003 and prospectively register the last collision-aware candidate."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r009.json');ledger=read(QA/'quality-ledger.json');assert len(ledger['trials'])==3
start=read(QA/'v003-start.json');result=read(QA/'v003-moving-target/result.json');now=datetime.now(timezone.utc);assert not result['static_numeric_gate']
events=[json.loads(line) for line in (QA/'v003-moving-target/evaluations.jsonl').read_text(encoding='utf-8').splitlines()]
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: correcteddampedcontact direction blocked byactualswordcrossing',
 'preflight':artifact(QA/'v003-moving-target/translation-preflight.json'),'actual_evaluations':result['actual_evaluations'],'full_proposals':result['full_tested_proposals'],
 'derivative_or_base_probes_not_functionchecked':result['derivative_probes_not_function_tested'],
 'rejected_crossings':[e['sword_pairs'] for e in events if e['collision_test']=='actual_full' and not e['admissible']],
 'stop':result['stop'],'next_hypothesis':'Actualnearcontact collision constraints canpermit tangent directions rather thanleast-squares step followed only by rejection.',
 'sourcebone_meshfailure_not_proven':True,'new_credits':0,'whole_scores_changed':False}
save(QA/'v003-review.json',review)
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator signedderivative preflight andguardedactualproposals',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],
 'supporting_reports':[artifact(QA/'v003-review.json'),artifact(QA/'v003-moving-target/result.json')],'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v004.json',read(QA/'quality-ledger.json'));compare=workbench.compare_quality(request,ledger,ROOT);assert not compare['blockers'],compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v003.json',compare)
plan=copy.deepcopy(start);plan.update(id='v004',started_utc=now.isoformat(),source=result['artifact'],initial_controls=result['controls'],initial_splays=result['splays'],initial_shift=result['weapon_shift'],
 hypothesis='Actual vertex/edge/face-centroid nearcontact halfspaces constrain coupledstep tofind collisionfree tangentialgrasp adjustment.',
 change='Onlycontrol solvingmethod: Hmetric cyclic projection on frozen-periteration collisionproxys andparameterbox. Same sourceskeleton/weights/mesh/UV/fixedpads andactualsworddimension.',
 previous_candidates_used=3,maximum_evaluations=700,maximum_proxy_samples=96,proxy_neighborhood_m=.004,proxy_clearance_m=.00005,proxy_projection_sweeps=400,
 solver_derivation=artifact(QA/'v004-solver-derivation.json'),proxy_limitations='Localsignednearest surface approximation excludesunselectedsamples/tangency/curvature; allaccepted proposals still actual triangle/sample tests.')
save(QA/'v004-start.json',plan)
print('R009_V004 lastcandidate registered')
