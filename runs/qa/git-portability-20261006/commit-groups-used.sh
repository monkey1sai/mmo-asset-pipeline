#!/usr/bin/env bash
# Stage, verify and commit the five groups of authorization entry 23, one at a time (stops at the first problem).
set -uo pipefail
cd /c/Repos/mmo-asset-pipeline/tmp/art-quality-loop
S=/c/Users/IOT/AppData/Local/Temp/claude/C--Repos-mmo-asset-pipeline/5e4b1695-2b20-4353-a5a6-f8d5dfcbf121/scratchpad
VERIFY=runs/qa/git-portability-20261005/verify-stage-used.py
n=0
for g in 1-records-attributes 2-tools 3-foundations-b19-b20 4-clip-assets 5-clip-qa-and-records; do
  n=$((n+1))
  if [ -n "$(git diff --cached --name-only)" ]; then echo "INDEX_NOT_EMPTY before $g"; exit 21; fi
  git add --pathspec-from-file="$S/groups/$g.txt" --pathspec-file-nul || { echo "ADD_FAILED $g"; exit 22; }
  python -B "$VERIFY" "$S/groups/$g.txt" || { echo "VERIFY_FAILED $g"; exit 23; }
  git commit -q -F "$S/msg/$n.txt" || { echo "COMMIT_FAILED $g"; exit 24; }
  echo "COMMITTED $g $(git rev-parse --short HEAD)"
done
git log --oneline -6
