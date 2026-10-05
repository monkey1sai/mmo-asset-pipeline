"""Close actual v002 failure; begin final local prototype without resetting budgets."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r005'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
ledger=read(QA/'quality-ledger.json'); request=read(ROOT/'requests/ro-swordsman-combo-r005.json'); phase=read(QA/'phase-accounting.json'); start=read(QA/'v002-start.json')
if [t['id'] for t in ledger['trials']]!=['baseline','v001']: raise RuntimeError('Preserve recorded trials')
now=datetime.now(timezone.utc); elapsed=(now-datetime.fromisoformat(start['started_utc'])).total_seconds()
if elapsed>=phase['budget']['trial_seconds'] or (now-datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()>=phase['budget']['total_seconds']: raise RuntimeError('Original budget exhausted')
review={'reviewer':'Independent batch_review; current weights report and actual R/L grip plus small-curl closeups',
        'verdict':'NO_SHIP','verified':['One new core generation completed/downloaded; service reports0.5 credits.',
            'Static source face sharper; actual new core15020tri before four isolated head fins removed.',
            'Exact four fin removals read back; other face positions and corner UVs retained, final core15016tri and nonmanifold0.',
            'Whole assembly58868tri; 48 FK bones and normalized max4 legal weights.',
            '100/160 contact search evaluations; loss reduction did not establish contact.',
            '493 local weight vertices repaired; sibling influences removed without geometry/UV changes; actual big-angle grip still fails.'],
        'failures':['Right finger-root angular collapse and handle penetration; left open grip and pinched web.',
            'Bracer/glove overlap and blue shirt protrusion at breastplate; actual cavity needs local verification.',
            'Full3stressposes for this core,300frames/60fps, separate VFX and animated GLB reimport not performed because local grip fails.'],
        'inference':'Remaining root and large-angle failure justifies bounded local palm/digit retopology plus remeasured joints; neither extra bones nor density alone guarantees a fix.',
        'final_trial_bounds':{'prototype_seconds':5400,'region':'Right hand/wrist seam first, then left only if right passes; equipment local fit/inner cavity only.',
            'stop':['Visible collapse, spikes or penetration at prototype gate','unexpected nonmanifold seam, UV stretch or >60000tri','need whole forearm/shoulder/coat or full armor rebuilding','same original max3/6h/18h exhausted']}}
save(QA/'v002-final-review.json',review); save(QA/'quality-ledger-before-v002.json',ledger)
reports=[QA/'v002-final-review.json',QA/'core-source-comparison/inspection.json',QA/'v002-fit/topology-readback.json',QA/'v002-rig-minimal/preflight.json',QA/'v002-contact-calibrated/calibration.json',QA/'v002-digit-weights/weights.json']
ledger['trials'].append({'id':'v002','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],'ended_utc':now.isoformat(),'elapsed_seconds':elapsed,
    'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'hypothesis':start['hypothesis'],
    'change':'Single improved core source, exact head-fin repair and measured minimal rig; bounded actual handle search and isolated digit weight test. All intermediate artifacts retained.',
    'failure_reason':'PRODUCT_FAILURE: actual latest single-hand grips still collapse/penetrate or remain open; source face improvement cannot offset failed craft/function. Full animation held by preflight. TEST_FAILURE knuckle vertex sampling replaced by edge-plane sections with evidence; no budget reset.',
    'supporting_reports':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in reports]})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison=workbench.compare_quality(request,ledger); save(QA/'comparison-v002.json',comparison)
if comparison['blockers'] or comparison['best_trial_id']!='baseline' or comparison['candidate_trials_used']!=2: raise RuntimeError(comparison)
save(QA/'v003-start.json',{'trial_id':'v003','parent_id':'baseline','started_utc':now.isoformat(),'previous_candidate_trials_used':2,'candidate_trial_limit':3,'phase_clock_reset':False,
    'hypothesis':'Local source-guided palm/digit edge flow and measured three-joint fingers may preserve hand volume at large flexion where isolated weights alone failed.',
    'primary_change':'Right hand prototype only; preserve core above wrist, head/body UVs and five reused equipment types. Expand to left/local cuff fit only after prototype passes.',
    'prototype_deadline_seconds':5400,'contact_search_prior_evaluations':100,'contact_search_global_maximum':160,'new_paid_operation_planned':False,
    'source_reuse':'Only the improved static core component from failed v002 is reused as a local guide; this does not promote the failed whole candidate. Baseline remains the declared parent and current best.'})
print(json.dumps({'v002':'failed','used':2,'remaining':1,'v003_started_utc':now.isoformat(),'quality_target_met':comparison['quality_target_met']},ensure_ascii=False))
