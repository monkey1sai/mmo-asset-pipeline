"""Read-only probe of the r010 right hand's cuff: which vertices lie behind the wrist joint and how they are weighted.

Run: blender -b --factory-startup --disable-autoexec <right_hand_grasp_61f.blend> --python <this file>
Nothing is saved. Output: hand-cuff-probe.json
"""
from pathlib import Path
import json

import bpy

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("hand-cuff-probe.json")
assert not OUT.exists()
contract = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r010/local-contract.json").read_text(encoding="utf-8"))
thumb = set(contract["thumb_protected_ids"])
pads = {name: set(ids) for name, ids in contract["pads"].items()}
all_pads = set().union(*pads.values())

arm = bpy.data.objects["ARM_RO_HandDiagnostic"]
mesh = bpy.data.objects["SM_RO_RightHand_Exterior"]
bones = arm.data.bones
wrist = bones["hand"].head_local
knuckles = sum((bones[f"finger{i}_01"].head_local for i in (1, 2, 3, 4)), wrist * 0) / 4
along = (knuckles - wrist).normalized()
names = [g.name for g in mesh.vertex_groups]
bands = {}
rows = []
for v in mesh.data.vertices:
    axial = (v.co - wrist).dot(along)
    weights = {names[g.group]: round(g.weight, 6) for g in v.groups if g.weight > 0}
    rows.append((v.index, axial, weights))
cuts = [0.0, -0.01, -0.02, -0.03]
result = {"hand_vertices": len(rows), "axis": "wrist joint (hand bone head) toward the mean of the four knuckle joints; negative is toward the elbow",
          "axial_range_mm": [round(min(r[1] for r in rows) * 1e3, 1), round(max(r[1] for r in rows) * 1e3, 1)], "by_cut": []}
for cut in cuts:
    behind = [r for r in rows if r[1] < cut]
    ids = {r[0] for r in behind}
    groups = {}
    for _, _, weights in behind:
        for name in weights:
            groups[name] = groups.get(name, 0) + 1
    result["by_cut"].append({
        "behind_axial_mm": cut * 1e3, "vertices": len(behind), "in_thumb_protected_203": len(ids & thumb), "in_any_pad": len(ids & all_pads),
        "only_hand_bone": sum(1 for r in behind if set(r[2]) == {"hand"}), "bones_present": groups})
moved_by_key = 0
keys = mesh.data.shape_keys.key_blocks
for v in mesh.data.vertices:
    if (keys[1].data[v.index].co - keys[0].data[v.index].co).length > 1e-9 and (v.co - wrist).dot(along) < 0:
        moved_by_key += 1
result["corrective_key_moves_vertices_behind_wrist"] = moved_by_key
result["thumb_protected_count"] = len(thumb)
result["pad_counts"] = {k: len(v) for k, v in pads.items()}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_CUFF_PROBE", json.dumps(result))
