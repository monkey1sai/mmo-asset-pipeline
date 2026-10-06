"""Count v002 TEST_FAILURE and freeze corrected moving-target v003."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r009.json');ledger=read(QA/'quality-ledger.json')
assert len(ledger['trials'])==2
start=read(QA/'v002-start.json');result=read(QA/'v002-coupled-IK/result.json');now=datetime.now(timezone.utc)
assert not result['static_numeric_gate']
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','classification':'TEST_FAILURE: fixed absolute IKtargets omitted movingweapontranslation derivative; savedgrip also remains PRODUCT_FAILURE.',
 'source_defect':'Residual uses handpoint-fixedabsolute target; derivativeweapontranslation changes weapon only, nothandpoint ortarget, so all3translationcolumns arezero.',
 'actual_evaluations':result['actual_evaluations'],'full_function_proposals':result['full_tested_proposals'],
 'derivative_only':result['derivative_probes_not_function_tested'],'contacts':{n:r['within_2mm'] for n,r in result['final_contact']['pad_contacts'].items()},
 'minimum_edge_ratio':result['final_self']['minimum_edge_ratio'],'original_budget_preserved':True,
 'next_method':'Move frozen periterationtarget by actualrigid weapon delta forderivative; assert known -translation normalizedJacobian, preserveotherconstraints.',
 'new_credits':0,'whole_scores_changed':False,'code':artifact(ROOT/'scripts/solve_ro_coupled_hand_contact.py')}
save(QA/'v002-review.json',review)
ledger['trials'].append({'id':'v002','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator defecttrace andactualfullproposals',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],
 'supporting_reports':[artifact(QA/'v002-review.json'),artifact(QA/'v002-coupled-IK/result.json')],'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v003.json',read(QA/'quality-ledger.json'));compare=workbench.compare_quality(request,ledger,ROOT);assert not compare['blockers'],compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v002.json',compare)
plan=copy.deepcopy(start);plan.update(id='v003',started_utc=now.isoformat(),source=result['artifact'],initial_controls=result['controls'],initial_splays=result['splays'],initial_shift=result['weapon_shift'],
 hypothesis='Correctedcoupled IK movingtarget derivatives permit commonrigid placement changes to improveallfingers without earlier palmcompression.',
 change='Only solver coordinateframe correction: frozeniteration targets move by actualweapon delta; explicit3column numericalassert. Same mesh/weights/bones/UV/pads and hardconstraints.',
 previous_candidates_used=2,original_failed_v002_preserved=True,solver_derivation=artifact(QA/'v003-solver-derivation.json'))
save(QA/'v003-start.json',plan)
print('R009_V003 correctioncandidate registered')
