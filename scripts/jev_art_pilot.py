"""有界中文 Jev 試點；預設離線，live 必須明確 --execute。"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity
import workbench

ROOT = Path(__file__).resolve().parents[1]
DATASET = "tools/jev-pilot/zh-game-cases-v1.json"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
CLIENT_SHA256 = "74d00fe280da4340970178e705990a905405ae9462a2ee33bfbf9a258e733d2e"
MAX_REQUESTS = 20
TASK_CRITERIA = {
    "static_prop": "固定道具、單棟建築、靜態展示人物；不要求活動部件、骨架或重複拼接。人物外形本身不代表需要骨架。",
    "interactive_prop": "物件明確要求開合、旋轉、往復、車輪轉向等活動部件；槍械、門、砲塔、車輛可屬此類，不是完整人形角色。",
    "modular_environment": "場景套件明確要求標準接合邊、統一模數、可重複拼接；僅分件方便換材質不算模組場景。",
    "rigged_character": "完整人物或生物明確需要綁骨、關節變形或角色動作；不因提到人物就選此項。",
    "needs_clarification": "用途或活動需求未定，無法合理選定上述資產類型；不要猜測未提供的功能。",
    "out_of_scope": "明確只要求 2D 插畫、PNG UI、聲音等非 3D 資產，超出本次 3D 工作台範圍。",
}
FIT_LEVELS = [
    "候選與需求用途無關，或有明確禁止元素／功能衝突，無法合理作為修訂起點。",
    "只有相近外觀或題材；活動結構、角色功能或拼接方式衝突，需要主要重建。",
    "主要物件和用途相近，但關鍵功能、風格或結構未知，仍需較多調查或修改。",
    "主要用途及必需功能相符，少量風格、材質或規格差距可修；可列為優先修訂候選。",
    "metadata 明確符合用途、必要功能與描述風格，可列為優先重用候選；仍未代表任何驗收通過。",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_dataset(root: Path) -> tuple[dict, dict]:
    dataset = identity.read_json(identity.recorded_path(root, DATASET))
    if dataset.get("schema_version") != 1 or not 1 <= len(dataset.get("cases", [])) <= MAX_REQUESTS:
        raise ValueError("DATASET_INVALID")
    assets = {}
    for source in dataset.get("assets", []):
        aid = source.get("id")
        if not identity.is_asset_id(aid) or aid in assets:
            raise ValueError("ASSET_ID_INVALID")
        if any(not workbench.text_value(source.get(k)) for k in ("name", "description")):
            raise ValueError("ASSET_DESCRIPTION_MISSING")
        assets[aid] = {**source, "provenance_kind": "synthetic_metadata", "limitations": ["合成測試條目，沒有模型檔案；功能只代表測試設定。"]}
    library = identity.read_json(root / "library/index.json")
    entries = {entry["id"]: entry for entry in library["entries"]}
    for aid in dataset.get("library_ids", []):
        if aid not in entries or aid in assets:
            raise ValueError("LIBRARY_REFERENCE_INVALID")
        source = entries[aid]
        assets[aid] = {
            "id": aid, "name": source["name"], "tags": source["tags"],
            "description": "現有素材庫 metadata：" + source["name"],
            "provenance_kind": "library_metadata_snapshot",
            "limitations": ["既有狀態只適用原需求，不證明本案例可用。", "原紀錄：" + json.dumps(source.get("acceptance", {}), ensure_ascii=False), *source.get("open_issues", [])],
        }
    seen = set()
    for case in dataset["cases"]:
        if not identity.is_asset_id(case.get("id")) or case["id"] in seen:
            raise ValueError("CASE_ID_INVALID")
        seen.add(case["id"])
        if any(not workbench.text_value(case.get(k)) for k in ("genre", "brief")) or not re.search(r"[\u3400-\u9fff]", case["brief"]):
            raise ValueError("CHINESE_BRIEF_REQUIRED")
        candidates = case.get("candidate_ids", [])
        if not 1 <= len(candidates) <= 6 or len(set(candidates)) != len(candidates) or any(a not in assets for a in candidates):
            raise ValueError("CANDIDATE_SET_INVALID")
        if case.get("expected_type") not in TASK_CRITERIA or not isinstance(case.get("acceptable_assets"), list) or not set(case["acceptable_assets"]) <= set(candidates):
            raise ValueError("EXPECTED_LABEL_INVALID")
    return dataset, assets


def bigrams(text: str) -> Counter:
    cleaned = "".join(re.findall(r"[\w]", text.casefold()))
    return Counter(cleaned[i:i + 2] for i in range(max(0, len(cleaned) - 1)))


def lexical_rank(case: dict, assets: dict) -> list[str]:
    query = bigrams(case["brief"])
    def score(aid: str) -> float:
        item = assets[aid]
        grams = bigrams(" ".join([item["name"], *item["tags"], item["description"]]))
        return sum((query & grams).values()) / max(1, sum((query | grams).values()))
    return sorted(case["candidate_ids"], key=lambda aid: (-score(aid), aid))


def make_payload(case: dict, assets: dict) -> dict:
    # Explicit allowlist: no labels, file paths, source code, QA logs or credentials.
    fields = ("id", "name", "tags", "description", "provenance_kind", "limitations")
    materials = [{key: deepcopy(assets[aid][key]) for key in fields} for aid in case["candidate_ids"]]
    state = {"genre": case["genre"], "brief": case["brief"], "materials": materials,
             "scope": "只依文字提出潛在重用或修訂候選，不能判定模型、動畫、技術、美術或交付通過。未定用途時先澄清。"}
    choices = {item["id"]: f"素材候選：{item['name']}；完整描述與限制在 state.materials。" for item in materials}
    choices["none"] = "所有候選均不符必要用途／功能，明確超出範圍，或需求不足以決定素材；先澄清，不強選。"
    questions = {
        "task_type": {"type": "choice", "instructions": "依 state.brief 判斷本次委託的 3D 資產類型。遊戲類型只作背景；否定句與未決事項優先。不要從候選推回未指定需求。", "criteria": TASK_CRITERIA},
        "match_asset": {"type": "choice", "instructions": "依 state.brief 的用途、功能與風格，在 state.materials 選一個最適合進一步核對的重用或修訂候選。缺資訊或無相符候選選 none；模型檔不存在與驗收未完成不代表可交付。", "criteria": choices},
    }
    for i, item in enumerate(materials):
        questions[f"fit_{i}"] = {"type": "score", "instructions": f"只評 state.materials[{i}]（{item['name']}）與 state.brief 的用途、必要功能與風格符合度。每個候選使用相同尺度；既有通過狀態不能替代本需求符合度，未知功能不要當已滿足。", "criteria": FIT_LEVELS}
    payload = {"state": state, "model": "jev-latest", "questions": questions}
    if len(identity.canonical_json(payload)) > 60000:
        raise ValueError("PAYLOAD_TOO_LARGE")
    return payload


def run_path(root: Path, run_id: str) -> Path:
    if not identity.is_asset_id(run_id):
        raise ValueError("RUN_ID_INVALID")
    return identity.recorded_path(root, f"runs/evidence/{run_id}")


def prepare(root: Path, run_id: str) -> dict:
    dataset, assets = load_dataset(root)
    folder = run_path(root, run_id)
    if (folder / "manifest.json").exists():
        raise ValueError("RUN_ALREADY_PREPARED")
    tracked = {}
    rows = []
    for case in dataset["cases"]:
        payload = make_payload(case, assets)
        target = folder / "inputs" / (case["id"] + ".json")
        write_json(target, payload, exclusive=True)
        task_type = case["expected_type"] if case["expected_type"] in workbench.TASKS else "static_prop"
        request = workbench.make_draft("jev-pilot-" + case["id"], case["brief"], task_type)
        request["purpose"] = f"{case['genre']}：中文語意判斷試點範例，製作用途待整理"
        request["provenance"] = {"kind": "example", "reference": f"{DATASET}#cases/{case['id']}"}
        request["assumptions"].append("合成試點需求；類型由預先標籤建立，不是 Jev 的輸出；沒有製作或驗收承諾。")
        if case["expected_type"] not in workbench.TASKS:
            request["assumptions"].append("static_prop 僅維持草稿結構；本例需澄清或移交 2D 流程，不可依此開始製作。")
        request_target = identity.recorded_path(root, f"requests/examples/jev-pilot/{request['id']}.json")
        if workbench.validate_request(request):
            raise ValueError("REQUEST_DRAFT_INVALID")
        write_json(request_target, request, exclusive=True)
        tracked[request_target.relative_to(root).as_posix()] = identity.file_digest(request_target)
        tracked[target.relative_to(root).as_posix()] = identity.file_digest(target)
        index = {"schema_version": 1, "entries": [{"id": item["id"], "name": item["name"], "tags": item["tags"]} for item in assets.values()]}
        rows.append({"id": case["id"], "genre": case["genre"], "brief": case["brief"], "candidate_ids": case["candidate_ids"], "expected_type": case["expected_type"], "acceptable_assets": case["acceptable_assets"],
                     "baseline_type": "static_prop", "baseline_ranking": lexical_rank(case, assets),
                     "existing_exact_matches": [a["id"] for a in workbench.search_library(index, case["brief"])], "payload_sha256": identity.json_digest(payload)})
    baseline = {"schema_version": 1, "label_source": dataset["label_source"], "assets": assets, "cases": rows,
                "baseline_notes": "分類對照是 intake 的 static_prop 預設，並非語意分類器。排序對照為相同人工候選集合的中文二字組字面相似度；不宣稱全庫檢索品質。"}
    write_json(folder / "baseline.json", baseline, exclusive=True)
    tracked[(folder / "baseline.json").relative_to(root).as_posix()] = identity.file_digest(folder / "baseline.json")
    for relative in (DATASET, "library/index.json", "scripts/jev_art_pilot.py", "scripts/workbench.py", "scripts/identity.py"):
        tracked[relative] = identity.file_digest(identity.recorded_path(root, relative))
    manifest = {"schema_version": 1, "run_id": run_id, "prepared_at": now(), "tracked_files": tracked,
                "provider_client_sha256": CLIENT_SHA256, "max_requests": len(rows), "confidence_threshold": 0.8,
                "price_reference": {"url": "https://docs.typesafe.ai/models", "checked_date": "2026-10-07", "model": "jev-1.13.0", "usd_per_million_input": 0.042, "usd_per_million_output": 0},
                "authorization": {"destination": ENDPOINT, "purpose": "使用者同意的遊戲類型中文需求分類＋素材 metadata 重排試點", "allowed_operations": "每案例一次推論，最多 20 次；保存本機去敏輸入、輸出與評估", "data_transmitted": "合成中文需求、遊戲類型、白名單素材摘要及問題；不含預期答案", "forbidden_operations": "傳送秘密、私人原始碼、完整 log、模型檔；重試未知提交；Hyper3D 生成；push／merge／部署", "stop_conditions": "輸入漂移、憑證無效、API 失敗、輸出不符契約、pending／unknown 操作；不自動重送"}}
    write_json(folder / "manifest.json", manifest, exclusive=True)
    return make_report(root, run_id)


def frozen(root: Path, run_id: str) -> tuple[dict, dict]:
    folder = run_path(root, run_id)
    manifest = identity.read_json(folder / "manifest.json")
    for relative, digest in manifest["tracked_files"].items():
        path = identity.recorded_path(root, relative)
        if not path.is_file() or identity.file_digest(path) != digest:
            raise ValueError("FROZEN_INPUT_DRIFT")
    baseline = identity.read_json(folder / "baseline.json")
    return manifest, baseline


def finite_number(value: object, low: float, high: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_response(payload: dict, response: dict) -> dict:
    if not isinstance(response, dict) or not workbench.text_value(response.get("model")):
        raise ValueError("MODEL_RESPONSE_INVALID")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(payload["questions"]):
        raise ValueError("ANSWER_SET_INVALID")
    clean = {}
    for qid, question in payload["questions"].items():
        answer = answers[qid]
        if not isinstance(answer, dict) or answer.get("type") != question["type"] or not finite_number(answer.get("confidence"), 0, 1):
            raise ValueError("ANSWER_TYPE_INVALID")
        options = set(question["criteria"]) if question["type"] == "choice" else {str(i) for i in range(len(question["criteria"]))}
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != options or any(not finite_number(p, 0, 1) for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 0.01:
            raise ValueError("PROBABILITIES_INVALID")
        clean[qid] = {"type": answer["type"], "confidence": answer["confidence"], "probabilities": probabilities}
        if question["type"] == "choice":
            selected = answer.get("choice")
            if selected not in options or probabilities[selected] + 1e-6 < max(probabilities.values()):
                raise ValueError("CHOICE_INVALID")
            clean[qid]["choice"] = selected
        else:
            score = answer.get("score")
            mean = sum(int(level) * probability for level, probability in probabilities.items())
            if not finite_number(score, 0, len(options) - 1) or abs(score - mean) > 0.03:
                raise ValueError("SCORE_INVALID")
            clean[qid]["score"] = score
    usage = response.get("usage", {})
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")):
        raise ValueError("USAGE_INVALID")
    return {"model": response["model"], "answers": clean, "usage": {k: usage[k] for k in ("input_tokens", "output_tokens")}}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "REDIRECT_BLOCKED", headers, None)


def load_client(source: Path, expected_digest: str):
    if not source.is_file() or identity.file_digest(source) != expected_digest:
        raise ValueError("PROVIDER_CLIENT_DRIFT")
    spec = importlib.util.spec_from_file_location("jev_art_pilot_provider", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.API_URL != ENDPOINT or module.DEFAULT_MODEL != "jev-latest":
        raise ValueError("PROVIDER_ENDPOINT_INVALID")
    # Existing provider resolves the key internally; the pilot never reads or logs it.
    return module.Client(model="jev-latest", timeout=20)


def execute(root: Path, run_id: str, client, limit: int = MAX_REQUESTS) -> dict:
    manifest, baseline = frozen(root, run_id)
    folder = run_path(root, run_id)
    operations = folder / "operations"
    existing = {p.stem: identity.read_json(p) for p in operations.glob("*.json")} if operations.exists() else {}
    if any(op.get("status") != "completed" for op in existing.values()):
        raise ValueError("ORIGINAL_OPERATION_UNRESOLVED")
    if not 1 <= limit <= MAX_REQUESTS or len(existing) > manifest["max_requests"]:
        raise ValueError("REQUEST_BUDGET_INVALID")
    completed_now = 0
    for case in baseline["cases"]:
        if case["id"] in existing:
            continue
        if completed_now >= limit:
            break
        # Recheck immediately before each submission, including resumed sessions.
        frozen(root, run_id)
        payload = identity.read_json(folder / "inputs" / (case["id"] + ".json"))
        if identity.json_digest(payload) != case["payload_sha256"]:
            raise ValueError("PAYLOAD_DRIFT")
        operation_path = operations / (case["id"] + ".json")
        operation = {"operation_id": run_id + "." + case["id"], "case_id": case["id"], "payload_sha256": case["payload_sha256"], "status": "prepared", "prepared_at": now(), "attempts": 1}
        write_json(operation_path, operation, exclusive=True)
        started = time.perf_counter()
        try:
            response = validate_response(payload, client.system_one(payload["state"], payload["questions"]))
            response["wall_ms"] = round((time.perf_counter() - started) * 1000, 2)
            response["payload_sha256"] = case["payload_sha256"]
            target = folder / "responses" / (case["id"] + ".json")
            write_json(target, response, exclusive=True)
            operation.update(status="completed", completed_at=now(), response_sha256=identity.file_digest(target))
            write_json(operation_path, operation)
            completed_now += 1
            print(json.dumps({"case": case["id"], "status": "completed", "model": response["model"], "wall_ms": response["wall_ms"]}, ensure_ascii=False), flush=True)
        except Exception as error:
            # Never expose provider error bodies, headers, credential values or tracebacks.
            http = re.search(r"HTTP (\d{3})", str(error))
            code = int(http.group(1)) if http else None
            operation.update(status="failed" if code else "unknown", ended_at=now(), error_type=type(error).__name__, http_status=code,
                             failure_class="AUTHORIZATION_DENIAL" if code in (401, 403) else "TOOL_OR_NETWORK_FAILURE", automatic_retry=False)
            write_json(operation_path, operation)
            make_report(root, run_id)
            raise ValueError("PROVIDER_STOPPED_NO_RETRY") from None
    return make_report(root, run_id)


def rank_metrics(rows: list[dict], field: str) -> dict:
    eligible = [r for r in rows if r["acceptable_assets"] and field in r]
    ranks = [next((i + 1 for i, aid in enumerate(row[field]) if aid in row["acceptable_assets"]), None) for row in eligible]
    count = len(eligible)
    return {"evaluated_cases": count, "top1_correct": sum(rank == 1 for rank in ranks), "top3_correct": sum(rank is not None and rank <= 3 for rank in ranks),
            "mrr": round(sum(1 / rank if rank else 0 for rank in ranks) / count, 4) if count else None}


def make_report(root: Path, run_id: str) -> dict:
    manifest, baseline = frozen(root, run_id)
    folder = run_path(root, run_id)
    rows = deepcopy(baseline["cases"])
    responses = []
    for row in rows:
        path = folder / "operations" / (row["id"] + ".json")
        row["provider_status"] = "NOT_RUN"
        if not path.exists():
            continue
        operation = identity.read_json(path)
        row["provider_status"] = operation["status"]
        if operation["status"] != "completed":
            continue
        target = folder / "responses" / (row["id"] + ".json")
        if identity.file_digest(target) != operation["response_sha256"]:
            raise ValueError("RESPONSE_DRIFT")
        payload = identity.read_json(folder / "inputs" / (row["id"] + ".json"))
        response = identity.read_json(target)
        validate_response(payload, response)
        if response.get("payload_sha256") != row["payload_sha256"]:
            raise ValueError("RESPONSE_INPUT_MISMATCH")
        answers = response["answers"]
        row["jev_type"] = answers["task_type"]["choice"]
        row["type_confidence"] = answers["task_type"]["confidence"]
        row["jev_asset"] = answers["match_asset"]["choice"]
        row["asset_confidence"] = answers["match_asset"]["confidence"]
        row["type_correct"] = row["jev_type"] == row["expected_type"]
        row["asset_correct"] = row["jev_asset"] in row["acceptable_assets"] if row["acceptable_assets"] else row["jev_asset"] == "none"
        scores = {aid: answers[f"fit_{i}"]["score"] for i, aid in enumerate(row["candidate_ids"])}
        row["jev_ranking"] = sorted(scores, key=lambda aid: (-scores[aid], aid))
        row["fit_scores"] = scores
        row["needs_review"] = row["jev_type"] in ("needs_clarification", "out_of_scope") or row["jev_asset"] == "none" or min(row["type_confidence"], row["asset_confidence"]) < manifest["confidence_threshold"]
        row["wall_ms"] = response["wall_ms"]
        responses.append(response)
    evaluated = [r for r in rows if r["provider_status"] == "completed"]
    accepted = [r for r in evaluated if not r["needs_review"]]
    input_tokens = sum(r["usage"]["input_tokens"] for r in responses)
    output_tokens = sum(r["usage"]["output_tokens"] for r in responses)
    models = sorted({r["model"] for r in responses})
    elapsed = [r["wall_ms"] for r in responses]
    price = manifest["price_reference"]
    paired_baseline = rank_metrics(evaluated, "baseline_ranking")
    report = {"schema_version": 1, "run_id": run_id, "generated_at": now(), "status": "completed" if len(evaluated) == len(rows) else "partial",
              "label_source": baseline["label_source"], "case_count": len(rows), "genre_count": len({r["genre"] for r in rows}), "models": models,
              "baseline_type_correct": sum(r["baseline_type"] == r["expected_type"] for r in rows), "baseline_rank": rank_metrics(rows, "baseline_ranking"), "paired_baseline_rank": paired_baseline,
              "jev": {"evaluated_cases": len(evaluated), "type_correct": sum(r["type_correct"] for r in evaluated), "asset_choice_correct": sum(r["asset_correct"] for r in evaluated),
                      "rank": rank_metrics(evaluated, "jev_ranking"), "needs_review": sum(r["needs_review"] for r in evaluated), "advisory_coverage": len(accepted),
                      "advisory_type_correct": sum(r["type_correct"] for r in accepted), "advisory_asset_correct": sum(r["asset_correct"] for r in accepted)},
              "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "estimated_usd": round(input_tokens * price["usd_per_million_input"] / 1000000, 8) if models == [price["model"]] else None, "actual_charge": "UNVERIFIED"},
              "latency": {"measurement": "每次 provider 呼叫至契約核對完成；不含案例編寫、離線準備或實際美術製作", "mean_ms": round(statistics.mean(elapsed), 2) if elapsed else None, "median_ms": round(statistics.median(elapsed), 2) if elapsed else None, "max_ms": max(elapsed) if elapsed else None},
              "baseline_notes": baseline["baseline_notes"], "cases": rows}
    write_json(folder / "report.json", report)
    lines = ["# Jev 中文遊戲美術需求試點", "", f"狀態：{report['status']}；{len(evaluated)}/{len(rows)} 案例有實際 provider 回覆。", "", report["label_source"], "", report["baseline_notes"], "",
             f"分類：Jev {report['jev']['type_correct']}/{len(evaluated)}；intake 預設 {report['baseline_type_correct']}/{len(rows)}。", f"素材 Choice：{report['jev']['asset_choice_correct']}/{len(evaluated)}。", f"同批已跑案例的字面排序：{paired_baseline}；Jev Score 排序：{report['jev']['rank']}。", f"待覆核：{report['jev']['needs_review']}；tokens／估算：{report['usage']}；實際扣款未核對。", f"實際模型：{models}；延遲：{report['latency']}。", "",
             "| 遊戲類型 | 中文需求 | 預期類型 | Jev 類型 | 建議素材 | 結果 |", "|---|---|---|---|---|---|"]
    for row in rows:
        result = "NOT_RUN" if row["provider_status"] == "NOT_RUN" else row["provider_status"]
        if row["provider_status"] == "completed":
            result = "符合預期" if row["type_correct"] and row["asset_correct"] else "有誤差"
            result += "／待覆核" if row["needs_review"] else "／僅建議"
        lines.append(f"| {row['genre']} | {row['brief'].replace('|', '/')} | {row['expected_type']} | {row.get('jev_type', '—')} | {row.get('jev_asset', '—')} | {result} |")
    lines += ["", "限制：合成案例、人工設計候選集合、單次抽樣，未經人類覆核；不能推廣成真實委託準確率、全庫檢索能力、模型美術／動畫／引擎驗收或節省總成本。", "", "0.8 只作本試點待覆核標記，不是校準完成或自動執行門檻。所有需求維持 draft，所有製作路線維持 review_existing。"]
    (folder / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {key: report[key] for key in ("status", "case_count", "genre_count", "models", "jev", "usage", "latency")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "report", "live"))
    parser.add_argument("--run-id", default="jev-zh-pilot-20261007")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--client-source", type=Path)
    parser.add_argument("--limit", type=int, default=MAX_REQUESTS)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(ROOT, args.run_id)
        elif args.command == "report":
            result = make_report(ROOT, args.run_id)
        else:
            if not args.execute or args.client_source is None:
                raise ValueError("LIVE_REQUIRES_EXECUTE_AND_PROVIDER")
            manifest, _ = frozen(ROOT, args.run_id)
            client = load_client(args.client_source.resolve(), manifest["provider_client_sha256"])
            opener = urllib.request.build_opener(NoRedirect())
            with patch.object(urllib.request, "urlopen", opener.open):
                result = execute(ROOT, args.run_id, client, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        message = str(error) if isinstance(error, (ValueError, identity.IdentityError)) and re.fullmatch(r"[A-Z_]+", str(error)) else "PILOT_STOPPED"
        print(json.dumps({"status": "blocked", "reason": message, "error_type": type(error).__name__, "automatic_retry": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
