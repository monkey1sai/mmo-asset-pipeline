#!/usr/bin/env bash
# Push the four commits of authorization entry 27 to origin codex/art-quality-loop one batch at a time (LFS objects first,
# then a fast-forward of the remote branch). Stops at the first failure and leaves later batches untouched.
set -uo pipefail
cd /c/Repos/mmo-asset-pipeline/tmp/art-quality-loop
export GIT_TERMINAL_PROMPT=0
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
remote=$(git ls-remote --heads origin codex/art-quality-loop | cut -f1)
if [ "$remote" != "50daee36d3c520a4e1588412465a7708adaa45df" ]; then echo "== $(stamp) REMOTE_MOVED $remote"; exit 10; fi
for c in 38c03ca 14fb448 3b7e4a5 75b8950; do
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
