"""v001: fit measured generated glove, own-branch rig, immutable contact masks."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import math
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ro_core_rig import assign, curl_digits, pose
from ro_review_common import camera, render_views
from ro_hand_gate import contacts

QA = ROOT / "runs/qa/ro-swordsman-combo-r006/v001-generated-glove"
OUT = ROOT / "assets/processed/ro-swordsman-combo-r006/v001-generated-glove"
baseline = ROOT / "assets/processed/ro-swordsman-combo-r006/baseline/ro_hand_baseline.blend"
source = ROOT / "assets/processed/ro-swordsman-combo-r006/hand-source/right_glove_source.blend"
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha == "2255ad32efc4a39ce79910d90e9409943b5f7bb507d736540e9efcd77c45add3"
assert not QA.exists() and not OUT.exists()
start = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r006/v001-start.json").read_text())
clock = json.loads((ROOT / "runs/qa/ro-swordsman-combo-r006/phase-start.json").read_text())
def guard():
    now = datetime.now(timezone.utc)
    assert (now-datetime.fromisoformat(start["started_utc"])).total_seconds() < clock["budget"]["trial_seconds"]
    assert (now-datetime.fromisoformat(clock["baseline_started_utc"])).total_seconds() < clock["budget"]["total_seconds"]
guard()
bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False, use_scripts=False)
rig = bpy.data.objects["ARM_RO_Swordsman"]
core = bpy.data.objects["SM_RO_core"]
sword = bpy.data.objects["SM_RO_sword"]
state = json.loads(rig["state_json"])
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
with bpy.data.libraries.load(str(source), link=False) as (src, dst):
    dst.objects = ["SM_RO_RightGlove_Source"]
glove = dst.objects[0]
bpy.data.collections["COL_Character"].objects.link(glove)
glove.name = "SM_RO_glove.R"

# Logical weld keeps per-corner UVs, unlike nearest cross-island UV transfer.
bm = bmesh.new(); bm.from_mesh(glove.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
bm.to_mesh(glove.data); bm.free(); glove.data.update()
local_points = [v.co.copy() for v in glove.data.vertices]
width = Vector(state["hand_frames"]["R"]["width"])
front = Vector(state["hand_frames"]["R"]["front"])
down = Vector(state["hand_frames"]["R"]["down"])
wrist = Vector(state["rest"]["hand.R"][0])
source_wrist = Vector((-.007,-.004,.026))
rotation = Matrix((-width,-front,down)).transposed()
assert abs(rotation.determinant()-1) < 1e-5
def transform(p):
    return wrist + rotation @ (Vector(p)-source_wrist)
for v,p in zip(glove.data.vertices,local_points):
    v.co = transform(p)
glove.data.update()

# Centers from actual rendered branch positions and edge-plane section probe.
source_digits = {
    "finger1": [(-.052,.011,.099),(-.056,.005,.160)],
    "finger2": [(-.030,.019,.108),(-.035,.014,.181)],
    "finger3": [(-.012,.022,.110),(-.015,.019,.194)],
    "finger4": [(.010,.021,.106),(.009,.019,.181)],
    "thumb": [(.025,-.006,.060),(.060,-.003,.130)],
}
source_bones = {}
for name,(h,t) in source_digits.items():
    h,t = Vector(h),Vector(t)
    levels = [0,.40,.72,1] if name != "thumb" else [0,.52,1]
    for j,(a,b) in enumerate(zip(levels,levels[1:]),1):
        n = f"{name}.R_{j:02}"
        source_bones[n] = (h.lerp(t,a),h.lerp(t,b))
        state["rest"][n] = (list(transform(source_bones[n][0])),list(transform(source_bones[n][1])))
        state["parents"][n] = "hand.R" if j==1 else f"{name}.R_{j-1:02}"
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for n,seg in source_bones.items():
    bone = rig.data.edit_bones.get(n) or rig.data.edit_bones.new(n)
    bone.head,bone.tail = map(transform,seg)
    bone.parent = rig.data.edit_bones[state["parents"][n]]
    bone.use_connect = n.endswith(("_02","_03"))
    bone.use_deform = True
bpy.ops.object.mode_set(mode="OBJECT")
state.setdefault("finger_joint_count",{})["R"] = 3
state["measurements"]["R"] = {"knuckles":[list(transform(source_digits[f"finger{i}"][0])) for i in range(1,5)],
    "tips":[list(transform(source_digits[f"finger{i}"][1])) for i in range(1,5)],
    "thumb_tip":list(transform(source_digits["thumb"][1])),"method":"actual source sections and manual anatomical review"}
mean_knuckle = sum((transform(source_digits[f"finger{i}"][0]) for i in range(1,5)),Vector())/4
old_grip = Vector(state["grips"]["R"])
new_grip = mean_knuckle + front*.030 + down*.020
state["grips"]["R"] = list(new_grip)
# Sword retains shape, UV and native width axis; only its fitting offset changes.
for v in sword.data.vertices:
    v.co += new_grip-old_grip
state["rest"]["sword"] = (list(new_grip),list(new_grip-width*.8))
bpy.ops.object.mode_set(mode="EDIT")
rig.data.edit_bones["sword"].head = new_grip
rig.data.edit_bones["sword"].tail = new_grip-width*.8
bpy.ops.object.mode_set(mode="OBJECT")
ordered = {}
while len(ordered) < len(state["rest"]):
    for n,seg in state["rest"].items():
        if n not in ordered and (state["parents"][n] is None or state["parents"][n] in ordered):
            ordered[n] = seg
state["rest"] = ordered

# Deliberately frozen source-space branch masks, independent of posed proximity.
semantic = {}
pads = {n:[] for n in source_digits}
for v,p in zip(glove.data.vertices,local_points):
    branch = None
    if p.x > .027 and p.z > .070:
        branch = "thumb"
    elif p.z > .087:
        i = 1 if p.x < -.043 else 2 if p.x < -.024 else 3 if p.x < -.001 else 4 if p.x < .027 else None
        if i:
            branch = f"finger{i}"
    weights = {"hand.R":1.0}
    if branch:
        h,t = map(Vector,source_digits[branch]); d = t-h
        s = (p-h).dot(d)/d.length_squared
        # Smooth hand/root blend and adjacent joints; sibling digits prohibited.
        digit = max(0,min(1,(s+.13)/.26))
        w2 = max(0,min(1,(s-.31)/.18))
        w3 = max(0,min(1,(s-.63)/.18)) if branch != "thumb" else 0
        if branch == "thumb":
            w2 = max(0,min(1,(s-.43)/.18))
        weights = {"hand.R":1-digit,f"{branch}.R_01":digit*(1-w2),
            f"{branch}.R_02":digit*w2*(1-w3)}
        if branch != "thumb":
            weights[f"{branch}.R_03"] = digit*w2*w3
        semantic[v.index] = {"branch":branch,"axial_s":s}
        if .22 < s < .96 and v.normal.dot(front) > .2:
            pads[branch].append(v.index)
    assign(glove,v,weights)
assert all(len(ids)>=3 for ids in pads.values()),pads
glove.parent = rig
glove.matrix_parent_inverse = Matrix.Identity(4)
mod = glove.modifiers.new("Skin","ARMATURE"); mod.object = rig
mod.use_deform_preserve_volume = False
rig["state_json"] = json.dumps(state)
glove["fixed_pad_indices"] = json.dumps(pads)

# A separate cuff overlays a deliberately open forearm boundary, no generic fan cap.
core_before = len(core.data.vertices)
bm = bmesh.new(); bm.from_mesh(core.data)
geom = [v for v in bm.verts if v.co.x<-.34 and v.co.z<.98]
geom += [e for e in bm.edges if all(v.co.x<-.34 and v.co.z<.98 for v in e.verts)]
geom += [f for f in bm.faces if all(v.co.x<-.34 and v.co.z<.98 for v in f.verts)]
bmesh.ops.bisect_plane(bm,geom=geom,dist=1e-7,plane_co=Vector((0,0,.923)),plane_no=Vector((0,0,1)),clear_inner=True,clear_outer=False)
discard = [v for v in bm.verts if v.co.x<-.34 and v.co.z<.923-1e-6]
bmesh.ops.delete(bm,geom=discard,context="VERTS")
seam_count = sum(e.is_boundary and all(v.co.x<-.34 and abs(v.co.z-.923)<1e-5 for v in e.verts) for e in bm.edges)
assert 10 <= seam_count <= 60,seam_count
bm.to_mesh(core.data); bm.free(); core.data.update()
OUT.mkdir(parents=True); QA.mkdir(parents=True)
def save_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
save_json(QA/"anatomy-and-masks.json",{"source_sha256":source_sha,"source_wrist":list(source_wrist),
    "source_digits":source_digits,"rotation":list(map(list,rotation)),"world_digits":state["measurements"]["R"],
    "semantic":semantic,"fixed_pad_indices":pads,"branch_order":"source little-to-index; IDs retain branch1..4 fixture convention"})
events = []
def reset():
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
def render_hand(folder):
    folder.mkdir(parents=True,exist_ok=False)
    target = rig.pose.bones["hand.R"].head.lerp(rig.pose.bones["hand.R"].tail,.6)
    for n,offset in [("palm",(.25,-1,.12)),("side",(1,.1,.1)),("back",(-.25,1,.1)),("wrist",(0,-.2,.9))]:
        camera((tuple(target+Vector(offset)),tuple(target),.29))
        bpy.context.scene.render.filepath = str(folder/(n+".png"))
        bpy.ops.render.render(write_still=True)
def event(label,params):
    guard()
    result = contacts(glove,sword,rig,pads,label,params)
    result["event_kind"] = "fixture_readback"
    result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    events.append(result)
    save_json(QA/"fixture-events.json",events)
    return result
reset(); render_views(QA/"whole-open")
render_hand(QA/"open-R")
event("open",{"curl":0,"fixture":"identity FK"})
curl_digits(rig,state,"R",.30); render_hand(QA/"small-curl-R")
event("small-curl",{"curl":.30,"fixture":"identity FK with .30rad"})
reset()
posed = pose(rig,state,.89,(-.08,-.29,1.12),(0,-.1,.995),curl=.85,two_hands=False)
render_hand(QA/"grip-R")
event("single-grip",{"curl":.85,"fixture_pose":posed})
reset()
for image in bpy.data.images:
    if image.type=="IMAGE" and image.size[0] and not image.packed_file:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"ro_generated_glove.blend"))
objects = [o for o in bpy.data.collections["COL_Character"].objects if o.type=="MESH"]
triangles = 0
for ob in objects:
    ob.data.calc_loop_triangles(); triangles += len(ob.data.loop_triangles)
save_json(QA/"prototype.json",{"trial":"v001","finished_utc":datetime.now(timezone.utc).isoformat(),
    "source_preserved":hashlib.sha256(source.read_bytes()).hexdigest()==source_sha,
    "source":str(source.relative_to(ROOT)),"source_sha256":source_sha,
    "whole_triangles":triangles,"triangle_limit_pass":triangles<=60000,
    "glove_triangles":len(glove.data.loop_triangles),"bones":len(rig.data.bones),
    "cut_seam_edges":seam_count,"removed_core_vertices":core_before-len(core.data.vertices),
    "grip_surface_gate":events[-1]["surface_gate_pass"],"source_uv_policy":"Original per-corner UV preserved through weld and fitting",
    "cuff_clearance_and_art_acceptance":"pending actual close-up review",
    "full_animation_accepted":False,"delivered":False,
    "artifact":{"path":str((OUT/"ro_generated_glove.blend").relative_to(ROOT)),
                "sha256":hashlib.sha256((OUT/"ro_generated_glove.blend").read_bytes()).hexdigest()}})
print("RO_GENERATED_GLOVE " + json.dumps({"whole_triangles":triangles,"grip_gate":events[-1]["surface_gate_pass"],
    "maximum_penetration_m":events[-1]["maximum_penetration_m"],"crossings":events[-1]["transverse_crossings_count"],
    "pad_contacts":events[-1]["pad_contacts"]}))
