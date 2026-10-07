"""Classify the collapse failures of a merged P4 transition check with the Blender probe (run from the worktree root).

  python -B .../classify-collapse-used.py list <merged transition-check.json>
      prints the probe argument: per scenario and collapsing triangle, the sample where it is smallest
  python -B .../classify-collapse-used.py classify <merged transition-check.json> <probe.json>
      prints JSON: per probed sample the triangle's area ratio and neighbour agreement in the evaluated blend, the
      same blend without the foot lock and each layer alone, and a class:
      - foot_lock: under 5 % only with the foot lock (the lock moves the leg through it);
      - folded_in_clip: under 5 % without the lock too, and some layer alone has it folded (agreement < 0) or under 5 %;
      - blend: under 5 % without the lock while every layer alone has it open and above 5 %.
"""
import json
import sys
from collections import Counter

GATE = 0.05


def worst_samples(check):
    out = {}
    for s in check["scenarios"]:
        for r in s["rows"]:
            for e in r.get("collapsed_examples", [])[:1]:
                key = (s["id"], e["triangle"])
                if key not in out or r["min_area_ratio"] < out[key][1]:
                    out[key] = (r["t"], r["min_area_ratio"])
    return out


def main(mode, check_path, probe_path=None):
    check = json.load(open(check_path, encoding="utf-8"))
    samples = worst_samples(check)
    if mode == "list":
        print(";".join(sorted({f"{sid}@{t}" for (sid, _), (t, _) in samples.items()})))
        return
    probe = json.load(open(probe_path, encoding="utf-8"))
    by_sample = {(e["id"], round(e["t"], 9)): e for e in probe["probes"]}
    pair_of = {s["id"]: s["pair"] for s in check["scenarios"]}
    rows, classes = [], Counter()
    for (sid, triangle), (t, _) in sorted(samples.items()):
        e = by_sample[(sid, round(t, 9))]
        key = str(triangle)
        snaps = {label: (snap["watch_ratios"].get(key), snap["watch_neighbour_agreement"].get(key)) for label, snap in e["snapshots"].items()}
        if None in snaps["blend"]:
            continue
        locked, unlocked = snaps["blend"][0], snaps["blend_without_foot_lock"][0]
        alone = [v for label, v in snaps.items() if label.startswith("only:")]
        if unlocked >= GATE and locked < GATE:
            kind = "foot_lock"
        elif any(ratio < GATE or (agree is not None and agree < 0) for ratio, agree in alone):
            kind = "folded_in_clip"
        else:
            kind = "blend"
        classes[(pair_of[sid], kind)] += 1
        rows.append({"id": sid, "t": t, "triangle": triangle, "class": kind, "ratio_and_agreement": snaps})
    print(json.dumps({"classes_by_pair": {f"{p}|{k}": n for (p, k), n in sorted(classes.items())}, "samples": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
