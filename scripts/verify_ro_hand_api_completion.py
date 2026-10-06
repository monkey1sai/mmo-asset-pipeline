"""Verify the exact authorized encrypted task file without exposing private fields."""
from datetime import datetime,timezone
from pathlib import Path
import json
from hyper3d_api import Client,read_json,file_sha,sha,canonical,write_json,PROVIDER,PROVIDER_SHA256
ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r006'; OP='ro-hand-source-20261003-001'
client=Client(ROOT); authority=read_json(QA/'hand-source-authority.json')
plan=read_json(client.plans/(OP+'.json')); plan_sha=plan.pop('plan_sha256')
assert sha(canonical(plan))==plan_sha==authority['plan_sha256']
record=read_json(client.record_path(OP)); assert record['state']=='downloaded' and record['operation_id']==OP
private=client.private_path(OP); assert str(private)==authority['exact_private_file']
# Read via the supported provider binding check only; never serialize private data.
binding=client.private_read(record)
assert binding['task_uuid']==record['task_uuid']; del binding
provider_hash=file_sha(PROVIDER); policy=PROVIDER.parent/'authorization.json'; policy_hash=file_sha(policy)
assert provider_hash==PROVIDER_SHA256
assert policy_hash=='431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10'
assert file_sha(ROOT/plan['request']['path'])==plan['request']['sha256']
assert all(client.image(i['path'])==i for i in plan['images'])
assert len(record['downloads'])==3 and all(file_sha(ROOT/i['path'])==i['sha256'] for i in record['downloads'])
before=(QA/'doctor-before-hand-source.txt').read_text(encoding='utf-8-sig')
after=(QA/'doctor-after-hand-source.txt').read_text(encoding='utf-8-sig')
failure='elevated Windows sandbox provisioning recorded a structured failure'
assert failure in before and failure in after
write_json(QA/'api-completion-verification.json',{
    'observed_utc':datetime.now(timezone.utc).isoformat(),'operator':'Codex coordinator','cwd':str(ROOT),'branch':'codex/art-quality-loop',
    'scope':'Only the exact newly authorized task recovery file was created/updated by this submission',
    'authority_record':{'path':(QA/'hand-source-authority.json').relative_to(ROOT).as_posix(),'sha256':file_sha(QA/'hand-source-authority.json')},
    'private_state':{'path':str(private),'bytes':private.stat().st_size,'before_exists':False,'after_sha256':file_sha(private),
        'supported_provider_binding_verified':True,'plaintext_printed_or_saved':False,'contains_master_key':False},
    'backup_path':None,'backup_reason':'New file; no previous contents','rollback':'Do not delete a submitted recovery record',
    'provider_sha256_unchanged':provider_hash,'old_policy_sha256_unchanged':policy_hash,
    'plan_request_input_and_download_hashes_verified':True,'operation_state':record['state'],
    'paid_submit_count':1,'service_reported_consumed_credits':record['consumed_credits'],
    'download_records':record['downloads'],'health':'doctor before/after same18ok/10notes/6warn/1fail; not an all-pass',
    'environment_failure':failure,'security_settings_repaired':False,
    'ACL_change':False,'ACL_runtime_verification':'not_run; no access-policy change requested',
    'global_config_link_line_import_gates':'not_applicable to a new encrypted task data file; no config/source edits',
    'old_history':'Preserved by no writes to old operation/state files; no broad all-history rehash claim',
    'next_action':'Actual Blender quality gates; downloaded is not animation acceptance',
},exclusive=True)
print(json.dumps({'exact_file_created_and_binding_verified':True,'old_policy_provider_hashes_unchanged':True,
    'operation_state':record['state'],'service_consumed':record['consumed_credits'],'downloaded_files':3,
    'doctor_all_pass':False,'no_secret_output':True}))
