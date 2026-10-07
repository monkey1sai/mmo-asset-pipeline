"""Transition timeline for the character V1 QA scene (pure Python; mirrored by tools/runtime-qa/three/src/cv1-transition.js).

A scenario is a list of events on a wall clock in seconds. The first event starts one layer at full weight. Each later
event fades one layer (new, or already present) to full weight over blend_s seconds; every other layer keeps the share
it had at the event time, scaled by (1 - a) with a = (t - t_event) / blend_s clamped to [0, 1]. The weights therefore
stay continuous through interrupted fades (three.js crossFadeTo restarts them at 0 / 1) and depend only on the time and
the event list: the evaluator carries no history. An event masked to "upper" acts on the upper-body bones only (spine_01
and every bone below it in the hierarchy); the lower body keeps its weights. A layer plays its clip from entry_frame at
`speed` (clip frames per wall second = fps * speed), wrapping a loop clip and holding the last frame of a non-loop clip.

Pose blending follows three.js 0.186 PropertyMixer: the first contributing layer is copied, each later one is mixed in
with weight / cumulative weight (Quaternion.slerpFlat for rotations, linear for the rest), and a cumulative weight under
1 is mixed with the original (rest) value by 1 - weight. Layers contribute in event order; zero weights are skipped.
"""
import math

GROUPS = ("upper", "lower")
UPPER_ROOT = "spine_01"
# Interaction states follow the bone group they belong to (the hands are upper body; lying is the whole body's support).
STATE_GROUP = {"grasp.R": "upper", "grasp.L": "upper"}


class TransitionError(ValueError):
    pass


def bone_group(name, parents):
    """'upper' for spine_01 and its descendants, 'lower' for every other bone."""
    node, seen = name, set()
    while node is not None:
        if node == UPPER_ROOT:
            return "upper"
        if node in seen:
            raise TransitionError(f"PARENT_CYCLE {name}")
        seen.add(node)
        node = parents.get(node)
    return "lower"


def validate(scenario, clips):
    """clips: {clip name: {"frames": n, "loop": bool, "fps": 60}}. Returns the scenario."""
    events = scenario.get("events", [])
    problems = []
    if not events:
        problems.append("NO_EVENTS")
    times = [e.get("t") for e in events]
    if any(not isinstance(t, (int, float)) for t in times) or times != sorted(times):
        problems.append("EVENT_TIMES_NOT_ASCENDING")
    layers = {}
    for i, e in enumerate(events):
        if e.get("mask") not in (None, "upper"):
            problems.append(f"MASK:{i}")
        if i == 0 and (e.get("blend_s") or e.get("mask")):
            problems.append("FIRST_EVENT_IS_A_CUT_OF_THE_WHOLE_BODY")
        if i > 0 and not (isinstance(e.get("blend_s"), (int, float)) and e["blend_s"] > 0):
            problems.append(f"BLEND:{i}")
        if e["layer"] in layers:
            if "clip" in e and e["clip"] != layers[e["layer"]]["clip"]:
                problems.append(f"LAYER_CLIP_CHANGED:{i}")
        else:
            if e.get("clip") not in clips:
                problems.append(f"UNKNOWN_CLIP:{i}")
            elif not isinstance(e.get("speed"), (int, float)) or e["speed"] <= 0 or not isinstance(e.get("entry_frame"), (int, float)):
                problems.append(f"LAYER_PLAYBACK:{i}")
            layers[e["layer"]] = e
    if problems:
        raise TransitionError(", ".join(problems))
    return scenario


def layers(scenario):
    """Layer id -> the event that started it (clip, entry_frame, speed, start time), in event order."""
    out = {}
    for e in scenario["events"]:
        out.setdefault(e["layer"], e)
    return out


def layer_frame(scenario, clips, layer, t):
    """Clip frame of a layer at wall time t (None before the layer starts)."""
    start = layers(scenario)[layer]
    if t < start["t"]:
        return None
    clip = clips[start["clip"]]
    frame = start["entry_frame"] + (t - start["t"]) * clip["fps"] * start["speed"]
    if clip["loop"]:
        return frame % clip["frames"]
    return min(max(frame, 0.0), float(clip["frames"] - 1))


def _weights(events, k, t):
    if k == 0:
        return {g: {events[0]["layer"]: 1.0} for g in GROUPS}
    event = events[k]
    if t < event["t"]:
        return _weights(events, k - 1, t)
    a = min(1.0, (t - event["t"]) / event["blend_s"])
    frozen = _weights(events, k - 1, event["t"])
    now = _weights(events, k - 1, t)
    out = {}
    for g in GROUPS:
        if event.get("mask") == "upper" and g == "lower":
            out[g] = now[g]
            continue
        w = {layer: value * (1.0 - a) for layer, value in frozen[g].items() if layer != event["layer"]}
        w[event["layer"]] = frozen[g].get(event["layer"], 0.0) * (1.0 - a) + a
        out[g] = w
    return out


def weights(scenario, t):
    """{group: {layer: weight}} at wall time t; each group's weights sum to 1."""
    return _weights(scenario["events"], len(scenario["events"]) - 1, t)


def blend_states(group_weights, layer_states):
    """Weighted interaction states: layer_states {layer: {key: value}}; a key uses its bone group's weights."""
    keys = sorted({k for states in layer_states.values() for k in states})
    out = {}
    for key in keys:
        w = group_weights[STATE_GROUP.get(key, "lower")]
        # A convex mix of values in [0, 1]; the clamp only removes the rounding of weights that sum to 1 + ulp.
        out[key] = min(1.0, max(0.0, sum(w.get(layer, 0.0) * states.get(key, 0.0) for layer, states in layer_states.items())))
    return out


def slerp_flat(q0, q1, t):
    """three.js 0.186 Quaternion.slerpFlat on (x, y, z, w) tuples."""
    x0, y0, z0, w0 = q0
    x1, y1, z1, w1 = q1
    if (w0, x0, y0, z0) != (w1, x1, y1, z1):
        dot = x0 * x1 + y0 * y1 + z0 * z1 + w0 * w1
        if dot < 0:
            x1, y1, z1, w1, dot = -x1, -y1, -z1, -w1, -dot
        s = 1 - t
        if dot < 0.9995:
            theta = math.acos(dot)
            sin = math.sin(theta)
            s, t = math.sin(s * theta) / sin, math.sin(t * theta) / sin
            x0, y0, z0, w0 = x0 * s + x1 * t, y0 * s + y1 * t, z0 * s + z1 * t, w0 * s + w1 * t
        else:
            x0, y0, z0, w0 = x0 * s + x1 * t, y0 * s + y1 * t, z0 * s + z1 * t, w0 * s + w1 * t
            f = 1 / math.sqrt(x0 * x0 + y0 * y0 + z0 * z0 + w0 * w0)
            x0, y0, z0, w0 = x0 * f, y0 * f, z0 * f, w0 * f
    return (x0, y0, z0, w0)


def lerp(v0, v1, t):
    return tuple(a * (1 - t) + b * t for a, b in zip(v0, v1))


def mix(contributions, original, kind):
    """three.js PropertyMixer: contributions [(value, weight)] in action order; kind 'quaternion' or 'vector'."""
    blend = slerp_flat if kind == "quaternion" else lerp
    buffer, cumulative = None, 0.0
    for value, weight in contributions:
        if weight <= 0:
            continue
        if cumulative == 0:
            buffer, cumulative = tuple(value), weight
        else:
            cumulative += weight
            buffer = blend(buffer, tuple(value), weight / cumulative)
    if buffer is None:
        return tuple(original)
    if cumulative < 1:
        buffer = blend(buffer, tuple(original), 1 - cumulative)
    return buffer


def sample_times(t_from, t_to, fps):
    """Wall times k / fps inside [t_from, t_to] (both ends included when on the grid)."""
    first, last = math.ceil(round(t_from * fps, 9)), math.floor(round(t_to * fps, 9))
    return [k / fps for k in range(first, last + 1)]
