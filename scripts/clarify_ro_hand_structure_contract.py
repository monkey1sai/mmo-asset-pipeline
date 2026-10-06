"""Preserve initial contract; clarify current budget and whole baked interval before candidates."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
old=QA/'hand-gate-contract.json'; value=json.loads(old.read_text(encoding='utf-8'))
value['status']='frozen_v2_before_first_source_candidate'
budget=value['budget']
budget['historical_r006_initial_scout']={k:budget.pop(k) for k in ['measured_before','planning_removed_right','planning_removed_left']}
budget['historical_r006_initial_scout']['not_current_authoritative_budget']=True
budget['current_authoritative_budget']={'baseline_whole_measured_triangles':57039,'right_glove_plus_tube_measured':2742,
    'left_hand_removal_historical_estimate':537,'left_removal_not_executed':True,'seam_planning_reserve':256,'both_hands_planning_remainder':5984,
    'equation':'60000 - (57039 - 2742 - estimated537 + reserve256) =5984; remeasure actual left removal and both finished hands before assembly acceptance'}
value['actual_baked_interval']={
    'required':'For any local grip animation, evaluate every actual baked frame with source vertex/triangle identity, collision/deformation and visible volume; known five-pose/endpoint success alone never passes the interval.',
    'contact_requirement':'Five frozen semantic pads required in declared holding interval; open/approach intervals need not touch, but must not penetrate/cross the weapon.',
    'local_default':'61frames/60fps from open to grip; holding frame61 only in the existing failed diagnostic, not a declaration of full-use success.',
    'between_frame_diagnostics':'Half-frame diagnostic samples on the short prototype; fast full-skill changes need additional intermediate samples and visual inspection.',
    'limits':'Discrete baked and half-frame samples do not prove mathematically continuous collision freedom; coplanar/tangential/adjacent-surface exclusions remain disclosed.'}
value['source_design']['image_length_observation']='Two 2D references show extra proximal forearm length relative to80/185; treat as source margin to cut in a measured forearm zone. Image proportions are not exact generated dimensions.'
new=QA/'hand-gate-contract-v2.json'
with new.open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n')
record={'observed_utc':datetime.now(timezone.utc).isoformat(),'reason':'Independent preparation reviewer requested removal of ambiguous old budget fields and explicit whole-baked interval checking',
    'original':{'path':old.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(old.read_bytes()).hexdigest()},
    'current':{'path':new.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(new.read_bytes()).hexdigest()},
    'first_candidate_started':False,'original_request_quality_targets_changed':False,'API_prepared_plan_changed':False,
    'history_preserved':True,'old_r006_not_reopened':True,'authority':'Scope clarification before any new source generation; no additional paid authority supplied by reviewer'}
with (QA/'contract-clarification.json').open('x',encoding='utf-8') as f: json.dump(record,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps({'local_contract':'v2','candidate_count':0,'original_preserved':True}))
