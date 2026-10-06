"""Read-only validation of the closed r008 phase; write a separate evidence report."""
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import json
import subprocess

import workbench

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r008'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def artifacts(value):
    if isinstance(value, dict):
        if set(('path', 'sha256')).issubset(value):
            yield value
        for item in value.values():
            yield from artifacts(item)
    elif isinstance(value, list):
        for item in value:
            yield from artifacts(item)


request = read(ROOT / 'requests/ro-swordsman-combo-r008.json')
ledger = read(QA / 'quality-ledger.json')
clock = read(QA / 'phase-start.json')
comparison = workbench.compare_quality(request, ledger, ROOT)
assessment = workbench.assess(request, read(QA / 'evidence-final.json'), ROOT)
assert not comparison['blockers']
assert comparison['candidate_trials_used'] == 4
assert comparison['next_action'] == 'stop_budget'
assert not comparison['quality_target_met']
assert assessment['decision'] == 'not_ready'
assert [row['id'] for row in ledger['trials']] == ['baseline', 'v001', 'v002', 'v003', 'v004']
assert all(row['status'] == 'failed' for row in ledger['trials'][1:])

hash_failures = []
checked = set()
json_files = sorted(QA.rglob('*.json'))
for path in json_files:
    for item in artifacts(read(path)):
        key = (item['path'], item['sha256'])
        if key in checked:
            continue
        target = (ROOT / item['path']).resolve()
        assert target.is_relative_to(ROOT.resolve()), item['path']
        checked.add(key)
        if not target.is_file() or digest(target) != item['sha256']:
            hash_failures.append({'record': path.relative_to(ROOT).as_posix(), **item})
assert not hash_failures, hash_failures
for item in clock['protected_history']:
    assert digest(ROOT / item['path']) == item['sha256']

syntax_paths = sorted((ROOT / 'scripts').glob('*.py')) + sorted((ROOT / 'tests').glob('*.py'))
for path in syntax_paths:
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))

library = read(ROOT / 'library/index.json')
entry = next(item for item in library['entries'] if item['id'] == 'ro-swordsman-combo-r008-v004')
assert entry['status'] == 'needs_revision'
assert entry['acceptance']['delivery'] == 'not_delivered'
for item in entry['files'] + [entry['qa_report'], entry['provenance']['record']]:
    assert (ROOT / item).is_file(), item

result = read(QA / 'v004-contact-solver/result.json')
fresh = read(QA / 'fresh-saved-verification.json')
events = [json.loads(line) for line in (QA / 'v004-contact-solver/evaluations.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(events) == result['actual_evaluations'] == 383
assert result['maximum_evaluations'] == 480
assert result['stop'] == 'fixedschedule_completed'
assert [event['index'] for event in events] == list(range(383))
assert fresh['source_file_unchanged']
assert fresh['geometry_faces_UV_source_attributes_exact'] and fresh['weights_exact']
assert fresh['sixteen_original_bone_heads_tails_exact'] and fresh['weapon_originaltriangles_unscaled']
assert not fresh['static_function_gate'] and not result['static_numeric_gate']
assert fresh['self']['transverse_pairs'] == fresh['contact']['transverse_crossings_count'] == 0
contacts = {name: row['within_2mm'] for name, row in fresh['contact']['pad_contacts'].items()}
assert contacts == {'finger1': 3, 'finger2': 1, 'finger3': 3, 'finger4': 0, 'thumb': 4}

original = result['final_self']
metric_deltas = {name: abs(fresh['self'][name] - original[name]) for name in
                 ('maximum_edge_stretch', 'minimum_edge_ratio', 'maximum_absolute_edge_change_m')}
matrix_delta = max(abs(x - y) for name, matrix in original['actual_basis'].items()
                   for row1, row2 in zip(matrix, fresh['self']['actual_basis'][name])
                   for x, y in zip(row1, row2))
account = read(QA / 'phase-accounting-final.json')
assert account['r008_paid_submissions'] == account['r008_new_service_credits'] == 0
heads = {
    'worktree': git(ROOT, 'rev-parse', 'HEAD'),
    'main': git(Path('C:/Repos/mmo-asset-pipeline'), 'rev-parse', 'HEAD'),
}
assert heads == {'worktree': 'c990639962b7ce85eb6beb631057aa4d76a3e86d',
                 'main': 'e077e22ba57447031b7cc89e3d37bd9cef47daf4'}
assert not git(ROOT, 'diff', '--cached', '--name-only')
assert not git(Path('C:/Repos/mmo-asset-pipeline'), 'diff', '--cached', '--name-only')
git(ROOT, 'diff', '--check')

report = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'closed r008 local phase; no candidate, API, generation or Git mutation',
    'status': 'verified_closed_NO_SHIP',
    'comparison': {'candidate_trials_used': 4, 'next_action': 'stop_budget', 'quality_target_met': False},
    'assessment_decision': 'not_ready',
    'artifact_references_checked': len(checked), 'hash_failures': hash_failures,
    'qa_json_parsed': len(json_files), 'python_sources_syntax_checked': len(syntax_paths),
    'protected_history_unchanged': clock['protected_history'],
    'library_entry': entry['id'], 'library_entry_delivery': entry['acceptance']['delivery'],
    'actual_evaluations': 383, 'fixed_schedule_stop': result['stop'],
    'fresh_function_failure_reproduced': True, 'pad_contacts': contacts,
    'fresh_posed_points_bit_identical': fresh['point_fingerprint_equal'],
    'fresh_vs_original_actual_basis_max_component_difference': matrix_delta,
    'fresh_vs_original_reported_metric_differences': metric_deltas,
    'posed_points_limit': 'No archived raw original posed point array. Unequal exact fingerprints do not establish bit-identical posed geometry; only recorded tested failure outcomes reproduce.',
    'phase_wall_seconds_at_close': account['phase_wall_seconds_at_close'],
    'postclose_documentation_verification_wall_seconds': (datetime.now(timezone.utc) - datetime.fromisoformat(account['phase_closed_utc'])).total_seconds(),
    'r008_paid_submissions': 0, 'r008_new_service_credits': 0,
    'git_heads': heads, 'staged_paths': [], 'stage_commit_push': 'held_by_user',
    'unit_test_evidence': {'path': 'runs/qa/ro-swordsman-combo-r008/unit-tests.log',
                           'sha256': digest(QA / 'unit-tests.log'), 'tests': 119,
                           'note': 'Earlier completed test log, not rerun by this verifier.'},
    'pipeline_schema': {'assets': 39, 'status': 'valid',
                        'note': 'Re-run after library/docs archive; freshness/runtime excluded.'},
    'files': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)} for path in
              (ROOT / 'library/index.json', ROOT / 'docs/art-quality-loop.md',
               ROOT / 'assets/processed/ro-swordsman-combo-r008/README.md', QA / 'README.md')],
}
with (QA / 'final-verification.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({name: report[name] for name in ('status', 'artifact_references_checked',
                 'qa_json_parsed', 'python_sources_syntax_checked', 'actual_evaluations',
                 'fresh_posed_points_bit_identical', 'fresh_vs_original_actual_basis_max_component_difference',
                 'fresh_vs_original_reported_metric_differences', 'assessment_decision')}))
