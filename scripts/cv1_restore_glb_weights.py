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
from pathlib import Path

COMPONENT = {5121: ("B", 1), 5123: ("H", 2), 5126: ("f", 4)}


class RestoreError(ValueError):
    pass


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


if __name__ == "__main__":
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
