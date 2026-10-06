"""Prepare request version r5: contacts that involve an armour piece are judged by penetration depth, not by count.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1-r5/prepare-used.py
Authority: user, 2026-10-05, "肩甲用做法 1，另立 r5 改量穿入深度。繼續第一個候選".
- cv1_joint_range.py: an optional armour class. A triangle is armour when its mesh is listed as armour or all three of
  its vertices carry at least half their weight on a listed armour bone (the core's own copy of the shoulder armour
  once bound to the pauldron). A non-hand intersecting pair with an armour triangle is an armour contact; its depth is
  how far the two triangles cross each other on the shallower side (orientation-free). Each triangle's rest depth is
  its deepest armour contact at rest. A pose passes when every armour contact is no deeper than the deeper rest depth
  of its two triangles plus the slack. Without an armour list the tool behaves exactly as before.
- cv1_joint_contract.py: copies the armour definition from the request into the contract limits.
- writes runs/qa/ro-swordsman-character-v1-r5/setup-used.py, derived from the r4 setup.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:70])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_joint_range.py", [
    ('''        total = 0.0
''', '''        total = 0.0
        armour_total = 0.0
'''),
    ('''            if name.startswith(hand_prefixes):
                total += g.weight
        hand_weight.append(total)''', '''            if name.startswith(hand_prefixes):
                total += g.weight
            if name in armour_bones:
                armour_total += g.weight
        hand_weight.append(total)
        armour_weight.append(armour_total)'''),
    ('''hand_prefixes = tuple(limits["hand_bone_prefixes"])''', '''hand_prefixes = tuple(limits["hand_bone_prefixes"])
armour_bones, armour_meshes = set(limits.get("armor_bones", [])), set(limits.get("armor_meshes", []))
armour_slack = limits.get("armor_depth_slack_m", 0.0)
armour_weight = []'''),
    ('''tri_hand = [any(is_hand_vertex[i] for i in t) for t in tris]''', '''tri_hand = [any(is_hand_vertex[i] for i in t) for t in tris]
# Armour class: triangles of an armour mesh, or body triangles carried by an armour bone (all three vertices >= 0.5).
tri_armour = [tri_mesh[k] in armour_meshes or all(armour_weight[i] >= 0.5 for i in t) for k, t in enumerate(tris)]'''),
    ('''    other = [p for p in pairs if not tri_hand[p[0]] and not tri_hand[p[1]]]
    return hand_self, hand_other, other''', '''    body = [p for p in pairs if not tri_hand[p[0]] and not tri_hand[p[1]]]
    armour = [p for p in body if tri_armour[p[0]] or tri_armour[p[1]]]
    other = [p for p in body if not (tri_armour[p[0]] or tri_armour[p[1]])]
    return hand_self, hand_other, other, armour


def crossing(points, t, plane_tri):
    """How far triangle t reaches through the plane of plane_tri on its shallower side."""
    a, b, c = (points[i] for i in tris[plane_tri])
    normal = (b - a).cross(c - a)
    if normal.length < 1e-14:
        return 0.0
    normal.normalize()
    side = [(points[i] - a).dot(normal) for i in tris[t]]
    return min(max(0.0, max(side)), max(0.0, -min(side)))


def pair_depth(points, a, b):
    return min(crossing(points, a, b), crossing(points, b, a))'''),
    ('''    hand_self, hand_other, other = classify(intersecting_pairs(points))''', '''    hand_self, hand_other, other, armour = classify(intersecting_pairs(points))
    excess, deepest, violations, armour_examples = 0.0, 0.0, 0, []
    for a, b in armour:
        depth = pair_depth(points, a, b)
        allowed = max(rest_depth.get(a, 0.0), rest_depth.get(b, 0.0)) + armour_slack
        deepest = max(deepest, depth)
        if depth > allowed:
            violations += 1
            excess = max(excess, depth - allowed)
            if len(armour_examples) < 5:
                armour_examples.append({"meshes": [tri_mesh[a], tri_mesh[b]], "depth_mm": round(depth * 1e3, 2), "allowed_mm": round(allowed * 1e3, 2),
                                        "at": [round(c, 4) for c in sum((points[i] for i in tris[a]), Vector()) / 3]})'''),
    ('''            "other_pairs": len(other), "other_new_pairs": len(other_new),''', '''            "other_pairs": len(other), "other_new_pairs": len(other_new),
            "armor_pairs": len(armour), "armor_depth_max_m": deepest, "armor_depth_violations": violations, "armor_excess_max_m": excess, "armor_examples": armour_examples,'''),
    ('''rest_hand_self, rest_hand_other, rest_other = classify(rest_pairs)''', '''rest_hand_self, rest_hand_other, rest_other, rest_armour = classify(rest_pairs)
rest_depth = {}
for a, b in rest_armour:
    depth = pair_depth(rest, a, b)
    rest_depth[a], rest_depth[b] = max(rest_depth.get(a, 0.0), depth), max(rest_depth.get(b, 0.0), depth)'''),
    ('''        "other_intersections_within_ceiling": bool(limit) and''', '''        "armor_contact_depth": all(row["levels"][n]["armor_depth_violations"] == 0 for n in ("typical", "extreme")),
        "other_intersections_within_ceiling": bool(limit) and'''),
    ('''    "armature": arm.name, "bones": len(bones),''', '''    "armor_contact": {"meshes": sorted(armour_meshes), "bones": sorted(armour_bones), "slack_m": armour_slack, "rest_pairs": len(rest_armour),
                      "rest_depth_max_m": max(rest_depth.values(), default=0.0), "triangles": sum(tri_armour)},
    "armature": arm.name, "bones": len(bones),'''),
])
patch("scripts/cv1_joint_contract.py", [
    ('''            "excluded_meshes": ["SM_RO_sword"],''', '''            "excluded_meshes": ["SM_RO_sword"],
            **({"armor_meshes": request["support_envelope"]["armor_contact"]["meshes"], "armor_bones": request["support_envelope"]["armor_contact"]["bones"],
                "armor_depth_slack_m": request["support_envelope"]["armor_contact"]["slack_mm"] / 1000} if "armor_contact" in request["support_envelope"] else {}),'''),
])

# r5 setup script, derived from the r4 one
src = (ROOT / "runs/qa/ro-swordsman-character-v1-r4/setup-used.py").read_text(encoding="utf-8")
start, end = src.index('if stage == "draft":'), src.index('elif stage == "bind":')
draft = '''if stage == "draft":
    old = json.loads(OLD.read_text(encoding="utf-8"))
    d = copy.deepcopy(old)
    d["id"] = "ro-swordsman-character-v1-r5"
    d["title"] = "RO劍士：可重用角色動畫V1（凍結後接入新動作驗收）r5"
    d["status"] = "draft"
    d["quality"]["status"] = "draft"
    d["provenance"]["reference"] = "requests/ro-swordsman-character-v1-r5.json#brief; previous version r4; docs/handoffs/claude-code-character-animation-v1-20261005.md"
    envelope = d["support_envelope"]
    envelope["armor_contact"] = {
        "meshes": ["SM_RO_pauldron.L", "SM_RO_pauldron.R", "SM_RO_cuirass", "SM_RO_bracer.L", "SM_RO_bracer.R"],
        "bones": ["pauldron.L", "pauldron.R"],
        "slack_mm": 2,
        "definition": "盔甲接觸＝至少一個三角形屬於盔甲件（上列網格），或屬於被盔甲骨帶動的身體部位（三個頂點的盔甲骨權重皆>=0.5）的非手區穿插對；"
                      "盔甲件之間（例如肩甲邊緣與胸甲）也算。深度＝兩個三角形互相穿過對方平面的較淺一側距離，取兩者較小值，與法線方向無關。"
                      "每個三角形的靜止深度＝它在靜止姿勢所有盔甲接觸中的最大深度（無接觸為0）。姿勢中每個盔甲接觸的深度不得超過兩個三角形靜止深度的較大者＋2mm。",
        "reason": "盔甲件靜止時就嵌在身體網格與胸甲裡；盔甲一動，嵌入的接觸會重新洗牌，被三角形對數當成新穿插。改量深度只看接觸是否變深。",
    }
    gates = envelope["joint_range_gates"]
    gates["armor_contact"] = "盔甲接觸改以深度判定：每個盔甲接觸不得比相關三角形的靜止深度深2mm以上；典型與極端角度皆適用。"
    gates["body_ratchet"] += " r5起，盔甲接觸不計入對數上限，改由 armor_contact 判定；其餘身體穿插仍照基準同動作的對數上限。"
    envelope.pop("joint_range_contract", None)
    envelope.pop("calibration", None)
    d["assumptions"].append("r5 與 r4 的差異僅一項：涉及盔甲件（含被盔甲骨帶動的身體部位）的穿插改量深度（不得比靜止時深2mm以上），其餘身體穿插的對數上限、手區零穿插、塌陷、邊長比門檻皆同。候選次數與時間延續，不重設。")
    d["phase_history"]["previous_version"] = {"request": art(PREVIOUS_REQUEST), "request_sha256": workbench.request_sha256(old),
                                              "ledger": art(V1 + "/quality-ledger.json"), "freeze": art(V1 + "/freeze.json"), "earlier_version": old["phase_history"]["previous_version"],
                                              "reason": "移動肩甲後新增的接觸多為靜止時已嵌入的盔甲接觸重新洗牌，對數上限無法分辨，見 runs/qa/ro-swordsman-character-v1/v001/v001-pause-07.json", "authority": AUTH,
                                              "candidates_used_in_previous_version": 0, "candidate_in_progress": "v001（延續，計為本版第1個候選）",
                                              "quality_targets_lowered": False,
                                              "thresholds_changed": "盔甲接觸由對數上限改為深度上限（靜止深度＋2mm）"}
    same = lambda a, b: json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
    for key in ("style", "spec", "production", "delivery", "additional_checks", "budget", "protected_zone", "transition_matrix", "runtime_contract", "grasp_gate", "holdout_policy"):
        assert same(old[key], d[key]), key
    assert same({k: v for k, v in old["quality"].items() if k != "status"}, {k: v for k, v in d["quality"].items() if k != "status"})
    assert same(old["support_envelope"]["joint_ranges_deg"], envelope["joint_ranges_deg"]) and same(old["support_envelope"]["frozen_poses"], envelope["frozen_poses"])
    dump(NEW_REQUEST, d)
    subprocess.run([sys.executable, "-B", "scripts/cv1_joint_contract.py", NEW_REQUEST, R2 + "/joint-range-contract-v6-calibration.json"], check=True, cwd=ROOT)
    record_path = "runs/qa/ro-swordsman-character-v1/authorizations.json"
    record = json.loads((ROOT / record_path).read_text(encoding="utf-8"))
    record["entries"].append({"utc_date": "2026-10-05", "text": AUTH,
                              "covers": ["肩甲做法1：綁定身體網格上的重複肩甲、肩甲上緣轉軸、輔助骨跟隨", "另立 ro-swordsman-character-v1-r5：盔甲接觸改量穿入深度（靜止深度＋2mm），重新登記baseline", "第一個候選延續"],
                              "interpretation": "盔甲接觸包含盔甲件之間（肩甲邊緣與胸甲）及被盔甲骨帶動的身體部位；這是上一則回報所述『肩甲邊緣嵌進胸甲』與『綁過去的那層盔甲』兩類接觸。",
                              "not_covered": ["其他門檻的任何放寬", "衣擺等非盔甲部位的門檻", "保護區C", "commit／push"]})
    record["applies_to"].append("ro-swordsman-character-v1-r5")
    dump(record_path, record, mode="w")
    print("draft written", workbench.validate_request(d))

'''
src = src[:start] + draft + src[end:]
for old, new in [('V1 = "runs/qa/ro-swordsman-character-v1-r3"', 'V1 = "runs/qa/ro-swordsman-character-v1-r4"'),
                 ('R2 = "runs/qa/ro-swordsman-character-v1-r4"', 'R2 = "runs/qa/ro-swordsman-character-v1-r5"'),
                 ('STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"', 'STUB = "runs/qa/ro-swordsman-character-v1-r4/baseline-pose-stub.json"  # reused: same frozen arm pose'),
                 ('PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r3.json"', 'PREVIOUS_REQUEST = "requests/ro-swordsman-character-v1-r4.json"'),
                 ('NEW_REQUEST = "requests/ro-swordsman-character-v1-r4.json"', 'NEW_REQUEST = "requests/ro-swordsman-character-v1-r5.json"'),
                 ('AUTH = "雙手下劈用做法 1。繼續第一個候選"', 'AUTH = "肩甲用做法 1，另立 r5 改量穿入深度。繼續第一個候選"'),
                 ('"request": "ro-swordsman-character-v1-r3",', '"request": "ro-swordsman-character-v1-r4",'),
                 ('"evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-03.json"', '"evidence": "runs/qa/ro-swordsman-character-v1/v001/v001-pause-07.json"')]:
    assert src.count(old) == 1, old
    src = src.replace(old, new)
src = src.replace("joint-range-contract-v5", "joint-range-contract-v6").replace("baseline-joint-range-v5", "baseline-joint-range-v6")
reason_start = src.index('"reason": "The two-hand chop had no baseline')
reason_end = src.index('",', reason_start) + 2
src = src[:reason_start] + '"reason": "Moving the pauldrons reshuffles armour contacts embedded at rest, which the count-based body ratchet cannot tell from new penetration.",' + src[reason_end:]
src = src.replace("Create request version ro-swordsman-character-v1-r4 from the frozen r3 request: the two-hand chop's body ceilings come from the baseline in the same arm pose.",
                  "Create request version ro-swordsman-character-v1-r5 from the frozen r4 request: armour contacts are judged by penetration depth.")
src = src.replace("runs/qa/ro-swordsman-character-v1-r4/setup-used.py", "runs/qa/ro-swordsman-character-v1-r5/setup-used.py")
src = src.replace('Authority: user, 2026-10-05, "雙手下劈用做法 1。繼續第一個候選". One ceiling source changed as authorized; r3 files are not modified',
                  'Authority: user, 2026-10-05, "肩甲用做法 1，另立 r5 改量穿入深度。繼續第一個候選". Armour contacts judged by depth as authorized; r4 files are not modified')
with open(ROOT / "runs/qa/ro-swordsman-character-v1-r5/setup-used.py", "x", encoding="utf-8", newline=NL) as handle:
    handle.write(src)
print("prepared")
