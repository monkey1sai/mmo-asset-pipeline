"""Freeze actual assembly baseline and review before source-preserving refinement."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import workbench

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r005"
ID = "ro-swordsman-combo-r005"


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def artifact(relative):
    path = ROOT / relative
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


request = workbench.read_json(ROOT / "requests" / (ID + ".json"))
clock = workbench.read_json(QA / "phase-accounting.json")
report = workbench.read_json(QA / "baseline/assembly.json")
assert report["triangles"] == 55488 and report["bone_count"] == report["animations"] == 0
review = {"reviewer": "Independent batch_review; actual five baseline PNGs and full request anchors",
    "views": request["quality"]["protocol"]["views"], "scores": {
        "design-intent": {"value": 3, "reason": "Core swordsman colors/equipment present; face blurred and chest/back armor obscured by clothing."},
        "silhouette": {"value": 3, "reason": "Front readable; side/back equipment relations unstable, pants protrude through rear garment."},
        "form-proportion": {"value": 2, "reason": "Torso armor does not contain the torso; bracers not fitted to forearm axes; hip garment volume insufficient; sword grip unformed."},
        "materials": {"value": 2, "reason": "Metal/leather/cloth types recognizable; face/eyes/hairline smeared and hair highlights inconsistent."},
        "craft": {"value": 1, "reason": "Large chest/collar/back, bracer/glove and hip/garment intersections; open hand does not grip sword."},
        "use-readability": {"value": 0, "reason": "Observed zero rig/animation; requested continuous skills and effects absent."}},
    "acceptance": "NO_SHIP baseline. Source geometry completeness does not establish fit, anatomy, rig or animation."}
save(QA / "baseline/independent-review.json", review)
content = [artifact("assets/processed/" + ID + "/baseline/ro_batch_assembly_baseline" + ext) for ext in (".blend", ".glb")]
support = [artifact("runs/qa/" + ID + "/baseline/" + name) for name in ("assembly.json", "independent-review.json")]
checks = {item["id"]: {"status": "fail", "method": "Baseline is incomplete for the full request: observed static8-object assembly/zero rig/animation and independent five-view fit/material failures. Required absent features are not passed; animated runtime and final package not performed.", "artifacts": support} for item in workbench.required_checks(request)}
evidence = {"schema_version": 1, "request_id": ID, "request_sha256": workbench.request_sha256(request),
    "checks": checks, "subject_artifacts": content, "deliverables": content}
ended = datetime.now(timezone.utc)
started = datetime.fromisoformat(clock["baseline_started_utc"])
trial = {"id": "baseline", "parent_id": None, "status": "completed", "started_utc": started.isoformat(),
    "ended_utc": ended.isoformat(), "elapsed_seconds": (ended - started).total_seconds(),
    "protocol_sha256": workbench.quality_sha256(request), "reviewer": review["reviewer"],
    "previews": {view: artifact("runs/qa/" + ID + "/baseline/" + view + ".png") for view in review["views"]},
    "scores": review["scores"], "evidence": evidence}
ledger = {"schema_version": 1, "request_id": ID, "request_sha256": workbench.request_sha256(request),
    "protocol_sha256": workbench.quality_sha256(request), "trials": [trial],
    "phase_accounting": "Original r004 time, all preparatory/generation/inspection/review time and three revisions carried forward; no reset."}
result = workbench.compare_quality(request, ledger)
if result["blockers"]:
    raise RuntimeError(result)
save(QA / "baseline/evidence.json", evidence)
save(QA / "quality-ledger.json", ledger)
save(QA / "comparison-baseline.json", result)
save(QA / "v001-start.json", {"id": "v001", "parent_id": "baseline", "started_utc": ended.isoformat(),
    "hypothesis": "Independent generated equipment can be fitted to measured body surfaces while preserving source geometry/UVs; rigid equipment and separate cloth then permit source-preserving functional validation.",
    "dependency_order": ["body-surface volume fit", "rig/weights and functional stress poses", "only after passing preflight, full sequence/export"],
    "stage_outputs": "Intermediate diagnostic masters preserve all steps; no keep or delivery decision until required candidate evidence is complete.",
    "revision_count_reserved": 1, "max_revisions": 3, "clock_reset": False})
print(json.dumps({"baseline_frozen": True, "scores": {k: v["value"] for k, v in review["scores"].items()}, "comparison": result}, ensure_ascii=False))
