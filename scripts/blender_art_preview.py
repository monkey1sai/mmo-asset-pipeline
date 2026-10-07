"""Fixed-condition neutral GLB previews, in a factory-startup Blender session.

Never opens .blend files, downloads, saves the source, edits an existing Blender
session or runs animations. Beauty/clay stills are review material, not art QA.
Use Blender --background --factory-startup --disable-autoexec --python THIS -- ...
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity
ROOT = Path(__file__).resolve().parents[1]


class PreviewError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise PreviewError(code)


def finite(v):
    return type(v) in (float, int) and math.isfinite(v)


def validate_protocol(p, request):
    need(isinstance(p, dict) and type(p.get('schema_version')) is int and p['schema_version'] == 1, 'PROTOCOL_SCHEMA')
    need(p.get('status') == 'frozen', 'PROTOCOL_NOT_FROZEN')
    need(p.get('request') == {'id':request.get('id'), 'sha256':identity.json_digest(request)}, 'REQUEST_BINDING_MISMATCH')
    need(request.get('status') == 'specified', 'REQUEST_NOT_SPECIFIED')
    need(p.get('coordinate_system') == 'Blender_Z_up_meters', 'COORDINATE_SYSTEM_REQUIRED')
    need(isinstance(p.get('blender_version'), str) and p['blender_version'].count('.') == 2, 'BLENDER_VERSION_REQUIRED')
    c = p.get('camera', {})
    target = c.get('target_m')
    need(isinstance(target,list) and len(target)==3 and all(finite(x) for x in target), 'CAMERA_TARGET_INVALID')
    need(finite(c.get('orthographic_scale_m')) and c['orthographic_scale_m'] > 0, 'CAMERA_SCALE_INVALID')
    need(finite(c.get('distance_m')) and c['distance_m'] > 0, 'CAMERA_DISTANCE_INVALID')
    need(finite(c.get('elevation_deg')) and -80 < c['elevation_deg'] < 80, 'CAMERA_ELEVATION_INVALID')
    views=c.get('azimuths_deg')
    need(isinstance(views,list) and 2 <= len(views) <= 16 and all(finite(x) and 0 <= x < 360 for x in views)
         and len(set(views)) == len(views), 'CAMERA_VIEWS_INVALID')
    r=p.get('render',{})
    need(all(type(r.get(k)) is int and 128 <= r[k] <= 4096 for k in ('width','height')), 'RENDER_SIZE_INVALID')
    need(finite(r.get('exposure')) and -10 <= r['exposure'] <= 10, 'EXPOSURE_INVALID')
    need(r.get('view_transform') == 'AgX' and r.get('engine') == 'BLENDER_EEVEE_NEXT', 'RENDER_PROFILE_UNSUPPORTED')
    return p


def embedded_glb_only(path):
    """Reject external image/buffer URIs before Blender can resolve any of them."""
    data=path.read_bytes()
    need(len(data)>=20 and data[:4]==b'glTF', 'INPUT_NOT_GLB')
    magic,version,length=struct.unpack_from('<4sII',data)
    need(version==2 and length==len(data), 'GLB_HEADER_INVALID')
    size,kind=struct.unpack_from('<II',data,12)
    need(kind==0x4E4F534A and 20+size<=len(data), 'GLB_JSON_CHUNK_INVALID')
    try:
        # URI screening only; the official validator remains necessary.
        doc=json.loads(data[20:20+size].decode('utf-8'))
    except (ValueError,UnicodeError):
        raise PreviewError('GLB_JSON_INVALID') from None
    need(isinstance(doc,dict),'GLB_JSON_INVALID')
    def reject_uris(value):
        if isinstance(value,dict):
            need('uri' not in value, 'EXTERNAL_OR_DATA_URI_NOT_SUPPORTED')
            for child in value.values(): reject_uris(child)
        elif isinstance(value,list):
            for child in value: reject_uris(child)
    reject_uris(doc)
    for key in ('buffers','images'):
        rows=doc.get(key,[])
        need(isinstance(rows,list) and all(isinstance(x,dict) for x in rows), 'GLB_RESOURCES_INVALID')
        need(not any('uri' in x for x in rows), 'EXTERNAL_OR_DATA_URI_NOT_SUPPORTED')
    # Unknown extensions may reference external resources; require a separate
    # audited importer path rather than silently accepting arbitrary extensions.
    allowed={'KHR_materials_unlit','KHR_materials_clearcoat','KHR_materials_transmission',
             'KHR_materials_volume','KHR_materials_ior','KHR_materials_specular',
             'KHR_materials_sheen','KHR_materials_emissive_strength','KHR_texture_transform'}
    used=doc.get('extensionsUsed',[])
    required=doc.get('extensionsRequired',[])
    need(all(isinstance(rows,list) and all(isinstance(x,str) and x in allowed for x in rows)
             for rows in (used,required)), 'GLB_EXTENSION_REQUIRES_REVIEW')
    need(set(required).issubset(used), 'GLB_EXTENSION_DECLARATION_INVALID')
    def screen_extensions(value):
        if isinstance(value,dict):
            if 'extensions' in value:
                extension=value['extensions']
                need(isinstance(extension,dict) and all(x in allowed for x in extension),
                     'GLB_EXTENSION_REQUIRES_REVIEW')
                need(set(extension).issubset(used), 'GLB_EXTENSION_DECLARATION_INVALID')
            for child in value.values(): screen_extensions(child)
        elif isinstance(value,list):
            for child in value: screen_extensions(child)
    screen_extensions(doc)
    return doc


def scoped_path(root,value,allowed,existing=True):
    need(isinstance(value,str) and not Path(value).is_absolute() and '\\' not in value and ':' not in value
         and '..' not in Path(value).parts, 'PATH_SCOPE')
    raw=root/value
    parts=raw.relative_to(root).parts
    p=raw
    need(any(parts[:len(prefix)]==prefix for prefix in allowed),'PATH_SCOPE')
    q=root
    for part in parts:
        q=q/part
        need(not q.is_symlink() and not (hasattr(q,'is_junction') and q.is_junction()),'SYMLINK_NOT_ALLOWED')
    p=identity.recorded_path(root,value)
    if existing:
        need(p.is_file(),'INPUT_MISSING')
    return p


def capture(args):
    # Import only in Blender, after safe arguments are available. Unit tests can
    # import protocol validation without pretending to have run the DCC.
    try:
        import bpy
        from mathutils import Vector
    except ImportError:
        raise PreviewError('BLENDER_RUNTIME_REQUIRED') from None
    root=ROOT.resolve()
    request_path=scoped_path(root,args.request,[("requests",)])
    protocol_path=scoped_path(root,args.protocol,[("requests",),("runs","qa")])
    asset=scoped_path(root,args.asset,[("assets",),("deliveries",)])
    out=scoped_path(root,args.out,[("runs","qa")],existing=False)
    need(not out.exists(),'OUTPUT_ALREADY_EXISTS')
    need(asset.suffix.lower()=='.glb' and asset.stat().st_size<=512*1024**2,'GLB_INPUT_REQUIRED')
    p=validate_protocol(identity.read_json(protocol_path),identity.read_json(request_path))
    need('.'.join(map(str,bpy.app.version))==p['blender_version'],'BLENDER_VERSION_MISMATCH')
    need(bpy.app.background and not bpy.data.filepath,'FACTORY_BACKGROUND_SESSION_REQUIRED')
    need('--factory-startup' in sys.argv and '--disable-autoexec' in sys.argv,'FACTORY_SAFE_FLAGS_REQUIRED')
    source_hash=identity.file_digest(asset)
    embedded_glb_only(asset)
    # This is a separate factory session. No source .blend or existing scene is opened.
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(asset))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    need(bool(meshes),'NO_MESH_IMPORTED')
    for o in bpy.context.scene.objects:
        o.animation_data_clear()
        if o.type=='ARMATURE': o.data.pose_position='REST'
        if o.type=='MESH' and o.data.shape_keys: o.data.shape_keys.animation_data_clear()
    scene=bpy.context.scene
    scene.render.engine=p['render']['engine']
    scene.render.resolution_x=p['render']['width']; scene.render.resolution_y=p['render']['height']
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=p['render']['exposure']
    scene.view_settings.gamma=1.0
    world=bpy.data.worlds.new('review-world'); world.use_nodes=True; scene.world=world
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.18,0.18,0.18,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.3
    target=Vector(p['camera']['target_m'])
    scale=p['camera']['orthographic_scale_m']
    # Fixed rig is derived only from the frozen protocol, NOT candidate bounds.
    for name,offset,power in [('key',(1.5,-2,2.5),1000),('fill',(-2,-1,1),500),('rim',(0,2,2),800)]:
        light=bpy.data.lights.new(name,'AREA'); light.energy=power; light.shape='DISK'; light.size=scale
        o=bpy.data.objects.new(name,light); scene.collection.objects.link(o)
        o.location=target+Vector(offset)*scale
        o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    camdata=bpy.data.cameras.new('fixed-review-camera'); camdata.type='ORTHO'; camdata.ortho_scale=scale
    camera=bpy.data.objects.new('fixed-review-camera',camdata); scene.collection.objects.link(camera); scene.camera=camera
    clay=bpy.data.materials.new('review-clay'); clay.use_nodes=True
    shader=clay.node_tree.nodes.get('Principled BSDF'); shader.inputs['Base Color'].default_value=(0.45,0.45,0.45,1)
    shader.inputs['Roughness'].default_value=0.7; shader.inputs['Metallic'].default_value=0
    metrics=[]
    for o in meshes:
        o.data.calc_loop_triangles()
        metrics.append({'mesh':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'uv_layers':len(o.data.uv_layers),'material_slots':len(o.data.materials)})
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.art-preview-',dir=out.parent))
    try:
        files=[]
        for mode in ('beauty','clay'):
            if mode=='clay':
                for o in meshes:
                    o.data.materials.clear(); o.data.materials.append(clay)
                    for face in o.data.polygons: face.material_index=0
            for index,azimuth in enumerate(p['camera']['azimuths_deg']):
                a=math.radians(azimuth); e=math.radians(p['camera']['elevation_deg']); d=p['camera']['distance_m']
                camera.location=target+Vector((d*math.sin(a)*math.cos(e),-d*math.cos(a)*math.cos(e),d*math.sin(e)))
                camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
                name=f'{mode}-{index:02d}.png'; scene.render.filepath=str(temp/name)
                bpy.ops.render.render(write_still=True)
                files.append({'path':name,'sha256':identity.file_digest(temp/name)})
        need(identity.file_digest(asset)==source_hash,'SOURCE_CHANGED')
        report={'schema_version':1,'decision':'preview_capture_completed','art_accepted':False,'technical_accepted':False,
                'asset':asset.relative_to(root).as_posix(),'asset_sha256':source_hash,
                'protocol_sha256':identity.json_digest(p),'script_sha256':identity.file_digest(Path(__file__)),
                'blender_version':p['blender_version'],'metrics_scope':'source mesh inventory; not deformation validation',
                'mesh_inventory':metrics,'files':files,'limitations':['Neutral rest-pose stills only.','No animation naturalness, external dependency, UV quality or game-ready certification.']}
        (temp/'capture.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        need(not out.exists(),'OUTPUT_ALREADY_EXISTS'); temp.rename(out); temp=None
        return report
    finally:
        if temp is not None: shutil.rmtree(temp)


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('asset','request','protocol','out'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(capture(args),ensure_ascii=False,indent=2)); return 0
    except (PreviewError,identity.IdentityError) as e:
        print(json.dumps({'decision':'not_completed','error':str(e),'art_accepted':False})); return 2
    except (OSError,ValueError,TypeError,KeyError):
        print('{"decision":"not_completed","error":"INPUT_OR_DCC_FAILURE","art_accepted":false}'); return 2


if __name__=='__main__': raise SystemExit(main())
