"""Close v001 failure for complete-grip scope; register different coupled solver."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
import hashlib
QA=ROOT/'runs/qa/ro-swordsman-combo-r009'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r009.json');ledger=read(QA/'quality-ledger.json')
assert len(ledger['trials'])==1
start=read(QA/'v001-start.json');result=read(QA/'v001-vectors/result.json');now=datetime.now(timezone.utc)
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: static grip remains missing ring/indexcontact',
 'local_improvement':result['fixed_problem_edges'],'same_grip_contacts':{n:r['within_2mm'] for n,r in result['same_grip_contact']['pad_contacts'].items()},
 'fixed_condition_comparison':True,'self':result['same_grip_self']['transverse_pairs'],'sword':result['same_grip_contact']['transverse_crossings_count'],
 'min_edge_ratio':result['same_grip_self']['minimum_edge_ratio'],'max_edge_ratio':result['same_grip_self']['maximum_edge_stretch'],
 'visual':'Actualside/palm retain fingershape in samegrip, root compression reduced; no completegrasp or volumePASS.',
 'shape_gate_scope':'metrics cross conservative stop only; still requirethumb/wholegrip visible plus isolated MCP/PIPimages.',
 'cap_domain_fixed':True,'thumb203_preserved':True,'geometry_UV_bones_weapon_controls_fixed':True,'whole_scores_changed':False,'new_credits':0}
save(QA/'v001-review.json',review)
ledger['trials'].append({'id':'v001','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],
 'reviewer':'Coordinator actualfixedgrip gray A/B and24isolated probes','hypothesis':start['hypothesis'],'change':start['change'],
 'failure_reason':review['classification'],'supporting_reports':[artifact(QA/'v001-review.json'),artifact(QA/'v001-vectors/result.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-v002.json',read(QA/'quality-ledger.json'))
comparison=workbench.compare_quality(request,ledger,ROOT);assert not comparison['blockers'],comparison
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-after-v001.json',comparison)
old=read(ROOT/'runs/qa/ro-swordsman-combo-r008/v004-start.json');previous=read(ROOT/'runs/qa/ro-swordsman-combo-r008/v004-contact-solver/result.json')
bounds=old['bounds'];bounds.update({'finger1:0':[.15,.90],'finger2:0':[.25,1.25],'finger3:0':[.25,1.25],'finger4:0':[.25,1.25]})
save(QA/'v002-start.json',{'id':'v002','started_utc':now.isoformat(),'budget':clock['budget'],'source':result['artifact'],
 'hypothesis':'Coupled finite-difference palm-pad IK canclose fixedmissingdigits without breaking improvedroot oractualcollision constraints.',
 'change':'Poseonly: dampedGaussNewton on3closest existingfixedmask points per digit, bounded jointcurl/MCPsplay andonerigidweapontranslation; no mesh/weights/bonescale/UV changes.',
 'bounds':bounds,'initial_controls':previous['controls'],'initial_splays':previous['splays'],'initial_shift':previous['weapon_shift'],
 'weapon':old['weapon'],'pads_source':'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json',
 'maximum_evaluations':700,'max_solver_seconds':1800,'maximum_iterations':24,'finite_steps':{'curl':.002,'shift':.0002},
 'damping':.0001,'max_normalized_step':.15,'line_search_factors':[1,.5,.25,.125],
 'point_target_distance_m':.0012,'parameter_scales':{'curl':1,'shift':.03},'derivative_collision_checks':'not_run; explicitlylogged diagnostic probes only',
 'hard_admissibility':'Onlyfull lineproposal testedself/swordcross0,unknown0,depth<=1mm,no degenerate,minedge>=.25,maxedge<=3 canreplacebest; finalgrayreview separately required.',
 'objective':'Three closestpoints from each fixed full semanticmask update byiteration as IKguides; acceptancealwaysuses entire original frozenmask>=3 per digit, no gate resampling.',
 'new_credits':0,'candidate_limit':4,'previous_candidates_used':1})
print('R009_V002 registered')
