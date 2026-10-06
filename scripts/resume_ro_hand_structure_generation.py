"""Bind current exact-file authority and non-consuming preflight; never submit."""
from datetime import datetime, timezone
from pathlib import Path
import json

import workbench
from hyper3d_api import Client, PROVIDER, PROVIDER_SHA256, file_sha, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r007"
OP = "ro-hand-structure-20261003-001"
EXPECTED_PLAN = "7dab8914d344854126bc1613a7bcd4b47e853d66e975914b231677a9d43a02c8"
POLICY_HASH = "431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10"
client = Client(ROOT)
plan = client.plan(OP)
request = read_json(ROOT / "requests/ro-swordsman-combo-r007.json")
clock = read_json(QA / "phase-start.json")
binding = read_json(QA / "baseline-binding-v2.json")
contract = binding["local_gate_contract"]
assert plan["plan_sha256"] == EXPECTED_PLAN
assert workbench.request_sha256(request) == clock["request_sha256"]
assert workbench.quality_sha256(request) == clock["protocol_sha256"]
assert file_sha(ROOT / contract["path"]) == contract["sha256"]
assert file_sha(PROVIDER) == PROVIDER_SHA256
assert file_sha(PROVIDER.parent / "authorization.json") == POLICY_HASH
private = client.private_path(OP)
assert not private.exists() and not client.record_path(OP).exists()
assert private.parent.is_dir()
unresolved = [p.stem for p in client.operations.glob("*.json")
              if read_json(p).get("state") in {"pending", "unknown"}]
assert not unresolved, unresolved
observed = datetime.now(timezone.utc)
elapsed = (observed - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()
assert elapsed < clock["budget"]["total_seconds"]
balance = client.balance()
assert balance["authenticated"] and balance["balance"] >= plan["estimated_credits"]
prepared = read_json(QA / "generation-prepared.json")
write_json(QA / "hand-structure-authority.json", {
    "observed_utc": observed.isoformat(), "operation_id": OP,
    "human_exact_authority": "Human selected quoted authorization: 授權新增並更新 ro-hand-structure-20261003-001.dpapi",
    "annotation_index": 1, "private_file_authority": "granted",
    "exact_private_file": str(private), "plan_sha256": EXPECTED_PLAN,
    "request_sha256": clock["request_sha256"], "local_gate_contract": contract,
    "credit_authority": "Existing demand-driven monthly or regular credits; no top-up or upgrade",
    "envelope": prepared["envelope"],
    "preserve": ["all old tasks", "old policy", "credential provider", "Git index/history"],
}, exclusive=True)
write_json(QA / "hand-structure-stage.json", {
    "timestamp_utc": observed.isoformat(), "operator": "Codex coordinator",
    "scope": "One new DPAPI task recovery file only", "cwd": str(ROOT),
    "branch": "codex/art-quality-loop", "source_file": str(private),
    "exists_before": False, "before_sha256": None, "backup_path": None,
    "backup_reason": "New file has no old content; preserve every existing task",
    "candidate_manifest": {"operation_id": OP, "plan_sha256": EXPECTED_PLAN,
                           "images": plan["images"], "local_gate_contract": contract},
    "candidate_age_seconds": (observed - datetime.fromisoformat(plan["created_utc"])).total_seconds(),
    "old_policy_sha256": POLICY_HASH, "provider_sha256": PROVIDER_SHA256,
    "ACL_change": False, "ACL_access_verification": "No ACL changes; actual exclusive DPAPI creation at submit checks access",
    "health_check": "codex doctor --summary before/after plus provider DPAPI roundtrip",
    "rollback": "Preserve submitted/unknown recovery state; no deletion or resubmit",
}, exclusive=True)
write_json(QA / "api-preflight-authorized.json", {
    "observed_utc": balance["observed_utc"], "balance": balance, "charged": False,
    "plan_sha256": EXPECTED_PLAN, "input_verified": plan["images"],
    "unresolved_operations": unresolved, "new_private_state_exists": False,
    "submission_performed": False, "phase_elapsed_seconds": elapsed,
    "waiting_time_policy": "Original wall clock preserved; no reset",
}, exclusive=True)
write_json(QA / "v001-start.json", {
    "id": "v001", "started_utc": observed.isoformat(),
    "phase_started_utc": clock["baseline_started_utc"], "phase_elapsed_before_candidate_seconds": elapsed,
    "request_sha256": clock["request_sha256"], "protocol_sha256": clock["protocol_sha256"],
    "local_gate_contract": contract, "operation_id": OP,
    "hypothesis": "Fitted worn glove with thenar volume and native quad topology can pass anatomy before rigging",
    "first_gate": "Native five-digit anatomy/topology and fitted wrist source; no bind-first compensations",
    "budget": clock["budget"], "paid_submission_performed_at_start": False,
}, exclusive=True)
print(json.dumps({"preflight": "verified", "balance": balance["balance"], "charged": False,
                  "operation": OP, "exact_file_authority": "granted", "phase_elapsed_seconds": elapsed}))
