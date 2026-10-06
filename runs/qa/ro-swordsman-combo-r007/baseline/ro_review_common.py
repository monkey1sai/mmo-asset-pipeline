"""Frozen Blender studio shared by baseline, candidate and fresh-import review."""
import bpy
from mathutils import Vector

VIEWS = {'front': ((0,-4,1.35),(0,0,.9),2.25), 'side': ((4,0,1.35),(0,0,.9),2.25), 'back': ((0,4,1.35),(0,0,.9),2.25), 'three-quarter': ((2.8,-4,2),(0,0,.9),2.25), 'detail': ((1.2,-4,1.75),(0,0,1.53),.62)}

def material(name, color, metal=0, rough=.5, emission=0):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emission
    return m

def stage():
    scene=bpy.context.scene; scene.unit_settings.system='METRIC'
    scene.render.engine='BLENDER_EEVEE_NEXT'; scene.eevee.taa_render_samples=64
    scene.render.fps=60; scene.frame_start=1; scene.frame_end=300
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
    # Default factory scene look is Medium High Contrast, same as previous fixed views.
    scene.view_settings.exposure=0; scene.world.color=(.16,.16,.16)
    col=bpy.data.collections.new('COL_ReviewStage'); scene.collection.children.link(col)
    bpy.ops.mesh.primitive_plane_add(size=200); floor=bpy.context.object
    for c in list(floor.users_collection): c.objects.unlink(floor)
    col.objects.link(floor); floor.data.materials.append(material('ReviewFloor',(.18,.19,.21),rough=.9))
    for name,loc,power,size in [('Key',(3,-4,5),700,4),('Fill',(-3,-2,3),350,3),('Rim',(0,3,4),800,3)]:
        d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
        o=bpy.data.objects.new(name,d); col.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
    d=bpy.data.cameras.new('ReviewCamera'); cam=bpy.data.objects.new('ReviewCamera',d); col.objects.link(cam)
    d.type='ORTHO'; scene.camera=cam
    return col

def camera(view='three-quarter'):
    loc,target,scale=VIEWS[view] if isinstance(view,str) else view
    cam=bpy.context.scene.camera; cam.location=loc
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.ortho_scale=scale

def render_views(folder, frame=1):
    folder.mkdir(parents=True, exist_ok=True)
    s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=1280; s.render.resolution_percentage=100
    s.frame_set(frame)
    for name in VIEWS:
        camera(name); s.render.filepath=str(folder/(name+'.png')); bpy.ops.render.render(write_still=True)
    camera()
