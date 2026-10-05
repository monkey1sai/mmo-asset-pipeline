"""Current closed-phase integrity/tools check; historical snapshots stay historical.

No API calls, private decryption, outside-repo writes, Blender execution or Git
mutations. Passing tools and hashes do not establish art acceptance.
"""
import ast
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys
from pathlib import Path
import workbench
from hyper3d_api import PROVIDER,PROVIDER_SHA256
ROOT=Path(__file__).resolve().parents[1];MAIN=Path(r'C:\Repos\mmo-asset-pipeline')
QA=ROOT/'runs/qa/ro-swordsman-combo-r007';destination=QA/'final-verification.json'
assert not destination.exists()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
verified={};historical=[]
snapshots={sha(p):p for p in QA.glob('quality-ledger-before-*.json')}
def check(item,evidence):
    raw=Path(item['path'])
    assert not raw.is_absolute(),('Unexpected outside artifact',evidence)
    path=(ROOT/raw).resolve();assert path.is_relative_to(ROOT) and path.is_file(),item['path']
    actual=sha(path)
    if actual!=item['sha256']:
        assert path==QA/'quality-ledger.json' and item['sha256'] in snapshots,(evidence,item['path'])
        snapshot=snapshots[item['sha256']]
        historical.append({'record':evidence,'original_mutable_path':item['path'],
            'historical_sha256':item['sha256'],'actual_preserved_snapshot':snapshot.relative_to(ROOT).as_posix(),
            'current_mutable_file_matches_historical':False})
        path=snapshot
    if 'bytes' in item:assert path.stat().st_size==item['bytes']
    key=path.relative_to(ROOT).as_posix();verified[key]={'path':key,'sha256':sha(path),'bytes':path.stat().st_size}
def walk(value,evidence):
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:check(value,evidence)
        for child in value.values():walk(child,evidence)
    elif isinstance(value,list):
        for child in value:walk(child,evidence)
request=read(ROOT/'requests/ro-swordsman-combo-r007.json');old=read(ROOT/'requests/ro-swordsman-combo-r006.json')
clock=read(QA/'phase-start.json');ledger=read(QA/'quality-ledger.json');accounting=read(QA/'phase-accounting-final.json')
assert request['spec']==old['spec'] and request['quality']['dimensions']==old['quality']['dimensions']
assert workbench.request_sha256(request)==clock['request_sha256']
assert workbench.quality_sha256(request)==clock['protocol_sha256']
assert [t['id'] for t in ledger['trials']]==['baseline','v001','v002','v003','v004']
assert all(t['status']=='failed' for t in ledger['trials'][1:])
assert ledger['trials'][0]['scores']==read(QA/'quality-ledger-before-v001.json')['trials'][0]['scores']
comparison=workbench.compare_quality(request,ledger,ROOT)
assert comparison==read(QA/'comparison-final.json') and not comparison['blockers']
assert comparison['candidate_trials_used']==4 and comparison['next_action']=='stop_budget'
assert not comparison['quality_target_met'] and comparison['best_trial_id']=='baseline'
assessment=workbench.assess(request,read(QA/'assessment-evidence-final.json'),ROOT)
assert assessment==read(QA/'assessment-final.json') and assessment['decision']=='not_ready'
assert abs(comparison['elapsed_seconds']-accounting['phase_wall_seconds_at_close'])<.001
assert ledger['trials'][0]['started_utc']==clock['baseline_started_utc']
for a,b in zip(ledger['trials'],ledger['trials'][1:]):assert a['ended_utc']==b['started_utc']
old_ledger=read(ROOT/'runs/qa/ro-swordsman-combo-r006/quality-ledger.json')
assert workbench.compare_quality(old,old_ledger,ROOT)==read(ROOT/'runs/qa/ro-swordsman-combo-r006/comparison-final.json')
reports=sorted(QA.rglob('*.json'))
for p in reports:walk(read(p),p.relative_to(ROOT).as_posix())
walk(request['quality']['reference_artifacts'],'frozen references')
op=read(ROOT/'runs/hyper3d/operations/ro-hand-structure-20261003-001.json')
assert op['state']=='downloaded' and op['task_uuid']=='4da84074-918b-4473-89f1-bf2589a445e5'
assert op['consumed_credits']==.5 and len(op['downloads'])==8
for item in op['downloads']:check(item,'actual completed API download')
assert sha(PROVIDER)==PROVIDER_SHA256
assert sha(PROVIDER.parent/'authorization.json')=='431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10'
assert sha(ROOT/'scripts/hyper3d_api.py')==sha(MAIN/'scripts/hyper3d_api.py')
api=read(QA/'api-completion-verification.json')
assert api['private_state']['supported_provider_binding_verified'] and not api['private_state']['contains_master_key']
assert not api['private_state']['plaintext_printed_or_saved'] and not api['doctor_global_all_pass']
patch=read(QA/'v003-thumb-patch/patch.json');uv=read(QA/'v003-thumb-patch/UV-islands.json')
assert patch['geometry']['source_gate'] and patch['geometry']['protected_faces']==814
assert not uv['cross_island_interpolation_gate'] and len(uv['mixed_source_island_faces'])==16
assert read(QA/'v004-review.json')['verdict']=='NO_SHIP'
interval=read(QA/'baseline/baked-interval.json');assert len(interval['samples'])==121
images=sorted(QA.rglob('*.png'))
for p in images:
    assert p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    check({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)},'actual rendered PNG')
for target in re.findall(r'\]\(([^)]+)\)',(QA/'README.md').read_text(encoding='utf-8')):
    if target.startswith('https://') or target==destination.name:continue
    assert (QA/target).resolve().is_file(),target
library=read(ROOT/'library/index.json');ids=[entry['id'] for entry in library['entries']]
assert len(ids)==len(set(ids))
for entry in library['entries']:
    if not entry['id'].startswith('ro-swordsman-combo-r007'):continue
    assert entry['status']=='needs_revision' and entry['acceptance']['delivery']=='not_delivered'
    for name in entry['files']:assert (ROOT/name).is_file(),name
scripts=sorted((ROOT/'scripts').glob('*.py'))
for p in scripts:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True,encoding='utf-8').stdout.strip()
git_state={}
for name,root,head in [('isolated_worktree',ROOT,'c990639962b7ce85eb6beb631057aa4d76a3e86d'),('main_checkout',MAIN,'e077e22ba57447031b7cc89e3d37bd9cef47daf4')]:
    assert git(root,'rev-parse','HEAD')==head and not git(root,'diff','--cached','--name-only')
    git(root,'diff','--check');git_state[name]={'head':head,'staged_paths':[],'diff_check':'pass'}
checks=[]
for name,args in [('unit-tests',['-m','unittest','discover','-s','tests','-v']),
                  ('pipeline-validation',['scripts/pipeline.py','validate']),
                  ('request-validation',['scripts/workbench.py','validate','requests/ro-swordsman-combo-r007.json']),
                  ('api-entry-help',['scripts/hyper3d_api.py','--help']),
                  ('api-completed-status',['scripts/hyper3d_api.py','status','--operation','ro-hand-structure-20261003-001'])]:
    started=datetime.now(timezone.utc)
    result=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    log=QA/(name+'-final.log')
    with log.open('x',encoding='utf-8') as f:f.write(result.stdout+result.stderr)
    assert result.returncode==0,(name,result.returncode)
    check({'path':log.relative_to(ROOT).as_posix(),'sha256':sha(log)},name)
    row={'name':name,'argv':[sys.executable,'-B',*args],'exit_code':0,'started_utc':started.isoformat(),
        'ended_utc':datetime.now(timezone.utc).isoformat(),'log':log.relative_to(ROOT).as_posix()}
    if name=='unit-tests':
        count=re.search(r'Ran (\d+) tests in ([\d.]+)s',result.stderr);assert count
        row.update(tests=int(count.group(1)),seconds=float(count.group(2)));assert 'OK' in result.stderr
    if name=='api-completed-status':
        current=json.loads(result.stdout);assert current['state']=='downloaded' and current['live_query'] is False
        row['verification_scope']='Actual CLI local download state; no remote query or cost'
    checks.append(row)
now=datetime.now(timezone.utc)
final={'observed_utc':now.isoformat(),'integrity':'pass','art_verdict':'NO_SHIP','delivered':False,
    'scope':'Closedphase archive, required current local tools, actual prior API/Blender readbacks; not model acceptance',
    'current_comparison':comparison,'assessment_decision':assessment['decision'],'verified_artifacts':list(verified.values()),
    'historical_mutable_bindings_resolved_to_preserved_snapshots':historical,'public_reports_parsed':len(reports),
    'script_hashes':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in scripts],
    'actual_pngs':len(images),'checks_executed_this_run':checks,'git':git_state,
    'request_spec_quality_targets_preserved':True,'phase_clock_reset':False,
    'phase_wall_seconds_at_trial_close':accounting['phase_wall_seconds_at_close'],
    'post_trial_archive_verification_seconds':(now-datetime.fromisoformat(accounting['phase_closed_utc'])).total_seconds(),
    'original_phase_wall_seconds_through_verification':(now-datetime.fromisoformat(clock['baseline_started_utc'])).total_seconds(),
    'API':{'entry':str(MAIN/'scripts/hyper3d_api.py'),'state':'downloaded','consumed_credits':.5,'paid_submissions':1,
        'files':8,'provider_oldpolicy_rootentry_unchanged':True,'exact_DPAPI_binding_verified':True,
        'outside_repo_health':'known ENVIRONMENT_FAILURE unchanged, no safety/config repair'},
    'right_grip_left_hand_full300frame_VFX_freshanimatedGLB':'not_run_this_phase',
    'independent_final_review':str((QA/'v004-independent-review.json').relative_to(ROOT)),
    'stage_commit_push':'held_by_user','task_owned_background_work':'none'}
with destination.open('x',encoding='utf-8') as f:json.dump(final,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'integrity':'pass','artifacts':len(verified),'historical_bindings':len(historical),'scripts':len(scripts),
    'reports':len(reports),'PNGs':len(images),'tests':next(r['tests'] for r in checks if r['name']=='unit-tests'),
    'comparison':'stop_budget','assessment':'not_ready','new_credits':.5}))
