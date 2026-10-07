"""Milestone 4 review sheet (report only): transitions in the Three.js QA scene (tools/runtime-qa/three/p4.html, run-04
manifest; gates from run-07), five instants per row, each tile labelled with its time and the foot-lock mode of each foot.

Run (worktree root): python -B runs/qa/ro-swordsman-character-v1/v001/p4/milestone-04-sheet-used.py <out.png>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
import cv1_foot_lock as fl  # noqa: E402

P = ROOT / "runs/qa/ro-swordsman-character-v1/v001/p4"
SHOTS = P / "runtime"
spec = json.loads((P / "transitions-05.json").read_text(encoding="utf-8"))
by_id = {s["id"]: s for s in spec["scenarios"]}
check = {s["id"]: s for s in json.loads((P / "run-07/merged/transition-check.json").read_text(encoding="utf-8"))["scenarios"]}
recheck = {s["id"]: s for s in json.loads((P / "run-07/merged/feet-recheck.json").read_text(encoding="utf-8"))["scenarios"]}
# Captures of one uninterrupted pass (whole-body and feet cameras); the side views of that hour were taken by two
# overlapping loops in a throttled hidden page and are not used.
WALK, IDLE_WALK, WALK_RUN = [0.45, 0.55, 0.65, 0.8, 0.95], [0.45, 0.55, 0.65, 0.8, 0.96], [0.45, 0.55, 0.6, 0.65, 0.75]
ROWS = [("idle-walk-p0-b200-s1.0", "whole", "p4-sheet", IDLE_WALK), ("idle-walk-p0-b200-s1.0", "feet", "p4-sheet", IDLE_WALK),
        ("walk-idle-r-b200-s1.0", "whole", "p4-sheet", WALK), ("walk-idle-r-b200-s1.0", "feet", "p4-sheet", WALK),
        ("walk-run-r-b200-s1.0", "whole", "p4-sheet", WALK_RUN), ("walk-run-r-b200-s1.0", "feet", "p4-sheet", WALK_RUN),
        ("walk-castupper-walk-r-b200-s1.0", "whole", "p4-sheet", [0.45, 0.6, 1.0, 1.85, 1.95]),
        ("idle-liedown-p0-b200-s1.0", "whole", "p4-sheet", [0.45, 0.55, 0.65, 0.85, 1.1]),
        ("getup-idle-end-b200-s1.0", "whole", "p4-sheet", [0.45, 0.55, 0.65, 0.75, 0.9])]
TILE, LABEL, CAPTION = 256, 30, 34
rows = len(ROWS) + 1
sheet = Image.new("RGB", (TILE * 5, (TILE + LABEL + CAPTION) * rows), (24, 24, 28))
draw = ImageDraw.Draw(sheet)


def stem(t):
    """The capture names follow JavaScript String(t): 1.0 is "1"."""
    return (str(int(t)) if float(t).is_integer() else str(t)).replace(".", "p")


for r, (sid, camera, prefix, times) in enumerate(ROWS):
    s = by_id[sid]
    locks = fl.schedule(s, spec["clips"])
    gates = recheck[sid]["gates"]
    failed = [k for k, ok in gates.items() if not ok]
    top = r * (TILE + LABEL + CAPTION)
    draw.text((6, top + 8), f"{s['pair']}  {sid}  ({camera})  gates {'all pass' if not failed else 'FAIL ' + ','.join(failed)}  "
                            f"min area {check[sid]['worst']['min_area_ratio']:.4f}", fill=(235, 235, 235))
    for c, t in enumerate(times):
        tile = Image.open(SHOTS / f"{prefix}-{sid}-{camera}-{stem(t)}.png").convert("RGB").resize((TILE, TILE))
        sheet.paste(tile, (c * TILE, top + LABEL))
        modes = " ".join(f"{side}:{fl.mode_at(locks[side], t)[0] or '-'}" for side in fl.SIDES)
        draw.text((c * TILE + 6, top + LABEL + TILE + 2), f"t {t:.2f} s   {modes}", fill=(200, 200, 200))
top = len(ROWS) * (TILE + LABEL + CAPTION)
draw.text((6, top + 8), "foot lock on / off at the same instant: idle-walk-p0-b200-s1.0 t 0.68 s (side, then whole)", fill=(235, 235, 235))
for c, name in enumerate(["p4-sheet-lock-on-side-0p68.png", "p4-sheet-lock-off-side-0p68.png", "p4-sheet-lock-on-whole-0p68.png", "p4-sheet-lock-off-whole-0p68.png"]):
    sheet.paste(Image.open(SHOTS / name).convert("RGB").resize((TILE, TILE)), (c * TILE, top + LABEL))
    draw.text((c * TILE + 6, top + LABEL + TILE + 2), "lock on" if "-on-" in name else "lock off", fill=(200, 200, 200))
sheet.save(sys.argv[1])
print(sys.argv[1], sheet.size)
