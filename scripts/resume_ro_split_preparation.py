"""Finish public plans after the recorded uncharged preparation signature error."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import workbench
from hyper3d_api import Client, read_json

root = Path(__file__).resolve().parents[1]
qa = root / "runs/qa/ro-swordsman-combo-r004"
client = Client(root)
source_manifest = read_json(root / "assets/raw/ro-swordsman-combo/design-v003/manifest.json")
for item in source_manifest["files"]:
    if hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
        raise RuntimeError("Design drift")
request = read_json(root / "requests/ro-swordsman-combo-r004.json")
clock = read_json(qa / "phase-start.json")
if workbench.request_sha256(request) != clock["request_sha256"]:
    raise RuntimeError("Frozen request drift")
template = read_json(qa / "api-spec-core.json")
parts = [("core", "Quad", 12000, "F", "symmetric"),
         ("cuirass", "Raw", 3000, "FL", "balanced"),
         ("pauldron", "Raw", 2000, "FL", "asymmetric"),
         ("bracer", "Raw", 2000, "FL", "asymmetric"),
         ("coat", "Raw", 5000, "F", "balanced"),
         ("sword", "Raw", 1500, "F", "symmetric")]


def save(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


if (qa / "generation-prepared.json").exists():
    raise RuntimeError("Completed preparation must not be overwritten")
operations = []
for index, (part, mode, faces, label, symmetry) in enumerate(parts):
    spec = deepcopy(template)
    operation = f"ro-split-{part}-20261003-001"
    spec.update(operation_id=operation,
        images=[f"assets/raw/ro-swordsman-combo/design-v003/{part}.png"],
        output_directory=f"assets/raw/ro-swordsman-combo/rodin-v003/{part}")
    spec["parameters"].update(mesh_mode=mode, quality_override=faces,
        quad_normal=mode == "Quad", TAPose=part == "core", is_symmetric=symmetry,
        image_label=[label], seed=4400 + index)
    spec_path = qa / f"api-spec-{part}.json"
    if spec_path.exists():
        if read_json(spec_path) != spec:
            raise RuntimeError("Existing spec differs; stop")
    else:
        save(spec_path, spec)
    client.prepare(spec)
    plan = client.plan(operation)
    operations.append({"part": part, "operation_id": operation,
        "estimated_credits": plan["estimated_credits"], "plan_sha256": plan["plan_sha256"],
        "global_task_file": str(client.private_path(operation)),
        "global_file_exists_before": client.private_path(operation).exists(),
        "status": "prepared_not_submitted", "output_directory": spec["output_directory"]})
save(qa / "preparation-recovery.json", {"classification": "TEST_FAILURE", "observed_error": "SPEC_FIELDS_INVALID",
    "cause": "Preparation helper passed a spec path instead of the required parsed dictionary.",
    "charged_calls": 0, "fix": "Pass parsed spec; finish only missing public plans, preserve design/request/clock.",
    "old_history_modified": False})
save(qa / "generation-prepared.json", {"operations": operations,
    "estimated_initial_credits": sum(x["estimated_credits"] for x in operations),
    "spending_authority": "Already granted; no new points approval requested.",
    "global_write_authority": "Awaiting exact six new task files; prior single-task authority remains scoped to its old operation.",
    "envelope": {"destination": "https://api.hyper3d.com/api/v2/rodin", "purpose": "Six designed parts for one RO character",
        "allowed_operations": ["one initial generation per prepared part", "same-task status", "completed result download"],
        "data_transmitted": ["six new design images, one per task", "validated nonsecret parameters"],
        "forbidden_operations": ["topup", "upgrade", "secret output", "old state overwrite", "Git mutation"],
        "stop_conditions": ["unknown/pending submission", "unexpected destination", "file collision", "global write authority missing"]}})
save(qa / "offline-plan.json", workbench.production_plan(request))
print(json.dumps({"prepared": operations, "charged": False}, ensure_ascii=False))
