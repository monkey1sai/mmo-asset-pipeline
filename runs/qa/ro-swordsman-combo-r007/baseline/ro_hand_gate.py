"""Actual evaluated glove/sword gate. Samples alone never pass intersections."""
import hashlib
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bpy
import bmesh

RAYS = [Vector((.713,.389,.587)).normalized(), Vector((.419,.831,.365)).normalized()]

def evaluated(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    mesh.calc_loop_triangles()
    points = [ev.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    edges = [tuple(e.vertices) for e in mesh.edges]
    ev.to_mesh_clear()
    return points, triangles, edges

def sword_solid(ob):
    points, triangles, edges = evaluated(ob)
    diagnostic = bmesh.new()
    for p in points:
        diagnostic.verts.new(p)
    diagnostic.verts.ensure_lookup_table()
    for t in triangles:
        diagnostic.faces.new([diagnostic.verts[i] for i in t])
    bmesh.ops.remove_doubles(diagnostic, verts=list(diagnostic.verts), dist=1e-6)
    bad = sum(not e.is_manifold for e in diagnostic.edges)
    diagnostic.free()
    if bad:
        raise RuntimeError("Actual sword is not a welded closed solid")
    return points, triangles, BVHTree.FromPolygons(points, triangles, all_triangles=True)

def inside(tree, point):
    votes = []
    for direction in RAYS:
        origin = point.copy()
        count = 0
        while count < 100:
            hit, normal, face, distance = tree.ray_cast(origin, direction, 10)
            if hit is None:
                break
            if distance < 1e-7 or abs(normal.dot(direction)) < 1e-7:
                return None
            count += 1
            origin = hit + direction * 2e-7
        if count == 100:
            return None
        votes.append(bool(count % 2))
    return votes[0] if votes[0] == votes[1] else None

def segment_hit(a, b, tri):
    # Transverse segment/triangle, including triangle boundaries; no coplanar pass claim.
    u,v,w = tri
    direction = b-a
    e1,e2 = v-u,w-u
    p = direction.cross(e2)
    det = e1.dot(p)
    if abs(det) < 1e-13:
        return None
    inv = 1/det
    tvec = a-u
    x = tvec.dot(p)*inv
    q = tvec.cross(e1)
    y = direction.dot(q)*inv
    t = e2.dot(q)*inv
    if x >= -1e-7 and y >= -1e-7 and x+y <= 1+1e-7 and 1e-6 < t < 1-1e-6:
        return a+direction*t
    return None

def contacts(glove, sword, rig, pads, label, parameters):
    points, triangles, edges = evaluated(glove)
    expected = {"finger1", "finger2", "finger3", "finger4", "thumb"}
    if not isinstance(pads, dict) or set(pads) != expected:
        raise ValueError("COMPLETE_FIVE_DIGIT_MASK_REQUIRED")
    for name, ids in pads.items():
        if (not isinstance(ids, list) or len(ids) < 3 or len(set(ids)) != len(ids)
            or any(type(i) is not int or not 0 <= i < len(points) for i in ids)):
            raise ValueError("UNIQUE_VALID_CONTACT_VERTEX_IDS_REQUIRED: " + name)
    sword_points, sword_triangles, solid = sword_solid(sword)
    root = rig.pose.bones['sword'].head
    axis = (rig.pose.bones['sword'].tail-root).normalized()
    indices = [i for i,t in enumerate(sword_triangles)
        if -.112 <= (sum((sword_points[v] for v in t), Vector())/3-root).dot(axis) <= .085]
    if not indices:
        raise RuntimeError("Actual handle mask empty")
    handle_triangles = [sword_triangles[i] for i in indices]
    handle = BVHTree.FromPolygons(sword_points, handle_triangles, all_triangles=True)
    sampled = [("vertex", i, p) for i,p in enumerate(points)]
    sampled += [("face", i, sum((points[j] for j in t),Vector())/3) for i,t in enumerate(triangles)]
    sampled += [("edge", i, (points[a]+points[b])/2) for i,(a,b) in enumerate(edges)]
    unknown = []
    penetrations = []
    for kind,index,p in sampled:
        nearest = solid.find_nearest(p)
        if nearest[0] is None:
            unknown.append([kind,index,"nearest_missing"])
            continue
        if nearest[3] < 1e-7:
            continue
        vote = inside(solid,p)
        if vote is None:
            unknown.append([kind,index,"parity_unknown"])
        elif vote:
            penetrations.append({"kind":kind,"index":index,"depth_m":nearest[3],"point":list(p)})
    pads_report = {}
    for name,ids in pads.items():
        distances = [handle.find_nearest(points[i])[3] for i in ids]
        pads_report[name] = {"vertices":len(ids),"minimum_gap_m":min(distances),
            "mean_gap_m":sum(distances)/len(distances),"within_2mm":sum(d<=.002 for d in distances)}
    glove_tree = BVHTree.FromPolygons(points,triangles,all_triangles=True)
    crossings = []
    for i,j in glove_tree.overlap(solid):
        a = [points[k] for k in triangles[i]]
        b = [sword_points[k] for k in sword_triangles[j]]
        hits = []
        for left,right in [(a,b),(b,a)]:
            for k in range(3):
                hit = segment_hit(left[k],left[(k+1)%3],right)
                if hit is not None:
                    hits.append(list(hit))
        if hits:
            crossings.append({"glove_triangle":i,"sword_triangle":j,"locations":hits})
    fingerprint = hashlib.sha256(json.dumps({"positions":[list(p) for p in points],
        "triangles":triangles,"parameters":parameters},sort_keys=True).encode()).hexdigest()
    maximum = max((p["depth_m"] for p in penetrations),default=0)
    return {"label":label,"parameters":parameters,"candidate_fingerprint":fingerprint,
        "actual_sword_closed_after_weld":True,"handle_triangles":len(indices),
        "pad_contacts":pads_report,"sample_count":len(sampled),"unknown_inside":unknown,
        "maximum_penetration_m":maximum,"deep_samples":sum(p['depth_m']>.001 for p in penetrations),
        "worst_penetrations":sorted(penetrations,key=lambda p:-p["depth_m"])[:12],
        "transverse_crossings_count":len(crossings),"crossings":crossings,
        "surface_gate_pass":not unknown and maximum<=.001 and not crossings and all(r["within_2mm"]>=3 for r in pads_report.values()),
        "visual_acceptance_required":True}
