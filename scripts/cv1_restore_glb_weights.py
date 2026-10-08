"""Restore the source skin weights in a GLB after Blender's exporter drops influences <= 1e-4.

Usage: python -B scripts/cv1_restore_glb_weights.py <in.glb> <weights-snapshot.json> <out.glb> [report.json]
Each primitive carrying the original-vertex-ID attribute gets its JOINTS_0 and WEIGHTS_0 payload rewritten
from the snapshot; every other byte of the file stays identical and the input is never modified.
The snapshot comes from scripts/cv1_weights_snapshot.py (float32 weights as stored in the BLEND).
"""
import hashlib
import json
import struct
import sys
import math
from pathlib import Path

COMPONENT = {5121: ("B", 1), 5123: ("H", 2), 5126: ("f", 4)}


class RestoreError(ValueError):
    pass


def patch_vertices(blob, node_name, changes):
    """Patch explicit primitive-local POSITION IDs, preserving all other bytes.

    This checks integrity only. Caller must establish semantic scope, rights,
    budget and actual deformation/visual acceptance before using the result.
    One primitive, non-interleaved FLOAT weights and byte/ushort joints only.
    """
    try:
        document, bin_start, bin_length = split_glb(blob)
        if struct.unpack_from('<I', blob, 8)[0] != len(blob) or bin_start + bin_length != len(blob):
            raise RestoreError('GLB_LENGTH')
        if len(document['buffers']) != 1 or 'uri' in document['buffers'][0]:
            raise RestoreError('EMBEDDED_ONLY')
        buffer_length = document['buffers'][0]['byteLength']
        if type(buffer_length) is not int or not 0 <= buffer_length <= bin_length:
            raise RestoreError('BUFFER_LENGTH')
        for view in document['bufferViews']:
            if type(view.get('buffer', 0)) is not int or view.get('buffer', 0) != 0:
                raise RestoreError('BUFFER_INDEX')
            if any(type(view.get(key, 0)) is not int or view.get(key, 0) < 0 for key in ('byteOffset', 'byteLength')):
                raise RestoreError('BUFFER_VIEW_RANGE')
            if 'byteLength' not in view or view.get('byteOffset', 0) + view['byteLength'] > buffer_length:
                raise RestoreError('BUFFER_VIEW_RANGE')
            if 'byteStride' in view and (type(view['byteStride']) is not int or view['byteStride'] <= 0):
                raise RestoreError('BUFFER_VIEW_STRIDE')
        if not isinstance(node_name,str) or not node_name:
            raise RestoreError('NODE_NAME')
        nodes = document['nodes']
        matches = [n for n in nodes if n.get('name') == node_name]
        if len(matches) != 1 or 'mesh' not in matches[0] or 'skin' not in matches[0]:
            raise RestoreError('SKINNED_NODE_UNIQUE')
        node = matches[0]
        if any(type(node[key]) is not int or not 0 <= node[key] < len(document[collection]) for key,collection in [('mesh','meshes'),('skin','skins')]):
            raise RestoreError('NODE_INDEX')
        primitives = document['meshes'][node['mesh']]['primitives']
        if len(primitives) != 1:
            raise RestoreError('EXPLICIT_SINGLE_PRIMITIVE_REQUIRED')
        attrs = primitives[0]['attributes']
        if any(type(attrs.get(name)) is not int or not 0 <= attrs[name] < len(document['accessors']) for name in ['POSITION','JOINTS_0','WEIGHTS_0']):
            raise RestoreError('ATTRIBUTE_INDEX')
        if 'JOINTS_1' in attrs or 'WEIGHTS_1' in attrs:
            raise RestoreError('UNSUPPORTED_WEIGHT_LAYOUT')
        count = document['accessors'][attrs['POSITION']]['count']
        if type(count) is not int or count <= 0:
            raise RestoreError('VERTEX_COUNT')
        joint_ids = document['skins'][node['skin']]['joints']
        if not joint_ids or any(type(j) is not int or not 0 <= j < len(nodes) for j in joint_ids) or len(set(joint_ids)) != len(joint_ids):
            raise RestoreError('JOINT_INDEX')
        bone_names = [nodes[j].get('name') for j in joint_ids]
        if any(not isinstance(n,str) or not n for n in bone_names) or len(set(bone_names)) != len(bone_names):
            raise RestoreError('BONE_NAMES_UNIQUE')
        bone_index = {n:i for i,n in enumerate(bone_names)}
        spans = []
        for name in ['JOINTS_0','WEIGHTS_0']:
            ai = attrs[name]; ac = document['accessors'][ai]
            if type(ac.get('bufferView')) is not int or not 0 <= ac['bufferView'] < len(document['bufferViews']):
                raise RestoreError('BUFFER_VIEW_INDEX')
            if type(ac.get('byteOffset', 0)) is not int or ac.get('byteOffset', 0) < 0:
                raise RestoreError('ACCESSOR_OFFSET')
            if type(ac.get('count')) is not int or type(ac.get('componentType')) is not int:
                raise RestoreError('ACCESSOR_COUNT')
            view = document['bufferViews'][ac['bufferView']]
            offset, letter, _, _ = accessor_span(document, ai, count, 'VEC4')
            size = struct.calcsize('<'+letter)
            if ac.get('normalized') or (name == 'WEIGHTS_0' and letter != 'f') or (name == 'JOINTS_0' and letter not in ('B','H')):
                raise RestoreError('UNSUPPORTED_WEIGHT_LAYOUT')
            length = count * 4 * size
            view_start = view.get('byteOffset',0)
            if offset < view_start or offset+length > view_start+view['byteLength'] or offset+length > document['buffers'][0]['byteLength'] or offset+length > bin_length:
                raise RestoreError('ACCESSOR_BOUNDS')
            if offset % size:
                raise RestoreError('ACCESSOR_ALIGNMENT')
            spans.append((bin_start+offset,length,letter,size,ai))
        # Reject aliased payload: another accessor/mesh may otherwise change too.
        for k,(start,length,_,_,ai) in enumerate(spans):
            for vi,view in enumerate(document['bufferViews']):
                if vi == document['accessors'][ai]['bufferView']: continue
                other = bin_start+view.get('byteOffset',0)
                if max(start,other) < min(start+length,other+view['byteLength']):
                    raise RestoreError('ALIASED_BUFFER_VIEW')
            def view_references(value, view_index):
                if isinstance(value, dict):
                    return sum(int(key == 'bufferView' and item == view_index) + view_references(item, view_index)
                               for key, item in value.items())
                if isinstance(value, list):
                    return sum(view_references(item, view_index) for item in value)
                return 0
            if view_references(document, document['accessors'][ai]['bufferView']) != 1:
                raise RestoreError('ALIASED_ACCESSOR')
            references = 0
            for mesh in document['meshes']:
                for primitive in mesh['primitives']:
                    references += sum(value == ai for value in primitive.get('attributes', {}).values())
                    references += int(primitive.get('indices') == ai)
                    references += sum(value == ai for target in primitive.get('targets', []) for value in target.values())
            references += sum(sampler.get(key) == ai for animation in document.get('animations', [])
                              for sampler in animation.get('samplers', []) for key in ('input', 'output'))
            references += sum(skin.get('inverseBindMatrices') == ai for skin in document['skins'])
            if references != 1:
                raise RestoreError('SHARED_SKIN_ACCESSOR')
            if sum(n.get('mesh') == node['mesh'] for n in nodes) != 1:
                raise RestoreError('SHARED_MESH')
        if not isinstance(changes,list) or not changes:
            raise RestoreError('EMPTY_PATCH')
        out = bytearray(blob); allowed = set(); seen = set()
        for row in changes:
            if not isinstance(row,dict) or set(row) != {'vertex','weights'}:
                raise RestoreError('PATCH_ROW')
            vid = row['vertex']; weights = row['weights']
            if type(vid) is not int or not 0 <= vid < count or vid in seen:
                raise RestoreError('PATCH_VERTEX')
            seen.add(vid)
            if not isinstance(weights,dict) or not 1 <= len(weights) <= 4 or any(n not in bone_index for n in weights):
                raise RestoreError('PATCH_BONE')
            if any(type(w) not in (int,float) or not math.isfinite(w) or not 0 < w <= 1 for w in weights.values()) or abs(sum(weights.values())-1) > 1e-6:
                raise RestoreError('PATCH_WEIGHT_SUM')
            ordered = sorted(weights.items(),key=lambda item:(-item[1],item[0]))
            joints = [bone_index[n] for n,w in ordered]+[0]*(4-len(ordered))
            values = [w for n,w in ordered]+[0.]*(4-len(ordered))
            for (base,_,letter,size,_), values4 in zip(spans,[joints,values]):
                offset = base+vid*4*size
                struct.pack_into('<4'+letter,out,offset,*values4)
                allowed.update(range(offset,offset+4*size))
        changed = [i for i,(a,b) in enumerate(zip(blob,out)) if a != b]
        if len(out) != len(blob) or not set(changed) <= allowed:
            raise RestoreError('CHANGE_OUTSIDE_SELECTED_SKIN_SLOTS')
        return bytes(out), {'original_vertex_ids':sorted(seen),'changed_bytes':len(changed),
                            'all_other_bytes_identical':True,'acceptance':'NOT_RUN'}
    except (KeyError,IndexError,TypeError,struct.error) as error:
        raise RestoreError('MALFORMED_PATCH_INPUT') from error


def split_glb(blob):
    if blob[:4] != b"glTF" or struct.unpack_from("<I", blob, 4)[0] != 2:
        raise RestoreError("NOT_GLB_V2")
    json_length, json_type = struct.unpack_from("<I4s", blob, 12)
    if json_type != b"JSON":
        raise RestoreError("MISSING_JSON_CHUNK")
    document = json.loads(blob[20:20 + json_length].decode("utf-8"))
    bin_header = 20 + json_length
    bin_length, bin_type = struct.unpack_from("<I4s", blob, bin_header)
    if bin_type != b"BIN\x00":
        raise RestoreError("MISSING_BIN_CHUNK")
    return document, bin_header + 8, bin_length


def accessor_span(document, index, expected_count, expected_type):
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    letter, size = COMPONENT[accessor["componentType"]]
    width = {"SCALAR": 1, "VEC4": 4}[accessor["type"]]
    if accessor["type"] != expected_type or accessor["count"] != expected_count or view.get("buffer", 0) != 0 or "sparse" in accessor:
        raise RestoreError("UNSUPPORTED_ACCESSOR")
    if view.get("byteStride") not in (None, size * width):
        raise RestoreError("INTERLEAVED_BUFFER_VIEW")
    return view.get("byteOffset", 0) + accessor.get("byteOffset", 0), letter, width, accessor["count"]


def restore(blob, snapshot):
    """Return (new_blob, report). Raises RestoreError instead of guessing."""
    document, bin_start, _ = split_glb(blob)
    out = bytearray(blob)
    attribute = snapshot["id_attribute"]
    nodes = document["nodes"]
    report = {"id_attribute": attribute, "meshes": [], "changed_bytes": 0}
    touched = []
    for node in nodes:
        if "mesh" not in node or "skin" not in node:
            continue
        mesh = document["meshes"][node["mesh"]]
        if not any(attribute in p["attributes"] for p in mesh["primitives"]):
            continue
        if node.get("name") not in snapshot["meshes"]:
            raise RestoreError(f"MESH_NOT_IN_SNAPSHOT:{node.get('name')}")
        source = snapshot["meshes"][node["name"]]["weights"]
        joint_index = {nodes[j].get("name"): i for i, j in enumerate(document["skins"][node["skin"]]["joints"])}
        row = {"mesh": node["name"], "export_vertices": 0, "vertices_with_restored_influence": 0, "max_l1_before": 0.0}
        for primitive in mesh["primitives"]:
            attrs = primitive["attributes"]
            if attribute not in attrs:
                raise RestoreError(f"PRIMITIVE_WITHOUT_ID:{node['name']}")
            count = document["accessors"][attrs[attribute]]["count"]
            id_offset, id_letter, _, _ = accessor_span(document, attrs[attribute], count, "SCALAR")
            joint_offset, joint_letter, _, _ = accessor_span(document, attrs["JOINTS_0"], count, "VEC4")
            weight_offset, weight_letter, _, _ = accessor_span(document, attrs["WEIGHTS_0"], count, "VEC4")
            if weight_letter != "f" or "JOINTS_1" in attrs:
                raise RestoreError("UNSUPPORTED_WEIGHT_LAYOUT")
            ids = struct.unpack_from(f"<{count}{id_letter}", blob, bin_start + id_offset)
            old_joints = struct.unpack_from(f"<{count * 4}{joint_letter}", blob, bin_start + joint_offset)
            old_weights = struct.unpack_from(f"<{count * 4}f", blob, bin_start + weight_offset)
            new_joints, new_weights = [], []
            for i, raw_id in enumerate(ids):
                vertex = int(round(raw_id))
                if abs(raw_id - vertex) > 1e-4 or not 0 <= vertex < len(source):
                    raise RestoreError(f"BAD_VERTEX_ID:{node['name']}:{raw_id}")
                influences = sorted(((w, b) for b, w in source[vertex] if w > 0), reverse=True)
                if not influences or len(influences) > 4:
                    raise RestoreError(f"UNSUPPORTED_INFLUENCE_COUNT:{node['name']}:{vertex}:{len(influences)}")
                if any(b not in joint_index for _, b in influences):
                    raise RestoreError(f"BONE_NOT_IN_SKIN:{node['name']}:{vertex}")
                before = {old_joints[4 * i + k]: old_weights[4 * i + k] for k in range(4) if old_weights[4 * i + k] > 0}
                after = {joint_index[b]: w for w, b in influences}
                total = sum(after.values())
                l1 = sum(abs(before.get(k, 0.0) - after.get(k, 0.0) / total) for k in set(before) | set(after))
                row["max_l1_before"] = max(row["max_l1_before"], l1)
                if set(after) - set(before):
                    row["vertices_with_restored_influence"] += 1
                padded = [(joint_index[b], w) for w, b in influences] + [(0, 0.0)] * (4 - len(influences))
                new_joints.extend(j for j, _ in padded)
                new_weights.extend(w for _, w in padded)
            struct.pack_into(f"<{count * 4}{joint_letter}", out, bin_start + joint_offset, *new_joints)
            struct.pack_into(f"<{count * 4}f", out, bin_start + weight_offset, *new_weights)
            touched.append((bin_start + joint_offset, count * 4 * COMPONENT[{"B": 5121, "H": 5123}[joint_letter]][1]))
            touched.append((bin_start + weight_offset, count * 16))
            row["export_vertices"] += count
        report["meshes"].append(row)
    if not report["meshes"]:
        raise RestoreError("NO_PRIMITIVE_WITH_ID_ATTRIBUTE")
    allowed = set()
    for start, length in touched:
        allowed.update(range(start, start + length))
    changed = [i for i, (a, b) in enumerate(zip(blob, out)) if a != b]
    if len(out) != len(blob) or not set(changed) <= allowed:
        raise RestoreError("CHANGE_OUTSIDE_SKIN_PAYLOAD")
    report["changed_bytes"] = len(changed)
    report["all_other_bytes_identical"] = True
    return bytes(out), report


def patch_main(argv=None):
    """Request-bound local prototype CLI. Review declarations are not approval."""
    import argparse
    import identity
    import art_sources
    import workbench
    from blender_art_preview import embedded_glb_only
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=patch_main.__doc__)
    for name in ('request','source-root','asset','sha256','profile','out'):
        parser.add_argument('--'+name,required=True)
    args = parser.parse_args(argv)
    request = identity.read_json(identity.command_path(root,args.request))
    if workbench.validate_request(request) or request['task_type'] != 'rigged_character':
        raise RestoreError('REQUEST_INVALID')
    profile = identity.read_json(identity.command_path(root,args.profile))
    if not isinstance(profile,dict):
        raise RestoreError('PROFILE_INVALID')
    if profile.get('request_sha256') != identity.json_digest(request) or profile.get('source_sha256') != args.sha256:
        raise RestoreError('PROFILE_BINDING')
    review = profile.get('review',{})
    if not isinstance(review,dict) or review.get('status') != 'local_prototype_accepted' or not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():
        raise RestoreError('LOCAL_SCOPE_REVIEW_REQUIRED')
    ids = review.get('original_vertex_ids')
    changes = profile.get('changes')
    if not isinstance(ids,list) or not ids or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids) or not isinstance(changes,list) or any(not isinstance(row,dict) or type(row.get('vertex')) is not int for row in changes) or sorted(ids) != sorted(row['vertex'] for row in changes):
        raise RestoreError('REVIEWED_MASK_MISMATCH')
    evidence = review.get('evidence',{})
    if not isinstance(evidence,dict):
        raise RestoreError('REVIEW_EVIDENCE_REQUIRED')
    evidence_path = art_sources.no_symlinks(root,art_sources.safe_relative(evidence.get('path','')))
    if identity.file_digest(evidence_path) != evidence.get('sha256'):
        raise RestoreError('REVIEW_EVIDENCE_DRIFT')
    source_root = Path(args.source_root)
    source = art_sources.no_symlinks(source_root,art_sources.safe_relative(args.asset))
    if identity.file_digest(source) != args.sha256:
        raise RestoreError('SOURCE_DRIFT')
    embedded_glb_only(source)
    relative = identity.command_path(root,args.out).relative_to(root).as_posix()
    art_sources.safe_relative(relative)
    if not relative.startswith('assets/processed/') or not relative.endswith('.glb'):
        raise RestoreError('OUTPUT_SCOPE')
    output = art_sources.no_symlinks(root,relative)
    report_path = output.with_suffix('.json')
    if output.exists() or report_path.exists():
        raise RestoreError('OUTPUT_EXISTS')
    blob = source.read_bytes()
    result,report = patch_vertices(blob,profile.get('mesh'),changes)
    if identity.file_digest(source) != args.sha256:
        raise RestoreError('SOURCE_DRIFT')
    report.update(request_sha256=identity.json_digest(request),profile_sha256=identity.json_digest(profile),
                  source_sha256=args.sha256,output_sha256=hashlib.sha256(result).hexdigest(),
                  review_evidence_sha256=evidence['sha256'],review_status='DECLARED_NOT_AUTHENTICATED',
                  game_ready=False,source_rights='CALLER_SCOPE_NOT_PUBLIC_REDISTRIBUTION_APPROVAL')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as handle:handle.write(result)
    with report_path.open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    if len(sys.argv)>1 and sys.argv[1]=='--patch':
        try:
            raise SystemExit(patch_main(sys.argv[2:]))
        except (ValueError,FileNotFoundError) as error:
            print(str(error),file=sys.stderr)
            raise SystemExit(2)
    source_path, snapshot_path, target_path = (Path(p) for p in sys.argv[1:4])
    data = source_path.read_bytes()
    result, summary = restore(data, json.loads(snapshot_path.read_text(encoding="utf-8")))
    with open(target_path, "xb") as handle:
        handle.write(result)
    summary.update({"input": {"path": source_path.as_posix(), "sha256": hashlib.sha256(data).hexdigest()},
                    "output": {"path": target_path.as_posix(), "sha256": hashlib.sha256(result).hexdigest(), "bytes": len(result)},
                    "snapshot": {"path": snapshot_path.as_posix(), "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest()}})
    if len(sys.argv) > 4:
        with open(sys.argv[4], "x", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=1)
    print(json.dumps({"changed_bytes": summary["changed_bytes"], "restored": {m["mesh"]: m["vertices_with_restored_influence"] for m in summary["meshes"]}}))
