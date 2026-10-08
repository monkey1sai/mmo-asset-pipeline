"""Real Blender material-only roundtrip; no character revision or animation claim."""
import argparse
import json
from pathlib import Path
import struct
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity
from blender_fixture_material import make_fixture_material

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = identity.command_path(ROOT, a.out)
if not out.relative_to(ROOT).as_posix().startswith('runs/qa/'):
    raise ValueError('OUTPUT_SCOPE')
out.mkdir(exist_ok=False, parents=True)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
negative = []
for color in ((1, 0, 0), (float('nan'), 0, 0, 1), (-.1, 0, 0, 1), (0, 0, 0, 1.1)):
    try:
        make_fixture_material(bpy, 'invalid', color)
    except ValueError as error:
        negative.append(str(error))
    else:
        raise AssertionError('INVALID_COLOR_ACCEPTED')
colors = [(0.2, .5, .9, 1), (.7, .55, .2, 1), (.16, .12, .08, 1), (.8, .12, .3, 1), (0, 1, 0, 1)]
expected = {}
for i, color in enumerate(colors):
    name = 'fixture-material-' + str(i)
    bpy.ops.mesh.primitive_plane_add(location=(i, 0, 0))
    bpy.context.object.data.materials.append(make_fixture_material(bpy, name, color))
    expected[name] = color
asset = out / 'material-only.glb'
bpy.ops.export_scene.gltf(filepath=str(asset), export_format='GLB', export_animations=False)
raw = asset.read_bytes()
size, kind = struct.unpack_from('<II', raw, 12)
assert kind == 0x4E4F534A
document = json.loads(raw[20:20 + size])
exported = {m['name']: m['pbrMetallicRoughness']['baseColorFactor'] for m in document['materials']}
for name, color in expected.items():
    assert max(abs(x-y) for x, y in zip(color, exported[name])) < 1e-6
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
bpy.ops.import_scene.gltf(filepath=str(asset))
imported = {}
for name, color in expected.items():
    shader = bpy.data.materials[name].node_tree.nodes.get('Principled BSDF')
    value = list(shader.inputs['Base Color'].default_value)
    imported[name] = value
    assert max(abs(x-y) for x, y in zip(color, value)) < 1e-6
report = {'status': 'PASS', 'blender': bpy.app.version_string, 'expected_linear_rgba': expected,
          'exported_linear_rgba': exported, 'reimported_linear_rgba': imported,
          'negative_checks': negative, 'asset_sha256': identity.file_digest(asset),
          'scope': 'material-only engineering check', 'character_revision': False,
          'visual_acceptance': 'NOT_RUN', 'mixamo': 'NOT_RUN', 'unity': 'NOT_RUN'}
(out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
