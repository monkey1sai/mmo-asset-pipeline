"""Freeze requests/ro-swordsman-character-v1.json after the user's explicit consent (2026-10-05).

Run from the repo root: python -B runs/qa/ro-swordsman-character-v1/p2-prep/freeze-used.py <turn_start_utc>
Sets status=specified and quality.status=frozen, appends the authorization outside the hashed request and writes freeze.json once.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import workbench

QA = ROOT / "runs/qa/ro-swordsman-character-v1"
REQUEST = ROOT / "requests/ro-swordsman-character-v1.json"
TEXT = "時鐘口徑同意；回讀門檻 5 µm 同意；holdout 不提供雜湊。凍結並開始第一個候選"
NL = chr(10)

d = json.loads(REQUEST.read_text(encoding="utf-8"))
assert d["status"] == "draft" and d["quality"]["status"] == "draft" and not d["open_questions"]
d["status"] = "specified"
d["quality"]["status"] = "frozen"
d["holdout_policy"]["commitment"] = "使用者2026-10-05決定不提供承諾雜湊；holdout紀錄檔註明無承諾雜湊，揭示內容無法事後核對是否更換。"
errors = workbench.validate_request(d)
assert not errors, errors
assert not workbench.readiness(d), workbench.readiness(d)
REQUEST.write_text(json.dumps(d, ensure_ascii=False, indent=2) + NL, encoding="utf-8", newline=NL)

record = QA / "authorizations.json"
authorizations = json.loads(record.read_text(encoding="utf-8"))
authorizations["entries"].append({"utc_date": "2026-10-05", "text": TEXT,
                                  "covers": ["單一時鐘口徑（協調者實際工作時間，等待使用者回覆不計入）", "完整角色世界座標回讀門檻5µm、runtime 10µm", "holdout不提供承諾雜湊", "凍結需求", "開始第一個候選"],
                                  "not_covered": ["保護區C、D", "commit／push", "Unity或其他目標環境", "新付費生成的加購或升級"]})
record.write_text(json.dumps(authorizations, ensure_ascii=False, indent=1) + NL, encoding="utf-8", newline=NL)

contract = d["support_envelope"]["joint_range_contract"]
assert hashlib.sha256((ROOT / contract["path"]).read_bytes()).hexdigest() == contract["sha256"]
freeze = {"frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "turn_start_utc": sys.argv[1], "authority": TEXT,
          "request": {"path": "requests/ro-swordsman-character-v1.json", "file_sha256": hashlib.sha256(REQUEST.read_bytes()).hexdigest(),
                      "request_sha256": workbench.request_sha256(d), "protocol_sha256": workbench.quality_sha256(d)},
          "joint_range_contract": contract, "max_candidate_trials": d["production"]["max_revisions"], "budget": d["quality"]["budget"],
          "required_checks": [c["id"] for c in workbench.required_checks(d)],
          "rule": "The request file must not change after this point; a contract change needs a new request version and baseline."}
with open(QA / "freeze.json", "x", encoding="utf-8", newline=NL) as handle:
    json.dump(freeze, handle, ensure_ascii=False, indent=1)
    handle.write(NL)
print(json.dumps(freeze["request"], indent=1), len(freeze["required_checks"]), "checks")
