"""Close the four failed whole-hand candidates and bind actual scoped evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r009';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r009.json');ledger=read(QA/'quality-ledger.json');assert len(ledger['trials'])==4
start=read(QA/'v004-start.json');result=read(QA/'v004-collision-constraints/result.json');fresh=read(QA/'fresh-saved-verification.json');now=datetime.now(timezone.utc)
assert not result['static_numeric_gate'] and not fresh['function_gate']
for item in clock['protected_history']:assert artifact(ROOT/item['path'])==item
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: constrainedcontact remains missingring/index; localroot vector improvement reusableonly.',
 'actual_evaluations':result['actual_evaluations'],'full_function_proposals':result['full_tested_proposals'],'derivative_base_preflight_not_functionchecked':result['derivative_probes_not_function_tested'],
 'stop':result['stop'],'self':fresh['self']['transverse_pairs'],'sword':fresh['contact']['transverse_crossings_count'],
 'contacts':{n:r['within_2mm'] for n,r in fresh['contact']['pad_contacts'].items()},
 'min_edge_ratio':fresh['self']['minimum_edge_ratio'],'max_edge_ratio':fresh['self']['maximum_edge_stretch'],
 'sample_depth_m':fresh['contact']['maximum_penetration_m'],'unknown_inside':len(fresh['contact']['unknown_inside']),
 'visual':'Actualside/palm showloose grasp; zero testedcrossings and conservativeedgebounds do notreplace shape orgripacceptance.',
 'fresh_saved_points_tolerance':{'max_m':fresh['max_saved_fresh_point_delta_m'],'rms_m':fresh['rms_saved_fresh_point_delta_m'],'tolerance_m':1e-6},
 'material_FAIL':16,'interval_left_assembly_300_VFX_freshanimatedGLB':'not_run prerequisitefailure',
 'whole_scores_changed':False,'new_credits':0,'no_fifth_candidate':True}
save(QA/'v004-review.json',review)
ledger['trials'].append({'id':'v004','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],'reviewer':'Coordinator actualproxy/guardedpose andfresh-savedreadback',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],
 'supporting_reports':[artifact(QA/'v004-review.json'),artifact(QA/'v004-collision-constraints/result.json'),artifact(QA/'fresh-saved-verification.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-close.json',read(QA/'quality-ledger.json'));compare=workbench.compare_quality(request,ledger,ROOT)
assert not compare['blockers'] and compare['candidate_trials_used']==4 and compare['next_action']=='stop_budget',compare
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');save(QA/'comparison-final.json',compare)
evidence=copy.deepcopy(ledger['trials'][0]['evidence']);evidence['quality_ledger']=artifact(QA/'quality-ledger.json')
evidence['scope_note']='Explicitfailedfullbaseline retained forfullspec assess; v001-v004 localmodels do not replace acceptedmaster/deliverable.'
save(QA/'evidence-final.json',evidence);assessment=workbench.assess(request,evidence,ROOT);assert assessment['decision']=='not_ready';save(QA/'assessment-final.json',assessment)
rows=[]
for name,folder in [('v002','v002-coupled-IK'),('v003','v003-moving-target'),('v004','v004-collision-constraints')]:
    r=read(QA/folder/'result.json');events=[json.loads(line) for line in (QA/folder/'evaluations.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(events)==r['actual_evaluations']
    rows.append({'id':name,'actual_evaluations':len(events),'full_function_proposals':r['full_tested_proposals'],'derivative_base_preflight_not_functionchecked':r['derivative_probes_not_function_tested'],'solver_seconds':r['elapsed_solver_seconds'],'stop':r['stop']})
save(QA/'phase-accounting-final.json',{'observed_utc':now.isoformat(),'id':request['id'],'phase_started_utc':clock['baseline_started_utc'],'phase_closed_utc':now.isoformat(),
 'phase_wall_seconds_at_close':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),'clock_source':clock['clock_source'],'preclock_preparation_unmeasured':True,
 'baseline_and_preparation_seconds':ledger['trials'][0]['elapsed_seconds'],'candidate_seconds':[{'id':r['id'],'seconds':r['elapsed_seconds']} for r in ledger['trials'][1:]],
 'candidate_used':4,'candidate_limit':4,'contact_solver_counts':rows,'total_contact_solver_probes':sum(r['actual_evaluations'] for r in rows),
 'total_full_function_proposals':sum(r['full_function_proposals'] for r in rows),'total_derivative_base_preflight_not_functionchecked':sum(r['derivative_base_preflight_not_functionchecked'] for r in rows),
 'isolated_positive_joint_poses':24,'additional_isolated_MCP_PIP_verification_poses':8,
 'r009_paid_submissions':0,'r009_new_service_credits':0,'API_balance_query_thisphase':False,'repo_external_writes':'none',
 'old183historyfiles_unchanged':True,'old_phase_reopened':False,'quality_targets_lowered':False,
 'stage_commit_push':'held_by_user','background':'No API/Blender jobs running at close; later readonly review recorded separately.'})
save(QA/'next-method-proposal.json',{'status':'draft_not_executed','new_phase_needed':True,'old_budget_reset':False,
 'reusable_local_weight_source':read(QA/'v001-vectors/result.json')['artifact'],'best_local_contact_source':result['artifact'],
 'finding':'Root vector defect repaired underfixedgeometry; fixedmissingcontact persists. Centers/mesh impossibility notproven; noautomaticgeneration orbone relocation.',
 'recommended':'Audit semantic pad coverage/normals andintendedphalange grasp; use artist-authored anatomical contacttargets and posecorrectives if actualdiagnosis supports it. Preserve exactshape/functionalgates.',
 'solver_limit':'v004 actualcollisionfree proposals canimprove sumgap while lexworstgap slightlyworsens, so algorithm stalls. Not physicalunreachabilityproof; objective revision requires explicitnewplan anddoesnotlower artgates.',
 'generation_route':'If substantivehandshape rebuild justified, designerimage→Hyper3D→Blender; no new operation/statefile silentlycreated.',
 'full_left_assembly_UV_300_VFX_animation_export':'still outstanding','APIandGit_not_started':True})
print(json.dumps({'status':'NO_SHIP','candidates':4,'next_action':compare['next_action'],'assessment':assessment['decision'],'new_credits':0,'probes':sum(r['actual_evaluations'] for r in rows),'full_function_proposals':sum(r['full_function_proposals'] for r in rows),'phase_seconds':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()}))
