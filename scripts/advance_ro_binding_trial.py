"""Close v007, start final v008 with measured Boolean binding defect evidence."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'; ledger=read_json(QA/'quality-ledger.json'); request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json'); clock=read_json(QA/'phase-start.json')
start=read_json(QA/'v007-start.json'); report=read_json(QA/'v007-underlay/underlay-fit.json'); binding=json.loads((QA/'boolean-binding-diagnosis.json').read_text())
assert len(ledger['trials'])==7 and report['whole_budget_pass']; assert len(binding[1]['objects'][0]['invalid_weights'])==265
now=datetime.now(timezone.utc); reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in [QA/'v007-underlay/underlay-fit.json',QA/'v007-underlay/wrist-transition.json',QA/'boolean-binding-diagnosis.json',QA/'v007-producer.log',QA/'wrist-volume-diagnosis.json']]
ledger['trials'].append({'id':'v007','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':workbench.quality_sha256(request),'reviewer':'Coordinator actual fixed PNG and bone-weight audit; independent hand_phase_review consult',
 'hypothesis':start['hypothesis'],'change':'Scoped old integrated forearm underlay,31mm cavity Boolean, dependent shoulder reduction and2K cuff maps',
 'failure_reason':'Boolean introduced265unweighted bracer vertices; pose explosions, core/bracer170..700; cuff bulge remains;57039tri budget and glove/sword subset pass; no full localPASS',
 'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v007.json',read_json(QA/'quality-ledger.json'),exclusive=True); write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v007.json',comparison,exclusive=True)
write_json(QA/'v008-start.json',{'id':'v008','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],'source':report['artifact'],
 'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],'local_gate_contract':start['local_gate_contract'],
 'hypothesis':'Explicit rigid own-bone rebinding after Boolean restores wearable gear; dependent rest-to-pose cuff correction and61frame local GLB test verify actual export, not skill-combo acceptance',
 'maximum_search_events':40,'paid_operations':0,'budget':clock['budget'],'new_evidence':reports,
 'final_revision':True,'left_or_full_animation_expansion':'only after all right local and art gates pass; no assumed pass'},exclusive=True)
print(json.dumps({'closed':'v007 failed; measured Boolean binding defect','started':'v008 final revision','candidate_trials_used':comparison['candidate_trials_used']}))
