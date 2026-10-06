"""Contact fixtures for the character V1 clip checks: foot sole sets and bed support sets as vertex-ID lists.

Run: blender -b --factory-startup --disable-autoexec <character.blend> --python scripts/cv1_contact_fixtures.py -- \
       --request <request.json> --contract <joint-range-contract.json> --out <new fixtures.json>
Definitions follow the request's support_envelope.contact_measurement:
- sole_set per foot: rest vertices whose foot + toe bone weights sum to >= 0.5 and that lie within 10 mm above the
  lowest of those vertices.
- bed support sets: back (spine bones), pelvis, back of head (head bone) and each calf (lower leg bone); vertices whose
  region bone weights sum to >= 0.5 and that lie within 10 mm of the region's rearmost point (+Y is the back).
Vertex IDs are Blender vertex indices, which the exporter writes as the _CV1_ID attribute. Measured meshes are all
skinned meshes except the contract's excluded ones. Rest positions are the Basis coordinates with the armature at rest.
The BLEND is never saved and an existing output is refused. The floor (Z=0) and the bed proxy plane placement belong
to each clip's interaction setup, not to these lists.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--request", required=True)
parser.add_argument("--contract", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


request = json.loads((ROOT / args.request).read_text(encoding="utf-8"))
contract = json.loads((ROOT / args.contract).read_text(encoding="utf-8"))
excluded = set(contract["limits"].get("excluded_meshes", contract.get("excluded_meshes", [])))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
meshes = sorted((o for o in arm.children if o.type == "MESH" and o.name not in excluded), key=lambda o: o.name)

# Rest positions and per-vertex weights of every measured mesh.
points, weights = {}, {}
for obj in meshes:
    names = [g.name for g in obj.vertex_groups]
    points[obj.name] = [obj.matrix_world @ v.co for v in obj.data.vertices]
    weights[obj.name] = [{names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in obj.data.vertices]


def members(bones):
    return [(name, index) for name in points for index, w in enumerate(weights[name]) if sum(w.get(b, 0.0) for b in bones) >= 0.5]


def as_lists(selected):
    lists = {}
    for name, index in selected:
        lists.setdefault(name, []).append(index)
    return {name: sorted(ids) for name, ids in sorted(lists.items())}


def summary(selected, lists):
    xs = [points[n][i] for n, i in selected]
    centre = [round(sum(p[k] for p in xs) / len(xs), 5) for k in range(3)]
    return {"vertices": len(selected), "by_mesh": {n: len(ids) for n, ids in lists.items()}, "centroid_m": centre,
            "z_range_m": [round(min(p.z for p in xs), 5), round(max(p.z for p in xs), 5)],
            "y_range_m": [round(min(p.y for p in xs), 5), round(max(p.y for p in xs), 5)], "sha256": canonical_sha(lists)}


fixtures = {}
for side in ("L", "R"):
    region = members((f"foot.{side}", f"toe.{side}"))
    lowest = min(points[n][i].z for n, i in region)
    chosen = [(n, i) for n, i in region if points[n][i].z <= lowest + 0.010]
    lists = as_lists(chosen)
    fixtures[f"sole_set.{side}"] = {"rule": "foot+toe weight >= 0.5 and z <= lowest + 10 mm", "region_vertices": len(region),
                                    "lowest_z_m": round(lowest, 5), **summary(chosen, lists), "ids": lists}

support_regions = {"back": ("spine_01", "spine_02"), "pelvis": ("pelvis",), "head_back": ("head",),
                   "calf.L": ("lower_leg.L",), "calf.R": ("lower_leg.R",)}
for key, bones in support_regions.items():
    region = members(bones)
    rearmost = max(points[n][i].y for n, i in region)
    chosen = [(n, i) for n, i in region if points[n][i].y >= rearmost - 0.010]
    lists = as_lists(chosen)
    fixtures[f"bed_support.{key}"] = {"rule": f"weight of {'+'.join(bones)} >= 0.5 and y >= rearmost - 10 mm (+Y is the back)",
                                      "region_vertices": len(region), "rearmost_y_m": round(rearmost, 5), **summary(chosen, lists), "ids": lists}

result = {
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "blender": bpy.app.version_string,
    "script_sha256": sha(__file__),
    "source": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)},
    "request": {"path": args.request, "sha256": sha(ROOT / args.request)},
    "definition_verbatim": {k: request["support_envelope"]["contact_measurement"][k] for k in ("floor", "sole_set", "bed")},
    "measured_meshes": [o.name for o in meshes],
    "vertex_id": "Blender vertex index per mesh = exported _CV1_ID",
    "fixtures": fixtures,
    "fixtures_sha256": canonical_sha({k: v["ids"] for k, v in fixtures.items()}),
    "scope": "Measurement point sets only. They are fixed with the foundation at freeze; floor and bed placement are per-clip setup.",
}
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "x", encoding="utf-8", newline="\n") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=1)
    handle.write("\n")
print("CV1_CONTACT_FIXTURES " + json.dumps({k: {x: v[x] for x in ("vertices", "by_mesh", "z_range_m", "y_range_m")} for k, v in fixtures.items()}))
