"""Check that the staged entries of one commit group match the working tree byte for byte.

Usage (from the worktree root): python -B verify_stage.py <group-file>
- the staged path set equals the group list (nothing missing, nothing extra);
- regular blobs: staged blob id == git hash-object --no-filters of the working file (no line-ending change);
- LFS entries: the staged blob is a pointer whose oid/size equal the working file's SHA-256/size, and the
  local object under <common-dir>/lfs/objects exists with that SHA-256.
Prints one JSON summary line; exits 1 on any mismatch.
"""
import hashlib
import json
import os
import subprocess
import sys

group = [p for p in open(sys.argv[1], encoding="utf-8").read().split("\0") if p]
staged_raw = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], capture_output=True, check=True).stdout.decode("utf-8")
staged = [p for p in staged_raw.split("\0") if p]
problems = []
if set(staged) != set(group):
    problems.append({"missing": sorted(set(group) - set(staged))[:5], "extra": sorted(set(staged) - set(group))[:5]})
entries = {}
for line in subprocess.run(["git", "ls-files", "-s", "-z", "--"] + [], capture_output=True, check=True).stdout.decode("utf-8").split("\0"):
    if line:
        meta, path = line.split("\t", 1)
        entries[path] = meta.split()[1]
common = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
filters = {}
out = subprocess.run(["git", "check-attr", "filter", "--stdin", "-z"], input="\0".join(group).encode("utf-8"), capture_output=True, check=True).stdout.decode("utf-8").split("\0")
for i in range(0, len(out) - 2, 3):
    filters[out[i]] = out[i + 2]
regular = [p for p in group if filters.get(p) != "lfs"]
lfs = [p for p in group if filters.get(p) == "lfs"]
if regular:
    hashed = subprocess.run(["git", "hash-object", "--no-filters", "--stdin-paths"], input="\n".join(regular).encode("utf-8"), capture_output=True, check=True).stdout.decode().split()
    for path, blob in zip(regular, hashed):
        if entries.get(path) != blob:
            problems.append({"regular_bytes_differ": path})
lfs_bytes = 0
for path in lfs:
    pointer = subprocess.run(["git", "cat-file", "blob", entries.get(path, "")], capture_output=True).stdout.decode("utf-8", "replace")
    fields = dict(line.split(" ", 1) for line in pointer.splitlines() if " " in line)
    data = open(path, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    oid = fields.get("oid", "").replace("sha256:", "")
    obj = os.path.join(common, "lfs", "objects", oid[:2], oid[2:4], oid)
    ok = oid == digest and fields.get("size") == str(len(data)) and os.path.exists(obj) and hashlib.sha256(open(obj, "rb").read()).hexdigest() == digest
    if not ok:
        problems.append({"lfs_mismatch": path})
    lfs_bytes += len(data)
summary = {"group": os.path.basename(sys.argv[1]), "staged": len(staged), "group_files": len(group), "regular": len(regular), "lfs": len(lfs),
           "lfs_bytes": lfs_bytes, "problems": problems[:10], "problem_count": len(problems)}
print(json.dumps(summary, ensure_ascii=False))
sys.exit(1 if problems else 0)
