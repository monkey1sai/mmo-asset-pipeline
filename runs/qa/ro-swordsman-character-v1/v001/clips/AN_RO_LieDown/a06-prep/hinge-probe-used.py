"""Check ArmIK.solve_hinge on the foundation armature (report only; nothing is saved).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python hinge-probe-used.py -- <out.json>
1. Hinge geometry per side: straight-arm angle, shoulder-wrist distance at rest and at the contract extreme.
2. flexion_for round trip on a grid of hinge angles.
3. Random reachable targets (seeded) and swivels from the rest shoulder: wrist error, posed lower-arm frame against the
   solution, lower-arm local rotation axis against the hinge axis, elbow point against elbow_of(), and the a05 diagnostic
   metric (swing axis off the hinge after a swing-twist split about the bone) for both solvers on the same targets.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r"C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop")
sys.path.insert(0, str(ROOT / "scripts"))
from cv1_arm_ik import ArmIK, ELBOW_FLEXION_MAX_DEG

out = sys.argv[sys.argv.index("--") + 1]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
ik = ArmIK(arm)
B = arm.data.bones


def reset():
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
        pb.rotation_mode = "QUATERNION"
    bpy.context.view_layer.update()


def local_rel(name):
    pb = arm.pose.bones[name]
    rest_local = B[name].parent.matrix_local.inverted() @ B[name].matrix_local
    return (rest_local.inverted() @ (pb.parent.matrix.inverted() @ pb.matrix)).to_quaternion()


def off_hinge_a05_metric(side):
    """Same split as a05-diag-hinge: swing part (after removing twist about the bone) against the hinge axis."""
    q = local_rel(f"lower_arm.{side}")
    along = Vector((0, 1, 0))
    p = Vector((q.x, q.y, q.z))
    proj = along * p.dot(along)
    twist = Quaternion((q.w, proj.x, proj.y, proj.z)).normalized()
    swing = q @ twist.inverted()
    axis = Vector((swing.x, swing.y, swing.z))
    hinge = ik.hinge[side]["axis"]
    if axis.length < 1e-9 or math.degrees(swing.angle) < 2:
        return None
    return math.degrees(min(axis.normalized().angle(hinge), axis.normalized().angle(-hinge)))


def axis_off_hinge(side):
    q = local_rel(f"lower_arm.{side}")
    axis = Vector((q.x, q.y, q.z))
    if axis.length < 1e-9:
        return 0.0
    hinge = ik.hinge[side]["axis"]
    return math.degrees(min(axis.normalized().angle(hinge), axis.normalized().angle(-hinge)))


report = {"geometry": {}, "round_trip_max_error_deg": {}, "random": {}}
reset()
for side in "RL":
    g = ik.hinge[side]
    dist = lambda th: (g["elbow"] + g["relation"] @ (Matrix.Rotation(th, 3, g["axis"]) @ g["wrist"])).length
    grid = [math.radians(d) for d in range(-60, 181)]
    straight = max(grid, key=dist)
    shoulder, elbow, wrist = B[f"upper_arm.{side}"].head_local, B[f"lower_arm.{side}"].head_local, B[f"hand.{side}"].head_local
    report["geometry"][side] = {"straight_arm_hinge_deg_grid": math.degrees(straight), "distance_rest_m": dist(0.0),
                                "distance_extreme_m": dist(math.radians(ELBOW_FLEXION_MAX_DEG)), "distance_straight_m": dist(straight),
                                "rest_elbow_angle_deg": math.degrees((shoulder - elbow).angle(wrist - elbow)),
                                "hinge_axis_vs_forearm_deg": math.degrees(g["axis"].angle(Vector((0, 1, 0)))),
                                "segment_lengths_m": ik.length[side]}
    worst = 0.0
    for d in range(0, int(ELBOW_FLEXION_MAX_DEG) + 1):
        th = math.radians(d)
        worst = max(worst, abs(math.degrees(ik.flexion_for(side, dist(th))) - d))
    report["round_trip_max_error_deg"][side] = worst

rng = random.Random(20261006)
for side in "RL":
    rows = []
    while len(rows) < 60:
        reset()
        shoulder = ik.shoulder(side)
        g = ik.hinge[side]
        th = math.radians(rng.uniform(5, 130))
        distance = (g["elbow"] + g["relation"] @ (Matrix.Rotation(th, 3, g["axis"]) @ g["wrist"])).length
        direction = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if direction.length < 0.2:
            continue
        target_rot = Quaternion(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized(), rng.uniform(0, math.pi)).to_matrix()
        target = Matrix.Translation(shoulder + direction.normalized() * distance) @ target_rot.to_4x4()
        swivel = rng.choice((-40, -10, 0, 20, 40))
        elbow_point = ik.elbow_of(side, target.translation, math.radians(swivel), shoulder)
        if elbow_point is None:
            continue
        solved = ik.solve_hinge(side, target, swivel)
        row = {"flexion_deg": solved["flexion_deg"], "wrist_error_mm": solved["wrist_error_mm"], "lower_frame_error_deg": solved["lower_frame_error_deg"],
               "hand_error_deg": math.degrees(arm.pose.bones[f"hand.{side}"].matrix.to_quaternion().rotation_difference(target.to_quaternion()).angle),
               "elbow_vs_swing_solver_mm": (arm.pose.bones[f"lower_arm.{side}"].head - elbow_point).length * 1e3,
               "lower_arm_axis_off_hinge_deg": axis_off_hinge(side), "a05_metric_hinge": off_hinge_a05_metric(side),
               "pronation_deg": solved["pronation_deg"], "wrist_swing_deg": solved["wrist_swing_deg"]}
        reset()
        ik.solve(side, target, swivel)
        row["a05_metric_swing"] = off_hinge_a05_metric(side)
        row["swing_lower_arm_axis_off_hinge_deg"] = axis_off_hinge(side)
        rows.append(row)
    summary = {k: [min(r[k] for r in rows if r[k] is not None), max(r[k] for r in rows if r[k] is not None)] for k in rows[0]}
    report["random"][side] = {"count": len(rows), "ranges": summary}
Path(out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_HINGE_PROBE " + json.dumps(report))
