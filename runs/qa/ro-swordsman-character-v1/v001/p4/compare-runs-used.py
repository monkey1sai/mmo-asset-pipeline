"""Compare P4 run-01 and run-02 merged transition checks (run from the worktree root; prints JSON, writes nothing).

Usage: python -B runs/qa/ro-swordsman-character-v1/v001/p4/compare-runs-used.py <run-01 merged check> <run-02 merged check>
Per pair: scenarios passed and failing gates in each run; for run-02 the worst feet slide, the settle steps (lift and
travel), the height-only contact diagnostic, the collapsing triangles (with their dominant bones and whether the foot
lock was active), bed clearance and weapon/grasp failures, and the continuity rows.
"""
import json
import sys
from collections import Counter, defaultdict


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def by_pair(check):
    out = defaultdict(lambda: {"scenarios": 0, "passed": 0, "failing": Counter()})
    for s in check["scenarios"]:
        row = out[s["pair"]]
        row["scenarios"] += 1
        row["passed"] += s["pass"]
        row["failing"].update(k for k, ok in s["gates"].items() if not ok)
    return out


def main(first, second):
    a, b = load(first), load(second)
    pa, pb = by_pair(a), by_pair(b)
    pairs = {}
    for pair in sorted(set(pa) | set(pb)):
        pairs[pair] = {"run_01": f"{pa[pair]['passed']}/{pa[pair]['scenarios']} {dict(pa[pair]['failing'])}",
                       "run_02": f"{pb[pair]['passed']}/{pb[pair]['scenarios']} {dict(pb[pair]['failing'])}"}
    feet, settles, contact = defaultdict(float), [], defaultdict(float)
    collapse, bed, weapon, continuity = defaultdict(Counter), Counter(), defaultdict(list), []
    for s in b["scenarios"]:
        for side, f in s["worst"]["feet"].items():
            feet[s["pair"]] = max(feet[s["pair"]], f["slide_m"])
            contact[s["pair"]] = max(contact[s["pair"]], f["contact_slide_diagnostic_m"])
            for st in f["settles"]:
                settles.append({"id": s["id"], "side": side, "lift_mm": round(st["max_lift_m"] * 1e3, 1), "travel_mm": round(st["travel_m"] * 1e3, 1)})
        for c in s["worst"]["continuity"]:
            if not c["pass"]:
                continuity.append({"id": s["id"], **c})
        for r in s["rows"]:
            for e in r.get("collapsed_examples", []):
                locked = any(r.get("foot_lock", {}).values())
                collapse[s["pair"]][(e["triangle"], "/".join(e["dominant"]), "lock" if locked else "free")] += 1
            if "bed_clearance" in r and not r["bed_clearance"]["pass"]:
                bed[(s["pair"], r["bed_clearance"].get("other_mesh"))] += 1
            if r["weapon_body_m"] > 0.001 or not r["grasp"]["pass"]:
                weapon[s["id"]].append(r["t"])
    report = {
        "summary": {"run_01": f"{sum(s['pass'] for s in a['scenarios'])}/{len(a['scenarios'])}", "run_02": f"{sum(s['pass'] for s in b['scenarios'])}/{len(b['scenarios'])}"},
        "by_pair": pairs,
        "run_02_feet_slide_worst_mm": {k: round(v * 1e3, 2) for k, v in sorted(feet.items())},
        "run_02_contact_diagnostic_worst_mm": {k: round(v * 1e3, 1) for k, v in sorted(contact.items())},
        "run_02_settles": {"count": len(settles), "lift_mm_min_max": [min((x["lift_mm"] for x in settles), default=None), max((x["lift_mm"] for x in settles), default=None)],
                           "travel_mm_max": max((x["travel_mm"] for x in settles), default=None), "largest": sorted(settles, key=lambda x: -x["travel_mm"])[:5]},
        "run_02_collapse": {pair: {f"{t}|{bones}|{mode}": n for (t, bones, mode), n in c.most_common(6)} for pair, c in sorted(collapse.items())},
        "run_02_bed_clearance_failures": {f"{p}|{m}": n for (p, m), n in bed.items()},
        "run_02_weapon_grasp_failures": {k: len(v) for k, v in weapon.items()},
        "run_02_continuity_failures": continuity[:10],
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
