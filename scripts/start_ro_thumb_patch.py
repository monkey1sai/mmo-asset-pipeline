"""Prospectively freeze the localized thumb patch method and its boundaries."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
ledger=read(QA/'quality-ledger.json'); clock=read(QA/'phase-start.json')
result=workbench.compare_quality(read(ROOT/'requests/ro-swordsman-combo-r007.json'),ledger,ROOT)
assert result['candidate_trials_used']==2 and not result['blockers']
assert result['next_action']=='revise_current_best'
now=datetime.now(timezone.utc)
assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
source=read(QA/'v001-thumb-flow/flow.json')['artifact']
probe=QA/'v001-source-preparation/joint-and-pole-probe.json'
value={'id':'v003','started_utc':now.isoformat(),'phase_started_utc':clock['baseline_started_utc'],
    'planning_gap_since_v002_seconds':(now-datetime.fromisoformat(ledger['trials'][-1]['ended_utc'])).total_seconds(),
    'budget':clock['budget'],'previous_candidates_used':2,'candidate_limit':4,'source':source,
    'joint_probe':{'path':probe.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(probe.read_bytes()).hexdigest()},
    'hypothesis':'A measured thumb IP-to-tip quad patch can place exceptional vertices in the distal cap while retaining the existing palm, four fingers and proximal thumb boundary',
    'protected':'Every retained original vertex position, face corner UV and material; frozen joint centers/bands unchanged',
    'maximum_boundary_probes':40,'maximum_patch_variants':12,'surface_max_error_m':.0015,'cap_margin_m':.003,
    'patch_surface_method':'Project new ring points onto the archived local source surface; preserve boundary exactly; actual loop triangles and bidirectional sample checks',
    'UV_method':'Transfer each changed corner from a single nearest original triangle with barycentric interpolation; retain each protected original face corner exactly',
    'new_paid_generation':False,'phase_clock_reset':False,
    'stop_before_rig':'No ordered patch boundary, any primary-band pole or incorrect pole destination, crossing/normal/UV/surface failure'}
with (QA/'v003-start.json').open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'started':now.isoformat(),'id':'v003','credits':0}))
