"""Verify prepared r007 evidence and run required local tool checks.

No network, paid submission, private decryption, global writes, DCC execution,
or Git mutations. Archive integrity does not establish art acceptance.
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
from hyper3d_api import Client, PROVIDER, PROVIDER_SHA256

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(r"C:\Repos\mmo-asset-pipeline")
QA = ROOT / "runs/qa/ro-swordsman-combo-r007"
OPERATION = "ro-hand-structure-20261003-001"
verified = {}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(item, evidence):
    path = (ROOT / item["path"]).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), item["path"]
    assert sha(path) == item["sha256"], (evidence, item["path"])
    size = path.stat().st_size
    if "bytes" in item:
        assert size == item["bytes"], item["path"]
    record = verified.setdefault(item["path"], {
        "path": item["path"], "sha256": item["sha256"], "bytes": size,
        "evidence": [],
    })
    if evidence not in record["evidence"]:
        record["evidence"].append(evidence)


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
    result = subprocess.run(["git", "-C", str(root), *args], check=True,
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip()


destination = QA / "preparation-verification.json"
assert not destination.exists(), "Preserve completed verification records"
request = read(ROOT / "requests/ro-swordsman-combo-r007.json")
old_request = read(ROOT / "requests/ro-swordsman-combo-r006.json")
assert request["spec"] == old_request["spec"]
assert request["quality"]["dimensions"] == old_request["quality"]["dimensions"]
clock = read(QA / "phase-start.json")
assert workbench.request_sha256(request) == clock["request_sha256"]
assert workbench.quality_sha256(request) == clock["protocol_sha256"]
history = clock["prior_phase_history"]
assert workbench.request_sha256(old_request) == history["previous_request_sha256"]
assert sha(ROOT / history["previous_result"]) == history["previous_result_sha256"]
old_ledger = read(ROOT / "runs/qa/ro-swordsman-combo-r006/quality-ledger.json")
old_comparison = workbench.compare_quality(old_request, old_ledger, ROOT)
assert old_comparison == read(ROOT / history["previous_result"])
assert old_comparison["candidate_trials_used"] == 8
assert old_comparison["next_action"] == "stop_budget"

reports = sorted(QA.rglob("*.json"))
for path in reports:
    walk(read(path), path.relative_to(ROOT).as_posix())
walk(request["quality"]["reference_artifacts"], "request reference artifacts")
ledger = read(QA / "quality-ledger.json")
assert len(ledger["trials"]) == 1 and ledger["trials"][0]["id"] == "baseline"
original_ledger = read(QA / "quality-ledger-before-local-clarification.json")
assert ledger["trials"][0]["scores"] == original_ledger["trials"][0]["scores"]
assert ledger["trials"][0]["started_utc"] == clock["baseline_started_utc"]
comparison = workbench.compare_quality(request, ledger, ROOT)
assert comparison == read(QA / "comparison-baseline-v2.json")
assert comparison["candidate_trials_used"] == 0 and not comparison["blockers"]
assert comparison["next_action"] == "revise_current_best"
assert not comparison["quality_target_met"]
assessment = workbench.assess(request, read(QA / "baseline/assessment-evidence-v2.json"), ROOT)
assert assessment == read(QA / "assessment-preparation.json")
assert assessment["decision"] == "not_ready"

interval = read(QA / "baseline/baked-interval.json")
samples = interval["samples"]
assert interval["frames"] == 61 and interval["half_frame_diagnostics"] == 60
assert len(samples) == 121
assert [s["frame"] for s in samples] == [1 + i / 2 for i in range(121)]
crossings = sum(s["sword_transverse_pairs"] > 0 for s in samples)
maximum = max(s["maximum_penetration_m"] for s in samples)
assert crossings == 118 and abs(maximum - .00734470970928669) < 1e-12
assert not interval["baked_interval_collision_pass"]
assert not interval["baked_interval_art_pass"] and interval["original_source_unchanged"]
assert interval["new_geometry_versions"] == 0 and interval["search_evaluations"] == 0
images = sorted((QA / "baseline").rglob("*.png"))
assert len(images) == 25
for path in images:
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), str(path)
    check({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}, "actual baseline PNG")
blend = ROOT / "assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend"
glb = ROOT / "assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.glb"
assert sha(blend) == "e1b17ac13d8677ef4914995e3308b18e99fd22f694c7fd240c541e74701d178e"
assert sha(glb) == "027cf2501619b4262ea8b040618364d2e756e6a3f476e12ed827fff9fadd2985"

client = Client(ROOT)
plan = client.plan(OPERATION)
assert not client.record_path(OPERATION).exists()
assert not client.private_path(OPERATION).exists()
assert plan["plan_sha256"] == read(QA / "generation-prepared.json")["plan_sha256"]
assert plan["estimated_credits"] == .5
assert plan["parameters"]["geometry_file_format"] == "obj"
assert plan["parameters"]["mesh_mode"] == "Quad"
assert plan["parameters"]["quality_override"] == 1200
assert plan["parameters"]["image_label"] == ["F", "B"]
assert len(plan["images"]) == 2
assert plan["authorization"]["credit_pool"] == "existing_monthly_or_regular"
assert plan["authorization"]["no_topup_or_upgrade"] is True
for item in plan["images"]:
    check(item, "API input design")
assert sha(PROVIDER) == PROVIDER_SHA256
policy = PROVIDER.parent / "authorization.json"
assert sha(policy) == "431e94888757628d6d7e6dcc42938bb5f0e2a2b1920a9fd9b7fd9cbf80e4ca10"
assert sha(ROOT / "scripts/hyper3d_api.py") == sha(MAIN / "scripts/hyper3d_api.py")
for target in re.findall(r"\]\(([^)]+)\)", (QA / "README.md").read_text(encoding="utf-8")):
    if target.startswith("https://") or target == destination.name:
        continue
    assert (QA / target).resolve().is_file(), target
scripts = sorted((ROOT / "scripts").glob("*.py"))
for script in scripts:
    ast.parse(script.read_text(encoding="utf-8-sig"), filename=str(script))

git_state = {}
for name, root, expected in [
    ("isolated_worktree", ROOT, "c990639962b7ce85eb6beb631057aa4d76a3e86d"),
    ("main_checkout", MAIN, "e077e22ba57447031b7cc89e3d37bd9cef47daf4"),
]:
    assert not git(root, "diff", "--cached", "--name-only")
    head = git(root, "rev-parse", "HEAD")
    assert head == expected, name
    git(root, "diff", "--check")
    git_state[name] = {"head": head, "staged_paths": [], "diff_check": "pass"}

checks = []
for name, args in [
    ("unit-tests", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("pipeline-validation", ["scripts/pipeline.py", "validate"]),
    ("api-entry-help", ["scripts/hyper3d_api.py", "--help"]),
]:
    started = datetime.now(timezone.utc)
    result = subprocess.run([sys.executable, "-B", *args], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = QA / (name + "-preparation.log")
    with log.open("x", encoding="utf-8") as stream:
        stream.write(result.stdout + result.stderr)
    assert result.returncode == 0, (name, result.returncode, str(log))
    check({"path": log.relative_to(ROOT).as_posix(), "sha256": sha(log)}, name)
    checks.append({"name": name, "argv": [sys.executable, "-B", *args],
                   "exit_code": result.returncode, "started_utc": started.isoformat(),
                   "ended_utc": datetime.now(timezone.utc).isoformat(),
                   "log": log.relative_to(ROOT).as_posix()})

now = datetime.now(timezone.utc)
result = {
    "observed_utc": now.isoformat(), "integrity": "pass",
    "scope": "Prepared local archive and tool verification; no new model or art acceptance",
    "verified_artifacts": list(verified.values()), "public_json_parsed": len(reports),
    "script_hashes": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in scripts],
    "original_spec_and_quality_dimensions_preserved": True,
    "old_closed_phase_and_original_source_preserved": True,
    "baseline_blend_and_glb_are_byte_identical_failed_v008": True,
    "actual_baseline_pngs": len(images),
    "actual_saved_clip_diagnostic": {"frames": 61, "half_frames": 60, "samples": 121,
        "samples_with_sword_crossings": crossings, "maximum_penetration_m": maximum,
        "interval_collision_pass": False, "continuous_collision_freedom_proven": False},
    "comparison": comparison, "assessment_decision": assessment["decision"],
    "phase_wall_seconds_so_far": (now - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds(),
    "phase_clock_reset": False, "checks_executed_this_check": checks,
    "api": {"state": "prepared_not_submitted", "operation_id": OPERATION,
        "private_file_exists": False, "paid_submissions_this_phase": 0,
        "new_Hyper3D_credits": 0, "native_OBJ_runtime_verified": False,
        "main_and_worktree_entry_identical": True, "provider_and_old_policy_unchanged": True,
        "resume_gate": "Human exact-file write authority for this new operation's DPAPI file"},
    "git": git_state, "art_verdict": "NO_SHIP", "delivered": False,
    "full300frame_skill_animation_verified": False, "effects_verified": False,
    "stage_commit_push": "held by user", "task_owned_background_work": "none",
}
with destination.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"integrity": "pass", "artifacts": len(verified), "scripts": len(scripts),
                  "reports": len(reports), "baseline_PNGs": len(images), "samples": 121,
                  "crossing_samples": crossings, "new_Hyper3D_charge": 0,
                  "assessment": "not_ready", "tool_checks": [c["name"] for c in checks]}))
