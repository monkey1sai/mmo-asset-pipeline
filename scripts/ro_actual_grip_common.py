"""Fixed source pad contact against the actual unchanged sword."""
from ro_weight_vector_common import *
from ro_hand_gate import contacts
from mathutils import Matrix,Vector

def add_weapon(rig, data, shift):
    delta=Vector(shift)
    vertices=[Vector(p)+delta for p in data['vertices']]
    me=bpy.data.meshes.new('ActualSwordLocal');me.from_pydata(vertices,[],data['triangles']);me.update()
    ob=bpy.data.objects.new('SM_RO_LocalActualSword',me);bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material('ActualSwordLocalMaterial',(.18,.23,.28),metal=.6))
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    b=rig.data.edit_bones.new('sword');b.head=Vector(data['bone']['head'])+delta;b.tail=Vector(data['bone']['tail'])+delta;b.parent=rig.data.edit_bones['hand']
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob

def place_weapon(weapon,rig,data,shift):
    delta=Vector(shift)
    for v,p in zip(weapon.data.vertices,data['vertices']):v.co=Vector(p)+delta
    weapon.data.update()
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    rig.data.edit_bones['sword'].head=Vector(data['bone']['head'])+delta;rig.data.edit_bones['sword'].tail=Vector(data['bone']['tail'])+delta
    bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()

def controls(rig,row,splays,splay_first=False):
    reset(rig)
    for branch in ['finger1','finger2','finger3','finger4','thumb']:
        for i,angle in enumerate(row[branch],1):rotate(rig,f'{branch}_{i:02}',angle)
        name=branch+'_01';bone=rig.data.bones[name];native=bone.matrix_local.to_3x3();pb=rig.pose.bones[name]
        axis=(bone.tail_local-bone.head_local).normalized() if branch=='thumb' else Vector((0,-1,0))
        side=-row['pronation'] if branch=='thumb' else splays[branch]
        side_local=native.inverted()@Matrix.Rotation(side,3,axis)@native
        curl_local=pb.rotation_quaternion.to_matrix()
        pb.rotation_quaternion=(curl_local@side_local if splay_first and branch!='thumb' else side_local@curl_local).to_quaternion()
    bpy.context.view_layer.update()

def capture(ob,rig,rest,label,params,ww):
    import ro_weight_vector_common as common
    matrices={b.name:b.matrix_basis.copy() for b in rig.pose.bones};original=common.pose
    def restore(rig,parameters):
        for n,m in matrices.items():rig.pose.bones[n].matrix_basis=m
        bpy.context.view_layer.update()
    common.pose=restore
    try:event,pts=common.actual(ob,rig,rest,label,params,ww)
    finally:common.pose=original
    event['actual_basis']={n:[list(row) for row in m] for n,m in matrices.items()}
    return event,pts

def score(contact,self_report):
    # No sum ofcontacts can offset anindividual missingdigit orpenetration.
    deficit=max(max(0,3-r['within_2mm']) for r in contact['pad_contacts'].values())
    return (self_report['transverse_pairs']+contact['transverse_crossings_count'],len(contact['unknown_inside']),contact['maximum_penetration_m'],deficit,
            max(r['minimum_gap_m'] for r in contact['pad_contacts'].values()))
