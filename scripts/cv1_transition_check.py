"""Transition check for the character V1 QA scene (Blender side): request r6 transition_matrix gates over P4 scenarios.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_transition_check.py -- \
       --scenarios <transitions.json> --registry <interaction-registry.json> --rules <rules.json> \
       --contract <joint-range-contract.json> --fixtures <contact-fixtures.json> --out <new dir> \
       [--shard i/n] [--only id,id] [--reference] [--fault weapon-in-hand|stance-window:<clip>] [--continuity-only] [--probe "id@t;id@t"]
Each sample blends the scenario's layers the way the runtime does (scripts/cv1_transition.py: layer weights, layer clip
frames, three.js PropertyMixer accumulation; each layer's channels are the clip's integer-frame keys joined by slerp /
lerp as three.js QuaternionLinearInterpolant does), puts the sword on the socket the active layers share (bed socket
transform, or the rest attachment to hand.R), lets the helpers follow, blends the interaction states and sets the
correctives, then measures with the clip check's methods (scripts/cv1_clip_check.py):
- collapse < 5 % area, hand self and new hand-other intersections 0 (scripts/cv1_soup.py);
- sword against the non-hand body <= 1 mm;
- r010 grasp gate while every layer that drives the hands is inside its grasp.R window, else unknown/inside 0,
  crossings 0, penetration <= 1 mm;
- feet: while every layer that drives the legs has the foot in stance, the sole_set centroid slides at most 2 x 5 mm
  from the first such sample (nominal-speed drift of in-place clips subtracted with the blended speed); only inside a
  foot-lock release or settle may a sole lifted over 5 mm leave the run (settle steps are reported with their lift);
- continuity (r6 wording): at each fade start the pose equals the source clips' pose and at each transition end (the
  fade end, or later while a foot lock, release or settle is still running then) the target clips' pose, the references taken straight from
  the clips (no weights, no mixing, the sword left to the socket gates); a fade that starts inside a running fade or
  foot lock is compared with the pose just before it and has no end (every bone <= 0.5 deg, pelvis <= 1 mm);
- bed clips: support sets within 5 mm while every layer is in a bed_support window, bed clearance as in the clip check
  (hand allowance near a socket event of any layer; the coat exemption holds when every bed-clip layer that drives the
  legs is inside its seated window, other layers neutral: user decision B1, authorization entry 25).
The stance-foot lock (user decision A1, authorization entry 25; scripts/cv1_foot_lock.py) runs after the mixer and
before the socket: a two-bone leg solve pins a foot that every leg layer has in stance while a transition fades.
The BLEND is never saved; an existing output folder is refused. --reference writes the runtime closed-loop blocks at the
scenarios' reference_times (float32 positions, with the foot-lock targets and the rest sole points for the runtime). --fault runs a disposable counterexample (never a result): weapon-in-hand pushes the sword
6 mm toward the palm; stance-window:<clip> widens that clip's stance windows to the whole clip.
--continuity-only writes continuity-check.json (that gate alone, no mesh measurement). --probe is a diagnostic,
never a result: per sample the blend, the blend without correctives and each layer alone (area ratios and
neighbour agreement of the lowest triangles, vertex groups, bone world rotations, deepest bed point by mesh).
"""
from array import array
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
import cv1_foot_lock as fl
import cv1_interaction as interaction
import cv1_pose_rules as rules_math
import cv1_transition as tr
from cv1_soup import Soup

parser = argparse.ArgumentParser()
for name in ("--scenarios", "--registry", "--rules", "--contract", "--fixtures", "--out"):
    parser.add_argument(name, required=True)
parser.add_argument("--shard", default="0/1")
parser.add_argument("--only", default="")
parser.add_argument("--reference", action="store_true")
parser.add_argument("--fault", default="")
parser.add_argument("--probe", default="")
parser.add_argument("--continuity-only", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def art(path):
    return {"path": Path(path).as_posix(), "sha256": sha(ROOT / path)}


spec = json.loads((ROOT / args.scenarios).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))
limits = contract["limits"]
THRESHOLDS = {"collapse_area_ratio": limits["collapse_area_ratio"], "weapon_body_m": 0.001, "grasp_outside_penetration_m": 0.001,
              "feet_slide_m": 2 * 0.005, "continuity_deg": 0.5, "continuity_m": 0.001, "bed_support_m": 0.005, "bed_clearance_m": 0.005,
              "bed_clearance_hand_m": 0.05, "bed_clearance_hand_event_window_frames": 6,
              "feet_lift_break_m": 0.005,
              "source": "requests/ro-swordsman-character-v1-r6.json transition_matrix.gates (feet: 2 x foot_stance_slide 5 mm); bed gates as scripts/cv1_clip_check.py"}

LIFT_BREAK_M = THRESHOLDS["feet_lift_break_m"]

# ---- clips: registered interaction configs and actions ----
clips, configs, registry_entries = spec["clips"], {}, {}
for short, clip in clips.items():
    configs[short], registry_entries[short] = interaction.registered(ROOT / args.registry, ROOT / clip["interaction"])
fault_stance = args.fault.split(":", 1)[1] if args.fault.startswith("stance-window:") else None
if fault_stance:
    frames = configs[fault_stance]["frames"]
    configs[fault_stance] = dict(configs[fault_stance], stance={"L": [[0, frames - 1]], "R": [[0, frames - 1]]})
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
bones = arm.data.bones
PARENTS = {b.name: b.parent.name if b.parent else None for b in bones}
REST_LOCAL = {b.name: tuple((b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local).to_quaternion()) for b in bones}
HELPERS = {h["bone"] for h in rules.get("helpers", [])}
GROUP = {b.name: tr.bone_group(b.name, PARENTS) for b in bones}
if any(pb.rotation_mode != "QUATERNION" for pb in arm.pose.bones):
    raise SystemExit("ROTATION_MODE_NOT_QUATERNION")
actions = {}
for short, clip in clips.items():
    with bpy.data.libraries.load(str(ROOT / clip["blend"]), link=False) as (source, target):
        if clip["clip"] not in source.actions:
            raise SystemExit(f"ACTION_NOT_IN_FILE {clip['clip']}")
        target.actions = [clip["clip"]]
    actions[short] = target.actions[0]
SOCKETED = {short for short in clips if configs[short].get("sword_socket")}
from cv1_contract_pose import ContractPoser
PALMAR_REST = ContractPoser(arm, contract, {}).hands["R"]["palmar"]
lookup = {short: {"frames": c["frames"], "loop": c["loop"], "fps": c["fps"]} for short, c in clips.items()}

# Channel values at integer frames (the exported clip's keys: unkeyed channels sit at rest; helpers never contribute; a
# socketed clip has no sword channel at runtime).
curves = {}
for short, action in actions.items():
    table = {}
    for fc in action.fcurves:
        if fc.data_path.startswith("pose.bones["):
            bone, prop = fc.data_path.split('"')[1], fc.data_path.rsplit(".", 1)[1]
            table.setdefault(bone, {}).setdefault(prop, {})[fc.array_index] = fc
    curves[short] = table
_cache = {}


def channels(short, frame):
    key = (short, frame)
    if key not in _cache:
        table, out = curves[short], {}
        for b in bones:
            if b.name in HELPERS or (b.name == "sword" and short in SOCKETED):
                continue
            props = table.get(b.name, {})
            q = props.get("rotation_quaternion", {})
            w, x, y, z = (q[i].evaluate(frame) if i in q else (1.0 if i == 0 else 0.0) for i in range(4))
            loc = tuple(props.get("location", {})[i].evaluate(frame) if i in props.get("location", {}) else 0.0 for i in range(3))
            scale = tuple(props.get("scale", {})[i].evaluate(frame) if i in props.get("scale", {}) else 1.0 for i in range(3))
            out[b.name] = ((x, y, z, w), loc, scale)
        _cache[key] = out
    return _cache[key]


def layer_pose(short, frame):
    """three.js track evaluation between integer keys: slerp for rotations, lerp for the rest."""
    f0 = math.floor(frame + 1e-9)
    alpha = frame - f0
    a = channels(short, f0)
    if alpha < 1e-9:
        return a
    b = channels(short, f0 + 1)
    return {name: (tr.slerp_flat(a[name][0], b[name][0], alpha), tr.lerp(a[name][1], b[name][1], alpha), tr.lerp(a[name][2], b[name][2], alpha)) for name in a}


IDENTITY = ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


def blended_pose(scenario, t, weights_override=None):
    """Per bone (rotation xyzw, location, scale) from the active layers, and the layer frames and weights."""
    w = weights_override or tr.weights(scenario, t)
    starts = tr.layers(scenario)
    frames = {layer: tr.layer_frame(scenario, lookup, layer, t) for layer in starts}
    poses = {layer: layer_pose(starts[layer]["clip"], frame) for layer, frame in frames.items() if frame is not None}
    order = [layer for layer in starts if layer in poses]
    out = {}
    for b in bones:
        if b.name in HELPERS:
            continue
        g = w[GROUP[b.name]]
        contrib = [(poses[layer][b.name], g.get(layer, 0.0)) for layer in order if b.name in poses[layer]]
        out[b.name] = tuple(tr.mix([(c[k], weight) for c, weight in contrib], IDENTITY[k], "quaternion" if k == 0 else "vector") for k in range(3))
    return out, frames, w


def set_pose(pose):
    for pb in arm.pose.bones:
        rot, loc, scale = pose.get(pb.name, IDENTITY)
        pb.rotation_quaternion = (rot[3], rot[0], rot[1], rot[2])
        pb.location, pb.scale = loc, scale
    bpy.context.view_layer.update()


def pose_rel():
    pose = {}
    for pb in arm.pose.bones:
        rest_local = pb.bone.parent.matrix_local.inverted() @ pb.bone.matrix_local if pb.bone.parent else pb.bone.matrix_local
        local = pb.parent.matrix.inverted() @ pb.matrix if pb.parent else pb.matrix
        pose[pb.name] = tuple((rest_local.inverted() @ local).to_quaternion())
    return pose


def bed_matrix(config):
    s = config["sword_socket"]["bed_socket"]
    return Matrix.Translation(Vector(s["head_m"])) @ Quaternion(s["quaternion_wxyz"]).to_matrix().to_4x4()


def active(w, group):
    return [layer for layer, value in w[group].items() if value > 1e-12]


def evaluate(scenario, t, weights_override=None):
    """Pose, foot lock, socket, helpers, states and correctives at wall time t; returns the sample's bookkeeping.
    A weights override (diagnostic snapshots of single layers) skips the foot lock."""
    starts = tr.layers(scenario)
    lock = weights_override is None
    if lock:
        locks = locks_of(scenario)
        for side in fl.SIDES:
            for at in fl.needed_times(locks[side], t):
                if at != t:
                    fk_soles(scenario, at)
    pose, frames, w = blended_pose(scenario, t, weights_override)
    set_pose(pose)
    foot_targets = apply_foot_lock(scenario, t) if lock else {}
    hands = active(w, "upper")
    sockets = {interaction.socket_at(configs[starts[layer]["clip"]], frames[layer]) for layer in hands if starts[layer]["clip"] in SOCKETED}
    if len(sockets) > 1:
        raise SystemExit(f"TRANSITION_SOCKET_CONFLICT {scenario['id']} t={t} {sockets}")
    socket = sockets.pop() if sockets else None
    sword = arm.pose.bones["sword"]
    if socket == "bed":
        bed_clip = next(starts[layer]["clip"] for layer in hands if starts[layer]["clip"] in SOCKETED)
        sword.matrix = arm.matrix_world.inverted() @ bed_matrix(configs[bed_clip])
        bpy.context.view_layer.update()
    elif socket == "hand":
        sword.location, sword.rotation_quaternion, sword.scale = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
    if args.fault == "weapon-in-hand" and (socket in (None, "hand")):
        # Counterexample: the sword 6 mm toward the palm (contract hand frame carried by the posed hand bone).
        hand = arm.pose.bones["hand.R"]
        carry = hand.matrix.to_3x3() @ hand.bone.matrix_local.to_3x3().inverted()
        palmar = (carry @ PALMAR_REST).normalized()
        sword.matrix = Matrix.Translation(palmar * 0.006) @ sword.matrix
        bpy.context.view_layer.update()
    rel = pose_rel()
    for name, quaternion in rules_math.helper_rotations(rules, rel, REST_LOCAL, PARENTS).items():
        arm.pose.bones[name].rotation_quaternion = Quaternion(quaternion)
        rel[name] = quaternion
    bpy.context.view_layer.update()
    keys = sorted({d["key"] for d in rules["drivers"].values() if d["type"] == "state"})
    layer_states = {}
    for layer, frame in frames.items():
        if frame is not None:
            states = interaction.states_at(configs[starts[layer]["clip"]], frame)
            layer_states[layer] = {k: float(states.get(k, 0.0)) for k in keys}
    state = {k: v for k, v in tr.blend_states(w, layer_states).items() if k in keys}
    for k in keys:
        state.setdefault(k, 0.0)
    weights = rules_math.evaluate(rules, rel, state)
    for (mesh_name, key_name), value in weights.items():
        bpy.data.objects[mesh_name].data.shape_keys.key_blocks[key_name].value = value
    bpy.context.view_layer.update()
    return {"frames": frames, "weights": w, "socket": socket, "state": state, "pose": pose, "rel": rel, "foot_targets": foot_targets,
            "drivers": rules_math.driver_values(rules, rel, state), "morph_weights": {f"{m}/{k}": v for (m, k), v in weights.items()}}


# ---- measurement set-up (as scripts/cv1_clip_check.py) ----
scene = bpy.context.scene
skinned = sorted((o for o in bpy.data.objects if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers))), key=lambda o: o.name)
meshes = [o for o in skinned if o.name not in set(limits["excluded_meshes"])]
sword_obj = bpy.data.objects["SM_RO_sword"]
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
for obj in skinned:
    for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
        key.value = 0.0
bpy.context.view_layer.update()
soup = Soup(meshes, limits)
soup.set_rest()
sole = {side: [soup.offsets[mesh] + i for mesh, ids in fixtures["fixtures"][f"sole_set.{side}"]["ids"].items() for i in ids] for side in ("L", "R")}
BED_SETS = ("back", "pelvis", "head_back", "calf.L", "calf.R")
support = {key: [soup.offsets[mesh] + i for mesh, ids in fixtures["fixtures"][f"bed_support.{key}"]["ids"].items() for i in ids] for key in BED_SETS}
point_mesh = [name for obj in meshes for name in [obj.name] * len(obj.data.vertices)]
from ro_certified_grasp_gate import certified_contacts  # r010 functional gate, thresholds unchanged
MODULES = {Path(m.__file__).name: sha(m.__file__) for m in (interaction, rules_math, tr, fl, sys.modules["cv1_soup"], sys.modules["cv1_contract_pose"], sys.modules["ro_certified_grasp_gate"])}
SCRIPT_SHA256 = sha(__file__)  # the version that runs (read at start, so a later edit of the file cannot relabel the run)
pads = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r010/local-contract.json").read_text(encoding="utf-8"))["pads"]
forward = Vector(contract["axes"]["forward"])

# ---- stance-foot lock (user decision A1, authorization entry 25; scripts/cv1_foot_lock.py) ----
# World frame (the armature's matrix_world applied). The sole point is the rest sole_set centroid carried rigidly by the
# foot bone; the runtime gets the same rest point and derives its own foot-bone offset.
AW = arm.matrix_world.copy()
UP = (0.0, 0.0, 1.0)
FORWARD = tuple(float(c) for c in forward)
FALLBACK_NORMAL = fl.scale(fl.cross(UP, FORWARD), -1.0)  # knee-bend axis of a straight leg facing forward
LEG = {side: (f"upper_leg.{side}", f"lower_leg.{side}", f"foot.{side}", f"toe.{side}") for side in fl.SIDES}  # the toe gives the knee its pole
SOLE_REST_WORLD = {side: tuple(float(c) for c in sum((soup.rest[i] for i in sole[side]), Vector()) / len(sole[side])) for side in fl.SIDES}
SOLE_LOCAL = {side: arm.data.bones[LEG[side][2]].matrix_local.inverted() @ (AW.inverted() @ Vector(SOLE_REST_WORLD[side])) for side in fl.SIDES}
FL_CLIPS = {short: {"frames": c["frames"], "loop": c["loop"], "fps": c["fps"], "nominal_speed_m_s": clips[short]["nominal_speed_m_s"],
                    "stance": configs[short]["stance"]} for short, c in lookup.items()}
FOOT_LOCK = {"constants": {"release_s": fl.RELEASE_S, "settle_s": fl.SETTLE_S, "settle_lift_m": fl.SETTLE_LIFT_M, "settle_lift_share": fl.SETTLE_LIFT_SHARE,
                           "horizon_s": fl.HORIZON_S, "pole_weight": fl.POLE_WEIGHT},
             "sole_rest_world_blender": SOLE_REST_WORLD, "forward_blender": FORWARD, "up_blender": UP, "fallback_normal_blender": FALLBACK_NORMAL,
             "legs": LEG, "source": "scripts/cv1_foot_lock.py (user decision A1, authorization entry 25)"}
_locks, _fk_soles = {}, {}


def locks_of(scenario):
    if scenario["id"] not in _locks:
        _locks[scenario["id"]] = fl.schedule(scenario, FL_CLIPS)
    return _locks[scenario["id"]]


def sole_points():
    out = {}
    for side in fl.SIDES:
        p = AW @ (arm.pose.bones[LEG[side][2]].matrix @ SOLE_LOCAL[side])
        out[side] = (float(p.x), float(p.y), float(p.z))
    return out


def fk_soles(scenario, t):
    """Lock-free sole points at t; sets that pose, so callers fetch these before posing their own sample."""
    key = (scenario["id"], t)
    if key not in _fk_soles:
        pose, _, _ = blended_pose(scenario, t)
        set_pose(pose)
        _fk_soles[key] = sole_points()
    return _fk_soles[key]


def world_quat(pb):
    q = (AW @ pb.matrix).to_quaternion()
    n = math.sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z)
    return (q.w / n, q.x / n, q.y / n, q.z / n)


def world_point(v):
    p = AW @ v
    return (float(p.x), float(p.y), float(p.z))


def local_basis(name, parent_world, world):
    """Pose-bone rotation (w, x, y, z) that gives `world` under a parent at `parent_world` (unit scale)."""
    return fl.qmul(fl.qconj(REST_LOCAL[name]), fl.qmul(fl.qconj(parent_world), world))


def apply_foot_lock(scenario, t):
    """Pins the locked feet of the current (lock-free) pose; returns {side: [mode, target]} for the feet it moved."""
    locks, current = locks_of(scenario), sole_points()

    def fk(side, at):
        return current[side] if at == t else _fk_soles[(scenario["id"], at)][side]

    moved, basis = {}, {}
    for side in fl.SIDES:
        target = fl.sole_target(scenario, FL_CLIPS, locks[side], side, t, fk, FORWARD, UP)
        if target is None:
            continue
        thigh, shin, foot, toe = (arm.pose.bones[name] for name in LEG[side])
        hip, knee, ankle = world_point(thigh.head), world_point(shin.head), world_point(foot.head)
        pole = fl.sub(world_point(toe.head), ankle)
        knee_turn, hip_turn = fl.two_bone(hip, knee, ankle, fl.add(ankle, fl.sub(target, current[side])), pole, FALLBACK_NORMAL)
        new_thigh = fl.qmul(hip_turn, world_quat(thigh))
        new_shin = fl.qmul(fl.qmul(hip_turn, knee_turn), world_quat(shin))
        basis[thigh.name] = local_basis(thigh.name, world_quat(thigh.parent), new_thigh)
        basis[shin.name] = local_basis(shin.name, new_thigh, new_shin)
        basis[foot.name] = local_basis(foot.name, new_shin, world_quat(foot))
        moved[side] = [fl.mode_at(locks[side], t)[0], list(target)]
    for name, q in basis.items():
        arm.pose.bones[name].rotation_quaternion = q
    if basis:
        bpy.context.view_layer.update()
    return moved


def crossing(tri, plane):
    normal = (plane[1] - plane[0]).cross(plane[2] - plane[0])
    if normal.length < 1e-14:
        return 0.0
    normal.normalize()
    side = [(p - plane[0]).dot(normal) for p in tri]
    return min(max(0.0, max(side)), max(0.0, -min(side)))


def weapon_body(points):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = sword_obj.evaluated_get(depsgraph)
    mesh = target.to_mesh()
    mesh.calc_loop_triangles()
    sp = [target.matrix_world @ v.co for v in mesh.vertices]
    st = [tuple(lt.vertices) for lt in mesh.loop_triangles]
    target.to_mesh_clear()
    depth = 0.0
    for i, j in BVHTree.FromPolygons(sp, st, all_triangles=True).overlap(BVHTree.FromPolygons(points, soup.tris, all_triangles=True)):
        if not soup.tri_hand[j]:
            depth = max(depth, min(crossing([sp[k] for k in st[i]], [points[k] for k in soup.tris[j]]), crossing([points[k] for k in soup.tris[j]], [sp[k] for k in st[i]])))
    return depth


def bed_of(scenario):
    for layer, start in tr.layers(scenario).items():
        if configs[start["clip"]].get("bed"):
            return configs[start["clip"]]["bed"]
    return None


def over_bed(bed, p):
    yaw = math.radians(bed["yaw_deg"])
    c, s = math.cos(yaw), math.sin(yaw)
    cx, cy = bed["centre_m"]
    return abs((p.x - cx) * c + (p.y - cy) * s) <= bed["size_m"][0] / 2 and abs(-(p.x - cx) * s + (p.y - cy) * c) <= bed["size_m"][1] / 2


def all_layers(predicate, layers_, info, scenario):
    starts = tr.layers(scenario)
    return bool(layers_) and all(predicate(configs[starts[l]["clip"]], info["frames"][l]) for l in layers_)


def measure(scenario, t, info, points):
    measured = soup.measure(points)
    row = {"t": round(t, 9), "frames": {l: (round(f, 4) if f is not None else None) for l, f in info["frames"].items()},
           "weights": {g: {l: round(v, 6) for l, v in info["weights"][g].items() if v > 1e-12} for g in tr.GROUPS}, "socket": info["socket"],
           "state": {k: round(v, 6) for k, v in info["state"].items()},
           "collapsed": measured["collapsed_triangles"], "min_area_ratio": round(measured["min_triangle_area_ratio"], 5),
           "hand_self": measured["hand_self_pairs"], "hand_other_new": measured["hand_other_new_pairs"], "flipped": measured["flipped_triangles"]}
    if measured["collapsed_triangles"]:
        row["collapsed_examples"] = [dict(e, dominant=sorted({soup.dominant[i] for i in soup.tris[e["triangle"]]})) for e in measured["collapsed_examples"][:3]]
    row["weapon_body_m"] = weapon_body(points)
    report = certified_contacts(bpy.data.objects["SM_RO_hand.R"], sword_obj, arm, pads, f"{scenario['id']}@{t}", {"scenario": scenario["id"], "t": t})
    in_window = all_layers(lambda c, f: interaction.covered(c["states"]["grasp.R"]["windows"], f, c["loop"]), active(info["weights"], "upper"), info, scenario)
    row["grasp"] = {"in_window": in_window, "surface_gate_pass": report["surface_gate_pass"], "unknown_inside": len(report["unknown_inside"]),
                    "crossings": report["transverse_crossings_count"], "penetration_m": report["maximum_penetration_m"]}
    row["grasp"]["pass"] = report["surface_gate_pass"] if in_window else (not report["unknown_inside"] and not report["transverse_crossings_count"]
                                                                       and report["maximum_penetration_m"] <= THRESHOLDS["grasp_outside_penetration_m"])
    legs = active(info["weights"], "lower")
    row["feet"] = {}
    for side in ("L", "R"):
        xs = [points[i] for i in sole[side]]
        centre = sum(xs, Vector()) / len(xs)
        row["feet"][side] = {"stance": all_layers(lambda c, f: fl.in_stance(c, side, f), legs, info, scenario),
                             "centroid_xy": [centre.x, centre.y], "min_z": min(p.z for p in xs)}
    locks = locks_of(scenario)
    row["foot_lock"] = {side: fl.mode_at(locks[side], t)[0] for side in fl.SIDES}
    starts = tr.layers(scenario)
    row["speed_mps"] = sum(info["weights"]["lower"].get(l, 0.0) * clips[starts[l]["clip"]]["nominal_speed_m_s"] * starts[l]["speed"] for l in info["weights"]["lower"])
    bed = bed_of(scenario)
    if bed:
        top = bed["top_z_m"]
        in_support = all_layers(lambda c, f: bool(c.get("bed_support")) and interaction.covered(c["bed_support"]["windows"], f, c["loop"]), active(info["weights"], "lower"), info, scenario)
        sets = {}
        for key, ids in support.items():
            xs = [points[i] for i in ids]
            sets[key] = {"min_z": min(p.z for p in xs), "over_bed": all(over_bed(bed, p) for p in xs)}
        row["bed_support"] = {"in_window": in_support, "pass": (not in_support) or all(abs(s["min_z"] - top) <= THRESHOLDS["bed_support_m"] and s["over_bed"] for s in sets.values()),
                              "worst_m": max(abs(s["min_z"] - top) for s in sets.values())}
        near_event = any(interaction.near_socket_event(configs[starts[l]["clip"]], info["frames"][l], THRESHOLDS["bed_clearance_hand_event_window_frames"]) for l in active(info["weights"], "upper"))
        hand_limit = THRESHOLDS["bed_clearance_hand_m"] if near_event else THRESHOLDS["bed_clearance_m"]
        # User decision B1 (entry 25): only the bed-clip layers that drive the legs decide; other layers are neutral.
        seated = all_layers(lambda c, f: interaction.seated_on_bed(c, f), [l for l in legs if configs[starts[l]["clip"]].get("bed")], info, scenario)
        depth, other_mesh = {"hand": 0.0, "other": 0.0, "exempt_coat": 0.0}, None
        for i, p in enumerate(points):
            if p.z >= top or not over_bed(bed, p):
                continue
            kind = "exempt_coat" if seated and point_mesh[i] == "SM_RO_coat" else ("hand" if soup.is_hand_vertex[i] else "other")
            if top - p.z > depth[kind]:
                depth[kind] = top - p.z
                other_mesh = point_mesh[i] if kind == "other" else other_mesh
        row["bed_clearance"] = {**{k: round(v, 6) for k, v in depth.items()}, "other_mesh": other_mesh, "hand_limit_m": hand_limit, "seated": seated,
                                "pass": depth["other"] <= THRESHOLDS["bed_clearance_m"] and depth["hand"] <= hand_limit}
    return row


def pose_distance(a, b):
    """Largest bone angle (deg) between two poses (quaternions normalised first) and the pelvis location distance (m)."""
    worst = 0.0
    for name in a:
        qa, qb = a[name][0], b[name][0]
        norm = math.sqrt(sum(x * x for x in qa) * sum(x * x for x in qb))
        dot = min(1.0, abs(sum(x * y for x, y in zip(qa, qb))) / norm)
        worst = max(worst, math.degrees(2 * math.acos(dot)))
    move = math.dist(a["pelvis"][1], b["pelvis"][1])
    return worst, move


def composed_pose(scenario, t, composition):
    """Independent reference pose: every bone straight from the clip of the layer its group is composed of (no weights,
    no mixing); composition {group: layer}."""
    starts = tr.layers(scenario)
    poses = {layer: layer_pose(starts[layer]["clip"], tr.layer_frame(scenario, lookup, layer, t)) for layer in set(composition.values())}
    return {b.name: poses[composition[GROUP[b.name]]].get(b.name, IDENTITY) for b in bones if b.name not in HELPERS}


def displayed_pose(scenario, t):
    """The evaluated pose at t (foot lock included) as {bone: (rotation xyzw, location, scale)}; helpers and the sword
    (its pose belongs to the socket gates) are left out."""
    evaluate(scenario, t)
    return {pb.name: ((pb.rotation_quaternion.x, pb.rotation_quaternion.y, pb.rotation_quaternion.z, pb.rotation_quaternion.w), tuple(pb.location), tuple(pb.scale))
            for pb in arm.pose.bones if pb.name not in HELPERS and pb.name != "sword"}


def continuity(scenario):
    """r6 transition_matrix.gates.continuity: at each fade start the evaluated pose equals the source clips' pose and at
    the transition end the target clips' pose (upper-body fades: target upper body over the unchanged lower body), the
    references taken straight from the clips, so the weights, the mixer and the foot lock are checked rather than
    reused. The transition ends at the fade end or, while a foot lock, release or settle is still running then, when the
    last of them has let go.
    A fade that starts while an earlier fade or foot lock is still running has no single source: its start is compared
    with the pose of the events before it at the same time, and a transition interrupted by the next event has no end."""
    rows, events = [], scenario["events"]
    locks = locks_of(scenario)
    comp = {g: events[0]["layer"] for g in tr.GROUPS}
    for k, event in enumerate(events[1:], start=1):
        t0, t1 = event["t"], event["t"] + event["blend_s"]
        prev = events[k - 1]
        t_end, moved = t1, True
        while moved:  # extend while any lock, release or settle is running at t_end
            moved = False
            for e in (e for side in fl.SIDES for e in locks[side]):
                end = (e.get("release") or e["settle"])[1]
                if e["lock"][0] <= t_end < end:
                    t_end, moved = end, True
        held = [fl.mode_at(locks[side], t0) for side in fl.SIDES]  # a lock that begins at t0 has no offset yet
        busy = (k > 1 and t0 < prev["t"] + prev["blend_s"]) or any(kind is not None and entry["lock"][0] < t0 for kind, entry in held)
        at = displayed_pose(scenario, t0)
        if busy:
            source, against = displayed_pose({"id": f"{scenario['id']}#before{k}", "events": events[:k]}, t0), "pose_before"
        else:
            source, against = composed_pose(scenario, t0, comp), "source_clips"
        target = dict(comp, upper=event["layer"]) if event.get("mask") == "upper" else {g: event["layer"] for g in tr.GROUPS}
        d0, m0 = pose_distance(at, source)
        row = {"event": k, "start_against": against, "start_deg": d0, "start_m": m0, "end_t": t_end, "end_deg": None, "end_m": None}
        if k + 1 == len(events) or t_end <= events[k + 1]["t"]:
            row["end_deg"], row["end_m"] = pose_distance(displayed_pose(scenario, t_end), composed_pose(scenario, t_end, target))
        else:
            row["end"] = "interrupted"
        row["pass"] = (max(v for v in (d0, row["end_deg"]) if v is not None) <= THRESHOLDS["continuity_deg"]
                       and max(v for v in (m0, row["end_m"]) if v is not None) <= THRESHOLDS["continuity_m"])
        rows.append(row)
        comp = target
    return rows


def _slide_runs(rows, side, member):
    """Largest slide (minus the blended nominal drift) over runs of consecutive rows that satisfy member(row)."""
    worst, runs, run = 0.0, 0, []
    for row in rows + [None]:
        if row is not None and member(row):
            run.append(row)
            continue
        if len(run) > 1:
            runs += 1
            drift, first = 0.0, run[0]
            for prev, cur in zip(run, run[1:]):
                drift += 0.5 * (prev["speed_mps"] + cur["speed_mps"]) * (cur["t"] - prev["t"])
                expected = Vector((*first["feet"][side]["centroid_xy"], 0.0)) - forward * drift
                worst = max(worst, (Vector((*cur["feet"][side]["centroid_xy"], 0.0)) - expected).length)
        run = []
    return worst, runs


def feet_slide(scenario, rows):
    """Per foot: runs of samples where every leg-driving layer has the foot in stance; the slide from the run's first
    sample minus the drift. Inside a release or settle of this foot a sole lifted more than LIFT_BREAK_M above the
    scenario's lowest stance height leaves the run (the synthesised step is not a slide; its lift and travel are
    reported); elsewhere a lifted stance sample still counts (a lock the leg cannot reach lifts the foot).
    Diagnostic (not gated): the same slide over runs where the sole is down whatever the windows declare."""
    out, locks = {}, locks_of(scenario)
    for side in fl.SIDES:
        stance_z = [r["feet"][side]["min_z"] for r in rows if r["feet"][side]["stance"]]
        ground = min(stance_z) if stance_z else math.inf
        floor = min(r["feet"][side]["min_z"] for r in rows)
        down = lambda r, base: r["feet"][side]["min_z"] <= base + LIFT_BREAK_M  # noqa: E731
        # Only a release or settle of this foot may leave the run by lifting (the synthesised step); a stance sample in a
        # lock, or with no lock, always counts, so a lock the leg cannot reach (the foot lifts) shows as a slide.
        worst, runs = _slide_runs(rows, side, lambda r: r["feet"][side]["stance"] and (down(r, ground) or r["foot_lock"][side] not in ("release", "settle")))
        diagnostic, _ = _slide_runs(rows, side, lambda r: down(r, floor))
        settles = []
        for entry in locks[side]:
            if "settle" in entry:
                inside = [r for r in rows if entry["settle"][0] <= r["t"] <= entry["settle"][1]]
                if inside:
                    a, b = inside[0]["feet"][side]["centroid_xy"], inside[-1]["feet"][side]["centroid_xy"]
                    settles.append({"t": entry["settle"], "samples": len(inside), "max_lift_m": max(r["feet"][side]["min_z"] for r in inside) - ground,
                                    "travel_m": math.dist(a, b)})
        out[side] = {"runs": runs, "slide_m": worst, "lifted_stance_samples": sum(1 for r in rows if r["feet"][side]["stance"] and not down(r, ground)),
                     "locked_lift_max_m": max([r["feet"][side]["min_z"] - ground for r in rows if r["feet"][side]["stance"] and r["foot_lock"][side] == "lock"], default=0.0),
                     "settles": settles, "contact_slide_diagnostic_m": diagnostic, "pass": worst <= THRESHOLDS["feet_slide_m"]}
    return out


def probe(items):
    """Diagnostic only (--probe "id@t;id@t"; never a result): the sample as measured, the same blend with the correctives
    off, and each active layer alone (its own states); the lowest triangle area ratios, the ratios of the triangles any
    of them puts lowest, the corrective weights and the deepest point under the bed top by mesh."""
    from cv1_soup import tri_area
    floor = limits["min_rest_triangle_area_m2"]
    by_id = {s["id"]: s for s in spec["scenarios"]}
    entries = []
    for item in items:
        sid, t = item.rsplit("@", 1)
        s, t = by_id[sid], float(t)
        tr.validate(s, lookup)
        bed = bed_of(s)

        def snapshot(info):
            points = soup.evaluated_points()
            ratios = sorted((tri_area(points, tri) / area, i) for i, (tri, area) in enumerate(zip(soup.tris, soup.rest_area)) if area > floor)
            deepest = {}
            if bed:
                for i, p in enumerate(points):
                    if p.z < bed["top_z_m"] and over_bed(bed, p):
                        deepest[point_mesh[i]] = max(deepest.get(point_mesh[i], 0.0), bed["top_z_m"] - p.z)
            return points, {"frames": info["frames"], "weights": info["weights"], "state": info["state"],
                            "morph_weights": {k: round(v, 6) for k, v in info["morph_weights"].items() if abs(v) > 1e-9},
                            "lowest": [{"triangle": i, "ratio": round(r, 5), "mesh": soup.tri_mesh[i], "dominant": sorted({soup.dominant[k] for k in soup.tris[i]})}
                                       for r, i in ratios[:6]],
                            "bed_depth_by_mesh_m": {k: round(v, 5) for k, v in sorted(deepest.items())}}

        snaps = {}
        info = evaluate(s, t)
        snaps["blend"] = snapshot(info)
        for obj in skinned:
            for key in (obj.data.shape_keys.key_blocks[1:] if obj.data.shape_keys else []):
                key.value = 0.0
        bpy.context.view_layer.update()
        snaps["blend_correctives_off"] = snapshot(dict(info, morph_weights={}))
        snaps["blend_without_foot_lock"] = snapshot(evaluate(s, t, tr.weights(s, t)))  # explicit weights skip the lock
        for layer in sorted({layer for g in tr.GROUPS for layer, v in info["weights"][g].items() if v > 1e-12}):
            snaps[f"only:{layer}"] = snapshot(evaluate(s, t, {g: {layer: 1.0} for g in tr.GROUPS}))
        watch = sorted({e["triangle"] for _, data in snaps.values() for e in data["lowest"][:3]})
        worst = snaps["blend"][1]["lowest"][0]["triangle"]
        vertex_groups = {}
        for k in soup.tris[worst]:
            obj = next(o for o in meshes if soup.offsets[o.name] <= k < soup.offsets[o.name] + len(o.data.vertices))
            v = obj.data.vertices[k - soup.offsets[obj.name]]
            vertex_groups[str(k)] = {obj.vertex_groups[g.group].name: round(g.weight, 4) for g in v.groups if g.weight > 0.005}
        involved = sorted({name for groups in vertex_groups.values() for name in groups if name in arm.pose.bones})
        entry = {"id": sid, "t": t, "watch": watch, "worst_triangle": worst, "worst_vertex_groups": vertex_groups, "snapshots": {}}
        entry["rest_neighbour_agreement"] = {str(i): soup.rest_agreement[i] for i in watch}
        for label, (points, data) in snaps.items():
            agreement = soup.normal_agreement(points)
            data["watch_ratios"] = {str(i): round(tri_area(points, soup.tris[i]) / soup.rest_area[i], 5) for i in watch}
            data["watch_neighbour_agreement"] = {str(i): (round(agreement[i], 4) if agreement[i] is not None else None) for i in watch}
            data["worst_points"] = [[round(c, 5) for c in points[k]] for k in soup.tris[worst]]
            entry["snapshots"][label] = data
        # Bone world rotations for the worst triangle's bones: re-evaluate each snapshot's pose (correctives do not move bones).
        for label in snaps:
            if label == "blend_correctives_off":
                continue
            override = {"blend": None, "blend_without_foot_lock": tr.weights(s, t)}.get(label, None if label == "blend" else {g: {label[5:]: 1.0} for g in tr.GROUPS})
            evaluate(s, t, override)
            entry["snapshots"][label]["bones_world"] = {name: {"q_wxyz": [round(c, 6) for c in arm.pose.bones[name].matrix.to_quaternion()],
                                                               "head": [round(c, 5) for c in arm.pose.bones[name].head]} for name in involved}
        entries.append(entry)
        print("CV1_TRANSITION_PROBE " + json.dumps({"id": sid, "t": t, "min_ratio": {k: d["lowest"][0]["ratio"] for k, (_, d) in snaps.items()}}))
    return entries


# ---- run ----
def run_matrix():
    index, count = (int(x) for x in args.shard.split("/"))
    only = {s for s in args.only.split(",") if s}
    chosen = [s for i, s in enumerate(spec["scenarios"]) if i % count == index and (not only or s["id"] in only)]
    for s in chosen:
        tr.validate(s, lookup)
    out.mkdir(parents=True)
    blob, blocks = array("f"), []  # reference positions as float32 (resolution about 0.1 um at 1.5 m; the runtime gate is 10 um)
    results = []
    for s in chosen:
        rows = []
        for t in s["samples"]:
            info = evaluate(s, t)
            points = soup.evaluated_points()
            rows.append(measure(s, t, info, points))
            if args.reference and round(t, 9) in {round(x, 9) for x in s.get("reference_times", [])}:
                data = array("f")
                for p in points:
                    data.extend(p)
                blocks.append({"label": f"transition/{s['id']}@{round(t, 9)}", "scenario": s["id"], "t": round(t, 9), "offset_values": len(blob), "values": len(data),
                               "frames": info["frames"], "weights": info["weights"], "socket": info["socket"], "state": info["state"],
                               "foot_targets": info["foot_targets"], "drivers": info["drivers"], "morph_weights": info["morph_weights"]})
                blob.extend(data)
        cont = continuity(s)
        feet = feet_slide(s, rows)
        gates = {"no_collapse": all(r["collapsed"] == 0 for r in rows), "hand_self_zero": all(r["hand_self"] == 0 for r in rows),
                 "hand_other_new_zero": all(r["hand_other_new"] == 0 for r in rows), "weapon_body": all(r["weapon_body_m"] <= THRESHOLDS["weapon_body_m"] for r in rows),
                 "grasp": all(r["grasp"]["pass"] for r in rows), "feet_slide": all(f["pass"] for f in feet.values()), "continuity": all(c["pass"] for c in cont)}
        if any("bed_support" in r for r in rows):
            gates["bed_support"] = all(r["bed_support"]["pass"] for r in rows)
            gates["bed_clearance"] = all(r["bed_clearance"]["pass"] for r in rows)
        failing = sorted({k for r in rows for k, ok in (("collapse", r["collapsed"] == 0), ("hand_self", r["hand_self"] == 0), ("hand_other_new", r["hand_other_new"] == 0),
                                                           ("weapon_body", r["weapon_body_m"] <= THRESHOLDS["weapon_body_m"]), ("grasp", r["grasp"]["pass"]),
                                                           ("bed_clearance", r.get("bed_clearance", {}).get("pass", True))) if not ok})
        result = {"id": s["id"], "pair": s["pair"], "blend_s": s["blend_s"], "speed": s["speed"], "samples": len(rows), "gates": gates, "pass": all(gates.values()),
                  "foot_lock": locks_of(s), "fade_timing": s.get("fade_timing"),
                  "failing_kinds": failing, "failing_times": [r["t"] for r in rows if (r["collapsed"] or r["hand_self"] or r["hand_other_new"] or r["weapon_body_m"] > THRESHOLDS["weapon_body_m"]
                                                                                      or not r["grasp"]["pass"] or not r.get("bed_clearance", {}).get("pass", True))][:20],
                  "worst": {"min_area_ratio": min(r["min_area_ratio"] for r in rows), "weapon_body_m": max(r["weapon_body_m"] for r in rows),
                            "grasp_penetration_m": max(r["grasp"]["penetration_m"] for r in rows), "feet": feet, "continuity": cont,
                            "bed_clearance_other_m": max((r["bed_clearance"]["other"] for r in rows if "bed_clearance" in r), default=None)},
                  "rows": rows}
        results.append(result)
        print("CV1_TRANSITION " + json.dumps({"id": s["id"], "pass": result["pass"], "failing": failing}))
    record = {"observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": SCRIPT_SHA256,
              "foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False},
              "modules": MODULES,
              "inputs": {"scenarios": art(args.scenarios), "rules": art(args.rules), "contract": art(args.contract), "fixtures": art(args.fixtures),
                         "clips": {short: {"blend": art(c["blend"]), "interaction": art(c["interaction"]), "registry_entry": registry_entries[short]} for short, c in clips.items()}},
              "thresholds": THRESHOLDS, "foot_lock": FOOT_LOCK, "shard": args.shard, "fault": args.fault or None,
              "scope": "Measured sample times of the listed scenarios only; numeric gates are not art acceptance." + (" COUNTEREXAMPLE RUN (disposable): not a result." if args.fault else ""),
              "scenarios": results}
    (out / "transition-check.json").write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if args.reference:
        (out / "transition-reference.f32.bin").write_bytes(blob.tobytes())
        offset, layout = 0, []
        for obj in meshes:
            layout.append({"name": obj.name, "vertices": len(obj.data.vertices), "offset_values_in_block": offset,
                           "morphs": [k.name for k in obj.data.shape_keys.key_blocks[1:]] if obj.data.shape_keys else []})
            offset += 3 * len(obj.data.vertices)
        (out / "transition-reference.json").write_text(json.dumps({
            "observed_utc": record["observed_utc"], "script_sha256": record["script_sha256"], "inputs": record["inputs"], "fps": 60,
            "coordinates": "Blender world metres, Z up, -Y front; glTF (x, y, z) = Blender (x, z, -y)", "id_attribute": "_CV1_ID",
            "binary": {"path": (out / "transition-reference.f32.bin").relative_to(ROOT).as_posix(), "sha256": sha(out / "transition-reference.f32.bin"),
                       "dtype": "float32 little-endian", "values_per_vertex": 3}, "mesh_layout": layout, "measured_meshes_only": True, "foot_lock": FOOT_LOCK,
            "blocks": blocks, "scope": "Transition reference samples (scenario reference_times); vertex order = cv1_soup measured meshes."}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8", newline="\n")
    print("CV1_TRANSITION_DONE " + json.dumps({"scenarios": len(results), "passed": sum(r["pass"] for r in results), "reference_blocks": len(blocks)}))


if args.continuity_only:
    # Continuity gate alone (no mesh measurement): every chosen scenario, poses straight from the clips.
    index, count = (int(x) for x in args.shard.split("/"))
    only = {s for s in args.only.split(",") if s}
    chosen = [s for i, s in enumerate(spec["scenarios"]) if i % count == index and (not only or s["id"] in only)]
    for s in chosen:
        tr.validate(s, lookup)
    out.mkdir(parents=True)
    rows = [{"id": s["id"], "pair": s["pair"], "continuity": continuity(s)} for s in chosen]
    for r in rows:
        r["pass"] = all(c["pass"] for c in r["continuity"])
    (out / "continuity-check.json").write_text(json.dumps({"observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string,
                                                           "script_sha256": SCRIPT_SHA256, "modules": MODULES, "scenarios_file": art(args.scenarios), "thresholds": THRESHOLDS,
                                                           "scope": "r6 transition_matrix.gates.continuity only; the other gates are in transition-check.json.",
                                                           "summary": {"scenarios": len(rows), "passed": sum(r["pass"] for r in rows)}, "scenarios": rows},
                                                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("CV1_CONTINUITY_DONE " + json.dumps({"scenarios": len(rows), "passed": sum(r["pass"] for r in rows)}))
elif args.probe:
    out.mkdir(parents=True)
    (out / "probe.json").write_text(json.dumps({"observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string,
                                                "script_sha256": SCRIPT_SHA256, "modules": MODULES, "scenarios": art(args.scenarios),
                                                "scope": "Diagnostic probe only; not a result.", "probes": probe([x for x in args.probe.split(";") if x])},
                                               ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
else:
    run_matrix()
