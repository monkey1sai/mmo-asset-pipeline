"""Register the human-selected new phase; preserve all closed source history."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,copy,subprocess
import workbench
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'runs/qa/ro-swordsman-combo-r007';QA=ROOT/'runs/qa/ro-swordsman-combo-r008'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
assert not QA.exists() and not (ROOT/'requests/ro-swordsman-combo-r008.json').exists()
old=read(ROOT/'requests/ro-swordsman-combo-r007.json');oldledger=read(OLD/'quality-ledger.json')
prior=workbench.compare_quality(old,oldledger,ROOT)
assert prior==read(OLD/'comparison-final.json') and prior['candidate_trials_used']==4 and prior['next_action']=='stop_budget'
assert subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()=='c990639962b7ce85eb6beb631057aa4d76a3e86d'
proposal=read(OLD/'next-method-proposal.json');assert proposal['status']=='draft_not_executed'
source=ROOT/proposal['source']['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==proposal['source']['sha256']
account=read(OLD/'phase-accounting-final.json');now=datetime.now(timezone.utc)
request=copy.deepcopy(old);request.update(id='ro-swordsman-combo-r008',title='RO劍士：完整拇指骨鏈權重向量與關節隔離診斷',brief='選擇方向1',purpose=old['purpose'])
request['production']['route']='modify';request['production']['max_revisions']=4
request['phase_history']={'previous_request':'requests/ro-swordsman-combo-r007.json',
    'previous_request_sha256':workbench.request_sha256(old),'previous_result':artifact(OLD/'comparison-final.json'),
    'previous_ledger':artifact(OLD/'quality-ledger.json'),'previous_accounting':artifact(OLD/'phase-accounting-final.json'),
    'previous_revisions':4,'previous_phase_seconds_at_close':account['phase_wall_seconds_at_close'],
    'previous_new_service_credits':.5,'r005_r006_r007_scoped_service_credits':2.,
    'authority':'Human 選擇方向1; four new candidates, complete weight vectors and isolated joint diagnosis; preserve history, no paid firstdiagnosis; stage/commit/push held',
    'new_method':'Separate truecap anchors from joint transition; solve normalized whole hand/thumb01/thumb02/thumb03 vectors; singlejoint anatomy tests',
    'old_phase_reopened':False,'quality_targets_lowered':False}
QA.mkdir(parents=True);save(ROOT/'requests/ro-swordsman-combo-r008.json',request)
assert request['spec']==old['spec'] and request['quality']==old['quality']
guarded=[ROOT/'requests/ro-swordsman-combo-r007.json',OLD/'quality-ledger.json',OLD/'comparison-final.json',OLD/'phase-accounting-final.json',
    source,ROOT/read(OLD/'v004-root-weights/weights.json')['artifact']['path']]
clock={'id':request['id'],'baseline_started_utc':'2026-10-03T13:48:14+00:00',
    'clock_source':'First current-turn UTC observation after initial readonlystate/memory command; later planning/review included',
    'initial_read_exec_wall_seconds_before_clock_observation':6.1,'precise_initial_start_unobserved':True,
    'registered_utc':now.isoformat(),'request_sha256':workbench.request_sha256(request),
    'protocol_sha256':workbench.quality_sha256(request),'max_revisions':4,'budget':request['quality']['budget'],
    'baseline_source':artifact(ROOT/'assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend'),
    'local_baseline_source':read(OLD/'v004-root-weights/weights.json')['artifact'],
    'geometry_guide':proposal['source'],'joint_probe':artifact(OLD/'v001-source-preparation/joint-and-pole-probe.json'),
    'protected_history': [artifact(p) for p in guarded],
    'existing_API_authority_preserved':True,'new_paid_generation':False,'repo_external_writes':'none',
    'effective_runtime':{'sandbox_mode':'workspace-write','approvals_reviewer':'auto_review','hooks':'not_changed',
        'default_command_probe':'ENVIRONMENT_FAILURE: sandbox provisioning failed','full_scoped_escalations':'individual review, no permanent prefix'},
    'stage_commit_push':'held_by_user','old_clocks_or_costs_reset':False}
save(QA/'phase-start.json',clock)
save(QA/'authorization.json',{'human':'選擇方向1','observed_utc':now.isoformat(),
    'scope':'Newfourcandidatephase usingexistinggeometry, fullweightvectors andisolatedCMC/MCP/IP; continuefunction/material/fullrequest gates only if prerequisites pass',
    'paid_generation_first_diagnosis':False,'global_files':'none','stage_commit_push':'held_by_user'})
save(QA/'planning-review.json',{'reviewer':'existing hand_phase_review required architecture advisory','route_observation':'8b9860b8-c498-46ae-90a6-7bafc74ce387',
    'scope':'Prior r007 observedsource/script/readbacks, proposed newmethod; no newlycreatedassets reviewedyet',
    'required_first':'Actual worstedge locations/source IDs/neighbor rings/CMC-MCP-IP coordinate relation and samepicture wire+sections before anchors freeze',
    'required_solver':'Whole normalized vector, cap byrestpointIDs/spatialaxis, MCPnotarbitrarynonzero-weightfrozen; protectedfourfinger; anchors everycomponent',
    'required_tests':'neutral; IP/MCP/CMC each±.05/.15/.30; CMCopposition separatelyverified; combined aftersingles pass; sameevaluatedpoints/triangles IDs',
    'numeric_not_artpass':True,'past16UVcrossislandfaces':'materialFAIL untilcorrectcharts aftergrayfunctionpass',
    'fourcandidatebudget_not_resetting_r007':True})
print(json.dumps({'request':request['id'],'clock':clock['baseline_started_utc'],'old_phase':'closed_preserved','new_credits':0}))
