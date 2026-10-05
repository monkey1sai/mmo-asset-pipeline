"""Archive final failed prototype and enforce original three-revision stop."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r005'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
ledger=read(QA/'quality-ledger.json'); request=read(ROOT/'requests/ro-swordsman-combo-r005.json'); start=read(QA/'v003-start.json'); phase=read(QA/'phase-accounting.json')
if [t['id'] for t in ledger['trials']]!=['baseline','v001','v002']: raise RuntimeError('Preserve recorded trials')
surface=read(QA/'v003-hand-surface/surface.json'); old_search=read(QA/'v002-contact-calibrated/calibration.json')
logged=dict(Counter(row['side'] for row in old_search['search_log']))
save(QA/'search-count-reconciliation.json',{'reported_prior_evaluations':old_search['evaluations'],'logged_prior_candidates':sum(logged.values()),'logged_by_side':logged,
    'difference_without_per_call_events':old_search['evaluations']-sum(logged.values()),
    'source_derived_explanation':'The saved optimizer source calls evaluate(side) three additional times per hand: baseline before the search; readback after selected grip; final readback.47 logged +3 =50 per side. These six events lack individual log rows, so per-side50/80 is source-derived, not a complete event trace.',
    'source':{'path':'scripts/optimize_ro_core_contact.py','sha256':sha(ROOT/'scripts/optimize_ro_core_contact.py')},
    'new_logged_searches':surface['new_searches'],'reported_accumulated_evaluations':surface['global_search_used'],'count_gap_releases_budget':False,'new_search_authorized_by_gap':False})
save(QA/'v002-axis-review-correction.json',{'classification':'TEST_FAILURE','affected_report':'v002-final-review.json and independent review of v002-digit-weights',
    'correction':'Sibling weight removal remains verified, but the individual axis direction was reversed in that test. v002 shape results cannot isolate source topology as the sole cause. v002 remains failed because actual grip was not accepted.',
    'old_helper':{'path':'runs/qa/ro-swordsman-combo-r005/v002-digit-weights/rig-helper-used.py','sha256':sha(QA/'v002-digit-weights/rig-helper-used.py')},
    'corrected_method_report':{'path':'runs/qa/ro-swordsman-combo-r005/v003-hand-direction/direction.json','sha256':sha(QA/'v003-hand-direction/direction.json')},
    'actual_runtime_direction_check':{'path':'runs/qa/ro-swordsman-combo-r005/v003-hand-surface/axis-runtime-check.json','sha256':sha(QA/'v003-hand-surface/axis-runtime-check.json')},'previous_files_preserved':True})
review={'reviewer':'Independent batch_review; actual final front/side/back gray diagnostics, prototype reports and method source',
    'verdict':'NO_SHIP','verified':['Right wrist-bounded prototype59120tri,52bones,724tri local replacement and0nonmanifold; protected body UV/geometry unchanged.',
        'Individual axis sign corrected; actual Blender20-bone small-angle matrix checks pass.',
        '14 thumb port vertices receive continuous hand/thumb blend; failed forearm roll disabled.',
        'Final30 search rows recorded, reported accumulated130/160; 3 candidates satisfy limited deep-penetration sampling.'],
    'failures':['Selected754 samples have no detected >1mm deep penetration, but all fixed pad within2mm counts are0. Finger minimum gaps6.68/10.20/10.97/16.16mm and thumb6.50mm.',
        'Actual side/back images still show unformed grip and palm/thumb-root angular collapse.',
        'New face UV interpolation crosses original islands and pollutes glove appearance; source-guided production rebake not performed.',
        'Left prototype, equipment repair,3stressposes,300frame sequence,VFX and animated roundtrip not performed because right prototype gate fails.'],
    'classification':{'TEST_FAILURE':['Reversed individual axis method corrected; old result cannot isolate topology failure.','Nearest corner UV transfer insufficient across islands; unresolved appearance defect.'],
        'PRODUCT_FAILURE':['Current corrected candidate still fails actual grip and deformation.'],
        'UNVERIFIED_RISK':['Complete triangle intersection not checked; finite sample no-penetration is limited.','Whole character art/rig/function has no PASS.']},
    'stop_reason':'Third and final original assembly revision failed the local prototype gate. Stop_budget after recording; not API balance or authorization failure.',
    'prototype_expanded_to_left':False,'uv_rebake_performed':False,'full_animation_performed':False}
save(QA/'v003-final-review.json',review); save(QA/'quality-ledger-before-v003.json',ledger)
now=datetime.now(timezone.utc); wall_trial=(now-datetime.fromisoformat(start['started_utc'])).total_seconds(); phase_wall=(now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()
prior=sum(t['elapsed_seconds'] for t in ledger['trials']); unallocated=max(0,phase_wall-prior-wall_trial); accounted=wall_trial+unallocated
if wall_trial>=phase['budget']['trial_seconds'] or accounted>=phase['budget']['trial_seconds'] or phase_wall>=phase['budget']['total_seconds']: raise RuntimeError('Original budget exceeded, preserve failure for audit')
save(QA/'phase-accounting-final.json',{'phase_started_utc':phase['baseline_started_utc'],'stopped_utc':now.isoformat(),'original_budget':phase['budget'],'original_candidate_limit':3,
    'prior_recorded_seconds':prior,'v003_execution_seconds':wall_trial,'previous_intertrial_seconds_carried':unallocated,'v003_accounted_seconds':accounted,'total_phase_wall_seconds':phase_wall,
    'intertrial_interval':{'start':ledger['trials'][1]['ended_utc'],'end':ledger['trials'][2]['started_utc']},
    'explanation':'Final trial elapsed includes previously unassigned intertrial/precharge waiting time so compare totals equal original phase wall time. Old elapsed records and timestamps remain unchanged; no clock reset.',
    'used_revisions':3,'remaining_revisions':0,'new_paid_operations_in_v003':0,'stop':'stop_budget'})
paths=[QA/'v003-final-review.json',QA/'v003-hand-prototype/prototype.json',QA/'v003-hand-direction/direction.json',QA/'v003-hand-surface/surface.json',QA/'v003-hand-surface/axis-runtime-check.json',QA/'v002-axis-review-correction.json',QA/'search-count-reconciliation.json',QA/'phase-accounting-final.json']
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),'elapsed_seconds':accounted,'execution_seconds':wall_trial,'carried_intertrial_seconds':unallocated,
    'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
    'change':'Wrist-bounded right palm/digit cage and measured3joint fingers; corrected sign, thumb-port blending and bounded actual-surface search. No left expansion after failed prototype.',
    'failure_reason':'PRODUCT_FAILURE: corrected actual prototype still has palm/thumb-root folding and fixed pad gaps, not a formed grip. TEST_FAILURE: reversed axis corrected, UV transfer invalid across islands; all originals preserved. Third revision consumed; full animation held by prototype gate. No API or permission blocker.',
    'supporting_reports':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in paths]})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison=workbench.compare_quality(request,ledger); save(QA/'comparison-final.json',comparison)
if comparison['blockers'] or comparison['next_action']!='stop_budget' or comparison['candidate_trials_used']!=3 or comparison['quality_target_met']: raise RuntimeError(comparison)
print(json.dumps({'verdict':'NO_SHIP','next_action':comparison['next_action'],'candidate_trials_used':3,'quality_target_met':False,'phase_wall_seconds':phase_wall,'accounted_seconds':comparison['elapsed_seconds'],'paid_operations_v003':0}))
