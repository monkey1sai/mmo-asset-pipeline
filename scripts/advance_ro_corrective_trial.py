"""Preserve v003 failure and begin a bounded local corrective/fitting experiment."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); start=read_json(QA/'v003-start.json'); clock=read_json(QA/'phase-start.json')
request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json'); report=read_json(QA/'v003-joint-ik/joint-ik.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002'] and not report['surface_gate_pass']
now=datetime.now(timezone.utc)
paths=[QA/'v003-joint-ik/joint-ik.json',QA/'v003-joint-ik/search-events.json',QA/'v003-joint-ik/mask-guard-tests.json']
reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in paths]
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':now.isoformat(),'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),
    'protocol_sha256':workbench.quality_sha256(request),'reviewer':'Coordinator actual three grip PNG and complete surface report',
    'hypothesis':start['hypothesis'],'change':'Fixed palm/handle and independently solved phalanx IK,37 searches+2readbacks,5 invalid masks rejected',
    'failure_reason':'All five pad groups have4/4/7/4/4 contact vertices but actual2.051mm penetration and54 transverse triangle pairs; cuff fitting incomplete',
    'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v003.json',read_json(QA/'quality-ledger.json'),exclusive=True)
write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v003.json',comparison,exclusive=True)
write_json(QA/'v004-start.json',{'id':'v004','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'source':report['artifact'],'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],
    'local_gate_contract':start['local_gate_contract'],'hypothesis':'Millimetre-scale corrective shape against actual sword, continuous cuff lower-arm/hand weights and independently authored sleeve fitting',
    'maximum_corrective_iterations':12,'maximum_rest_corrective_m':.005,'paid_operations':0,'budget':clock['budget'],'new_evidence':reports},exclusive=True)
print(json.dumps({'closed':'v003 failed','started':'v004','candidate_trials_used':comparison['candidate_trials_used']}))
