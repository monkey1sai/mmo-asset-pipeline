"""Freeze r010 authoring scope and unchanged acceptance before first candidate."""
from datetime import datetime, timezone
from pathlib import Path
import copy, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r010';OLD=ROOT/'runs/qa/ro-swordsman-combo-r009'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
artifact=lambda p:{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
clock=read(QA/'phase-start.json');request=read(ROOT/'requests/ro-swordsman-combo-r010.json')
maskpath=ROOT/'runs/qa/ro-swordsman-combo-r007/v003-skin-diagnostic/frozen-masks-and-weights.json'
mask=read(maskpath);oldcontract=read(OLD/'local-contract.json');now=datetime.now(timezone.utc)
contract={
 'created_utc':now.isoformat(),'source':clock['local_source'],'basis_snapshot':artifact(QA/'baseline/mesh-and-weights.json'),
 'pads_source':artifact(maskpath),'pads':mask['pads'],'thumb_protected_ids':oldcontract['thumb_protected_ids'],
 'corrective_body_domains':{n:sorted(int(i) for i,r in mask['semantic'].items() if r['branch']==n) for n in ['finger1','finger2','finger3','finger4']},
 'basis_topology_UV_weights_bones_fixed':True,'original_source_ids_required':list(range(904)),
 'geometry_change':'Only explicit additive shape keys over original Basis; no topology or direct Basis edits.',
 'authoring_sequence':'First authored bone controls only. Corrective requires plausible collision-free base control selection and actual surface audit; not blind filling numeric contact deficits.',
 'author_contact_intent':'C-shaped fourfinger wrap, finger pulp facing handle; thumb opposition retained. Ring and index need distributed distal phalange contact; whole palmar pad width and knuckle silhouettes remain visible.',
 'target_policy':'Full branch/phalange fields derived from anatomy and pad-normal audit. No acceptance-mask or nearest-three selection changes.',
 'corrective_scope':'Fourfinger semantic body only; broad distal palmar pad fields, proximal smooth taper, 203thumb and all other vertices zero offset. All patch vertices/edges/faces checked, not only pads.',
 'corrective_displacement_limits':{'rest_max_m':.004,'grasp_world_max_m':.003,'inverse_skin_condition_max':20,'inverse_roundtrip_tolerance_m':1e-6},
 'skin_coordinates':'Shape key before linear-blend Armature. Verify weighted pose/rest matrices against actual Blender; inverse only stable transforms. Store rest and desired/actual posed deltas.',
 'original_shape_guard':{'min_ratio':.25,'max_ratio':3,'denominator':'Original immutable Basis edge lengths; conservative diagnostic, not artistic volume acceptance.'},
 'functional_gate':'Original5pads each>=3pointswithin2mm; unknowninside0; actualself/swordtransverse0; degenerates0; sampledmaxpenetration<=1mm; independentgrayshapeacceptance.',
 'corrective_neutral':'value0 restores source Basis; samebonepose keyon/off regionoutside and203thumb havezeroextraoffset.',
 'activation':'Explicit baked morph weights with grip controls, no Blender-only driver claim. Frame1open,value0; frame31firstrequiredgrasp,value1; frames31-61heldgrasp; no moving establishment time after failure.',
 'interval':{'fps':60,'frames':[1,61],'contact_required_frames':[31,61],'supplemental_half_frames':True,'rigid_weapon_follow_hand_required':True,'no_perframe_weapon_sliding':True},
 'coordinate_gate':'World vertex and world transformed swordbone head/tail; legacygate identity only; new framed wrapper preserves unchanged thresholds.',
 'required_views':['palm','side','back'],'wireframe_and_pad_normal_review_required':True,
 'verification':'SameID fresh BLEND and freshGLB skin/morph/weapon sampling; preserves original full300spec as outstanding, localPASS never wholePASS.',
 'API_new_submissions':0,'candidate_limit':4,'budget':clock['budget'],'older_clocks_and_results_preserved':True}
assert not set(contract['thumb_protected_ids']) & set().union(*map(set,contract['corrective_body_domains'].values()))
save(QA/'local-contract.json',contract)
trial=copy.deepcopy(read(OLD/'quality-ledger.json')['trials'][0])
trial.update(started_utc=clock['baseline_started_utc'],ended_utc=now.isoformat(),elapsed_seconds=(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),reviewer='Coordinator fresh full views, unchanged baseline content, fixed whole-grasp audit')
trial['previews']={n:artifact(QA/'baseline'/f'{n}.png') for n in request['quality']['protocol']['views']}
whole=read(QA/'baseline/whole-baseline.json');evidence=trial['evidence']
evidence.update(request_id=request['id'],request_sha256=workbench.request_sha256(request),deliverables=whole['artifacts'],subject_artifacts=whole['artifacts'],local_gate_contract=artifact(QA/'local-contract.json'))
evidence.pop('quality_ledger',None)
for r in evidence['checks'].values():r['artifacts'] += [artifact(QA/'baseline/whole-baseline.json'),artifact(QA/'baseline/local-baseline.json')]
ledger={'schema_version':1,'request_id':request['id'],'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'local_gate_contract':artifact(QA/'local-contract.json'),'trials':[trial],'phase_history':request['phase_history']}
comparison=workbench.compare_quality(request,ledger,ROOT);assert not comparison['blockers'],comparison
save(QA/'quality-ledger.json',ledger);save(QA/'comparison-baseline.json',comparison)
pose=copy.deepcopy(read(OLD/'v004-collision-constraints/result.json'))
controls=copy.deepcopy(pose['controls'])
controls['finger2'][1]+=.04;controls['finger2'][2]+=.04
controls['finger4'][0]-=.015;controls['finger4'][1]+=.04;controls['finger4'][2]+=.08
save(QA/'v001-start.json',{'id':'v001','started_utc':now.isoformat(),'source':clock['local_source'],'contract':artifact(QA/'local-contract.json'),
 'hypothesis':'Authored distal curl distribution increases ring/index pulp wrapping while preserving opposed thumb and rest of safe grasp.',
 'change':'Only explicit ring/index joint rotation, same original Basis/skin/UV/weapon position; no shape key or automatic search.',
 'controls':controls,'splays':pose['splays'],'weapon_shift':pose['weapon_shift'],'previous_candidates_used':0,'new_credits':0})
print('R010_CONTRACT_AND_AUTHORED_CONTROL_CANDIDATE_REGISTERED')
