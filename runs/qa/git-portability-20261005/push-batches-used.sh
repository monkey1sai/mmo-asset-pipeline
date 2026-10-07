#!/usr/bin/env bash
# Push the four commits of codex/art-quality-loop one batch at a time (authorization entry 15).
# For each commit: upload its LFS objects first, then fast-forward the new remote branch to it.
# Stops at the first failure (quota refusal, size limit, auth or host-key problem) and leaves later batches untouched.
set -uo pipefail
cd /c/Repos/mmo-asset-pipeline/tmp/art-quality-loop
export GIT_TERMINAL_PROMPT=0
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
for c in ab8338e 78fae61 0b7c7c7 1002450; do
  echo "== $(stamp) LFS_PUSH_START $c"
  if ! git lfs push origin "$c"; then echo "== $(stamp) LFS_PUSH_FAILED $c"; exit 11; fi
  echo "== $(stamp) LFS_PUSH_DONE $c"
  echo "== $(stamp) GIT_PUSH_START $c"
  if ! git push origin "$c:refs/heads/codex/art-quality-loop"; then echo "== $(stamp) GIT_PUSH_FAILED $c"; exit 12; fi
  echo "== $(stamp) GIT_PUSH_DONE $c"
done
git branch --set-upstream-to=origin/codex/art-quality-loop codex/art-quality-loop
echo "== $(stamp) REMOTE_HEADS"
git ls-remote --heads origin
echo "== $(stamp) ALL_DONE"
