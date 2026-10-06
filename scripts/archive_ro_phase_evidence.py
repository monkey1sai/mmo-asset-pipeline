"""Local traceable archive/index; no delivered state or Git mutation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r002'
def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=workbench.read_json(ROOT/'library/index.json')
entry_id='ro-swordsman-combo-r002-v003'
if not any(x['id']==entry_id for x in index['entries']):
    index['entries'].append({'id':entry_id,'asset_id':'ro-swordsman-combo','name':'RO 劍士連段壓力測試失敗候選','project':None,'version':'r002-v003','tags':['RO','劍士','character','rig','combo','stress-test'],'status':'needs_revision','acceptance':{'art':'failed','technical':'diagnostics_partial_failed','target_environment':'not_requested','delivery':'not_delivered'},'files':['assets/processed/ro-swordsman-combo-r002/v003/ro_swordsman_master.blend','assets/processed/ro-swordsman-combo-r002/v003/ro_swordsman_combo.glb','assets/processed/ro-swordsman-combo-r002/v003/ro_skill_effects.glb'],'provenance':{'operation_id':'ro-swordsman-reference-20261002-001','generation_id':'7120b25b-c2af-4393-b0b0-0bbc809fc11a','record':'runs/qa/ro-swordsman-combo-r002/quality-ledger.json'},'qa_report':'runs/qa/ro-swordsman-combo-r002/assessment-final.json','open_issues':['勝利站姿浮地','支撐腳滑動','握持轉折突變','匯出肘甲差異','造型比例與效果未達標']})
    save(ROOT/'library/index.json',index)
files=[]
for relative in ['assets/raw/ro-swordsman-combo/design-v002','assets/processed/ro-swordsman-combo-r002','runs/qa/ro-swordsman-combo-r002','runs/qa/ro-swordsman-combo-r003']:
    folder=ROOT/relative
    for p in sorted(folder.rglob('*')):
        if p.is_file() and p.name!='archive-manifest.json':files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
save(QA/'archive-manifest.json',{'schema_version':1,'saved_utc':datetime.now(timezone.utc).isoformat(),'status':'local_failed_review_and_new_design_preparation','files':files,'file_count':len(files),'bytes':sum(f['bytes'] for f in files),'current_phase':'r002 v003 discarded; no fourth local revision','next_phase':'r003 input prepared; old API refused path before submit; new user-selected API entrypoint awaited','paid_cost_this_phase':0,'earlier_raw_cost':.5,'github':'not_staged_not_committed_not_pushed','lfs':'No new pointers/objects/remote sync claimed; all media currently local files','background':'none'})
print(json.dumps({'archive_files':len(files),'archive_bytes':sum(f['bytes'] for f in files),'status':'NO_SHIP'},ensure_ascii=False))
