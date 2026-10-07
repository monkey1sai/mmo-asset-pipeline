"""Diagnostic only. Use unchanged P4 evaluator, then sample base/morph/skin."""
from pathlib import Path
import json
import runpy
import sys
import bpy

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.argv = ['blender', '--', '--scenarios', 'runs/qa/ro-swordsman-character-v1/v001/p4/transitions-05.json',
            '--registry', 'runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json',
            '--rules', 'assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/corrective-rules.json',
            '--contract', 'runs/qa/ro-swordsman-character-v1-r4/joint-range-contract-v5.json',
            '--fixtures', 'assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/contact-fixtures.json',
            '--out', str(OUT / 'diagnostic-init-03'), '--continuity-only', '--only', '__diagnostic_no_scenario__']
ns = runpy.run_path(str(ROOT / 'scripts/cv1_transition_check.py'))
obj = bpy.data.objects['SM_RO_core']
arm = ns['arm']
def points():
    target = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = target.to_mesh()
    data = [list(v.co) for v in mesh.vertices]
    target.to_mesh_clear()
    return data

records = []
solver_calls = []
original_solver = ns['fl'].two_bone
def capture_solver(*args):
    result = original_solver(*args)
    solver_calls.append({'inputs': args, 'output': result})
    return result
ns['fl'].two_bone = capture_solver
for sid, t in [('combo-idle-end-b100-s1.0', .55), ('combo-idle-end-b200-s0.5', .6)]:
    scenario = next(s for s in ns['spec']['scenarios'] if s['id'] == sid)
    solver_calls.clear()
    unlocked_pose, _, _ = ns['blended_pose'](scenario, t)
    ns['set_pose'](unlocked_pose)
    bone_names = ['root', 'pelvis'] + [f'{n}.{s}' for s in ['L','R'] for n in ['upper_leg', 'lower_leg', 'foot', 'toe']]
    unlocked = {name: {'basis_quaternion': list(arm.pose.bones[name].rotation_quaternion),
                      'matrix_local': [list(row) for row in arm.data.bones[name].matrix_local],
                      'matrix_world': [list(row) for row in (arm.matrix_world @ arm.pose.bones[name].matrix)],
                      'parent': arm.data.bones[name].parent.name if arm.data.bones[name].parent else None} for name in bone_names}
    pose = ns['evaluate'](scenario, t)
    skinned = points()
    mod_state = [m.show_viewport for m in obj.modifiers]
    for m in obj.modifiers:
        m.show_viewport = False
    bpy.context.view_layer.update()
    morphed = points()
    for m, enabled in zip(obj.modifiers, mod_state):
        m.show_viewport = enabled
    bpy.context.view_layer.update()
    keys = obj.data.shape_keys.key_blocks
    groups = [{'bone': obj.vertex_groups[g.group].name, 'weight': g.weight,
               'matrix': [list(row) for row in (obj.matrix_world.inverted() @ arm.matrix_world @ arm.pose.bones[obj.vertex_groups[g.group].name].matrix @ arm.data.bones[obj.vertex_groups[g.group].name].matrix_local.inverted() @ arm.matrix_world.inverted() @ obj.matrix_world)]}
              for g in obj.data.vertices[5297].groups if obj.vertex_groups[g.group].name in arm.pose.bones]
    records.append({'scenario': sid, 't': t, 'pose': pose, 'unlocked': unlocked, 'solver_calls': list(solver_calls),
                    'base': [list(v.co) for v in obj.data.vertices],
                    'morphed': morphed, 'skinned_local': skinned,
                    'matrix_world': [list(row) for row in obj.matrix_world], 'vertex_5297_weights': groups,
                    'shape_keys': [{'name': k.name, 'value': k.value, 'relative_key': k.relative_key.name,
                                    'vertex_group': k.vertex_group, 'mute': k.mute,
                                    'delta_5297': list(k.data[5297].co - k.relative_key.data[5297].co)} for k in keys],
                    'modifiers': [{'name': m.name, 'type': m.type, 'enabled': m.show_viewport,
                                  'preserve_volume': getattr(m, 'use_deform_preserve_volume', None),
                                  'vertex_groups': getattr(m, 'use_vertex_groups', None)} for m in obj.modifiers]})
(OUT / 'blender-decomposition-03.json').write_text(json.dumps({'scope': 'diagnostic_only; empty initialization continuity is NOT a gate run',
              'blender': bpy.app.version_string, 'source_sha256': ns['SCRIPT_SHA256'], 'modules': ns['MODULES'], 'records': records}, indent=1))
print('DIAGNOSTIC_SAVED')
