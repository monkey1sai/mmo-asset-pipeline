"""Close measured v006 failure and start bounded v007 regional underlay repair."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json'); clock=read_json(QA/'phase-start.json')
start=read_json(QA/'v006-start.json'); report=read_json(QA/'v006-wrist-loft-attempt2/wrist-loft.json'); diagnosis=read_json(QA/'v006-underlay-diagnosis/underlay.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002','v003','v004','v005'] and diagnosis['protected_readback_pass']
now=datetime.now(timezone.utc)
review={'reviewer':'Independent hand_phase_review Astra/high read-only actual code/reports/PNG plus coordinator readback',
 'verdict':'NO_SHIP; actual contact and seam subsets pass',
 'observed':'core/bracer329/324/331/333/359, tube3.138xstretch/.311xcompression, core ring251.26mm vs glove179.74mm;60386tri',
 'next_method':['Map intersections to source triangle IDs, own forearm weights, axial/angular region and all5radial gear coverage before any core change',
 'Regional underlay only; sleeve boundary/upperarm/torso preserved; measured old integrated bracer explains overlarge ring, not a license to delete whole core',
 'Actual newUV/basis/key/weights readback separately completed; protected915verts/1780triangleUV with no differences',
 'Fit bracer cavity and controlled cuff underlay independently, preserve semantic pads, recheck5intermediates and fixed whole views',
 'Any rigid-gear simplification is derived and requires silhouette/material comparison; no hand decimation to hide density budget'],
 'authority':'Repo-local derived repair authorized; all source/history and existing frozen targets retained'}
write_json(QA/'v006-independent-review.json',review,exclusive=True)
paths=[QA/'v006-wrist-loft-attempt2/wrist-loft.json',QA/'v006-wrist-loft-attempt2/wrist-transition.json',QA/'v006-underlay-diagnosis/underlay.json',QA/'covered-forearm-diagnosis.json',QA/'v006-independent-review.json',QA/'v006-producer.log']
reports=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in paths]
ledger['trials'].append({'id':'v006','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],
 'hypothesis':start['hypothesis'],'change':'Graph-ordered two-layer cuff loft, source semantic preservation, bracer distal trim; same-trial one-ring precondition diagnosis preserved',
 'failure_reason':'Zero glove/sword and glove+tube/bracer intersections, seam0; still visible cuff bulge and old integrated core bracer overlap329..359;60386tri; full local gate failed',
 'supporting_reports':reports})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
write_json(QA/'quality-ledger-before-v006.json',read_json(QA/'quality-ledger.json'),exclusive=True); write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-v006.json',comparison,exclusive=True)
write_json(QA/'v007-start.json',{'id':'v007','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],'source':report['artifact'],
 'request_sha256':clock['request_sha256'],'protocol_sha256':clock['protocol_sha256'],'local_gate_contract':start['local_gate_contract'],
 'hypothesis':'Scoped old integrated forearm armor underlay and cavity fitting removes duplicated volume and cuff bulge; dependent rigid shoulder simplification preserves full budget',
 'maximum_search_events':40,'paid_operations':0,'budget':clock['budget'],'new_evidence':reports},exclusive=True)
print(json.dumps({'closed':'v006 failed with contact/seam subsetPASS','started':'v007','candidate_trials_used':comparison['candidate_trials_used']}))
