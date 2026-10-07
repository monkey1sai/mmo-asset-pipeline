"""Read-only byte checks for this consolidation; no DCC/runtime acceptance claims."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import workbench


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def artifacts(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and re.fullmatch(r"[a-f0-9]{64}", str(value.get("sha256", ""))):
            yield value
        for child in value.values():
            yield from artifacts(child)
    elif isinstance(value, list):
        for child in value:
            yield from artifacts(child)


checks = []
for path in ["deliveries/cl-barracks-set-v1/v1/manifest.json",
             "runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json",
             "runs/qa/ro-swordsman-character-v1/v001/p4/runtime/20261007t054356z-p4-results.json",
             "runs/qa/ro-swordsman-character-v1/v001/p4/runtime/20261007t054356z-background-execution.json"]:
    unique = {(v["path"], v["sha256"]): v for v in artifacts(read(path))}
    problems = []
    for item in unique.values():
        artifact = (ROOT / item["path"]).resolve()
        if not artifact.is_relative_to(ROOT) or not artifact.is_file():
            problems.append("missing or outside repo: " + item["path"])
            continue
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != item["sha256"]:
            problems.append("hash mismatch: " + item["path"])
        if "bytes" in item and artifact.stat().st_size != item["bytes"]:
            problems.append("size mismatch: " + item["path"])
    checks.append({"manifest": path, "unique_artifacts": len(unique), "problems": problems})

request = read("requests/cl-barracks-set-v1.json")
evidence = read("runs/qa/cl-barracks-set-v1/v1/acceptance-evidence.json")
assessment = workbench.assess(request, evidence, ROOT)
write("barracks-assessment.json", assessment)

# Reuse only the literal regex definitions, without executing the older scanner.
tree = ast.parse((ROOT / "runs/qa/git-portability-20261007/precommit-check-used.py").read_text(encoding="utf-8"))
assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PATTERNS" for t in n.targets))
patterns = {ast.literal_eval(k): re.compile(ast.literal_eval(v.args[0]).encode("ascii"), re.I if len(v.args) > 1 else 0)
            for k, v in zip(assignment.value.keys, assignment.value.values)}
dispositions = []
for hit in read("runs/qa/consolidation-20261007/raw-byte-pattern-scan.json")["hits"]:
    data = (ROOT / hit["path"]).read_bytes()
    match = patterns[hit["pattern"]].match(data, hit["offset"])
    if match is None:
        raise ValueError("scanner hit no longer matches")
    matched = match.group(0)
    context = data[max(0, hit["offset"] - 1024):match.end() + 1024]
    nonprintable = sum(not (32 <= byte <= 126) for byte in matched)
    utf8_valid = True
    try:
        matched.decode("utf-8")
    except UnicodeDecodeError:
        utf8_valid = False
    http_present = b"http://" in context.lower() or b"https://" in context.lower()
    resolved = hit["path"].endswith("transition-reference.f32.bin") and len(data) % 4 == 0 and nonprintable > 0 and not utf8_valid and not http_present
    dispositions.append({**hit, "match_bytes": len(matched), "nonprintable_bytes": nonprintable,
                         "utf8_valid": utf8_valid, "http_scheme_in_surrounding_1k": http_present,
                         "match_sha256": hashlib.sha256(matched).hexdigest(),
                         "disposition": "binary float32 regex false positive" if resolved else "unresolved; stop publication"})

result = {"artifact_checks": checks, "scan_dispositions": dispositions,
          "assessment_decision": assessment["decision"], "assessment_blockers": assessment["blockers"],
          "scope": "Local byte/hash/evidence-contract checks only; historical failures and runtime/art claims unchanged."}
write("integrity-checks.json", result)
print(json.dumps(result, ensure_ascii=False))
if any(c["problems"] for c in checks) or assessment["blockers"] or any(d["disposition"].startswith("unresolved") for d in dispositions):
    raise SystemExit(1)
