"""One-off static evidence capture for this blocked P4 task; no DCC/trial/network calls."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import identity
import pipeline
import workbench

destination = OUT / "verification-v001.json"
if destination.exists():
    raise SystemExit("REFUSE_OVERWRITE verification-v001.json")


def load(path):
    return identity.read_json(identity.recorded_path(ROOT, path))


def artifact(path):
    target = identity.recorded_path(ROOT, path)
    return {"path": path, "bytes": target.stat().st_size, "sha256": identity.file_digest(target)}


def check_artifact(expected):
    actual = artifact(expected["path"])
    assert actual["sha256"] == expected["sha256"], expected["path"]
    if "bytes" in expected:
        assert actual["bytes"] == expected["bytes"], expected["path"]
    actual["status"] = "PASS_FILE_IDENTITY_ONLY"
    return actual


plan = load("runs/qa/gait-p4-natural-motion-20261007/ab-plan.json")
request = load(plan["request"]["path"])
freeze = load("runs/qa/ro-swordsman-character-v1-r6/freeze.json")
assert not workbench.validate_request(request)
assert request["quality"]["status"] == "frozen"
assert identity.json_digest(request) == plan["request"]["request_sha256"] == freeze["request"]["request_sha256"]
assert identity.json_digest(request["quality"]) == plan["request"]["quality_sha256"] == freeze["request"]["protocol_sha256"]

baseline = plan["baseline_a"]
actual_artifacts = [check_artifact(baseline[name]) for name in ("foundation", "action", "glb")]
assert (ROOT / baseline["foundation"]["path"]).read_bytes()[:7] == b"BLENDER"
assert (ROOT / baseline["action"]["path"]).read_bytes()[:7] == b"BLENDER"
inventory = pipeline.inspect_glb((ROOT / baseline["glb"]["path"]).read_bytes())
assert inventory["sha256"] == baseline["glb"]["sha256"]
assert inventory["skins"] == 1 and inventory["animations"] == 1

clip_check = load(baseline["historical_clip_check"])
for name, source_name in (("foundation", "foundation"), ("action", "clip_blend")):
    assert clip_check["subject"][source_name]["sha256"] == baseline[name]["sha256"]
references = [check_artifact(clip_check[name]) for name in ("interaction", "rules", "fixtures", "contract")]
interaction = load(baseline["interaction"])
contact = plan["comparison"]["contact"]
assert interaction["stance"]["R"] == [contact["stance_R_inclusive_frames"]]
assert interaction["stance"]["L"] == [contact["stance_L_inclusive_frames"]]
assert interaction["states"]["grasp.R"]["windows"] == [contact["grasp_R_inclusive_frames"]]
assert interaction["nominal_speed_m_s"] == plan["comparison"]["nominal_speed_m_s"]
assert set(plan["comparison"]["playback_speeds"]) <= set(request["transition_matrix"]["playback_speed"])
assert plan["candidate_b"] is None and plan["budget"]["new_trial_created"] is False
assert all(value is False for value in plan["execution"].values())

pause_path = "runs/qa/ro-swordsman-character-v1/v001/v001-pause-31.json"
pause = load(pause_path)
assert len(pause["intervals_seconds"]) == len(pause["interval_starts_utc"]) == 36
assert sum(pause["intervals_seconds"]) == pause["active_seconds_total"] == 54306
assert request["quality"]["budget"]["total_seconds"] == 172800
assert request["production"]["max_revisions"] == 4
ledger_path = "runs/qa/ro-swordsman-character-v1-r6/quality-ledger.json"
ledger = load(ledger_path)
assert [(trial["id"], trial["elapsed_seconds"]) for trial in ledger["trials"]] == [("baseline", 2641.0)]

progress_path = plan["known_failures_preserved"]["source"]
progress = load(progress_path)
closed_loop = progress["runtime"]["closed_loop"]
assert closed_loop["passed_blocks"] == 116 and closed_loop["blocks"] == 118
assert closed_loop["max_error_um"] == plan["known_failures_preserved"]["runtime_max_error_um"]
assert closed_loop["gate_um"] == 10 and progress["runtime"]["pass"] is False

paths = {ROOT / plan["request"]["path"], ROOT / pause_path, ROOT / ledger_path, ROOT / progress_path}
for name in ("scripts", "tests", "tools", ".github"):
    for path in (ROOT / name).rglob("*"):
        if path.is_file() and path.suffix in {".py", ".js", ".mjs", ".json", ".html", ".yml", ".toml"} and not any(part in {"node_modules", "__pycache__", ".venv"} for part in path.parts):
            paths.add(path)
for path in (ROOT / "runs/qa/art-tools-upgrade-20261007").rglob("*"):
    if path.is_file():
        paths.add(path)
for entry in references:
    paths.add(ROOT / entry["path"])
protected = [artifact(path.relative_to(ROOT).as_posix()) for path in sorted(paths)]

result = {
    "schema_version": 1,
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "overall_status": "BLOCKED_BEFORE_ANIMATION_TRIAL",
    "capture_script": artifact(Path(__file__).relative_to(ROOT).as_posix()),
    "comparison_plan": artifact("runs/qa/gait-p4-natural-motion-20261007/ab-plan.json"),
    "comparison_plan_canonical_sha256": identity.json_digest(plan),
    "request": {"status": "PASS_IDENTITY_AND_SCHEMA_ONLY", "request_sha256": identity.json_digest(request), "quality_sha256": identity.json_digest(request["quality"]), "pending": workbench.readiness(request)},
    "baseline_artifacts": actual_artifacts,
    "source_qa_references": references,
    "inventory": inventory,
    "historical_clip_check": {"record": artifact(baseline["historical_clip_check"]), "sample_count": len(clip_check["samples"]), "failure_count": len(clip_check["failures"]), "fresh_execution": False},
    "snapshot_clock_arithmetic": {"status": "PASS_SNAPSHOT_ARITHMETIC_ONLY", "record": artifact(pause_path), "intervals": 36, "active_seconds_total": 54306, "recorded_utc": pause["recorded_utc"], "current_remaining_seconds": None},
    "r6_ledger": {"record": artifact(ledger_path), "trials": [{"id": trial["id"], "elapsed_seconds": trial["elapsed_seconds"]} for trial in ledger["trials"]], "v001_elapsed_entry_present": False, "is_current_consumption_evidence": False},
    "protected_files": protected,
    "protected_files_scope": "Static source bytes and selected historical records; no fresh DCC category signatures. Compare this list at handoff. Git diff separately verifies equality to the engineering checkpoint.",
    "fresh_motion_baseline": "NOT_RUN",
    "candidate_ab": "NOT_RUN",
    "candidate_protected_categories": "NOT_RUN",
    "candidate_gates": "NOT_RUN",
    "budget_admission": "UNVERIFIED",
    "scores": None,
    "paid_calls": 0,
    "new_trial_created": False,
    "art_accepted": False,
    "technical_accepted": False
}
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"record": destination.relative_to(ROOT).as_posix(), "status": result["overall_status"], "payloads_verified": len(actual_artifacts), "protected_files_recorded": len(protected), "new_trial_created": False, "fresh_motion_baseline": "NOT_RUN"}, ensure_ascii=False))
