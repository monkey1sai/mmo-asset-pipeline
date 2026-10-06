"""Fresh-Blender readback of a GLB against Blender-evaluated reference positions.

Run: blender -b --factory-startup --python scripts/cv1_verify_glb_roundtrip.py -- \
       --glb <file.glb> --reference <blender-reference.json> --prefix baked --time-rule frame_over_fps --out <new result.json>
Imports the GLB into an empty scene, plays the imported clip (bones and morph weights as stored in the file),
and compares every exported vertex with the reference position of the same original vertex ID.
"""
from array import array
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--glb", required=True)
parser.add_argument("--reference", required=True)
parser.add_argument("--prefix", required=True)
parser.add_argument("--baked-samples-only", action="store_true", help="skip reference blocks marked baked_sample false (half frames a baked GLB does not key)")
parser.add_argument("--time-rule", choices=("frame_over_fps", "frame_minus_start_over_fps"), required=True)
parser.add_argument("--tolerance", type=float, default=1e-6)
parser.add_argument("--out", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out = (ROOT / args.out).resolve()
assert not out.exists(), out
reference_path = (ROOT / args.reference).resolve()
reference = json.loads(reference_path.read_text(encoding="utf-8"))
values = array("d")
values.frombytes((ROOT / reference["binary"]["path"]).read_bytes())
glb = (ROOT / args.glb).resolve()

# Start from --factory-startup and clear the default objects by hand. Never call wm.read_factory_settings here:
# on 2026-10-05 it made Blender empty the user's extension wheel cache (see p2-prep/incident-blender-extension-cache.json).
for leftover in list(bpy.data.objects):
    bpy.data.objects.remove(leftover)
scene = bpy.context.scene
scene.render.fps = reference["fps"]
bpy.ops.import_scene.gltf(filepath=str(glb), merge_vertices=False)
attribute = reference["id_attribute"]
imported = [o for o in bpy.data.objects if o.type == "MESH" and attribute in o.data.attributes]
objects = {o.name: o for o in imported}
# The importer names an object after its mesh data when the mesh has morph targets; match those by their morph names.
for layout in reference["mesh_layout"]:
    if layout["name"] not in objects:
        candidates = [o for o in imported if o.name not in {l["name"] for l in reference["mesh_layout"]} and o.data.shape_keys
                      and [k.name for k in o.data.shape_keys.key_blocks[1:]] == layout["morphs"]]
        assert len(candidates) == 1, (layout["name"], [o.name for o in candidates])
        objects[layout["name"]] = candidates[0]
first_frame = min(b["frame"] for b in reference["blocks"] if b["label"].startswith(args.prefix + "/frame-"))
rows = []
for block in reference["blocks"]:
    if not block["label"].startswith(args.prefix + "/frame-"):
        continue
    if args.baked_samples_only and block.get("baked_sample") is False:
        continue
    # The importer places a key stored at time t on frame t * fps.
    frame = block["frame"] if args.time_rule == "frame_over_fps" else block["frame"] - first_frame
    scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    worst, squares, count, over = None, 0.0, 0, 0
    for layout in reference["mesh_layout"]:
        obj = objects[layout["name"]]
        ids = [int(round(d.value)) for d in obj.data.attributes[attribute].data]
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        assert len(mesh.vertices) == len(ids)
        base = block["offset_values"] + layout["offset_values_in_block"]
        seen = set()
        for vertex, vertex_id in zip(mesh.vertices, ids):
            seen.add(vertex_id)
            p = evaluated.matrix_world @ vertex.co
            error = math.dist(p, values[base + 3 * vertex_id: base + 3 * vertex_id + 3])
            squares += error * error
            count += 1
            over += error > args.tolerance
            if worst is None or error > worst["error_m"]:
                worst = {"mesh": layout["name"], "blender_vertex": vertex_id, "error_m": error}
        assert len(seen) == layout["vertices"], (layout["name"], len(seen))
        evaluated.to_mesh_clear()
    rows.append({"reference_block": block["label"], "frame": block["frame"], "half_frame": block["frame"] != int(block["frame"]), "vertices": count,
                 "max_error_m": worst["error_m"], "rms_error_m": math.sqrt(squares / count), "over_tolerance": over, "worst": worst})
result = {
    "blender": bpy.app.version_string, "fresh_process_empty_scene": True,
    "glb": {"path": glb.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(glb.read_bytes()).hexdigest()},
    "reference": {"path": reference_path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest()},
    "prefix": args.prefix, "baked_samples_only": args.baked_samples_only, "time_rule": args.time_rule, "tolerance_m": args.tolerance, "samples": rows,
    "max_error_m": max(r["max_error_m"] for r in rows), "over_tolerance": sum(r["over_tolerance"] for r in rows),
    "pass": all(r["over_tolerance"] == 0 for r in rows),
    "scope": "Sampled frames only; same-version Blender source against its own GLB.",
}
out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_ROUNDTRIP", json.dumps({"pass": result["pass"], "max_um": result["max_error_m"] * 1e6, "over": result["over_tolerance"],
                                   "per_frame_um": {r["frame"]: round(r["max_error_m"] * 1e6, 3) for r in rows}}))
