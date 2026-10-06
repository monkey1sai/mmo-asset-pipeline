"""Read-only Blender budget scout before choosing replacement-hand density."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r006"
source = ROOT / "assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.blend"
destination = QA / "hand-budget-scout.json"
if destination.exists():
    raise RuntimeError("Preserve budget scout")
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
core = bpy.data.objects["SM_RO_core"]
components = {}
for ob in bpy.data.collections["COL_Character"].objects:
    if ob.type == "MESH":
        ob.data.calc_loop_triangles()
        components[ob.name] = len(ob.data.loop_triangles)
removed = {}
for side, sign in [("R", -1), ("L", 1)]:
    removed[side] = sum(all(sign * core.data.vertices[i].co.x > .34 and
        core.data.vertices[i].co.z < .923 for i in tri.vertices) for tri in core.data.loop_triangles)
limit = 60000
kept = sum(components.values()) - sum(removed.values())
report = {
    "subject": {"path": source.relative_to(ROOT).as_posix(), "sha256": source_sha},
    "actual_component_triangles": components, "whole_triangles_before": sum(components.values()),
    "hypothetical_removed_hand_triangles": removed,
    "cut_rule": "Planning count only: all triangle vertices in side x>.34m and z<.923m, no actual cut",
    "whole_triangles_after_hypothetical_removal": kept,
    "character_triangle_limit": limit, "both_hands_and_seams_available_triangles": limit - kept,
    "seam_reserve_triangles": 256,
    "per_hand_triangles_without_gear_reduction": (limit - kept - 256) // 2,
    "rigid_gear_budget_strategy": "Measure actual generated hand count first. If needed, source-preserving rigid pauldron/bracer mesh simplification must be a documented dependent change and compare the same five quality views; do not decimate a proven deforming hand to fit.",
    "source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == source_sha,
    "model_modified": False,
}
with destination.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
print("RO_HAND_BUDGET " + json.dumps(report))
