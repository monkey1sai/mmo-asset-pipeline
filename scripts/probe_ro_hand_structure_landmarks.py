"""Read native cross sections and existing rig; no mesh/model writes."""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "runs/qa/ro-swordsman-combo-r007"
destination = QA / "hand-source/landmark-sections.json"
assert not destination.exists()
source = ROOT / "assets/processed/ro-swordsman-combo-r007/hand-source/right_hand_native_source.blend"
original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects["SM_RO_RightHand_Native_00"]
edge_lookup = {tuple(sorted(e.vertices)): e.index for e in ob.data.edges}
sections = []
for step in range(1, 53):
    z = step * .005
    points = {}
    links = {}
    for e in ob.data.edges:
        a, b = (ob.data.vertices[i].co for i in e.vertices)
        if (a.z - z) * (b.z - z) <= 0 and abs(a.z - b.z) > 1e-9:
            points[e.index] = a.lerp(b, (z - a.z) / (b.z - a.z))
            links[e.index] = set()
    for face in ob.data.polygons:
        edge_ids = [key_to_id for key in face.edge_keys
                    for key_to_id in [edge_lookup[tuple(sorted(key))]]
                    if key_to_id in points]
        for a in edge_ids:
            links[a].update(b for b in edge_ids if b != a)
    remaining = set(points)
    groups = []
    while remaining:
        stack = [min(remaining)]; ids = []
        while stack:
            i = stack.pop()
            if i not in remaining:
                continue
            remaining.remove(i); ids.append(i); stack.extend(links[i])
        values = [points[i] for i in ids]
        lo = [min(p[j] for p in values) for j in range(3)]
        hi = [max(p[j] for p in values) for j in range(3)]
        groups.append({"edge_ids": ids, "min": lo, "max": hi,
                       "center": [(lo[j] + hi[j]) / 2 for j in range(3)]})
    sections.append({"z": z, "contours": sorted(groups, key=lambda g: g["center"][0])})
baseline = ROOT / "assets/processed/ro-swordsman-combo-r007/baseline/ro_hand_structure_baseline.blend"
bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False, use_scripts=False)
state = json.loads(bpy.data.objects["ARM_RO_Swordsman"]["state_json"])
report = {"source": {"path": source.relative_to(ROOT).as_posix(), "sha256": original_sha},
          "sections": sections,
          "baseline": {key: state[key] for key in ["hand_frames", "grips", "measurements"]},
          "baseline_right_rest": {n: seg for n, seg in state["rest"].items()
                                  if ".R" in n and n.startswith(("hand", "lower_arm", "finger", "thumb"))},
          "actual_anatomical_joint_centers_validated": False,
          "source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == original_sha}
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("RO_NATIVE_SECTIONS " + json.dumps([{ "z": s["z"], "centers": [c["center"] for c in s["contours"]]}
                                        for s in sections if .085 <= s["z"] <= .265]))
