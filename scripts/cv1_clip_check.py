"""Clip-set check for one character V1 animation clip (Blender side), with optional preview renders.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_clip_check.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --registry <interaction-registry.json> \
       --rules <rules.json> --contract <joint-range-contract.json> --fixtures <contact-fixtures.json> --out <new dir> \
       [--preview-frames 0,30,60,90] [--preview-only]
Each sample (whole and half frames, quarter frames near window and event boundaries; scripts/cv1_interaction.py)
plays the action, lets the helper bones follow (rules.helpers), sets the interaction states from the declared windows
and the corrective weights from the final pose (scripts/cv1_pose_rules.py), then measures the evaluated mesh:
- triangle collapse, hand-region self intersections and new hand-to-other intersections (scripts/cv1_soup.py, the same
  measurement as the joint-range sweep); other new intersections are reported (no frozen ceiling exists for clips);
- feet in their stance windows: sole_set slide (minus nominal-speed drift), floor penetration and float;
- the r010 functional grasp gate (certified, unchanged thresholds) at every sample inside a grasp.R window, and
  unknown/inside, transverse crossings and penetration <= 1 mm outside;
- sword against the non-hand body: crossing depth <= 1 mm;
- loop seam: the closing key (frame `frames`) against frame 0, every bone <= 1 degree, sole and grip points <= 1 mm;
- bed clips (interaction config `bed`): inside the declared bed_support windows, the lowest point of each fixed support
  set (back, pelvis, back of head, each calf) against the proxy's top plane, penetration and float <= 5 mm, with every
  point over the bed footprint; the proxy is drawn in the previews only and is not part of the measured soup;
- bed clearance (bed clips, every sample): no measured body point over the bed footprint lies more than 5 mm below the
  bed top (coordinator assumption, the support-set penetration limit applied to the whole body; the opaque proxy hides
  such points in the previews); within 6 frames of a sword-socket event the hand region may press up to 50 mm into the
  bed top, as into a mattress (user decision, authorization entry 18); inside the clip's seated_on_bed windows the coat
  mesh may hang into the bed, as an opaque mattress hides it (user decisions, authorization entries 19-20: while seated
  and through the lie-back or sit-up, a seated window meeting the bed-support window on one shared frame, which the
  support keeps; scripts/cv1_interaction.py seated_on_bed); hand, other and exempted coat points are reported apart;
- sword sockets (interaction config `sword_socket`): from each switch event on, the sword bone holds the fixed bed
  socket transform instead of following hand.R; at every switch the hand-held transform must meet the socket within
  1 mm / 1 degree (no pop; coordinator assumption equal to the loop-seam limits).
Only measured sample times are claimed. Independent gray acceptance of the grasp is required and not decided here.
The BLEND is never saved; an existing output folder is refused. --preview-only renders without measuring and does not
need a registered interaction config.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
from cv1_soup import Soup

parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--registry", "--rules", "--contract", "--fixtures", "--out"):
    parser.add_argument(name, required=True)
parser.add_argument("--preview-frames", default="")
parser.add_argument("--preview-only", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def art(path):
    return {"path": Path(path).as_posix(), "sha256": sha(ROOT / path)}


if args.preview_only:
    config, registry_entry = interaction.load(ROOT / args.interaction), None
else:
    config, registry_entry = interaction.registered(ROOT / args.registry, ROOT / args.interaction)
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))
limits = contract["limits"]
thresholds = {"foot_stance_slide_m": 0.005, "foot_floor_penetration_m": 0.002, "foot_float_m": 0.003, "weapon_body_penetration_m": 0.001,
              "bed_support_penetration_m": 0.005, "bed_support_float_m": 0.005,
              "loop_seam_deg": 1.0, "loop_seam_m": 0.001, "source": "request support_envelope.contact_thresholds_proposed and transition_matrix.gates",
              "socket_pop_m": 0.001, "socket_pop_deg": 1.0,
              "socket_pop_source": "coordinator assumption for spec.parts sword (socket switch without weapon drift): the loop-seam limits, 1 mm / 1 degree",
              "bed_clearance_penetration_m": 0.005,
              "bed_clearance_source": "coordinator assumption (2026-10-06): every measured body point over the bed footprint stays within the bed-support penetration limit (5 mm) of the bed top; added after AN_RO_Sleep_Loop a02 coat tails were found 169 mm inside the opaque bed proxy",
              "bed_clearance_hand_at_socket_events_m": 0.05, "bed_clearance_hand_event_window_frames": 6,
              "bed_clearance_hand_source": "user decision 2026-10-06 (authorization entry 18, runs/qa/ro-swordsman-character-v1/v001/clips/putdown-bed-decision-20261006.json option 1): within 6 frames of a sword-socket event the bed top under the hand region counts as a mattress",
              "bed_clearance_seated_exempt_meshes": ["SM_RO_coat"],
              "bed_clearance_seated_source": "user decisions 2026-10-06 (authorization entries 19-20, runs/qa/ro-swordsman-character-v1/v001/clips/seated-coat-decision-20261006.json and lieback-coat-decision-20261006.json option 1): inside the interaction config's seated_on_bed windows (LieDown: until the bed support is established; GetUp: from leaving it), the coat may lie below the bed top"}
# Bed proxy (request assumption: 0.45 m high, 2.0 x 0.9 m; placement from the registered interaction config).
bed = config.get("bed")
BED_SETS = ("back", "pelvis", "head_back", "calf.L", "calf.R")

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (source, target):
    if config["clip"] not in source.actions:
        raise SystemExit(f"ACTION_NOT_IN_FILE {config['clip']}")
    target.actions = [config["clip"]]
action = bpy.data.actions[config["clip"]]
keyed = sorted({c.data_path.split('"')[1] for c in action.fcurves if c.data_path.startswith("pose.bones")})
first_key = min(p.co.x for c in action.fcurves for p in c.keyframe_points)
helper_conflicts = rules_math.helper_conflicts(rules, keyed)
if helper_conflicts:
    raise SystemExit(f"HELPER_BONES_KEYED {helper_conflicts}")
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
sword_obj = bpy.data.objects["SM_RO_sword"]


def reset_pose():
    arm.animation_data_create()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    for obj in skinned:
        for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
            key.value = 0.0
    bpy.context.view_layer.update()


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


SOCKET = config.get("sword_socket")
BED_SOCKET = (Matrix.Translation(Vector(SOCKET["bed_socket"]["head_m"])) @ Quaternion(SOCKET["bed_socket"]["quaternion_wxyz"]).to_matrix().to_4x4()) if SOCKET else None
SWORD_KEYED = any(c.data_path.startswith('pose.bones["sword"]') for c in action.fcurves)
if SOCKET and SWORD_KEYED:
    raise SystemExit("SOCKETED_CLIP_KEYS_SWORD (a socketed clip's sword follows its socket: hand.R's rest attachment or the bed transform; the exporter strips the channel)")
if SOCKET and arm.pose.bones["sword"].rotation_mode != "QUATERNION":
    raise SystemExit("SWORD_ROTATION_MODE_NOT_QUATERNION (the hand-socket reset writes rotation_quaternion)")


def evaluate_at(t, socket=None):
    """Play the clip at time t (frames), sword socket from the events, helpers follow, interaction states from the
    windows, correctives from the final pose. `socket` overrides the event-driven socket (used for the pop check)."""
    frame = math.floor(t)
    scene.frame_set(frame, subframe=t - frame)
    bpy.context.view_layer.update()
    if (socket or interaction.socket_at(config, t)) == "bed":
        # Socket switch: the sword bone leaves hand.R and holds the fixed bed-socket transform (no per-frame drift).
        arm.pose.bones["sword"].matrix = arm.matrix_world.inverted() @ BED_SOCKET
        bpy.context.view_layer.update()
    elif SOCKET:
        # Hand socket: the rest attachment to hand.R. A socketed clip does not key the sword (refused above) and frame_set
        # leaves an unkeyed bone alone, so an earlier bed placement would carry over (GetUp samples the bed before the hand).
        sword = arm.pose.bones["sword"]
        sword.location, sword.rotation_quaternion, sword.scale = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
    pose = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, pose, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        pose[name] = quaternion
    bpy.context.view_layer.update()
    states = interaction.states_at(config, t)
    state = {d["key"]: states.get(d["key"], 0.0) for d in rules["drivers"].values() if d["type"] == "state"}
    for (mesh_name, key_name), value in rules_math.evaluate(rules, pose, state).items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    return pose, state


def world_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = obj.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    mesh.calc_loop_triangles()
    points = [target.matrix_world @ v.co for v in mesh.vertices]
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    target.to_mesh_clear()
    return points, tris


# ---- preview renders: gray workbench, orthographic, fixed cameras ----
camera = bpy.data.objects.new("CV1_ClipCamera", bpy.data.cameras.new("CV1_ClipCamera"))
scene.collection.objects.link(camera)
camera.data.type, camera.data.ortho_scale = "ORTHO", 2.2
scene.camera = camera
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "SINGLE"
scene.display.shading.single_color = (0.62, 0.62, 0.62)
scene.display.shading.show_cavity = True
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj not in skinned:
        obj.hide_render = True
VIEWS = {"front": Vector((0.0, -4.0, 1.0)), "right": Vector((-4.0, 0.0, 1.0)), "three-quarter": Vector((-2.8, -2.8, 1.4))}
look_at = Vector((0.0, 0.0, 0.92))
if bed:
    # Gray box for the bed proxy in the previews only (not measured, not part of the character).
    import bmesh
    box = bpy.data.meshes.new("CV1_BedProxy")
    builder = bmesh.new()
    bmesh.ops.create_cube(builder, size=1.0)
    builder.to_mesh(box)
    builder.free()
    proxy = bpy.data.objects.new("CV1_BedProxy", box)
    scene.collection.objects.link(proxy)
    proxy.scale = (bed["size_m"][0], bed["size_m"][1], bed["top_z_m"])
    proxy.location = (bed["centre_m"][0], bed["centre_m"][1], bed["top_z_m"] / 2)
    proxy.rotation_euler = (0.0, 0.0, math.radians(bed["yaw_deg"]))
    look_at = Vector((bed["centre_m"][0] / 2, bed["centre_m"][1] / 2, 0.7))
    VIEWS = {name: position + look_at - Vector((0.0, 0.0, 0.92)) for name, position in VIEWS.items()}
    camera.data.ortho_scale = 3.2


def render(frame):
    names = []
    for view, position in VIEWS.items():
        camera.location = position
        camera.rotation_euler = (look_at - position).to_track_quat("-Z", "Y").to_euler()
        target = out / "preview" / f"f{frame:03d}-{view}.png"
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        names.append(target.relative_to(ROOT).as_posix())
    return names


out.mkdir(parents=True)
reset_pose()
previews = {}
preview_frames = [int(f) for f in args.preview_frames.split(",") if f.strip()]
if args.preview_only:
    arm.animation_data.action = action
    for f in preview_frames:
        evaluate_at(f)
        previews[f] = render(f)
    (out / "preview.json").write_text(json.dumps({"clip": config["clip"], "clip_blend": art(args.clip_blend), "rules": art(args.rules), "previews": previews,
                                                  "note": "Preview only; nothing measured."}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("CV1_CLIP_PREVIEW " + json.dumps({"frames": preview_frames}))
    raise SystemExit(0)

# ---- rest state, then samples ----
soup = Soup(meshes, limits)
soup.set_rest()
sole = {side: [soup.offsets[mesh] + i for mesh, ids in fixtures["fixtures"][f"sole_set.{side}"]["ids"].items() for i in ids] for side in ("L", "R")}
support = {key: [soup.offsets[mesh] + i for mesh, ids in fixtures["fixtures"][f"bed_support.{key}"]["ids"].items() for i in ids] for key in BED_SETS} if bed else {}
point_mesh = [name for obj in meshes for name in [obj.name] * len(obj.data.vertices)]


def bed_contact(points):
    """Per support set: lowest point against the bed top plane, and whether every point lies over the bed footprint."""
    yaw = math.radians(bed["yaw_deg"])
    c, s = math.cos(yaw), math.sin(yaw)
    cx, cy = bed["centre_m"]
    half_l, half_w = bed["size_m"][0] / 2, bed["size_m"][1] / 2
    out = {}
    for key, ids in support.items():
        xs = [points[i] for i in ids]
        over = all(abs((p.x - cx) * c + (p.y - cy) * s) <= half_l and abs(-(p.x - cx) * s + (p.y - cy) * c) <= half_w for p in xs)
        out[key] = {"min_z": min(p.z for p in xs), "over_bed": over}
    return out


def bed_clearance(points, t):
    """Deepest measured body point below the bed top while over the bed footprint, hand region and the rest apart.

    The hand region (hand bones weigh >= 0.5) may press deeper near a sword-socket event (the hand lays the sword on the
    bed or takes it up); inside a seated_on_bed window the coat mesh is exempt (reported, not gated); every other point
    keeps the general limit."""
    yaw = math.radians(bed["yaw_deg"])
    c, s = math.cos(yaw), math.sin(yaw)
    cx, cy = bed["centre_m"]
    half_l, half_w, top = bed["size_m"][0] / 2, bed["size_m"][1] / 2, bed["top_z_m"]
    general = thresholds["bed_clearance_penetration_m"]
    hand_limit = thresholds["bed_clearance_hand_at_socket_events_m"] if interaction.near_socket_event(config, t, thresholds["bed_clearance_hand_event_window_frames"]) else general
    seated = interaction.seated_on_bed(config, t)
    deepest = {"hand": None, "other": None, "exempt": None}
    over_limit = 0
    for i, p in enumerate(points):
        if p.z >= top or abs((p.x - cx) * c + (p.y - cy) * s) > half_l or abs(-(p.x - cx) * s + (p.y - cy) * c) > half_w:
            continue
        if seated and point_mesh[i] in thresholds["bed_clearance_seated_exempt_meshes"]:
            if deepest["exempt"] is None or p.z < points[deepest["exempt"]].z:
                deepest["exempt"] = i
            continue
        kind = "hand" if soup.is_hand_vertex[i] else "other"
        over_limit += top - p.z > (hand_limit if kind == "hand" else general)
        if deepest[kind] is None or p.z < points[deepest[kind]].z:
            deepest[kind] = i
    depth = {k: (top - points[i].z if i is not None else 0.0) for k, i in deepest.items()}
    row = {"max_depth_m": max(depth["hand"], depth["other"]), "other_depth_m": depth["other"], "hand_depth_m": depth["hand"], "hand_limit_m": hand_limit,
           "seated_on_bed": seated, "exempt_coat_depth_m": depth["exempt"], "points_over_limit": over_limit,
           "pass": depth["other"] <= general and depth["hand"] <= hand_limit}
    for kind, i in deepest.items():
        if i is not None:
            row[f"deepest_{kind}"] = {"mesh": point_mesh[i], "dominant": soup.dominant[i]}
    return row


from ro_certified_grasp_gate import certified_contacts  # r010 functional gate, thresholds unchanged
pads_source = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r010/local-contract.json").read_text(encoding="utf-8"))
pads = pads_source["pads"]
forward = Vector(contract["axes"]["forward"])
arm.animation_data.action = action
samples = []
seam_pose, seam_points = {}, {}
for t in interaction.sample_times(config):
    pose, state = evaluate_at(t)
    points = soup.evaluated_points()
    measured = soup.measure(points)
    row = {"t": t, "states": state, **{k: v for k, v in measured.items() if k not in ("other_new_examples", "collapsed_examples", "armor_examples")}}
    if measured["collapsed_triangles"]:
        row["collapsed_examples"] = [dict(e, dominant=sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in measured["collapsed_examples"][:3]]
    # Feet: sole_set lowest point and horizontal centroid.
    row["feet"] = {}
    for side in ("L", "R"):
        xs = [points[i] for i in sole[side]]
        centre = sum(xs, Vector()) / len(xs)
        row["feet"][side] = {"centroid_xy": [centre.x, centre.y], "min_z": min(p.z for p in xs)}
    if bed:
        row["bed"] = bed_contact(points)
        row["bed_clearance"] = bed_clearance(points, t)
    # Sword against the non-hand body: deepest crossing over intersecting triangle pairs.
    sword_points, sword_tris = world_mesh(sword_obj)
    sword_tree = BVHTree.FromPolygons(sword_points, sword_tris, all_triangles=True)
    soup_tree = BVHTree.FromPolygons(points, soup.tris, all_triangles=True)
    depth, pairs = 0.0, 0
    for i, j in sword_tree.overlap(soup_tree):
        if soup.tri_hand[j]:
            continue
        pairs += 1
        a = [sword_points[k] for k in sword_tris[i]]
        b = [points[k] for k in soup.tris[j]]

        def crossing(tri, plane):
            normal = (plane[1] - plane[0]).cross(plane[2] - plane[0])
            if normal.length < 1e-14:
                return 0.0
            normal.normalize()
            side = [(p - plane[0]).dot(normal) for p in tri]
            return min(max(0.0, max(side)), max(0.0, -min(side)))

        depth = max(depth, min(crossing(a, b), crossing(b, a)))
    row["weapon_body"] = {"pairs": pairs, "max_depth_m": depth}
    # Grasp: r010 certified functional gate on the right glove.
    report = certified_contacts(bpy.data.objects["SM_RO_hand.R"], sword_obj, arm, pads, f"{config['clip']}@{t}", {"clip": config["clip"], "t": t})
    in_window = interaction.covered(config["states"]["grasp.R"]["windows"], t, config["loop"])
    row["grasp"] = {"in_window": in_window, "pads_within_2mm": {k: v["within_2mm"] for k, v in report["pad_contacts"].items()},
                    "unknown_inside": len(report["unknown_inside"]), "transverse_crossings": report["transverse_crossings_count"],
                    "max_penetration_m": report["maximum_penetration_m"], "surface_gate_pass": report["surface_gate_pass"]}
    row["grasp"]["pass"] = report["surface_gate_pass"] if in_window else (not report["unknown_inside"] and not report["transverse_crossings_count"] and report["maximum_penetration_m"] <= 0.001)
    row["sword_grip_point"] = list(arm.matrix_world @ arm.pose.bones["sword"].head)
    if t == 0:
        seam_pose[0], seam_points[0] = pose, {"sole.L": row["feet"]["L"], "sole.R": row["feet"]["R"], "grip": row["sword_grip_point"]}
    samples.append(row)
if config["loop"]:
    # Loop clips carry a closing key at frame `frames` that must equal frame 0; the seam compares the two.
    end = config["frames"]
    seam_pose[end], _ = evaluate_at(end)
    points = soup.evaluated_points()
    seam_points[end] = {"grip": list(arm.matrix_world @ arm.pose.bones["sword"].head)}
    for side in ("L", "R"):
        xs = [points[i] for i in sole[side]]
        centre = sum(xs, Vector()) / len(xs)
        seam_points[end][f"sole.{side}"] = {"centroid_xy": [centre.x, centre.y], "min_z": min(p.z for p in xs)}
reset_pose()


def window_samples(windows):
    return [s for s in samples if interaction.covered(windows, s["t"], config["loop"])]


feet = {}
for side in ("L", "R"):
    rows = []
    for window in config["stance"].get(side, []):
        inside = window_samples([window])
        if not inside:
            continue
        # Chronological order from the window start, also when the window wraps across a loop seam.
        inside.sort(key=lambda s: (s["t"] - window[0]) % config["frames"])
        first = inside[0]
        elapsed = lambda s: ((s["t"] - first["t"]) % config["frames"]) / config["fps"]
        drift = lambda s: forward * (-config["nominal_speed_m_s"] * elapsed(s))
        slide = max((Vector((*s["feet"][side]["centroid_xy"], 0)) - Vector((*first["feet"][side]["centroid_xy"], 0)) - drift(s)).length for s in inside)
        rows.append({"window": window, "slide_m": slide, "penetration_m": max(0.0, -min(s["feet"][side]["min_z"] for s in inside)),
                     "float_m": max(0.0, min(s["feet"][side]["min_z"] for s in inside))})
    feet[side] = rows
sockets = None
if SOCKET:
    # Pop check at every socket switch: the hand-held sword transform at the event frame against the bed socket.
    events = {event["name"]: event["frame"] for event in config["events"]}
    sockets = {"initial": SOCKET["initial"], "bed_socket": SOCKET["bed_socket"], "switches": []}
    for switch in SOCKET["switches"]:
        arm.animation_data.action = action
        evaluate_at(events[switch["event"]], socket="hand")
        held = arm.matrix_world @ arm.pose.bones["sword"].matrix
        move = (held.translation - BED_SOCKET.translation).length
        turn = math.degrees(held.to_quaternion().rotation_difference(BED_SOCKET.to_quaternion()).angle)
        sockets["switches"].append({**switch, "frame": events[switch["event"]], "pop_m": move, "pop_deg": turn,
                                    "pass": move <= thresholds["socket_pop_m"] and turn <= thresholds["socket_pop_deg"]})
    reset_pose()
bed_support = None
if bed:
    # Inside the declared bed windows every support set rests on the bed top: lowest point within +-5 mm, over the footprint.
    inside = window_samples(config.get("bed_support", {}).get("windows", []))
    top = bed["top_z_m"]
    bed_support = {"samples": len(inside), "sets": {key: {
        "penetration_m": max([0.0] + [top - s["bed"][key]["min_z"] for s in inside]),
        "float_m": max([0.0] + [s["bed"][key]["min_z"] - top for s in inside]),
        "off_bed_times": [s["t"] for s in inside if not s["bed"][key]["over_bed"]][:10]} for key in BED_SETS}}
seam = None
if config["loop"]:
    last = config["frames"]
    angle = max(math.degrees(Quaternion(seam_pose[0][b]).rotation_difference(Quaternion(seam_pose[last][b])).angle) for b in keyed)
    moves = [(Vector((*seam_points[0][k]["centroid_xy"], seam_points[0][k]["min_z"])) - Vector((*seam_points[last][k]["centroid_xy"], seam_points[last][k]["min_z"]))).length for k in ("sole.L", "sole.R")]
    moves.append((Vector(seam_points[0]["grip"]) - Vector(seam_points[last]["grip"])).length)
    seam = {"from_frame": last, "to_frame": 0, "max_bone_deg": angle, "max_point_m": max(moves), "pass": interaction.seam_ok(angle, max(moves))}
gates = {
    "clip_time_origin_zero": first_key == 0,
    "helper_bones_not_keyed": not helper_conflicts,
    "no_collapse": all(s["collapsed_triangles"] == 0 for s in samples),
    "hand_self_intersection_zero": all(s["hand_self_pairs"] == 0 for s in samples),
    "hand_other_new_intersection_zero": all(s["hand_other_new_pairs"] == 0 for s in samples),
    "feet_slide": all(r["slide_m"] <= thresholds["foot_stance_slide_m"] for rows in feet.values() for r in rows),
    "feet_penetration": all(r["penetration_m"] <= thresholds["foot_floor_penetration_m"] for rows in feet.values() for r in rows),
    "feet_float": all(r["float_m"] <= thresholds["foot_float_m"] for rows in feet.values() for r in rows),
    "weapon_body_penetration": all(s["weapon_body"]["max_depth_m"] <= thresholds["weapon_body_penetration_m"] for s in samples),
    "grasp_functional": all(s["grasp"]["pass"] for s in samples),
}
if seam is not None:
    gates["loop_seam"] = seam["pass"]
if sockets is not None and sockets["switches"]:
    gates["sword_socket_pop"] = all(s["pass"] for s in sockets["switches"])
if bed_support is not None:
    sets = bed_support["sets"].values()
    gates["bed_support_penetration"] = bed_support["samples"] > 0 and all(r["penetration_m"] <= thresholds["bed_support_penetration_m"] for r in sets)
    gates["bed_support_float"] = bed_support["samples"] > 0 and all(r["float_m"] <= thresholds["bed_support_float_m"] for r in sets)
    gates["bed_support_over_bed"] = bed_support["samples"] > 0 and all(not r["off_bed_times"] for r in sets)
    gates["bed_clearance"] = all(s["bed_clearance"]["pass"] for s in samples)
failures = [{"t": s["t"], "failed": [k for k, ok in (("collapse", s["collapsed_triangles"] == 0), ("hand_self", s["hand_self_pairs"] == 0),
                                                     ("hand_other_new", s["hand_other_new_pairs"] == 0), ("weapon_body", s["weapon_body"]["max_depth_m"] <= 0.001),
                                                     ("grasp", s["grasp"]["pass"]),
                                                     ("bed_clearance", s.get("bed_clearance", {}).get("pass", True))) if not ok]}
            for s in samples]
failures = [f for f in failures if f["failed"]]
for f in preview_frames:
    arm.animation_data.action = action
    evaluate_at(f)
    previews[f] = render(f)
reset_pose()
result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
    "subject": {"foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
                "clip_blend": art(args.clip_blend), "action": action.name, "keyed_bones": keyed, "first_key_frame": first_key},
    "interaction": {**art(args.interaction), "registry_entry": registry_entry}, "rules": art(args.rules), "contract": art(args.contract), "fixtures": art(args.fixtures),
    "grasp_gate": {"source": "runs/qa/ro-swordsman-combo-r010/local-contract.json", "functional_gate_verbatim": pads_source["functional_gate"],
                   "method": "scripts/ro_certified_grasp_gate.py (world coordinates, certified solid-angle fallback)", "pads": {k: len(v) for k, v in pads.items()},
                   "independent_gray_acceptance": "required, not decided by this tool"},
    "thresholds": thresholds, "sample_count": len(samples), "sample_rule": "whole and half frames; quarter frames within one frame of each boundary",
    "feet": feet, "loop_seam": seam, "bed": bed, "bed_support": bed_support, "sword_sockets": sockets,
    "report_only": {"other_new_pairs_max": max(s["other_new_pairs"] for s in samples), "other_new_by_mesh_pair_at_worst": max(samples, key=lambda s: s["other_new_pairs"])["other_new_by_mesh_pair"],
                    "min_triangle_area_ratio": min(s["min_triangle_area_ratio"] for s in samples),
                    "hand_edge_ratio_range": [min(s["hand_edge_ratio"][0] for s in samples), max(s["hand_edge_ratio"][1] for s in samples)],
                    "note": "No frozen ceiling exists for body intersections in clips; reported for the art review."},
    "gates": gates, "pass_numeric": all(gates.values()), "failures": failures[:40], "previews": previews,
    "scope": "Measured sample times only; numeric gates are not art acceptance; grasp gray acceptance pending independent review.",
    "samples": samples,
}
(out / "clip-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_CLIP_CHECK " + json.dumps({"clip": config["clip"], "samples": len(samples), "gates": gates, "failures": len(failures), "feet": feet, "loop_seam": seam, "bed_support": bed_support,
                                       "report_only": {k: result["report_only"][k] for k in ("other_new_pairs_max", "min_triangle_area_ratio")}}))
