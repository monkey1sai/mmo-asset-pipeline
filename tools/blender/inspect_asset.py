"""Inspect actual Blender/FBX/GLB data without saving the source scene."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from pipeline import local_path, load_json, write_new


def inspect(tri_budget, rig_profile=None, max_influences=4):
    errors = []
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    rows = []
    total = 0
    for obj in meshes:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        data = evaluated.to_mesh()
        try:
            data.calc_loop_triangles()
            count = len(data.loop_triangles)
            total += count
            if not count:
                errors.append(f"{obj.name}: empty mesh")
            if not data.uv_layers:
                errors.append(f"{obj.name}: missing UVs")
        finally:
            evaluated.to_mesh_clear()
        row = {"name": obj.name, "triangles": count, "uv_layers": len(obj.data.uv_layers), "material_slots": len(obj.material_slots), "modifiers": [m.type for m in obj.modifiers]}
        if rig_profile:
            bindings = [m.object for m in obj.modifiers if m.type == "ARMATURE" and m.object and m.object.type == "ARMATURE" and m.show_viewport]
            ancestor = obj
            rigid_parent = None
            while ancestor.parent:
                if ancestor.parent_type == "BONE" and ancestor.parent.type == "ARMATURE":
                    if ancestor.parent_bone in ancestor.parent.data.bones:
                        rigid_parent = ancestor.parent_bone
                    else:
                        errors.append(f"{obj.name}: invalid rigid parent bone")
                    break
                ancestor = ancestor.parent
            if not bindings and rigid_parent:
                row.update(deformation="rigid", parent_bone=rigid_parent)
            elif len(bindings) != 1:
                errors.append(f"{obj.name}: expected one enabled armature binding")
            else:
                binding = bindings[0]
                groups = {g.index for g in obj.vertex_groups if g.name in binding.data.bones and binding.data.bones[g.name].use_deform}
                bad_sum = unweighted = excessive = 0
                peak = 0
                for vertex in obj.data.vertices:
                    weights = [g.weight for g in vertex.groups if g.group in groups and g.weight > 0.000001]
                    peak = max(peak, len(weights))
                    unweighted += not weights
                    excessive += len(weights) > max_influences
                    bad_sum += bool(weights) and abs(sum(weights) - 1.0) > 0.001
                row.update(deformation="skin", max_deform_influences=peak, unweighted_vertices=unweighted, excessive_influences_vertices=excessive, unnormalized_vertices=bad_sum)
                if unweighted or excessive or bad_sum:
                    errors.append(f"{obj.name}: skin weights invalid (unweighted={unweighted}, excessive={excessive}, unnormalized={bad_sum})")
        rows.append(row)
    if not meshes:
        errors.append("No mesh objects found")
    if total > tri_budget:
        errors.append(f"Triangle budget exceeded: {total} > {tri_budget}")
    if rig_profile:
        if len(armatures) != 1:
            errors.append("Expected one export armature")
        else:
            bones = armatures[0].data.bones
            for name, parent in rig_profile["bones"].items():
                bone = bones.get(name)
                if not bone:
                    errors.append(f"Missing required bone: {name}")
                elif (bone.parent.name if bone.parent else None) != parent:
                    errors.append(f"Invalid parent: {name}")
    return {
        "technical_status": "FAIL" if errors else "PASS", "production_status": "UNVERIFIED",
        "scope": "mesh counts, UV presence, optional required rig hierarchy and deform weights",
        "triangles": total, "triangle_budget": tri_budget, "meshes": rows, "errors": errors,
        "armatures": [{"name": a.name, "bones": len(a.data.bones)} for a in armatures],
        "unverified": ["visual deformation", "T-pose", "sockets", "textures and shaders", "LOD chain", "Unity import/runtime", "performance"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--tri-budget", type=int, required=True)
    parser.add_argument("--rig-profile")
    parser.add_argument("--max-influences", type=int, default=4)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    try:
        source, output = local_path(args.input), local_path(args.report)
        if output.exists():
            raise ValueError("Report exists; choose a new versioned filename")
        if args.tri_budget <= 0 or args.max_influences <= 0:
            raise ValueError("Budgets must be positive")
        rigs = load_json(ROOT / "configs/rig_profiles.json")
        if args.rig_profile and args.rig_profile not in rigs:
            raise ValueError("Unknown rig profile")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        suffix = source.suffix.lower()
        if suffix == ".blend":
            bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
        elif suffix in (".fbx", ".glb", ".gltf"):
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete()
            if suffix == ".fbx":
                bpy.ops.import_scene.fbx(filepath=str(source))
            else:
                bpy.ops.import_scene.gltf(filepath=str(source))
        else:
            raise ValueError("Use .blend, .fbx, .glb or .gltf")
        report = inspect(args.tri_budget, rigs.get(args.rig_profile), args.max_influences)
        report.update(source=source.relative_to(ROOT).as_posix(), source_sha256=digest, blender_version=bpy.app.version_string, rig_profile=args.rig_profile)
        write_new(output, report)
        print(f"{report['technical_status']}: Blender inspection; production remains UNVERIFIED")
        return 1 if report["errors"] else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
