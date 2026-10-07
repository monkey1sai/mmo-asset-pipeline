"""Compare two action-only BLENDs key by key (report only): every fcurve (data path, index) and every keyframe value.

Run: blender -b --factory-startup --disable-autoexec --python compare-actions-used.py -- <a.blend> <action> <b.blend> <action> <out.json>
"""
import json
import sys

import bpy

a_path, a_name, b_path, b_name, out = sys.argv[sys.argv.index("--") + 1:]


def load(path, name):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.actions = [name]
    action = dst.actions[0]
    action.name = path  # keep the two copies apart
    return {(c.data_path, c.array_index): [tuple(p.co) for p in c.keyframe_points] for c in action.fcurves}


a, b = load(a_path, a_name), load(b_path, b_name)
worst, missing = 0.0, sorted(set(a) ^ set(b))
for key in set(a) & set(b):
    if len(a[key]) != len(b[key]):
        missing.append(key)
        continue
    for (fa, va), (fb, vb) in zip(a[key], b[key]):
        worst = max(worst, abs(fa - fb), abs(va - vb))
report = {"a": a_path, "b": b_path, "fcurves": [len(a), len(b)], "mismatched_curves": [list(k) for k in missing], "max_abs_difference": worst,
          "identical": not missing and worst == 0.0}
open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(report, indent=1) + "\n")
print("CV1_COMPARE " + json.dumps(report))
