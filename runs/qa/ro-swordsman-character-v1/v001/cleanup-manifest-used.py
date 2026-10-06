"""List the superseded intermediate BLEND files of candidate v001 with size and SHA-256 before they are removed.

Usage: python -B cleanup-manifest-used.py   (writes cleanup-manifest-01.json and cleanup-list-01.txt; removes nothing)
Authority: user, 2026-10-05, "清掉被取代的中間檔，只留紀錄與目前版本".
"""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "assets/processed/ro-swordsman-character-v1/v001"
KEEP = BASE / "b03-hands/ro_character_v001_b03-hands.blend"
Q = ROOT / "runs/qa/ro-swordsman-character-v1/v001"


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


blends = sorted(BASE.rglob("*.blend"))
assert KEEP in blends and not list(BASE.rglob("*.blend1"))
remove = [p for p in blends if p != KEEP]
manifest = {
    "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "authority": "清掉被取代的中間檔，只留紀錄與目前版本",
    "method": "moved to the Windows Recycle Bin (recoverable until the bin is emptied); not hard-deleted",
    "kept": {"path": KEEP.relative_to(ROOT).as_posix(), "bytes": KEEP.stat().st_size, "sha256": sha(KEEP)},
    "kept_records": "every JSON report, rules file and poses file beside the removed BLENDs, and all of runs/qa",
    "removed": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in remove],
    "rebuild": ["scripts/cv1_v001_assemble.py --tag <name> --cuff-blend-mm 30 --twist-fade-mm 12 --stump-cut-mm -55 --toe-blend-mm 50 --toe-radius-mm 60 --left-bracer cut --hand-material",
                "scripts/cv1_core_microcorrectives.py --sites runs/qa/ro-swordsman-character-v1/v001/core-fold-sites-3-c0.json --poses <poses.json>",
                "scripts/cv1_hand_correctives.py", "exact arguments of each build are in runs/qa/ro-swordsman-character-v1/v001/*.log and the per-build reports"],
    "note": "Earlier evidence files still cite the removed BLENDs by path and SHA-256; those citations now point to files that are no longer in the repository.",
}
manifest["removed_count"], manifest["removed_bytes"] = len(remove), sum(r["bytes"] for r in manifest["removed"])
with open(Q / "cleanup-manifest-01.json", "x", encoding="utf-8", newline=chr(10)) as handle:
    json.dump(manifest, handle, ensure_ascii=False, indent=1)
with open(Q / "cleanup-list-01.txt", "x", encoding="utf-8", newline=chr(10)) as handle:
    handle.write(chr(10).join(str(p) for p in remove) + chr(10))
print(manifest["removed_count"], "files", round(manifest["removed_bytes"] / 1048576, 1), "MB; keeping", manifest["kept"]["path"])
