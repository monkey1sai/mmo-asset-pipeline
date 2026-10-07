"""Per-node bounding boxes of a binary glTF (no external deps): node name, mesh primitives, triangle count, material
count and the world-space AABB from the POSITION accessors' min/max under each node's translation/rotation/scale
(TRS only, no skins). Prints JSON. Usage: python tools/glb_bounds.py <file.glb> [...]"""
import json
import math
import struct
import sys


def read_glb(path):
    data = open(path, 'rb').read()
    magic, version, length = struct.unpack_from('<III', data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError('not a binary glTF 2.0 container')
    offset = 12
    doc = None
    bin_chunk = None
    while offset < length:
        chunk_len, chunk_type = struct.unpack_from('<II', data, offset)
        chunk = data[offset + 8:offset + 8 + chunk_len]
        if chunk_type == 0x4E4F534A:
            doc = json.loads(chunk.decode('utf-8'))
        elif chunk_type == 0x004E4942:
            bin_chunk = chunk
        offset += 8 + chunk_len
    return doc, bin_chunk


def quat_rotate(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    # v' = v + 2w(q × v) + 2(q × (q × v))
    cx, cy, cz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (vx + 2 * (w * cx + ccx), vy + 2 * (w * cy + ccy), vz + 2 * (w * cz + ccz))


def accessor_count(doc, index):
    return doc['accessors'][index]['count']


def node_bounds(doc, node):
    mesh = doc['meshes'][node['mesh']]
    t = node.get('translation', [0, 0, 0])
    r = node.get('rotation', [0, 0, 0, 1])
    s = node.get('scale', [1, 1, 1])
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    triangles = 0
    materials = set()
    for prim in mesh['primitives']:
        acc = doc['accessors'][prim['attributes']['POSITION']]
        if 'indices' in prim:
            triangles += accessor_count(doc, prim['indices']) // 3
        else:
            triangles += acc['count'] // 3
        if 'material' in prim:
            materials.add(prim['material'])
        for corner in [(x, y, z) for x in (acc['min'][0], acc['max'][0]) for y in (acc['min'][1], acc['max'][1]) for z in (acc['min'][2], acc['max'][2])]:
            scaled = (corner[0] * s[0], corner[1] * s[1], corner[2] * s[2])
            world = quat_rotate(r, scaled)
            world = (world[0] + t[0], world[1] + t[1], world[2] + t[2])
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])
    return {
        'node': node.get('name'), 'triangles': triangles, 'materials': len(materials), 'translation': t, 'rotation': r, 'scale': s,
        'min': [round(v, 4) for v in lo], 'max': [round(v, 4) for v in hi], 'size': [round(hi[i] - lo[i], 4) for i in range(3)],
    }


def main():
    out = []
    for path in sys.argv[1:]:
        doc, _ = read_glb(path)
        nodes = [node_bounds(doc, n) for n in doc.get('nodes', []) if 'mesh' in n]
        out.append({
            'file': path, 'nodes': nodes, 'triangles': sum(n['triangles'] for n in nodes), 'materials': len(doc.get('materials', [])),
            'extensionsRequired': doc.get('extensionsRequired', []), 'images': len(doc.get('images', [])),
        })
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
