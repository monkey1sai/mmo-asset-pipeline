"""Move each pauldron bone's pivot to the pauldron's inner top edge (where it rests on the cuirass), and optionally lift
the pauldron a few millimetres off the cuirass.

Run: blender -b --factory-startup --disable-autoexec <candidate.blend> --python scripts/cv1_pauldron_hinge.py -- \
       --tag <name> --out-dir <assets dir of the candidate> [--lift-mm N]
A pauldron turning about the shoulder joint sweeps its inner rim through the cuirass; hinged at the inner top edge,
that rim stays put and the outer plates swing. The bone keeps its parent, direction and length; only the head and
tail move. Mesh weights are unchanged, so the rest shape does not move unless --lift-mm is given, in which case the
pauldron mesh (and any core vertex bound to the pauldron bone, in proportion to its weight) moves along the
pauldron's outward direction. The input BLEND is not modified; a new BLEND is written and existing outputs are refused.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--tag", required=True)
parser.add_argument("--out-dir", required=True)
parser.add_argument("--lift-mm", type=float, default=0.0)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
core = bpy.data.objects["SM_RO_core"]
report = {}
pivots = {}
for side, sign in (("L", 1.0), ("R", -1.0)):
    pauldron = bpy.data.objects[f"SM_RO_pauldron.{side}"]
    points = [pauldron.matrix_world @ v.co for v in pauldron.data.vertices]
    # Inner top edge: highest points of the pauldron on the neck side; take the mean of the 2 % most extreme ones.
    inward_up = Vector((-sign, 0.0, 1.0)).normalized()
    ranked = sorted(points, key=lambda p: -p.dot(inward_up))
    top = ranked[:max(5, len(ranked) // 50)]
    pivots[side] = sum(top, Vector()) / len(top)
    outward = Vector((sign, 0.0, 0.6)).normalized()
    lift = outward * (args.lift_mm / 1000)
    if args.lift_mm:
        for v in pauldron.data.vertices:
            v.co = v.co + pauldron.matrix_world.inverted().to_3x3() @ lift
        group = core.vertex_groups.get(f"pauldron.{side}")
        moved = 0
        if group:
            for v in core.data.vertices:
                weight = next((g.weight for g in v.groups if g.group == group.index), 0.0)
                if weight > 0:
                    v.co = v.co + lift * weight
                    moved += 1
                    if core.data.shape_keys:
                        for key in core.data.shape_keys.key_blocks:
                            key.data[v.index].co = key.data[v.index].co + lift * weight
        report[f"core_vertices_lifted_{side}"] = moved
    report[f"pivot_{side}"] = [round(c, 4) for c in pivots[side]]

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for side in ("L", "R"):
    bone = arm.data.edit_bones[f"pauldron.{side}"]
    before = (bone.head.copy(), bone.tail.copy())
    offset = pivots[side] - bone.head
    bone.head = bone.head + offset
    bone.tail = bone.tail + offset
    report[f"pauldron.{side}_head_moved_mm"] = round(offset.length * 1e3, 2)
    report[f"pauldron.{side}_head_before"] = [round(c, 4) for c in before[0]]
bpy.ops.object.mode_set(mode="OBJECT")
out_dir.mkdir(parents=True)
blend = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "source": source, "source_sha256_after": sha(ROOT / source["path"]),
           "output": {"path": blend.relative_to(ROOT).as_posix(), "sha256": sha(blend)}, "lift_mm": args.lift_mm, **report}
(out_dir / "hinge-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8", newline=chr(10))
print("CV1_PAULDRON_HINGE " + json.dumps(report))
