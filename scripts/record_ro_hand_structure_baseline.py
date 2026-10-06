"""Bind the actual r007 baseline and append a preserved r006 scope correction."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import workbench

ROOT=Path(__file__).resolve().parents[1]; ID='ro-swordsman-combo-r007'; QA=ROOT/'runs/qa'/ID
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def artifact(p): return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,obj):
    with p.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n')
request=read(ROOT/'requests'/(ID+'.json')); clock=read(QA/'phase-start.json'); base=read(QA/'baseline/baseline.json')
assert workbench.request_sha256(request)==clock['request_sha256']
assert base['source_unchanged'] and base['whole_character_triangles']==57039 and not base['invalid_weights']
scores={
    'design-intent':{'value':3,'reason':'Brown-haired anime swordsman, silver armor, blue/white cloth and brown leather present; overlapping fittings and nonfunctional intermediate grasp remain.'},
    'silhouette':{'value':3,'reason':'Recognizable whole-character views; source wrist interface has visible bulb and discontinuous armor fit.'},
    'form-proportion':{'value':2,'reason':'Actual close views show thenar/palm-root fold and a balloon-like wrist sleeve; source-core duplicated armor volume remains.'},
    'materials':{'value':3,'reason':'Major PBR regions and packed2K source textures readable; seams/soft gear detail and unresolved sampler equivalence remain.'},
    'craft':{'value':1,'reason':'Five evaluated local samples show transverse self-crossings and palm/wrist folding; contact only passes at fully closed endpoint.'},
    'use-readability':{'value':0,'reason':'Existing actual61frame grip prototype is not requested300frameProvoke/Bash/MagnumBreak/Endure/Victory and has no independent required effects.'},
}
review={'verdict':'NO_SHIP baseline','reviewer':'Coordinator: actual whole-character/hand PNG and evaluated Blender measurements; required independent preparation review separately recorded',
    'scores':scores,'source_not_accepted_master':True,
    'verified_scope':'25actual fixed PNGs, mesh/bone/weight inventory,5baked-frame contacts and actual evaluated-triangle diagnostic with stable point-ID assertions',
    'unverified':'New design anatomy/3D/native topology; full300frame/VFX and fresh complete animated package; no new source generated',
    'numeric_method_change_is_not_art_improvement':True}
save(QA/'baseline/review.json',review)
support=[artifact(QA/'baseline'/name) for name in ['baseline.json','review.json']]
methods={
 'art_match':('fail','Actual fixed whole-character PNG and grip/wrist close-ups show folds, bulbous wrist and armor overlap.'),
 'scale_pivot':('pass','Actual neutral source core height1.739999903m, floor-1.27e-8m; source rig/root world origin preserved. X/Z planning envelope not an exact size assertion.'),
 'geometry_materials':('fail','57039tri and packed source textures measured; visible fitting, diagnostic self-crossings and unresolved material equivalence prevent full geometry/material acceptance.'),
 'package_complete':('fail','Byte-identical baselineBLEND/GLB exist; full accepted300frame skills and effects delivery package absent.'),
 'rig_mapping':('pass','Actual53bones/oneGLBskin, maximum4influences, normalized per-vertex weights and0invalid; scope mapping only, not deformation.'),
 'deformation':('fail','Actual5bakedframe readbacks and near PNG show palm/wrist folding; sword depth7.19/5.43/3.41/1.34/0mm and nonzero transverse pairs before closed endpoint.'),
 'animation':('fail','Actual source clip61frames/60fps; requested300frame continuous skills absent; no full skill playback claimed.'),
 'export-roundtrip':('fail','ActualGLBinventory one61frame prototype exists; priorr006local geometry readback report retained, no new full300frame/material-equivalent fresh import performed.'),
 'skill-effects':('fail','Required independent slash/fire/golden skill effects absent from inspected source; fullVFXproduction/playback not_run.'),
}
checks={}
for c in workbench.required_checks(request):
    status,method=methods[c['id']]
    checks[c['id']]={'status':status,'method':method,'artifacts':support}
    if c['id'] in ['export-roundtrip','skill-effects']:
        checks[c['id']]['runtime_execution_status']='not_run_for_complete_request'
content=base['artifacts']
evidence={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),
          'checks':checks,'deliverables':content,'subject_artifacts':content,'local_gate_contract':artifact(QA/'hand-gate-contract.json')}
now=datetime.now(timezone.utc)
trial={'id':'baseline','parent_id':None,'status':'completed','started_utc':clock['baseline_started_utc'],'ended_utc':now.isoformat(),
       'elapsed_seconds':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
       'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],
       'previews':{n:artifact(QA/'baseline'/(n+'.png')) for n in request['quality']['protocol']['views']},
       'scores':scores,'evidence':evidence}
ledger={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),
        'local_gate_contract':artifact(QA/'hand-gate-contract.json'),'trials':[trial],'phase_history':request['phase_history']}
comparison=workbench.compare_quality(request,ledger,ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used']==0 and comparison['next_action']=='revise_current_best'
save(QA/'baseline/evidence.json',evidence); save(QA/'quality-ledger.json',ledger); save(QA/'comparison-baseline.json',comparison)
save(QA/'baseline-binding.json',{'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),
    'local_gate_contract':artifact(QA/'hand-gate-contract.json'),'actual_baseline_report':artifact(QA/'baseline/baseline.json'),
    'source_helpers':[artifact(QA/'baseline'/n) for n in ['ro_hand_gate.py','ro_review_common.py']],
    'first_candidate_started':False,'source_model_byte_identical':True})
correction={'observed_utc':now.isoformat(),'classification':'TEST_FAILURE in reporting scope, not a newly changed source mesh',
    'original_phase_closed_unchanged':True,'r006_ledger_modified':False,
    'corrected_claim':'v008sword-contact pass refers to the fully closed endpoint. The five-sample claim of zero sword penetration/crossings throughout the saved local clip is not supported.',
    'new_actual_evidence':artifact(QA/'baseline/baseline.json'),
    'source':clock['baseline_source'],'source_byte_unchanged':True,
    'actual_frames':[s['frame'] for s in base['local_samples']],
    'maximum_penetration_m':[s['contact']['maximum_penetration_m'] for s in base['local_samples']],
    'sword_transverse_pairs':[s['contact']['transverse_crossings_count'] for s in base['local_samples']],
    'closed_endpoint_contacts':[v['within_2mm'] for v in base['local_samples'][-1]['contact']['pad_contacts'].values()],
    'meaning':'r006NO_SHIP/stop_budget and localGLBgeometry roundtrip remain; geometry equivalence preserves defects and never constitutes collision acceptance.'}
save(ROOT/'runs/qa/ro-swordsman-combo-r006/v008-baked-clip-scope-correction.json',correction)
print(json.dumps({'baseline_recorded':True,'candidates':0,'quality':False,'r006_scope_correction_appended':True,'new_paid_generation':False}))
