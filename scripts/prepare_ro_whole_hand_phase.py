"""Register the explicitly authorized r009 phase without reopening r008."""
from datetime import datetime, timezone
from pathlib import Path
import copy, hashlib, json, subprocess
import workbench

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'runs/qa/ro-swordsman-combo-r008'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r009'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))


def artifact(p):
    return {'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


assert not QA.exists() and not (ROOT / 'requests/ro-swordsman-combo-r009.json').exists()
old = read(ROOT / 'requests/ro-swordsman-combo-r008.json')
comparison = workbench.compare_quality(old, read(OLD / 'quality-ledger.json'), ROOT)
assert comparison['candidate_trials_used'] == 4 and comparison['next_action'] == 'stop_budget'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == 'c990639962b7ce85eb6beb631057aa4d76a3e86d'
request = copy.deepcopy(old)
request.update(id='ro-swordsman-combo-r009', title='RO劍士：全手掌根形變與實際握持校準',
               brief='方向1：開始全手校準的新階段，保留歷史，commit／push 繼續等我驗證。')
request['production']['route'] = 'modify'
request['production']['max_revisions'] = 4
request['phase_history'] = {
    'previous_request': artifact(ROOT / 'requests/ro-swordsman-combo-r008.json'),
    'previous_ledger': artifact(OLD / 'quality-ledger.json'),
    'previous_result': artifact(OLD / 'comparison-final.json'),
    'previous_accounting': artifact(OLD / 'phase-accounting-final.json'),
    'previous_revisions': 4, 'previous_phase_reopened': False,
    'authority': request['brief'], 'quality_targets_lowered': False,
    'new_method': 'Diagnose root compression and reachability; necessary fourfinger weights/bones/limitedmesh may change; preserve reusable thumb benefit and actual sword.',
}
assert not workbench.validate_request(request)
QA.mkdir(parents=True)
save(ROOT / 'requests/ro-swordsman-combo-r009.json', request)
preserved = [ROOT / 'requests/ro-swordsman-combo-r008.json'] + sorted(p for p in OLD.rglob('*') if p.is_file())
preserved += sorted(p for p in (ROOT / 'assets/processed/ro-swordsman-combo-r008').rglob('*') if p.is_file())
source = read(OLD / 'v004-contact-solver/result.json')['artifact']
assert artifact(ROOT / source['path']) == source
save(QA / 'phase-start.json', {
    'id': request['id'], 'baseline_started_utc': '2026-10-04T01:28:58+00:00',
    'clock_source': 'First observed UTC of current turn; preparatory reads before observation were not precisely timed and are explicitly unmeasured.',
    'earlier_preclock_preparation_seconds': None, 'registered_utc': datetime.now(timezone.utc).isoformat(),
    'request_sha256': workbench.request_sha256(request), 'protocol_sha256': workbench.quality_sha256(request),
    'max_revisions': 4, 'budget': request['quality']['budget'], 'local_source': source,
    'whole_source': read(OLD / 'phase-start.json')['baseline_source'],
    'protected_history': [artifact(p) for p in preserved],
    'repo_external_writes': 'none', 'new_paid_submissions': 0, 'stage_commit_push': 'held_by_user',
    'effective_runtime': {'sandbox_mode': 'workspace-write', 'approvals_reviewer': 'auto_review',
                          'default_exec_probe': 'ENVIRONMENT_FAILURE: sandbox provisioning failed',
                          'execution': 'individually reviewed exact scoped host commands; no permission changes',
                          'saved_approval_policy': 'on-request', 'saved_hooks': False},
})
save(QA / 'authorization.json', {
    'human': request['brief'], 'allowed': 'Repository local new phase, necessary fourfinger weights/joints/limitedmesh calibration and Blender readbacks.',
    'preserve': 'All r008 history, sources, costs, old clocks and quality/spec; no automatic reopening or fifth candidate.',
    'API_scope': 'Existing demand-driven generation authority persists; first stage uses existing source and no new submission.',
    'repo_external_files': 'No new file authorized or needed this phase.',
    'stage_commit_push': 'held_by_user', 'quality_spec_identical_to_r008': request['spec'] == old['spec'] and request['quality'] == old['quality'],
})
print(json.dumps({'registered': request['id'], 'protected_files': len(preserved), 'new_paid_submissions': 0}))
