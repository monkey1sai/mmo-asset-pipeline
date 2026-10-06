"""Freeze r007's new method/input; prepare one native-OBJ API operation only."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
ID = 'ro-swordsman-combo-r007'
QA = ROOT / 'runs/qa' / ID
OP = 'ro-hand-structure-20261003-001'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def artifact(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


start = read(QA / 'preparation-start.json')
measure = read(QA / 'assembly-measurements.json')
assert measure['whole_character_and_sword_triangles'] == 57039
assert not (ROOT / 'requests' / (ID+'.json')).exists()
old = read(ROOT / 'requests/ro-swordsman-combo-r006.json')
request = deepcopy(old)
request.update(id=ID, title='RO 劍士：掌根面流先驗與貼身腕部配裝的新方法', brief='同意 — 接續新掌腕造型、動畫面流與護腕配裝方法；保留歷史，API按需授權沿用，commit/push等驗證。')
request['provenance']['reference'] = f'requests/{ID}.json#brief'
request['production'] = {'route':'split_then_generate', 'max_revisions':4,
    'reuse_candidates':['ro-swordsman-combo-r006-v008','ro-swordsman-combo-r006-hand-source'],
    'reason':'New worn-hand exterior removes hollow double cuff; validate actual anatomy/native topology and joint centers before rigging. Existing rigid armor and duplicate core volume are diagnosed separately; no repeat of large sleeve/contact corrective patches.'}
request['assumptions'] = [
    start['user_authority'], 'r006 remains closed at8/8; this is a prospectively recorded materially different method, not reopening or renaming an old trial.',
    'Four candidate revisions,6h each/48h phase are local experimental bounds, not API credit limits. A candidate may include source generation and required dependent DCC work; four candidates are not four prepaid random generations.',
    'New phase baseline uses failed v008 as an explicit diagnostic specimen; it was never adopted as the accepted r006 master.',
    'Spec and six quality dimensions remain unchanged; partial hand success cannot establish complete300frames/60fps, left-hand, VFX or delivery acceptance.',
    'Source aims wrist-to-middle-tip185mm, palm width75mm, wrist50x40mm and short forearm80mm ending55x55mm; design measurements, not facts about the generated geometry. Existing bracer first-ray hits at60..120mm proximal measure31..33mm; ray coverage is not free-space/animation PASS.',
    'API OBJ is requested to preserve native polygon evidence. Native quads alone do not certify animation flow. Keep raw OBJ/materials/textures and inspect actual output before rigging.',
    'Whole model budget uses both hands. Approximate baseline remainder after right glove/tube2742tri and prior left-hand537tri is53760; with256tri seam reserve,5984tri remain for both replacement hands. Left removal estimate is historical, not actual r007 cutting.',
    'If anatomy or bend topology needs substantial rebuilding, stop direct rigging and record required redesign/retopology cost; never call it minor polishing.',
    'Source and evaluated topology mappings must be explicit. No posed-position welding to decide semantic adjacency; retain actual evaluated loop triangles and crossing locations.',
    'Only the prepared new task recovery file needs additional exact repo-external authority. Do not overwrite old operations/state or change credentials/global controls.',
]
images = [artifact(ROOT/'assets/raw/ro-swordsman-combo/design-v007'/name) for name in ['right-hand-palm.png','right-hand-back.png']]
request['quality']['reference_artifacts'].extend(images)
request['phase_history'] = {
    'previous_request':'requests/ro-swordsman-combo-r006.json', 'previous_request_sha256':workbench.request_sha256(old),
    'previous_result':start['previous_comparison']['path'], 'previous_result_sha256':start['previous_comparison']['sha256'],
    'previous_revisions':8, 'previous_phase_seconds':start['prior_history']['phase_wall_seconds_including_waiting_and_candidateQA'],
    'previous_phase_service_reported_credits':.5, 'r005_plus_r006_service_reported_credits':1.5,
    'r005_accounting':'runs/qa/ro-swordsman-combo-r005/phase-accounting-final.json',
    'r006_accounting':'runs/qa/ro-swordsman-combo-r006/phase-accounting-final.json',
    'authority':request['brief'], 'new_method':start['new_method'], 'old_phase_reopened':False,'quality_targets_lowered':False,
}
assert request['spec'] == old['spec'] and request['quality']['dimensions'] == old['quality']['dimensions']
save(ROOT/'requests'/(ID+'.json'),request)
contract = read(ROOT/'runs/qa/ro-swordsman-combo-r006/hand-gate-contract.json')
contract['request_id'] = ID
contract['anatomy_topology']['source_gate'] = 'Worn-hand single exterior; actual thenar/opposition, webs, wrist section; native OBJ polygons plus actual evaluated topology. No inner cuff pair or balloon sleeve. Validate before rigging.'
contract['anatomy_topology']['self_intersection_protocol'] = 'Use one evaluated mesh positions+loop_triangles. Adjacency/UV duplicate identity from fixed rest topology and stable original-point attribute mapping; never weld posed coordinates. Separate transverse, coplanar/tangential and exclusions; zero is not complete absence proof.'
contract['rig']['skeleton_before_binding'] = 'Locate actual MCP/PIP/DIP, thumb opposition base+MCP/IP and wrist pivot within the new3D volume; verify each joint direction by actual vertex motion before grasp.'
contract['budget']['baseline_latest_triangles'] = 57039
contract['budget']['replaceable_right_glove_plus_tube'] = 2742
contract['budget']['estimated_left_old_hand'] = 537
contract['budget']['planning_both_new_hands_after_seam_reserve'] = 5984
contract['budget']['per_hand_without_other_reduction'] = 2992
contract['budget']['equation'] = 'Measure both actual removals, both new hand/forearm skins and seams; total character+sword<=60000. No historical removal estimate counts as an executed cut.'
contract['source_design'] = {'wrist_to_middle_tip_m':.185,'palm_width_m':.075,'wrist_width_depth_m':[.050,.040],
    'forearm_coverage_m':.080,'proximal_width_depth_m':[.055,.055], 'source_near_end':'Truncated proximal exterior is a disposable source cap; do not bind its cap as a sleeve seam',
    'assembly_measurements':artifact(QA/'assembly-measurements.json'),'dimensions_are_design_not_generated_measurement':True}
contract['stop_old_method'] = 'Do not use the old nearest-pad projection or20mm wrist corrective/40mm core shrink as a generic remedy. Any substantial change triggers source/topology method adjudication with cost, actual mesh readback and no budget reset.'
contract['acceptance'] = 'All source, right-hand motion, contact, deformation, fitting/visual/material gates pass before left/full300frame/VFX expansion. Whole request targets remain required.'
save(QA/'hand-gate-contract.json',contract)
save(QA/'phase-start.json',{'baseline_started_utc':start['planning_started_utc'], 'clock_scope':'Prospective from first r007 planning registration, includes measurements/design/review/baseline and later production; no old clock reset',
    'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),
    'budget':request['quality']['budget'],'max_revisions':4,'baseline_source':start['baseline_source'],
    'prior_phase_history':request['phase_history'],'local_contract':artifact(QA/'hand-gate-contract.json')})
save(QA/'offline-plan.json',workbench.production_plan(request))
spec = {'operation_id':OP,'request':f'requests/{ID}.json','images':[i['path'] for i in images],
    'output_directory':'assets/raw/ro-swordsman-combo/rodin-v007/right-hand',
    'parameters':{'tier':'Gen-2.5-High','mesh_mode':'Quad','quality_override':1200,'quad_normal':True,
        'geometry_file_format':'obj','material':'PBR','texture_mode':'high','texture_delight':True,
        'TAPose':False,'is_symmetric':'asymmetric','image_label':['F','B'],'seed':4701,'preview_render':True},
    'authorization':{'spending_scope':'Existing explicit demand-driven monthly/regular API authority; human agrees new anatomy/topology-first method. Exact new recovery file authority still pending; no top-up/upgrade or Git mutation.',
        'credit_pool':'existing_monthly_or_regular','no_topup_or_upgrade':True}}
save(QA/'api-spec-hand-structure.json',spec)
client = Client(ROOT)
client.prepare(spec)
plan = client.plan(OP)
assert not client.private_path(OP).exists() and not client.record_path(OP).exists()
save(QA/'generation-prepared.json',{'operation_id':OP,'state':'prepared_not_submitted','plan_sha256':plan['plan_sha256'],
    'estimated_credits':plan['estimated_credits'],'inputs':images,'global_task_file':str(client.private_path(OP)),
    'global_file_exists_before':False,'global_file_authority':'Exact-file write authority pending; spending already authorized',
    'envelope':{'destination':'https://api.hyper3d.com/api/v2/rodin','purpose':'One anatomically fitted right-hand/short-forearm source; native topology inspection before rigging',
        'allowed_operations':['one generation','same-task status','completed native OBJ/material/texture download'],
        'data_transmitted':['two selected consistent-view design PNGs','validated nonsecret generation parameters'],
        'forbidden_operations':['top-up','upgrade','old state/history overwrite','credential output','Git mutation'],
        'stop_conditions':['missing exact-file authority','pending/unknown operation','collision','unexpected destination','source anatomy/topology/fitting fail']}})
print(json.dumps({'request':ID,'operation':OP,'estimated_credits':plan['estimated_credits'],'native_format':'obj',
                  'state_file':str(client.private_path(OP)),'submitted':False,'original_targets_preserved':True}))
