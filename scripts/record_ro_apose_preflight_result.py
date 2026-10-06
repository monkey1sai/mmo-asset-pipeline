"""Close the one failed local candidate honestly; preserve clocks and artifacts."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import workbench
ROOT=Path(__file__).resolve().parents[1];ID='ro-swordsman-combo-r003';QA=ROOT/'runs/qa'/ID;V=QA/'v001';OUT=ROOT/'assets/processed'/ID/'v001'
def artifact(relative):
    p=(ROOT/relative).resolve(strict=True);assert p.is_relative_to(ROOT)
    return {'path':relative,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(path,value):
    assert not path.exists(),'Preserve old record'
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
request=workbench.read_json(ROOT/'requests'/f'{ID}.json');ledger=workbench.read_json(QA/'quality-ledger.json')
assert len(ledger['trials'])==1 and ledger['trials'][0]['id']=='baseline'
review=workbench.read_json(V/'independent-review.json');fresh=workbench.read_json(V/'preflight-fresh-import.json')
assert review['decision']=='NO_SHIP' and fresh['animation_count']==0
models=[artifact(f'assets/processed/{ID}/v001/{name}') for name in ['ro_swordsman_preflight_final.blend','ro_swordsman_preflight_final.glb']]
assert models[1]['sha256']==review['verified_technical_scope']['character_glb_sha256']==fresh['subject_sha256']
readme='''# RO劍士第三階段：失敗預檢包

狀態 NO-SHIP，不是完整連段交付。原始來源保留於 assets/raw/ro-swordsman-combo/rodin-v002。
本檔為可編輯46骨架的Blender預檢master，以及39,946三角面、1skin、3張內嵌2K貼圖的GLB。
Blender以+Z上/-Y前，GLB以+Y上/+Z前；角色bind名義身高1.74m，地面中心root。
直劍掛sword骨與hand.R，左右衣擺coat.L/R、前襟tabard；GLB是rest骨架、沒有動畫channel。

尚未完成300幀60fps5秒連段、技能效果及姿勢動畫匯出回讀。不得標示animation-ready或game_ready。
手掌／拇指／腕部與硬甲保形預檢失敗，原8條非流形邊仍在；品質分數3/3/2/3/2/0，目標各4。
保留每次失敗master、視圖、接觸／拉伸診斷及原baseline/v001時鐘。頂點座標與UV保留不等於功能通過。
參考由使用者提供，背面／不可見部位為設計推定；原作商業使用權未驗證。未指定遊戲引擎。
commit/push等待使用者驗證；不將本失敗包複製到accepted deliveries。
'''
assert not (OUT/'README.md').exists();(OUT/'README.md').write_text(readme,encoding='utf-8')
reports=[artifact(f'runs/qa/{ID}/v001/{name}') for name in ['independent-review.json','preflight-fresh-import.json','final-preflight-report.json','hand-region-restoration.json','continuous-base-report.json','paired-reach-report.json','grip-frame-probe/report.json']]
methods={
    'art_match':'Actual independent28-view review scores3/3/2/3/2/0 below all4 targets; form regresses from baseline3 to2.',
    'scale_pivot':'Body fresh bind bounds verify nominal1.74m and ground numerical epsilon; full weapon/posed pivot and grip acceptance remains incomplete, no blanket scale/pivot PASS.',
    'geometry_materials':'Actual8 source nonmanifold edges and malformed wrist/armor surfaces remain; threeembedded2K textures/39946tri alone are inventory.',
    'rig_mapping':'46named bones/1skin and finite normalized weights observed in fresh import; functional hand/armor mapping fails actual stress poses.',
    'deformation':'Actual wrist/thumb/palm volume collapse and soft armor folds remain; repairing long spikes/tabard does not close this check.',
    'animation':'GLB actual0animations; requested continuous300frames60fps5s not authored after preflight rejection.',
    'export-roundtrip':'Actual static rig/texture fresh import done; posed/continuous-animation preservation cannot pass without the required animation.',
    'skill-effects':'Requested separateBash/Magnum/Endure effects absent; not authored to hide failed deformation.',
    'package_complete':'Local failed preflight master/glb/README saved; requested complete character+continuous animation+effects package absent.'}
checks={c['id']:{'status':'fail','method':methods.get(c['id'],'Full requested check incomplete/failed; independent actual preflight report.'),'artifacts':reports} for c in workbench.required_checks(request)}
evidence={'schema_version':1,'request_id':ID,'request_sha256':workbench.request_sha256(request),'checks':checks,'subject_artifacts':models,'deliverables':models+[artifact(f'assets/processed/{ID}/v001/README.md')]}
start=workbench.read_json(QA/'v001-start.json');end=datetime.now(timezone.utc)
trial={**start,'status':'completed','ended_utc':end.isoformat(),'elapsed_seconds':(end-datetime.fromisoformat(start['started_utc'])).total_seconds(),
       'protocol_sha256':workbench.quality_sha256(request),'reviewer':review['reviewer'],'scores':review['scores'],
       'previews':{v:artifact(f'runs/qa/{ID}/v001/final-views/{v}.png') for v in request['quality']['protocol']['views']},'evidence':evidence,
       'intra_trial_attempts':['original_uv_mask_failed','smooth_cloth_envelope_thumb_capture_failed','restore9native_hand_vertices','continuous_leg_boot_pelvis_transitions','tabard_motion_probe','grip_frame_and_thumb_probe','paired_reach_and_forward_elbow_poles','final_actual_preflight_NO_SHIP']}
ledger['trials'].append(trial);comparison=workbench.compare_quality(request,ledger)
assert not comparison['blockers'],comparison
assert comparison['trials'][-1]['decision']=='discard' and comparison['next_action']=='stop_budget',comparison
save(V/'evidence.json',evidence);save(QA/'quality-ledger-baseline-preserved.json',workbench.read_json(QA/'quality-ledger.json'))
(QA/'quality-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(QA/'comparison-final.json',comparison)
evidence['quality_ledger']=artifact(f'runs/qa/{ID}/quality-ledger.json');save(V/'delivery-review-evidence.json',evidence);save(QA/'assessment-final.json',workbench.assess(request,evidence))
save(V/'manifest.json',{'status':'failed_preflight_not_delivery','request_sha256':workbench.request_sha256(request),'files':evidence['deliverables'],'source_operation':'ro-swordsman-apose-20261002-001','no_new_paid_job':True,'git':'not_staged_not_committed_not_pushed'})
print(json.dumps(comparison,ensure_ascii=False));print('NO_SHIP; failed single trial and original clocks preserved')
