"""Append clarified baseline evidence; preserve every original preparation record."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def artifact(p): return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v,exclusive=True):
    with p.open('x' if exclusive else 'w',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2); f.write('\n')
request=read(ROOT/'requests/ro-swordsman-combo-r007.json'); clock=read(QA/'phase-start.json')
old=read(QA/'quality-ledger.json'); assert len(old['trials'])==1 and old['trials'][0]['id']=='baseline'
interval=read(QA/'baseline/baked-interval.json'); assert interval['frames']==61 and interval['half_frame_diagnostics']==60 and not interval['baked_interval_collision_pass']
contract=artifact(QA/'hand-gate-contract-v2.json'); evidence=deepcopy(old['trials'][0]['evidence'])
evidence['local_gate_contract']=contract
for item in evidence['checks'].values(): item['artifacts'].append(artifact(QA/'baseline/baked-interval.json'))
evidence['checks']['deformation']['method'] += ' Additional61actualframes+60half-frame samples confirm saved-clip intervalcollisionFAIL; contact only required at declared closed holdingframe61; other intervals still require no penetration.'
save(QA/'quality-ledger-before-local-clarification.json',old)
ledger=deepcopy(old); ledger['local_gate_contract']=contract; ledger['trials'][0]['evidence']=evidence
now=datetime.now(timezone.utc); ledger['trials'][0]['ended_utc']=now.isoformat(); ledger['trials'][0]['elapsed_seconds']=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()
ledger['pre_candidate_clarification']={'record':artifact(QA/'contract-clarification.json'),'old_record_preserved':'runs/qa/ro-swordsman-combo-r007/quality-ledger-before-local-clarification.json',
    'scope':'Before first candidate: remove ambiguous historical budget and add actual baked-interval requirement; same source/geometry/scores/targets, include additional baseline QA time; no counter/clock reset'}
comparison=workbench.compare_quality(request,ledger,ROOT); assert not comparison['blockers'] and comparison['candidate_trials_used']==0
save(QA/'quality-ledger.json',ledger,False); save(QA/'baseline/evidence-v2.json',evidence)
save(QA/'comparison-baseline-v2.json',comparison)
save(QA/'baseline-binding-v2.json',{'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),
    'local_gate_contract':contract,'actual_baseline_report':artifact(QA/'baseline/baseline.json'),'actual_baked_interval':artifact(QA/'baseline/baked-interval.json'),
    'original_binding':artifact(QA/'baseline-binding.json'),'supersession':artifact(QA/'contract-clarification.json'),'first_candidate_started':False})
assessment_evidence=deepcopy(evidence); assessment_evidence['quality_ledger']=artifact(QA/'quality-ledger.json')
save(QA/'baseline/assessment-evidence-v2.json',assessment_evidence)
assessment=workbench.assess(request,assessment_evidence,ROOT); assert assessment['decision']=='not_ready'
save(QA/'assessment-preparation.json',assessment)
save(QA/'preparation-state.json',{'observed_utc':now.isoformat(),'phase':'r007','API':'prepared_not_submitted',
    'current_local_contract':contract,'comparison':artifact(QA/'comparison-baseline-v2.json'),'assessment':'not_ready','candidate_trials_used':0,
    'resume_operation':'ro-hand-structure-20261003-001','resume_gate':'Exact new DPAPI file authority; existing demand-driven API spending remains authorized',
    'authority_question_is_not_credit_limit':True,'new_Hyper3D_credits':0,'image_cost':'not_returned',
    'prior_r005_plus_r006_service_credits':1.5,'phase_clock_not_reset':True,'commit_push':'held by user'})
print(json.dumps({'baseline_v2_bound':True,'frames':61,'half_frames':60,'candidates':0,'assessment':'not_ready','new_charge':0}))
