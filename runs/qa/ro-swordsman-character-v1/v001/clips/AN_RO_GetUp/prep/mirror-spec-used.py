"""Build the AN_RO_GetUp key spec as the time reversal of an AN_RO_LieDown key spec (report: the anchors used).

Run: python -B mirror-spec-used.py <LieDown clip.json> <out GetUp clip.json>
Every key list ([[frame, value], ...]) is re-timed through a decreasing piecewise-linear map g(L) of LieDown frame L to
GetUp frame g and re-sorted; values are unchanged. Smoothstep easing between neighbouring keys is symmetric under time
reversal, so between anchors GetUp(g) equals LieDown(L(g)) exactly. Anchors: LieDown 89 -> 0 (Sleep pose), 63 -> 27
(bed support established in LieDown = leave_bed, request: at or after 30% = 27), 30 -> 60 (put_sword_down =
pick_sword_up, request: at or before 75% = 67.5), 0 -> 89 (Idle pose); between 63 and 30 the map is g = 90 - L exactly.
"""
import json
import sys
from pathlib import Path

ANCHORS = [(89.0, 0.0), (63.0, 27.0), (30.0, 60.0), (0.0, 89.0)]


def g(frame):
    for (l0, g0), (l1, g1) in zip(ANCHORS, ANCHORS[1:]):
        if l1 <= frame <= l0:
            return round(g0 + (frame - l0) * (g1 - g0) / (l1 - l0), 4)
    raise ValueError(f"FRAME_OUTSIDE_CLIP {frame}")


def remap(node):
    if isinstance(node, dict):
        return {k: (sorted([[g(f), v] for f, v in node[k]], key=lambda kv: kv[0]) if k == "keys" else remap(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [remap(v) for v in node]
    return node


source, out = Path(sys.argv[1]), Path(sys.argv[2])
lie = json.loads(source.read_text(encoding="utf-8"))
assert lie["clip"] == "AN_RO_LieDown" and lie["frames"] == 90 and lie["mode"] == "keys"
up = {k: remap(v) for k, v in lie.items() if k not in ("intent", "revision_note", "end_pose_note")}
up["clip"] = "AN_RO_GetUp"
up["intent"] = ("Time reversal of AN_RO_LieDown a07: from the AN_RO_Sleep_Loop a04 frame-0 pose (0-14.5) the coat swings towards the "
                "body right (14.5-27), sit up off the bed support (leave_bed 27, 27-34), turn back on the seat with the legs raised over "
                "the sword (33-40), bend the knees (40-44), scoot to the bed edge (43-50), the right hand comes off the thigh, reaches "
                "behind the socketed grip, slides the half-closed fingers under it and closes on it (50-60, pick_sword_up 60) while the "
                "feet come down to the floor (52-58) and the body leans right (54-62), lift the sword (60-72) and stand to the Idle ready "
                "stance (72-89; feet slide back 75.5-86).")
up["revision_note"] = ("a01: built by prep/mirror-spec-used.py from AN_RO_LieDown clip.json a07 (time map anchors LieDown 89/63/30/0 -> "
                       "GetUp 0/27/60/89; between 63 and 30 g = 90 - L). Entry 20: seated_on_bed mirrors LieDown, from leaving the lying "
                       "support until standing.")
up["start_pose_note"] = "Frame 0 equals AN_RO_Sleep_Loop a04 frame 0; frame 89 equals AN_RO_LieDown a07 frame 0 (the Idle ready stance)."
out.write_text(json.dumps(up, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_MIRROR " + json.dumps({"anchors": ANCHORS, "leave_bed": g(63.0), "pick_sword_up": g(30.0), "stance_from_lie_16_32": [g(32.0), g(16.0)],
                                 "seated_from_lie_2_63": [g(63.0), g(2.0)]}))
