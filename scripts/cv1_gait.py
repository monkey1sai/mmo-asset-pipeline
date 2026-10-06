"""In-place locomotion cycle for character V1 clips (pure math, no Blender).

Phase f / frames in [0, 1). Each foot has a stance part [0, stance) where it stays flat (rest orientation) and moves
backward at the nominal speed, as the ground would under an in-place loop, and a swing part where it returns: a
cubic Hermite path whose end velocities match the stance velocity (scaled by tangent_scale), a sin^2 lift, and a
pitch that lifts the heel first (pivot at the toe) and the toes before landing (pivot at the heel), so nothing dips
below the floor. Distances are along the character's forward axis, relative to the rest ankle.
The pelvis bobs twice per cycle (highest at mid-stance), sways toward the stance foot and turns the leading hip
forward; its height is lowered as far as the legs' reach requires (see pelvis_heights).
"""
import math


def hermite(p0, m0, p1, m1, s):
    s2, s3 = s * s, s * s * s
    return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1


def foot_state(phase, gait, cycle_seconds):
    """Forward offset (m, + = forward), lift (m), pitch (deg, + = heel up about the toe, - = toes up about the heel), in stance."""
    stance, speed = gait["stance"], gait["nominal_speed_m_s"]
    travel = speed * stance * cycle_seconds
    phase %= 1.0
    if phase < stance - 1e-12:
        return {"forward": travel / 2 - travel * phase / stance, "lift": 0.0, "pitch": 0.0, "stance": True}
    s = (phase - stance) / (1.0 - stance)
    tangent = -travel * (1.0 - stance) / stance * gait.get("tangent_scale", 0.5)
    forward = hermite(-travel / 2, tangent, travel / 2, tangent, s)
    lift = gait["swing_height_m"] * math.sin(math.pi * s) ** 2
    if s < 0.5:
        pitch = gait["toe_off_pitch_deg"] * math.sin(2 * math.pi * s)
    else:
        pitch = gait["landing_pitch_deg"] * math.sin(2 * math.pi * (s - 0.5))
    return {"forward": forward, "lift": lift, "pitch": pitch, "stance": False}


def foot_phase(frame, side, gait, frames):
    """Phase of one foot at a (possibly fractional) frame, from whole-frame offsets so window edges stay exact."""
    start = round(gait["phase_offsets"][side] * frames)
    return ((frame - start) % frames) / frames


def stance_window(gait, side, frames):
    """Whole frames in which the foot is flat: [start, end] inclusive, wrapping in a loop when needed."""
    start = round(gait["phase_offsets"][side] * frames) % frames
    count = sum(1 for f in range(frames) if foot_state(foot_phase(f, side, gait, frames), gait, 1.0)["stance"])
    return [start, (start + count - 1) % frames]


def pelvis_motion(phase, gait):
    """Pelvis offsets before the height fit: bob shape (unitless, max at mid-stance), sway (m, + = toward +X), yaw and roll (deg)."""
    p = gait["pelvis"]
    stance = gait["stance"]
    bob = math.cos(4 * math.pi * (phase - stance / 2))
    # Right foot (phase offset 0) in stance near phase stance/2: shift toward the right foot (-X) and drop the left hip.
    sway = -p["sway_m"] * math.cos(2 * math.pi * (phase - stance / 2))
    yaw = p["yaw_deg"] * math.cos(2 * math.pi * phase)
    roll = p.get("roll_deg", 0.0) * math.cos(2 * math.pi * (phase - stance / 2))
    return {"bob": bob, "sway": sway, "yaw": yaw, "roll": roll}


def pelvis_heights(frames, gait, reach_limit):
    """Pelvis height offset per frame: base drop plus bob, lowered as a whole so every leg target stays in reach.

    reach_limit(frame, base_offset) -> the largest pelvis height offset (m) that keeps both legs in reach at that frame.
    The bob keeps its amplitude and shape; only its centre moves down, so the motion stays smooth.
    """
    amplitude = gait["pelvis"]["bob_m"]
    shapes = [pelvis_motion(f / frames, gait)["bob"] for f in range(frames + 1)]
    allowed = [reach_limit(f) - amplitude * shapes[f] for f in range(frames + 1)]
    centre = min(min(allowed) - gait["pelvis"]["margin_m"], gait["pelvis"].get("max_height_offset_m", 0.0))
    if centre < -gait["pelvis"]["max_drop_m"]:
        raise ValueError(f"PELVIS_DROP_TOO_LARGE {centre:.3f}")
    return [centre + amplitude * shapes[f] for f in range(frames + 1)], centre
