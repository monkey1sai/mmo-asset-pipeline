"""Bounded, explicitly authorized local metadata repair. Never loads credentials.

prepare writes a reviewable exact candidate in this repo. apply requires matching
policy, journal, input and implementation hashes, live previous-task terminal
evidence and the already recorded human permission. Not a global configuration
manager; it updates only this adapter's single nonsecret authorization file.
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=Path(r'C:\Users\IOT\.codex\tools\hyper3d-api')
POLICY=ADAPTER/'authorization.json'
PROPOSAL=ROOT/'runs/ro-swordsman-api-grant-proposal.json'
REPORT=ROOT/'runs/ro-swordsman-api-grant-dryrun.json'
BACKUP=ROOT/'tmp/ro-swordsman-api-grant-backup'
KNOWN={'input_roots','output_roots','operation_id','external_credits_reserved','total_credit_limit','max_api_submissions','download_hosts'}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def journal_snapshot(): return {p.name:sha(p) for p in sorted((ADAPTER/'state').glob('*.json'))}
def audit():
    old=read(POLICY)
    if set(old)!=KNOWN: raise RuntimeError('unknown authorization schema: '+str(sorted(set(old)-KNOWN)))
    proof=read(ROOT/'runs/ro-swordsman-prior-api-status.json')
    records=[read(ADAPTER/'state'/name) for name in journal_snapshot()]
    if not proof['done'] or proof['failed'] or any(j!='Done' for j in proof['jobs']): raise RuntimeError('old API operation not terminal')
    for record in records:
        if record.get('state')=='submitted' and record.get('task_uuid')==proof['task_uuid']: continue
        if record.get('state') not in {'completed','failed','cancelled','downloaded'}: raise RuntimeError('nonterminal or unverified old operation')
    proposal=read(PROPOSAL)
    input_file=Path(proposal['input_roots'][0]).resolve(strict=True)
    original=Path(r'C:\.llmcode\ro_swordsman_animation\transparent_frames\sprite_12.png').resolve(strict=True)
    output=Path(proposal['output_roots'][0]).resolve()
    if not input_file.is_relative_to(ROOT.resolve()) or not output.is_relative_to(ROOT.resolve()): raise RuntimeError('task path escaped worktree')
    if input_file.suffix!='.png' or input_file.is_dir(): raise RuntimeError('wrong input')
    if sha(input_file)!=sha(original) or sha(input_file)!=read(ROOT/'runs/ro-swordsman-api-prepared-20261002.json')['input_sha256']: raise RuntimeError('input hash drift')
    reserved=sum(record.get('credit_limit',.5) for record in records)
    if type(old['external_credits_reserved']) not in (int,float) or old['external_credits_reserved']<0: raise RuntimeError('invalid reservations')
    if any(type(r.get('credit_limit',.5)) not in (int,float) or r.get('credit_limit',.5)<0 for r in records): raise RuntimeError('invalid record reservations')
    new=dict(old)
    new.update(input_roots=[input_file.as_posix()],output_roots=[output.as_posix()],operation_id=proposal['operation_id'],
               total_credit_limit=old['external_credits_reserved']+reserved+.5,max_api_submissions=len(records)+1)
    return {'status':'prepared_not_applied','policy_path':str(POLICY),'policy_sha256':sha(POLICY),
            'implementation_sha256':sha(ADAPTER/'rodin_api.py'),'journal_sha256':journal_snapshot(),
            'input_sha256':sha(input_file),'source_sha256':sha(original),'old':old,'new':new,
            'arithmetic':{'external_reserved':old['external_credits_reserved'],'journal_reserved':reserved,'new_allowed':.5,'submission_records':len(records),'new_submission_count':1},
            'prior_terminal_proof_sha256':sha(ROOT/'runs/ro-swordsman-prior-api-status.json'),
            'backup_directory':BACKUP.relative_to(ROOT).as_posix(),
            'authority':'User approved one0.5 existing-credit character task and clarified the API is an art-engineer workflow permission, after the exact narrow repair was presented.',
            'forbidden':'No credentials/env/ACL/global Codex or MCP config/tool code/journal changes; no counter reset; no extra spend.'}
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['prepare','apply']); args=parser.parse_args()
    if args.mode=='prepare':
        report=audit()
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':report['status'],'old':report['old'],'new':report['new'],'arithmetic':report['arithmetic']},indent=2)); return
    # Read+write lock prevents concurrent updates by this task; hash checks also
    # catch other writers. The adapter's policy is still read atomically.
    lock=BACKUP/'apply.lock'; BACKUP.mkdir(parents=True,exist_ok=True)
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.close(fd)
    try:
        expected=read(REPORT); current=audit()
        if current!=expected: raise RuntimeError('dryrun/apply drift; stop')
        backup=BACKUP/'authorization.before.json'
        if backup.exists() and sha(backup)!=expected['policy_sha256']: raise RuntimeError('backup collision')
        if not backup.exists(): backup.write_bytes(POLICY.read_bytes())
        if sha(backup)!=expected['policy_sha256']: raise RuntimeError('backup hash mismatch')
        candidate=json.dumps(expected['new'],ensure_ascii=False,indent=2)+'\n'
        # Recheck state immediately before the sole authorized global mutation.
        if audit()!=expected: raise RuntimeError('late drift; stop')
        staged=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=POLICY.parent,prefix='.authorization-ro-',suffix='.tmp',delete=False) as stream:
                staged=Path(stream.name); stream.write(candidate); stream.flush(); os.fsync(stream.fileno())
            if read(staged)!=expected['new'] or audit()!=expected: raise RuntimeError('staged candidate/late drift; stop')
            os.replace(staged,POLICY)
        finally:
            if staged and staged.exists(): staged.unlink()
        if read(POLICY)!=expected['new'] or journal_snapshot()!=expected['journal_sha256']: raise RuntimeError('readback/journal drift; stop')
        result={'status':'applied_and_readback_verified','target':str(POLICY),'before_sha256':expected['policy_sha256'],'after_sha256':sha(POLICY),'backup':str(backup),'journal_unchanged':True,'new_allowed_spend':.5,'new_submissions':1,'rollback':'restore only the backup after verifying no new operation was submitted; otherwise preserve new reservations and stop for adjudication.'}
        (ROOT/'runs/ro-swordsman-api-grant-applied.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
    finally: lock.unlink()
if __name__=='__main__': main()
