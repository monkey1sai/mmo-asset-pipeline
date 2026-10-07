"""Re-evaluate the feet gate of a merged P4 check with the corrected lift rule (run from the worktree root).

Usage: python -B runs/qa/ro-swordsman-character-v1/v001/p4/feet-recheck-used.py <merged transition-check.json> <out.json>
The run-04 check let any stance sample whose sole rose more than 5 mm above the lowest stance height end its run. That
was meant for the settle step (a synthesised swing) but also hid locks the leg could not reach (the foot lifted while
held). Corrected rule, the same as scripts/cv1_transition_check.py from this fix on: only samples inside a release or
settle of that foot may leave the run by lifting; a stance sample in a lock, or with no lock, always counts. The gate
is a function of the stored per-sample measurements (sole centroid, lowest sole height, stance, blended speed, time,
foot-lock mode), so it is recomputed from the merged rows without re-running Blender.
"""
import json
import sys
from pathlib import Path

LIFT_BREAK_M, SLIDE_M = 0.005, 2 * 0.005
FORWARD = (0.0, -1.0)  # contract forward (Blender -Y), horizontal part


def runs_slide(rows, side, member):
    worst, runs, run = 0.0, 0, []
    for row in rows + [None]:
        if row is not None and member(row):
            run.append(row)
            continue
        if len(run) > 1:
            runs += 1
            drift, first = 0.0, run[0]
            fx, fy = first["feet"][side]["centroid_xy"]
            for prev, cur in zip(run, run[1:]):
                drift += 0.5 * (prev["speed_mps"] + cur["speed_mps"]) * (cur["t"] - prev["t"])
                ex, ey = fx + FORWARD[0] * (-drift), fy + FORWARD[1] * (-drift)
                cx, cy = cur["feet"][side]["centroid_xy"]
                worst = max(worst, ((cx - ex) ** 2 + (cy - ey) ** 2) ** 0.5)
        run = []
    return worst, runs


def main(check_path, out_path):
    check = json.loads(Path(check_path).read_text(encoding="utf-8"))
    out, changed = [], []
    for s in check["scenarios"]:
        feet = {}
        for side in ("L", "R"):
            stance_z = [r["feet"][side]["min_z"] for r in s["rows"] if r["feet"][side]["stance"]]
            ground = min(stance_z) if stance_z else float("inf")

            def member(r, side=side, ground=ground):
                if not r["feet"][side]["stance"]:
                    return False
                lifted = r["feet"][side]["min_z"] > ground + LIFT_BREAK_M
                return not (lifted and r.get("foot_lock", {}).get(side) in ("release", "settle"))

            slide, runs = runs_slide(s["rows"], side, member)
            locked_lift = max([r["feet"][side]["min_z"] - ground for r in s["rows"] if r["feet"][side]["stance"] and r.get("foot_lock", {}).get(side) == "lock"], default=0.0)
            feet[side] = {"slide_m": slide, "runs": runs, "locked_lift_max_m": max(0.0, locked_lift), "pass": slide <= SLIDE_M,
                          "stored_slide_m": s["worst"]["feet"][side]["slide_m"]}
        gates = dict(s["gates"], feet_slide=all(f["pass"] for f in feet.values()))
        row = {"id": s["id"], "pair": s["pair"], "feet": feet, "gates": gates, "pass": all(gates.values()), "stored_pass": s["pass"]}
        out.append(row)
        if row["pass"] != s["pass"] or gates["feet_slide"] != s["gates"]["feet_slide"]:
            changed.append({"id": s["id"], "feet_mm": {k: round(v["slide_m"] * 1e3, 1) for k, v in feet.items()},
                            "locked_lift_mm": {k: round(v["locked_lift_max_m"] * 1e3, 1) for k, v in feet.items()}})
    record = {"source": check_path, "script_sha256": check["script_sha256"], "rule": __doc__.strip().splitlines()[0],
              "summary": {"scenarios": len(out), "passed": sum(r["pass"] for r in out), "stored_passed": sum(r["stored_pass"] for r in out),
                          "feet_failures": sum(not r["gates"]["feet_slide"] for r in out)},
              "changed": changed, "scenarios": out}
    Path(out_path).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"summary": record["summary"], "changed": changed}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
