"""Freeze the user-directed redesign as a separate phase; never submit API."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1];ID='ro-swordsman-combo-r003'
request_path=ROOT/'requests'/f'{ID}.json';qa=ROOT/'runs/qa'/ID
if request_path.exists() or qa.exists():raise RuntimeError('New phase already exists; preserve it')
request=deepcopy(workbench.read_json(ROOT/'requests/ro-swordsman-combo-r002.json'))
request.update(id=ID,title='RO 劍士：清晰中性設計圖與 API 重建第三階段',brief='用Blender無法修好的動作(因為需要修的幅度太大)，改用先產生圖片、Hyper3D建模、Blender修細節；不限制現有點數，按建模需求測試API；commit、push等使用者驗證。')
request['production'].update(route='generate',reason='User-directed reconstruction after major source-pose fusion and joint rebuilding. Clear empty-hand A-pose design separates arms/torso/weapon; new raw baseline, same six quality targets. Prior failures and consumption preserved.',reuse_candidates=[],max_revisions=1)
image='assets/raw/ro-swordsman-combo/design-v002/ro_swordsman_apose.png';image_sha=hashlib.sha256((ROOT/image).read_bytes()).hexdigest()
request['quality']['reference_artifacts'].append({'path':image,'sha256':image_sha})
request['quality']['budget']={'trial_seconds':7200,'total_seconds':14400}
request['phase_history']={'original_phase':request['phase_history'],'previous_request':'requests/ro-swordsman-combo-r002.json','previous_ledger':'runs/qa/ro-swordsman-combo-r002/quality-ledger.json','status':'Final third candidate under independent review. Preserved, no remaining fourth local candidate. New user-directed API route changes source; does not erase prior trials.'}
request['assumptions']=[x for x in request['assumptions'] if 'No new paid' not in x]
request['assumptions'].extend(['One initial image-to-3D job at adapter fixed0.5 credits. Latest user permits existing monthly/regular credits and all available APIs as needed; no top-up/upgrade.','Clear frontal A-pose does not prove hidden surfaces, separate fingers, skin topology or automatic rig/animation; inspect actual result before local work.','One local refinement candidate in this new phase, after complete raw baseline; do not reset old phase budget.'])
request['provenance']={'kind':'user_brief','reference':f'requests/{ID}.json#brief'}
qa.mkdir(parents=True)
def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(request_path,request)
errors=workbench.validate_request(request)
if errors:raise RuntimeError(errors)
operation='ro-swordsman-apose-20261002-001'
save(qa/'generation-prepared.json',{'operation_id':operation,'execution_state':'prepared','request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'prepared_utc':datetime.now(timezone.utc).isoformat(),'input':{'path':image,'sha256':image_sha},'output_directory':'assets/raw/ro-swordsman-combo/rodin-v002','tool':'mcp__hyper3d_api__rodin_generate','parameters':{'authorized_credit_limit':0.5,'prompt':'Single anime swordsman exactly matching the input design. Symmetric A-pose, empty open hands completely separated from waist and torso, five distinct gloved fingers, arms45degrees down, legs apart, feet flat. No sword, no scabbard, no effects. Preserve chestnut spiky hair, open brown eyes, silver layered armor, navy split coat, ivory white tabard and brown leather boots. Clean closed 3D surfaces, natural joints; avoid fused cloth or body parts.','fixed_settings':'Gen-2.5 High/Raw30k/GLB/PBR2K'},'authorization':{'source':'User answer: 不限制點數使用；這是壓力測試，可以用api所有介面與功能，請依照建模的需求來','pool':'existing_monthly_or_regular','no_topup_or_upgrade':True,'initial_job_count':1},'envelope':{'destination':'Hyper3D authenticated user API account','purpose':'New neutral-pose character candidate for directed art stress test','allowed_operations':['upload one generated design reference','one initial0.5-credit generation','read same task status','download completed task to new raw version'],'data_transmitted':['generated A-pose design image','nonsecret character prompt'],'forbidden_operations':['topup','upgrade','expose secrets','publish','commit','push'],'stop_conditions':['unknown/pending submission without same-task reconciliation','unexpected account/destination','failed input','download collision']}})
save(qa/'phase-start.json',{'baseline_started_utc':datetime.now(timezone.utc).isoformat(),'time_accounting':'Real wall clock starts before this raw generation; candidate edit clock begins only after full baseline record; prior r002 clocks preserved.'})
save(qa/'offline-plan.json',workbench.production_plan(request))
print(json.dumps({'request':ID,'request_sha256':workbench.request_sha256(request),'protocol_sha256':workbench.quality_sha256(request),'operation_id':operation,'input_sha256':image_sha}))
