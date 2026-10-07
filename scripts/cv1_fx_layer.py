"""Separate skill-effects layer for a character V1 clip (Blender side): procedural meshes animated by object transforms, exported
as their own GLB so the game can switch them off (request r6 style.must_have "可關閉的斬擊、怒爆火焰、霸體金色光效", parts[effects]).

Run: blender -b --factory-startup --disable-autoexec <foundation.blend> --python scripts/cv1_fx_layer.py -- \
       --clip-blend <action .blend> --interaction <interaction.json> --out-dir <new dir> [--preview-frames 112,180,230,275]
The clip's action is linked onto the armature only to read the sword path (grip and tip per frame); nothing of the character
is exported or saved. Effects, each visible only inside its window (scale 0 outside, keyed on whole frames, LINEAR):
- FX_BashArc: ribbon swept by the blade (grip to tip) over the frames before the bash_slash event, fading after it;
- FX_MagnumGroundRing + FX_MagnumFlame00..11: a ground ring under the sword tip at magnum_impact, expanding, and twelve flame
  cones around it rising and shrinking;
- FX_EndureHaloFront/Side + FX_EndureGround: two crossed translucent planes around the character and a ground disc from
  endure_start, pulsing until the victory event;
- FX_VictorySparkle00..07: eight small stars around the raised sword tip at the victory event.
Writes <out-dir>/ro_skill_effects.glb and fx-report.json (objects, triangles, windows, SHA-256 of the GLB and inputs), and
optional preview renders with the character for the review sheet (not the evaluation protocol views).
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
for name in ("--clip-blend", "--interaction", "--out-dir"):
    parser.add_argument(name, required=True)
parser.add_argument("--preview-frames", default="")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
out_dir = (ROOT / args.out_dir).resolve()
if out_dir.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out_dir}")
config = json.loads((ROOT / args.interaction).read_text(encoding="utf-8"))
events = {e["name"]: e["frame"] for e in config["events"]}
for needed in ("bash_slash", "magnum_impact", "endure_start", "victory"):
    if needed not in events:
        raise SystemExit(f"EVENT_MISSING {needed}")
fps, frames = config["fps"], config["frames"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---- sword path from the clip ----
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(c.type == "MESH" for c in o.children))
with bpy.data.libraries.load(str(ROOT / args.clip_blend), link=False) as (source, target):
    if config["clip"] not in source.actions:
        raise SystemExit(f"ACTION_NOT_IN_FILE {config['clip']}")
    target.actions = [config["clip"]]
arm.animation_data_create()
arm.animation_data.action = target.actions[0]
sword_obj = bpy.data.objects["SM_RO_sword"]
sword_bone = arm.pose.bones["sword"]
# Blade length: the sword mesh's extent along the bone axis from the bone head (rest).
rest_head, rest_axis = arm.data.bones["sword"].head_local, (arm.data.bones["sword"].tail_local - arm.data.bones["sword"].head_local).normalized()
extent = max((sword_obj.matrix_world @ v.co - arm.matrix_world @ rest_head).dot(rest_axis) for v in sword_obj.data.vertices)
path = {}
scene = bpy.context.scene
for f in range(frames):
    scene.frame_set(f)
    head = arm.matrix_world @ sword_bone.head
    axis = (arm.matrix_world.to_3x3() @ (sword_bone.tail - sword_bone.head)).normalized()
    path[f] = (head.copy(), (head + axis * extent).copy())
scene.frame_set(0)

# ---- helpers ----
fx_collection = bpy.data.collections.new("FX")
scene.collection.children.link(fx_collection)
made = []


def material(name, color, strength, alpha):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Alpha"].default_value = alpha
    mat.blend_method = "BLEND"
    return mat


MAT = {"slash": material("FX_SlashIvory", (1.0, 0.95, 0.8), 2.0, 0.55), "fire": material("FX_FireOrange", (1.0, 0.45, 0.08), 4.0, 0.8),
       "gold": material("FX_FireGold", (1.0, 0.8, 0.2), 4.0, 0.8), "endure": material("FX_EndureGold", (1.0, 0.85, 0.35), 1.2, 0.3)}


def new_object(name, verts, faces, mat, origin):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(v) - Vector(origin)) for v in verts]
    bm.verts.ensure_lookup_table()
    for face in faces:
        try:
            bm.faces.new([vs[i] for i in face])
        except ValueError:
            pass
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(origin)
    obj.data.materials.append(mat)
    fx_collection.objects.link(obj)
    made.append(obj)
    return obj


def key_scale(obj, keys):
    """[(frame, scale)] on whole frames, LINEAR; scale 0 hides the object outside its window."""
    for f, s in keys:
        obj.scale = (s, s, s)
        obj.keyframe_insert("scale", frame=f)
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def ring(centre, radius, height, segments=24):
    return [(centre[0] + radius * math.cos(2 * math.pi * i / segments), centre[1] + radius * math.sin(2 * math.pi * i / segments), centre[2] + height) for i in range(segments)]


# ---- 1. bash slash arc: ribbon between grip and tip over the 14 frames before the slash event ----
slash = events["bash_slash"]
arc_frames = list(range(slash - 14, slash + 1))
verts, faces = [], []
for i, f in enumerate(arc_frames):
    grip, tip = path[f]
    mid = grip.lerp(tip, 0.55)  # the ribbon follows the outer part of the blade
    verts += [tuple(mid), tuple(tip)]
    if i:
        a = 2 * (i - 1)
        faces += [(a, a + 1, a + 3), (a, a + 3, a + 2)]
arc = new_object("FX_BashArc", verts, faces, MAT["slash"], path[slash][1])
key_scale(arc, [(slash - 15, 0.0), (slash - 14, 0.0), (slash - 8, 1.0), (slash + 8, 1.0), (slash + 14, 0.0)])

# ---- 2. magnum: ground ring under the tip at impact + twelve flame cones ----
impact = events["magnum_impact"]
tip_x, tip_y = path[impact][1].x, path[impact][1].y
ring_centre = (tip_x, tip_y, 0.0)
outer, inner = ring(ring_centre, 0.9, 0.01), ring(ring_centre, 0.6, 0.01)
rv = outer + inner
rf = [(i, (i + 1) % 24, 24 + (i + 1) % 24, 24 + i) for i in range(24)]
ground_ring = new_object("FX_MagnumGroundRing", rv, rf, MAT["gold"], ring_centre)
key_scale(ground_ring, [(impact - 1, 0.0), (impact, 0.1), (impact + 6, 1.0), (impact + 22, 1.3), (impact + 28, 0.0)])
for i in range(12):
    angle = 2 * math.pi * i / 12
    base = (tip_x + 0.8 * math.cos(angle), tip_y + 0.8 * math.sin(angle), 0.0)
    cone_v = ring(base, 0.12, 0.0, 8) + [(base[0], base[1], 0.55)]
    cone_f = [(j, (j + 1) % 8, 8) for j in range(8)] + [tuple(range(8))]
    flame = new_object(f"FX_MagnumFlame{i:02d}", cone_v, cone_f, MAT["fire"] if i % 2 else MAT["gold"], base)
    d = i % 3
    key_scale(flame, [(impact + d, 0.0), (impact + d + 4, 1.0), (impact + d + 14, 0.8), (impact + d + 26, 0.0)])

# ---- 3. endure: two crossed planes around the character and a ground disc ----
start, victory = events["endure_start"], events["victory"]
scene.frame_set(start)
centre_xy = (arm.matrix_world @ arm.pose.bones["pelvis"].head)
scene.frame_set(0)
cx, cy = centre_xy.x, centre_xy.y
for name, (dx, dy) in (("FX_EndureHaloFront", (1.0, 0.0)), ("FX_EndureHaloSide", (0.0, 1.0))):
    w, h = 0.9, 2.1
    pv = [(cx - dx * w, cy - dy * w, 0.02), (cx + dx * w, cy + dy * w, 0.02), (cx + dx * w, cy + dy * w, h), (cx - dx * w, cy - dy * w, h)]
    halo = new_object(name, pv, [(0, 1, 2, 3)], MAT["endure"], (cx, cy, 0.0))
    key_scale(halo, [(start - 1, 0.0), (start, 0.2), (start + 8, 1.0), (start + 20, 0.92), (start + 32, 1.0), (victory - 24, 1.0), (victory - 10, 0.0)])
disc = ring((cx, cy, 0.0), 1.0, 0.005, 32)
ground = new_object("FX_EndureGround", disc + [(cx, cy, 0.005)], [(i, (i + 1) % 32, 32) for i in range(32)], MAT["endure"], (cx, cy, 0.0))
key_scale(ground, [(start - 1, 0.0), (start, 0.2), (start + 8, 1.0), (victory - 24, 1.0), (victory - 10, 0.0)])

# ---- 4. victory sparkles around the raised tip ----
vt = path[victory][1]
for i in range(8):
    angle = 2 * math.pi * i / 8
    c = (vt.x + 0.28 * math.cos(angle), vt.y + 0.08 * math.sin(angle), vt.z + 0.28 * math.sin(angle))
    r = 0.10
    star_v = [(c[0] + r, c[1], c[2]), (c[0], c[1], c[2] + r), (c[0] - r, c[1], c[2]), (c[0], c[1], c[2] - r), (c[0], c[1] + 0.03, c[2]), (c[0], c[1] - 0.03, c[2])]
    star_f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)]
    star = new_object(f"FX_VictorySparkle{i:02d}", star_v, star_f, MAT["slash"], c)
    key_scale(star, [(victory - 1 + i, 0.0), (victory + i, 0.0), (victory + i + 4, 1.0), (victory + i + 14, 0.0)])

# ---- export the effects alone ----
out_dir.mkdir(parents=True)
for obj in bpy.data.objects:
    obj.select_set(obj in made)
bpy.context.view_layer.objects.active = made[0]
glb = out_dir / "ro_skill_effects.glb"
scene.frame_start, scene.frame_end = 0, frames - 1
bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True, export_animations=True, export_apply=True,
                          export_skins=False, export_morph=False, export_yup=True, export_cameras=False, export_lights=False,
                          export_frame_range=True, export_force_sampling=False, export_nla_strips=False)
tris = sum(len(p.vertices) - 2 for o in made for p in o.data.polygons)
report = {"observed_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string, "script_sha256": sha(__file__),
          "inputs": {"clip_blend": {"path": args.clip_blend, "sha256": sha(ROOT / args.clip_blend)}, "interaction": {"path": args.interaction, "sha256": sha(ROOT / args.interaction)},
                     "foundation": {"path": Path(bpy.data.filepath).resolve().relative_to(ROOT).as_posix(), "sha256": sha(bpy.data.filepath), "saved": False}},
          "events": events, "objects": [o.name for o in made], "triangles": tris, "blade_extent_m": round(extent, 4),
          "windows": {"bash_arc": [slash - 14, slash + 14], "magnum": [impact, impact + 28], "endure": [start, victory - 10], "victory": [victory, victory + 21]},
          "output": {"path": glb.relative_to(ROOT).as_posix(), "bytes": glb.stat().st_size, "sha256": sha(glb)},
          "scope": "Effects layer only: separate GLB, object scale animation, no skinning; switching it off leaves the character clip untouched. "
                   "Not a measurement of the character; the clip check runs without effects."}
(out_dir / "fx-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
previews = [int(x) for x in args.preview_frames.split(",") if x]
if previews:
    (out_dir / "preview").mkdir()
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.film_transparent = False
    cam_data = bpy.data.cameras.new("fx_cam")
    cam = bpy.data.objects.new("fx_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = Vector((-2.8, -3.2, 1.6))
    look = Vector((0.0, 0.0, 0.9)) - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    light = bpy.data.objects.new("fx_key", bpy.data.lights.new("fx_key", "SUN"))
    light.data.energy = 3.0
    light.rotation_euler = (math.radians(50), 0.0, math.radians(-30))
    scene.collection.objects.link(light)
    for f in previews:
        scene.frame_set(f)
        scene.render.filepath = str(out_dir / "preview" / f"f{f:03d}-fx.png")
        bpy.ops.render.render(write_still=True)
print("CV1_FX_LAYER " + json.dumps({"objects": len(made), "triangles": tris, "glb": report["output"]["path"], "previews": previews}))
