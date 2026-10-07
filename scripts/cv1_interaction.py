"""Interaction configuration of a character V1 clip: contact windows, events and interaction states (pure Python).

Each clip declares its windows in an interaction config, and the config's SHA is registered before the clip is first
measured (request support_envelope.contact_measurement.window_lock). Registry entries are append-only; changing a
config after a failed measurement is an implementation fix that keeps the earlier failure on record.

Frames: a clip has `frames` distinct frames 0..frames-1 at `fps`, key f at time f/fps. A loop clip's seam joins frame
frames-1 to frame 0. Windows are [start, end] frame pairs, inclusive; in a loop clip start > end wraps across the seam.

Interaction state (runtime_contract.interaction_state): 1 inside a window, 0 outside, with fixed 12-frame linear
transitions. Coordinator definitions, recorded as assumptions:
- The transition lies outside the window: the state rises over the 12 frames before the window start and falls over
  the 12 frames after its end, so it is exactly 1 at every sample inside the window, where the grasp gate applies.
- A window covering a whole loop clip has no boundary; the state stays 1 across the seam. A non-loop clip clips the
  transition at its ends.
The minimum coverage of support_envelope.contact_window_rules is checked before registration, so a window cannot be
shortened to pass.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

COMBO = "AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory"
FULL_GRASP_R = {"AN_RO_Idle_Sword", "AN_RO_Walk_Sword", "AN_RO_Run_Sword", "AN_RO_Cast_OpenPalm", COMBO}
FULL_STANCE = {"AN_RO_Idle_Sword", "AN_RO_Cast_OpenPalm"}
STANCE_SHARE = {"AN_RO_Walk_Sword": 0.40, "AN_RO_Run_Sword": 0.20}
BED_CLIPS = {"AN_RO_LieDown", "AN_RO_Sleep_Loop", "AN_RO_GetUp"}
BED_TOP_Z, BED_SIZE = 0.45, [2.0, 0.9]


class InteractionError(ValueError):
    pass


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def covered(windows, t, loop):
    """Whether time t (in frames) lies inside any window."""
    for start, end in windows:
        if start <= end:
            if start <= t <= end:
                return True
        elif loop and (t >= start or t <= end):
            return True
    return False


def windows_overlap(first, second, loop):
    """Whether two windows share frames beyond the one frame where one ends and the other starts. Windows that wrap
    across a loop seam are compared by their end frames only."""
    (a, b), (s, e) = first, second
    if a <= b and s <= e:
        lo, hi = max(a, s), min(b, e)
        return lo < hi or (lo == hi and b != s and a != e)
    return any(covered([second], t, loop) for t in first) or any(covered([first], t, loop) for t in second)


def share(percent, frames):
    """percent x frames as a frame number, rounded to 1e-9 so that e.g. 70% of 90 frames is frame 63 (0.7 * 90 = 62.999...)."""
    return round(percent * frames, 9)


def coverage(windows, frames, loop):
    """Share of the clip's whole frames covered by the windows."""
    return sum(1 for f in range(frames) if covered(windows, f, loop)) / frames


def is_full(windows, frames):
    return any(start <= 0 and end >= frames - 1 for start, end in windows if start <= end)


def state_value(config, key, t):
    """Interaction state at time t (frames): 1 inside a window, 0 outside, linear over `ramp_frames` outside the window."""
    spec = config["states"].get(key)
    if spec is None:
        raise InteractionError("UNDECLARED_STATE:" + key)
    frames, loop, ramp = config["frames"], config["loop"], float(config["ramp_frames"])
    windows = spec["windows"]
    if not windows:
        return 0.0
    if loop and is_full(windows, frames):
        return 1.0
    if covered(windows, t, loop):
        return 1.0
    best = 0.0
    for start, end in windows:
        for distance in ((start - t), (t - end)):
            candidates = [distance]
            if loop:
                candidates += [distance + frames, distance - frames]
            for d in candidates:
                if 0 < d < ramp:
                    best = max(best, 1.0 - d / ramp)
    return best


def states_at(config, t):
    return {key: state_value(config, key, t) for key in sorted(config["states"])}


def boundaries(config):
    """Frames around which sampling is refined: window ends, establishment frames, events and stance changes."""
    marks = set()
    for spec in config["states"].values():
        for start, end in spec["windows"]:
            marks |= {start, end}
        marks |= set(spec.get("establishment_frames", []))
    for windows in config.get("stance", {}).values():
        for start, end in windows:
            marks |= {start, end}
    for start, end in config.get("bed_support", {}).get("windows", []):
        marks |= {start, end}
    for start, end in config.get("seated_on_bed", {}).get("windows", []):
        marks |= {start, end}
    marks |= {event["frame"] for event in config.get("events", [])}
    return sorted(m for m in marks if 0 <= m <= config["frames"] - 1)


def sample_times(config):
    """Whole and half frames, plus quarter frames within one frame of every boundary (request contact_measurement.sampling)."""
    frames, loop = config["frames"], config["loop"]
    last = frames - 0.5 if loop else frames - 1
    times = {f / 2 for f in range(int(last * 2) + 1)}
    for mark in boundaries(config):
        times |= {mark + q / 4 for q in range(-4, 5)}
    return sorted(t for t in times if 0 <= t <= last)


def validate(config):
    """Schema and the request's minimum window coverage; returns the config."""
    problems = []
    for key in ("schema_version", "clip", "fps", "frames", "loop", "ramp_frames", "states", "stance", "events", "nominal_speed_m_s"):
        if key not in config:
            problems.append("MISSING:" + key)
    if problems:
        raise InteractionError(", ".join(problems))
    clip, frames, loop = config["clip"], config["frames"], config["loop"]
    if config["schema_version"] != 1 or config["fps"] != 60 or config["ramp_frames"] != 12 or not isinstance(frames, int) or frames < 2:
        raise InteractionError("SCHEMA")

    def check_windows(name, windows):
        for pair in windows:
            if len(pair) != 2 or not all(isinstance(v, (int, float)) for v in pair) or not (0 <= pair[0] <= frames - 1 and 0 <= pair[1] <= frames - 1):
                problems.append(f"WINDOW_RANGE:{name}")
            elif pair[0] > pair[1] and not loop:
                problems.append(f"WRAP_IN_NON_LOOP:{name}")

    for key, spec in config["states"].items():
        check_windows(key, spec["windows"])
    for side, windows in config["stance"].items():
        check_windows("stance." + side, windows)
    events = {event["name"]: event["frame"] for event in config["events"]}
    for event in config["events"]:
        if not (isinstance(event.get("frame"), (int, float)) and 0 <= event["frame"] <= frames - 1):
            problems.append("EVENT_RANGE:" + str(event.get("name")))
    if clip == "AN_RO_Cast_OpenPalm" and [event["name"] for event in config["events"]] != ["release"]:
        problems.append("CAST_ONE_RELEASE_EVENT")
    grasp = config["states"].get("grasp.R", {"windows": []})["windows"]
    if clip in FULL_GRASP_R and not is_full(grasp, frames):
        problems.append("GRASP_R_MUST_COVER_CLIP")
    if clip == "AN_RO_LieDown":
        put = events.get("put_sword_down")
        if put is None or put < share(0.25, frames) or grasp != [[0, put]]:
            problems.append("LIEDOWN_GRASP_UNTIL_PUT_DOWN_AT_OR_AFTER_25PCT")
    if clip == "AN_RO_GetUp":
        pick = events.get("pick_sword_up")
        if pick is None or pick > share(0.75, frames) or grasp != [[pick, frames - 1]]:
            problems.append("GETUP_GRASP_FROM_PICK_UP_AT_OR_BEFORE_75PCT")
    for side in ("L", "R"):
        windows = config["stance"].get(side, [])
        if clip in FULL_STANCE and not is_full(windows, frames):
            problems.append(f"STANCE_{side}_MUST_COVER_CLIP")
        if clip in STANCE_SHARE and coverage(windows, frames, loop) + 1e-9 < STANCE_SHARE[clip]:
            problems.append(f"STANCE_{side}_BELOW_{int(STANCE_SHARE[clip] * 100)}PCT")
    # The bed proxy of the request (assumption: 0.45 m high, 2.0 x 0.9 m); any clip may declare one (a holdout needs no
    # tool change), the bed clips must. Its placement is per-clip interaction setup, locked with the config SHA.
    proxy = config.get("bed")
    if proxy is not None or clip in BED_CLIPS:
        if not isinstance(proxy, dict) or proxy.get("top_z_m") != BED_TOP_Z or proxy.get("size_m") != BED_SIZE \
                or not (isinstance(proxy.get("centre_m"), list) and len(proxy["centre_m"]) == 2) or not isinstance(proxy.get("yaw_deg"), (int, float)):
            problems.append("BED_PROXY_0.45M_2.0x0.9M_WITH_CENTRE_AND_YAW")
    if config.get("bed_support", {}).get("windows") and proxy is None:
        problems.append("BED_SUPPORT_NEEDS_BED_PROXY")
    # Seated on the bed (user decisions, authorization entries 19-20): the coat may hang into the bed inside these
    # windows; one may meet a bed-support window on the frame where one ends and the other starts, never overlap it.
    seated = config.get("seated_on_bed", {}).get("windows", [])
    check_windows("seated_on_bed", seated)
    if seated and proxy is None:
        problems.append("SEATED_ON_BED_NEEDS_BED_PROXY")
    if any(windows_overlap(window, support, loop) for window in seated for support in config.get("bed_support", {}).get("windows", [])):
        problems.append("SEATED_ON_BED_OVERLAPS_BED_SUPPORT")
    bed = config.get("bed_support", {}).get("windows", [])
    if clip == "AN_RO_LieDown" and (not bed or bed[0][0] > share(0.70, frames) or bed[0][1] != frames - 1):
        problems.append("LIEDOWN_BED_FROM_ESTABLISHMENT_AT_OR_BEFORE_70PCT")
    if clip == "AN_RO_Sleep_Loop" and not is_full(bed, frames):
        problems.append("SLEEP_BED_MUST_COVER_CLIP")
    if clip == "AN_RO_GetUp":
        leave = events.get("leave_bed")
        if leave is None or leave < share(0.30, frames) or bed != [[0, leave]]:
            problems.append("GETUP_BED_UNTIL_LEAVE_AT_OR_AFTER_30PCT")
    problems += validate_sockets(config)
    if problems:
        raise InteractionError(", ".join(problems))
    return config


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))


def _read_registry(registry_path):
    path = Path(registry_path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "rule": "append-only; see scripts/cv1_interaction.py", "entries": []}


def register(registry_path, config_path, root, reason="before first measurement"):
    """Append the config's SHA for its clip. A clip already registered needs a reason (an implementation fix)."""
    config = load(config_path)
    registry = _read_registry(registry_path)
    digest = sha256_file(config_path)
    earlier = [e for e in registry["entries"] if e["clip"] == config["clip"]]
    if earlier and earlier[-1]["sha256"] == digest:
        return earlier[-1]
    if earlier and reason == "before first measurement":
        raise InteractionError("ALREADY_REGISTERED_GIVE_FIX_REASON:" + config["clip"])
    entry = {"clip": config["clip"], "path": Path(config_path).resolve().relative_to(Path(root).resolve()).as_posix(), "sha256": digest,
             "registered_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "reason": reason, "supersedes": earlier[-1]["sha256"] if earlier else None}
    registry["entries"].append(entry)
    Path(registry_path).parent.mkdir(parents=True, exist_ok=True)
    Path(registry_path).write_text(json.dumps(registry, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return entry


def registered(registry_path, config_path):
    """The registry entry matching this config file, or an error: measurement needs the latest registered SHA."""
    config = load(config_path)
    entries = [e for e in _read_registry(registry_path)["entries"] if e["clip"] == config["clip"]]
    if not entries:
        raise InteractionError("NOT_REGISTERED:" + config["clip"])
    if entries[-1]["sha256"] != sha256_file(config_path):
        raise InteractionError("CONFIG_CHANGED_SINCE_REGISTRATION:" + config["clip"])
    return config, entries[-1]


SOCKET_PLAN = {"AN_RO_LieDown": ("hand", [("put_sword_down", "bed")]), "AN_RO_Sleep_Loop": ("bed", []), "AN_RO_GetUp": ("bed", [("pick_sword_up", "hand")])}


def socket_at(config, t):
    """Where the sword hangs at time t: the initial socket, switched from each listed event frame on (inclusive)."""
    plan = config.get("sword_socket")
    if not plan:
        return "hand"
    events = {event["name"]: event["frame"] for event in config["events"]}
    current = plan["initial"]
    for switch in sorted(plan["switches"], key=lambda s: events[s["event"]]):
        if t >= events[switch["event"]]:
            current = switch["to"]
    return current


def seated_on_bed(config, t):
    """True inside the clip's declared seated-on-bed windows (no ramp; the coat exemption of authorization entries 19-20),
    except where a bed-support window covers t: on a frame the two windows share, the lying support has taken over."""
    if covered(config.get("bed_support", {}).get("windows", []), t, config["loop"]):
        return False
    return covered(config.get("seated_on_bed", {}).get("windows", []), t, config["loop"])


def near_socket_event(config, t, frames):
    """True when t lies within `frames` of a sword-socket switch event (the hand meets the sword on its rest)."""
    plan = config.get("sword_socket")
    if not plan:
        return False
    events = {event["name"]: event["frame"] for event in config["events"]}
    return any(abs(t - events[switch["event"]]) <= frames for switch in plan["switches"])


SOCKETS = ("hand", "bed")


def validate_sockets(config):
    """Any clip may declare a sword socket plan (generic schema: a start socket, switches on declared events, one bed
    socket transform beside a declared bed proxy); the three bed clips must declare the request's put-down / pick-up plan."""
    clip, plan = config["clip"], config.get("sword_socket")
    if plan is None:
        return ["SWORD_SOCKET_PLAN_" + clip] if clip in SOCKET_PLAN else []
    if not isinstance(plan, dict) or plan.get("initial") not in SOCKETS or not isinstance(plan.get("switches"), list):
        return ["SWORD_SOCKET_SCHEMA"]
    problems = []
    events = {event["name"]: event["frame"] for event in config["events"]}
    current = plan["initial"]
    for switch in sorted(plan["switches"], key=lambda s: events.get(s.get("event"), -1)):
        if switch.get("event") not in events:
            problems.append(f"SOCKET_EVENT_MISSING:{switch.get('event')}")
        elif switch.get("to") not in SOCKETS or switch["to"] == current:
            problems.append(f"SOCKET_SWITCH_INVALID:{switch.get('event')}")
        else:
            current = switch["to"]
    socket = plan.get("bed_socket", {})
    head, rotation = socket.get("head_m"), socket.get("quaternion_wxyz")
    if not (isinstance(head, list) and len(head) == 3 and isinstance(rotation, list) and len(rotation) == 4
            and abs(sum(v * v for v in rotation) - 1.0) < 1e-6):
        problems.append("BED_SOCKET_TRANSFORM")
    if "bed" not in config:
        problems.append("BED_SOCKET_NEEDS_BED_PROXY")
    if clip in SOCKET_PLAN:
        initial, switches = SOCKET_PLAN[clip]
        if plan.get("initial") != initial or [(s.get("event"), s.get("to")) for s in plan["switches"]] != switches:
            problems.append("SWORD_SOCKET_PLAN_" + clip)
    return problems


def seam_ok(angle_deg, distance_m):
    """Loop seam gate (transition_matrix.gates.loop_seam): every bone <= 1 degree, sole and grip points <= 1 mm."""
    return angle_deg <= 1.0 + 1e-9 and distance_m <= 0.001 + 1e-12
