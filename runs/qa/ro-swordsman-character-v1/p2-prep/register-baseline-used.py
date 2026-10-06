"""Register the real baseline as the first quality-ledger trial for ro-swordsman-character-v1.

Run from the repo root after the request is frozen:
  python -B runs/qa/ro-swordsman-character-v1/p2-prep/register-baseline-used.py <started_utc> <ended_utc> <elapsed_seconds>
The baseline is the unmodified whole character (NO_SHIP source). Every required check is reviewed and
most fail; nothing here is an acceptance. The ledger file is created once and never overwritten.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import workbench

QA = "runs/qa/ro-swordsman-character-v1"
R010 = "runs/qa/ro-swordsman-combo-r010/baseline"
started, ended, elapsed = sys.argv[1], sys.argv[2], float(sys.argv[3])


def art(path):
    return {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


request = json.loads((ROOT / "requests/ro-swordsman-character-v1.json").read_text(encoding="utf-8"))
assert request["status"] == "specified" and request["quality"]["status"] == "frozen"
request_sha, protocol_sha = workbench.request_sha256(request), workbench.quality_sha256(request)

INSPECT = art(f"{QA}/p0-whole-baseline-inspect.json")
JOINTS = art(f"{QA}/p2-prep/baseline-joint-range-v2/joint-range-result.json")
ROUNDTRIP = art(f"{QA}/p2-prep/weights-probe/roundtrip-as-exported.json")
P1 = art(f"{QA}/p1/runtime/p1-20261005t034404z-runtime-results.json")
P1_REPORT = art(f"{QA}/p1/p1-report.md")
OLD_REVIEW = art("runs/qa/ro-swordsman-combo-r007/baseline/review.json")
OLD_INTERVAL = art("runs/qa/ro-swordsman-combo-r007/baseline/baked-interval.json")
VIEWS = {view: art(f"{R010}/{view}.png") for view in ("front", "side", "back", "three-quarter", "detail")}
FRONT, DETAIL = VIEWS["front"], VIEWS["detail"]


def check(status, method, *artifacts):
    return {"status": status, "method": method, "artifacts": list(artifacts)}


checks = {
    "art_match": check("fail", "Viewed the five fixed views of this exact file: character reads correctly, but painted armor patches on the cloth core overlap the cuirass, the right wrist fitting is bulbous and the grasp is a prototype.", FRONT, DETAIL, OLD_REVIEW),
    "scale_pivot": check("pass", "Read-only Blender inventory: core height 1.74 m, armature and meshes at world origin with unit scale; GLB accessor bounds Y 0..1.74 with +Y up. Scope: size, axis and ground pivot only.", INSPECT),
    "geometry_materials": check("fail", "57,039 triangles measured (budget 60,000) and 2K textures present, but every mesh has open boundary edges of undiagnosed cause, armor and core overlap visibly, and the right hand is a different source than the r010 hand.", INSPECT, FRONT),
    "package_complete": check("fail", "Only the baseline BLEND and GLB exist; no clips, interaction data, QA scene package, README or manifest for this request.", INSPECT),
    "rig_mapping": check("fail", "53 bones: right thumb has 2 segments, left fingers 2 segments each, no control layer. Five contract motions cannot be posed because the bones are missing, and no grasp pose asset exists.", INSPECT, JOINTS),
    "deformation": check("fail", "Joint-range sweep on this file: 36 of 73 contract motions fail or cannot be posed (triangle collapse at shoulders, elbow and spine twist; hand-region intersections at typical angles; toes carry no weights).", JOINTS),
    "animation": check("fail", "Only the 61-frame wrist-grip prototype action exists; none of the nine listed clips is present.", INSPECT),
    "export-roundtrip": check("fail", "Fresh-Blender readback of this file as exported: maximum 14.55 um on 8 samples, above the 5 um world-space tolerance, because the exporter drops skin weights <= 1e-4; no listed clip exists to read back.", ROUNDTRIP, P1_REPORT),
    "skill-effects": check("fail", "No slash, fire or golden effect objects exist in the inspected file.", INSPECT),
    "grasp-contact-windowed": check("fail", "Earlier interval readback of this same file (identical SHA) shows sword crossings before the closed endpoint; no windowed grasp verification exists for any listed clip.", OLD_INTERVAL, OLD_REVIEW),
    "joint-range": check("fail", "scripts/cv1_joint_range.py with the frozen contract: numeric gate false, 27 motions fail and 9 cannot be posed (5 missing bones, 4 missing the grasp pose).", JOINTS),
    "clip-set": check("fail", "No listed clip exists to sample.", INSPECT),
    "transition-interaction": check("fail", "No clips, sockets or bed interaction exist to transition between.", INSPECT),
    "runtime-closed-loop": check("fail", "P1 proved the wiring on this file at a 100 um gate with a probe rule only; the frozen 10 um runtime tolerance is not met (14.7 um) and no accepted corrective rules or clips exist.", P1, P1_REPORT),
    "frozen-holdout-reuse": check("fail", "No frozen character base exists and the holdout has not been revealed.", INSPECT),
    "negative-controls": check("fail", "Only the four P1 probe controls exist; weapon-inside-hand and wrong-contact-window controls have not been built.", P1),
    "performance-report": check("fail", "No frame-time measurement exists; the P1 timing is CPU vertex comparison, not rendering cost.", P1_REPORT),
    "target_environment": check("fail", "Three.js 0.186.0 QA scene loaded this file only for the P1 wiring probe; none of the listed clips, transitions or corrective rules exists to verify in the target environment.", P1, P1_REPORT),
    "art-motion-review": check("fail", "No motion exists to review and no independent art review has been run for this request.", JOINTS),
}
deliverables = [art("assets/processed/ro-swordsman-combo-r010/baseline/ro_whole_baseline.blend"), art("assets/processed/ro-swordsman-combo-r010/baseline/ro_whole_baseline.glb")]
evidence = {"schema_version": 1, "request_id": request["id"], "request_sha256": request_sha, "checks": checks, "deliverables": deliverables, "subject_artifacts": deliverables}
scores = {
    "design-intent": {"value": 3, "reason": "Brown spiky hair, anime face, silver plate, blue coat with white tabard, leather gloves, belt and boots and a straight sword are all present; armor patches painted on the cloth core clash with the separate cuirass."},
    "silhouette": {"value": 3, "reason": "Front and three-quarter read clearly; side and back are stable, but the right wrist fitting is bulbous and the pauldrons sit detached from the arm line."},
    "form-proportion": {"value": 2, "reason": "Main volumes hold at rest, but the left hand has mitten-like fused finger segments, the right wrist sleeve balloons and duplicated armor volume remains on the core."},
    "materials": {"value": 3, "reason": "Material regions are readable in all five views; seams and the duplicated painted armor on the core remain."},
    "craft": {"value": 1, "reason": "Several critical defects under the contract poses: shoulder flexion collapses triangles and drives the arm through the cuirass, elbow and hip fold, and the exposed right hand self-intersects at typical angles."},
    "use-readability": {"value": 0, "reason": "None of the required skill combo, locomotion, sleep or cast clips exists; only a 61-frame grip prototype."},
}
trial = {"id": "baseline", "parent_id": None, "status": "completed", "started_utc": started, "ended_utc": ended, "elapsed_seconds": elapsed,
         "protocol_sha256": protocol_sha, "reviewer": "Coordinator (Claude Code): viewed all five fixed views and reviewed every check against measured files; not an independent sign-off",
         "previews": VIEWS, "scores": scores, "evidence": evidence}
ledger = {"schema_version": 1, "request_id": request["id"], "request_sha256": request_sha, "protocol_sha256": protocol_sha,
          "joint_range_contract": request["support_envelope"]["joint_range_contract"], "trials": [trial],
          "phase_history": {"previous_ledger": art("runs/qa/ro-swordsman-combo-r010/quality-ledger.json"), "previous_phase_reopened": False, "quality_targets_lowered": False}}
target = ROOT / QA / "quality-ledger.json"
with open(target, "x", encoding="utf-8", newline="\n") as handle:
    json.dump(ledger, handle, ensure_ascii=False, indent=1)
    handle.write("\n")
print("ledger written", request_sha, protocol_sha)
