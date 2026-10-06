"""Verify batch preparation and the actual historical downloader contract, uncharged."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import workbench
from hyper3d_api import Client, read_json

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r005"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path = QA / "preparation-verification.json"
    if report_path.exists():
        raise RuntimeError("Preserve prior verification")
    parent = read_json(ROOT / "requests/ro-swordsman-combo-r004.json")
    current = read_json(ROOT / "requests/ro-swordsman-combo-r005.json")
    preflight = read_json(ROOT / "requests/ro-swordsman-combo-r005-preflight.json")
    preflight_before = read_json(QA / "preflight-before-text-correction.json")
    for key in ("dimensions", "protocol", "budget"):
        assert current["quality"][key] == parent["quality"][key], key
    assert current["spec"] == parent["spec"]
    assert current["production"]["max_revisions"] == parent["production"]["max_revisions"] == 3
    assert preflight["quality"] == preflight_before["quality"]
    assert preflight["spec"] == preflight_before["spec"]
    assert not any("Six initial" in x for x in preflight["assumptions"])
    assert not workbench.validate_request(current)
    assert not workbench.validate_request(preflight)
    clock = read_json(QA / "phase-accounting.json")
    parent_clock = read_json(ROOT / clock["parent_clock"])
    assert clock["baseline_started_utc"] == parent_clock["baseline_started_utc"]
    assert clock["parent_clock_sha256"] == digest(ROOT / clock["parent_clock"])
    assert clock["clock_reset"] is False
    manifest = read_json(ROOT / "assets/raw/ro-swordsman-combo/design-v004/manifest.json")
    for image in manifest["files"]:
        assert digest(ROOT / image["path"]) == image["sha256"]
    client = Client(ROOT)
    plan = client.plan("ro-split-batch-20261003-001")
    old_operations = read_json(ROOT / "runs/qa/ro-swordsman-combo-r004/generation-prepared.json")["operations"]
    operations = [x["operation_id"] for x in old_operations] + [plan["operation_id"]]
    assert not any(client.record_path(op).exists() or client.private_path(op).exists() for op in operations)
    for old in old_operations:
        assert client.plan(old["operation_id"])["plan_sha256"] == old["plan_sha256"]
    # Execute only the pure source-boundary functions; never import bpy or launch Blender.
    inspector = ROOT / "scripts/inspect_ro_batch_source.py"
    parsed = ast.parse(inspector.read_text(encoding="utf-8"))
    functions = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in {"digest", "bound_source"}]
    namespace = {"hashlib": hashlib, "Path": Path}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(inspector), "exec"), namespace)
    historical = read_json(ROOT / "runs/hyper3d/operations/ro-swordsman-apose-20261002-001.json")
    raw = ROOT / "assets/raw/ro-swordsman-combo/rodin-v002"
    source, source_hash = namespace["bound_source"](ROOT, raw, historical["downloads"])
    assert digest(source) == source_hash
    failures = []
    cases = {"outside_expected_raw": (ROOT / "assets/raw/ro-swordsman-combo/rodin-v004/batch", historical["downloads"]),
        "hash_mismatch": (raw, deepcopy(historical["downloads"]))}
    next(x for x in cases["hash_mismatch"][1] if x["path"].endswith(".glb"))["sha256"] = "0" * 64
    for name, (directory, downloads) in cases.items():
        try:
            namespace["bound_source"](ROOT, directory, downloads)
        except RuntimeError:
            failures.append(name)
        else:
            raise AssertionError("Unexpected boundary acceptance: " + name)
    report = {"verified_utc": datetime.now(timezone.utc).isoformat(), "status": "preparation_verified_not_generated",
        "requests_valid": [current["id"], preflight["id"]], "parent_quality_targets_spec_budget_unchanged": True,
        "clock_reset": False, "r004_clock_elapsed_seconds": (datetime.now(timezone.utc) - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds(),
        "source_binding": {"fixture_kind": "actual previous downloaded GLB and downloader journal",
            "fixture_operation": historical["operation_id"], "valid_path_contract_pass": True,
            "rejected_cases": failures, "fixture_hash_unchanged": True},
        "batch_blender_execution": "not_run_no_batch_download", "batch_3d_generated": False,
        "batch_semantic_parts_accepted": False, "rig_animation_or_delivery_accepted": False,
        "global_state_files_written": 0, "new_hyper3d_paid_submissions": 0,
        "existing_six_plans_preserved_not_submitted": True,
        "connectivity": {"source": "mcp__hyper3d_api__rodin_balance observed this turn", "authenticated": True,
            "balance": 229, "charged": False, "pool_breakdown": "not_returned"},
        "required_checks": {"unittest": {"command": "python -B -m unittest discover -s tests -v", "passed": 116, "seconds": 1.946},
            "pipeline": {"command": "python -B scripts/pipeline.py validate", "valid_schema_assets": 39},
            "scripts_syntax": "AST parse passed", "diff_check": "passed; existing library CRLF warning"},
        "preflight_text_correction": {"before": digest(QA / "preflight-before-text-correction.json"),
            "after": digest(ROOT / "requests/ro-swordsman-combo-r005-preflight.json"), "quality_spec_unchanged": True},
        "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in
            [ROOT / "requests/ro-swordsman-combo-r005.json", ROOT / "requests/ro-swordsman-combo-r005-preflight.json",
             inspector, ROOT / "scripts/prepare_ro_batch_source.py", QA / "api-spec-batch.json", QA / "generation-prepared.json"]],
        "held": "Exact new global state-file authority pending; spending already authorized. Stage/commit/push await user validation."}
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "source_boundary_checks": 3,
        "batch_paid_submissions": 0, "global_writes": 0, "report": str(report_path)}))


if __name__ == "__main__":
    main()
