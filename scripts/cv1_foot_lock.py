"""Stance-foot lock for character V1 transitions (pure Python; mirrored by tools/runtime-qa/three/src/cv1-foot-lock.js).

User decision A1 (authorization entry 25): cross-fading two in-place clips slides a planted foot, so while a transition
fades, a foot that every leg-driving layer (lower-body weight > 0) has inside its stance window is pinned where it stood
when the lock began and carried back by the blended nominal speed (the clips are in place: the ground moves under the
character). A two-bone leg solve (thigh, shin) moves the ankle; the foot keeps its blended world rotation.
- The lock starts at the first instant at which two or more leg layers are active and all of them have the foot in
  stance (never while an earlier release or settle of that foot is still running). It holds while any active leg layer
  still has the foot in stance, through the rest of the fade and after it, so the foot lets go only when it is in the
  air in every layer.
- Then the offset to the blended foot is released over RELEASE_S (smoothstep) while the foot swings.
- When some layer still has the foot in stance HORIZON_S after the last fade (a layer that never lifts it, such as
  Idle), the foot settles at the end of the last fade instead: the offset goes to zero over SETTLE_S while the foot rises by
  min(SETTLE_LIFT_M, SETTLE_LIFT_SHARE * |horizontal offset|) * sin(pi u), a step whose lift the feet gate can measure.
The schedule depends only on the events and the clips' stance windows; the targets use the blended (lock-free) foot at
the schedule's own instants. Evaluation therefore stays a function of time: playing, pausing and seeking agree.
Vectors are 3-tuples in one right-handed world frame; quaternions are (w, x, y, z).
"""
import math

import cv1_interaction as interaction
import cv1_transition as tr

SIDES = ("L", "R")
RELEASE_S, SETTLE_S, SETTLE_LIFT_M, SETTLE_LIFT_SHARE, HORIZON_S = 0.12, 0.3, 0.04, 0.5, 2.0
POLE_WEIGHT = 0.2
ACTIVE_WEIGHT = 1e-12


# ---- schedule ----
def _always(clip, side):
    return clip["loop"] and interaction.is_full(clip["stance"][side], clip["frames"])


def in_stance(clip, side, frame):
    """The foot is inside a stance window of the clip (a window covering a whole loop has no seam gap)."""
    return _always(clip, side) or interaction.covered(clip["stance"][side], frame, clip["loop"])


def _crossings(scenario, clips, layer, side, t_end):
    """Wall times at which the layer's frame meets an edge of the side's stance windows."""
    start = tr.layers(scenario)[layer]
    clip = clips[start["clip"]]
    if _always(clip, side):
        return []
    rate, out = clip["fps"] * start["speed"], []
    for window in clip["stance"][side]:
        for edge in window:
            if clip["loop"]:
                k = math.ceil((start["entry_frame"] - edge) / clip["frames"])
                while True:
                    t = start["t"] + (edge + k * clip["frames"] - start["entry_frame"]) / rate
                    if t > t_end:
                        break
                    if t >= start["t"]:
                        out.append(t)
                    k += 1
            elif edge <= clip["frames"] - 1:
                t = start["t"] + (edge - start["entry_frame"]) / rate
                if start["t"] <= t <= t_end:
                    out.append(t)
    return out


def _state(scenario, clips, side, t):
    """(every active leg layer has the foot in stance, two or more leg layers are active, some active leg layer has the
    foot in stance) at time t."""
    starts = tr.layers(scenario)
    lookup = {short: {"frames": c["frames"], "loop": c["loop"], "fps": c["fps"]} for short, c in clips.items()}
    active = [layer for layer, w in tr.weights(scenario, t)["lower"].items() if w > ACTIVE_WEIGHT]
    planted = [in_stance(clips[starts[layer]["clip"]], side, tr.layer_frame(scenario, lookup, layer, t)) for layer in active]
    return bool(active) and all(planted), len(active) >= 2, any(planted)


def horizon(scenario):
    events = scenario["events"]
    return max([events[0]["t"]] + [e["t"] + e["blend_s"] for e in events[1:]]) + HORIZON_S


def schedule(scenario, clips):
    """Per side, the locks: {"lock": [t0, t1], then "release": [t1, t1 + RELEASE_S] or "settle": [t1, t1 + SETTLE_S]}.
    clips: {short: {"frames", "loop", "fps", "stance": {"L": windows, "R": windows}}}."""
    events, t_end = scenario["events"], horizon(scenario)
    base = {e["t"] for e in events} | {e["t"] + e["blend_s"] for e in events[1:]} | {t_end}
    out = {}
    for side in SIDES:
        points = set(base)
        for layer in tr.layers(scenario):
            points.update(_crossings(scenario, clips, layer, side, t_end))
        points = sorted(p for p in points if events[0]["t"] <= p <= t_end)
        segments = []
        for a, b in zip(points, points[1:]):
            if b - a > 1e-12:
                segments.append((a, b) + _state(scenario, clips, side, 0.5 * (a + b)))
        locks, free_from, i = [], -math.inf, 0
        while i < len(segments):
            a, b, all_planted, fading, _ = segments[i]
            if not (all_planted and fading and b > free_from):
                i += 1
                continue
            t_lock, j = max(a, free_from), i
            while j + 1 < len(segments) and segments[j + 1][4]:  # held while some active layer has the foot planted
                j += 1
            if j == len(segments) - 1:  # planted past the horizon: settle at the end of the last fade
                t_off = max(max(s[1] for s in segments[i:j + 1] if s[3]), t_lock)
                locks.append({"lock": [t_lock, t_off], "settle": [t_off, t_off + SETTLE_S]})
                free_from = t_off + SETTLE_S
            else:
                t_off = segments[j][1]
                locks.append({"lock": [t_lock, t_off], "release": [t_off, t_off + RELEASE_S]})
                free_from = t_off + RELEASE_S
            i = j + 1
        out[side] = locks
    return out


def mode_at(locks, t):
    """('lock' | 'release' | 'settle', entry) for the interval holding t (half-open), or (None, None)."""
    for entry in locks:
        if entry["lock"][0] <= t < entry["lock"][1]:
            return "lock", entry
        kind = "release" if "release" in entry else "settle"
        if entry[kind][0] <= t < entry[kind][1]:
            return kind, entry
    return None, None


def end_time(locks):
    """When the last lock of a side has fully let go (or None)."""
    return max((e["release" if "release" in e else "settle"][1] for e in locks), default=None)


def needed_times(locks, t):
    """Instants whose lock-free foot the target at t needs (besides t itself)."""
    kind, entry = mode_at(locks, t)
    if kind is None or entry is None:
        return []
    return [entry["lock"][0]] if kind == "lock" else [entry["lock"][0], entry[kind][0]]


# ---- drift (in-place clips: the blended nominal speed moves the ground) ----
def speed_at(scenario, clips, t):
    starts = tr.layers(scenario)
    return sum(w * clips[starts[layer]["clip"]]["nominal_speed_m_s"] * starts[layer]["speed"] for layer, w in tr.weights(scenario, t)["lower"].items())


def drift(scenario, clips, t0, t1):
    """Distance travelled from t0 to t1: the weights are linear between event times and fade ends, so the trapezoid on
    those breakpoints is exact."""
    if t1 <= t0:
        return 0.0
    events = scenario["events"]
    points = sorted({t0, t1} | {e["t"] for e in events if t0 < e["t"] < t1} | {e["t"] + e["blend_s"] for e in events[1:] if t0 < e["t"] + e["blend_s"] < t1})
    return sum(0.5 * (speed_at(scenario, clips, a) + speed_at(scenario, clips, b)) * (b - a) for a, b in zip(points, points[1:]))


# ---- vector and quaternion helpers ----
def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def angle(a, b):
    return math.atan2(norm(cross(a, b)), dot(a, b))


def axis_angle(axis, theta):
    n = norm(axis)
    s = math.sin(0.5 * theta) / n
    return (math.cos(0.5 * theta), axis[0] * s, axis[1] * s, axis[2] * s)


def qmul(a, b):
    return (a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
            a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0])


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def rotate(q, v):
    w = qmul(qmul(q, (0.0, v[0], v[1], v[2])), qconj(q))
    return (w[1], w[2], w[3])


def smooth(u):
    return u * u * (3.0 - 2.0 * u)


# ---- targets and the leg solve ----
def sole_target(scenario, clips, locks, side, t, fk_sole, forward, up):
    """Where the sole point should be at t, or None when the foot is free. fk_sole(side, time) is the lock-free sole point."""
    kind, entry = mode_at(locks, t)
    if kind is None or entry is None:
        return None
    t_lock = entry["lock"][0]

    def locked(at):
        return sub(fk_sole(side, t_lock), scale(forward, drift(scenario, clips, t_lock, at)))

    if kind == "lock":
        return locked(t)
    r0, r1 = entry[kind]
    offset = sub(locked(r0), fk_sole(side, r0))
    u = (t - r0) / (r1 - r0)
    target = add(fk_sole(side, t), scale(offset, 1.0 - smooth(u)))
    if kind == "settle":
        horizontal = sub(offset, scale(up, dot(offset, up)))
        target = add(target, scale(up, min(SETTLE_LIFT_M, SETTLE_LIFT_SHARE * norm(horizontal)) * math.sin(math.pi * u)))
    return target


def two_bone(hip, knee, ankle, ankle_target, pole, fallback_normal):
    """(knee_turn, hip_turn) world quaternions: the shin turns about the knee hinge by the angle (nearest zero) that gives
    the hip-ankle distance of the target (clamped just short of a straight leg), then the leg turns about the hip onto
    it. New world rotations: thigh hip_turn * thigh, shin hip_turn * knee_turn * shin; the foot keeps its own.
    The hinge is the leg-plane normal u x w plus POLE_WEIGHT * l1 * l2 times the unit normal of the plane through the
    hip-ankle line and `pole` (the toe direction): a bent knee keeps its own plane, a nearly straight one (Idle stands
    at about 178 deg, its plane pointing sideways) bends towards the toes. No threshold, so the hinge moves smoothly."""
    l1, l2 = norm(sub(knee, hip)), norm(sub(ankle, knee))
    u, w = sub(hip, knee), sub(ankle, knee)
    reach = norm(sub(ankle_target, hip))
    reach = min(max(reach, abs(l1 - l2) * (1.0 + 1e-9)), (l1 + l2) * (1.0 - 1e-9))
    hinge = cross(u, w)
    toward = cross(sub(ankle, hip), pole)
    if norm(toward) > 1e-12:
        hinge = add(hinge, scale(toward, POLE_WEIGHT * l1 * l2 / norm(toward)))
    if norm(hinge) < 1e-12 * l1 * l2:
        hinge = fallback_normal
    n = scale(hinge, 1.0 / norm(hinge))
    w_par = scale(n, dot(w, n))
    w_perp = sub(w, w_par)
    across = cross(n, w_perp)
    # u . w(phi) = c0 + A cos(phi) + B sin(phi) must equal (|u|^2 + |w|^2 - reach^2) / 2.
    c0, a_cos, b_sin = dot(u, w_par), dot(u, w_perp), dot(u, across)
    radius = math.hypot(a_cos, b_sin)
    if radius < 1e-15:
        phi = 0.0
    else:
        x = max(-1.0, min(1.0, ((dot(u, u) + dot(w, w) - reach * reach) / 2.0 - c0) / radius))
        base, spread = math.atan2(b_sin, a_cos), math.acos(x)
        phi = min((_wrap(base - spread), _wrap(base + spread)), key=abs)
    knee_turn = axis_angle(n, phi)
    a = sub(add(knee, rotate(knee_turn, w)), hip)
    b = sub(ankle_target, hip)
    axis = cross(a, b)
    hip_turn = (1.0, 0.0, 0.0, 0.0) if norm(axis) < 1e-12 * norm(a) * norm(b) else axis_angle(axis, angle(a, b))
    return knee_turn, hip_turn


def _wrap(phi):
    """phi in (-pi, pi]."""
    return phi - 2.0 * math.pi * math.ceil((phi - math.pi) / (2.0 * math.pi))
