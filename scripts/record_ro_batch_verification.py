"""Read-only integrity checks and public handoff evidence; no network/private reads."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005'
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')

operation = read(ROOT/'runs/hyper3d/operations/ro-split-batch-20261003-001.json')
assert operation['state'] == 'downloaded' and operation['consumed_credits']==.5
for item in operation['downloads']:
    assert sha(ROOT/item['path']) == item['sha256']
for relative in ['baseline/assembly.json','source-parts/extraction.json','v001-rig-seams/preflight.json']:
    for item in read(QA/relative)['artifacts']:
        assert sha(ROOT/item['path']) == item['sha256']
request = read(ROOT/'requests/ro-swordsman-combo-r005.json')
comparison = workbench.compare_quality(request,read(QA/'quality-ledger.json'))
assert not comparison['blockers'] and not comparison['quality_target_met']
assert comparison['candidate_trials_used']==1 and comparison['best_trial_id']=='baseline'
index = read(ROOT/'library/index.json')
entry = next(e for e in index['entries'] if e['id']=='ro-swordsman-combo-r005-v001')
assert entry['acceptance']['delivery']=='not_delivered'
assert all((ROOT/p).is_file() for p in entry['files'])
assert entry in workbench.search_library(index,'RO')
plan = Client(ROOT).plan('ro-core-fallback-20261003-001')
assert not Client(ROOT).record_path(plan['operation_id']).exists()
assert not Client(ROOT).private_path(plan['operation_id']).exists()
scripts = ['extract_ro_batch_parts.py','assemble_ro_batch_baseline.py','record_ro_batch_baseline.py',
    'fit_ro_batch_candidate.py','probe_ro_equipment_fit.py','tailor_ro_batch_fit.py','rig_ro_batch_preflight.py',
    'check_ro_batch_roundtrip.py','finish_ro_batch_experiment.py','record_ro_batch_verification.py']
for name in scripts:
    ast.parse((ROOT/'scripts'/name).read_text(encoding='utf-8'))
assert sha(ROOT/'scripts/hyper3d_api.py') == sha(Path(r'C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py'))
provider = Path(r'C:\Users\IOT\.codex\tools\hyper3d-api\rodin_api.py')
policy = Path(r'C:\Users\IOT\.codex\tools\hyper3d-api\authorization.json')
assert sha(provider)=='45247a8def85815d03bb296767aec5f79699a518489f2e68bddad3ff39b09e3a'
assert sha(policy)=='431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10'
base = Path(r'C:\Users\IOT\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\.local\lib\python3.11\site-packages')
extension_state = [{'path':str(base/name),'directory_exists':(base/name).is_dir(),
                    'init_py_exists':(base/name/'__init__.py').is_file()} for name in ['aiohttp','yarl','multidict']]
save(QA/'extension-readonly-observation.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),
    'method':'Path existence only; no content, secret or writes', 'modules':extension_state,
    'before_inventory_available':False,'global_repair_performed':False,
    'conclusion':'Paths currently absent. Full prior-to-current change extent remains unverified.'})
result = {'observed_utc':datetime.now(timezone.utc).isoformat(),
    'integrity_verified':['all3raw_downloads','source_parts','frozen_baseline','current_rig_preflight','API provider/old authorization unchanged'],
    'syntax_checked':scripts,'library_entry':'needs_revision/not_delivered',
    'quality_comparison':comparison,'unit_test_run':'116 tests passed in1.885s, actual current-turn command',
    'existing_pipeline_validation':'valid39assets; schema only','git_diff_check':'passed actual current-turn command',
    'fallback_plan_sha256':plan['plan_sha256'],'fallback_state':'prepared_not_submitted, exact global file authority pending',
    'static_roundtrip':read(QA/'v001-glb-roundtrip/roundtrip.json'),
    'art_verdict':'NO_SHIP','full_animation_verified':False,'effects_verified':False,
    'environment_event':'Unexpected global extension cleanup observed; partial change extent unverified; no repair.',
    'stage_commit_push':'held by user','task_owned_background_work':'none'}
save(QA/'verification.json',result)
print(json.dumps({'integrity':'pass','syntax_files':len(scripts),'library_entry':entry['id'],
                  'fallback_submitted':False,'art_verdict':'NO_SHIP','candidate_trials_used':1,'remaining_revisions':2},ensure_ascii=False))
