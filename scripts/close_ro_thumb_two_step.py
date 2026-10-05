"""Close the observed second failed method; include gaps in phase accounting."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
import workbench
ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r007'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
def artifact(p):
    return {'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
ledger = read(QA/'quality-ledger.json'); start = read(QA/'v002-start.json')
report = read(QA/'v002-two-step/two-step.json'); clock = read(QA/'phase-start.json')
assert [t['id'] for t in ledger['trials']] == ['baseline', 'v001']
assert not report['source_gate'] and report['sequence_probes'] == 72
now = datetime.now(timezone.utc)
seconds = (now-datetime.fromisoformat(start['started_utc'])).total_seconds()
assert seconds < clock['budget']['trial_seconds']
snapshot = QA/'quality-ledger-before-v002.json'
with snapshot.open('xb') as f: f.write((QA/'quality-ledger.json').read_bytes())
gap = start['planning_gap_since_v001_seconds']
ledger['trials'][-1]['elapsed_seconds'] += gap
ledger['trials'][-1]['ended_utc'] = start['started_utc']
ledger['trials'][-1]['post_trial_planning_gap_seconds'] = gap
review = {
    'observed_utc': now.isoformat(), 'verdict': 'NO_SHIP', 'source_gate': False,
    'actual_second_step_probes': 72, 'maximum_second_step_probes': 160,
    'stop_reason': 'Eligible neighbors of both frozen seeds enumerated; no sequence passed all gates',
    'remaining_band_poles': report['final_bad'],
    'pole_wrong_destination': report['actual_geometry_check']['pole_wrong_destination'],
    'method_limit': 'Does not prove all topology edits impossible; only these two-step sequences were tested',
    'not_run': ['Rig', 'Posed skin', 'Whole character animation', 'VFX', 'Animated GLB'],
    'new_service_credits': 0, 'phase_clock_reset': False,
}
save(QA/'v002-review.json', review)
ledger['trials'].append({
    'id': 'v002', 'parent_id': 'baseline', 'status': 'failed',
    'started_utc': start['started_utc'], 'ended_utc': now.isoformat(), 'elapsed_seconds': seconds,
    'protocol_sha256': ledger['protocol_sha256'], 'reviewer': 'Coordinator actual Blender source readback',
    'hypothesis': start['hypothesis'], 'change': 'Bounded two-step edge rotations with frozen joint bands and cap margin',
    'failure_reason': 'PRODUCT_FAILURE: one primary-band pole remains and three new/moved poles fail distal cap margin; no binding',
    'supporting_reports': [artifact(QA/'v002-start.json'), artifact(QA/'v002-review.json'), artifact(QA/'v002-two-step/two-step.json')],
    'prototype_artifacts': [report['artifact']],
})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison = workbench.compare_quality(read(ROOT/'requests/ro-swordsman-combo-r007.json'), ledger, ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used'] == 2
save(QA/'comparison-v002.json',comparison)
save(QA/'v002-accounting.json',{
    'phase_wall_seconds_through_v002': (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
    'ledger_elapsed_seconds': comparison['elapsed_seconds'], 'planning_gaps_included': True,
    'v002_seconds': seconds, 'new_service_credits': 0, 'phase_clock_reset': False,
})
print(json.dumps({'v002':'failed','used':2,'next':comparison['next_action']}))
