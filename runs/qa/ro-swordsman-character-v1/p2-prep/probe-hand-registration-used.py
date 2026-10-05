"""Read-only probe: how would the r010 right hand sit on the whole character's right wrist?

Run: blender -b --factory-startup --disable-autoexec <ro_whole_baseline.blend> --python <this file>
Appends the r010 hand objects in memory only; neither BLEND is saved. Output: hand-registration-probe.json
"""
from pathlib import Path
import hashlib
import json

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
HAND = ROOT / "assets/processed/ro-swordsman-combo-r010/v004-certified-animation/right_hand_grasp_61f.blend"
OUT = Path(__file__).with_name("hand-registration-probe.json")
assert not OUT.exists()

with bpy.data.libraries.load(str(HAND), link=False) as (source, target):
    target.objects = ["ARM_RO_HandDiagnostic", "SM_RO_RightHand_Exterior"]
hand_arm, hand_mesh = target.objects
whole = bpy.data.objects["ARM_RO_Swordsman"]
wb, hb = whole.data.bones, hand_arm.data.bones

pairs = [("hand.R", "hand")] + [(f"finger{i}.R_0{j}", f"finger{i}_0{j}") for i in (1, 2, 3, 4) for j in (1, 2, 3)] + [("thumb.R_01", "thumb_01"), ("thumb.R_02", "thumb_02")]
src = np.array([hb[h].head_local for _, h in pairs])
dst = np.array([wb[w].head_local for w, _ in pairs])


def kabsch(a, b):
    ca, cb = a.mean(0), b.mean(0)
    u, _, vt = np.linalg.svd((a - ca).T @ (b - cb))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1, 1, d]) @ u.T
    return rot, cb - rot @ ca


def report(names, a, b):
    rot, trans = kabsch(a, b)
    residual = np.linalg.norm((a @ rot.T + trans) - b, axis=1)
    return rot, trans, {"landmarks": names, "rms_mm": float(np.sqrt((residual ** 2).mean()) * 1e3), "max_mm": float(residual.max() * 1e3),
                        "per_landmark_mm": {n: round(float(r) * 1e3, 2) for n, r in zip(names, residual)}}


all_names = [w for w, _ in pairs]
rot_all, trans_all, fit_all = report(all_names, src, dst)
base = [i for i, (w, _) in enumerate(pairs) if w == "hand.R" or w.endswith("_01")]
rot_base, trans_base, fit_base = report([all_names[i] for i in base], src[base], dst[base])

# Wrist opening of the r010 hand (its only boundary loop) and overall extents along the hand axis.
bm = bmesh.new()
bm.from_mesh(hand_mesh.data)
ring = sorted({v.index for e in bm.edges if e.is_boundary for v in e.verts})
ring_points = np.array([hand_mesh.data.vertices[i].co for i in ring])
bm.free()
ring_centre = ring_points.mean(0)
_, _, vt = np.linalg.svd(ring_points - ring_centre)
ring_normal = vt[2]
radii = np.linalg.norm(ring_points - ring_centre, axis=1)
verts = np.array([v.co for v in hand_mesh.data.vertices])
hand_bone_head = np.array(hb["hand"].head_local)
along = np.array(hb["finger3_01"].head_local) - hand_bone_head
along /= np.linalg.norm(along)
axial = (verts - hand_bone_head) @ along


def to_whole(rot, trans, p):
    return [round(float(c), 5) for c in rot @ np.asarray(p) + trans]


bracer = bpy.data.objects["SM_RO_bracer.R"]
bracer_points = np.array([bracer.matrix_world @ v.co for v in bracer.data.vertices])
wrist_whole = np.array(wb["hand.R"].head_local)
forearm_axis = wrist_whole - np.array(wb["lower_arm.R"].head_local)
forearm_axis /= np.linalg.norm(forearm_axis)
bracer_axial = (bracer_points - wrist_whole) @ forearm_axis
result = {
    "sources": {"whole": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()},
                "hand": {"path": HAND.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(HAND.read_bytes()).hexdigest()}},
    "method": "Rigid Kabsch fit (rotation + translation, no scale) of r010 hand bone heads onto the whole character's right-hand bone heads.",
    "fit_all_15_joints": fit_all, "fit_wrist_and_knuckles_6": fit_base,
    "determinant": {"all": float(np.linalg.det(rot_all)), "base": float(np.linalg.det(rot_base))},
    "hand_local": {
        "vertices": len(verts), "wrist_ring_vertices": len(ring), "wrist_ring_centre": [round(float(c), 5) for c in ring_centre],
        "wrist_ring_radius_mm": {"min": round(float(radii.min()) * 1e3, 2), "max": round(float(radii.max()) * 1e3, 2)},
        "ring_axial_from_hand_bone_mm": round(float((ring_centre - hand_bone_head) @ along) * 1e3, 2),
        "mesh_axial_range_from_hand_bone_mm": [round(float(axial.min()) * 1e3, 2), round(float(axial.max()) * 1e3, 2)],
        "hand_bone_head": [round(float(c), 5) for c in hand_bone_head],
    },
    "in_whole_space_using_base_fit": {
        "wrist_ring_centre": to_whole(rot_base, trans_base, ring_centre), "hand_bone_head": to_whole(rot_base, trans_base, hand_bone_head),
        "whole_hand.R_head": [round(float(c), 5) for c in wrist_whole],
        "ring_centre_along_forearm_from_wrist_mm": round(float(((rot_base @ ring_centre + trans_base) - wrist_whole) @ forearm_axis) * 1e3, 2),
    },
    "bracer_R": {"axial_range_from_wrist_mm": [round(float(bracer_axial.min()) * 1e3, 2), round(float(bracer_axial.max()) * 1e3, 2)],
                 "note": "Negative values are toward the elbow."},
    "bone_length_mm": {"whole": {w: round(wb[w].length * 1e3, 2) for w, _ in pairs}, "hand": {h: round(hb[h].length * 1e3, 2) for _, h in pairs}},
    "base_fit_matrix_rows": [[round(float(c), 6) for c in row] + [round(float(t), 6)] for row, t in zip(rot_base, trans_base)],
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_HAND_PROBE", json.dumps({"all": [fit_all["rms_mm"], fit_all["max_mm"]], "base": [fit_base["rms_mm"], fit_base["max_mm"]], "hand_local": result["hand_local"], "whole": result["in_whole_space_using_base_fit"], "bracer": result["bracer_R"]}))
