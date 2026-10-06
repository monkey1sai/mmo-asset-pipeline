"""Register separately authorized r010 without reopening older phases."""
from datetime import datetime, timezone
from pathlib import Path
import copy, hashlib, json, subprocess
import workbench

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'runs/qa/ro-swordsman-combo-r009'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r010'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))


def artifact(p):
    return {'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def save(p, value):
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


assert not QA.exists()
old = read(ROOT / 'requests/ro-swordsman-combo-r009.json')
assert read(OLD / 'comparison-final.json')['next_action'] == 'stop_budget'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == 'c990639962b7ce85eb6beb631057aa4d76a3e86d'
request = copy.deepcopy(old)
request.update(id='ro-swordsman-combo-r010', title='RO劍士：作者握姿設計與受限姿勢修正形變',
               brief='方向1：開始設計握姿與必要形變修正的新階段，保留原驗收與歷史，commit／push 繼續等我驗證。')
request['production'].update(route='modify', max_revisions=4,
    reason='Artist-authored whole phalange grasp fields after pad/normal audit; localized pose corrective with full surface and interval checks. Preserve original gates, sources and old budgets.')
request['phase_history'] = {
    'previous_request': artifact(ROOT / 'requests/ro-swordsman-combo-r009.json'),
    'previous_ledger': artifact(OLD / 'quality-ledger.json'),
    'previous_result': artifact(OLD / 'comparison-final.json'),
    'previous_accounting': artifact(OLD / 'phase-accounting-final.json'),
    'previous_revisions': 4, 'previous_phase_reopened': False,
    'authority': request['brief'], 'quality_targets_lowered': False,
    'new_method': 'Audit original pad semantics/normals; author coherent phalange grasp and localized smooth corrective shapes, not independent contact-vertex snapping.'}
assert request['spec'] == old['spec'] and request['quality'] == old['quality']
assert not workbench.validate_request(request)
QA.mkdir(parents=True)
save(ROOT / 'requests/ro-swordsman-combo-r010.json', request)
paths = set()
for phase in ['ro-swordsman-combo-r008', 'ro-swordsman-combo-r009']:
    paths.add(ROOT / 'requests' / (phase + '.json'))
    for folder in [ROOT / 'runs/qa' / phase, ROOT / 'assets/processed' / phase]:
        paths.update(p for p in folder.rglob('*') if p.is_file())
source = read(OLD / 'v004-collision-constraints/result.json')['artifact']
assert artifact(ROOT / source['path']) == source
save(QA / 'phase-start.json', {
    'id': request['id'], 'baseline_started_utc': '2026-10-04T05:08:12+00:00',
    'clock_source': 'First UTC observed this turn; prior preparatory reads unmeasured, not backfilled.',
    'earlier_preclock_preparation_seconds': None, 'registered_utc': datetime.now(timezone.utc).isoformat(),
    'request_sha256': workbench.request_sha256(request), 'protocol_sha256': workbench.quality_sha256(request),
    'max_revisions': 4, 'budget': request['quality']['budget'], 'local_source': source,
    'whole_source': read(OLD / 'phase-start.json')['whole_source'],
    'protected_history': [artifact(p) for p in sorted(paths)],
    'repo_external_writes': 'none', 'new_paid_submissions': 0, 'stage_commit_push': 'held_by_user',
    'execution': 'Default sandbox provisioning failed; individually reviewed exact scoped commands, no security/config changes.'})
save(QA / 'authorization.json', {
    'human': request['brief'], 'allowed': 'New local phase: designed grasp and necessary localized corrective deformation, required readbacks and independent review.',
    'preserve': 'Old budgets, clocks, source, API cost/history and exact frozen contact/shape/art gates.',
    'API_scope': 'Existing authority persists, no new generation planned without evidence for substantive rebuild.',
    'repo_external_writes': 'none', 'stage_commit_push': 'held_by_user'})
print(json.dumps({'phase': request['id'], 'protected_files': len(paths), 'paid': 0}))
