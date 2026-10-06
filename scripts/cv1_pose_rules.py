"""Character V1 corrective rule evaluation: final joint pose and interaction state -> morph weights.

Pure math, no DCC or engine imports. The JavaScript twin is
tools/runtime-qa/three/src/cv1-pose-rules.js; tests/test_cv1_pose_rules.py checks both agree.
Quaternions are (w, x, y, z), rest-relative local rotations of the named bone.
"""
from __future__ import annotations

import math

OWNERS = {"runtime_evaluator", "baked_clip"}


class RuleError(ValueError):
    pass


def _unit(q):
    n = math.sqrt(sum(float(c) * float(c) for c in q))
    if len(q) != 4 or not math.isfinite(n) or n < 1e-12:
        raise RuleError("INVALID_QUATERNION")
    return tuple(float(c) / n for c in q)


def quat_angle(a, b) -> float:
    """Shortest rotation angle in radians between two orientations."""
    a, b = _unit(a), _unit(b)
    return 2.0 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, b)))))


def rotation_difference_progress(q_rel, q_target) -> float:
    """0 at rest, 1 at the target pose; off-axis rotations of equal size score lower."""
    span = quat_angle((1.0, 0.0, 0.0, 0.0), q_target)
    if span < 1e-9:
        raise RuleError("DEGENERATE_TARGET")
    return min(1.0, max(0.0, 1.0 - quat_angle(q_rel, q_target) / span))


def hat(p: float, prev: float, at: float, nxt: float | None) -> float:
    """In-between weight: 0 at prev, 1 at `at`, 0 at nxt; holds 1 past `at` when nxt is None."""
    if not prev < at or (nxt is not None and not at < nxt):
        raise RuleError("INVALID_HAT")
    if p <= prev:
        return 0.0
    if p <= at:
        return (p - prev) / (at - prev)
    if nxt is None:
        return 1.0
    return max(0.0, (nxt - p) / (nxt - at))


def _mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def _share(q, t):
    """Slerp from identity toward q by t along the shortest path."""
    w, x, y, z = _unit(q)
    if w < 0:
        w, x, y, z = -w, -x, -y, -z
    half = math.acos(min(1.0, w))
    s = math.sin(half)
    if s < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    k = math.sin(t * half) / s
    return (math.cos(t * half), x * k, y * k, z * k)


def swing_only(q):
    """Remove the twist about the bone's own axis (local +Y) from a rest-relative local rotation."""
    w, x, y, z = _unit(q)
    n = math.sqrt(w * w + y * y)
    if n < 1e-12:
        return (w, x, y, z)
    return _mul((w, x, y, z), _conj((w / n, 0.0, y / n, 0.0)))


def twist_about(q, axis):
    """The twist part of q about a unit axis (swing-twist decomposition, q = swing * twist)."""
    w, x, y, z = _unit(q)
    d = x * axis[0] + y * axis[1] + z * axis[2]
    n = math.sqrt(w * w + d * d)
    if n < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    return (w / n, d * axis[0] / n, d * axis[1] / n, d * axis[2] / n)


def _rotate(q, v):
    return _mul(_mul(q, (0.0, v[0], v[1], v[2])), _conj(q))[1:]


def helper_rotations(rules: dict, pose_rel: dict, rest_local: dict, parents: dict) -> dict:
    """Rest-relative local rotations of the helper bones.

    rest_local: bone -> rest rotation relative to its parent (wxyz); parents: bone -> parent name.
    Each source's rotation is moved into the shared parent frame, scaled by its share and applied to the helper.
    twist_only keeps just the source's turn about the helper's own axis (its local +Y seen from the parent),
    as a forearm twist bone follows the hand's roll and ignores its bend.
    """
    out = {}
    for helper in rules.get("helpers", []):
        bone = helper["bone"]
        if bone not in rest_local:
            raise RuleError("MISSING_BONE:" + bone)
        total = (1.0, 0.0, 0.0, 0.0)
        for follow in helper["follow"]:
            source = follow["source"]
            if source not in pose_rel or source not in rest_local:
                raise RuleError("MISSING_BONE:" + source)
            if parents.get(source) != parents.get(bone):
                raise RuleError("HELPER_NOT_SIBLING:" + bone)
            rest = _unit(rest_local[source])
            local = swing_only(pose_rel[source]) if follow.get("swing_only") else _unit(pose_rel[source])
            in_parent = _mul(_mul(rest, local), _conj(rest))
            if follow.get("twist_only"):
                in_parent = twist_about(in_parent, _rotate(_unit(rest_local[bone]), (0.0, 1.0, 0.0)))
            total = _mul(_share(in_parent, float(follow["share"])), total)
        rest = _unit(rest_local[bone])
        out[bone] = _unit(_mul(_mul(_conj(rest), total), rest))
    return out


def helper_conflicts(rules: dict, animated_bones) -> list:
    """Helper bones that an animation clip also keys."""
    validate_rules(rules)
    return sorted({h["bone"] for h in rules.get("helpers", [])} & set(animated_bones))


def validate_rules(rules: dict) -> None:
    if not isinstance(rules, dict) or rules.get("schema_version") != 1:
        raise RuleError("RULES_SCHEMA")
    drivers, channels = rules.get("drivers"), rules.get("channels")
    if not isinstance(drivers, dict) or not isinstance(channels, list) or not channels:
        raise RuleError("RULES_SCHEMA")
    for driver in drivers.values():
        if driver.get("type") == "rotation_difference":
            if not isinstance(driver.get("bone"), str):
                raise RuleError("RULES_SCHEMA")
            _unit(driver.get("target_quaternion_wxyz", ()))
        elif driver.get("type") == "state":
            if not isinstance(driver.get("key"), str):
                raise RuleError("RULES_SCHEMA")
        elif driver.get("type") == "product":
            # Product of other, non-product drivers: active only when all of them are.
            factors = driver.get("of")
            if not isinstance(factors, list) or len(factors) < 2 or any(drivers.get(name, {}).get("type") not in ("rotation_difference", "state") for name in factors):
                raise RuleError("INVALID_PRODUCT_DRIVER")
        else:
            raise RuleError("UNKNOWN_DRIVER_TYPE")
    helpers = rules.get("helpers", [])
    if not isinstance(helpers, list):
        raise RuleError("RULES_SCHEMA")
    helper_bones = set()
    for helper in helpers:
        follow = helper.get("follow") if isinstance(helper, dict) else None
        if not isinstance(helper.get("bone"), str) or helper["bone"] in helper_bones or helper.get("owner") != "runtime_evaluator" or not isinstance(follow, list) or not follow:
            raise RuleError("INVALID_HELPER")
        if any(not isinstance(f, dict) or not isinstance(f.get("source"), str) or not 0.0 <= float(f.get("share", -1)) <= 1.0
               or not isinstance(f.get("swing_only", False), bool) or not isinstance(f.get("twist_only", False), bool)
               or (f.get("swing_only") and f.get("twist_only")) for f in follow):
            raise RuleError("INVALID_HELPER")
        helper_bones.add(helper["bone"])
    if helper_bones & {f["source"] for h in helpers for f in h["follow"]}:
        raise RuleError("HELPER_CHAIN")
    seen = set()
    for channel in channels:
        key = (channel.get("mesh"), channel.get("morph"))
        if not all(isinstance(v, str) and v for v in key) or key in seen:
            raise RuleError("DUPLICATE_OR_INVALID_CHANNEL")
        seen.add(key)
        if channel.get("owner") not in OWNERS or channel.get("driver") not in drivers:
            raise RuleError("CHANNEL_OWNER_OR_DRIVER")
        curve = channel.get("curve", {})
        if curve.get("type") == "hat":
            hat(0.0, curve["prev"], curve["at"], curve.get("next"))
        elif curve.get("type") != "linear":
            raise RuleError("UNKNOWN_CURVE_TYPE")


def driver_values(rules: dict, pose_rel: dict, state: dict) -> dict:
    out = {}
    for name, driver in rules["drivers"].items():
        if driver["type"] == "rotation_difference":
            if driver["bone"] not in pose_rel:
                raise RuleError("MISSING_BONE:" + driver["bone"])
            out[name] = rotation_difference_progress(pose_rel[driver["bone"]], driver["target_quaternion_wxyz"])
        elif driver["type"] == "state":
            if driver["key"] not in state:
                raise RuleError("MISSING_STATE:" + driver["key"])
            value = float(state[driver["key"]])
            if not 0.0 <= value <= 1.0:
                raise RuleError("STATE_OUT_OF_RANGE:" + driver["key"])
            out[name] = value
    for name, driver in rules["drivers"].items():
        if driver["type"] == "product":
            value = 1.0
            for factor in driver["of"]:
                value *= out[factor]
            out[name] = value
    return out


def evaluate(rules: dict, pose_rel: dict, state: dict) -> dict:
    """Return {(mesh, morph): weight} for channels owned by the runtime evaluator."""
    validate_rules(rules)
    values = driver_values(rules, pose_rel, state)
    weights = {}
    for channel in rules["channels"]:
        if channel["owner"] != "runtime_evaluator":
            continue
        p, curve = values[channel["driver"]], channel["curve"]
        weights[(channel["mesh"], channel["morph"])] = p if curve["type"] == "linear" else hat(p, curve["prev"], curve["at"], curve.get("next"))
    return weights


def ownership_conflicts(rules: dict, animated_channels) -> list:
    """Channels written by an animation clip while the rules assign them to the runtime evaluator."""
    validate_rules(rules)
    owned = {(c["mesh"], c["morph"]) for c in rules["channels"] if c["owner"] == "runtime_evaluator"}
    return sorted(owned & {tuple(c) for c in animated_channels})
