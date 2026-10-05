"""Consume a real failed candidate; retain files and prepare the next bounded one."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import workbench

ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r002'
p=argparse.ArgumentParser();p.add_argument('--version',required=True);p.add_argument('--reason',required=True);p.add_argument('--next-hypothesis');p.add_argument('--next-change');a=p.parse_args()
ledger=workbench.read_json(QA/'quality-ledger.json'); req=workbench.read_json(ROOT/'requests/ro-swordsman-combo-r002.json')
start=workbench.read_json(QA/(a.version+'-start.json')); end=datetime.now(timezone.utc)
if any(t['id']==a.version for t in ledger['trials']): raise RuntimeError('Already recorded')
trial={**start,'status':'failed','elapsed_seconds':(end-datetime.fromisoformat(start['started_utc'])).total_seconds(),'ended_utc':end.isoformat(),'protocol_sha256':workbench.quality_sha256(req),'reviewer':'Coordinator actual bind/preflight images and coordinate probe; full animation stopped before construction','failure_reason':a.reason}
ledger['trials'].append(trial); result=workbench.compare_quality(req,ledger)
if result['blockers']: raise ValueError(result['blockers'])
save=lambda path,obj:path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(QA/'quality-ledger.json',ledger);save(QA/('comparison-'+a.version+'.json'),result)
if result['next_action']=='revise_current_best':
    nxt='v%03d'%(int(a.version[1:])+1)
    save(QA/(nxt+'-start.json'),{'id':nxt,'started_utc':end.isoformat(),'parent_id':result['best_trial_id'],'hypothesis':a.next_hypothesis or 'Measured source body is offset by -0.105m because source whole-mesh bounds include diagonal scabbard; calibrating semantic centre and retaining only main connected components prevents wrong part and eye placements.', 'change':a.next_change or 'Calibrate actual body/face coordinates, restrict retained surfaces to clean main components, rebuild elbow plates and face features at measured positions.', 'before_candidate_work':True})
print(json.dumps(result,ensure_ascii=False))
