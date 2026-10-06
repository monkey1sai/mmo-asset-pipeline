"""Close r010: keep local technical success separate from full-quality failure."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import workbench

QA = ROOT / 'runs/qa/ro-swordsman-combo-r010'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
artifact = lambda p: {'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


clock = read(QA / 'phase-start.json')
request = read(ROOT / 'requests/ro-swordsman-combo-r010.json')
ledger = read(QA / 'quality-ledger.json')
assert len(ledger['trials']) == 4
start = read(QA / 'v004-start.json')
static = read(QA / 'v003-index-pulp/result.json')
interval = read(QA / 'v004-certified-animation/result.json')
fresh = read(QA / 'v004-fresh-glb-attempt3/result.json')
weights = read(QA / 'v004-certified-animation/exact-weights-verification.json')
assert static['numeric_gate'] and interval['interval_numeric_pass'] and fresh['numeric_interval_pass']
assert interval['samples'] == fresh['samples'] == 121
assert weights['maximum_restored_L1'] == 0 and weights['all_other_bytes_unchanged']
assert fresh['subject'] == weights['artifact']
contacts = {n: r['within_2mm'] for n, r in static['contact']['pad_contacts'].items()}
assert list(contacts.values()) == [3, 3, 3, 3, 3]
for item in clock['protected_history']:
    assert artifact(ROOT / item['path']) == item
review_path = QA / 'independent-final-review.md'
assert review_path.is_file()  # Actual returned reviewer report, not a routing observation.
now = datetime.now(timezone.utc)
review = {
    'observed_utc': now.isoformat(), 'whole_verdict': 'NO_SHIP', 'local_numeric_and_export_subchecks': 'PASS',
    'independent_gray_shape_accepted': False, 'entire_local_functional_gate_passed': False,
    'classification': 'Full-quality scope incomplete: UV/material, grasp art judgment, left hand, assembly,300frames,VFX. Local frozen numerical checks pass; no whole scores increased.',
    'contacts': contacts, 'self': static['self']['transverse_pairs'],
    'sword': static['contact']['transverse_crossings_count'],
    'sample_penetration_m': static['contact']['maximum_penetration_m'],
    'static_edge_ratio': [static['self']['minimum_edge_ratio'], static['self']['maximum_edge_stretch']],
    'BLEND_and_freshGLB_samples_each': 121, 'original_unknown_samples': 1,
    'supplemental_outside_samples': 1, 'remaining_unknown_samples': 0,
    'fresh_hand_max_difference_m': fresh['maximum_hand_point_difference_m'],
    'fresh_hand_RMS_difference_m': fresh['hand_RMS_difference_m'],
    'fresh_weapon_point_difference_m': fresh['maximum_weapon_point_difference_m'],
    'fresh_actual_bone_follow_error_m': fresh['maximum_actual_bone_follow_error_m'],
    'original_point_tolerance_m': 1e-6, 'all_original_pad_masks_preserved': True,
    'all_weights_exact_frozen_float32': True, 'material_crossUV_faces_unresolved': 16,
    'finite_time_surface_samples_not_continuous_volume_proof': True,
    'independent_review': artifact(review_path), 'whole_scores_changed': False,
    'new_API_submissions': 0, 'new_credits': 0, 'no_fifth_candidate': True,
}
save(QA / 'v004-review.json', review)
ledger['trials'].append({
    'id': 'v004', 'parent_id': 'baseline', 'status': 'failed',
    'local_numeric_and_export_status': 'passed', 'local_functional_gate_status': 'not_satisfied_art',
    'full_quality_status': 'not_satisfied',
    'started_utc': start['started_utc'], 'ended_utc': now.isoformat(),
    'elapsed_seconds': (now - datetime.fromisoformat(start['started_utc'])).total_seconds(),
    'protocol_sha256': clock['protocol_sha256'],
    'reviewer': 'Coordinator fresh actual BLEND/GLB interval plus independent Astra/high report',
    'hypothesis': start['hypothesis'], 'change': start['change'],
    'failure_reason': review['classification'],
    'supporting_reports': [artifact(QA / name) for name in [
        'v004-review.json', 'v004-certified-animation/result.json',
        'v004-certified-animation/exact-weights-verification.json',
        'v004-fresh-glb-attempt3/result.json', 'independent-final-review.md']],
    'prototype_artifacts': [interval['artifact'], fresh['subject']],
})
save(QA / 'quality-ledger-before-close.json', read(QA / 'quality-ledger.json'))
comparison = workbench.compare_quality(request, ledger, ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used'] == 4
assert comparison['next_action'] == 'stop_budget' and not comparison['quality_target_met']
(QA / 'quality-ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
save(QA / 'comparison-final.json', comparison)
evidence = copy.deepcopy(ledger['trials'][0]['evidence'])
evidence['quality_ledger'] = artifact(QA / 'quality-ledger.json')
evidence['scope_note'] = 'Original full failed baseline retained for original full-spec assessment. Locally passing hand prototype does not replace a full evaluated master.'
save(QA / 'evidence-final.json', evidence)
assessment = workbench.assess(request, evidence, ROOT)
assert assessment['decision'] == 'not_ready'
save(QA / 'assessment-final.json', assessment)
save(QA / 'phase-accounting-final.json', {
    'observed_utc': now.isoformat(), 'id': request['id'],
    'phase_started_utc': clock['baseline_started_utc'], 'phase_closed_utc': now.isoformat(),
    'phase_wall_seconds_at_close': (now - datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
    'clock_source': clock['clock_source'], 'preclock_preparation_unmeasured': True,
    'baseline_and_preparation_seconds': ledger['trials'][0]['elapsed_seconds'],
    'candidate_seconds': [{'id': t['id'], 'seconds': t['elapsed_seconds']} for t in ledger['trials'][1:]],
    'candidate_used': 4, 'candidate_limit': 4, 'old310historyfiles_unchanged': True,
    'old_phase_reopened': False, 'quality_targets_lowered': False,
    'BLEND_and_finalGLB_121_samples_each': True,
    'failed_export_and_fresh_attempts_preserved': True,
    'new_API_submissions': 0, 'new_service_credits': 0, 'API_balance_query_this_phase': False,
    'repo_external_writes': 'none', 'stage_commit_push': 'held_by_user',
    'background': 'No API/Blender jobs running at close; documentation/final verification recorded separately.',
})
print(json.dumps({'local_technical': 'PASS', 'full_quality': 'NO_SHIP',
                  'comparison': comparison['next_action'], 'assessment': assessment['decision'],
                  'candidates': 4, 'new_credits': 0}))
