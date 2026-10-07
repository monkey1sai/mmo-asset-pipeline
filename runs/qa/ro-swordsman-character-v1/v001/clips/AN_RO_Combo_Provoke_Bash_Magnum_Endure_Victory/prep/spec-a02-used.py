"""Clip spec and interaction config of AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory attempt a02 (run from the worktree root).

Usage: python -B .../prep/spec-a02-used.py
300 keyed frames at 60 fps (r6 animation_contract), in place, from and back to the Idle a03 frame-0 pose so Idle->Combo->Idle
can fade. Phases (reference_order): provoke 10-70, bash 70-135, magnum_break 135-200, endure 200-255, victory 255-299.
Choreography follows the twelve poses of assets/raw/ro-swordsman-combo/references-v001/ro_swordsman_action_sheet.jpg
(re-authored, no motion taken from the r001/r002 attempts: p3-plan-review-01 D2). Two-hand phases use the frozen
two_hand_chop pose (r6 frozen_poses) with the sword on its grip point, moved with the pelvis. Effects are a separate
layer timed by the events (bash_slash, magnum_impact, endure_start, victory).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
CLIP = "AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory"
OUT = ROOT / "assets/processed/ro-swordsman-character-v1/v001/clips" / CLIP
FRAMES, LAST = 300, 299
# Idle a03 frame-0 values (procedural waves evaluated at frame 0; the Cast clip starts from the same numbers).
IDLE = {"head_fwd": 1.4045, "ual_twist_fwd": -4.6473, "lal_twist_right": 15.809, "fingers_01": [15, 18, 21, 24], "fingers_02": [18, 22, 25, 28], "thumb": 10}
IDLE_GRIP, IDLE_BLADE, IDLE_PITCH, IDLE_ROLL, IDLE_SWIVEL = [-0.38, -0.1, 0.900927], [-0.587, -0.492, 0.643], 0.4702, 170.0, -10.0
PELVIS_REST = [0.0, 0.04, 0.89]
ANKLE = {"L": [0.195, 0.075, 0.105], "R": [-0.195, 0.075, 0.105]}
# two_hand_chop (frozen): the raised two-hand guard, sword bone at the grip point with the blade 65 deg UP-forward (measured on the pose:
# prep/chop-sword-used.py), roll 180 in the sword_world convention, elbow swivel -40, solved with the pelvis at rest and the spine at rest.
CHOP_GRIP, CHOP_BLADE, CHOP_ROLL, CHOP_SWIVEL = [0.0, -0.38, 1.26], [0.0, -0.4226, 0.9063], 180.0, -40.0
import math


def k(*pairs):
    return {"keys": [list(p) for p in pairs]}


pelvis_keys = [(0, PELVIS_REST), (10, PELVIS_REST), (36, [0.0, 0.10, 0.80]), (56, [0.0, 0.10, 0.80]), (70, [0.0, 0.06, 0.80]), (96, [0.0, 0.08, 0.80]),
               (112, [0.0, -0.12, 0.76]), (135, [0.0, 0.0, 0.80]), (150, [0.0, 0.02, 0.70]), (160, [0.0, -0.02, 1.12]), (172, [0.0, -0.04, 0.62]),
               (200, [0.0, -0.02, 0.64]), (215, [0.0, 0.04, 0.78]), (245, [0.0, 0.04, 0.78]), (262, [0.0, 0.04, 0.80]), (276, [0.0, 0.04, 0.80]),
               (286, PELVIS_REST), (LAST, PELVIS_REST)]
P = dict(pelvis_keys)


def pelvis_at(f):
    """Pelvis head at frame f (the author's smoothstep between keys)."""
    keys = pelvis_keys
    if f <= keys[0][0]:
        return list(keys[0][1])
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0); u = t * t * (3 - 2 * t)
            return [a + (b - a) * u for a, b in zip(v0, v1)]
    return list(keys[-1][1])


def smooth_keys(keys, f):
    keys = sorted(keys, key=lambda x: x[0])
    if f <= keys[0][0]:
        return list(keys[0][1])
    for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0); u = t * t * (3 - 2 * t)
            return [a + (b - a) * u for a, b in zip(v0, v1)]
    return list(keys[-1][1])


def grip_keys(offset_keys):
    """Sword grip keys = pelvis + offset at every offset key AND every pelvis key in between, so a held sword rides with the body
    between keys too (the author eases each channel between its own keys; a grip keyed only at the span ends would float
    while the pelvis dips or jumps in between)."""
    frames = sorted({f for f, _ in offset_keys} | {f for f, _ in pelvis_keys if offset_keys[0][0] <= f <= offset_keys[-1][0]})
    return k(*((f, [a + b for a, b in zip(pelvis_at(f), smooth_keys(offset_keys, f))]) for f in frames))


def rel(f, offset):
    """Pelvis at frame f plus an offset (a held sword rides with the body)."""
    return [a + b for a, b in zip(pelvis_at(f), offset)]


IDLE_OFF = [a - b for a, b in zip(IDLE_GRIP, PELVIS_REST)]
CHOP_OFF = [a - b for a, b in zip(CHOP_GRIP, PELVIS_REST)]
# Approach point for the two-hand grip: 85 % of the way from the right shoulder (rest offset from the pelvis head) to the
# chop grip, same blade direction, roll and swivel, so only the reach changes while the arm closes on the frozen pose.
SHOULDER_OFF = [-0.205, 0.03, 0.44]
CHOP_NEAR = [sh + 0.85 * (g - sh) for sh, g in zip(SHOULDER_OFF, CHOP_OFF)]
# Forward lean of the whole body (pelvis turn about world X, negative = forward): with the frozen guard held, leaning tilts the
# raised sword towards the ground for the magnum chop (sheet poses 7-8) and back up for the endure guard (poses 9-11).
# Positive = forward (a +X turn takes the head towards -Y). The guard's blade (65 deg up) comes down to near horizontal at 55 deg.
lean_keys = [(0, 0.0), (140, 0.0), (150, 10.0), (160, 30.0), (172, 55.0), (186, 50.0), (200, 20.0), (215, 10.0), (245, 10.0), (262, 0.0), (LAST, 0.0)]
# Every channel that rides on the pelvis (location, lean, sword grip/blade/roll) shares one key set over the guard span, so their
# easing between keys is the same and the sword stays on the frozen pose's hands between keys as well.
_union = sorted({f for f, _ in pelvis_keys if 135 <= f <= 262} | {f for f, _ in lean_keys if 135 <= f <= 262} | {135, 140, 156, 248, 262})


def lean_at(f):
    return smooth_keys([(fr, [v]) for fr, v in lean_keys], f)[0]


def _densify(keys, frames):
    keys = sorted(keys, key=lambda x: x[0])
    return sorted({f for f, _ in keys} | set(frames)) and [(f, (smooth_keys(keys, f) if isinstance(keys[0][1], list) else smooth_keys([(fr, [v]) for fr, v in keys], f)[0])) for f in sorted({f for f, _ in keys} | set(frames))]


pelvis_keys = _densify(pelvis_keys, _union)
lean_keys = _densify(lean_keys, _union)
P = dict(pelvis_keys)
GUARD_FRAMES = sorted(f for f in _union if 135 <= f <= 248)


def rot_x(v, deg):
    a = math.radians(deg); c, s_ = math.cos(a), math.sin(a)
    return [v[0], v[1] * c - v[2] * s_, v[1] * s_ + v[2] * c]


def sword_roll(blade, x_axis):
    """Roll in the sword_world convention (side = blade x Z, up = side x blade) that puts the sword X axis on x_axis."""
    b = blade; n = math.sqrt(sum(c * c for c in b)); b = [c / n for c in b]
    side = [b[1], -b[0], 0.0]; n = math.sqrt(side[0] ** 2 + side[1] ** 2); side = [side[0] / n, side[1] / n, 0.0] if n > 1e-6 else [1.0, 0.0, 0.0]
    up = [side[1] * b[2] - side[2] * b[1], side[2] * b[0] - side[0] * b[2], side[0] * b[1] - side[1] * b[0]]
    return math.degrees(math.atan2(sum(a * c for a, c in zip(x_axis, up)), sum(a * c for a, c in zip(x_axis, side)))) % 360.0


CHOP_X = [-1.0, 0.0, 0.0]  # sword X axis of the guard at zero lean (roll 180 with blade x Z = -X side... measured: roll 180)


def chop_sword_at(f, scale=1.0):
    """Grip, blade and roll of the frozen guard under the pelvis of frame f (location and forward lean); scale < 1 pulls the grip
    towards the shoulder along the shoulder-grip line (approach)."""
    lean = lean_at(f)
    off = rot_x(CHOP_OFF, lean); sh = rot_x(SHOULDER_OFF, lean)
    off = [a + scale * (b - a) for a, b in zip(sh, off)]
    grip = [a + b for a, b in zip(pelvis_at(f), off)]
    blade = rot_x(CHOP_BLADE, lean)
    x_axis = rot_x(_chop_x_axis(), lean)
    return grip, blade, sword_roll(blade, x_axis)


def _chop_x_axis():
    """Sword X axis at zero lean from the measured roll 180 in the sword_world convention."""
    b = CHOP_BLADE; side = [b[1], -b[0], 0.0]; n = math.sqrt(side[0] ** 2 + side[1] ** 2); side = [side[0] / n, side[1] / n, 0.0]
    up = [side[1] * b[2] - side[2] * b[1], side[2] * b[0] - side[0] * b[2], side[0] * b[1] - side[1] * b[0]]
    r = math.radians(CHOP_ROLL)
    return [si * math.cos(r) + u * math.sin(r) for si, u in zip(side, up)]


spec = {
    "schema_version": 1, "clip": CLIP, "fps": 60, "frames": FRAMES, "loop": False, "mode": "keys",
    "intent": "RO swordsman skill combo in place, from and back to the Idle frame-0 ready stance: provoke (wide stance, sword raised beside "
              "the head, left hand beckons twice), bash (overhead windup, lunge and one-handed slash down-forward at 112), magnum break (jump, "
              "two-hand chop into the ground at 172, crouch), endure (rise to a wide stance holding the sword two-handed, point down, hold), "
              "victory (release the left hand, stand tall, sword raised, fist pump at 268, return to Idle by 299). The twelve action-sheet poses "
              "in order; effects are a separate layer keyed to the events.",
    "poses": ["grasp.R", {"name": "two_hand_chop", "weight": k((140, 0.0), (156, 1.0), (248, 1.0), (262, 0.0))}],  # raised guard: jump, chop-by-lean, endure
    "pelvis": {"location_m": k(*pelvis_keys),
               "rotation": [{"axis": "x", "degrees": k(*lean_keys)},
                            {"axis": "z", "degrees": k((0, 0.0), (10, 0.0), (36, 18.0), (56, 18.0), (70, 10.0), (112, -8.0), (135, 0.0), (LAST, 0.0))}]},
    "legs_ik": {"weight": k((0, 1.0), (150, 1.0), (154, 0.0), (168, 0.0), (172, 1.0), (284, 1.0), (LAST, 0.0)), "pole_yaw_deg": 0.0, "reach": 1.0,
                "L": {"ankle_m": k((0, ANKLE["L"]), (10, ANKLE["L"]), (17, [0.27, 0.03, 0.26]), (24, [0.33, 0.0, 0.105]), (88, [0.33, 0.0, 0.105]),
                                   (94, [0.27, -0.16, 0.24]), (100, [0.20, -0.30, 0.105]), (150, [0.20, -0.30, 0.105]), (160, [0.24, -0.20, 0.40]),
                                   (170, [0.28, -0.12, 0.105]), (256, [0.28, -0.12, 0.105]), (262, [0.24, -0.02, 0.22]), (268, ANKLE["L"]), (LAST, ANKLE["L"])),
                      "foot_turn_deg": k((0, 0.0), (10, 0.0), (24, 12.0), (100, 6.0), (170, 10.0), (256, 10.0), (268, 0.0), (LAST, 0.0))},
                "R": {"ankle_m": k((0, ANKLE["R"]), (22, ANKLE["R"]), (29, [-0.25, 0.15, 0.26]), (36, [-0.30, 0.22, 0.105]), (150, [-0.30, 0.22, 0.105]),
                                   (160, [-0.26, 0.20, 0.40]), (170, [-0.28, 0.20, 0.105]), (264, [-0.28, 0.20, 0.105]), (270, [-0.24, 0.14, 0.22]),
                                   (276, ANKLE["R"]), (LAST, ANKLE["R"])),
                      "foot_turn_deg": k((0, 0.0), (22, 0.0), (36, -25.0), (170, -18.0), (264, -18.0), (276, 0.0), (LAST, 0.0))}},
    "sword": {
        "ik": "swing",
        "grip": None, "blade": None, "roll_deg": None,  # filled below
        "pitch_deg": k((0, IDLE_PITCH), (22, IDLE_PITCH), (135, 0.0), (248, 0.0), (286, IDLE_PITCH), (LAST, IDLE_PITCH)),  # the Idle grip sits at the reach edge: keep its pitch where the IK holds it
        "swivel_deg": k((0, IDLE_SWIVEL), (10, IDLE_SWIVEL), (140, CHOP_SWIVEL), (248, CHOP_SWIVEL), (290, IDLE_SWIVEL), (LAST, IDLE_SWIVEL)),
        # The sword IK holds the Idle grip at both ends and the frozen guard grip in the middle; the free phases (provoke, bash,
        # victory) are FK: the sword stays on its rest attachment to hand.R, so the blade follows the forearm as a real grip does
        # (a free blade direction with the hand on the hilt bent the wrist 90-150 deg in a01's first pass).
        "ik_weight": k((0, 1.0), (10, 1.0), (22, 0.0), (140, 0.0), (156, 1.0), (248, 1.0), (262, 0.0), (286, 0.0), (292, 1.0), (LAST, 1.0)),
    },
    "steps": [],
}
S = spec["steps"]
# Sword IK keys: the Idle grip at both ends (riding on the pelvis), the frozen guard under the leaning pelvis in the middle.
grip, blade, roll = [], [], []
for f in (0, 10, 22):
    grip.append([f, rel(f, IDLE_OFF)]); blade.append([f, IDLE_BLADE]); roll.append([f, IDLE_ROLL])
for f in GUARD_FRAMES:
    g, b, r = chop_sword_at(f, 0.85 if f == 135 else 1.0)
    grip.append([f, g]); blade.append([f, b]); roll.append([f, r])
for f in (286, 290, LAST):  # the pelvis is back at rest from 286
    grip.append([f, rel(f, IDLE_OFF)]); blade.append([f, IDLE_BLADE]); roll.append([f, IDLE_ROLL])
spec["sword"]["grip"], spec["sword"]["blade"], spec["sword"]["roll_deg"] = {"keys": grip}, {"keys": blade}, {"keys": roll}


def step(bone, kind, direction, keys, side=None):
    entry = {"bone": bone, "kind": kind, ("toward" if kind == "swing" else "about"): direction, "degrees": k(*keys)}
    if side:
        entry["side"] = side
    S.append(entry)


# Torso and head
# The frozen two_hand_chop pose was solved with the torso at rest: while it is in (140-262) the spine stays at rest, so the
# left hand of the pose meets the sword that the right-arm IK holds at the pose grip point; the crouch is pelvis height only.
step("spine_02", "swing", "back", [(0, 0.0), (70, 0.0), (96, 8.0), (112, -14.0), (135, 0.0), (262, 0.0), (272, 4.0), (282, 0.0), (LAST, 0.0)])
step("spine_01", "swing", "back", [(0, 0.0), (96, 0.0), (112, -8.0), (135, 0.0), (LAST, 0.0)])
step("spine_02", "twist", "up", [(0, 0.0), (10, 0.0), (34, 15.0), (56, 15.0), (70, 6.0), (96, 10.0), (112, -12.0), (135, 0.0), (LAST, 0.0)])
step("neck", "swing", "forward", [(0, 0.0), (112, 0.0), (124, 6.0), (135, 0.0), (172, 10.0), (200, 10.0), (215, 2.0), (LAST, 0.0)])
step("head", "swing", "forward", [(0, IDLE["head_fwd"]), (10, IDLE["head_fwd"]), (34, -6.0), (56, -6.0), (70, 0.0), (112, 8.0), (135, 1.4), (172, 12.0), (200, 10.0), (215, 2.0), (262, -4.0), (280, -4.0), (LAST, IDLE["head_fwd"])])
step("clavicle.R", "swing", "up", [(0, 0.0), (56, 0.0), (70, 8.0), (96, 8.0), (112, 0.0), (LAST, 0.0)])
step("clavicle.L", "swing", "up", [(0, 0.0), (10, 0.0), (34, 6.0), (56, 6.0), (70, 0.0), (248, 0.0), (262, 8.0), (280, 8.0), (LAST, 0.0)])
# Right arm FK (the sword rides on hand.R, so the blade follows the frozen grasp: it leaves the fist roughly opposite the forearm,
# which rules out a forward-down blade with the arm pointing at the target). Poses chosen from the FK table prep/arm-pose-table.json
# (joint-range-contract vocabulary): provoke raise (blade up-back, hand right of the head), bash windup (higher, wrist back),
# slash end (sweep down to the front-right), pre-guard (hand before the chest, blade up-forward), victory (arm out and up, blade up).
# Around the guard (140-156, 248-262) and the Idle ends the IK takes over; these keys park at the handover values.
R_KEYS = {  # frame: (flexion, abduction, axial, elbow, pronation, wrist palmar)
    0: (0, 0, 0, 0, 0, 0), 22: (0, 0, 0, 0, 0, 0), 34: (30, 90, -60, 90, 30, 0), 56: (30, 90, -60, 90, 30, 0), 70: (30, 90, -30, 90, 30, -40),
    96: (30, 90, -30, 90, 30, -40), 112: (30, 0, -60, 90, 60, -40), 124: (30, 0, -60, 90, 60, -40), 135: (60, 30, 0, 45, -30, 0), 140: (60, 30, 0, 45, -30, 0),
    262: (60, 30, 0, 45, -30, 0), 272: (0, 90, -30, 45, 60, 0), 280: (0, 90, -30, 45, 60, 0), 286: (0, 0, 0, 0, 0, 0), LAST: (0, 0, 0, 0, 0, 0)}
R_STEPS = [("upper_arm.R", "twist", {"about": "right"}), ("upper_arm.R", "twist", {"about": "back"}), ("upper_arm.R", "twist", {"about_bone": "upper_arm.R"}),
           ("lower_arm.R", "twist", {"about": "right"}), ("hand.R", "twist", {"about_bone": "lower_arm.R"}), ("hand.R", "swing", {"toward": "palmar"})]
for i, (bone, kind, axis) in enumerate(R_STEPS):
    S.append({"bone": bone, "kind": kind, **axis, "degrees": k(*((f, float(v[i])) for f, v in sorted(R_KEYS.items()))), "side": "R"})
# Left arm: provoke beckon (forward, elbow bent, palm up, fingers curl twice), bash counter-swing back, two-hand phases come from the frozen
# pose (weight ramps 140-156 and 248-262; the steps below stay flat at the handover values), victory fist pump overhead.
step("upper_arm.L", "twist", "forward", [(0, IDLE["ual_twist_fwd"]), (10, IDLE["ual_twist_fwd"]), (34, 10.0), (56, 10.0), (70, 0.0), (112, 0.0), (140, 0.0), (262, 0.0), (280, 0.0), (LAST, IDLE["ual_twist_fwd"])], "L")
step("upper_arm.L", "twist", "right", [(0, 0.0), (10, 0.0), (34, 65.0), (56, 65.0), (70, 20.0), (96, 30.0), (112, -25.0), (124, -25.0), (140, 0.0), (262, 0.0), (272, 120.0), (280, 120.0), (LAST, 0.0)], "L")
step("upper_arm.L", "swing", "out", [(0, 0.0), (10, 0.0), (34, 12.0), (56, 12.0), (70, 10.0), (140, 10.0), (262, 0.0), (272, 10.0), (280, 10.0), (LAST, 0.0)], "L")
step("lower_arm.L", "twist", "right", [(0, IDLE["lal_twist_right"]), (10, IDLE["lal_twist_right"]), (34, 95.0), (56, 95.0), (70, 40.0), (96, 50.0), (112, 20.0), (124, 20.0), (140, 25.0), (262, 25.0), (272, 70.0), (280, 70.0), (LAST, IDLE["lal_twist_right"])], "L")
step("hand.L", "swing", "dorsal", [(0, 0.0), (10, 0.0), (34, 20.0), (56, 20.0), (70, 0.0), (140, 0.0), (262, 0.0), (272, 10.0), (280, 10.0), (LAST, 0.0)], "L")
for i, (base1, base2) in enumerate(zip(IDLE["fingers_01"], IDLE["fingers_02"]), start=1):
    curl = [(0, base1), (10, base1), (34, 12.0), (38, 55.0), (42, 12.0), (46, 55.0), (50, 12.0), (56, 12.0), (70, base1), (140, base1), (262, base1), (268, 80.0), (280, 80.0), (LAST, base1)]
    step(f"finger{i}.L_01", "swing", "palmar", curl, "L")
    step(f"finger{i}.L_02", "swing", "palmar", [(0, base2), (10, base2), (34, 15.0), (38, 70.0), (42, 15.0), (46, 70.0), (50, 15.0), (56, 15.0), (70, base2), (140, base2), (262, base2), (268, 90.0), (280, 90.0), (LAST, base2)], "L")
step("thumb.L_01", "swing", "palmar", [(0, IDLE["thumb"]), (10, IDLE["thumb"]), (34, 5.0), (56, 5.0), (70, IDLE["thumb"]), (140, IDLE["thumb"]), (262, IDLE["thumb"]), (268, 35.0), (280, 35.0), (LAST, IDLE["thumb"])], "L")
# Legs in the air (magnum jump): hips flex and knees bend while the leg IK is off (152-170), back to the IK pose at landing.
for side in "LR":
    step(f"upper_leg.{side}", "swing", "forward", [(150, 0.0), (160, 55.0), (170, 0.0)], side)
    step(f"lower_leg.{side}", "swing", "back", [(150, 0.0), (160, 80.0), (170, 0.0)], side)
# Coat tails follow the lunge and the crouch a little (the lying corrective is not used: no lying state).
for side in "LR":
    step(f"coat.{side}", "swing", "back", [(0, 0.0), (96, 0.0), (112, 10.0), (135, 0.0), (160, -12.0), (172, 8.0), (200, 6.0), (215, 0.0), (LAST, 0.0)], side)

interaction = {
    "schema_version": 1, "clip": CLIP, "fps": 60, "frames": FRAMES, "loop": False, "ramp_frames": 12,
    "states": {"grasp.R": {"windows": [[0, LAST]], "establishment_frames": [0]}, "grasp.L": {"windows": [[156, 248]], "establishment_frames": [156]}},
    "stance": {"L": [[0, 10], [26, 88], [102, 150], [172, 256], [270, LAST]], "R": [[0, 22], [38, 150], [172, 264], [278, LAST]]},
    "events": [{"name": "bash_slash", "frame": 112}, {"name": "magnum_impact", "frame": 172}, {"name": "endure_start", "frame": 205}, {"name": "victory", "frame": 268}],
    "nominal_speed_m_s": 0.0,
    "note": "grasp.R covers the whole clip (contact_window_rules.grasp_R: Combo 全程); grasp.L covers the two-hand phases where the frozen "
            "two_hand_chop pose is at full weight (magnum break and endure). Stance windows: each foot while it is planted (steps out 10-26 L / "
            "22-38 R, lunge 88-102 L, jump 150-172 both, steps back 256-270 L / 264-278 R); the jump has no stance. Events time the separate "
            "effects layer and are not socket events (the sword stays in hand.R).",
}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "clip.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
(OUT / "interaction.json").write_text(json.dumps(interaction, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("steps", len(S), "written", OUT)
