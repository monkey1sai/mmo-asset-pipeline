"""Print a compact table from a joint-range result. Usage: python -B scripts/cv1_joint_range_summary.py <joint-range-result.json>"""
import json
import sys

result = json.load(open(sys.argv[1], encoding="utf-8"))
print("subject", result["subject"]["path"], "bones", result["bones"], "soup", result["soup"])
print("rest pairs", result["rest_pairs"], "rest gate", result["rest_gate"], "calibration", result["calibration_run"])
print("numeric_gate_pass", result["numeric_gate_pass"], "measured", result["measured"], "missing", result["missing"])
MARK = {"direction": "D", "deforms": "M", "no_collapse": "C", "hand_self_intersection_zero": "H", "hand_other_new_intersection_zero": "X",
        "hand_shape_guard": "G", "other_intersections_within_ceiling": "O", "other_stretch_within_ceiling": "S"}
for row in result["results"]:
    if row["status"] != "measured":
        print(f"{row['id']:<32} {row['status'].upper()} {row['missing']}")
        continue
    t, e = row["levels"]["typical"], row["levels"]["extreme"]
    flags = "".join(MARK[k] for k, ok in row["gate"].items() if not ok)
    cell = lambda r: f"c{r['collapsed_triangles']} hs{r['hand_self_pairs']} hx{r['hand_other_new_pairs']} o{r['other_new_pairs']}"
    print(f"{row['id']:<32} {'PASS' if row['pass'] else 'FAIL ' + flags:<12} typ {cell(t):<24} ext {cell(e):<26} stretch {e['other_edge_ratio'][1]:.1f}"
          f" hand {e['hand_edge_ratio'][0]:.2f}-{e['hand_edge_ratio'][1]:.2f} idle {t['bones_not_deforming']}")
