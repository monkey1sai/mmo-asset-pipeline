"""v001 dependency: editable FK humanoid, independent rigid gear, true stress poses."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ro_review_common import camera, render_views
SOURCE = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-fit-tailored/ro_tailored_fit.blend'
SOURCE_SHA = 'eaf01613d30cddbf44a951236aabdbfd3931f309da8e0791ef5924b309993a66'
OUT = ROOT / 'assets/processed/ro-swordsman-combo-r005/v001-rig-seams'
QA = ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-rig-seams'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def segment_distance(point, name):
    head, tail = map(Vector, REST[name])
    axis = tail - head
    along = max(0, min(1, (point - head).dot(axis) / axis.length_squared))
    return (point - head - axis * along).length

def assign(ob, vertex, weights):
    for group in ob.vertex_groups:
        group.remove([vertex.index])
    weights = sorted(((n, w) for n, w in weights.items() if w > 1e-8), key=lambda row:-row[1])[:4]
    total = sum(w for n, w in weights)
    if not total:
        raise RuntimeError('No valid weight')
    for name, weight in weights:
        group = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        group.add([vertex.index], weight / total, 'REPLACE')

def proximity(ob, vertex, names):
    best = sorted([(name, segment_distance(vertex.co, name)) for name in names], key=lambda row:row[1])[:3]
    assign(ob, vertex, {name:1 / max(.012, distance)**4 for name, distance in best})

def world_matrix(head, tail, reference):
    axis = (Vector(tail) - Vector(head)).normalized()
    x = axis.cross(reference)
    if x.length < 1e-6:
        x = axis.cross(Vector((1, 0, 0)))
    x.normalize()
    result = Matrix((x, axis, x.cross(axis).normalized())).transposed().to_4x4()
    result.translation = head
    return result

def solve(head, target, length1, length2, pole):
    requested = Vector(target)
    direction = requested - head
    requested_distance = direction.length
    distance = min(length1 + length2 - .002, max(abs(length1 - length2) + .002, requested_distance))
    direction.normalize()
    target = head + direction * distance
    bend = Vector(pole) - direction * direction.dot(Vector(pole))
    bend.normalize()
    along = (length1**2 - length2**2 + distance**2) / (2 * distance)
    joint = head + direction * along + bend * math.sqrt(max(0, length1**2 - along**2))
    return joint, target, (target - requested).length

if OUT.exists() or QA.exists() or sha(SOURCE) != SOURCE_SHA:
    raise RuntimeError('Preserve input/previous preflight')
start = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/v001-start.json').read_text())
phase = json.loads((ROOT / 'runs/qa/ro-swordsman-combo-r005/phase-accounting.json').read_text())
now = datetime.now(timezone.utc)
trial_elapsed = (now - datetime.fromisoformat(start['started_utc'])).total_seconds()
phase_elapsed = (now - datetime.fromisoformat(phase['baseline_started_utc'])).total_seconds()
if trial_elapsed >= phase['budget']['trial_seconds'] or phase_elapsed >= phase['budget']['total_seconds']:
    raise RuntimeError('Original budget exhausted')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
OUT.mkdir(parents=True)
QA.mkdir(parents=True)
scene = bpy.context.scene
char = bpy.data.collections['COL_Character']
core = bpy.data.objects['SM_RO_core']
vertices_before = len(core.data.vertices)
uv_before = [(round(loop.uv.x,7),round(loop.uv.y,7)) for loop in core.data.uv_layers.active.data]
bm = bmesh.new()
bm.from_mesh(core.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
nonmanifold_after_weld = sum(not edge.is_manifold for edge in bm.edges)
bm.to_mesh(core.data)
bm.free()
core.data.update()
uv_after = [(round(loop.uv.x,7),round(loop.uv.y,7)) for loop in core.data.uv_layers.active.data]
if sorted(uv_before) != sorted(uv_after):
    raise RuntimeError('UV preservation failed')
REST = {'root':((0,0,0),(0,0,.18)), 'pelvis':((0,.06,.89),(0,.06,1.0)),
    'spine_01':((0,.06,1.0),(0,.06,1.16)), 'spine_02':((0,.06,1.16),(0,.08,1.34)),
    'neck':((0,.08,1.34),(0,.07,1.46)), 'head':((0,.07,1.46),(0,.07,1.69))}
PARENTS = {'root':None,'pelvis':'root','spine_01':'pelvis','spine_02':'spine_01','neck':'spine_02','head':'neck'}
GRIP = {'R':Vector((-.435,-.045,.82)), 'L':Vector((.435,-.045,.82))}
for side, sign in [('R',-1),('L',1)]:
    shoulder = (sign*.225,.095,1.32)
    elbow = (sign*.325,.105,1.12)
    wrist = (sign*.408,.012,.935)
    for name, h, t, parent in [
        ('clavicle',(0,.08,1.32),shoulder,'spine_02'),
        ('upper_arm',shoulder,elbow,'clavicle.'+side),
        ('lower_arm',elbow,wrist,'upper_arm.'+side),
        ('hand',wrist,(sign*.437,-.005,.855),'lower_arm.'+side),
        ('upper_leg',(sign*.16,.06,.89),(sign*.185,.06,.50),'pelvis'),
        ('lower_leg',(sign*.185,.06,.50),(sign*.195,.06,.10),'upper_leg.'+side),
        ('foot',(sign*.195,.06,.10),(sign*.195,-.12,.055),'lower_leg.'+side),
        ('toe',(sign*.195,-.12,.055),(sign*.195,-.22,.055),'foot.'+side),
        ('pauldron',shoulder,(sign*.275,.08,1.23),'clavicle.'+side),
        ('coat',(sign*.14,.08,.91),(sign*.27,.13,.46),'pelvis')]:
        REST[name+'.'+side] = (h,t)
        PARENTS[name+'.'+side] = parent
    # Landmarks follow the generated spread across X; old r003 fingers across Y are not reused.
    for index, (x, tip_z) in enumerate([(.380,.788),(.420,.753),(.457,.753),(.490,.795)],1):
        h, mid, tip = (sign*x,-.005,.844), (sign*(x+.004),-.012,(.844+tip_z)/2), (sign*(x+.007),-.014,tip_z)
        first, second = f'finger{index}.{side}_01', f'finger{index}.{side}_02'
        REST[first], REST[second] = (h,mid),(mid,tip)
        PARENTS[first], PARENTS[second] = 'hand.'+side, first
    REST['thumb.'+side+'_01'] = ((sign*.462,-.01,.889),(sign*.484,-.02,.873))
    REST['thumb.'+side+'_02'] = ((sign*.484,-.02,.873),(sign*.505,-.03,.855))
    PARENTS['thumb.'+side+'_01'], PARENTS['thumb.'+side+'_02'] = 'hand.'+side, 'thumb.'+side+'_01'
REST['tabard'] = ((0,-.13,.91),(0,-.18,.46))
REST['sword'] = (tuple(GRIP['R']),tuple(GRIP['R']+Vector((.8,0,0))))
PARENTS['tabard'], PARENTS['sword'] = 'pelvis','hand.R'
data = bpy.data.armatures.new('RO_Batch_Humanoid')
rig = bpy.data.objects.new('ARM_RO_Swordsman',data)
char.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name,(head,tail) in REST.items():
    bone = data.edit_bones.new(name)
    bone.head, bone.tail = head,tail
    if PARENTS[name]:
        bone.parent = data.edit_bones[PARENTS[name]]
    if name == 'root':
        bone.use_deform = False
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True
rig['control_method'] = 'Editable FK; geometric two-bone IK used only to author stress poses. No IK/FK switch is claimed.'
heat_warning = None
GEAR_BONES = {name for name in REST if name.startswith(('coat.', 'pauldron.')) or name in {'tabard','sword'}}
for name in GEAR_BONES:
    data.bones[name].use_deform = False
bpy.ops.object.select_all(action='DESELECT')
core.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except RuntimeError as error:
    heat_warning = str(error)
for name in GEAR_BONES:
    data.bones[name].use_deform = True
modifier = next((m for m in core.modifiers if m.type=='ARMATURE'),None) or core.modifiers.new('Skin','ARMATURE')
modifier.object = rig
modifier.use_deform_preserve_volume = False
core.parent = rig
for vertex in core.data.vertices:
    x,y,z = vertex.co
    side = 'L' if x >= 0 else 'R'
    if z > 1.46:
        assign(core,vertex,{'head':1})
    elif z < .35:
        assign(core,vertex,{'foot.'+side:1})
    elif z < .94 and abs(x) > .34:
        if z > .895:
            proximity(core,vertex,['hand.'+side,'lower_arm.'+side])
        elif z > .835 and abs(x) > .462:
            proximity(core,vertex,['hand.'+side,'thumb.'+side+'_01','thumb.'+side+'_02'])
        elif z < .852:
            names = ['hand.'+side]+[f'finger{i}.{side}_{joint}' for i in range(1,5) for joint in ('01','02')]
            proximity(core,vertex,names)
        else:
            assign(core,vertex,{'hand.'+side:1})
    elif .80 < z < .99 and abs(x) < .29:
        assign(core,vertex,{'pelvis':1})
    else:
        if abs(x) > .23 and z > .93:
            names = ['clavicle.'+side,'upper_arm.'+side,'lower_arm.'+side,'hand.'+side]
            if z > 1.10 and abs(x) < .30:
                names += ['spine_01','spine_02']
        elif z < .80:
            names = ['pelvis','upper_leg.'+side,'lower_leg.'+side]
        else:
            names = ['pelvis','spine_01','spine_02','neck','head']
            if abs(x) > .12 and z > 1.27:
                names.append('clavicle.'+side)
            if abs(x) > .12 and z > 1.09:
                names.append('upper_arm.'+side)
        existing = {core.vertex_groups[g.group].name:g.weight for g in vertex.groups
                    if core.vertex_groups[g.group].name in names and g.weight > 1e-8}
        if existing:
            assign(core,vertex,existing)
        else:
            proximity(core,vertex,names)
for ob in list(char.objects):
    if ob.type != 'MESH' or ob == core:
        continue
    mod = ob.modifiers.new('Skin','ARMATURE')
    mod.object = rig
    mod.use_deform_preserve_volume = False
    ob.parent = rig
    if ob.name == 'SM_RO_coat':
        for vertex in ob.data.vertices:
            z = vertex.co.z
            if z > .85:
                assign(ob,vertex,{'pelvis':1})
            else:
                blend = min(1,max(0,(.86-z)/.22))
                side = 'L' if vertex.co.x >= 0 else 'R'
                front = vertex.co.y < -.05 and abs(vertex.co.x) < .13
                assign(ob,vertex,{'pelvis':1-blend, 'tabard' if front else 'coat.'+side:blend})
    else:
        bone = 'spine_02' if 'cuirass' in ob.name else 'sword' if 'sword' in ob.name else ('pauldron.' if 'pauldron' in ob.name else 'lower_arm.') + ob.name[-1]
        for vertex in ob.data.vertices:
            assign(ob,vertex,{bone:1})

# Move real generated sword to rest hand's cylindrical grip frame. Keep its topology/maps.
sword = bpy.data.objects['SM_RO_sword']
native_axis = Vector((-.2,-.6,-.775)).normalized()
rotation = native_axis.rotation_difference(Vector((1,0,0))).to_matrix()
native_grip = Vector((-.435,-.105,.86))
for vertex in sword.data.vertices:
    vertex.co = GRIP['R'] + rotation @ (vertex.co-native_grip)
sword.data.update()

pose_reports = []
def pose(frame, pose_name, hip_height, grip_center, sword_direction, curl=.95):
    scene.frame_set(frame)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    shift = Vector((0,0,hip_height-.89))
    worlds = {}
    for name in ['root','pelvis','spine_01','spine_02','neck','head']:
        worlds[name] = data.bones[name].matrix_local.copy()
        if name != 'root':
            worlds[name].translation += shift
    axis = Vector(sword_direction).normalized()
    y = Vector((0,1,0)) - axis * axis.y
    if y.length < .01:
        y = Vector((0,0,1)) - axis * axis.z
    y.normalize()
    requested_grip = Vector(grip_center)
    feasible_grip = requested_grip.copy()
    reachable_balls = []
    for side,sign in [('R',-1),('L',1)]:
        yy = y if side == 'R' else -y
        rotation = Matrix((axis,yy,axis.cross(yy))).transposed()
        shoulder = Vector(REST['upper_arm.'+side][0])+shift
        reach = (Vector(REST['upper_arm.'+side][1])-Vector(REST['upper_arm.'+side][0])).length + (Vector(REST['lower_arm.'+side][1])-Vector(REST['lower_arm.'+side][0])).length - .004
        ball_center = shoulder + rotation @ (GRIP[side]-Vector(REST['hand.'+side][0])) + (axis*.11 if side=='L' else Vector((0,0,0)))
        reachable_balls.append((ball_center,reach))
    for _ in range(60):
        for center,radius in reachable_balls:
            delta = feasible_grip-center
            if delta.length > radius:
                feasible_grip = center+delta.normalized()*radius
    if any((feasible_grip-center).length > radius+.00001 for center,radius in reachable_balls):
        raise RuntimeError('No jointly reachable grip')
    if (feasible_grip-requested_grip).length > .10:
        raise RuntimeError('Feasible grip changes the intended pose too far')
    residuals = {}
    for side, sign in [('R',-1),('L',1)]:
        yy = y if side == 'R' else -y
        rotation = Matrix((axis,yy,axis.cross(yy))).transposed()
        grip = feasible_grip if side == 'R' else feasible_grip-axis*.11
        wrist_target = grip - rotation @ (GRIP[side]-Vector(REST['hand.'+side][0]))
        shoulder = Vector(REST['upper_arm.'+side][0])+shift
        length1 = (Vector(REST['upper_arm.'+side][1])-Vector(REST['upper_arm.'+side][0])).length
        length2 = (Vector(REST['lower_arm.'+side][1])-Vector(REST['lower_arm.'+side][0])).length
        elbow,wrist,residual = solve(shoulder,wrist_target,length1,length2,(sign*.7,-.5,.2))
        residuals[side] = residual
        worlds['clavicle.'+side] = data.bones['clavicle.'+side].matrix_local.copy()
        worlds['clavicle.'+side].translation += shift
        for bone,h,t in [('upper_arm',shoulder,elbow),('lower_arm',elbow,wrist)]:
            reference = rotation @ data.bones[bone+'.'+side].matrix_local.to_3x3().col[2]
            worlds[bone+'.'+side] = world_matrix(h,t,reference)
        hand = (rotation @ data.bones['hand.'+side].matrix_local.to_3x3()).to_4x4()
        hand.translation = wrist
        worlds['hand.'+side] = hand
        thigh = Vector(REST['upper_leg.'+side][0])+shift
        ankle = Vector(REST['lower_leg.'+side][1])
        knee,actual_ankle,residuals['foot.'+side] = solve(thigh,ankle,.391,.400,(0,-1,0))
        worlds['upper_leg.'+side] = world_matrix(thigh,knee,data.bones['upper_leg.'+side].matrix_local.to_3x3().col[2])
        worlds['lower_leg.'+side] = world_matrix(knee,actual_ankle,data.bones['lower_leg.'+side].matrix_local.to_3x3().col[2])
        for bone in ['foot','toe']:
            worlds[bone+'.'+side] = data.bones[bone+'.'+side].matrix_local.copy()
        shoulder_rotation = worlds['upper_arm.'+side].to_quaternion() @ data.bones['upper_arm.'+side].matrix_local.to_quaternion().inverted()
        pauldron = (shoulder_rotation.slerp(Matrix.Identity(3).to_quaternion(),.45).to_matrix() @ data.bones['pauldron.'+side].matrix_local.to_3x3()).to_4x4()
        pauldron.translation = shoulder
        worlds['pauldron.'+side] = pauldron
        coat = data.bones['coat.'+side].matrix_local.copy()
        coat.translation += shift
        coat_rotation = Matrix.Rotation(min(.85,max(0,(.89-hip_height)*3)),3,'X')
        coat = (coat_rotation @ coat.to_3x3()).to_4x4()
        coat.translation = Vector(REST['coat.'+side][0])+shift
        worlds['coat.'+side] = coat
    worlds['tabard'] = data.bones['tabard'].matrix_local.copy()
    worlds['tabard'].translation += shift
    for bone in REST:
        if bone not in worlds:
            continue
        parent = PARENTS[bone]
        rest = data.bones[bone].matrix_local
        rig.pose.bones[bone].matrix_basis = rest.inverted() @ data.bones[parent].matrix_local @ worlds[parent].inverted() @ worlds[bone] if parent else rest.inverted() @ worlds[bone]
    bpy.context.view_layer.update()
    for side in ['R','L']:
        for index in range(1,5):
            for joint,angle in [('01',-curl),('02',-1.20*curl)]:
                pb = rig.pose.bones[f'finger{index}.{side}_{joint}']
                rest = data.bones[pb.name].matrix_local.to_3x3()
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = (rest.inverted() @ Matrix.Rotation(angle,3,'X') @ rest).to_quaternion()
    bpy.context.view_layer.update()
    return {'pose':pose_name,'hip_height_m':hip_height,'requested_grip':list(grip_center),
            'feasible_grip':list(feasible_grip),'grip_position_adjustment_m':(feasible_grip-requested_grip).length,
            'wrist_and_foot_target_residual_m':residuals,
            'acceptance':'Unreviewed; numerical reach is not surface grip acceptance'}

data.pose_position = 'REST'
render_views(QA / 'bind')
data.pose_position = 'POSE'
scene.render.resolution_x = scene.render.resolution_y = 960
for frame,(name,hip,grip,axis) in enumerate([
    ('overhead',.89,(0,-.16,1.50),(0,-.15,.9887)),
    ('deep-crouch',.70,(0,-.22,1.02),(0,-.45,.893)),
    ('downslash',.82,(-.08,-.20,1.00),(0,-.85,-.5268))],1):
    pose_reports.append(pose(frame,name,hip,grip,axis))
    for view in ['front','side','back','three-quarter']:
        camera(view)
        folder = QA / 'stress' / name
        folder.mkdir(parents=True,exist_ok=True)
        scene.render.filepath = str(folder / (view+'.png'))
        bpy.ops.render.render(write_still=True)
    target = rig.pose.bones['hand.R'].head.copy()
    camera((tuple(target+Vector((.35,-1,.2))),tuple(target),.28))
    scene.render.filepath = str(folder / 'grip-close.png')
    bpy.ops.render.render(write_still=True)
pose(1,'review-pose',.89,(0,-.20,1.10),(0,-.1,.995))
render_views(QA)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ro_rig_preflight.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in char.objects:
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(OUT / 'ro_rig_preflight.glb'),export_format='GLB',use_selection=True,
                          export_animations=False,export_yup=True,export_skins=True)
invalid_weights = []
for ob in char.objects:
    if ob.type != 'MESH':
        continue
    for vertex in ob.data.vertices:
        weights = [g.weight for g in vertex.groups if g.weight > 1e-8]
        if not weights or len(weights)>4 or abs(sum(weights)-1)>.0001:
            invalid_weights.append([ob.name,vertex.index])
triangles = sum(len(p.vertices)-2 for ob in char.objects if ob.type=='MESH' for p in ob.data.polygons)
report = {'candidate':'v001','stage':'rig preflight; not full continuous animation',
    'known_failure_repaired':'Gear bones excluded from core bone heat and all core assignment; downslash grip moved to shared reachable volume. Actual visual acceptance remains separate.',
    'source_seam_vertices_before':vertices_before,'source_seam_vertices_after':len(core.data.vertices),
    'uv_loop_values_preserved':True,'nonmanifold_edges_after_position_weld':nonmanifold_after_weld,
    'seam_failure_evidence':'269 coincident core vertex groups in prior output had different skin weights; source positions welded before heat. Original masters preserved.',
    'source_sha256':SOURCE_SHA,'source_preserved':sha(SOURCE)==SOURCE_SHA,
    'bone_heat_warning':heat_warning,'bones':len(data.bones),'triangles':triangles,
    'invalid_weights':invalid_weights,'weight_validation_pass':not invalid_weights,
    'linear_skinning':True,'fk_editable':True,'ik_fk_switch':False,
    'real_stress_poses':pose_reports,'animation_channels':0,'effects':False,
    'elapsed_trial_seconds':trial_elapsed,'elapsed_phase_seconds':phase_elapsed,
    'artifacts':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in OUT.iterdir()],
    'acceptance':'Pending actual views/grip/deformation and fresh GLB reimport; no art/technical PASS'}
(QA / 'preflight.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('RO_RIG_PREFLIGHT '+json.dumps(report))
