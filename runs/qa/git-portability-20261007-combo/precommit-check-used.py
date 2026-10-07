"""Reuse the previous precommit patterns, recording locations only (never matched secret values).

Read-only scan of pending files; only the explicitly named report is written. Run from the worktree root.
LFS/binary/large-file exclusions match the previous scanner and remain explicit in the report.
"""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys


def git(*args, data=None):
    return subprocess.run(["git", *args], input=data, capture_output=True, check=True).stdout


source = Path("runs/qa/git-portability-20261007/precommit-check-used.py")
tree = ast.parse(source.read_text(encoding="utf-8"))
assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "PATTERNS" for t in n.targets))
patterns = {}
for key, value in zip(assignment.value.keys, assignment.value.values):
    flags = 0
    if len(value.args) > 1:
        flag = value.args[1]
        if not (isinstance(flag, ast.Attribute) and isinstance(flag.value, ast.Name)
                and flag.value.id == "re" and flag.attr == "I"):
            raise ValueError("Unexpected regex flag in the existing scanner")
        flags = re.I
    patterns[ast.literal_eval(key)] = re.compile(ast.literal_eval(value.args[0]), flags)

modified = [p for p in git("diff", "--name-only", "-z").decode().split("\0") if p]
untracked = [p for p in git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0") if p]
pending = sorted(set(modified) | set(untracked))
attributes = {}
parts = git("check-attr", "text", "eol", "filter", "--stdin", "-z",
            data="\0".join(pending).encode()).decode().split("\0")
for i in range(0, len(parts) - 2, 3):
    attributes.setdefault(parts[i], {})[parts[i + 1]] = parts[i + 2]
hits, crlf, no_rule, excluded = [], [], [], {"lfs": 0, "binary": 0, "over_8mb": 0}
scanned = 0
for name in pending:
    attr = attributes[name]
    if attr.get("filter") == "lfs":
        excluded["lfs"] += 1
        continue
    file = Path(name)
    with file.open("rb") as handle:
        body = handle.read(8_000_001)
    if b"\0" in body[:8192]:
        excluded["binary"] += 1
        continue
    # An explicit -text disables conversion even when an inherited eol=lf attribute remains visible.
    if (attr.get("text") == "set" or (attr.get("text") != "unset" and attr.get("eol") == "lf")) and b"\r\n" in body:
        crlf.append(name)
    if attr.get("text") == "unspecified" and attr.get("eol") == "unspecified":
        no_rule.append(name)
    if len(body) > 8_000_000:
        excluded["over_8mb"] += 1
        continue
    scanned += 1
    text = body.decode("utf-8", "replace")
    for pattern_name, pattern in patterns.items():
        for match in pattern.finditer(text):
            hits.append({"file": name, "line": text.count("\n", 0, match.start()) + 1,
                         "pattern": pattern_name})
report = {"pending": len(pending), "modified_tracked": len(modified), "untracked": len(untracked),
          "pattern_source": source.as_posix(), "text_scanned": scanned, "excluded": excluded,
          "crlf_in_text_rule_files": crlf, "text_like_without_rule": no_rule, "secret_pattern_hits": hits,
          "scope": "Pattern scan of text-like pending files <=8MB; binary and LFS content not inspected for secrets."}
target = Path(sys.argv[1]).resolve()
allowed = Path("runs/qa/git-portability-20261007-combo").resolve()
if not target.is_relative_to(allowed):
    raise ValueError("Report path outside task evidence folder")
target.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"pending": len(pending), "text_scanned": scanned, "excluded": excluded,
                  "crlf": crlf, "no_rule": no_rule, "secret_pattern_hits": hits}, ensure_ascii=False))
sys.exit(1 if hits or crlf or no_rule else 0)
