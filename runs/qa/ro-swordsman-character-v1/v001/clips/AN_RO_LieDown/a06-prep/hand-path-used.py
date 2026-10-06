"""Probe (report only): the right hand's world path in a clip action, frame by frame: wrist (hand.R head) and grip
point (sword bone head; the clip does not key the sword, so in the raw action it rides hand.R's rest attachment),
with the speed between consecutive frames (m/s at the clip fps). No sockets, helpers or correctives: bone motion only.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python hand-path-used.py -- <action .blend> <action> <first> <last> <out.json>
"""
import json
import sys
from pathlib import Path

import bpy

action_blend, name, first, last, out = sys.argv[sys.argv.index("--") + 1:]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [name]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
fps = bpy.context.scene.render.fps
rows, prev = [], None
for f in range(int(first), int(last) + 1):
    bpy.context.scene.frame_set(f)
    wrist = arm.matrix_world @ arm.pose.bones["hand.R"].head
    grip = arm.matrix_world @ arm.pose.bones["sword"].head
    row = {"frame": f, "wrist": [round(c, 4) for c in wrist], "grip": [round(c, 4) for c in grip]}
    if prev is not None:
        row["wrist_m_s"] = round((wrist - prev[0]).length * 60, 3)
        row["grip_m_s"] = round((grip - prev[1]).length * 60, 3)
    prev = (wrist.copy(), grip.copy())
    rows.append(row)
    print("CV1_PATH " + json.dumps(row))
Path(out).write_text(json.dumps({"action": name, "fps_assumed": 60, "rows": rows}, indent=1) + "\n", encoding="utf-8", newline="\n")
