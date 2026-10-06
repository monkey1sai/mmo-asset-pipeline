"""Snapshot every skinned mesh's vertex weights from a BLEND, keyed by original vertex index.

Run: blender -b --factory-startup --disable-autoexec <character.blend> --python scripts/cv1_weights_snapshot.py -- --out <new snapshot.json>
Read-only for the BLEND. The snapshot feeds scripts/cv1_restore_glb_weights.py.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy

parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--id-attribute", default="_CV1_ID")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
target = Path(args.out).resolve()
armatures = [o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children)]
assert len(armatures) == 1
meshes = {}
for obj in sorted((o for o in armatures[0].children if o.type == "MESH"), key=lambda o: o.name):
    names = [g.name for g in obj.vertex_groups]
    meshes[obj.name] = {"vertices": len(obj.data.vertices),
                        "weights": [[[names[g.group], g.weight] for g in v.groups if g.weight > 0] for v in obj.data.vertices]}
snapshot = {"source": {"path": bpy.data.filepath, "sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()},
            "id_attribute": args.id_attribute, "armature": armatures[0].name, "meshes": meshes}
with open(target, "x", encoding="utf-8", newline="\n") as handle:
    json.dump(snapshot, handle)
print("CV1_WEIGHTS_SNAPSHOT", json.dumps({name: m["vertices"] for name, m in meshes.items()}))
