"""Record observed v002 failure and new independently reviewed joint-IK method."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); clock=read_json(QA/'phase-start.json')
request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json'); start=read_json(QA/'v002-start.json')
report=read_json(QA/'v002-calibration/calibration.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001']
assert not report['surface_gate_pass'] and report['total_events']==36
now=datetime.now(timezone.utc); elapsed=(now-datetime.fromisoformat(start['started_utc'])).total_seconds()
review={'reviewer':'hand_phase_review independent Astra/high read-only review plus coordinator actual PNG readback',
    'verdict':'NO_SHIP','observed':'34search+2readback; source masks unchanged; all36 fail. Final0penetration/0crossings, four fingers10.27–17.66mm minimum gap and0 contacts, thumb1contact. Sleeve still open, whole60543tri.',
    'method_findings':['Scalar penalty cannot certify or prioritize true hard-gate compliance; pass candidates must sort first',
        'One angle with fixed three-joint ratio cannot isolate source topology as failure cause',
        'Gate must reject incomplete/empty/duplicate/out-of-range fixed anatomical masks'],
    'next_method':'Fixed palm/handle relationship, actual independent joint IK against an inflated physical handle cross-section; actual full surface checks remain authoritative',
    'scope':'No left/full animation/effects after right gate fails; no new API credit/state file'}
write_json(QA/'v002-independent-review.json',review,exclusive=True)
reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in [QA/'v002-calibration/calibration.json',QA/'v002-calibration/search-events.json',QA/'v002-independent-review.json']]
ledger['trials'].append({'id':'v002','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':now.isoformat(),'elapsed_seconds':elapsed,'protocol_sha256':workbench.quality_sha256(request),
    'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
    'change':'Retained wrist deletion, cuff weights and thenar blend,34 bounded coupled-angle surface searches',
    'failure_reason':'Safe selected pose has no full finger contacts; wrist opening/tri budget also fail',
    'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v002.json',read_json(QA/'quality-ledger.json'),exclusive=True)
write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v002.json',comparison,exclusive=True)
write_json(QA/'v003-start.json',{'id':'v003','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'source':report['artifact'],'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],
    'local_gate_contract':start['local_gate_contract'],'hypothesis':review['next_method'],'maximum_search_events':40,
    'paid_operations':0,'budget':clock['budget'],'new_evidence':reports},exclusive=True)
print(json.dumps({'closed':'v002 failed','started':'v003','revisions_used':comparison['candidate_trials_used']}))
