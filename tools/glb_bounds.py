"""Conservative world AABBs of static POSITION accessor boxes, including parent TRS.

Reports all mesh nodes (including nodes outside the active scene), in document
order. Existing translation/rotation/scale fields remain LOCAL transforms.
Not tight geometry bounds: rotated accessor boxes can overestimate the mesh.
Matrix nodes, skins, morphs and non-triangle primitives are rejected.
Usage: python tools/glb_bounds.py <file.glb> [...]
"""
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


def finite_vector(value, length, label):
    if (not isinstance(value, list) or len(value) != length or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError(f'{label}: expected {length} finite numbers')
    return value


def node_transform_chains(doc):
    """Each chain applies child TRS first, then ancestors, without reboxing.

    Applying full TRS in this order is equivalent to parent @ local affine
    matrices, including shear from nonuniform parent scales and child rotation.
    """
    nodes = doc.get('nodes', [])
    parents = [None] * len(nodes)
    local = []
    for i, node in enumerate(nodes):
        if 'matrix' in node:
            raise ValueError('matrix nodes are unsupported; TRS required')
        t = finite_vector(node.get('translation', [0, 0, 0]), 3, 'translation')
        r = finite_vector(node.get('rotation', [0, 0, 0, 1]), 4, 'rotation')
        s = finite_vector(node.get('scale', [1, 1, 1]), 3, 'scale')
        if abs(sum(v * v for v in r) - 1) > 1e-5:
            raise ValueError('rotation quaternion must have unit length')
        local.append((t, r, s))
        children = node.get('children', [])
        if not isinstance(children, list):
            raise ValueError('children must be a list')
        for child in children:
            if type(child) is not int or not 0 <= child < len(nodes):
                raise ValueError('child index outside nodes')
            if parents[child] is not None:
                raise ValueError('duplicate child or multiple parents')
            parents[child] = i
    chains = []
    for i in range(len(nodes)):
        chain, seen = [], set()
        current = i
        while current is not None:
            if current in seen:
                raise ValueError('node hierarchy cycle')
            seen.add(current)
            chain.append(local[current])
            current = parents[current]
        chains.append(chain)
    return chains


def node_bounds(doc, node, transform_chain=None):
    if transform_chain is None:
        chains = node_transform_chains(doc)
        index = next((i for i, n in enumerate(doc.get('nodes', [])) if n is node), None)
        if index is None:
            raise ValueError('node must belong to document nodes')
        transform_chain = chains[index]
    mesh = doc['meshes'][node['mesh']]
    if 'skin' in node or 'weights' in node or 'weights' in mesh:
        raise ValueError('skins and morph weights are unsupported')
    if not mesh.get('primitives'):
        raise ValueError('mesh has no primitives')
    t = node.get('translation', [0, 0, 0])
    r = node.get('rotation', [0, 0, 0, 1])
    s = node.get('scale', [1, 1, 1])
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    triangles = 0
    materials = set()
    for prim in mesh['primitives']:
        if prim.get('mode', 4) != 4 or 'targets' in prim:
            raise ValueError('only static TRIANGLES primitives are supported')
        acc = doc['accessors'][prim['attributes']['POSITION']]
        if acc.get('type') != 'VEC3' or acc.get('componentType') != 5126:
            raise ValueError('POSITION must be a float VEC3 accessor')
        amin = finite_vector(acc.get('min'), 3, 'POSITION min')
        amax = finite_vector(acc.get('max'), 3, 'POSITION max')
        if any(amin[i] > amax[i] for i in range(3)):
            raise ValueError('POSITION min exceeds max')
        if 'indices' in prim:
            count = accessor_count(doc, prim['indices'])
        else:
            count = acc['count']
        if type(count) is not int or count <= 0 or count % 3:
            raise ValueError('TRIANGLES count must be positive and divisible by 3')
        triangles += count // 3
        if 'material' in prim:
            materials.add(prim['material'])
        for corner in [(x, y, z) for x in (amin[0], amax[0]) for y in (amin[1], amax[1]) for z in (amin[2], amax[2])]:
            world = corner
            for pt, pr, ps in transform_chain:
                scaled = tuple(world[i] * ps[i] for i in range(3))
                rotated = quat_rotate(pr, scaled)
                world = tuple(rotated[i] + pt[i] for i in range(3))
            if not all(math.isfinite(v) for v in world):
                raise ValueError('world transform overflow')
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
        chains = node_transform_chains(doc)
        nodes = [node_bounds(doc, n, chains[i]) for i, n in enumerate(doc.get('nodes', [])) if 'mesh' in n]
        out.append({
            'file': path, 'nodes': nodes, 'triangles': sum(n['triangles'] for n in nodes), 'materials': len(doc.get('materials', [])),
            'extensionsRequired': doc.get('extensionsRequired', []), 'images': len(doc.get('images', [])),
        })
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
