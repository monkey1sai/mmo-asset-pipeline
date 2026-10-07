#!/usr/bin/env bash
# Push the five commits of authorization entry 23 to origin codex/art-quality-loop one batch at a time.
# For each commit: upload its LFS objects first, then fast-forward the remote branch to it.
# Stops at the first failure (quota refusal, size limit, auth or host-key problem, non-fast-forward) and leaves later batches untouched.
set -uo pipefail
cd /c/Repos/mmo-asset-pipeline/tmp/art-quality-loop
export GIT_TERMINAL_PROMPT=0
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
remote=$(git ls-remote --heads origin codex/art-quality-loop | cut -f1)
if [ "$remote" != "10024506e332f75f6f9b8577fe377fd4796c1b1b" ]; then echo "== $(stamp) REMOTE_MOVED $remote"; exit 10; fi
for c in 7b73d60 86091bf 3a04b55 9d2a4fc 50daee3; do
  echo "== $(stamp) LFS_PUSH_START $c"
  if ! git lfs push origin "$c"; then echo "== $(stamp) LFS_PUSH_FAILED $c"; exit 11; fi
  echo "== $(stamp) LFS_PUSH_DONE $c"
  echo "== $(stamp) GIT_PUSH_START $c"
  if ! git push origin "$c:refs/heads/codex/art-quality-loop"; then echo "== $(stamp) GIT_PUSH_FAILED $c"; exit 12; fi
  echo "== $(stamp) GIT_PUSH_DONE $c"
done
echo "== $(stamp) REMOTE_HEADS"
git ls-remote --heads origin
echo "== $(stamp) ALL_DONE"
