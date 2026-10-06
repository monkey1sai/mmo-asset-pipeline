"""Actual corrected-axis baseline; preserve all source geometry/UV/weights."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_core_rig import curl_digits, pose
from ro_review_common import camera, render_views

ID = "ro-swordsman-combo-r006"
QA = ROOT / "runs/qa" / ID / "baseline"
OUT = ROOT / "assets/processed" / ID / "baseline"
clock = json.loads((ROOT / "runs/qa" / ID / "phase-start.json").read_text())
source_artifact = clock["baseline_source"]
source = ROOT / source_artifact["path"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if QA.exists() or OUT.exists() or sha(source) != source_artifact["sha256"]:
    raise RuntimeError("Preserve baseline and frozen source")
if (datetime.now(timezone.utc) - datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds() > clock["budget"]["trial_seconds"]:
    raise RuntimeError("Prospective baseline time limit exceeded")
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
rig = bpy.data.objects["ARM_RO_Swordsman"]
core = bpy.data.objects["SM_RO_core"]
sword = bpy.data.objects["SM_RO_sword"]
state = json.loads(rig["state_json"])
state["digit_axis_method"] = "individual_centerline_cross_palm"
state.pop("finger_angles", None)
state["forearm_twist_to_palm"] = {"R": False, "L": False}
geometry = [tuple(v.co) for v in core.data.vertices]
uvs = [tuple(v.uv) for v in core.data.uv_layers.active.data]
weights = [[(g.group, g.weight) for g in v.groups] for v in core.data.vertices]
QA.mkdir(parents=True)
OUT.mkdir(parents=True)
(QA / "rig-helper-used.py").write_bytes((ROOT / "scripts/ro_core_rig.py").read_bytes())


def reset():
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def hand_views(folder, side):
    folder.mkdir(parents=True)
    target = rig.pose.bones["hand." + side].head.lerp(rig.pose.bones["hand." + side].tail, .6)
    for name, offset in [
        ("palm", (.25, -1, .12)), ("side", (1, .1, .1)),
        ("back", (-.25, 1, .1)), ("wrist", (0, -.2, .9)),
    ]:
        camera((tuple(target + Vector(offset)), tuple(target), .29))
        bpy.context.scene.render.filepath = str(folder / (name + ".png"))
        bpy.ops.render.render(write_still=True)


def fixed_pad_sets(side):
    frame = state["hand_frames"][side]
    front = Vector(frame["front"])
    pads = {}
    for name in ["finger1", "finger2", "finger3", "finger4", "thumb"]:
        joints = [f"{name}.{side}_{i:02}" for i in [1, 2]]
        group_ids = {core.vertex_groups[n].index for n in joints}
        candidates = [v for v in core.data.vertices if
            sum(g.weight for g in v.groups if g.group in group_ids) > .5
            and v.normal.dot(front) > .15]
        if not candidates:
            raise RuntimeError("No fixed palm-side pad candidates: " + name + side)
        # Same unposed semantic mask is used in every later test; no nearest-point selection.
        pads[name] = [v.index for v in candidates]
    return pads


reset()
core.data.update()
pads = {side: fixed_pad_sets(side) for side in ["R", "L"]}
render_views(QA)
for side in ["R", "L"]:
    hand_views(QA / ("open-" + side), side)
    reset()
    curl_digits(rig, state, side, .30)
    hand_views(QA / ("small-curl-" + side), side)
    reset()

measurements = {}
directions = [Vector((.713, .389, .587)).normalized(), Vector((.419, .831, .365)).normalized()]


def contact(side):
    deps = bpy.context.evaluated_depsgraph_get()
    co = core.evaluated_get(deps)
    so = sword.evaluated_get(deps)
    mesh = co.to_mesh()
    smesh = so.to_mesh()
    try:
        pts = [so.matrix_world @ v.co for v in smesh.vertices]
        solid = BVHTree.FromPolygons(pts, [list(f.vertices) for f in smesh.polygons])
        center = rig.pose.bones["sword"].head
        axis = (rig.pose.bones["sword"].tail - center).normalized()
        faces = [list(f.vertices) for f in smesh.polygons if all(
            -.112 < (pts[i] - center).dot(axis) < .085 for i in f.vertices)]
        if not faces:
            raise RuntimeError("Actual handle mask empty")
        handle = BVHTree.FromPolygons(pts, faces)

        def inside(p, direction):
            origin = p + direction * 1e-6
            count = 0
            for _ in range(80):
                hit, normal, index, dist = solid.ray_cast(origin, direction, 4)
                if hit is None:
                    return bool(count % 2)
                count += 1
                origin = hit + direction * 1e-6
            return None

        result = {}
        for name, indices in pads[side].items():
            ds, depths = [], []
            disagreements = 0
            for i in indices:
                p = co.matrix_world @ mesh.vertices[i].co
                ds.append(handle.find_nearest(p)[3])
                votes = [inside(p, direction) for direction in directions]
                if None in votes or len(set(votes)) != 1:
                    disagreements += 1
                if all(v is True for v in votes):
                    depths.append(solid.find_nearest(p)[3])
            result[name] = {
                "fixed_pad_vertices": len(indices), "minimum_gap_m": min(ds),
                "mean_gap_m": sum(ds) / len(ds), "within2mm": sum(d <= .002 for d in ds),
                "inside_deeper_than1mm": sum(d > .001 for d in depths),
                "maximum_measured_penetration_m": max(depths, default=0),
                "ray_disagreements_or_unknown": disagreements,
            }
        return result
    finally:
        co.to_mesh_clear()
        so.to_mesh_clear()


for side in ["R", "L"]:
    reset()
    posed = pose(rig, state, .89, (-.08 if side == "R" else .08, -.29, 1.12),
                 (0, -.1, .995), curl=.85, two_hands=False, active_side=side)
    measurements[side] = {"pose": posed, "fixed_pad_contact": contact(side)}
    hand_views(QA / ("grip-" + side), side)
reset()
assert geometry == [tuple(v.co) for v in core.data.vertices]
assert uvs == [tuple(v.uv) for v in core.data.uv_layers.active.data]
assert weights == [[(g.group, g.weight) for g in v.groups] for v in core.data.vertices]
rig["state_json"] = json.dumps(state)
rig["r006_fixed_pad_vertices"] = json.dumps(pads)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "ro_hand_baseline.blend"))
bpy.ops.object.select_all(action="DESELECT")
objects = [ob for ob in bpy.data.collections["COL_Character"].objects if ob.type == "MESH"]
for ob in [rig, *objects]:
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(OUT / "ro_hand_baseline.glb"), export_format="GLB",
    use_selection=True, export_animations=False)
triangles = 0
for ob in objects:
    ob.data.calc_loop_triangles()
    triangles += len(ob.data.loop_triangles)
report = {
    "stage": "r006 real baseline with corrected individual finger-axis fixture",
    "source": source_artifact, "source_preserved": sha(source) == source_artifact["sha256"],
    "baseline_started_utc": clock["baseline_started_utc"],
    "finished_utc": datetime.now(timezone.utc).isoformat(),
    "triangles": triangles, "bones": len(rig.data.bones),
    "geometry_uv_weights_unchanged": True, "axis_method": state["digit_axis_method"],
    "pose_contract": "Open palm, .30rad small curl, .85rad single grip; actual source dimensions and sword",
    "grip_measurements": measurements, "fixed_pad_indices": pads,
    "measurement_limit": "Fixed palm-facing vertices and two solid parity rays, not complete face intersection validation",
    "full_animation_channels": 0, "effects_present": False,
    "rig_accepted": False, "art_accepted": False,
    "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
                  for p in sorted(OUT.iterdir()) if p.suffix in [".blend", ".glb"]],
}
(QA / "baseline.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("RO_HAND_BASELINE " + json.dumps({k: report[k] for k in ["triangles", "bones", "geometry_uv_weights_unchanged", "source_preserved"]}))
