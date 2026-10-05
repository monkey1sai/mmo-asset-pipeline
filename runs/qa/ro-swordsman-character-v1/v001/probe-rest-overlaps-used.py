"""Read-only: count intersecting triangle pairs between each pair of meshes at rest, and the depth of the overlap.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python <this file> -- <out.json>
Depth: for each vertex of mesh A that lies inside the closed region bounded by mesh B (ray parity test along +Z and -X),
the distance to B's surface. Open meshes make parity approximate; the counts are reported as a diagnostic.
"""
from itertools import combinations
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

out = sys.argv[sys.argv.index("--") + 1]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
for pb in arm.pose.bones:
    pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
data = {}
for obj in sorted((o for o in arm.children if o.type == "MESH"), key=lambda o: o.name):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    data[obj.name] = (points, tris, BVHTree.FromPolygons(points, tris, all_triangles=True))
    evaluated.to_mesh_clear()


def inside(tree, point):
    hits = 0
    for direction in (Vector((0, 0, 1)), Vector((-1, 0, 0))):
        count, origin = 0, point.copy()
        for _ in range(64):
            location, _, _, _ = tree.ray_cast(origin, direction)
            if location is None:
                break
            count += 1
            origin = location + direction * 1e-6
        hits += count % 2
    return hits == 2


rows = []
for a, b in combinations(sorted(data), 2):
    pairs = data[a][2].overlap(data[b][2])
    if not pairs:
        continue
    depths = []
    for name, other in ((a, b), (b, a)):
        tree = data[other][2]
        for point in data[name][0][::3]:
            if inside(tree, point):
                _, _, _, distance = tree.find_nearest(point)
                depths.append(distance)
    depths.sort()
    rows.append({"meshes": [a, b], "triangle_pairs": len(pairs), "sampled_vertices_inside_other": len(depths),
                 "depth_mm_p50": round(depths[len(depths) // 2] * 1e3, 2) if depths else None, "depth_mm_max": round(depths[-1] * 1e3, 2) if depths else None})
rows.sort(key=lambda r: -r["triangle_pairs"])
json.dump({"rest_overlaps_between_meshes": rows}, open(out, "x", encoding="utf-8"), indent=1)
print("CV1_REST_OVERLAPS", json.dumps(rows[:12]))
