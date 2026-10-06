"""Verify the archived r010 evidence, history and held Git state offline."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import workbench

QA = ROOT / 'runs/qa/ro-swordsman-combo-r010'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def artifacts(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            yield value
        for row in value.values():
            yield from artifacts(row)
    elif isinstance(value, list):
        for row in value:
            yield from artifacts(row)


request = read(ROOT / 'requests/ro-swordsman-combo-r010.json')
assert not workbench.validate_request(request)
clock = read(QA / 'phase-start.json')
ledger = read(QA / 'quality-ledger.json')
account = read(QA / 'phase-accounting-final.json')
comparison = workbench.compare_quality(request, ledger, ROOT)
assessment = workbench.assess(request, read(QA / 'evidence-final.json'), ROOT)
assert comparison == read(QA / 'comparison-final.json')
assert assessment == read(QA / 'assessment-final.json')
assert not comparison['blockers'] and comparison['candidate_trials_used'] == 4
assert comparison['next_action'] == 'stop_budget' and assessment['decision'] == 'not_ready'
assert not comparison['quality_target_met']
assert [t['id'] for t in ledger['trials']] == ['baseline', 'v001', 'v002', 'v003', 'v004']
assert all(t['status'] == 'failed' for t in ledger['trials'][1:])
assert ledger['trials'][-1]['local_numeric_and_export_status'] == 'passed'
assert ledger['trials'][-1]['local_functional_gate_status'] == 'not_satisfied_art'
assert abs(comparison['elapsed_seconds'] - account['phase_wall_seconds_at_close']) < 1e-3
assert len(clock['protected_history']) == 310
for item in clock['protected_history']:
    assert sha(ROOT / item['path']) == item['sha256']
checked = set()
json_paths = sorted(QA.rglob('*.json'))
for path in json_paths:
    for item in artifacts(read(path)):
        key = item['path'], item['sha256']
        if key in checked:
            continue
        target = (ROOT / item['path']).resolve()
        assert target.is_relative_to(ROOT.resolve()) and target.is_file(), key
        assert sha(target) == item['sha256'], (path, key)
        checked.add(key)
python_paths = sorted((ROOT / 'scripts').glob('*.py')) + sorted((ROOT / 'tests').glob('*.py'))
for path in python_paths:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
review = read(QA / 'v004-review.json')
assert review['local_numeric_and_export_subchecks'] == 'PASS'
assert not review['independent_gray_shape_accepted'] and not review['entire_local_functional_gate_passed']
fresh = read(QA / 'v004-fresh-glb-attempt3/result.json')
events = [json.loads(line) for line in (QA / 'v004-fresh-glb-attempt3/interval-events.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(events) == fresh['samples'] == 121
assert [r['frame'] for r in events] == [1 + i / 2 for i in range(121)]
assert sum(r['contact_required'] for r in events) == 61
for row in events:
    assert row['pass'] and row['self'] == row['sword'] == row['remaining_unknown'] == 0
    assert row['depth_m'] == 0
    assert max(row['hand_max_m'], row['weapon_max_m'], row['weapon_bone_follow_m']) <= 1e-6
    if row['contact_required']:
        assert set(row['contacts']) == {'finger1', 'finger2', 'finger3', 'finger4', 'thumb'}
        assert min(row['contacts'].values()) >= 3
assert sum(row['original_ray_unknown'] for row in events) == 1
assert sum(len(row['supplemental']) for row in events) == 1
weights = read(QA / 'v004-certified-animation/exact-weights-verification.json')
assert weights['artifact'] == fresh['subject']
assert weights['original_ids'] == 904 and weights['exported_vertices'] == 1106
assert weights['maximum_restored_L1'] == 0 and weights['changed_bytes'] == 1686
assert weights['all_other_bytes_unchanged'] and weights['single_animation_channels'] == 52
assert not read(QA / 'v004-fresh-glb-attempt2/result.json')['numeric_interval_pass']
assert not read(QA / 'v003-local-animation/result.json')['interval_numeric_pass']
index = read(ROOT / 'library/index.json')
entry = next(r for r in index['entries'] if r['id'] == 'ro-swordsman-combo-r010-v004')
assert workbench.search_library(index, 'r010-v004') == [entry]
assert entry['status'] == 'needs_revision' and entry['acceptance']['delivery'] == 'not_delivered'
assert fresh['subject']['path'] in entry['files']
for file in entry['files'] + [entry['qa_report'], entry['provenance']['record']]:
    assert (ROOT / file).is_file()
tests = (QA / 'unit-tests-final.log').read_text(encoding='utf-8')
assert 'Ran 131 tests' in tests and tests.rstrip().endswith('OK')
pipeline = read(QA / 'pipeline-validate-final.log')
assert pipeline['status'] == 'valid' and pipeline['assets'] == 39  # Legacy inventory, not library-entry count.
main = Path('C:/Repos/mmo-asset-pipeline')
heads = {'worktree': git(ROOT, 'rev-parse', 'HEAD'), 'main': git(main, 'rev-parse', 'HEAD')}
assert heads == {'worktree': 'c990639962b7ce85eb6beb631057aa4d76a3e86d',
                 'main': 'e077e22ba57447031b7cc89e3d37bd9cef47daf4'}
assert not git(ROOT, 'diff', '--cached', '--name-only') and not git(main, 'diff', '--cached', '--name-only')
git(ROOT, 'diff', '--check')
attributes = git(ROOT, 'check-attr', 'filter', '--',
                 fresh['subject']['path'], 'runs/qa/ro-swordsman-combo-r010/v003-local-animation/expected-animation-points.npz')
assert all(line.endswith(': filter: lfs') for line in attributes.splitlines())
report = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'verified_archived_local_numeric_pass_full_NO_SHIP',
    'request_schema_valid': True, 'candidate_count': 4, 'comparison': 'stop_budget', 'assessment': 'not_ready',
    'local_numeric_and_export_subchecks': 'PASS', 'entire_local_functional_gate_passed': False,
    'independent_gray_shape_accepted': False, 'whole_quality_scores_unchanged': True,
    'artifact_references_checked': len(checked), 'QA_json_parsed': len(json_paths),
    'python_sources_syntax_checked': len(python_paths), 'protected_history_files': 310,
    'protected_history_unchanged': True, 'fresh_GLb_samples': 121, 'required_grasp_samples': 61,
    'fresh_hand_max_m': fresh['maximum_hand_point_difference_m'],
    'fresh_hand_RMS_m': fresh['hand_RMS_difference_m'], 'frozen_point_tolerance_m': 1e-6,
    'unit_tests': 131, 'unit_tests_log_sha256': sha(QA / 'unit-tests-final.log'),
    'legacy_inventory_assets_schema_valid': 39, 'pipeline_log_sha256': sha(QA / 'pipeline-validate-final.log'),
    'library_entry': entry['id'], 'library_delivery': 'not_delivered',
    'phase_wall_seconds_at_close': account['phase_wall_seconds_at_close'],
    'postclose_documentation_verification_seconds': (datetime.now(timezone.utc) - datetime.fromisoformat(account['phase_closed_utc'])).total_seconds(),
    'preclock_preparation_unmeasured': True, 'git_heads': heads, 'staged_paths': [],
    'new_API_submissions': 0, 'new_service_credits': 0, 'repo_external_writes': 'none',
    'LFS_attributes_configured': True, 'LFS_stage_remote_clone_not_run': True,
    'target_engine_and_full300_not_verified': True,
    'document_artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in [
        ROOT / 'library/index.json', ROOT / 'docs/art-quality-loop.md', ROOT / '.gitattributes',
        ROOT / 'assets/processed/ro-swordsman-combo-r010/README.md', QA / 'README.md',
        QA / 'independent-final-review.md']],
}
with (QA / 'integrity-final.json').open('x', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({k: report[k] for k in ['status', 'artifact_references_checked', 'protected_history_files',
                 'fresh_GLb_samples', 'unit_tests', 'comparison', 'assessment']}))
