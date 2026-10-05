"""Read-only verification of the r010 GLB weight adapter, including every ID.

Creates evidence only. Does not repair a GLB or alter Blender's installation.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'runs/qa/ro-swordsman-combo-r010'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
artifact = lambda p: {'path': p.relative_to(ROOT).as_posix(),
                      'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def save(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def decode(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', data)
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A and size % 4 == 0
    doc = json.loads(data[20:20 + size])
    binary_length, binary_kind = struct.unpack_from('<II', data, 20 + size)
    offset = 28 + size
    assert binary_kind == 0x004E4942 and offset + binary_length == len(data)
    assert len(doc['buffers']) == 1 and 'uri' not in doc['buffers'][0]
    assert 0 <= binary_length - doc['buffers'][0]['byteLength'] <= 3
    return data, doc, offset


def array(data, doc, binary, index, component, kind, width):
    a = doc['accessors'][index]
    assert 'sparse' not in a and not a.get('normalized', False)
    assert a['componentType'] in component and a['type'] == kind
    v = doc['bufferViews'][a['bufferView']]
    assert v['buffer'] == 0
    dtype = np.dtype({5121: 'u1', 5123: '<u2', 5126: '<f4'}[a['componentType']])
    count = a['count']
    assert type(count) is int and count > 0
    view_offset = v.get('byteOffset', 0)
    accessor_offset = a.get('byteOffset', 0)
    stride = v.get('byteStride', dtype.itemsize * width)
    assert all(type(x) is int and x >= 0 for x in [view_offset, accessor_offset, stride])
    assert stride >= dtype.itemsize * width and stride % dtype.itemsize == 0
    if 'byteStride' in v:
        assert 4 <= stride <= 252 and stride % 4 == 0
    assert accessor_offset % dtype.itemsize == view_offset % dtype.itemsize == 0
    assert view_offset + v['byteLength'] <= doc['buffers'][0]['byteLength']
    assert accessor_offset + (count - 1) * stride + width * dtype.itemsize <= v['byteLength']
    offset = binary + view_offset + accessor_offset
    result = np.ndarray((count, width), dtype=dtype, buffer=data,
                        offset=offset, strides=(stride, dtype.itemsize))
    assert np.isfinite(result).all()
    return result, offset, stride


record = read(QA / 'v004-certified-animation/exact-weights-export.json')
old_path, new_path = [ROOT / record[k]['path'] for k in ['prior_export', 'artifact']]
assert artifact(old_path) == record['prior_export'] and artifact(new_path) == record['artifact']
old, doc, binary = decode(old_path)
new, new_doc, new_binary = decode(new_path)
assert new_doc == doc and new_binary == binary and len(new) == len(old)
selected = [(mi, pi, p) for mi, m in enumerate(doc['meshes'])
            for pi, p in enumerate(m['primitives']) if '_R010_ID' in p['attributes']]
assert len(selected) == 1
mesh_index, primitive_index, primitive = selected[0]
nodes = [(i, n) for i, n in enumerate(doc['nodes']) if n.get('mesh') == mesh_index]
assert len(nodes) == 1 and 'skin' in nodes[0][1]
node_index, node = nodes[0]
skin_index = node['skin']
skin = doc['skins'][skin_index]
joint_names = [doc['nodes'][i]['name'] for i in skin['joints']]
assert len(set(joint_names)) == len(joint_names)
attrs = primitive['attributes']
ids, _, _ = array(old, doc, binary, attrs['_R010_ID'], {5126}, 'SCALAR', 1)
assert np.equal(ids, np.round(ids)).all()
ids = ids[:, 0].astype(int).tolist()
snapshot = ROOT / record['frozen_weights']['path']
assert artifact(snapshot) == record['frozen_weights']
frozen = read(snapshot)['weights']
assert set(ids) == {int(i) for i in frozen} == set(range(904))
wj = {}
for name, types in [('WEIGHTS_0', {5126}), ('JOINTS_0', {5121, 5123})]:
    wj[name] = [array(blob, doc, binary, attrs[name], types, 'VEC4', 4)
                for blob in [old, new]]
    assert all(len(a[0]) == len(ids) for a in wj[name])
allowed = set()
for name in wj:
    a, offset, stride = wj[name][0]
    for row in range(len(ids)):
        allowed.update(range(offset + row * stride, offset + row * stride + 4 * a.dtype.itemsize))
joint_capacity = np.iinfo(wj['JOINTS_0'][0][0].dtype).max
assert len(joint_names) - 1 <= joint_capacity
rows = []
lost = set()
lost_expanded = 0
for row, source_id in enumerate(ids):
    target = frozen[str(source_id)]
    assert 1 <= len(target) <= 4 and all(name in joint_names for name in target)
    assert all(np.isfinite(value) and value > 0 for value in target.values())
    assert abs(sum(target.values()) - 1) < 1e-6
    decoded = []
    for version in range(2):
        weights = wj['WEIGHTS_0'][version][0][row]
        joints = wj['JOINTS_0'][version][0][row]
        assert np.all(weights >= 0) and np.all(joints < len(joint_names))
        names = [joint_names[int(j)] for j, w in zip(joints, weights) if w > 0]
        assert len(names) == len(set(names))
        decoded.append({joint_names[int(j)]: float(w) for j, w in zip(joints, weights) if w > 0})
    before, after = decoded
    assert after == target
    missing = sorted(set(target) - set(before))
    lost.update((source_id, name) for name in missing)
    lost_expanded += len(missing)
    error = lambda values: sum(abs(values.get(n, 0) - target.get(n, 0))
                               for n in set(values) | set(target))
    rows.append({'exported_vertex': row, 'original_id': source_id,
                 'prior_weights': before, 'restored_weights': after,
                 'missing_prior_influences': missing,
                 'prior_L1': error(before), 'restored_L1': error(after)})
diff = {i for i, (a, b) in enumerate(zip(old, new)) if a != b}
assert diff <= allowed and len(diff) == record['changed_bytes']
assert len(doc['animations']) == 1 and len(doc['animations'][0]['channels']) == 52
mapping = QA / 'v004-certified-animation/exact-weights-all-IDs.json'
save(mapping, {'rows': rows, 'actual_skin_index': skin_index, 'joint_names': joint_names})
fresh = read(QA / 'v004-fresh-glb-attempt3/result.json')
assert fresh['subject'] == record['artifact'] and fresh['numeric_interval_pass']
assert fresh['samples'] == 121 and fresh['maximum_hand_point_difference_m'] <= 1e-6
save(QA / 'v004-certified-animation/exact-weights-verification.json', {
    'observed_utc': datetime.now(timezone.utc).isoformat(), 'artifact': record['artifact'],
    'prior_export': record['prior_export'], 'all_ID_mapping': artifact(mapping),
    'actual_node_index': node_index, 'actual_mesh_index': mesh_index,
    'actual_primitive_index': primitive_index, 'actual_skin_index': skin_index,
    'exported_vertices': len(ids), 'original_ids': len(set(ids)),
    'integer_source_IDs': True, 'actual_skin_joint_mapping_verified': True,
    'accessor_types_strides_offsets_bounds_verified': True,
    'source_weights_finite_nonnegative_normalized_max4': True,
    'joint_index_capacity': int(joint_capacity),
    'maximum_prior_L1': max(r['prior_L1'] for r in rows),
    'maximum_restored_L1': max(r['restored_L1'] for r in rows),
    'lost_prior_unique_source_influences': len(lost),
    'lost_prior_expanded_influences': lost_expanded,
    'all_original_and_split_weights_match_frozen_float32_exact': True,
    'changed_bytes': len(diff), 'all_other_bytes_unchanged': True,
    'single_animation_channels': 52, 'fresh_verification': artifact(QA / 'v004-fresh-glb-attempt3/result.json'),
    'input_models_unmodified': True, 'new_candidate_or_clock_reset': False})
print(json.dumps({'status': 'verified', 'vertices': len(ids), 'lost_unique_influences': len(lost),
                  'maximum_prior_L1': max(r['prior_L1'] for r in rows), 'maximum_restored_L1': 0}))
