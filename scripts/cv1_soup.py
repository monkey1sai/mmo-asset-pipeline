"""Shared mesh measurement for the character V1 checks (Blender side): one triangle soup over all measured meshes.

Used by scripts/cv1_joint_range.py (contract poses) and scripts/cv1_clip_check.py (animation samples), so both judge
collapse, hand-region intersections, stretch and armour contact the same way. `limits` is the joint-range contract's
limits block. Call set_rest() with the armature at rest before measuring.
"""
from collections import Counter

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def tri_area(points, tri):
    return (points[tri[1]] - points[tri[0]]).cross(points[tri[2]] - points[tri[0]]).length / 2


class Soup:
    def __init__(self, meshes, limits):
        self.meshes, self.limits = meshes, limits
        self.hand_prefixes = tuple(limits["hand_bone_prefixes"])
        self.armour_bones, self.armour_meshes = set(limits.get("armor_bones", [])), set(limits.get("armor_meshes", []))
        self.armour_slack = limits.get("armor_depth_slack_m", 0.0)
        self.armour_weight, self.tris, self.tri_mesh, self.edges, self.hand_weight, self.bone_vertices, self.dominant = [], [], [], [], [], {}, []
        self.offsets = {}
        for obj in meshes:
            base = len(self.hand_weight)
            self.offsets[obj.name] = base
            names = [g.name for g in obj.vertex_groups]
            for v in obj.data.vertices:
                total = 0.0
                armour_total = 0.0
                for g in v.groups:
                    name = names[g.group]
                    if g.weight >= limits["deform_min_weight"]:
                        self.bone_vertices.setdefault(name, []).append(base + v.index)
                    if name.startswith(self.hand_prefixes):
                        total += g.weight
                    if name in self.armour_bones:
                        armour_total += g.weight
                self.hand_weight.append(total)
                self.armour_weight.append(armour_total)
                self.dominant.append(max(((g.weight, names[g.group]) for g in v.groups), default=(0, None))[1])
            obj.data.calc_loop_triangles()
            self.tris.extend(tuple(base + i for i in t.vertices) for t in obj.data.loop_triangles)
            self.tri_mesh.extend(obj.name for _ in obj.data.loop_triangles)
            self.edges.extend((base + e.vertices[0], base + e.vertices[1]) for e in obj.data.edges)
        self.is_hand_vertex = [w >= 0.5 for w in self.hand_weight]
        self.tri_hand = [any(self.is_hand_vertex[i] for i in t) for t in self.tris]
        # Armour class: triangles of an armour mesh, or body triangles carried by an armour bone (all three vertices >= 0.5).
        self.tri_armour = [self.tri_mesh[k] in self.armour_meshes or all(self.armour_weight[i] >= 0.5 for i in t) for k, t in enumerate(self.tris)]
        self.edge_hand = [self.is_hand_vertex[a] or self.is_hand_vertex[b] for a, b in self.edges]

    def evaluated_points(self):
        """World positions of every measured vertex, in soup order."""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        points = []
        for obj in self.meshes:
            target = obj.evaluated_get(depsgraph)
            mesh = target.to_mesh()
            assert len(mesh.vertices) == len(obj.data.vertices), obj.name
            points.extend(target.matrix_world @ v.co for v in mesh.vertices)
            target.to_mesh_clear()
        return points

    def set_rest(self):
        """Record the rest state; the caller has put the armature at rest and updated the view layer."""
        self.rest = rest = self.evaluated_points()
        position_keys = {}
        # Rest-coincident vertices (UV or normal splits, also across meshes) count as one for adjacency; posed coordinates are never welded.
        self.canonical = [position_keys.setdefault(tuple(round(c, 7) for c in p), len(position_keys)) for p in rest]
        self.rest_area = [tri_area(rest, t) for t in self.tris]
        self.rest_edge = [(rest[a] - rest[b]).length for a, b in self.edges]
        self.rest_pairs = self.intersecting_pairs(rest)
        self.rest_hand_self, self.rest_hand_other, self.rest_other, self.rest_armour = self.classify(self.rest_pairs)
        # Triangle neighbours across shared (rest-welded) edges, for the flip diagnostic: an area ratio cannot see a
        # triangle that folds through and opens again on the other side.
        by_edge = {}
        for t, tri in enumerate(self.tris):
            keys = [self.canonical[i] for i in tri]
            for a, b in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
                by_edge.setdefault((min(a, b), max(a, b)), []).append(t)
        self.neighbours = [[] for _ in self.tris]
        for members in by_edge.values():
            if 2 <= len(members) <= 4:
                for t in members:
                    self.neighbours[t].extend(m for m in members if m != t)
        self.rest_agreement = self.normal_agreement(rest)
        self.rest_depth = {}
        for a, b in self.rest_armour:
            depth = self.pair_depth(rest, a, b)
            self.rest_depth[a], self.rest_depth[b] = max(self.rest_depth.get(a, 0.0), depth), max(self.rest_depth.get(b, 0.0), depth)

    def intersecting_pairs(self, points):
        tree = BVHTree.FromPolygons(points, self.tris, all_triangles=True, epsilon=0.0)
        canonical, tris = self.canonical, self.tris
        return {(a, b) for a, b in tree.overlap(tree) if a < b and not ({canonical[i] for i in tris[a]} & {canonical[i] for i in tris[b]})}

    def classify(self, pairs):
        tri_hand, tri_armour = self.tri_hand, self.tri_armour
        hand_self = [p for p in pairs if tri_hand[p[0]] and tri_hand[p[1]]]
        hand_other = [p for p in pairs if tri_hand[p[0]] != tri_hand[p[1]]]
        body = [p for p in pairs if not tri_hand[p[0]] and not tri_hand[p[1]]]
        armour = [p for p in body if tri_armour[p[0]] or tri_armour[p[1]]]
        other = [p for p in body if not (tri_armour[p[0]] or tri_armour[p[1]])]
        return hand_self, hand_other, other, armour

    def crossing(self, points, t, plane_tri):
        """How far triangle t reaches through the plane of plane_tri on its shallower side."""
        a, b, c = (points[i] for i in self.tris[plane_tri])
        normal = (b - a).cross(c - a)
        if normal.length < 1e-14:
            return 0.0
        normal.normalize()
        side = [(points[i] - a).dot(normal) for i in self.tris[t]]
        return min(max(0.0, max(side)), max(0.0, -min(side)))

    def pair_depth(self, points, a, b):
        return min(self.crossing(points, a, b), self.crossing(points, b, a))

    def normal_agreement(self, points):
        """Per triangle: cosine between its normal and the summed normals of its edge neighbours (None without neighbours)."""
        normals = []
        for tri in self.tris:
            n = (points[tri[1]] - points[tri[0]]).cross(points[tri[2]] - points[tri[0]])
            normals.append(n.normalized() if n.length > 1e-14 else Vector())
        out = []
        for t, around in enumerate(self.neighbours):
            total = sum((normals[m] for m in around), Vector())
            out.append(None if not around or total.length < 1e-9 else normals[t].dot(total.normalized()))
        return out

    def centre(self, points, t):
        return [round(c, 4) for c in sum((points[i] for i in self.tris[t]), Vector()) / 3]

    def measure(self, points):
        limits, tris, rest_area, rest, tri_mesh, dominant = self.limits, self.tris, self.rest_area, self.rest, self.tri_mesh, self.dominant
        ratios = [tri_area(points, t) / area for t, area in zip(tris, rest_area) if area > limits["min_rest_triangle_area_m2"]]
        collapsed = [i for i, (t, area) in enumerate(zip(tris, rest_area)) if area > limits["min_rest_triangle_area_m2"] and tri_area(points, t) / area < limits["collapse_area_ratio"]]
        hand_ratio, other_ratio = [], []
        for (a, b), length, hand in zip(self.edges, self.rest_edge, self.edge_hand):
            if length > 1e-6:
                (hand_ratio if hand else other_ratio).append((points[a] - points[b]).length / length)
        hand_self, hand_other, other, armour = self.classify(self.intersecting_pairs(points))
        excess, deepest, violations, armour_examples = 0.0, 0.0, 0, []
        for a, b in armour:
            depth = self.pair_depth(points, a, b)
            allowed = max(self.rest_depth.get(a, 0.0), self.rest_depth.get(b, 0.0)) + self.armour_slack
            deepest = max(deepest, depth)
            if depth > allowed:
                violations += 1
                excess = max(excess, depth - allowed)
                if len(armour_examples) < 5:
                    armour_examples.append({"meshes": [tri_mesh[a], tri_mesh[b]], "depth_mm": round(depth * 1e3, 2), "allowed_mm": round(allowed * 1e3, 2), "at": self.centre(points, a)})
        hand_other_new = [p for p in hand_other if p not in self.rest_pairs]
        other_new = [p for p in other if p not in self.rest_pairs]
        examples = [{"meshes": [tri_mesh[a], tri_mesh[b]], "bones": [sorted({dominant[i] for i in tris[a]}), sorted({dominant[i] for i in tris[b]})],
                     "at": self.centre(points, a)} for a, b in (hand_self + hand_other_new)[:8]]
        # Flip diagnostic (report only): a triangle that agreed with its neighbours at rest now faces against them.
        agreement = self.normal_agreement(points)
        flipped = [t for t, (now, before) in enumerate(zip(agreement, self.rest_agreement)) if now is not None and before is not None and before > 0.5 and now < 0.0]
        return {"collapsed_triangles": sum(1 for r in ratios if r < limits["collapse_area_ratio"]), "min_triangle_area_ratio": min(ratios),
                "hand_self_pairs": len(hand_self), "hand_other_pairs": len(hand_other), "hand_other_new_pairs": len(hand_other_new),
                "other_pairs": len(other), "other_new_pairs": len(other_new),
                "armor_pairs": len(armour), "armor_depth_max_m": deepest, "armor_depth_violations": violations, "armor_excess_max_m": excess, "armor_examples": armour_examples,
                "other_new_by_mesh_pair": dict(sorted(Counter("|".join(sorted((tri_mesh[a], tri_mesh[b]))) for a, b in other_new).items(), key=lambda kv: -kv[1])[:8]),
                "other_new_examples": [{"meshes": [tri_mesh[a], tri_mesh[b]], "at": self.centre(points, a)} for a, b in other_new[:4]],
                "hand_edge_ratio": [min(hand_ratio), max(hand_ratio)] if hand_ratio else None, "other_edge_ratio": [min(other_ratio), max(other_ratio)],
                "hand_examples": examples,
                "collapsed_examples": [{"mesh": tri_mesh[i], "triangle": i, "rest_at": self.centre(rest, i), "rest_area_mm2": round(rest_area[i] * 1e6, 4)} for i in collapsed[:6]],
                "flipped_triangles": len(flipped),
                "flipped_examples": [{"mesh": tri_mesh[i], "triangle": i, "rest_at": self.centre(rest, i), "dominant": sorted({dominant[k] for k in tris[i]})} for i in flipped[:6]]}
