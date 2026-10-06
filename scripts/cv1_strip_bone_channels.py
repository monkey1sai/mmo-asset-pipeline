"""Remove the animation channels of named nodes from a GLB, so a runtime evaluator is their only writer.

Usage: python -B scripts/cv1_strip_bone_channels.py <in.glb> <out.glb> <node,node,...> [report.json]
Only the JSON chunk changes: channels targeting the named nodes are removed and the samplers they used are dropped
and re-indexed. The BIN chunk is copied unchanged (the dropped accessors stay in the buffer, unused).
Existing outputs are refused.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path


def strip(blob, names):
    if blob[:4] != b"glTF":
        raise ValueError("NOT_GLB")
    json_length = struct.unpack_from("<I", blob, 12)[0]
    document = json.loads(blob[20:20 + json_length].decode("utf-8"))
    rest = blob[20 + json_length:]
    nodes = {i for i, node in enumerate(document["nodes"]) if node.get("name") in names}
    missing = set(names) - {document["nodes"][i]["name"] for i in nodes}
    if missing:
        raise ValueError(f"NODES_NOT_FOUND {sorted(missing)}")
    removed = 0
    for animation in document.get("animations", []):
        keep = [c for c in animation["channels"] if c["target"].get("node") not in nodes]
        removed += len(animation["channels"]) - len(keep)
        used = sorted({c["sampler"] for c in keep})
        remap = {old: new for new, old in enumerate(used)}
        animation["samplers"] = [animation["samplers"][i] for i in used]
        for channel in keep:
            channel["sampler"] = remap[channel["sampler"]]
        animation["channels"] = keep
    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    body = struct.pack("<I4s", len(text), b"JSON") + text + rest
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body, removed


if __name__ == "__main__":
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    names = [n for n in sys.argv[3].split(",") if n]
    data = source.read_bytes()
    out, removed = strip(data, names)
    with open(target, "xb") as handle:
        handle.write(out)
    report = {"input": {"path": source.as_posix(), "sha256": hashlib.sha256(data).hexdigest()}, "output": {"path": target.as_posix(), "sha256": hashlib.sha256(out).hexdigest(), "bytes": len(out)},
              "nodes": names, "channels_removed": removed, "bin_chunk_unchanged": data[20 + struct.unpack_from("<I", data, 12)[0]:] == out[20 + struct.unpack_from("<I", out, 12)[0]:]}
    if len(sys.argv) > 4:
        with open(sys.argv[4], "x", encoding="utf-8", newline=chr(10)) as handle:
            json.dump(report, handle, indent=1)
    print(json.dumps({"channels_removed": removed, "bin_chunk_unchanged": report["bin_chunk_unchanged"]}))
