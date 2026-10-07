"""Probe (report only): which coat vertices a supine clip frame sinks into the bed, by rest-space region, with the
local panel slope (angle between the evaluated face normal and world up) of the sunk faces.

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python sunk-coat-probe-used.py -- \
       <action .blend> <action name> <frame> <interaction.json> <out.json>
Skinning only (the coat has no shape keys in b19), nothing saved.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector

action_blend, action_name, frame, interaction_path, out = sys.argv[sys.argv.index("--") + 1:]
config = json.loads(Path(interaction_path).read_text(encoding="utf-8"))
bed = config["bed"]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(action_blend, link=False) as (src, dst):
    dst.actions = [action_name]
arm.animation_data_create()
arm.animation_data.action = dst.actions[0]
bpy.context.scene.frame_set(int(frame))
bpy.context.view_layer.update()
coat = bpy.data.objects["SM_RO_coat"]
groups = {g.index: g.name for g in coat.vertex_groups}
depsgraph = bpy.context.evaluated_depsgraph_get()
target = coat.evaluated_get(depsgraph)
mesh = target.to_mesh()
world = [target.matrix_world @ v.co for v in mesh.vertices]
mesh.calc_loop_triangles()
tris = [tuple(t.vertices) for t in mesh.loop_triangles]
target.to_mesh_clear()
rest = [v.co.copy() for v in coat.data.vertices]
cx, cy = bed["centre_m"]
top = bed["top_z_m"]
half_l, half_w = bed["size_m"][0] / 2, bed["size_m"][1] / 2
over = [abs(p.x - cx) <= half_l and abs(p.y - cy) <= half_w for p in world]
sunk = [i for i, p in enumerate(world) if over[i] and p.z < top]


def region(i):
    x, y, z = rest[i]
    dom = max(coat.data.vertices[i].groups, key=lambda g: g.weight)
    name = groups[dom.group]
    side = "back" if y > 0.12 else ("front" if y < -0.05 else "side")
    return f"{name}:{side}"


by_region = Counter(region(i) for i in sunk)
depth_by_region = {}
for i in sunk:
    r = region(i)
    depth_by_region[r] = max(depth_by_region.get(r, 0.0), top - world[i].z)
slopes = Counter()
for a, b, c in tris:
    if all(i in set(sunk) for i in (a, b, c)) if False else (world[a].z < top and world[b].z < top and world[c].z < top and over[a]):
        n = (world[b] - world[a]).cross(world[c] - world[a])
        if n.length < 1e-12:
            continue
        angle = math.degrees(math.acos(min(1.0, abs(n.normalized().z))))
        slopes[int(angle // 15) * 15] += 1
report = {"frame": int(frame), "sunk_vertices": len(sunk), "by_region": dict(by_region.most_common()),
          "max_depth_mm_by_region": {k: round(v * 1e3, 1) for k, v in sorted(depth_by_region.items())},
          "sunk_face_slope_deg_histogram": {f"{k}-{k + 15}": v for k, v in sorted(slopes.items())},
          "rest_y_range_of_sunk": [round(min(rest[i].y for i in sunk), 3), round(max(rest[i].y for i in sunk), 3)],
          "rest_z_range_of_sunk": [round(min(rest[i].z for i in sunk), 3), round(max(rest[i].z for i in sunk), 3)],
          "rest_x_range_of_sunk": [round(min(rest[i].x for i in sunk), 3), round(max(rest[i].x for i in sunk), 3)]}
Path(out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_SUNK " + json.dumps(report))
