"""Write the P4 transition scenarios of request r6 transition_matrix for the current clips (pure Python).

Usage: python -B scripts/cv1_p4_scenarios.py <out.json>
Every transition is played at each blend time (100/200/400 ms) and playback speed (0.5/1.0/1.5): a scenario starts the
source clip at wall time 0 and switches at SWITCH_S (a multiple of 1/30 s, so the 30, 60 and 120 fps grids meet the fade
start). Loop sources leave at two phases (for Walk/Run: mid-stance of each foot), non-loop sources start the fade
blend_s * speed of clip time before their last frame so the fade ends as the clip ends. Walk<->Run enter the target at
the matching foot's mid-stance; Idle->Walk enters Walk at the right foot's mid-stance. Walk->Cast(upper)->Walk is one scenario with two upper-body fades. Two repeated-switch
scenarios interrupt fades. Idle->Combo->Idle is the Idle->Combo entry (two Idle phases) and the Combo->Idle exit.
Fade timing (user decision C1, authorization entry 25): a fade never spans a socket or bed-support event of either clip.
An entry fade ends by the target's first event (shortened to fit, recorded in fade_timing); an exit fade from a non-loop
clip starts at its last event or later (the clip then holds its last frame).
Samples: the 120 fps grid inside each fade and each foot-lock release or settle (scripts/cv1_foot_lock.py), the 30 fps
grid over the rest of the window, which runs from one step before the first fade to one step after the last fade or
foot-lock end. Closed-loop reference samples: the fade midpoint at (100 ms, 1.0x), (200 ms, 0.5x), (200 ms, 1.0x) and
(400 ms, 1.5x), at (200 ms, 1.0x) also the middle of each foot lock after the fade and of each release or settle, the
return fade of Walk->Cast(upper)->Walk, and five points of each repeated switch.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_foot_lock as fl
import cv1_transition as tr

A = "assets/processed/ro-swordsman-character-v1/v001/clips"
CURRENT = {"Idle": ("AN_RO_Idle_Sword", "a03"), "Walk": ("AN_RO_Walk_Sword", "a04"), "Run": ("AN_RO_Run_Sword", "a02"),
           "Cast": ("AN_RO_Cast_OpenPalm", "a04"), "LieDown": ("AN_RO_LieDown", "a08"), "Sleep": ("AN_RO_Sleep_Loop", "a04"),
           "Combo": ("AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory", "a07"),
           "GetUp": ("AN_RO_GetUp", "a02")}
NOMINAL = {"Walk": 1.4, "Run": 3.5}  # request contact_measurement.nominal_speed_m_s
BLENDS, SPEEDS, FPS = (0.1, 0.2, 0.4), (0.5, 1.0, 1.5), 120
SWITCH_S = 0.5


def clips():
    out = {}
    for short, (clip, attempt) in CURRENT.items():
        config = json.loads((ROOT / A / clip / "interaction.json").read_text(encoding="utf-8"))
        out[short] = {"clip": clip, "attempt": attempt, "blend": f"{A}/{clip}/{attempt}/{clip}.blend", "interaction": f"{A}/{clip}/interaction.json",
                      "frames": config["frames"], "loop": config["loop"], "fps": config["fps"], "nominal_speed_m_s": NOMINAL.get(short, 0.0),
                      "stance": config["stance"], "interaction_events": interaction_events(config)}
    return out


def interaction_events(config):
    """Frames of the clip's sword-socket switches and of its bed-support window edges inside the clip (C1)."""
    named = {e["name"]: e["frame"] for e in config.get("events", [])}
    out = {named[s["event"]] for s in (config.get("sword_socket") or {}).get("switches", [])}
    for a, b in config.get("bed_support", {}).get("windows", []):
        out |= {x for x in (a, b) if 0 < x < config["frames"] - 1}
    return sorted(out)


def mid_stance(clip, side):
    start, end = clip["stance"][side][0]
    return (start + end) / 2.0


def source_entry(clip, exit_frame, speed):
    """Entry frame that puts the source clip at exit_frame when the fade starts at SWITCH_S."""
    frame = exit_frame - SWITCH_S * clip["fps"] * speed
    return frame % clip["frames"] if clip["loop"] else frame


def grid(t):
    return round(round(t * FPS) / FPS, 9)


def scenario(sid, pair, events, fades, blend, speed, clips_, timing=None, extra_reference=()):
    """Samples and closed-loop reference times (see the module docstring)."""
    locks = fl.schedule({"events": events}, clips_)
    lock_end = max([fades[-1][1]] + [fl.end_time(locks[side]) or 0.0 for side in fl.SIDES])
    lo, hi = fades[0][0] - 1.0 / FPS, lock_end + 1.0 / FPS
    times = set(round(t, 9) for t in tr.sample_times(lo, hi, 30))
    dense = [(a, b) for a, b in fades] + [tuple(e["release" if "release" in e else "settle"]) for side in fl.SIDES for e in locks[side]]
    for start, end in dense:
        times |= set(round(t, 9) for t in tr.sample_times(max(lo, start - 1.0 / FPS), min(hi, end + 1.0 / FPS), FPS))
    nominal = timing["nominal_blend_s"] if timing else blend
    reference = set()
    if (nominal, speed) in ((0.1, 1.0), (0.2, 0.5), (0.2, 1.0), (0.4, 1.5)):
        reference.add(grid(fades[0][0] + 0.5 * (fades[0][1] - fades[0][0])))
    if (nominal, speed) == (0.2, 1.0):
        for side in fl.SIDES:
            for e in locks[side]:
                if e["lock"][1] > fades[0][1]:
                    reference.add(grid(0.5 * (max(e["lock"][0], fades[0][1]) + e["lock"][1])))
                kind = "release" if "release" in e else "settle"
                reference.add(grid(0.5 * (e[kind][0] + e[kind][1])))
        reference |= {grid(t) for t in extra_reference}
    reference = sorted(t for t in reference if lo <= t <= hi)
    times |= set(reference)
    s = {"id": sid, "pair": pair, "blend_s": blend, "speed": speed, "events": events, "fades": fades, "sample_window": [lo, hi],
         "samples": sorted(times), "foot_lock_end": lock_end}
    if timing:
        s["fade_timing"] = timing
    if reference:
        s["reference_times"] = reference
    return s


def build():
    c = clips()
    lookup = {short: {"frames": v["frames"], "loop": v["loop"], "fps": v["fps"]} for short, v in c.items()}
    out = []

    def add(sid, pair, src, exit_frame, dst, entry_frame, blend, speed, mask=None):
        timing = {"nominal_blend_s": blend, "rule": "C1 (authorization entry 25)"}
        rate = c[dst]["fps"] * speed
        later = [f for f in c[dst]["interaction_events"] if f > entry_frame]
        if later and blend * rate > later[0] - entry_frame:  # the entry fade ends by the target's first event
            timing["shortened_from_s"], blend = blend, (later[0] - entry_frame) / rate
            timing["target_event_frame"] = later[0]
        if not c[src]["loop"] and c[src]["interaction_events"] and exit_frame < c[src]["interaction_events"][-1]:
            timing["exit_moved_from_frame"], exit_frame = exit_frame, float(c[src]["interaction_events"][-1])
        timing["blend_s"] = blend
        start = source_entry(c[src], exit_frame, speed)
        events = [{"t": 0.0, "layer": src, "clip": src, "entry_frame": start, "speed": speed},
                  {"t": SWITCH_S, "layer": dst, "clip": dst, "entry_frame": entry_frame, "speed": speed, "blend_s": blend, **({"mask": mask} if mask else {})}]
        tr.validate({"events": events}, lookup)
        out.append(scenario(sid, pair, events, [[SWITCH_S, SWITCH_S + blend]], blend, speed, c, timing))

    for blend in BLENDS:
        for speed in SPEEDS:
            tag = f"b{int(blend * 1000)}-s{speed}"
            walk_r, walk_l, run_r, run_l = (mid_stance(c["Walk"], "R"), mid_stance(c["Walk"], "L"), mid_stance(c["Run"], "R"), mid_stance(c["Run"], "L"))
            for phase in (0.0, 60.0):
                # Walk enters at the right foot's mid-stance (its foot under the body, as Walk<->Run match feet): the
                # foot lock then starts from where Idle stands instead of a heel strike 30 cm ahead.
                add(f"idle-walk-p{int(phase)}-{tag}", "Idle->Walk", "Idle", phase, "Walk", walk_r, blend, speed)
                add(f"idle-cast-p{int(phase)}-{tag}", "Idle->Cast", "Idle", phase, "Cast", 0.0, blend, speed)
                add(f"idle-combo-p{int(phase)}-{tag}", "Idle->Combo", "Idle", phase, "Combo", 0.0, blend, speed)
                add(f"idle-liedown-p{int(phase)}-{tag}", "Idle->LieDown", "Idle", phase, "LieDown", 0.0, blend, speed)
            for name, frame in (("r", walk_r), ("l", walk_l)):
                add(f"walk-idle-{name}-{tag}", "Walk->Idle", "Walk", frame, "Idle", 0.0, blend, speed)
            add(f"walk-run-r-{tag}", "Walk->Run", "Walk", walk_r, "Run", run_r, blend, speed)
            add(f"walk-run-l-{tag}", "Walk->Run", "Walk", walk_l, "Run", run_l, blend, speed)
            add(f"run-walk-r-{tag}", "Run->Walk", "Run", run_r, "Walk", walk_r, blend, speed)
            add(f"run-walk-l-{tag}", "Run->Walk", "Run", run_l, "Walk", walk_l, blend, speed)
            for src, dst in (("Cast", "Idle"), ("LieDown", "Sleep"), ("GetUp", "Idle"), ("Combo", "Idle")):
                end = c[src]["frames"] - 1
                add(f"{src.lower()}-{dst.lower()}-end-{tag}", f"{src}->{dst}", src, end - blend * c[src]["fps"] * speed, dst, 0.0, blend, speed)
            # Sleep -> GetUp: GetUp frame 0 equals Sleep frame 0, so the fade starts as Sleep wraps to frame 0.
            add(f"sleep-getup-wrap-{tag}", "Sleep->GetUp", "Sleep", 0.0, "GetUp", 0.0, blend, speed)
            # Walk -> Cast (upper body) -> Walk: the Cast upper body fades in, plays, and fades back to the Walk upper body.
            for name, frame in (("r", walk_r), ("l", walk_l)):
                cast_s = (c["Cast"]["frames"] - 1) / (c["Cast"]["fps"] * speed)
                back = SWITCH_S + cast_s - blend
                events = [{"t": 0.0, "layer": "Walk", "clip": "Walk", "entry_frame": source_entry(c["Walk"], frame, speed), "speed": speed},
                          {"t": SWITCH_S, "layer": "Cast", "clip": "Cast", "entry_frame": 0.0, "speed": speed, "blend_s": blend, "mask": "upper"},
                          {"t": back, "layer": "Walk", "blend_s": blend, "mask": "upper"}]
                tr.validate({"events": events}, lookup)
                out.append(scenario(f"walk-castupper-walk-{name}-{tag}", "Walk->Cast(upper)->Walk", events, [[SWITCH_S, SWITCH_S + blend], [back, back + blend]],
                                    blend, speed, c, extra_reference=(back + 0.5 * blend,)))
    # Repeated switch (1.0x, 200 ms fades interrupted every 100 ms).
    for pair, a, b, frame_a, frame_b in (("Idle<->Walk", "Idle", "Walk", 0.0, 0.0), ("Walk<->Run", "Walk", "Run", mid_stance(c["Walk"], "R"), mid_stance(c["Run"], "R"))):
        events = [{"t": 0.0, "layer": a, "clip": a, "entry_frame": source_entry(c[a], frame_a, 1.0), "speed": 1.0},
                  {"t": SWITCH_S, "layer": b, "clip": b, "entry_frame": frame_b, "speed": 1.0, "blend_s": 0.2}]
        for k, layer in enumerate((a, b, a), start=1):
            events.append({"t": round(SWITCH_S + 0.1 * k, 9), "layer": layer, "blend_s": 0.2})
        tr.validate({"events": events}, lookup)
        out.append(scenario(f"repeat-{a.lower()}-{b.lower()}", pair + " repeated", events, [[SWITCH_S, round(SWITCH_S + 0.5, 9)]], 0.2, 1.0, c,
                            extra_reference=(0.55, 0.65, 0.75, 0.85, 0.95)))
    changed = [{"id": s["id"], **s["fade_timing"]} for s in out if {"shortened_from_s", "exit_moved_from_frame"} & set(s.get("fade_timing", {}))]
    return {"schema_version": 2, "source": "requests/ro-swordsman-character-v1-r6.json#transition_matrix", "fps_grid": FPS, "switch_s": SWITCH_S,
            "decisions": "authorization entry 25: A1 foot lock (scripts/cv1_foot_lock.py), B1 coat exemption in transitions, C1 fade timing",
            "clips": c, "scenarios": out, "fade_timing_changed": changed, "pending": []}


if __name__ == "__main__":
    data = build()
    Path(sys.argv[1]).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"scenarios": len(data["scenarios"]), "samples": sum(len(s["samples"]) for s in data["scenarios"]),
                      "reference_samples": sum(len(s.get("reference_times", [])) for s in data["scenarios"])}))
