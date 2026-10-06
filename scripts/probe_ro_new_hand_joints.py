"""Freeze measured source joint landmarks and inspect native poles before binding."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from ro_hand_gate import inside
BASE = ROOT / "runs/qa/ro-swordsman-combo-r007"
QA = BASE / "v001-source-preparation"
assert not (QA / "joint-and-pole-probe.json").exists()
preparation = json.loads((QA / "preparation.json").read_text())
source = ROOT / preparation["artifact"]["path"]
assert hashlib.sha256(source.read_bytes()).hexdigest() == preparation["artifact"]["sha256"]
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
ob = bpy.data.objects["SM_RO_RightHand_Exterior"]; ob.data.calc_loop_triangles()
scale = preparation["uniform_scale"]
# Centerlines follow actual measured source sections, the visible branch bend
# and ring positions. Names retain fixture little-to-index branch ordering.
native = {
    "finger1": [(-.050,-.010,.177),(-.0537,-.021,.198),(-.0528,-.029,.215),(-.052,-.034,.232)],
    "finger2": [(-.032,-.001,.180),(-.0356,-.013,.205),(-.0348,-.029,.235),(-.034,-.035,.252)],
    "finger3": [(-.013,.005,.182),(-.014,-.005,.210),(-.0127,-.020,.245),(-.0117,-.0254,.264)],
    "finger4": [(.007,.008,.183),(.0102,.0025,.210),(.0124,-.0094,.235),(.0136,-.015,.253)],
    "thumb": [(.019,-.012,.130),(.038,-.020,.166),(.0501,-.02598,.185),(.055,-.026,.197)],
}
landmarks = {name: [list(Vector(p) * scale) for p in values] for name, values in native.items()}
tree = BVHTree.FromPolygons([v.co for v in ob.data.vertices], [t.vertices for t in ob.data.loop_triangles], all_triangles=True)
votes = []
for name, values in landmarks.items():
    for index, point in enumerate(values[:-1]):
        p = Vector(point)
        votes.append({"branch": name, "joint": index, "point": point,
                      "inside_positive_ray_vote": inside(tree, p), "nearest_surface_m": tree.find_nearest(p)[3]})
bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
thumb = [Vector(p) for p in landmarks["thumb"]]
# Anatomical flexion masks are frozen before posing. Axial bands around CMC,
# MCP/IP and bounded radial neighborhood; disclose these are authored masks.
bands = [(thumb[0], (thumb[1]-thumb[0]).normalized(), .010*scale, .030*scale, "CMC"),
         (thumb[1], (thumb[2]-thumb[1]).normalized(), .008*scale, .015*scale, "MCP"),
         (thumb[2], (thumb[3]-thumb[2]).normalized(), .006*scale, .013*scale, "IP")]
regions = {name: [] for *_, name in bands}
poles = []
native_id = bm.verts.layers.int["native_source_id"]
for v in bm.verts:
    membership = []
    for center, direction, axial, radial, name in bands:
        delta = v.co-center; along = delta.dot(direction)
        if abs(along) <= axial and (delta-direction*along).length <= radial:
            membership.append(name); regions[name].append(v.index)
    if len(v.link_edges) != 4:
        poles.append({"vertex": v.index, "native_source_id": v[native_id]-1 if v[native_id] else None,
                      "valence": len(v.link_edges), "point": list(v.co), "thumb_flex_regions": membership})
bm.free()
bad = [p for p in poles if p["thumb_flex_regions"]]
report = {"observed_utc": datetime.now(timezone.utc).isoformat(), "source": preparation["artifact"],
    "method": "Actual native sections + visible source rings; authored centers frozen before skin/pose; parity with upward rays on open wrist shell is diagnostic",
    "source_normalized_native_landmarks": native, "scaled_landmarks": landmarks,
    "wrist_center_scaled": [-.010693962685763836*scale,.001922769472002983*scale,.095*scale],
    "joint_volume_checks": votes, "all_joint_centers_inside_diagnostic": all(v["inside_positive_ray_vote"] is True for v in votes),
    "thumb_flex_masks": regions, "thumb_flex_band_parameters": [{"name": n,"center":list(c),"axis":list(d),"half_axial_m":a,"radius_m":r} for c,d,a,r,n in bands],
    "native_poles": poles, "poles_in_primary_thumb_flex_bands": bad,
    "thumb_flex_band_pole_gate": not bad, "rig_created": False,
    "animation_topology_accepted": False, "source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == preparation["artifact"]["sha256"],
    "limitations": ["Band location/radius is artist-authored, not a complete mathematical deformation region",
                    "Joint centers need actual direction/skin testing; pole-band result alone never proves animation acceptance"]}
(QA / "joint-and-pole-probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("RO_JOINT_POLES " + json.dumps({"inside": report["all_joint_centers_inside_diagnostic"], "bad_poles": bad}))
