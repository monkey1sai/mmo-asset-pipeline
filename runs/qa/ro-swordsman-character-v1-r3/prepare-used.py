"""Prepare request version r3: patch the contract builder for the two corrected gates and derive the r3 setup script.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1-r3/prepare-used.py
Authority: user, 2026-10-05, "契約用做法 1。繼續第一個候選".
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NL = chr(10)


def patch(text, old, new):
    assert text.count(old) == 1, old[:70]
    return text.replace(old, new)


# 1. contract builder
path = ROOT / "scripts/cv1_joint_contract.py"
s = path.read_text(encoding="utf-8")
s = patch(s, '''        add(f"spine-{name}", "torso", [swing("spine_01", toward, half), swing("spine_02", toward, half)], ["spine_01", "spine_02"], view, 1.3,
            expect={"bone": "spine_02", "toward": toward})''',
          '''        # Leaning sideways while the arms stay at rest carries a hand into the coat; that extreme is reported, not gated.
        add(f"spine-{name}", "torso", [swing("spine_01", toward, half), swing("spine_02", toward, half)], ["spine_01", "spine_02"], view, 1.3,
            expect={"bone": "spine_02", "toward": toward}, hand_extreme=name != "lateral")''')
s = patch(s, '''            for row in baseline["results"] if row["status"] == "measured"}''',
          '''            for row in baseline["results"] if row["status"] == "measured" and row["gate"]["deforms"]}''')
s = patch(s, "Motions the baseline could not pose have no entry and get no allowance: zero new pairs and the hand guard's stretch bound.",
          "Motions the baseline could not pose, or posed without deforming any skin, have no entry and get the general bound: zero new pairs and the hand guard's stretch limit.")
s = patch(s, '"schema_version": 3,', '"schema_version": 4,')
path.write_text(s, encoding="utf-8", newline=NL)

# 2. r3 setup script, derived from the r2 one
src = (ROOT / "runs/qa/ro-swordsman-character-v1-r2/setup-used.py").read_text(encoding="utf-8")
start, end = src.index('if stage == "draft":'), src.index('elif stage == "bind":')
draft = '''if stage == "draft":
    old = json.loads(OLD.read_text(encoding="utf-8"))
    d = copy.deepcopy(old)
    d["id"] = "ro-swordsman-character-v1-r3"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r3"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r3.json#brief; previous version r2; docs/handoffs/claude-code-character-animation-v1-20261005.md"
    envelope = d["support_envelope"]
    envelope["joint_range_gates"]["body_ratchet"] += " 基準無法擺出、或擺了但沒有任何皮膚變形的動作（基準的腳趾沒有權重）不沿用基準數值，改用一般上限：新增交叉0對、邊長比不超過3。"
    envelope["joint_range_gates"]["reported_only"] += "；脊椎側彎在極端角度的手區交叉亦只報告（手臂維持原位時手會壓進衣擺），典型角度仍須為0"
    envelope.pop("joint_range_contract", None)
    envelope.pop("calibration", None)
    d["assumptions"].append("r3 與 r2 的差異僅兩項：腳趾等基準未變形的動作改用一般上限；脊椎側彎極端角度的手區交叉改為只報告。其餘角度、門檻、動作清單、品質契約、預算與保護區規則皆同。候選次數與時間延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art(PREVIOUS_REQUEST), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(V1 + "/quality-ledger.json"), "freeze": art(V1 + "/freeze.json"), "earlier_version": old["phase_history"]["previous_version"],
                                              "reason": "兩個無法通過的門檻，見 runs/qa/ro-swordsman-character-v1/v001/v001-pause-02.json", "authority": AUTH,
                                              "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選）",
                                              "quality_targets_lowered": False,
                                              "thresholds_changed": "腳趾上限由基準的不變形數值改為一般上限；脊椎側彎極端角度手區交叉由必須為0改為只報告"}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "budget", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate", "holdout_policy"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["quality"].items() if k != "status"}, {k: v for k, v in d["quality"].items() if k != "status"})
    assert same(old["support_envelope"]["joint_ranges_deg"], envelope["joint_ranges_deg"])
    dump(NEW_REQUEST, d)
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v4-calibration.json"], check=True, cwd=ROOT)
    record_path = "runs/qa/ro-swordsman-character-v1/authorizations.json"
    record = json.loads((ROOT / record_path).read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "text": AUTH,
                              "covers": ["契約做法1：另立 ro-swordsman-character-v1-r3 並重新登記baseline", "腳趾改用一般上限（不得新增交叉、邊長比不超過3）",
                                         "脊椎側彎極端角度的手區交叉改為只報告、交美術審查；典型角度仍須為0", "第一個候選延續"],
                              "not_covered": ["其他門檻的任何放寬", "保護區C", "commit／push"]})
    record["applies_to"].append("ro-swordsman-character-v1-r3")
    dump(record_path, record, mode="w")
    print("draft written", workbench.validate_request(d))

'''
src = src[:start] + draft + src[end:]
src = patch(src, 'V1 = "runs/qa/ro-swordsman-character-v1"', 'V1 = "runs/qa/ro-swordsman-character-v1-r2"')
src = patch(src, 'R2 = "runs/qa/ro-swordsman-character-v1-r2"', 'R2 = "runs/qa/ro-swordsman-character-v1-r3"')
src = patch(src, 'OLD = ROOT / "requests/ro-swordsman-character-v1.json"',
            'PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r2.json"' + NL + 'NEW_REQUEST = "requests/ro-swordsman-character-v1-r3.json"' + NL + 'OLD = ROOT / PREVIOUS_REQUEST')
src = patch(src, 'NEW = ROOT / "requests/ro-swordsman-character-v1-r2.json"', 'NEW = ROOT / NEW_REQUEST')
src = patch(src, 'AUTH = "袖口權重授權；契約用做法 1。繼續第一個候選"', 'AUTH = "契約用做法 1。繼續第一個候選"')
src = src.replace('"requests/ro-swordsman-character-v1-r2.json"', "NEW_REQUEST").replace('PREVIOUS_REQUEST = NEW_REQUEST', 'PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r2.json"')
src = src.replace("joint-range-contract-v3", "joint-range-contract-v4").replace("baseline-joint-range-v3", "baseline-joint-range-v4")
src = src.replace('"request": "ro-swordsman-character-v1",', '"request": "ro-swordsman-character-v1-r2",').replace("r2 contract", "r3 contract")
src = src.replace('"successor": NEW_REQUEST', '"successor": NEW_REQUEST').replace('"evidence": V1 + "/v001/v001-pause-01.json"', '"evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-02.json"')
src = src.replace("Pose definitions in the frozen joint-range contract made two combination poses impossible to pass.",
                  "Two gates could not be passed by any candidate: toe ceilings taken from a non-deforming baseline, and the hand rule at the extreme of a side bend.")
src = src.replace("Create request version ro-swordsman-character-v1-r2 from the frozen v1 request: pose definitions only.",
                  "Create request version ro-swordsman-character-v1-r3 from the frozen r2 request: two infeasible gates corrected.")
src = src.replace("runs/qa/ro-swordsman-character-v1-r2/setup-used.py", "runs/qa/ro-swordsman-character-v1-r3/setup-used.py")
src = src.replace('Authority: user, 2026-10-05, "袖口權重授權；契約用做法 1。繼續第一個候選". No threshold changes; v1 files are not modified',
                  'Authority: user, 2026-10-05, "契約用做法 1。繼續第一個候選". Two gate changes as authorized; r2 files are not modified')
target = ROOT / "runs/qa/ro-swordsman-character-v1-r3/setup-used.py"
with open(target, "x", encoding="utf-8", newline=NL) as handle:
    handle.write(src)
print("prepared")
