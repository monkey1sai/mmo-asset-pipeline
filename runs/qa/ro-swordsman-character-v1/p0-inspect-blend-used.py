# Read-only inspection: never saves the opened file.
import bpy, bmesh, json, sys
out={}
sc=bpy.context.scene
out['file']=bpy.data.filepath
out['blender']=bpy.app.version_string
out['scene']={'fps':sc.render.fps,'frame_start':sc.frame_start,'frame_end':sc.frame_end,'unit_scale':sc.unit_settings.scale_length,'unit_system':sc.unit_settings.system}
objs=[]
for o in bpy.data.objects:
    e={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'parent_bone':o.parent_bone or None,
       'dims':[round(x,4) for x in o.dimensions],'loc':[round(x,4) for x in o.matrix_world.translation],
       'scale':[round(x,4) for x in o.scale],'hide_render':o.hide_render,
       'modifiers':[(m.type,m.name,getattr(getattr(m,'object',None),'name',None)) for m in o.modifiers],
       'constraints':[(c.type,c.name) for c in o.constraints]}
    if o.type=='MESH':
        me=o.data
        me.calc_loop_triangles()
        bm=bmesh.new(); bm.from_mesh(me)
        nm=sum(1 for ed in bm.edges if not ed.is_manifold); bd=sum(1 for ed in bm.edges if ed.is_boundary)
        loose=sum(1 for v in bm.verts if not v.link_edges)
        ngon=sum(1 for f in bm.faces if len(f.verts)>4); quad=sum(1 for f in bm.faces if len(f.verts)==4); tri=sum(1 for f in bm.faces if len(f.verts)==3)
        bm.free()
        vg=[g.name for g in o.vertex_groups]
        zero=0;over4=0;maxinf=0;unnorm=0
        used={}
        for v in me.vertices:
            ws=[(g.group,g.weight) for g in v.groups if g.weight>0]
            n=len(ws); maxinf=max(maxinf,n)
            if n==0: zero+=1
            if n>4: over4+=1
            s=sum(w for _,w in ws)
            if n and abs(s-1)>1e-3: unnorm+=1
            for gi,w in ws: used[vg[gi]]=used.get(vg[gi],0)+1
        e.update({'verts':len(me.vertices),'polys':len(me.polygons),'tris':len(me.loop_triangles),'face_tri_quad_ngon':[tri,quad,ngon],
                  'non_manifold_edges':nm,'boundary_edges':bd,'loose_verts':loose,
                  'uv_layers':[u.name for u in me.uv_layers],'materials':[m.name if m else None for m in me.materials],
                  'shape_keys':[k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
                  'shape_key_drivers':len(me.shape_keys.animation_data.drivers) if me.shape_keys and me.shape_keys.animation_data else 0,
                  'shape_key_action':(me.shape_keys.animation_data.action.name if me.shape_keys and me.shape_keys.animation_data and me.shape_keys.animation_data.action else None),
                  'vertex_groups':len(vg),'weights':{'zero_weight_verts':zero,'gt4_influence_verts':over4,'max_influences':maxinf,'not_normalized_verts':unnorm},
                  'groups_used':used,'attributes':[a.name for a in me.attributes if not a.is_internal][:20]})
    if o.type=='ARMATURE':
        arm=o.data
        bones=[]
        for b in arm.bones:
            bones.append({'name':b.name,'parent':b.parent.name if b.parent else None,'deform':b.use_deform,'connected':b.use_connect,
                          'head':[round(x,4) for x in b.head_local],'tail':[round(x,4) for x in b.tail_local],'length':round(b.length,4)})
        e['bones']=bones
        e['pose_constraints']={pb.name:[(c.type,c.name,getattr(c,'subtarget',None)) for c in pb.constraints] for pb in o.pose.bones if pb.constraints}
        e['rotation_modes']=sorted({pb.rotation_mode for pb in o.pose.bones})
        e['bone_collections']=[c.name for c in arm.collections] if hasattr(arm,'collections') else None
        ad=o.animation_data
        e['action']=ad.action.name if ad and ad.action else None
        e['nla_tracks']=[(t.name,[s.name for s in t.strips]) for t in ad.nla_tracks] if ad else []
        e['drivers']=len(ad.drivers) if ad else 0
    objs.append(e)
out['objects']=objs
acts=[]
for a in bpy.data.actions:
    try: n=len(a.fcurves)
    except Exception: n=None
    acts.append({'name':a.name,'range':[a.frame_range[0],a.frame_range[1]],'fcurves':n,'users':a.users})
out['actions']=acts
out['images']=[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file),'filepath':i.filepath} for i in bpy.data.images]
out['materials']=[m.name for m in bpy.data.materials]
out['is_dirty_after_inspect']=bpy.data.is_dirty
dst=sys.argv[sys.argv.index('--')+1]
json.dump(out,open(dst,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('INSPECT_DONE',dst)
