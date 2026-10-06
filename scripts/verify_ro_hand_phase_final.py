"""Offline integrity and required tool checks for the closed r006 experiment.

No API calls, DCC execution, private decryption, global writes or Git mutations.
This verifies recorded evidence; it cannot promote a failed prototype to delivery.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import workbench

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(r"C:\Repos\mmo-asset-pipeline")
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"
verified = {}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(item, evidence):
    path = (ROOT / item["path"]).resolve()
    assert path.is_relative_to(ROOT), item["path"]
    assert path.is_file(), item["path"]
    assert sha(path) == item["sha256"], (evidence, item["path"])
    size = path.stat().st_size
    if "bytes" in item:
        assert size == item["bytes"], item["path"]
    entry = verified.setdefault(item["path"], {
        "path": item["path"], "bytes": size, "sha256": item["sha256"], "evidence": [],
    })
    if evidence not in entry["evidence"]:
        entry["evidence"].append(evidence)


def walk(value, evidence):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            check(value, evidence)
        for child in value.values():
            walk(child, evidence)
    elif isinstance(value, list):
        for child in value:
            walk(child, evidence)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()


assert not (QA / "final-verification.json").exists(), "Do not overwrite final evidence"
request = read(ROOT / "requests/ro-swordsman-combo-r006.json")
binding = read(QA / "baseline-binding.json")
assert workbench.request_sha256(request) == binding["request_sha256"]
assert workbench.quality_sha256(request) == binding["quality_sha256"]
old_request = read(ROOT / "requests/ro-swordsman-combo-r005.json")
assert request["spec"] == old_request["spec"]
assert request["quality"]["dimensions"] == old_request["quality"]["dimensions"]
previous = request["phase_history"]
assert sha(ROOT / previous["previous_result"]) == previous["previous_result_sha256"]
assert read(ROOT / previous["previous_result"])["next_action"] == "stop_budget"
reports = sorted(QA.rglob("*.json"))
for path in reports:
    walk(read(path), path.relative_to(ROOT).as_posix())
walk(request["quality"]["reference_artifacts"], "request quality reference_artifacts")

ledger = read(QA / "quality-ledger.json")
comparison = workbench.compare_quality(request, ledger, ROOT)
assert comparison == read(QA / "comparison-final.json")
assert comparison["candidate_trials_used"] == 8
assert comparison["best_trial_id"] == "baseline"
assert comparison["next_action"] == "stop_budget"
assert not comparison["quality_target_met"] and not comparison["blockers"]
assessment = workbench.assess(request, read(QA / "final-evidence.json"), ROOT)
assert assessment == read(QA / "assessment-final.json")
assert assessment["decision"] == "not_ready"
clock = read(QA / "phase-accounting-final.json")
wall = (datetime.fromisoformat(clock["closed_utc"]) -
        datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds()
assert abs(wall - sum(t["elapsed_seconds"] for t in ledger["trials"])) < .002
assert wall == clock["phase_wall_seconds_including_waiting_and_candidateQA"]
assert clock["revisions_used"] == 8 and clock["service_reported_credits"] == .5
assert len(list((QA / "baseline").rglob("*.png"))) == 29

operation = read(ROOT / "runs/hyper3d/operations/ro-hand-source-20261003-001.json")
assert operation["state"] == "downloaded"
assert operation["consumed_credits"] == .5 and operation["cost_state"] == "service_reported"
for item in operation["downloads"]:
    check(item, "operation downloads")
api_check = read(QA / "api-completion-verification.json")
assert api_check["paid_submit_count"] == 1
private = Path(r"C:\Users\IOT\.codex\tools\hyper3d-api\state\ro-hand-source-20261003-001.dpapi")
assert private.is_file() and private.stat().st_size == 934
assert sha(private) == api_check["private_state"]["after_sha256"]
unchanged = [
    (Path(r"C:\Users\IOT\.codex\tools\hyper3d-api\rodin_api.py"), api_check["provider_sha256_unchanged"]),
    (Path(r"C:\Users\IOT\.codex\tools\hyper3d-api\authorization.json"), api_check["old_policy_sha256_unchanged"]),
]
for path, expected in unchanged:
    assert sha(path) == expected, str(path)
assert sha(ROOT / "scripts/hyper3d_api.py") == sha(MAIN / "scripts/hyper3d_api.py")

roundtrip = read(QA / "v008-glb-roundtrip/roundtrip.json")
assert roundtrip["prototype_geometry_playback_pass"] and roundtrip["all61frames_evaluated"]
assert roundtrip["source_frames"] == [1, 61] and roundtrip["fps"] == 60
assert not roundtrip["full300frame_skill_combo_accepted"] and not roundtrip["art_accepted"]
samples = roundtrip["skeletal_and_morph_playback_samples"]
assert len(samples) == 5 and all(len(s["objects"]) == 5 for s in samples)
errors = [o["sampled_surface_bidirectional_max_error_m"] for s in samples for o in s["objects"].values()]
assert max(errors) < .0001
assert all(o["pass_0_1mm"] for s in samples for o in s["objects"].values())
assert read(QA / "final-review.json")["verdict"] == "NO_SHIP"

learning = read(QA / "workflow-learning.json")
for rule in learning["verified_this_turn"]:
    for relative in rule["evidence"]:
        assert (QA / relative).is_file(), relative
for failure in read(QA / "failure-classification.json")["failures"]:
    assert (QA / failure["evidence"]).is_file(), failure["evidence"]
# Check local Markdown links; inline code/API URLs are not artifact links.
for target in re.findall(r"\]\(([^)]+)\)", (QA / "README.md").read_text(encoding="utf-8")):
    if target != "final-verification.json":
        assert (QA / target).resolve().is_file(), target

index = read(ROOT / "library/index.json")
found = workbench.search_library(index, "RO")
entries = []
for entry in index["entries"]:
    if entry["id"] in {"ro-swordsman-combo-r006-hand-source", "ro-swordsman-combo-r006-v008"}:
        assert entry in found and entry["status"] == "needs_revision"
        assert entry["acceptance"]["delivery"] == "not_delivered"
        for relative in entry["files"] + [entry["qa_report"]]:
            path = (ROOT / relative).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), relative
        entries.append(entry["id"])
assert len(entries) == 2

scripts = sorted((ROOT / "scripts").glob("*.py"))
for script in scripts:
    ast.parse(script.read_text(encoding="utf-8-sig"), filename=str(script))
git_state = {}
for name, root, expected in [("isolated_worktree", ROOT, "c990639962b7ce85eb6beb631057aa4d76a3e86d"),
                             ("main_checkout", MAIN, "e077e22ba57447031b7cc89e3d37bd9cef47daf4")]:
    assert not git(root, "diff", "--cached", "--name-only")
    head = git(root, "rev-parse", "HEAD")
    assert head == expected, name
    git(root, "diff", "--check")
    git_state[name] = {"head": head, "staged_paths": [], "diff_check": "pass"}

checks = []
for name, args in [("unit-tests", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
                   ("pipeline-validation", ["scripts/pipeline.py", "validate"]),
                   ("api-entry-help", ["scripts/hyper3d_api.py", "--help"])]:
    started = datetime.now(timezone.utc)
    result = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    log = QA / (name + "-final.log")
    with log.open("x", encoding="utf-8") as stream:
        stream.write(result.stdout + result.stderr)
    assert result.returncode == 0, (name, result.returncode, log)
    check({"path": log.relative_to(ROOT).as_posix(), "sha256": sha(log)}, name)
    checks.append({"name": name, "argv": [sys.executable, "-B", *args], "exit_code": result.returncode,
                   "started_utc": started.isoformat(), "ended_utc": datetime.now(timezone.utc).isoformat(),
                   "log": log.relative_to(ROOT).as_posix()})

result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Offline archive/hash/bookkeeping and required tool tests; no new art/runtime/API acceptance",
    "integrity": "pass", "verified_artifacts": list(verified.values()),
    "public_json_reports_parsed": len(reports),
    "current_script_hashes": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in scripts],
    "historical_helper_versions": "Frozen baseline helper retained; do not claim complete dependency snapshots for every earlier prototype",
    "library_entries_checked": entries, "quality_comparison": comparison,
    "assessment_decision": assessment["decision"], "closed_phase_seconds": wall,
    "old_phase_and_original_targets_preserved": True,
    "api": {"state": "downloaded", "paid_generation_count_this_phase": 1,
            "service_reported_credits_this_phase": .5, "new_credits_during_final_verification": 0,
            "live_api_query_during_final_verification": False, "main_and_worktree_entry_identical": True},
    "authorized_private_state": {"path": str(private), "bytes": private.stat().st_size,
                                 "encrypted_file_sha256": sha(private), "private_decryption_this_check": False},
    "provider_and_old_policy_hashes_unchanged": [str(p) for p, _ in unchanged],
    "actual_local_roundtrip": {"reported_pass": True, "all61frames_evaluated": True,
                               "five_sample_surface_max_error_m": max(errors), "fresh_runtime_rerun_this_check": False},
    "checks_executed_this_check": checks, "git": git_state,
    "art_verdict": "NO_SHIP", "full300frame_skill_animation_verified": False,
    "effects_verified": False, "delivered": False, "stage_commit_push": "held by user",
    "task_owned_background_work": "none; coordinator observed all API/DCC/reviewer sessions completed",
    "global_blender_environment": "Earlier cleanup impact unresolved; not inspected/repaired or claimed all-pass",
}
with (QA / "final-verification.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"integrity": "pass", "artifacts": len(verified), "scripts": len(scripts),
                  "reports": len(reports), "tool_checks": [c["name"] for c in checks],
                  "quality": comparison["next_action"], "art_verdict": "NO_SHIP", "new_credits": 0}))
