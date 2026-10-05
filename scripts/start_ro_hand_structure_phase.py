"""Register the newly authorized method and prospective preparation clock."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r007'
assert not QA.exists(), 'Preserve any existing phase'
previous = ROOT / 'runs/qa/ro-swordsman-combo-r006'
comparison = json.loads((previous / 'comparison-final.json').read_text(encoding='utf-8'))
assert comparison['candidate_trials_used'] == 8 and comparison['next_action'] == 'stop_budget'
source = json.loads((previous / 'final-review.json').read_text(encoding='utf-8'))['prototype_artifacts'][0]
assert hashlib.sha256((ROOT / source['path']).read_bytes()).hexdigest() == source['sha256']
QA.mkdir(parents=True)
record = {
    'planning_started_utc': datetime.now(timezone.utc).isoformat(),
    'user_authority': '同意 — continue the proposed new palm/thumb/wrist and armor fitting method; existing demand-driven API credits remain authorized; commit/push remain held',
    'phase': 'r007', 'previous_phase_reopened': False,
    'previous_comparison': {'path': (previous / 'comparison-final.json').relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256((previous / 'comparison-final.json').read_bytes()).hexdigest()},
    'baseline_source': source,
    'new_method': 'Fitted worn glove outer skin with anatomical thenar/opposition and measured short forearm; topology/anatomy validation before rigging; rigid armor/internal core volume independent from wrist skin',
    'architecture_review': 'hand_phase_review Astra/high, read-only, new method accepted for preparation; no source or asset PASS',
    'max_candidate_revisions': 4, 'trial_seconds': 21600, 'total_seconds': 172800,
    'budget_is_not_API_credit_limit': True,
    'original_targets': '60000 whole character+sword triangles;2K; editable rig;300frames/60fps continuous skills; independent VFX;BLEND/GLB',
    'prior_history': json.loads((previous / 'phase-accounting-final.json').read_text(encoding='utf-8')),
    'repo_external_new_state_file': 'Exact-file authority still required after concrete design/plan; do not reuse or overwrite old task records',
    'status': 'preparing_new_method_not_submitted', 'commit_push': 'held by user',
}
with (QA / 'preparation-start.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'registered': 'r007', 'new_method': True, 'previous_closed': True, 'submitted': False}))
