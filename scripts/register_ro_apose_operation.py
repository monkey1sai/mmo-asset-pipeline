"""Register the authorized next API operation; no credential/journal parsing."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'runs/qa/ro-swordsman-combo-r003'
ADAPTER=Path(r'C:\Users\IOT\.codex\tools\hyper3d-api');POLICY=ADAPTER/'authorization.json'
KNOWN={'input_roots','output_roots','operation_id','external_credits_reserved','total_credit_limit','max_api_submissions','download_hosts'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snapshots():
    # Review rejected content reads, including hashes. Inspect directory metadata
    # only; terminal status comes from the supported service tool, not journals.
    return {p.name:{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in sorted((ADAPTER/'state').glob('*.json'))}
def audit():
    old=read(POLICY)
    if set(old)!=KNOWN:raise RuntimeError('Unknown nonsecret policy schema; stop')
    history=snapshots()
    if set(history)!={'ro-swordsman-reference-20261002-001.json','zhaoyun-20261001-api-1.json'}:raise RuntimeError('Unexpected task set; status must be reconciled')
    proof=read(QA/'prior-live-status.json')
    if len(proof['tasks'])!=2 or any(not t['done'] or t['failed'] or any(x!='Done' for x in t['jobs']) for t in proof['tasks']):raise RuntimeError('Previous task not terminal')
    prepared=read(QA/'generation-prepared.json');image=(ROOT/prepared['input']['path']).resolve(strict=True)
    output=(ROOT/prepared['output_directory']).resolve()
    if not image.is_relative_to(ROOT/'assets/raw') or not output.is_relative_to(ROOT/'assets/raw'):raise RuntimeError('Task asset path escape')
    if digest(image)!=prepared['input']['sha256']:raise RuntimeError('Input hash drift')
    if old['operation_id']!='ro-swordsman-reference-20261002-001':raise RuntimeError('Unexpected current operation; stop')
    new=dict(old);new.update(input_roots=[image.as_posix()],output_roots=[output.as_posix()],operation_id=prepared['operation_id'],total_credit_limit=old['total_credit_limit']+.5,max_api_submissions=old['max_api_submissions']+1)
    return {'policy_sha256':digest(POLICY),'implementation_sha256':digest(ADAPTER/'rodin_api.py'),'journal_metadata':history,'proof_sha256':digest(QA/'prior-live-status.json'),'input_sha256':digest(image),'old':old,'new':new,'authority':'Latest human explicitly authorizes all available APIs and existing monthly/regular credits according to modeling needs; no total point limit. This registers one actual0.5-cost operation, not a user budget cap. Preserve prior counters and repeat only for separately recorded needed jobs.','scope':'Only authorization.json metadata; exact new design input/output/operation. No key/env/DPAPI/journal read, tool code/MCP/config/ACL changes, broad filesystem root, counter reset or purchase.'}
p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','apply']);a=p.parse_args()
if a.mode=='prepare':
    report=audit();(QA/'api-registration-dryrun.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));raise SystemExit(0)
expected=read(QA/'api-registration-dryrun.json')
if audit()!=expected:raise RuntimeError('Prepared registration drift')
backup=ROOT/'tmp/ro-apose-api-registration-backup';backup.mkdir(exist_ok=False)
before=backup/'authorization.before.json';before.write_bytes(POLICY.read_bytes())
if digest(before)!=expected['policy_sha256']:raise RuntimeError('Backup hash mismatch')
candidate=json.dumps(expected['new'],ensure_ascii=False,indent=2)+'\n'
staged=None
try:
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=POLICY.parent,prefix='.ro-apose-authorized-',suffix='.tmp',delete=False) as stream:
        staged=Path(stream.name);stream.write(candidate);stream.flush();os.fsync(stream.fileno())
    if read(staged)!=expected['new'] or audit()!=expected:raise RuntimeError('Late policy/journal drift')
    os.replace(staged,POLICY)
finally:
    if staged and staged.exists():staged.unlink()
if read(POLICY)!=expected['new'] or snapshots()!=expected['journal_metadata']:raise RuntimeError('Registration readback drift')
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'target':str(POLICY),'before_sha256':expected['policy_sha256'],'after_sha256':digest(POLICY),'backup':before.relative_to(ROOT).as_posix(),'journal_metadata_unchanged':True,'journal_content_integrity':'Not read/hashed; onlynames,size,mtime observed unchanged, script never writes journal.','new_registered_operation':expected['new']['operation_id'],'new_job_cost':.5,'user_total_credit_ceiling':None,'rollback':'Before submit restore verified backup; after submit preserve new reservation/history and reconcile original task, never restore old accounting over a paid operation.'}
(QA/'api-registration-applied.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
