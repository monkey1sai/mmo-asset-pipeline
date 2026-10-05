"""Close four failed candidates; bind real output and preserve all earlier history."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,copy
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r008'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r008.json');ledger=read(QA/'quality-ledger.json')
start=read(QA/'v004-start.json');result=read(QA/'v004-contact-solver/result.json');fresh=read(QA/'fresh-saved-verification.json')
assert len(ledger['trials'])==4 and not result['static_numeric_gate'] and not fresh['static_function_gate']
for entry in clock['protected_history']:assert artifact(ROOT/entry['path'])==entry
now=datetime.now(timezone.utc)
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','classification':'PRODUCT_FAILURE: two digits lackfrozenrequiredcontact despitezeroactualcrossings',
 'actual_evaluations':result['actual_evaluations'],'maximum_evaluations':480,'schedule_stop':result['stop'],
 'solver_seconds':result['elapsed_solver_seconds'],'self_transverse':fresh['self']['transverse_pairs'],
 'sword_transverse':fresh['contact']['transverse_crossings_count'],'unknown_inside':len(fresh['contact']['unknown_inside']),
 'maximum_penetration_m':fresh['contact']['maximum_penetration_m'],
 'each_digit_required':3,'actual_contacts':result['best']['each_digit_contacts'],
 'third_nearest_fixedpad_gaps_m':result['best']['third_pad_gap_m'],
 'visual':'Actualpalm/side/back show loose ring/index grasp; nominalzero transverse is insufficient. Neutral thenarindent remains sourceform; nofullartPASS.',
 'verified_preservation':'FreshBlender confirms exacthandpoints/faces/UV/sourceID attrs/weights,16originalboneheads/tails andunscaledswordtriangles; onlycontrols andonerigidweaponshift.',
 'limitations':['383completedactualevaluations fromfixedschedule within480cap; not480performed or globalinfeasibilityproof.',
  'Finite transverse/sample test excludes tangency/coplanar/adjacentfold; no completeabsenceclaim.',
  'L1in earlyr008 reports wasthumbfourcomponentonly; laterboundary/allweights probe includesfourfinger influences. Oldreports preserved.',
  'Polygonsections/convexenclosures diagnostic only, notvolumeacceptance. No animationinterval asserted.'],
 'material_FAIL':16,'UV_rebake':'not_run: function prerequisitefailed','interval_test':'not_run: staticgripfailed',
 'left_assembly_full300_VFX_freshanimatedGLB':'not_run: prerequisitesfailed','whole_scores_changed':False,'new_credits':0}
save(QA/'v004-review.json',review)
ledger['trials'].append({'id':'v004','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':clock['protocol_sha256'],
 'reviewer':'Coordinator savedactualgrayviews/freshBlender readback; independent finalreview separatelyrecorded',
 'hypothesis':start['hypothesis'],'change':start['change'],'failure_reason':review['classification'],
 'supporting_reports':[artifact(QA/'v004-review.json'),artifact(QA/'v004-contact-solver/result.json'),artifact(QA/'fresh-saved-verification.json')],
 'prototype_artifacts':[result['artifact']]})
save(QA/'quality-ledger-before-close.json',read(QA/'quality-ledger.json'))
comparison=workbench.compare_quality(request,ledger,ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used']==4 and comparison['next_action']=='stop_budget',comparison
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(QA/'comparison-final.json',comparison)
evidence=copy.deepcopy(ledger['trials'][0]['evidence']);evidence['quality_ledger']=artifact(QA/'quality-ledger.json')
evidence['scope_note']='Explicitfailedwholebaseline evaluatedbest; localv004diagnostic prototype is notregistered delivery. Never copiedfail intoacceptedmaster.'
save(QA/'evidence-final.json',evidence)
assessment=workbench.assess(request,evidence,ROOT);assert assessment['decision']=='not_ready'
save(QA/'assessment-final.json',assessment)
account={'observed_utc':now.isoformat(),'id':request['id'],'phase_started_utc':clock['baseline_started_utc'],
 'phase_closed_utc':now.isoformat(),'phase_wall_seconds_at_close':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
 'baseline_and_preparation_seconds':ledger['trials'][0]['elapsed_seconds'],
 'candidate_seconds':[{'id':r['id'],'seconds':r['elapsed_seconds']} for r in ledger['trials'][1:]],
 'waiting_planning_review_verification_included_in_wall':True,'preclock_readwall_seconds_separately_reported':6.1,
 'precise_initial_start_unobserved':True,'candidate_used':4,'candidate_limit':4,
 'r008_paid_submissions':0,'r008_new_service_credits':0,'no_API_balance_query_thisphase':True,
 'historical_r007_newservicecredits':.5,'historical_r005_r006_r007_scopedsubtotal':2.,
 'historical_APIcost_subtotal_is_not_entireprojecttotal':True,'imagegen_or_machine_cost':'notpricedbyservice, noestimatedpriceclaim',
 'old_history_hashes_preserved':clock['protected_history'],'stop':'fourcandidatephase closed; no newfifthcandidate oroldclock reset',
 'stage_commit_push':'held_by_user','background':'no_API_orBlender_jobs_running'}
save(QA/'phase-accounting-final.json',account)
save(QA/'next-method-proposal.json',{'status':'draft_not_executed','purpose':'Newmethod required afterfourfailedboundedcandidates; no automaticrestart',
 'source_form':clock['geometry_guide'],'reuseable_weights':read(QA/'v002-direction/result.json')['artifact'],
 'recommended':'Preserve generated appearance/highpoly andtextures as reference; rebuildonly necessaryMCP/web animationloops andcalibrateallfingercenters/weights againstactualunchangedhandle beforematerialwork.',
 'freeze_conflict':'Requires explicitlynewphase thatpermitschanging fourfingerweights/bonecenters/limitedmesh; currentr008keptthese frozen.',
 'alternative':'Boundedmultivariate/IK contactsolver withsameprotectedgeometry; moresearchcost,383coordinatedprobesnotproof ofimpossibility.',
 'generation_alternative':'Newhandinputdesign includingneutral/closedgrasp anatomicalguide, generateonly when evidencejustifies; samefunctionalgates, generationnotrigPASS.',
 'original_full_request_andtargets_preserved':True,'old_budget_reset':False,'noAPI_orGit_globalwrites_started':True})
print(json.dumps({'status':'NO_SHIP','candidates':4,'next_action':comparison['next_action'],'assessment':assessment['decision'],
 'new_credits':0,'phase_seconds':account['phase_wall_seconds_at_close'],'evaluations':result['actual_evaluations']}))
