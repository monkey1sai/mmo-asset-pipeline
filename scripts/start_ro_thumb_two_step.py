"""Prospectively register the distinct second method without resetting history."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
request=read(ROOT/'requests/ro-swordsman-combo-r007.json'); ledger=read(QA/'quality-ledger.json')
comparison=workbench.compare_quality(request,ledger,ROOT)
assert comparison['candidate_trials_used']==1 and not comparison['blockers']
assert comparison['next_action']=='revise_current_best'
clock=read(QA/'phase-start.json'); flow=read(QA/'v001-thumb-flow/flow.json'); now=datetime.now(timezone.utc)
assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
start={'id':'v002','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'planning_gap_since_v001_seconds':(now-datetime.fromisoformat(ledger['trials'][-1]['ended_utc'])).total_seconds(),
    'budget':clock['budget'],'previous_candidates_used':1,'candidate_limit':4,
    'source':flow['artifact'],'source_reuse_scope':'Only failed-v001 local exterior/quad edits as guide; baseline remains current-best parent',
    'joint_probe':{'path':'runs/qa/ro-swordsman-combo-r007/v001-source-preparation/joint-and-pole-probe.json',
        'sha256':hashlib.sha256((QA/'v001-source-preparation/joint-and-pole-probe.json').read_bytes()).hexdigest()},
    'hypothesis':'Two independently observed plateau states may permit a legal improving second edge rotation while frozen joint bands stay unchanged',
    'maximum_second_step_probes':160,'maximum_sequence_length':2,
    'seeds':[{'edge_vertices':[48,49],'ccw':False},{'edge_vertices':[49,50],'ccw':True}],
    'surface_max_error_m':.0015,'cap_margin_m':.003,'inverse_and_duplicate_topology_rejected':True,
    'old_v001_probes_preserved':160,'phase_clock_reset':False,'new_paid_generation':False,
    'stop_before_rig':'Any primary-band pole, changed triangle/self-cross/UV/surface failure'}
with (QA/'v002-start.json').open('x',encoding='utf-8') as f:json.dump(start,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'v002_started':now.isoformat(),'prior_candidates':1,'new_credits':0}))
