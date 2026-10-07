"""Compare one frame of two action-only BLENDs (report only): every pose bone's keyed rotation (angle between the two
quaternions) and location (distance) at the given frames, e.g. a transition clip's last frame against the next clip's
first frame. Bones keyed in only one action count as rest in the other.

Run: blender -b --factory-startup --disable-autoexec --python end-pose-match-used.py -- <a.blend> <action> <frame> <b.blend> <action> <frame> <out.json>
"""
import json
import math
import sys

import bpy
from mathutils import Quaternion, Vector

a_path, a_name, a_frame, b_path, b_name, b_frame, out = sys.argv[sys.argv.index("--") + 1:]


def pose(path, name, frame):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.actions = [name]
    action = dst.actions[0]
    action.name = path
    values = {}
    for curve in action.fcurves:
        bone = curve.data_path.split('"')[1]
        kind = curve.data_path.rsplit(".", 1)[1]
        values.setdefault(bone, {}).setdefault(kind, {})[curve.array_index] = curve.evaluate(float(frame))
    out = {}
    for bone, kinds in values.items():
        q = kinds.get("rotation_quaternion")
        loc = kinds.get("location")
        out[bone] = {"q": Quaternion([q.get(i, 1.0 if i == 0 else 0.0) for i in range(4)]).normalized() if q else Quaternion(),
                     "loc": Vector([loc.get(i, 0.0) for i in range(3)]) if loc else Vector()}
    return out


a, b = pose(a_path, a_name, a_frame), pose(b_path, b_name, b_frame)
rows = []
for bone in sorted(set(a) | set(b)):
    qa, qb = a.get(bone, {"q": Quaternion()})["q"], b.get(bone, {"q": Quaternion()})["q"]
    la, lb = a.get(bone, {"loc": Vector()})["loc"], b.get(bone, {"loc": Vector()})["loc"]
    rows.append({"bone": bone, "deg": math.degrees(qa.rotation_difference(qb).angle), "m": (la - lb).length})
rows.sort(key=lambda r: -r["deg"])
report = {"a": [a_path, a_name, a_frame], "b": [b_path, b_name, b_frame], "max_deg": max(r["deg"] for r in rows), "max_m": max(r["m"] for r in rows),
          "worst": rows[:8]}
open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(report, indent=1) + "\n")
print("CV1_MATCH " + json.dumps({k: report[k] for k in ("max_deg", "max_m")}) + " " + json.dumps(rows[:5]))
