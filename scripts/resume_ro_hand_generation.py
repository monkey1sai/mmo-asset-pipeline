"""Record exact current human authority and non-consuming preflight, no submit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from hyper3d_api import Client, file_sha, read_json, write_json
import workbench

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"
OP = "ro-hand-source-20261003-001"
EXPECTED_PLAN = "0d1d8ee2f4d5b0ab7ddaf6876c9c350d66b915d9e501f78d4e9340f5208597aa"
EXPECTED_POLICY = "431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10"
client = Client(ROOT)
plan = client.plan(OP)
request = read_json(ROOT / "requests/ro-swordsman-combo-r006.json")
clock = read_json(QA / "phase-start.json")
binding = read_json(QA / "baseline-binding.json")
contract = binding["local_gate_contract"]
assert plan["plan_sha256"] == EXPECTED_PLAN
assert workbench.request_sha256(request) == clock["request_sha256"]
assert workbench.quality_sha256(request) == clock["protocol_sha256"]
assert file_sha(ROOT / contract["path"]) == contract["sha256"]
assert file_sha(Path.home() / ".codex/tools/hyper3d-api/authorization.json") == EXPECTED_POLICY
private = client.private_path(OP)
assert not private.exists() and not client.record_path(OP).exists()
unresolved = [p.stem for p in client.operations.glob("*.json")
              if read_json(p).get("state") in {"pending", "unknown"}]
assert not unresolved, unresolved
observed = datetime.now(timezone.utc)
phase_elapsed = (observed - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()
assert phase_elapsed < clock["budget"]["total_seconds"]
balance = client.balance()
prepared = read_json(QA / "generation-prepared.json")
write_json(QA / "hand-source-authority.json", {
    "observed_utc": observed.isoformat(), "operation_id": OP,
    "human_exact_authority": "授權新增並更新 ro-hand-source-20261003-001.dpapi",
    "exact_private_file": str(private),
    "credit_authority": "Existing human demand-driven monthly or regular credit authorization; no top-up or upgrade",
    "plan_sha256": EXPECTED_PLAN, "request_sha256": clock["request_sha256"],
    "envelope": prepared["envelope"], "private_file_authority": "granted",
    "preserve": ["all old tasks", "old policy", "credential provider", "Git index and history"],
}, exclusive=True)
write_json(QA / "hand-source-stage.json", {
    "timestamp_utc": observed.isoformat(), "operator": "Codex coordinator",
    "scope": "One new DPAPI task recovery file only", "cwd": str(ROOT),
    "branch": "codex/art-quality-loop", "source_file": str(private),
    "exists_before": False, "before_sha256": None, "backup_path": None,
    "backup_reason": "New file; no previous content to back up",
    "candidate_manifest": {"operation_id": OP, "plan_sha256": EXPECTED_PLAN,
                           "input_sha256": plan["images"][0]["sha256"]},
    "candidate_age_seconds": 0, "old_policy_sha256": EXPECTED_POLICY,
    "provider_sha256": plan["provider_sha256"], "ACL_change": False,
    "health_check": "codex doctor --summary before/after; DPAPI supported-provider roundtrip",
    "rollback": "Preserve new state if submitted/unknown; no deletion or paid retry",
}, exclusive=True)
write_json(QA / "api-preflight-authorized.json", {
    "observed_utc": balance["observed_utc"], "balance": balance,
    "charged": False, "plan_sha256": EXPECTED_PLAN, "input_verified": plan["images"],
    "unresolved_operations": unresolved, "new_private_state_exists": False,
    "submission_performed": False, "phase_elapsed_seconds": phase_elapsed,
    "waiting_time_policy": "All wall clock since original phase start included; no clock reset",
}, exclusive=True)
write_json(QA / "v001-start.json", {
    "id": "v001", "started_utc": observed.isoformat(),
    "phase_started_utc": clock["baseline_started_utc"],
    "phase_elapsed_before_candidate_seconds": phase_elapsed,
    "request_sha256": clock["request_sha256"], "protocol_sha256": clock["protocol_sha256"],
    "local_gate_contract": contract, "operation_id": OP,
    "hypothesis": "Independent generated anatomical glove permits coherent palm/thumb topology and local fitting",
    "first_gate": "Actual five-digit geometry, palm/cuff and topology inspection; then right hand only",
    "budget": clock["budget"], "paid_submission_performed": False,
}, exclusive=True)
print(json.dumps({"preflight": "verified", "authenticated": balance["authenticated"],
                  "balance": balance["balance"], "charged": False,
                  "operation": OP, "exact_file_authority": "granted",
                  "phase_elapsed_seconds": phase_elapsed}, ensure_ascii=False))
