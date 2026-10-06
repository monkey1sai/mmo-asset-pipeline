"""Read-only probe of the whole character's forearm ends: where the right hand was cut off the core and what the left hand is.

Run: blender -b --factory-startup --disable-autoexec <ro_whole_baseline.blend> --python <this file>
Nothing is saved to the BLEND. Output: left-arm-probe.json
"""
from pathlib import Path
import json

import bpy
import bmesh
from mathutils import Vector

OUT = Path(__file__).with_name("left-arm-probe.json")
assert not OUT.exists()
arm = bpy.data.objects["ARM_RO_Swordsman"]
bones = arm.data.bones
core = bpy.data.objects["SM_RO_core"]
groups = [g.name for g in core.vertex_groups]


def axial(side):
    wrist = bones[f"hand.{side}"].head_local
    axis = (wrist - bones[f"lower_arm.{side}"].head_local).normalized()
    return wrist, axis


bm = bmesh.new()
bm.from_mesh(core.data)
bm.verts.ensure_lookup_table()
# boundary loops of the core
edges = [e for e in bm.edges if e.is_boundary]
neighbours = {}
for e in edges:
    a, b = e.verts[0].index, e.verts[1].index
    neighbours.setdefault(a, set()).add(b)
    neighbours.setdefault(b, set()).add(a)
loops, seen = [], set()
for start in neighbours:
    if start in seen:
        continue
    stack, loop = [start], []
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        loop.append(v)
        stack.extend(neighbours[v] - seen)
    centre = sum((bm.verts[i].co for i in loop), Vector()) / len(loop)
    radius = max((bm.verts[i].co - centre).length for i in loop)
    row = {"vertices": len(loop), "centre": [round(c, 4) for c in centre], "max_radius_mm": round(radius * 1e3, 1)}
    for side in "LR":
        wrist, axis = axial(side)
        row[f"axial_from_wrist_{side}_mm"] = round((centre - wrist).dot(axis) * 1e3, 1)
    loops.append(row)
bm.free()

sides = {}
for side in "LR":
    wrist, axis = axial(side)
    hand_names = {n for n in groups if n.endswith(f".{side}") and n.startswith("hand") or f".{side}_" in n}
    weights = {}
    beyond_wrist = distal_major = 0
    low, high = 1e9, -1e9
    for v in core.data.vertices:
        hand_weight = sum(g.weight for g in v.groups if groups[g.group] in hand_names)
        position = (v.co - wrist).dot(axis)
        if position > 0:
            beyond_wrist += 1
        if hand_weight > 0.5:
            distal_major += 1
            low, high = min(low, position), max(high, position)
        for g in v.groups:
            name = groups[g.group]
            if name in hand_names and g.weight > 0:
                weights[name] = weights.get(name, 0) + 1
    obj = bpy.data.objects.get(f"SM_RO_bracer.{side}")
    span = [(obj.matrix_world @ v.co - wrist).dot(axis) for v in obj.data.vertices]
    sides[side] = {"wrist": [round(c, 4) for c in wrist], "forearm_axis": [round(c, 4) for c in axis], "core_vertices_past_wrist": beyond_wrist,
                   "core_vertices_mostly_hand_weighted": distal_major, "their_axial_range_mm": [round(low * 1e3, 1), round(high * 1e3, 1)] if distal_major else None,
                   "hand_group_vertex_counts": weights, "bracer_axial_range_mm": [round(min(span) * 1e3, 1), round(max(span) * 1e3, 1)], "bracer_vertices": len(span)}
mirror = {name: round((Vector((-bones[f"{name}.R"].head_local.x, bones[f"{name}.R"].head_local.y, bones[f"{name}.R"].head_local.z)) - bones[f"{name}.L"].head_local).length * 1e3, 3)
          for name in ("clavicle", "upper_arm", "lower_arm", "hand")}
result = {"core_boundary_loops": sorted(loops, key=lambda r: -r["vertices"]), "sides": sides, "left_vs_mirrored_right_bone_head_mm": mirror,
          "core_vertices": len(core.data.vertices)}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_LEFT_PROBE", json.dumps(result))
