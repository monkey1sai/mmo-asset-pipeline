"""Per-category signatures of a character V1 foundation, for the frozen-holdout reuse check.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_foundation_signature.py -- \
       --rules <rules.json> --out <new signature.json> [--compare <earlier signature.json>]
Adding a clip changes the BLEND and GLB container hashes, so the frozen data is hashed category by category in a
normalized form that does not depend on actions, frame or object order:
  mesh      vertex rest positions (rounded to 0.1 um), polygons, per-corner UVs, material slot names
  rest      bone names, parents, deform flags, rest matrices (rounded to 1e-7)
  weights   per-vertex (group name, weight rounded to 1e-6), groups sorted by name
  morphs    shape key names and rest-space deltas (rounded to 0.1 um)
  rules     the corrective rules file, canonical JSON
  evaluator the rule evaluators and the runtime measurement module, file bytes
The BLEND is not saved. With --compare, prints which categories differ.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ["scripts/cv1_pose_rules.py", "tools/runtime-qa/three/src/cv1-pose-rules.js", "tools/runtime-qa/three/src/cv1-runtime.js"]
parser = argparse.ArgumentParser()
parser.add_argument("--rules", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--compare")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")


class Digest:
    def __init__(self):
        self.h = hashlib.sha256()

    def add(self, *items):
        for item in items:
            self.h.update(repr(item).encode("utf-8"))
            self.h.update(b"\x1f")

    def hex(self):
        return self.h.hexdigest()


def r(values, step):
    return tuple(int(round(v / step)) for v in values)


arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
meshes = sorted((o for o in arm.children if o.type == "MESH"), key=lambda o: o.name)
categories = {name: Digest() for name in ("mesh", "rest", "weights", "morphs")}
for obj in meshes:
    data = obj.data
    basis = data.shape_keys.key_blocks[0].data if data.shape_keys else None
    categories["mesh"].add("object", obj.name, len(data.vertices), [m.name if m else None for m in data.materials])
    for index, vertex in enumerate(data.vertices):
        categories["mesh"].add(r(basis[index].co if basis else vertex.co, 1e-7))
    for polygon in data.polygons:
        categories["mesh"].add(tuple(polygon.vertices), polygon.material_index)
    for layer in sorted(data.uv_layers, key=lambda u: u.name):
        categories["mesh"].add("uv", layer.name)
        for loop in layer.data:
            categories["mesh"].add(r(loop.uv, 1e-7))
    names = [g.name for g in obj.vertex_groups]
    categories["weights"].add("object", obj.name)
    for vertex in data.vertices:
        categories["weights"].add(tuple(sorted((names[g.group], int(round(g.weight * 1e6))) for g in vertex.groups if g.weight > 0)))
    categories["morphs"].add("object", obj.name)
    if data.shape_keys:
        for key in data.shape_keys.key_blocks[1:]:
            categories["morphs"].add(key.name, key.relative_key.name)
            for index, point in enumerate(key.data):
                delta = point.co - basis[index].co
                if delta.length > 5e-8:
                    categories["morphs"].add(index, r(delta, 1e-7))
for bone in sorted(arm.data.bones, key=lambda b: b.name):
    categories["rest"].add(bone.name, bone.parent.name if bone.parent else None, bone.use_deform, r([c for row in bone.matrix_local for c in row], 1e-7))

rules = json.loads((ROOT / args.rules).read_text(encoding="utf-8"))
signature = {name: digest.hex() for name, digest in categories.items()}
signature["rules"] = hashlib.sha256(json.dumps({k: v for k, v in rules.items() if k != "id"}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
evaluator = Digest()
for path in EVALUATOR:
    evaluator.add(path, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
signature["evaluator"] = evaluator.hex()
subject = Path(bpy.data.filepath).resolve()
record = {"subject": {"path": subject.relative_to(ROOT).as_posix() if subject.is_relative_to(ROOT) else "outside the repository: " + subject.name,
                      "sha256": hashlib.sha256(subject.read_bytes()).hexdigest()},
          "rules": args.rules, "evaluator_files": EVALUATOR, "meshes": [o.name for o in meshes], "bones": len(arm.data.bones),
          "actions_present": sorted(a.name for a in bpy.data.actions), "signature": signature}
if args.compare:
    earlier = json.loads((ROOT / args.compare).read_text(encoding="utf-8"))["signature"]
    record["compared_with"] = args.compare
    record["changed_categories"] = sorted(k for k in signature if signature[k] != earlier.get(k))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_SIGNATURE " + json.dumps({"signature": {k: v[:12] for k, v in signature.items()}, "changed": record.get("changed_categories")}))
