"""Split the pending files of the worktree into the commit groups of authorization entry 23 (run from the worktree root).

Usage: python -B make-groups-used.py <out dir>
Writes <n>-<name>.txt (NUL-separated paths, the input of verify-stage) and prints counts and LFS/regular bytes per group.
Every pending file (modified tracked + untracked, not ignored) must land in exactly one group, else it stops.
"""
import json
import os
import subprocess
import sys

run = lambda *a, **k: subprocess.run(list(a), capture_output=True, check=True, **k).stdout
pending = sorted({p for p in run("git", "diff", "--name-only", "-z").decode("utf-8").split("\0") if p} |
                 {p for p in run("git", "ls-files", "--others", "--exclude-standard", "-z").decode("utf-8").split("\0") if p})
V = "runs/qa/ro-swordsman-character-v1/"
A = "assets/processed/ro-swordsman-character-v1/v001/"
GROUPS = [
    ("1-records-attributes", lambda p: p == ".gitattributes" or p.startswith("runs/qa/git-portability-2026100")),
    ("2-tools", lambda p: p.startswith(("scripts/", "tests/", "tools/"))),
    ("3-foundations-b19-b20", lambda p: p.startswith((A + "b19-", A + "b20-", V + "v001/b18-", V + "v001/b19-", V + "v001/b20-",
                                                     V + "v001/core-fold-sites-crotch-b19.json"))),
    ("4-clip-assets", lambda p: p.startswith(A + "clips/")),
    ("5-clip-qa-and-records", lambda p: p.startswith((V + "v001/clips/", V + "authorizations.json", V + "v001/v001-pause-", V + "v001/write-pause-"))),
]
assigned = {}
for path in pending:
    names = [name for name, test in GROUPS if test(path)]
    if len(names) != 1:
        raise SystemExit(f"UNASSIGNED_OR_DOUBLE {path} {names}")
    assigned.setdefault(names[0], []).append(path)
filters = {}
out = run("git", "check-attr", "filter", "--stdin", "-z", input="\0".join(pending).encode("utf-8")).decode("utf-8").split("\0")
for i in range(0, len(out) - 2, 3):
    filters[out[i]] = out[i + 2]
os.makedirs(sys.argv[1], exist_ok=True)
summary = {}
for name, _ in GROUPS:
    paths = assigned.get(name, [])
    with open(os.path.join(sys.argv[1], name + ".txt"), "w", encoding="utf-8", newline="") as handle:
        handle.write("\0".join(paths))
    lfs = [p for p in paths if filters.get(p) == "lfs"]
    summary[name] = {"files": len(paths), "lfs": len(lfs), "lfs_bytes": sum(os.path.getsize(p) for p in lfs),
                     "regular_bytes": sum(os.path.getsize(p) for p in paths if p not in lfs)}
print(json.dumps({"pending": len(pending), "groups": summary}, indent=1))
