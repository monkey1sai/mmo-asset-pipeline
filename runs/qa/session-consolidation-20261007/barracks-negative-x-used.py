"""Supplementary view of the SAME delivery, using the existing preview light rig."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import bpy

asset, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
expected = '9431e8c367c55afe0b6d1876b1dec75923a6ff79540419b90f63434321a9142f'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(asset) == expected
assert not output.exists()
root = Path(__file__).resolve().parents[3]
helper_path = root / 'tools/blender/render_preview.py'
spec = importlib.util.spec_from_file_location('original_preview', helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
helper.clear_scene()
bpy.ops.import_scene.gltf(filepath=str(asset))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
lo, hi = helper.bounds(meshes)
center = (lo + hi) / 2
radius = max((hi - lo).length / 2, 0.5)
helper.setup_world(center, radius)
output.mkdir()
for label, elevation in [('negative-x', 0), ('negative-x-elevated', 8)]:
    helper.render(center, radius, 180, elevation, str(output / f'{label}.png'))
assert digest(asset) == expected
scene = bpy.context.scene
report = {
    'decision': 'supplementary_static_views_captured',
    'asset_sha256': expected,
    'helper_sha256': digest(helper_path),
    'script_sha256': digest(Path(__file__)),
    'blender_version': bpy.app.version_string,
    'engine': scene.render.engine,
    'view_transform': scene.view_settings.view_transform,
    'exposure': scene.view_settings.exposure,
    'camera_center_blender_m': list(center),
    'radius_m': radius,
    'camera_distance_m': radius * 2.6,
    'azimuth_deg': 180,
    'elevations_deg': [0, 8],
    'lights': 'unchanged existing setup_world sun/fill/background/floor',
    'files': [{'path': p.name, 'sha256': digest(p)} for p in sorted(output.glob('*.png'))],
    'scope': 'Additional static evidence only; original accepted images and model unchanged.',
    'art_accepted': False,
    'runtime_retested': False,
}
(output / 'capture.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
