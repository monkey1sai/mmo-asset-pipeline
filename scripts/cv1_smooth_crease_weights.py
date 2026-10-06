"""Smooth the skin-weight transition of joint creases on the character V1 body mesh (SM_RO_core only).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_smooth_crease_weights.py -- \
       --rules-in <rules.json> --spec <regions.json> --tag <name> --out-dir <assets dir>
For each region (a parent bone group and a child bone group, e.g. pelvis / upper_leg.L for the left groin) the child
share s = child / (child + parent) is smoothed over the mesh graph inside the transition zone (vertices weighted to
both groups, grown by a few edge rings); the joint total and every other bone's weight stay as they were, and each
group keeps its internal proportions. Coincident split vertices are linked, so they keep equal weights. At most four
influences remain per vertex, renormalised. Body fold shape keys named by the spec are removed with their rules,
because their offsets were computed for the old weights. Other meshes, Basis and topology are untouched.
The input BLEND is not modified; a new BLEND, rules file and report are written; existing outputs are refused.
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
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_pose_rules as rules_math

parser = argparse.ArgumentParser()
for name in ("--rules-in", "--spec", "--tag", "--out-dir"):
    parser.add_argument(name, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir / args.tag).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


spec = json.loads((ROOT / args.spec).read_text(encoding="utf-8"))
rules = json.loads((ROOT / args.rules_in).read_text(encoding="utf-8"))
source = {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath)}
core = bpy.data.objects[spec.get("mesh", "SM_RO_core")]
mesh = core.data
names = [g.name for g in core.vertex_groups]
index_of = {n: i for i, n in enumerate(names)}
weights = [{names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in mesh.vertices]
before = [dict(w) for w in weights]

# Mesh graph with coincident split vertices linked.
neighbours = [set() for _ in mesh.vertices]
for edge in mesh.edges:
    a, b = edge.vertices
    neighbours[a].add(b)
    neighbours[b].add(a)
by_position = {}
for v in mesh.vertices:
    by_position.setdefault(tuple(round(c, 6) for c in v.co), []).append(v.index)
for members in by_position.values():
    for a in members:
        neighbours[a].update(m for m in members if m != a)

report = {"regions": []}
for region in spec["regions"]:
    parent, child = set(region["parent"]), set(region["child"])
    totals = [sum(w.get(b, 0.0) for b in parent | child) for w in weights]
    share = [sum(w.get(b, 0.0) for b in child) / t if t > 1e-6 else None for w, t in zip(weights, totals)]
    seed = {i for i, s in enumerate(share) if s is not None and 0.02 < s < 0.98}
    zone = set(seed)
    for _ in range(region["rings"]):
        zone |= {n for i in zone for n in neighbours[i] if share[n] is not None}
    # Optional local mode: only near named crease points, with the smoothing factor fading to zero at the radius.
    reach = {i: 1.0 for i in zone}
    if region.get("centres"):
        centres = [core.matrix_world.inverted() @ Vector(c) for c in region["centres"]]
        radius = region["radius_m"]
        reach = {}
        for i in zone:
            d = min((mesh.vertices[i].co - c).length for c in centres)
            if d < radius:
                t = 1.0 - d / radius
                reach[i] = t * t * (3 - 2 * t)
        zone = set(reach)
    current = list(share)
    for _ in range(region["iterations"]):
        nxt = list(current)
        for i in zone:
            around = [current[n] for n in neighbours[i] if current[n] is not None]
            if around:
                factor = region["factor"] * reach[i]
                nxt[i] = (1 - factor) * current[i] + factor * sum(around) / len(around)
        current = nxt
    changed, largest = 0, 0.0
    for i in zone:
        if abs(current[i] - share[i]) < 1e-6:
            continue
        w = weights[i]
        total = totals[i]
        old_child = {b: w.get(b, 0.0) for b in child}
        old_parent = {b: w.get(b, 0.0) for b in parent}
        # Keep each group's internal proportions; a group the vertex had no weight on takes its neighbours' mix.
        def mix(group, old):
            mass = sum(old.values())
            if mass > 1e-9:
                return {b: v / mass for b, v in old.items()}
            pooled = {b: 0.0 for b in group}
            for n in neighbours[i]:
                for b in group:
                    pooled[b] += weights[n].get(b, 0.0)
            norm = sum(pooled.values())
            return {b: v / norm for b, v in pooled.items()} if norm > 1e-9 else {sorted(group)[0]: 1.0}
        for b, f in mix(child, old_child).items():
            w[b] = total * current[i] * f
        for b, f in mix(parent, old_parent).items():
            w[b] = total * (1 - current[i]) * f
        changed += 1
        largest = max(largest, abs(current[i] - share[i]))
    report["regions"].append({"name": region["name"], "parent": sorted(parent), "child": sorted(child), "seed_vertices": len(seed), "zone_vertices": len(zone),
                              "local_centres": len(region.get("centres", [])), "radius_m": region.get("radius_m"),
                              "vertices_changed": changed, "max_share_change": round(largest, 4),
                              "rings": region["rings"], "iterations": region["iterations"], "factor": region["factor"]})

# At most four influences, renormalised; write back only what changed.
rewritten = 0
for i, w in enumerate(weights):
    kept = dict(sorted(((b, v) for b, v in w.items() if v > 1e-6), key=lambda kv: -kv[1])[:4])
    norm = sum(kept.values())
    kept = {b: v / norm for b, v in kept.items()}
    if kept == before[i]:
        continue
    if all(abs(kept.get(b, 0.0) - before[i].get(b, 0.0)) < 1e-7 for b in set(kept) | set(before[i])):
        continue
    for b in set(before[i]) - set(kept):
        core.vertex_groups[b].remove([i])
    for b, v in kept.items():
        group = core.vertex_groups.get(b) or core.vertex_groups.new(name=b)
        group.add([i], v, "REPLACE")
    rewritten += 1

# Body fold keys computed for the old weights are dropped with their rules.
dropped = []
prefix = spec.get("drop_shape_key_prefix")
named = set(spec.get("drop_shape_keys", []))
if (prefix or named) and mesh.shape_keys:
    for key in list(mesh.shape_keys.key_blocks[1:]):
        if key.name in named or (prefix and key.name.startswith(prefix)):
            dropped.append(key.name)
            core.shape_key_remove(key)
    gone = {c["driver"] for c in rules["channels"] if c["mesh"] == core.name and c["morph"] in dropped}
    rules["channels"] = [c for c in rules["channels"] if not (c["mesh"] == core.name and c["morph"] in dropped)]
    for driver in gone:
        if not any(c["driver"] == driver for c in rules["channels"]):
            rules["drivers"].pop(driver, None)
rules["id"] = f"ro-swordsman-character-v1-v001-{args.tag}"
rules_math.validate_rules(rules)
out_dir.mkdir(parents=True)
(out_dir / "corrective-rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
blend = out_dir / f"ro_character_v001_{args.tag}.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
summary = {"observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__), "source": source,
           "source_sha256_after": sha(ROOT / source["path"]), "spec": {"path": args.spec, "sha256": sha(ROOT / args.spec)},
           "rules_in": {"path": args.rules_in, "sha256": sha(ROOT / args.rules_in)},
           "output": {"path": blend.relative_to(ROOT).as_posix(), "sha256": sha(blend)}, "mesh": core.name, "vertices_rewritten": rewritten,
           "dropped_shape_keys": dropped, "channels_after": len(rules["channels"]), **report,
           "scope": "Skin weights of the body mesh inside the named crease zones only; Basis, topology, UVs, other meshes and the r010 hand untouched."}
(out_dir / "smooth-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print("CV1_SMOOTH_CREASES " + json.dumps({"rewritten": rewritten, "dropped": len(dropped), "regions": [(r["name"], r["zone_vertices"], r["vertices_changed"], r["max_share_change"]) for r in report["regions"]]}))
