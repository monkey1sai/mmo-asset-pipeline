"""Integration checks for the actual Blender inspection tool."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--blender", required=True)
args = parser.parse_args()
output = ROOT / "artifacts" / "blender-checks" / uuid.uuid4().hex
output.mkdir(parents=True)
temp = output / "temp"
temp.mkdir()
environment = dict(os.environ, TEMP=str(temp), TMP=str(temp))
prefix = [args.blender, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "2", "--python"]
generation = subprocess.run(prefix + [str(ROOT / "tests/make_blender_fixtures.py"), "--", str(output)], env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
(output / "fixture.log").write_text(generation.stdout + generation.stderr, encoding="utf-8")
if generation.returncode:
    raise SystemExit("TEST_FAILURE: synthetic fixture creation failed; see artifacts log")

cases = [
    ("static", "static.blend", 12, False, "PASS", None),
    ("fbx", "static.fbx", 12, False, "PASS", None),
    ("over_budget", "static.blend", 1, False, "FAIL", "budget exceeded"),
    ("unbound", "static.blend", 12, True, "FAIL", "armature binding"),
    ("no_uv", "no_uv.blend", 12, False, "FAIL", "missing UVs"),
    ("skin_valid", "skin_valid.blend", 12, True, "PASS", None),
    ("rigid_valid", "rigid_valid.blend", 24, True, "PASS", None),
    ("bad_sum", "bad_sum.blend", 12, True, "FAIL", "unnormalized=8"),
    ("too_many", "too_many.blend", 12, True, "FAIL", "excessive=8"),
    ("non_deform", "non_deform_groups.blend", 12, True, "FAIL", "unweighted=8"),
    ("bad_parent", "bad_parent.blend", 12, True, "FAIL", "Invalid parent: hand_r"),
]
results = []
for name, filename, budget, rigged, expected, evidence in cases:
    source = output / filename
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    report_path = output / (name + ".json")
    command = prefix + [str(ROOT / "tools/blender/inspect_asset.py"), "--", "--input", str(source), "--report", str(report_path), "--tri-budget", str(budget)]
    if rigged:
        command += ["--rig-profile", "humanoid-v1"]
    result = subprocess.run(command, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    (output / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    success = (
        report.get("technical_status") == expected
        and (result.returncode == 0 if expected == "PASS" else result.returncode != 0)
        and report.get("production_status") == "UNVERIFIED"
        and report.get("source_sha256") == digest
        and hashlib.sha256(source.read_bytes()).hexdigest() == digest
        and (evidence is None or any(evidence in e for e in report.get("errors", [])))
    )
    results.append({"case": name, "expected": expected, "observed": report.get("technical_status"), "check": "PASS" if success else "FAIL", "exit_code": result.returncode})
    print(f"{name}: {'PASS' if success else 'FAIL'} (expected model status {expected})", flush=True)
summary = {"fixture_scope": "synthetic technical inputs, not art or Unity acceptance", "results": results, "passed": sum(r["check"] == "PASS" for r in results), "total": len(results)}
(output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print("Evidence: " + str(output.relative_to(ROOT)))
raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
