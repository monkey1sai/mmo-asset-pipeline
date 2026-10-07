"""Finalize the authorized stage, failed candidate patch and evidence hashes."""
from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json
import socket
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=json.loads((OUT/'candidate-01-source/manifest.json').read_text())
patch=[]
for item in archive['source_files']:
    candidate=ROOT/item['archive_path']
    assert sha(candidate)==item['sha256']
    current=ROOT/item['runtime_path']
    before=current.read_text().splitlines(keepends=True) if current.exists() else []
    after=candidate.read_text().splitlines(keepends=True)
    patch.extend(difflib.unified_diff(before,after,fromfile='a/'+item['runtime_path'] if before else '/dev/null',tofile='b/'+item['runtime_path']))
(OUT/'candidate-01.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
assert sha(ROOT/'tools/runtime-qa/three/src/p4.js')=='8b661ccd444787b0b6843241f753eae6b9825b247f20658cd43c7ec347c1f6e8'
with socket.socket() as connection:
    connection.settimeout(1)
    stopped=connection.connect_ex(('127.0.0.1',8774)) != 0
assert stopped, 'TASK_SERVER_STILL_LISTENING'
start=datetime.fromisoformat('2026-10-07T09:54:47+00:00')
end=datetime.now(timezone.utc)
elapsed=(end-start).total_seconds()
assert 0 <= elapsed < 7200
ledger={'schema_version':1,'authorization':'user selection 1: independent <=2h, <=1 character candidate',
        'start_utc':start.isoformat(),'end_utc':end.isoformat(),'deadline_utc':'2026-10-07T11:54:47Z',
        'elapsed_seconds':elapsed,'maximum_seconds':7200,'candidates_used':1,'maximum_candidates':1,
        'candidate_status':'failed_discard','overall_character_status':'incomplete','legacy_clock_reset':False,
        'legacy_spending_reset':False,'legacy_failures_removed':False,'paid_operations':0,'remote_mutations':0,
        'commit_or_push':False,'baseline_source_restored':True,'task_server_stopped':stopped,
        'background_trial_running':False,'stop_reason':'candidate limit reached after full regression and rejection; no second candidate authorized'}
(OUT/'stage-ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
files=[]
for path in sorted(OUT.rglob('*')):
    if path.is_file() and path.name!='evidence-manifest.json':
        files.append({'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)})
(OUT/'evidence-manifest.json').write_text(json.dumps({'schema_version':1,'observed_utc':end.isoformat(),'files':files},indent=1)+'\n')
print(json.dumps({'elapsed_seconds':elapsed,'minutes':round(elapsed/60,2),'candidate_disposition':'discard','files_hashed':len(files),'evidence_bytes':sum(f['bytes'] for f in files),'server_stopped':stopped}))
