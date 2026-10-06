"""Retain full v005 failure and subset contact success; start reviewed v006."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json')
clock=read_json(QA/'phase-start.json'); start=read_json(QA/'v005-start.json'); report=read_json(QA/'v005-thumb-wrist/thumb-wrist.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002','v003','v004'] and report['final_surface_gate_pass']
assert not report['whole_budget_pass'] and any(r['SM_RO_bracer.R'] for r in report['cuff_armor_transverse_pairs_by_sample'])
now=datetime.now(timezone.utc)
review={'reviewer':'Independent hand_phase_review Astra/high read-only actual code/reports/PNG plus coordinator readback',
 'verdict':'NO_SHIP; glove/sword surface subset passed',
 'observed':'contacts4/4/5/4/4, zero penetration/crossings; cuff/bracer82/77/69/56/62;60543tri; visible bag-shaped cuff and armor intersection',
 'next_method':['Start thumb checkpoint; remove retained bad sleeve in new derivative; checkpoint has no later wrist helper',
 'Cut cap and malformed cuff; graph-ordered actual boundary loops, consistent winding and controlled loft; no world-plane angle sorting',
 'Preserve stable old-to-new source vertex identity, protected Basis/corrective/UV/weights; semantic pad masks must be identical before new replay',
 'Save wrist loft checkpoint separately from collision-directed rigid bracer trim; new wrist geometry included in collision collection',
 'Recheck5transitions, actual seams, UVs, silhouette, face budget; glove subsetPASS never replaces full gates'],
 'authority':'Advisory review; repo-local derived modeling already authorized; no new paid generation'}
write_json(QA/'v005-independent-review.json',review,exclusive=True)
paths=[QA/'v005-thumb-wrist/thumb-wrist.json',QA/'v005-thumb-wrist/wrist-transition.json',QA/'v005-independent-review.json',QA/'wrist-interface-diagnosis.json']
reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in paths]
ledger['trials'].append({'id':'v005','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
 'ended_utc':now.isoformat(),'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),
 'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
 'change':'Thumb correction retained; actual cuff radius fit and rest-relative wrist helper tested at5transitions',
 'failure_reason':'Glove/sword subsetPASS but cuff/bracer intersections and visible open bag shape remain;60543tri exceeds60k; full local gate failed',
 'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v005.json',read_json(QA/'quality-ledger.json'),exclusive=True)
write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v005.json',comparison,exclusive=True)
checkpoint=ROOT/'assets/processed/ro-swordsman-combo-r006/v005-thumb-wrist/ro_thumb_contact_checkpoint.blend'
write_json(QA/'v006-start.json',{'id':'v006','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
 'source':{'path':checkpoint.relative_to(ROOT).as_posix(),'sha256':file_sha(checkpoint)},
 'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],'local_gate_contract':start['local_gate_contract'],
 'hypothesis':'Actual ring wrist reconstruction followed by independently saved rigid bracer clearance trim; source finger/palm and contact retained',
 'maximum_corrective_m':.005,'maximum_search_events':40,'paid_operations':0,'budget':clock['budget'],'new_evidence':reports},exclusive=True)
print(json.dumps({'closed':'v005 failed; glove/sword subset passed','started':'v006','candidate_trials_used':comparison['candidate_trials_used']}))
