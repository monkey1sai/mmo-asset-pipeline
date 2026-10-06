"""Persist truthful failure evidence; never fabricate a completed quality trial."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo'
request=workbench.read_json(ROOT/'requests/ro-swordsman-combo.json')
def artifact(relative):
    path=(ROOT/relative).resolve(strict=True)
    if ROOT not in path.parents:raise ValueError('Artifact outside worktree')
    return {'path':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def save(relative,obj):
    (ROOT/relative).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
digest=workbench.request_sha256(request);protocol=workbench.quality_sha256(request)
ledger={'schema_version':1,'request_id':request['id'],'request_sha256':digest,'protocol_sha256':protocol,
        'trials':[], 'status':'blocked',
        'note':'No valid fully-reviewed baseline was recorded before revisions. Do not invent elapsed_seconds, scores or parent-best history. Actual three revisions remain spent; empty trials do not reset production budget.',
        'production_attempts':[{'id':v,'role':'baseline diagnostic' if i==0 else 'revision diagnostic','construction_report':artifact(f'runs/qa/ro-swordsman-combo/{v}/construction-check.json'),'numeric_roundtrip':artifact(f'runs/qa/ro-swordsman-combo/{v}/roundtrip-check.json'),'full_elapsed_accounting':'not_recorded','completed_quality_trial':False} for i,v in enumerate(['v001','v002','v003','v004'])],
        'actual_revision_usage':{'used':3,'limit':3,'remaining':0,'source':'Preserved baseline v001 and diagnostic revisions v002/v003/v004; API candidate included in last revision.'}}
save('runs/qa/ro-swordsman-combo/quality-ledger-blocked.json',ledger)
review_path='runs/qa/ro-swordsman-combo/independent-review-v004.md'
review='''# v004 獨立唯讀審查：不接受

審查者：本任務 quality_review 子任務。實際查看固定五視角及12張姿勢，讀取構建、roundtrip、API授權與下載證據；未修改檔、未外部API重查、未觀看全部300幀。

觀察：正／側面已出現肩肘放射狀補面與跨身體長三角片；腰間仍有原手／握柄，原鞘和新增直條並存。抬劍時切口與扇形拉扯放大，旋轉時有碎片、握持混亂及衣襬鋸齒切口。前襟只有局部白色，臉部眼形仍不清楚。

依凍結0–5錨點，design-intent=2、silhouette=2、form-proportion=1、materials=2、craft=1、use-readability=0；每項目標4，不能平均抵銷。不把17張圖評分當作全段PASS。

建議：淘汰選用v004但保留檔案和已花費修訂。後續需先語義拆件、移除原姿態殘留、補遮蔽表面及關節面流，甲片有剛性控制。中性姿態的抬臂／雙手下劈／深蹲落地先通過，再做連段與效果。任意切口中心封面和0非流形不足以證明可動畫。

結論：art_match與deformation失敗；必要效果未完成，三次修訂用完，conditional commit／push main尚不成立。數值重匯入、服務Done、下載hash及工具測試都不取代藝術驗收。
'''
(ROOT/review_path).write_text(review,encoding='utf-8')
review_artifact=artifact(review_path)
construction=artifact('runs/qa/ro-swordsman-combo/v004/construction-check.json')
roundtrip=artifact('runs/qa/ro-swordsman-combo/v004/roundtrip-check.json')
full=artifact('runs/qa/ro-swordsman-combo/v004/full-animation-stress.json')
video=artifact('runs/qa/ro-swordsman-combo/v004/continuous-neutral-failed.mp4')
checks={
 'art_match':{'status':'fail','method':'Coordinator and independent reviewer observed five fixed views and 12 key poses; six scores below4; see exact failures','artifacts':[review_artifact]},
 'scale_pivot':{'status':'not_run','method':'Bind normalization applied to1.74m; full contractual motion envelope/pivot acceptance not completed','artifacts':[construction,full]},
 'geometry_materials':{'status':'fail','method':'33096tri and numeric manifold check pass, but photographed material regions, reconstructed surfaces and visible intersections fail','artifacts':[construction,review_artifact]},
 'package_complete':{'status':'not_run','method':'Candidate files exist; no accepted delivery package or library delivered status','artifacts':[]},
 'rig_mapping':{'status':'fail','method':'25bones, skin and normalized weights exist; visible body/hand/sword surface correspondence and intended grip are incorrect','artifacts':[roundtrip,review_artifact]},
 'deformation':{'status':'fail','method':'Actual overhead sword, impact and turn poses exhibit large stretched surfaces and residual fused geometry','artifacts':[review_artifact,video]},
 'animation':{'status':'fail','method':'Rendered all300 true3D frames to five-second60fps video; sampled visible skills/transition poses fail bodily integrity and grip. Rendering is not a claim every frame was visually reviewed','artifacts':[full,video,review_artifact]},
 'export-roundtrip':{'status':'not_run','method':'Clean GLB numeric roundtrip passes; full materials/visual/deformation roundtrip acceptance deliberately not asserted','artifacts':[roundtrip]},
 'skill-effects':{'status':'fail','method':'Saved construction explicitly reports skill_effects not_done; required slash/fire/endure layers absent, not hidden by VFX','artifacts':[construction]}}
deliverables=[artifact(f'assets/processed/ro-swordsman-combo/v004/{name}') for name in ['ro_swordsman_combo.glb','ro_swordsman_master.blend']]
evidence={'schema_version':1,'request_id':request['id'],'request_sha256':digest,'checks':checks,'deliverables':deliverables,'subject_artifacts':deliverables,'quality_ledger':artifact('runs/qa/ro-swordsman-combo/quality-ledger-blocked.json'),'note':'Actual failed candidate subjects, not accepted delivery; hashes alone do not establish quality.'}
save('runs/qa/ro-swordsman-combo/v004-failed-evidence.json',evidence)
comparison=workbench.compare_quality(request,ledger)
assessment=workbench.assess(request,evidence)
save('runs/qa/ro-swordsman-combo/quality-compare-blocked.json',comparison)
save('runs/qa/ro-swordsman-combo/assessment-not-ready.json',assessment)
print(json.dumps({'comparison':comparison['next_action'],'assessment':assessment['decision'],'actual_revision_usage':ledger['actual_revision_usage'],'blockers':assessment['blockers']},ensure_ascii=False,indent=2))
