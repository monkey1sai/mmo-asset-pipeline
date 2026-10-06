"""Verify the closed RO phase without networking, DCC changes or private reads."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import workbench


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r005"
MAIN = Path(r"C:\Repos\mmo-asset-pipeline")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        text=True, encoding="utf-8",
    ).stdout.strip()


verified = {}


def check(item, evidence):
    path = (ROOT / item["path"]).resolve()
    assert path.is_relative_to(ROOT.resolve()), item["path"]
    assert path.is_file(), item["path"]
    assert sha(path) == item["sha256"], item["path"]
    size = path.stat().st_size
    if "bytes" in item:
        assert size == item["bytes"], item["path"]
    entry = verified.setdefault(item["path"], {
        "path": item["path"], "bytes": size, "sha256": item["sha256"],
        "evidence": [],
    })
    entry["evidence"].append(evidence)


operations = []
for operation_id in ["ro-split-batch-20261003-001", "ro-core-fallback-20261003-001"]:
    relative = f"runs/hyper3d/operations/{operation_id}.json"
    operation = read(ROOT / relative)
    assert operation["state"] == "downloaded"
    assert operation["cost_state"] == "service_reported"
    assert operation["consumed_credits"] == 0.5
    for item in operation["downloads"]:
        check(item, relative)
    operations.append({
        "operation_id": operation_id, "state": operation["state"],
        "service_reported_credits": operation["consumed_credits"],
        "live_query_during_final_verification": False,
    })

reports = sorted(QA.rglob("*.json"))
for report in reports:
    value = read(report)
    if not isinstance(value, dict):
        continue
    items = list(value.get("artifacts", []))
    if isinstance(value.get("artifact"), dict):
        items.append(value["artifact"])
    if isinstance(value.get("subject"), dict) and "sha256" in value["subject"]:
        items.append(value["subject"])
    for item in items:
        check(item, report.relative_to(ROOT).as_posix())

request = read(ROOT / "requests/ro-swordsman-combo-r005.json")
comparison = workbench.compare_quality(request, read(QA / "quality-ledger.json"))
assert comparison == read(QA / "comparison-final.json")
assert comparison["candidate_trials_used"] == 3
assert comparison["next_action"] == "stop_budget"
assert not comparison["quality_target_met"] and not comparison["blockers"]

index = read(ROOT / "library/index.json")
entries = []
found = workbench.search_library(index, "RO")
for entry in index["entries"]:
    if entry["id"] not in ["ro-swordsman-combo-r005-v002", "ro-swordsman-combo-r005-v003"]:
        continue
    assert entry in found
    assert entry["acceptance"]["art"] == "failed"
    assert entry["acceptance"]["delivery"] == "not_delivered"
    for relative in entry["files"]:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT.resolve()) and path.is_file(), relative
    assert (ROOT / entry["qa_report"]).is_file()
    entries.append(entry["id"])
assert len(entries) == 2

scripts = sorted((ROOT / "scripts").glob("*.py"))
for script in scripts:
    ast.parse(script.read_text(encoding="utf-8-sig"), filename=str(script))
assert sha(ROOT / "scripts/hyper3d_api.py") == sha(MAIN / "scripts/hyper3d_api.py")
unchanged = [
    (Path(r"C:\Users\IOT\.codex\tools\hyper3d-api\rodin_api.py"),
     "45247a8def85815d03bb296767aec5f79699a518489f2e68bddad3ff39b09e3a"),
    (Path(r"C:\Users\IOT\.codex\tools\hyper3d-api\authorization.json"),
     "431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10"),
]
for path, expected in unchanged:
    assert sha(path) == expected, str(path)
private_state = Path(
    r"C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-core-fallback-20261003-001.dpapi"
)
assert private_state.is_file()
axis_check = read(QA / "v003-hand-surface/axis-runtime-check.json")
assert axis_check["status"] == "pass" and axis_check["bones_checked"] == 20
assert axis_check["art_pass"] is False

git_state = {}
for name, root in [("isolated_worktree", ROOT), ("main_checkout", MAIN)]:
    assert not git(root, "diff", "--cached", "--name-only")
    git(root, "diff", "--check")
    git_state[name] = {"head": git(root, "rev-parse", "HEAD"), "staged_paths": []}

result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Local archive integrity and bookkeeping, not new art or runtime acceptance",
    "artifact_integrity": "pass", "verified_artifacts": list(verified.values()),
    "public_json_reports_parsed": len(reports),
    "syntax_checked": [script.relative_to(ROOT).as_posix() for script in scripts],
    "library_entries_checked": entries,
    "api_operations": operations,
    "phase_service_reported_credits": sum(item["service_reported_credits"] for item in operations),
    "new_credits_during_final_verification": 0,
    "main_and_worktree_api_entry_identical": True,
    "provider_and_old_authorization_unchanged": [str(path) for path, _ in unchanged],
    "authorized_private_state": {
        "path": str(private_state), "exists": True,
        "bytes": private_state.stat().st_size,
        "content_read": False, "method": "File existence and size only",
    },
    "quality_comparison": comparison,
    "checks_executed_earlier_this_turn": {
        "unit_tests": "116 passed in 1.968s; not rerun by this integrity script",
        "existing_pipeline": "valid 39 assets; schema only",
        "actual_blender_digit_axis": "20 bones passed; no art/deformation acceptance",
    },
    "git": git_state,
    "art_verdict": "NO_SHIP", "full_animation_verified": False,
    "effects_verified": False, "delivered": False,
    "global_blender_environment": "Historical cleanup impact unresolved; not inspected or repaired here",
    "stage_commit_push": "held by user", "task_owned_background_work": "none",
}
with (QA / "verification-final.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({
    "integrity": "pass", "artifacts": len(verified), "scripts": len(scripts),
    "reports_parsed": len(reports), "quality": comparison["next_action"],
    "art_verdict": "NO_SHIP", "new_charge": 0,
}, ensure_ascii=False))
