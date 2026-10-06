"""Preserve failed first source gate and its full original wall clock."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json
import workbench
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def artifact(p): return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2); f.write('\n')
request=read(ROOT/'requests/ro-swordsman-combo-r007.json'); ledger=read(QA/'quality-ledger.json')
assert [t['id'] for t in ledger['trials']]==['baseline']
start=read(QA/'v001-start.json'); clock=read(QA/'phase-start.json'); flow=read(QA/'v001-thumb-flow/flow.json')
assert not flow['pole_gate'] and flow['probe_count']==160
now=datetime.now(timezone.utc)
elapsed=(now-datetime.fromisoformat(start['started_utc'])).total_seconds()
assert elapsed<clock['budget']['trial_seconds']
assert (now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds()<clock['budget']['total_seconds']
snapshot=QA/'quality-ledger-before-v001.json'
assert not snapshot.exists(); snapshot.write_bytes((QA/'quality-ledger.json').read_bytes())
save(QA/'v001-stop-scope-correction.json',{
    'observed_utc':now.isoformat(),'source_report':artifact(QA/'v001-thumb-flow/flow.json'),
    'original_stop_reason':flow['stop_reason'],'actual_bounded_stop':'160-probe budget reached with2poles remaining',
    'does_not_prove_Blender_cannot_fix':True,'old_report_preserved':True,
    'correction':'Unsearched neighbors after probe limit are not proof of no legal edge rotation; no extra v001 probes allowed'})
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP','scope':'v001 source gate; no rig/posed skin',
    'verified':['One native OBJ generation/download; service0.5credits;1213nativequads',
        'Actual cuff has inner/outer contours;189liningvertices removed in new exterior specimen',
        '18edge singleordered cuff;1730tri;retainedface cornerUV actualreadback consistent; neutraltransverse0',
        'Corrected diffuse material in new file; preserved initial orange material wiring diagnostic',
        'Frozen source joint centers inside diagnostic; 160local topologyprobes,2chosen rotations reduce4poles to2'],
    'failed_gate':'2non-four-valence poles remain in frozen thumb IP flexionband; must not bind or call animation-ready',
    'not_run':['Character wrist fitting','Rig/skin deformation','Grip/contact','300frame skills','VFX','Fresh animated GLB'],
    'method_limit':'Single-step strictpole-reduction hillclimb +160bound; not an impossibility result',
    'source_and_old_history_preserved':True,'quality_targets_lowered':False}
save(QA/'v001-review.json',review)
# Include the actual authorization waiting/preflight gap in the baseline period.
ledger['trials'][0]['ended_utc']=start['started_utc']
ledger['trials'][0]['elapsed_seconds']=start['phase_elapsed_before_candidate_seconds']
ledger['trials'][0]['waiting_time_accounting']={'prior_snapshot':artifact(snapshot),
    'reason':'Includes time after saved baseline QA through authorized preflight; source/scores unchanged; no clock reset'}
ledger['trials'].append({'id':'v001','parent_id':'baseline','status':'failed',
    'started_utc':start['started_utc'],'ended_utc':now.isoformat(),'elapsed_seconds':elapsed,
    'protocol_sha256':workbench.quality_sha256(request),'reviewer':'Coordinator actual source views + required independent hand_phase_review architecture',
    'hypothesis':start['hypothesis'],'change':'New worn-glove native source, lining removal, explicit PBR reconstruction, measured joint bands and bounded local edge flow repair',
    'failure_reason':'PRODUCT_FAILURE: frozen primary thumb flexion bands retain2poles after160boundedprobes; source gate fails, rig and full animation held. TEST_FAILURE: initial packed PBR map used as color, corrected; initial black bottom view corrected. No full-character score claimed.',
    'supporting_reports':[artifact(p) for p in [QA/'api-completion-verification.json',QA/'v001-review.json',
        QA/'v001-source-preparation/preparation.json',QA/'v001-source-preparation/joint-and-pole-probe.json',
        QA/'v001-thumb-flow/flow.json',QA/'v001-stop-scope-correction.json']],
    'prototype_artifacts':[artifact(ROOT/flow['artifact']['path'])]})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison=workbench.compare_quality(request,ledger,ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used']==1
save(QA/'comparison-v001.json',comparison)
save(QA/'v001-accounting.json',{'phase_wall_seconds_through_v001':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
    'ledger_elapsed_seconds':comparison['elapsed_seconds'],'baseline_waiting_included':True,'v001_seconds':elapsed,
    'service_credits':.5,'source_geometry_trials_used':1,'topology_probes':160,'continued_time_clock_reset':False})
assert abs(comparison['elapsed_seconds']-(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds())<.001
print(json.dumps({'v001':'failed','candidates_used':1,'next_action':comparison['next_action'],
                  'quality_target_met':False,'pole_gate':False,'phase_wall_seconds':comparison['elapsed_seconds']}))
