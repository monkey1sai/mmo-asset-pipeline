"""Merge P4 transition-check shards and write the runtime QA manifest (pure Python; run from the worktree root).

Usage: python -B scripts/cv1_p4_manifest.py <run dir with shard-*/> <transitions.json> <out dir>
Writes <out>/transition-check.json (all scenarios, per-gate counts by pair), <out>/transition-reference.json and the
binary (the shards' reference blocks, offsets rebased; float64 or float32 as the shards wrote them) and
<out>/p4-manifest.json for tools/runtime-qa/three/p4.html: the character GLB, every clip's runtime-owner GLB, its
interaction states per integer frame (states are linear between integer frames, so the runtime interpolates them
exactly), its stance windows, its sword socket block from the clip's closed-loop reference, the foot-lock data of the
reference (scripts/cv1_foot_lock.py), the rules and the scenarios that carry reference times.
"""
import hashlib
import json
import sys
from array import array
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_interaction as interaction

RULES = "assets/processed/ro-swordsman-character-v1/v001/b20-coatlie3/corrective-rules.json"
EXPORT = {"Idle": "a03/export-b20", "Walk": "a04/export-b20", "Run": "a02/export-b20", "Cast": "a04/export-b20", "LieDown": "a08/export",
          "Sleep": "a04/export", "GetUp": "a02/export"}
LOOP_QA = {"Idle": "a03-closed-loop-b20", "Walk": "a04-closed-loop-b20", "Run": "a02-closed-loop-b20", "Cast": "a04-closed-loop-b20",
           "LieDown": "a08-closed-loop", "Sleep": "a04-closed-loop", "GetUp": "a02-closed-loop"}


def info(path):
    path = ROOT / path
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main(run_dir, spec_path, out_dir):
    run_dir, out_dir = ROOT / run_dir, ROOT / out_dir
    spec = json.loads((ROOT / spec_path).read_text(encoding="utf-8"))
    shards = sorted(run_dir.glob("shard-*/transition-check.json"))
    checks = [json.loads(p.read_text(encoding="utf-8")) for p in shards]
    scenarios = sorted((s for c in checks for s in c["scenarios"]), key=lambda s: s["id"])
    expected = {s["id"] for s in spec["scenarios"]}
    if {s["id"] for s in scenarios} != expected:
        raise SystemExit(f"SHARDS_INCOMPLETE missing {sorted(expected - {s['id'] for s in scenarios})[:5]}")
    by_pair = defaultdict(lambda: defaultdict(int))
    for s in scenarios:
        by_pair[s["pair"]]["scenarios"] += 1
        by_pair[s["pair"]]["passed"] += s["pass"]
        for gate, ok in s["gates"].items():
            by_pair[s["pair"]][f"fail:{gate}"] += not ok
    out_dir.mkdir(parents=True, exist_ok=False)
    first = checks[0]
    merged = {k: first[k] for k in ("blender", "script_sha256", "foundation", "inputs", "thresholds", "scope")}
    merged.update({k: first[k] for k in ("modules", "foot_lock") if k in first})
    if any(c.get("script_sha256") != first["script_sha256"] or c.get("modules") != first.get("modules") for c in checks):
        raise SystemExit("SHARDS_RAN_DIFFERENT_CODE")
    merged.update({"observed_utc": max(c["observed_utc"] for c in checks), "shards": [p.relative_to(ROOT).as_posix() for p in shards],
                   "summary": {"scenarios": len(scenarios), "passed": sum(s["pass"] for s in scenarios), "by_pair": {k: dict(v) for k, v in by_pair.items()}},
                   "scenarios": scenarios})
    (out_dir / "transition-check.json").write_text(json.dumps(merged, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    # Each shard's blocks are relative to its own binary: rebase them by the values already merged.
    blob, rebased, layout, binary, foot_lock = None, [], None, None, None
    for p in sorted(run_dir.glob("shard-*/transition-reference.json")):
        ref = json.loads(p.read_text(encoding="utf-8"))
        layout, binary, foot_lock = layout or ref["mesh_layout"], binary or ref["binary"], foot_lock or ref.get("foot_lock")
        if ref["mesh_layout"] != layout or ref["binary"]["dtype"] != binary["dtype"] or ref.get("foot_lock") != foot_lock:
            raise SystemExit("SHARD_REFERENCES_DIFFER")
        code = {"float64 little-endian": "d", "float32 little-endian": "f"}[binary["dtype"]]
        blob = blob if blob is not None else array(code)
        rebased += [dict(block, offset_values=len(blob) + block["offset_values"]) for block in ref["blocks"]]
        data = array(code)
        data.frombytes((ROOT / ref["binary"]["path"]).read_bytes())
        blob.extend(data)
    bin_path = out_dir / ("transition-reference.f32.bin" if binary["dtype"].startswith("float32") else "transition-reference.f64.bin")
    bin_path.write_bytes(blob.tobytes())
    reference = {"observed_utc": merged["observed_utc"], "script_sha256": merged["script_sha256"], "inputs": merged["inputs"], "fps": 60,
                 "coordinates": "Blender world metres, Z up, -Y front; glTF (x, y, z) = Blender (x, z, -y)", "id_attribute": "_CV1_ID",
                 "binary": {**info(bin_path.relative_to(ROOT)), "dtype": binary["dtype"], "values_per_vertex": 3}, "mesh_layout": layout, "foot_lock": foot_lock,
                 "blocks": sorted(rebased, key=lambda b: b["label"]), "scope": "Transition reference samples merged from the shards."}
    (out_dir / "transition-reference.json").write_text(json.dumps(reference, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    clips = {}
    A, Q = "assets/processed/ro-swordsman-character-v1/v001/clips", "runs/qa/ro-swordsman-character-v1/v001/clips"
    for short, clip in spec["clips"].items():
        config = interaction.load(ROOT / clip["interaction"])
        export_dir = ROOT / A / clip["clip"] / EXPORT[short]
        glb = next(export_dir.glob("*_runtime_owner_stripped_exact_weights.glb"))
        last = config["frames"]
        states = {key: [interaction.state_value(config, key, f) for f in range(last + 1)] for key in sorted(config["states"])}
        loop_ref = json.loads((ROOT / Q / clip["clip"] / LOOP_QA[short] / "blender-reference.json").read_text(encoding="utf-8"))
        clips[short] = {"clip": clip["clip"], "glb": info(glb.relative_to(ROOT)), "frames": config["frames"], "loop": config["loop"], "fps": config["fps"],
                        "states_per_frame": states, "stance": config["stance"], "sword_socket": loop_ref.get("sword_socket"), "nominal_speed_m_s": clip["nominal_speed_m_s"]}
    manifest = {"schema_version": 1, "base": "Idle", "gate_m": 1e-5, "gate_source": "requests/ro-swordsman-character-v1-r6.json#runtime_contract.tolerances_m.runtime_cpu_evaluated_world",
                "determinism_gate_m": 1e-9, "determinism_source": "requests/ro-swordsman-character-v1-r6.json#transition_matrix.gates.determinism",
                "loop_seam": {"deg": 1.0, "m": 0.001}, "rules": info(RULES), "reference": info((out_dir / "transition-reference.json").relative_to(ROOT)),
                "reference_binary": reference["binary"], "foot_lock": foot_lock, "transitions": info(Path(spec_path)), "clips": clips,
                "scenarios": [s for s in spec["scenarios"] if s.get("reference_times")], "eval_fps": [30, 60, 120]}
    (out_dir / "p4-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"scenarios": len(scenarios), "passed": merged["summary"]["passed"], "reference_blocks": len(rebased), "by_pair": merged["summary"]["by_pair"]}, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
