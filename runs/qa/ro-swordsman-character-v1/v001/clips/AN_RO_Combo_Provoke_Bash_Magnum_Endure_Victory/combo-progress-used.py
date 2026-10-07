"""Writes combo-progress.json for AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory from the attempt records (run from the worktree root).

Usage: python -B .../combo-progress-used.py <recorded_utc> <current attempt, e.g. a07>
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CLIP = "AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory"
Q = Path("runs/qa/ro-swordsman-character-v1/v001/clips") / CLIP
A = Path("assets/processed/ro-swordsman-character-v1/v001/clips") / CLIP
now, current = sys.argv[1], sys.argv[2]


def check_summary(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    S = d["samples"]
    ranges, collapse_sites = [], Counter()
    for s in S:
        if s["collapsed_triangles"]:
            if ranges and s["t"] - ranges[-1][1] <= 1.0:
                ranges[-1][1] = s["t"]; ranges[-1][2] = min(ranges[-1][2], s["min_triangle_area_ratio"])
            else:
                ranges.append([s["t"], s["t"], s["min_triangle_area_ratio"]])
            for e in s.get("collapsed_examples", []):
                collapse_sites[f"{e['triangle']} {'/'.join(e['dominant'])}"] += 1
    hand = Counter()
    for s in S:
        for e in s["hand_examples"][:3]:
            hand[" vs ".join("+".join(b) for b in e["bones"])] += 1
    return {"path": path.as_posix(), "script_sha256": d["script_sha256"], "samples": d["sample_count"], "gates": d["gates"],
            "collapse_samples": sum(1 for s in S if s["collapsed_triangles"]), "min_area_ratio": round(min(s["min_triangle_area_ratio"] for s in S), 4),
            "collapse_ranges": [[a, b, round(c, 4)] for a, b, c in ranges], "collapse_sites": dict(collapse_sites.most_common(8)),
            "hand_fail_samples": sum(1 for s in S if s["hand_self_pairs"] or s["hand_other_new_pairs"]), "hand_pairs": dict(hand.most_common(6)),
            "grasp_fail_samples": sum(1 for s in S if not s["grasp"].get("pass", True)),
            "weapon_body_max_m": max(s["weapon_body"]["max_depth_m"] for s in S), "feet": d["feet"]}


attempts = {}
for folder in sorted(Q.glob("a0*")):
    if not folder.is_dir() or "-" in folder.name:
        continue
    att = folder.name
    entry = {}
    rep = folder / "author-report.json"
    if rep.exists():
        r = json.loads(rep.read_text(encoding="utf-8"))
        entry["author"] = {"spec_sha256": r["spec"]["sha256"], "ik": r.get("ik"), "blend": r["output"]["path"]}
    chk = Q / f"{att}-check-b20" / "clip-check.json"
    if chk.exists():
        entry["check"] = check_summary(chk)
    elif (Q / f"{att}-check-b20.note").exists():
        entry["check"] = (Q / f"{att}-check-b20.note").read_text(encoding="utf-8").strip()
    fx = A / att / "fx" / "fx-report.json"
    if fx.exists():
        f = json.loads(fx.read_text(encoding="utf-8"))
        entry["fx"] = {"glb": f["output"], "objects": len(f["objects"]), "triangles": f["triangles"], "windows": f["windows"]}
    loop = Q / f"{att}-closed-loop"
    if loop.exists():
        rb = next(loop.glob("roundtrip-*.json"), None)
        readback = json.loads(rb.read_text(encoding="utf-8")) if rb else None
        entry["closed_loop"] = {"export_manifest": (loop / "runtime-manifest.json").as_posix(),
                                "readback": {"path": rb.as_posix(), **{k: readback[k] for k in readback if k in ("pass", "max_error_m", "tolerance_m", "over_tolerance", "samples")}} if readback else None}
        runtime_dir = Path("runs/qa/ro-swordsman-character-v1/v001/clips/runtime")
        for res in sorted(runtime_dir.glob("*-runtime-results.json")):
            r = json.loads(res.read_text(encoding="utf-8"))
            if r["inputs"]["manifest"]["path"] == (loop / "runtime-manifest.json").as_posix():
                entry["closed_loop"]["runtime"] = {"results": res.as_posix(), "pass": r["pass"], "summary": r.get("summary")}
    gen = Q / "prep" / f"spec-{att}-used.py"
    if gen.exists():
        entry["spec_generator"] = gen.as_posix()
    attempts[att] = entry
progress = {
    "schema_version": 1, "recorded_utc": now, "clip": CLIP, "current_attempt": current,
    "authorization": "runs/qa/ro-swordsman-character-v1/authorizations.json entries 27 (Hyper3D paid allowed), 28 (start the combo) and 29 (H1: close a07 with known failures, then export, runtime, transitions, art review)",
    "status": "a07 closed with known failures per entry 29 (collapse 254/671 samples, 184 of them the frozen guard pose's own triangle; grasp 3 transitional samples); export, readback and runtime closed loop pass; Idle<->Combo transitions and art review pending",
    "plan": (Q / "combo-plan.md").as_posix(),
    "interaction_config": {"path": (A / "interaction.json").as_posix(), "registry": "runs/qa/ro-swordsman-character-v1/v001/clips/interaction-registry.json"},
    "attempts": attempts,
    "tool_changes": ["scripts/cv1_author_clip.py: a partial named pose blends from the bone's current rotation (an earlier pose), not from rest",
                     "scripts/cv1_fx_layer.py: new separate effects layer builder (procedural FX meshes keyed to the clip events)",
                     "scripts/cv1_p4_scenarios.py / cv1_p4_manifest.py: Idle->Combo and Combo->Idle pairs, Combo clip export mapping"],
    "diagnostics": [p.as_posix() for p in sorted((Q / "prep").glob("*-used.py"))],
    "hyper3d": {"used": False, "balance_readonly": {"observed_utc": "2026-10-07T02:36:09Z", "balance": 224, "charged": False},
                "reason": "the combo is a skeletal clip and the effects are procedural meshes; no generation input was needed"},
    "known_deviations": ["slash end sweeps down to the front-right instead of the action sheet's forward-down cut: the frozen grasp holds the blade roughly opposite the forearm",
                         "the magnum chop is the raised two-hand guard pressed down by a 45 deg body lean; the blade ends near horizontal, not into the ground",
                         "the frozen two_hand_chop pose alone collapses triangle 28476 (upper_arm.R, area ratio 0.047) on b20 with the correctives on: every guard sample carries it"],
}
(Q / "combo-progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"attempts": {k: ("check" in v and (v["check"]["gates"] if isinstance(v["check"], dict) else v["check"])) for k, v in attempts.items()}}, ensure_ascii=False)[:1500])
