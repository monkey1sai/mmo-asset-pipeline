"""Close actual eight-revision r006 with preserved partial success and NO-SHIP."""
from datetime import datetime,timezone
from pathlib import Path
import copy,json
from hyper3d_api import file_sha,read_json,write_json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'
ledger=read_json(QA/'quality-ledger.json'); request=read_json(ROOT/'requests/ro-swordsman-combo-r006.json'); clock=read_json(QA/'phase-start.json'); start=read_json(QA/'v008-start.json')
report=read_json(QA/'v008-rigid-wrist/rigid-wrist.json'); rt=read_json(QA/'v008-glb-roundtrip/roundtrip.json'); operation=read_json(ROOT/'runs/hyper3d/operations/ro-hand-source-20261003-001.json')
assert len(ledger['trials'])==8 and ledger['trials'][-1]['id']=='v007'; assert rt['prototype_geometry_playback_pass'] and report['glove_self_crossings_by_sample'][-1]>0
now=datetime.now(timezone.utc)
review={'reviewer':'Independent hand_phase_review Astra/high read-only code/reports/neutral-half-fullPNG plus coordinator actual DCC/readback',
 'verdict':'NO_SHIP','observed':'Rigid265unweighted repair works;1second localGLB geometry/morph playback works; still visible oval cuff bulge, palm folding and source-core armor overlap',
 'partial_verified':{'whole_triangles':57039,'rigid_prediction_max_error_m':report['rigid_prediction_max_error_m'],'pad_contacts':[4,4,5,4,4],'sword_transverse_pairs':0,'seams_max_m':0,'local61frame_roundtrip_pass':True},
 'failures':{'glove_diagnostic_mesh_self_intersection_pairs':report['glove_self_crossings_by_sample'],'tube_diagnostic_mesh_self_intersection_pairs':report['tube_self_crossings_by_sample'],'core_bracer_pairs':[r['SM_RO_core'] for r in report['armor_crossings_by_sample']]},
 'selfcross_limitations':['Evaluated positions paired with source topology; no explicit vertex-order assertion in original diagnostic',
 'Diagnostic BMesh reweld/retriangulate may choose a different nonplanar quad diagonal; pair counts are not distinct physical defects',
 '1um posed weld, shared-vertex skipping and tangential/coplanar exclusions can omit intersections; zero never proves general self-intersectionPASS'],
 'next_professional_method':'Before another production phase, redesign actual neutral thenar/thumb opposition/wrist anatomy and animation loops; evaluate source inner lining and old integrated armor separately, with source vertex/face provenance and actual evaluated triangle locations.',
 'no_new_revision':'8/8 reached. Freeze phase; no left/full combat animation/VFX expansion; no budget reset.',
 'authority':'Advisory private review; no external message, no delivery approval'}
write_json(QA/'v008-independent-review.json',review,exclusive=True)
paths=[QA/'v008-rigid-wrist/rigid-wrist.json',QA/'v008-rigid-wrist/wrist-transition.json',QA/'v008-glb-roundtrip/roundtrip.json',QA/'v008-independent-review.json']
refs=[{'path':p.relative_to(ROOT).as_posix(),'sha256':file_sha(p)} for p in paths]
ledger['trials'].append({'id':'v008','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),
 'elapsed_seconds':(now-datetime.fromisoformat(start['started_utc'])).total_seconds(),'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],
 'hypothesis':start['hypothesis'],'change':'Rigid own-bone rebinding and protected-endpoint wrist correction;61frame/60fps local diagnostic exported and actually reimported',
 'failure_reason':'PRODUCTION/ART_FAILURE: visible cuff bulge/palm folding, diagnostic self-intersections and core armor overlap; left/full300framecombo/VFX absent. Partial contact, rigidity, budget and local roundtrip pass do not compensate.',
 'supporting_reports':refs})
comparison=workbench.compare_quality(request,ledger); assert not comparison['blockers'],comparison
assert comparison['candidate_trials_used']==8 and comparison['next_action']=='stop_budget' and not comparison['quality_target_met']
write_json(QA/'quality-ledger-before-v008.json',read_json(QA/'quality-ledger.json'),exclusive=True); write_json(QA/'quality-ledger.json',ledger); write_json(QA/'comparison-final.json',comparison,exclusive=True)
wall=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(); declared=sum(t['elapsed_seconds'] for t in ledger['trials'])
assert abs(wall-declared)<.002,(wall,declared)
account={'phase':'r006','baseline_started_utc':clock['baseline_started_utc'],'closed_utc':now.isoformat(),'phase_wall_seconds_including_waiting_and_candidateQA':wall,
 'declared_trial_seconds_sum':declared,'max_revisions':8,'revisions_used':8,'next_action':'stop_budget','quality_target_met':False,
 'service_reported_paid_generation_count':1,'service_reported_credits':operation['consumed_credits'],'credits_inferred_from_balance':False,
 'prior_r005':clock['prior_phase_history'],'r005_plus_r006_service_reported_credits':clock['prior_phase_history']['previous_phase_service_reported_credits']+operation['consumed_credits'],
 'history_scope':'r005+r006 only; no claim of whole-project lifetime totals','new_image_tool_elapsed_seconds':clock['preceding_image_tool_elapsed_seconds'],
 'built_in_image_monetary_cost':'not_returned','earlier_planning_wall_time':'not_instrumented','archive_and_final_tool_test_time':'separate final-verification timestamp; not added by overwriting closed phase',
 'commit_push':'held by user','background_work':'none; all paidAPI/Blenderproducers/readback finished'}
write_json(QA/'phase-accounting-final.json',account,exclusive=True)
baseline=ledger['trials'][0]['evidence']; evidence=copy.deepcopy(baseline); evidence['quality_ledger']={'path':(QA/'quality-ledger.json').relative_to(ROOT).as_posix(),'sha256':file_sha(QA/'quality-ledger.json')}
evidence['deliverables']=report['artifacts']; evidence['subject_artifacts']=report['artifacts']
for name,item in evidence['checks'].items():
    item['artifacts']=refs
    if name in ['art_match','geometry_materials','deformation']:
        item['status']='fail'; item['method']='Actual source and freshGLB PNG, full contact/armor diagnostics, and independent review show remaining shape/folding/intersection defects; short playback does not resolve them.'
    elif name=='animation':
        item['status']='fail'; item['method']='Actual61frames/60fps local open-to-grip prototype exists; requested300framecontinuousProvoke/Bash/MagnumBreak/Endure/Victory not produced or accepted.'
    elif name=='export-roundtrip':
        item['status']='fail'; item['method']='FreshGLB local61frame skeletal/morph playback passes,5samplemaxsurfaceerror14.141um; required complete300framecombo and material equivalence not satisfied.'; item['runtime_execution_status']='local_prototype_performed; full_skill_not_run'
    elif name=='skill-effects':
        item['status']='fail'; item['method']='Final local prototype has no required independent slash/fire/golden effects; fullVFXproduction/playback not_run.'
    elif name=='package_complete':
        item['status']='fail'; item['method']='DiagnosticBLEND/GLB archived; completeaccepted300frame/VFXdeliverypackage does not exist.'
    elif name=='rig_mapping':
        item['status']='not_run'; item['method']='Observed53bones/oneskin/actuallocalmovement and rigidrepair; full current-character vertex/branch/rigacceptance not yet performed. Baseline mapping does not automatically transfer.'
    elif name=='scale_pivot':
        item['status']='not_run'; item['method']='Source1.74m preserved; latest complete rest scale/pivot acceptance not separately executed. Do not promote baseline measurement to full current-characterPASS.'
    else: item['status']='not_run'; item['method']='No full current-character acceptance performed for this gate.'
write_json(QA/'final-evidence.json',evidence,exclusive=True); assessment=workbench.assess(request,evidence,ROOT); assert assessment['decision']=='not_ready'
write_json(QA/'assessment-final.json',assessment,exclusive=True)
write_json(QA/'final-review.json',{'verdict':'NO_SHIP','request_id':request['id'],'request_sha256':workbench.request_sha256(request),
 'prototype_artifacts':report['artifacts'],'raw_source_operation':operation['operation_id'],'roundtrip':refs[2],'independent_review':refs[3],
 'quality_comparison':comparison,'assessment':assessment,'full_character_delivered':False,'best_workflow_proven':False,
 'remaining':['reliable neutral palm/thenar/wrist animation topology and rig','independent inner/outer lining fitting','old core/bracer overlap','left hand','full300framecontinuousskillcombo','independentVFX','full-character animated/mat package acceptance'],
 'next_stage_condition':'A new method and prospective production scope/budget must be established without changing the old phase or lowering original targets; no further r006 revisions.'},exclusive=True)
learning=read_json(QA/'workflow-learning-prepared.json'); learning['phase_status']='Closed8/8local revisions; NO_SHIP; API and local61frame roundtrip completed'
learning['verified_this_turn']=[
 {'topic':'Exact DPAPI authority and supported API','evidence':['api-completion-verification.json'],'observed':'Oneauthorizedfile934bytes, provider/policy hashes unchanged, onepaidgeneration0.5credits, sourceGLB/preview downloaded'},
 {'topic':'Generated source is a starting point','evidence':['hand-source/inspection.json'],'observed':'requestedQuad/1000; actual2268tri, packed2K, two-layer cuff; no automatic topologyPASS'},
 {'topic':'Hard contact gates before scalar optimization','evidence':['v002-calibration/calibration.json','v003-joint-ik/joint-ik.json','v005-thumb-wrist/thumb-wrist.json'],'observed':'Scalarcollisionminimization removesgrasp; independent joints andbounded3.804mmcontactshape achieve fivepad4/4/5/4/4+sword0crossings but othergatesfail'},
 {'topic':'Preserve source anatomy identifiers during cutting','evidence':['v006-underlay-diagnosis/underlay.json'],'observed':'915protectedvertices and1780triangleUV readback equal; masks mappedbefore search, inner/outer rings diagnosed'},
 {'topic':'Topology modifiers must revalidate bone data','evidence':['boolean-binding-diagnosis.json','wrist-volume-diagnosis.json','v008-rigid-wrist/rigid-binding-repair.json'],'observed':'Boolean265unweighted vertices cause explosion; explicitoriginalrigidbone binding restores0.303ummaxpredictionerror'},
 {'topic':'Seams/contact do not establish shape acceptance','evidence':['v008-rigid-wrist/wrist-transition.json','v008-independent-review.json'],'observed':'seam0/contactPASS coexistwithbulge,palmfolds,diagnosticselfcrossings andcorearmoroverlap;20.777mmwrist and46.680mmunderlayare substantial fitting, notmicrodetail'},
 {'topic':'Actual export playback needs exact GLB mappings','evidence':['v008-glb-roundtrip/roundtrip.json'],'observed':'Originaltime1/60..61/60 retained; importskinmayreparentmesh; exactnode.mesh binding and actual61frame skeletal/morph playback pass,5samplegeometry14.141ummaxerror'},
 {'topic':'Bounded experiments stop honestly','evidence':['comparison-final.json','assessment-final.json','phase-accounting-final.json'],'observed':'8failedfull candidates, bestbaselineunchanged, stop_budget/not_ready; allpartial successes/history/costs preserved'}]
learning['prepared_rules_are_historical']=True; learning['final_character_delivered']=False; learning['best_workflow_proven']=False
learning['updated_workflow_files']=['docs/art-workflow.md','docs/art-quality-loop.md','.agents/skills/art-engineer/SKILL.md']; learning['commit_push']='held by user'
write_json(QA/'workflow-learning.json',learning)
print(json.dumps({'closed':True,'verdict':'NO_SHIP','comparison':comparison['next_action'],'assessment':assessment['decision'],'phase_seconds':wall,'service_credits':operation['consumed_credits']}))
