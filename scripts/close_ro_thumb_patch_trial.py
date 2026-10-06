"""Close v003 with useful local geometry and failed UV/visible root skin."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import workbench
ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def artifact(p):return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
ledger=read(QA/'quality-ledger.json');start=read(QA/'v003-start.json');clock=read(QA/'phase-start.json')
patch=read(QA/'v003-thumb-patch/patch.json');uv=read(QA/'v003-thumb-patch/UV-islands.json');skin=read(QA/'v003-skin-diagnostic/skin.json')
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002']
assert patch['geometry']['source_gate'] and not uv['cross_island_interpolation_gate']
now=datetime.now(timezone.utc);elapsed=(now-datetime.fromisoformat(start['started_utc'])).total_seconds()
assert elapsed<clock['budget']['trial_seconds']
snapshot=QA/'quality-ledger-before-v003.json'
with snapshot.open('xb') as f:f.write((QA/'quality-ledger.json').read_bytes())
gap=start['planning_gap_since_v002_seconds'];ledger['trials'][-1]['elapsed_seconds']+=gap
ledger['trials'][-1]['ended_utc']=start['started_utc'];ledger['trials'][-1]['post_trial_planning_gap_seconds']=gap
review={'observed_utc':now.isoformat(),'verdict':'NO_SHIP',
    'geometry_gate':'pass_local_patch_only','material_gate':'fail16mixedsourceUVfaces',
    'thumb_curl_direction':'pass±.05rad_actual_surface_displacement',
    'small_motion_numeric':'no detected transverse pairs; not visible shape acceptance',
    'visible_skin_gate':'fail palm-root angular ridge in actual small0.30 side view',
    'failure_evidence':'Adjacent root vertices123/133 and488/489 jump hand1 tothumb01_1; max edge ratio2.1923778 at0.30rad',
    'next_hypothesis':'Mesh-neighbor root weights with bounded anatomical region and fixed distal/fourfinger weights',
    'full_request_not_run':['Assembly','Sword contact','Left hand','300frame skills','VFX','Fresh animatedGLB'],
    'new_service_credits':0,'phase_clock_reset':False}
save(QA/'v003-review.json',review)
save(QA/'v003-independent-review.json',{
    'reviewer':'existing hand_phase_review required architecture advisory',
    'scope':'actual script/patch/boundary/front/back texture and3Qwire inspected',
    'result':'Supports limited fixed-joint gray skin diagnostic; no source/full-animation acceptance',
    'required_before_material_acceptance':'UVislands, boundary seam, collapse/flip/texturecloseups; no crossislandtransfer',
    'required_before_grip':'Actual single-bone±.05 direction and.15/.30 root/skin/cap views; max4 ownbranch and distalcap rigid',
    'stop':'Palm-root drag/webfold/hinge/reverse/self-cross/capflatten or large corrective/bone movement',
    'model_judgment':'advisory_only','raw_report_received':True})
ledger['trials'].append({'id':'v003','parent_id':'baseline','status':'failed','started_utc':start['started_utc'],
    'ended_utc':now.isoformat(),'elapsed_seconds':elapsed,'protocol_sha256':ledger['protocol_sha256'],
    'reviewer':'Coordinator actual PNG/Blender readbacks plus required independent geometry-to-skin review',
    'hypothesis':start['hypothesis'],'change':'51face thumbIPcap quad patch plus fixed-joint ownbranch LBS diagnosis',
    'failure_reason':'PRODUCT_FAILURE: local geometry passes but16mixedUVfaces and visible palm-root fold from abrupt weights; no grip/full-animation expansion',
    'supporting_reports':[artifact(p) for p in [QA/'v003-review.json',QA/'v003-thumb-patch/patch.json',QA/'v003-thumb-patch/UV-islands.json',QA/'v003-skin-diagnostic/skin.json',QA/'v003-independent-review.json']],
    'prototype_artifacts':[patch['artifact'],skin['artifact']]})
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
comparison=workbench.compare_quality(read(ROOT/'requests/ro-swordsman-combo-r007.json'),ledger,ROOT)
assert not comparison['blockers'] and comparison['candidate_trials_used']==3
save(QA/'comparison-v003.json',comparison)
save(QA/'v003-accounting.json',{'phase_wall_seconds':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
    'ledger_elapsed_seconds':comparison['elapsed_seconds'],'planning_gaps_included':True,'v003_seconds':elapsed,
    'boundary_probes':2,'patch_variants':1,'skin_events':len(skin['events']),'new_credits':0,'phase_clock_reset':False})
print(json.dumps({'v003':'failed','used':3,'next':comparison['next_action']}))
