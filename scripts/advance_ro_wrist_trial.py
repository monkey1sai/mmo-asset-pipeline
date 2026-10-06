"""Retain v004 contact/visual regression; start independently reviewed v005."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json')
clock=read_json(QA/'phase-start.json'); start=read_json(QA/'v004-start.json'); report=read_json(QA/'v004-corrective/corrective.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002','v003'] and not report['surface_gate_pass']
now=datetime.now(timezone.utc)
review={'reviewer':'Independent hand_phase_review Astra/high read-only actual code/reports/PNG plus coordinator readback',
    'verdict':'NO_SHIP','observed':'v004 zero penetration/crossings but thumb2contact; new sleeve flat patches regress fitting; whole60699tri',
    'next_method':['Keep all54thumb pads; freeze own-branch plus1-ring neighborhood for smooth local contact; no nearest3selection',
        'Remove failed derived sleeve; fit actual cuff surface before adding another sleeve',
        'Helper must slerp pose-times-rest-inverse rotations at wrist pivot and update on every replay',
        'Rebuild actual skin inverse after weight changes; evaluate0/.25/.5/.75/1 wrist/corrective transition',
        'Actual five-pad/sword check does not cover armor fitting; add separate cuff/armor crossings and closeups'],
    'method_correction':'v004 crossing projection uses closest sword face to glove-face centroid as a heuristic, not necessarily crossed face. Final0crossings remains verified; preserve original code/result.',
    'authority':'Advisory review; no new permission required for repo-local correction'}
write_json(QA/'v004-independent-review.json',review,exclusive=True)
paths=[QA/'v004-corrective/corrective.json',QA/'v004-corrective/corrective-events.json',QA/'v004-independent-review.json']
reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in paths]
ledger['trials'].append({'id':'v004','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':now.isoformat(),'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),
    'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
    'change':'Bounded3.804mm corrective removes collision; cuff blending and156tri sleeve attempted',
    'failure_reason':'Thumb only2contacts; new wrist flat patches regress fitting; whole60699tri; no full localPASS',
    'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v004.json',read_json(QA/'quality-ledger.json'),exclusive=True)
write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v004.json',comparison,exclusive=True)
write_json(QA/'v005-start.json',{'id':'v005','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'source':report['artifact'],'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],
    'local_gate_contract':start['local_gate_contract'],'hypothesis':'Two isolated checkpoints: smooth thumb contact, then rest-relative wrist helper/cuff fit with actual intermediate deformation checks',
    'maximum_corrective_m':.005,'maximum_search_events':40,'paid_operations':0,'budget':clock['budget'],'new_evidence':reports},exclusive=True)
print(json.dumps({'closed':'v004 failed','started':'v005','candidate_trials_used':comparison['candidate_trials_used']}))
