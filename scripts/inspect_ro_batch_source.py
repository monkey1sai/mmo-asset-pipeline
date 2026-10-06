"""Inspect a completed batch source without claiming semantic parts or animation QA."""
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_review_common import stage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_source(root, raw, downloads):
    models = [x for x in downloads if isinstance(x.get("path"), str) and Path(x["path"]).suffix.lower() == ".glb"]
    if len(models) != 1:
        raise RuntimeError("Inspect changed output contract; expected one GLB")
    relative = Path(models[0]["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("Raw source path/hash mismatch")
    source = (root / relative).resolve(strict=True)
    if not source.is_relative_to(raw.resolve()) or digest(source) != models[0]["sha256"]:
        raise RuntimeError("Raw source path/hash mismatch")
    return source, models[0]["sha256"]


def components(mesh):
    """Logical adjacency weld for diagnostics only; source vertices/UVs are untouched."""
    parents = list(range(len(mesh.vertices)))

    def find(v):
        while parents[v] != v:
            parents[v] = parents[parents[v]]
            v = parents[v]
        return v

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[b] = a

    positions = {}
    for v in mesh.vertices:
        key = tuple(round(c / 1e-6) for c in v.co)
        if key in positions:
            union(v.index, positions[key])
        else:
            positions[key] = v.index
    for edge in mesh.edges:
        union(*edge.vertices)
    groups = defaultdict(list)
    for v in mesh.vertices:
        groups[find(v.index)].append(v)
    triangles = defaultdict(int)
    polygons = defaultdict(list)
    for face in mesh.polygons:
        root = find(face.vertices[0])
        triangles[root] += len(face.vertices) - 2
        polygons[root].append(face.index)
    ordered = sorted(groups, key=lambda root: (-triangles[root], -len(groups[root]), root))
    return [{"id": index, "vertices": len(groups[root]), "triangles": triangles[root],
        "min": [min(v.co[i] for v in groups[root]) for i in range(3)],
        "max": [max(v.co[i] for v in groups[root]) for i in range(3)],
        "polygon_indices": polygons[root]} for index, root in enumerate(ordered)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", default="ro-split-batch-20261003-001")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if args.operation != "ro-split-batch-20261003-001":
        raise RuntimeError("This inspection is bound to the prepared batch operation")
    journal = json.loads((ROOT / "runs/hyper3d/operations" / (args.operation + ".json")).read_text(encoding="utf-8"))
    if journal["state"] != "downloaded" or journal["operation_id"] != args.operation:
        raise RuntimeError("Only the bound completed download is eligible")
    raw = ROOT / "assets/raw/ro-swordsman-combo/rodin-v004/batch"
    source, source_sha256 = bound_source(ROOT, raw, journal["downloads"])
    out = ROOT / "assets/processed/ro-swordsman-combo-r005/batch-source"
    qa = ROOT / "runs/qa/ro-swordsman-combo-r005/batch-source"
    if out.exists() or qa.exists():
        raise RuntimeError("Preserve existing inspection; use a new version for any rerun")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    if not points:
        raise RuntimeError("Downloaded source contains no mesh")
    lo = Vector([min(v[i] for v in points) for i in range(3)])
    hi = Vector([max(v[i] for v in points) for i in range(3)])
    if hi.z - lo.z <= 1e-6:
        raise RuntimeError("Unexpected source orientation; inspect before normalization")
    factor = 1.74 / (hi.z - lo.z)
    origin = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    out.mkdir(parents=True)
    qa.mkdir(parents=True)
    stats = []
    mapping = []
    for index, ob in enumerate(meshes):
        ob.data = ob.data.copy()
        matrix = ob.matrix_world.copy()
        for v in ob.data.vertices:
            v.co = (matrix @ v.co - origin) * factor
        ob.parent = None
        ob.matrix_world = Matrix.Identity(4)
        ob.name = f"SM_RO_Batch_Source_{index:03d}"
        ob.data.update()
        groups = components(ob.data)
        mapping.append({"mesh": ob.name, "components": groups})
        stats.append({"mesh": ob.name, "vertices": len(ob.data.vertices),
            "triangles": sum(len(p.vertices) - 2 for p in ob.data.polygons),
            "uv_layers": len(ob.data.uv_layers),
            "materials": [m.name for m in ob.data.materials if m],
            "components": [{k: v for k, v in g.items() if k != "polygon_indices"} for g in groups]})
    for image in bpy.data.images:
        if image.type == "IMAGE" and image.size[0] and not image.packed_file:
            image.pack()
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.export_scene.gltf(filepath=str(out / "batch_source.glb"), export_format="GLB",
        use_selection=True, export_animations=False, export_yup=True)
    stage()
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    target = Vector((0, 0, .87))
    extent = max((hi - lo).x * factor, (hi - lo).y * factor, 1.74)
    radius = max(4, extent * 2.5)
    views = {"front": (0, -radius, 1.0), "side": (radius, 0, 1.0),
        "back": (0, radius, 1.0), "three-quarter": (radius * .65, -radius, 1.5),
        "top-three-quarter": (radius * .4, -radius * .8, radius * .7)}
    for name, location in views.items():
        cam = scene.camera
        cam.location = location
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = extent * 1.35
        scene.render.filepath = str(qa / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "batch_source.blend"))
    (qa / "component-polygon-map.json").write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    report = {"operation_id": args.operation, "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": source_sha256, "tool": bpy.app.version_string,
        "normalization": {"purpose": "display only; not character height or component fit", "factor": factor,
            "original_min": list(lo), "original_max": list(hi)}, "mesh_stats": stats,
        "triangle_total": sum(x["triangles"] for x in stats),
        "diagnostic_component_count": sum(len(x["components"]) for x in stats),
        "semantic_asset_count": None, "anatomy_accepted": False, "art_accepted": False,
        "rig_accepted": False, "animation_accepted": False, "delivered": False,
        "interpretation": "Connected geometry is diagnostic, not a count of six complete useful assets. Visual/component/fit review required.",
        "images": [{"name": x.name, "size": list(x.size), "packed": bool(x.packed_file)} for x in bpy.data.images if x.type == "IMAGE"],
        "bones": sum(len(o.data.bones) for o in bpy.data.objects if o.type == "ARMATURE"),
        "animations": len(bpy.data.actions),
        "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
            "sha256": digest(p)} for p in sorted(out.iterdir()) if p.suffix in {".blend", ".glb"}]}
    (qa / "inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if digest(source) != source_sha256:
        raise RuntimeError("Raw source changed")
    print("RO_BATCH_INSPECTION " + json.dumps({"triangles": report["triangle_total"],
        "diagnostic_components": report["diagnostic_component_count"], "semantic_assets": None,
        "report": str(qa / "inspection.json")}))


if __name__ == "__main__":
    main()
