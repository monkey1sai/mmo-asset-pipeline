"""Close failed direction hypothesis; record new axis sign candidate first."""
from datetime import datetime,timezone
import json,hashlib
from pathlib import Path
import workbench
ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'runs/qa/ro-swordsman-combo-r008'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');ledger=read(QA/'quality-ledger.json')
request=read(ROOT/'requests/ro-swordsman-combo-r008.json');start=read(QA/'v001-start.json');result=read(QA/'v001-vectors/result.json')
assert len(ledger['trials'])==1 and not result['direction_gate'] and result['numeric_self_gate']
now=datetime.now(timezone.utc)
review={'verdict':'NO_SHIP local candidate','classification':'TEST_FAILURE: initial CMC longitudinal rotation sign opposite fixed ulnar-palmar target',
 'flexion': 'Six ±.05 direction checks pass, eighteen ±.05/.15/.30 isolated numericchecks no transverse/degenerate.',
 'opposition':'Two fixedpad ±.05 observed meanX move radial for positive rotation, opposite fixedexpectedulnar direction. Sign correction is a newcandidate, not changingtarget.',
 'visual':'Actual positiveIP/MCP/CMC palm/side show smoother thenar; signednegative/back finalreview remains incomplete, no localvisualPASS.',
 'geometry_UV_fourfinger_preserved':True,'known_material_FAIL16':True,'grip_started':False,'new_credits':0,
 'result':artifact(QA/'v001-vectors/result.json')}
save(QA/'v001-review.json',review)
ledger['trials'].append({'id':'v001','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],
 'reviewer':'Coordinator actual signed skin displacement and renderedgray views','hypothesis':start['hypothesis'],'change':start['change'],
 'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v001-review.json'),artifact(QA/'v001-vectors/result.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v002.json',read(QA/'quality-ledger.json'))
result_comparison=workbench.compare_quality(request,ledger,ROOT);assert not result_comparison['blockers'],result_comparison
(QA/'quality-ledger.json').write_text(__import__('json').dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(QA/'comparison-after-v001.json',result_comparison)
save(QA/'v002-start.json',{'id':'v002','started_utc':now.isoformat(),'budget':clock['budget'],
 'source':result['artifact'],'weights':artifact(QA/'v001-vectors/weights.json'),'contract':artifact(QA/'local-contract.json'),
 'hypothesis':'Correct axialCMC sign matches frozenulnarpad direction with same completevectorweights.',
 'change':'Only opposite longitudinalCMC rotation sign; geometry,bones,UV,weights unchanged; allisolatedsigned tests repeated; combined only aftervisual review.',
 'opposition_mode':'opposition_ulnar','previous_candidates_used':1,'candidate_limit':4,'new_credits':0})
print('R008_ADVANCE v001failed v002started')
