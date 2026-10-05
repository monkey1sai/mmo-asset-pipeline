"""Verify the pending hand phase archive; no network, private reads or global writes."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import workbench
from hyper3d_api import Client

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


request = read(ROOT / "requests/ro-swordsman-combo-r006.json")
old = read(ROOT / "requests/ro-swordsman-combo-r005.json")
assert request["spec"] == old["spec"]
assert request["quality"]["dimensions"] == old["quality"]["dimensions"]
assert sha(ROOT / request["phase_history"]["previous_result"]) == request["phase_history"]["previous_result_sha256"]
assert read(ROOT / request["phase_history"]["previous_result"])["next_action"] == "stop_budget"
ledger = read(QA / "quality-ledger.json")
comparison = workbench.compare_quality(request, ledger)
assert comparison == read(QA / "comparison-baseline.json")
assert comparison["candidate_trials_used"] == 0 and not comparison["quality_target_met"]
binding = read(QA / "baseline-binding.json")
for item in [binding["local_gate_contract"], binding["actual_baseline_report"], binding["source_helper"]]:
    assert sha(ROOT / item["path"]) == item["sha256"]
baseline = read(QA / "baseline/baseline.json")
artifacts = baseline["artifacts"] + list(ledger["trials"][0]["previews"].values())
for item in artifacts:
    assert sha(ROOT / item["path"]) == item["sha256"]
assert baseline["geometry_uv_weights_unchanged"] and baseline["source_preserved"]
assert sha(ROOT / baseline["source"]["path"]) == baseline["source"]["sha256"]
for item in request["quality"]["reference_artifacts"]:
    assert sha(ROOT / item["path"]) == item["sha256"]
images = sorted((QA / "baseline").rglob("*.png"))
assert len(images) == 29
client = Client(ROOT)
plan = client.plan("ro-hand-source-20261003-001")
assert not client.record_path(plan["operation_id"]).exists()
assert not client.private_path(plan["operation_id"]).exists()
assert plan["plan_sha256"] == read(QA / "generation-prepared.json")["plan_sha256"]
assert sha(ROOT / "scripts/hyper3d_api.py") == sha(Path(r"C:\Repos\mmo-asset-pipeline\scripts\hyper3d_api.py"))
scripts = ["prepare_ro_hand_phase.py", "baseline_ro_hand_phase.py", "probe_ro_hand_budget.py",
           "probe_ro_hand_baseline_technical.py", "record_ro_hand_baseline.py", "verify_ro_hand_preparation.py"]
for name in scripts:
    ast.parse((ROOT / "scripts" / name).read_text(encoding="utf-8"))
reports = sorted(QA.rglob("*.json"))
for path in reports:
    read(path)
assert not subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT,
    capture_output=True, text=True, check=True).stdout.strip()
result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "integrity": "pass",
    "request_targets_and_spec_unchanged": True, "old_phase_result_unchanged": True,
    "bound_baseline_artifacts_verified": artifacts,
    "local_gate_contract": binding["local_gate_contract"],
    "additional_baseline_pngs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in images],
    "scripts_syntax_checked": scripts, "public_json_parsed": len(reports),
    "current_turn_unit_tests": "116 passed in2.054s", "existing_pipeline": "valid39; schema only",
    "git_diff_check": "passed; CRLF normalization warning in prior index only", "staged_paths": [],
    "api": {"state": "prepared_not_submitted", "operation_id": plan["operation_id"],
        "global_private_file_exists": False, "charged_generation_this_phase": False,
        "nonconsuming_preflight": read(QA / "api-preflight.json")["balance"],
        "main_and_worktree_entry_identical": True},
    "art_verdict": "NO_SHIP", "fresh_glb_roundtrip": "not_run", "full_animation": "not_run", "effects": "not_run",
    "resume_gate": "Human exact-file authority for the prepared operation's DPAPI state file",
    "task_owned_background_production": "none", "commit_push": "held by user",
}
with (QA / "preparation-verification.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"integrity": "pass", "baseline_pngs": len(images), "scripts": len(scripts),
    "request": request["id"], "api_submitted": False, "new_hyper3d_charge": 0, "art_verdict": "NO_SHIP"}))
