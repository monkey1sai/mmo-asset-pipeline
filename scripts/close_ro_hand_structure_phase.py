"""Close r007 at the original four-candidate boundary; keep all failed specimens."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
request=read(ROOT/'requests/ro-swordsman-combo-r007.json');ledger=read(QA/'quality-ledger.json')
start=read(QA/'v004-start.json');clock=read(QA/'phase-start.json');weights=read(QA/'v004-root-weights/weights.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002','v003']
assert weights['actual_variants']==3 and weights['small_motion_numeric_gate'] and not weights['material_gate']
assert weights['events'][-1]['maximum_edge_stretch']>2.3
now=datetime.now(timezone.utc);elapsed=(now-datetime.fromisoformat(start['started_utc'])).total_seconds()
assert elapsed<clock['budget']['trial_seconds']
snapshot=QA/'quality-ledger-before-v004.json'
with snapshot.open('xb') as f:f.write((QA/'quality-ledger.json').read_bytes())
gap=start['planning_gap_since_v003_seconds'];ledger['trials'][-1]['elapsed_seconds']+=gap
ledger['trials'][-1]['ended_utc']=start['started_utc'];ledger['trials'][-1]['post_trial_planning_gap_seconds']=gap
independent={'observed_utc':now.isoformat(),'reviewer':'existing hand_phase_review / required Astra architecture advisory',
    'scope':'weight script/reports/frozenweights + actual .30palm/back/side and .30+.15opposition side views',
    'verdict':'NO_SHIP; do not expand to grip; close originalfourcandidatephase',
    'verified_problem':'All vertices with any thumb02/03 weight were frozen; solver changed only thumb01 scalar, allowing hand->thumb02 adjacency jumps',
    'actual_examples':[
        {'edge':[56,580],'adjustable_weights':{'hand':.9442,'thumb_01':.0558},'fixed_weights':{'thumb_02':.9850,'thumb_01':.0150}},
        {'edge':[57,582],'adjustable_weights':{'hand':.9617,'thumb_01':.0383},'fixed_weights':{'thumb_02':1.0}},
        {'edge':[59,578],'adjustable_weights':{'hand':.9226,'thumb_01':.0774},'fixed_weights':{'thumb_02':.9449,'thumb_01':.0551}}],
    'values_scope':'Rounded reviewer examples; exact frozen-weights.json retained',
    'inference':'Chain-incompatible neighboring weights plausibly contribute to observed root fold; not proven sole cause',
    'unverified':['CMC pivot necessarilywrong','Fullpalm topology necessarilyunusable','Wholehand regeneration necessary'],
    'recommended_new_method':'Distinguish truly rigid distalcap from CMC/MCP transition; constrain complete hand/thumb01/thumb02 vectors, singlebone CMC/MCP/IP diagnosis, then decide topology/axis work',
    'not_authorization':'Advisory does not extend fourcandidatebudget or paid/global/Git scope',
    'background_work':'none'}
save(QA/'v004-independent-review.json',independent)
save(QA/'delivery-routing.json',{'stage':'before_delivery','failure_count':4,'required_review':True,
    'route':'architecture_review','model':'gpt-6-astra','reasoning_effort':'high','provider_called':False,
    'advisory_only':True,'observation_id':'6ab471bd-c201-42f2-8ac0-468e235d6634','review_record':'v004-independent-review.json'})
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','scope':'v004 fixedsource smallmotion only',
    'visible_deformation_gate':'fail_root indentation/fold in .30side and .30+.15opposition side',
    'small_motion_numeric_gate':weights['small_motion_numeric_gate'],'numeric_subset_does_not_override_visual_failure':True,
    'source_geometry_gate':'passed local thumbcap only','material_gate':'fail16mixedsourceUVislandfaces',
    'weight_domain_failure':'Full weight-vector chain transitions not solved by scalar thumb01 smoothing; any thumb02 influence incorrectly frozen for this hypothesis',
    'not_run':['Sword contact','Forearm/bracer assembly','Left hand','Full300frame skills','VFX','Fresh animatedGLB'],
    'new_service_credits':0,'quality_targets_lowered':False,'phase_clock_reset':False}
save(QA/'v004-review.json',review)
save(QA/'v003-source-gate-scope-correction.json',{
    'original_report':artifact(QA/'v003-thumb-patch/patch.json'),'original_report_preserved':True,
    'original_source_gate_true_scope':'Local geometry/preservedcornerUV only',
    'actual_all_source_gates_pass':False,'changed_material_gate':False,
    'actual_crossisland_faces':16,'skin_visual_acceptance':False,
    'correction':'Local pole/topology/sample pass permits diagnostic only, not full source/rig/material/animation acceptance'})
ledger['trials'].append({'id':'v004','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':now.isoformat(),'elapsed_seconds':elapsed,'protocol_sha256':ledger['protocol_sha256'],
    'reviewer':'Coordinator actual fixedviews/readbacks plus required independent finalarchitecturereview',
    'hypothesis':start['hypothesis'],'change':'100step meshneighbor root scalar weights in3bounded domains; fixed geometry/bones/fourfingers/distal thumb',
    'failure_reason':'PRODUCT_FAILURE: visible root folding remains; scalar-only solver cannot remove full hand-to-thumb02 vector jump at frozen boundary;16mixedUVfaces still fail. No grip/fullskill expansion.',
    'supporting_reports':[artifact(p) for p in [QA/'v004-review.json',QA/'v004-independent-review.json',QA/'v004-root-weights/weights.json',QA/'v004-root-weights/frozen-weights.json']],
    'prototype_artifacts':[weights['artifact']]})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison=workbench.compare_quality(request,ledger,ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used']==4
assert comparison['next_action']=='stop_budget' and not comparison['quality_target_met']
save(QA/'comparison-final.json',comparison)
evidence=read(QA/'baseline/assessment-evidence-v2.json')
evidence['quality_ledger']=artifact(QA/'quality-ledger.json')
evidence['assessment_scope']='Best baseline remains failed; all four new source/skin prototypes failed before whole-request scoring; no candidate quality improvement claimed'
save(QA/'assessment-evidence-final.json',evidence)
assessment=workbench.assess(request,evidence,ROOT);assert assessment['decision']=='not_ready'
save(QA/'assessment-final.json',assessment)
wall=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()
assert abs(comparison['elapsed_seconds']-wall)<.001
api=read(QA/'api-completion-verification.json')
accounting={'phase_started_utc':clock['baseline_started_utc'],'phase_closed_utc':now.isoformat(),
    'phase_wall_seconds_at_close':wall,'ledger_elapsed_seconds':comparison['elapsed_seconds'],
    'planning_waiting_and_review_time_included':True,'candidates_used':4,'maximum_candidates':4,
    'per_trial_seconds_max':clock['budget']['trial_seconds'],'phase_seconds_max':clock['budget']['total_seconds'],
    'new_Hyper3D_service_reported_credits':api['service_reported_consumed_credits'],
    'paid_submissions':1,'downloads':len(api['download_records']),
    'scoped_r005_r006_r007_service_credits':2.0,'scope_not_all_project_cost':True,
    'image_generation_price':'not_returned','old_phase_clocks_or_costs_reset':False,
    'decision':'stop_budget/NO_SHIP','stage_commit_push':'held_by_user'}
save(QA/'phase-accounting-final.json',accounting)
save(QA/'final-review.json',{'observed_utc':now.isoformat(),'verdict':'NO_SHIP',
    'API':'downloaded, one0.5credit source, exactauthorizedDPAPIcreated',
    'local_geometry':'v003thumbcap geometry preserved814faces and clears authoredprimarybands; not fullsource acceptance',
    'remaining':'Visible rootskin fold and16UVcrossislandfaces; no acceptedrightgrip/left/fullskills/effects/export',
    'proven_new_method_gap':'Wrong freeze boundary + scalar-only weight solver preserve neighboring chain jumps',
    'not_proven':'Wholehand regeneration or fullpalm retopo necessary',
    'next_condition':'New method and prospective bounded plan for complete weightvector/isolatedjoint diagnosis, preservingallprior clocks/costs/failedartifacts',
    'comparison':artifact(QA/'comparison-final.json'),'assessment':artifact(QA/'assessment-final.json'),
    'background_work':'none','stage_commit_push':'held_by_user'})
print(json.dumps({'used':4,'next':comparison['next_action'],'assessment':assessment['decision'],'phase_wall_seconds':wall,'new_credits':.5}))
