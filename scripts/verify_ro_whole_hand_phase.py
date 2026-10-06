"""Validate closed r009 records and preservation; never infer artistic PASS."""
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import workbench
QA=ROOT/'runs/qa/ro-swordsman-combo-r009'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def artifacts(value):
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:yield value
        for row in value.values():yield from artifacts(row)
    elif isinstance(value,list):
        for row in value:yield from artifacts(row)
request=read(ROOT/'requests/ro-swordsman-combo-r009.json');assert not workbench.validate_request(request)
clock=read(QA/'phase-start.json');ledger=read(QA/'quality-ledger.json');account=read(QA/'phase-accounting-final.json')
compare=workbench.compare_quality(request,ledger,ROOT);assessment=workbench.assess(request,read(QA/'evidence-final.json'),ROOT)
assert compare==read(QA/'comparison-final.json') and not compare['blockers'] and compare['next_action']=='stop_budget' and compare['candidate_trials_used']==4
assert not compare['quality_target_met'] and assessment['decision']=='not_ready'
assert [row['id'] for row in ledger['trials']]==['baseline','v001','v002','v003','v004'] and all(row['status']=='failed' for row in ledger['trials'][1:])
checked=set();failures=[];json_paths=sorted(QA.rglob('*.json'))
for path in json_paths:
    for item in artifacts(read(path)):
        key=(item['path'],item['sha256'])
        if key in checked:continue
        target=(ROOT/item['path']).resolve();assert target.is_relative_to(ROOT.resolve())
        checked.add(key)
        if not target.is_file() or sha(target)!=item['sha256']:failures.append({'record':path.relative_to(ROOT).as_posix(),**item})
assert not failures,failures
for item in clock['protected_history']:assert sha(ROOT/item['path'])==item['sha256']
python_paths=sorted((ROOT/'scripts').glob('*.py'))+sorted((ROOT/'tests').glob('*.py'))
for path in python_paths:ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
entry=next(row for row in read(ROOT/'library/index.json')['entries'] if row['id']=='ro-swordsman-combo-r009-v004')
assert entry['status']=='needs_revision' and entry['acceptance']['delivery']=='not_delivered'
for path in entry['files']+[entry['qa_report'],entry['provenance']['record']]:assert (ROOT/path).is_file()
totals=[]
for folder in ['v002-coupled-IK','v003-moving-target','v004-collision-constraints']:
    result=read(QA/folder/'result.json');events=[json.loads(line) for line in (QA/folder/'evaluations.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(events)==result['actual_evaluations'] and [e['index'] for e in events]==list(range(len(events)))
    full=sum(e['collision_test']=='actual_full' for e in events);assert full==result['full_tested_proposals']
    totals.append((len(events),full,len(events)-full))
assert [sum(row[i] for row in totals) for i in range(3)]==[205,23,182]
fresh=read(QA/'fresh-saved-verification.json');assert fresh['posed_points_within_tolerance'] and fresh['max_saved_fresh_point_delta_m']==0 and fresh['rms_saved_fresh_point_delta_m']==0
assert not fresh['function_gate'] and {n:r['within_2mm'] for n,r in fresh['contact']['pad_contacts'].items()}=={'finger1':3,'finger2':1,'finger3':3,'finger4':0,'thumb':3}
assert fresh['self']['transverse_pairs']==fresh['contact']['transverse_crossings_count']==0
tests=(QA/'unit-tests.log').read_text(encoding='utf-8');assert 'Ran 122 tests' in tests and tests.rstrip().endswith('OK')
pipeline=read(QA/'pipeline-validate.log');assert pipeline['status']=='valid' and pipeline['assets']==39
heads={'worktree':git(ROOT,'rev-parse','HEAD'),'main':git(Path('C:/Repos/mmo-asset-pipeline'),'rev-parse','HEAD')}
assert heads=={'worktree':'c990639962b7ce85eb6beb631057aa4d76a3e86d','main':'e077e22ba57447031b7cc89e3d37bd9cef47daf4'}
assert not git(ROOT,'diff','--cached','--name-only') and not git(Path('C:/Repos/mmo-asset-pipeline'),'diff','--cached','--name-only');git(ROOT,'diff','--check')
report={'observed_utc':datetime.now(timezone.utc).isoformat(),'status':'verified_closed_NO_SHIP','request_schema_valid':True,
 'comparison':{'candidates':4,'next_action':'stop_budget','quality_target_met':False},'assessment':'not_ready',
 'artifact_references_checked':len(checked),'hash_failures':failures,'qa_json_parsed':len(json_paths),'python_sources_syntax_checked':len(python_paths),
 'protected_history_files':len(clock['protected_history']),'protected_history_unchanged':True,'library_entry':entry['id'],'library_delivery':'not_delivered',
 'solver_probes':205,'full_function_proposals':23,'derivative_base_preflight_not_functionchecked':182,
 'fresh_saved_point_count':904,'max_saved_fresh_point_delta_m':0.0,'rms_saved_fresh_point_delta_m':0.0,'fresh_point_tolerance_m':1e-6,
 'fresh_function_gate':False,'fresh_fixed_contacts':[3,1,3,0,3],'unit_tests':122,'unit_tests_log_sha256':sha(QA/'unit-tests.log'),
 'pipeline_assets_schema_valid':39,'pipeline_log_sha256':sha(QA/'pipeline-validate.log'),'freshness_runtime_not_verified':True,
 'phase_wall_seconds_at_close':account['phase_wall_seconds_at_close'],'postclose_documentation_verification_wall_seconds':(datetime.now(timezone.utc)-datetime.fromisoformat(account['phase_closed_utc'])).total_seconds(),
 'earliest_preclock_preparation_unmeasured':True,'git_heads':heads,'staged_paths':[],'stage_commit_push':'held_by_user',
 'r009_new_API_submissions':0,'r009_new_service_credits':0,'no_API_balance_query':True,'repo_external_writes':'none',
 'document_artifacts':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in [ROOT/'library/index.json',ROOT/'docs/art-quality-loop.md',ROOT/'assets/processed/ro-swordsman-combo-r009/README.md',QA/'README.md',QA/'planning-review.md']]}
with (QA/'final-verification.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ['status','artifact_references_checked','qa_json_parsed','python_sources_syntax_checked','protected_history_files','unit_tests','solver_probes','full_function_proposals','assessment']}))
