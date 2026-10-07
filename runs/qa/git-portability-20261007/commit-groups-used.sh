#!/usr/bin/env bash
# Stage, verify and commit the four groups of authorization entry 27, one at a time (stops at the first problem).
set -uo pipefail
cd /c/Repos/mmo-asset-pipeline/tmp/art-quality-loop
G=runs/qa/git-portability-20261007
VERIFY=runs/qa/git-portability-20261005/verify-stage-used.py
n=0
for g in 1-records 2-tools 3-p4-blender-runs 4-p4-runtime-and-records; do
  n=$((n+1))
  if [ -n "$(git diff --cached --name-only)" ]; then echo "INDEX_NOT_EMPTY before $g"; exit 21; fi
  git add --pathspec-from-file="$G/groups/$g.txt" --pathspec-file-nul || { echo "ADD_FAILED $g"; exit 22; }
  python -B "$VERIFY" "$G/groups/$g.txt" || { echo "VERIFY_FAILED $g"; exit 23; }
  git commit -q -F "$G/commit-message-$n.txt" || { echo "COMMIT_FAILED $g"; exit 24; }
  echo "COMMITTED $g $(git rev-parse --short HEAD)"
done
git log --oneline -5
