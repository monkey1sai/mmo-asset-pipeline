"""Verify this authorized task's protected binding and actual native downloads."""
from datetime import datetime, timezone
from pathlib import Path
import json
from hyper3d_api import Client, PROVIDER, PROVIDER_SHA256, read_json, file_sha, write_json

ROOT=Path(__file__).resolve().parents[1]; QA=ROOT/'runs/qa/ro-swordsman-combo-r007'
OP='ro-hand-structure-20261003-001'; client=Client(ROOT)
authority=read_json(QA/'hand-structure-authority.json')
record=read_json(client.record_path(OP)); assert record['state']=='downloaded'
private=client.private_path(OP); assert str(private)==authority['exact_private_file']
binding=client.private_read(record)
assert binding['task_uuid']==record['task_uuid']; del binding
assert file_sha(PROVIDER)==PROVIDER_SHA256
policy=PROVIDER.parent/'authorization.json'
assert file_sha(policy)=='431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10'
assert file_sha(ROOT/'scripts/hyper3d_api.py')==file_sha(Path(r'C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py'))
assert len(record['downloads'])==8
for item in record['downloads']:
    assert file_sha(ROOT/item['path'])==item['sha256']
    assert (ROOT/item['path']).stat().st_size==item['bytes']
before=read_json(QA/'maintenance-health-before.json')
after=(QA/'maintenance-health-after.log').read_text(encoding='utf-8-sig')
failure='elevated Windows sandbox provisioning recorded a structured failure'
assert failure in before['failed_gate'] and failure in after
balance=client.balance()
write_json(QA/'api-completion-verification.json',{
    'observed_utc':datetime.now(timezone.utc).isoformat(),'operator':'Codex coordinator','cwd':str(ROOT),
    'branch':'codex/art-quality-loop','scope':'Only one explicitly authorized new task-state DPAPI file',
    'authority_record':{'path':(QA/'hand-structure-authority.json').relative_to(ROOT).as_posix(),
                        'sha256':file_sha(QA/'hand-structure-authority.json')},
    'private_state':{'path':str(private),'bytes':private.stat().st_size,'before_exists':False,
        'after_sha256':file_sha(private),'supported_provider_binding_verified':True,
        'plaintext_printed_or_saved':False,'contains_master_key':False},
    'backup_path':None,'backup_reason':'New file; no previous content; existing tasks untouched',
    'rollback':'Preserve submitted recovery state and history; no delete or resubmit',
    'provider_sha256_unchanged':file_sha(PROVIDER),'old_policy_sha256_unchanged':file_sha(policy),
    'operation_state':record['state'],'paid_submit_count':1,
    'service_reported_consumed_credits':record['consumed_credits'],'download_records':record['downloads'],
    'live_nonconsuming_balance':balance,'native_OBJ_downloaded':True,'raw_MTL_present':False,
    'old_prepared_pending_authority_text':'Frozen plan retained; exact authority granted later in hand-structure-authority.json and CLI authorized-state-file',
    'health_before_after_same_known_failure':True,'doctor_global_all_pass':False,
    'classification':'ENVIRONMENT_FAILURE','environment_failure':failure,'security_settings_repaired':False,
    'ACL_change':False,'ACL_access_check':'Parent owner metadata read; actual exclusive task-state creation/update succeeded',
    'global_config_link_line_import_gates':'Not applicable to encrypted task data; no config/source edits',
    'source_animation_accepted':False,'commit_push':'held by user',
},exclusive=True)
print(json.dumps({'protected_binding_verified':True,'state':'downloaded','files':8,
                  'service_credits':record['consumed_credits'],'balance':balance['balance'],
                  'old_provider_policy_unchanged':True,'doctor_global_all_pass':False}))
