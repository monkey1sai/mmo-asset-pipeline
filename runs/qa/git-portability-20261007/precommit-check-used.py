"""Pre-commit checks for the pending files of the worktree (report only; run from the worktree root).

Usage: python -B precommit-check-used.py <out.json>
- pending = modified tracked files + untracked files not ignored;
- line endings: a file whose attributes set text (or eol=lf) must not contain CRLF; a text-like file (no NUL byte) with no
  text rule and no LFS filter is listed (core.autocrlf could rewrite it and break recorded SHA-256 values);
- secret patterns over text-like files up to 8 MB (subscription keys, bearer tokens, cookies, signed-URL parameters,
  GitHub/AWS/sk- keys, PEM private keys, api_key values); every hit is listed for review.
"""
import json
import os
import re
import subprocess
import sys

run = lambda *a, **k: subprocess.run(list(a), capture_output=True, check=True, **k).stdout
modified = [p for p in run("git", "diff", "--name-only", "-z").decode("utf-8").split("\0") if p]
untracked = [p for p in run("git", "ls-files", "--others", "--exclude-standard", "-z").decode("utf-8").split("\0") if p]
pending = sorted(set(modified) | set(untracked))
attrs = {}
out = run("git", "check-attr", "text", "eol", "filter", "--stdin", "-z", input="\0".join(pending).encode("utf-8")).decode("utf-8").split("\0")
for i in range(0, len(out) - 2, 3):
    attrs.setdefault(out[i], {})[out[i + 1]] = out[i + 2]
PATTERNS = {
    "subscription_key_value": re.compile(r"subscription[_-]?key[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9]{16,}", re.I),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    "cookie_header": re.compile(r"(?i)\b(set-)?cookie\s*[:=]\s*\S{8,}"),
    "signed_url": re.compile(r"X-Amz-Signature|X-Goog-Signature|[?&](Signature|sig|token|Expires|se|sp|sv)=[^&\s\"']{6,}"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|gho_[A-Za-z0-9]{30,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "sk_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    "pem_private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "api_key_value": re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}", re.I),
}
crlf_in_text, no_rule, hits, scanned = [], [], [], 0
for path in pending:
    a = attrs.get(path, {})
    if a.get("filter") == "lfs":
        continue
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        data = handle.read(min(size, 8_000_000))
    if b"\0" in data[:8192]:
        continue  # binary
    text_set = a.get("text") == "set" or a.get("eol") == "lf"
    if text_set and b"\r\n" in data:
        crlf_in_text.append(path)
    if a.get("text") == "unspecified" and a.get("eol") in ("unspecified", None):
        no_rule.append(path)
    if size <= 8_000_000:
        scanned += 1
        body = data.decode("utf-8", "replace")
        for name, pattern in PATTERNS.items():
            for m in pattern.finditer(body):
                line = body.count("\n", 0, m.start()) + 1
                hits.append({"file": path, "line": line, "pattern": name, "text": body[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")[:140]})
report = {"pending": len(pending), "modified_tracked": len(modified), "untracked": len(untracked), "text_scanned": scanned,
          "crlf_in_text_rule_files": crlf_in_text, "text_like_without_rule": no_rule[:50], "text_like_without_rule_count": len(no_rule),
          "secret_pattern_hits": hits}
open(sys.argv[1], "w", encoding="utf-8", newline="\n").write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}))
