"""Prospectively register the last bounded root-skin hypothesis."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
ledger=read(QA/'quality-ledger.json');clock=read(QA/'phase-start.json')
result=workbench.compare_quality(read(ROOT/'requests/ro-swordsman-combo-r007.json'),ledger,ROOT)
assert result['candidate_trials_used']==3 and not result['blockers'] and result['next_action']=='revise_current_best'
now=datetime.now(timezone.utc)
source=read(QA/'v003-skin-diagnostic/skin.json')['artifact'];masks=QA/'v003-skin-diagnostic/frozen-masks-and-weights.json'
value={'id':'v004','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'planning_gap_since_v003_seconds':(now-datetime.fromisoformat(ledger['trials'][-1]['ended_utc'])).total_seconds(),
    'budget':clock['budget'],'previous_candidates_used':3,'candidate_limit':4,'source':source,
    'frozen_masks':{'path':masks.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(masks.read_bytes()).hexdigest()},
    'hypothesis':'Bounded mesh-neighbor harmonic hand/thumb-root transition removes observed binary edge jumps while keeping joints, distal cap and fourfinger weights fixed',
    'maximum_weight_variants':3,'iterations_per_variant':100,'relaxation':.7,
    'protected':'All original geometry/UV, all fixed bone positions, fourfinger weights and distal thumb/cap weights',
    'stop':'Visible thenar/web/root collapse or self-cross; no grip expansion on small-motion failure',
    'known_material_gate':'16mixedUVfaces unchanged; solve only after functional pass',
    'new_paid_generation':False,'phase_clock_reset':False}
with (QA/'v004-start.json').open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'v004':now.isoformat(),'remaining_candidates_after_this':0}))
