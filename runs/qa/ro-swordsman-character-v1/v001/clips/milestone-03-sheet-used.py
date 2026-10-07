"""Milestone 3 review sheet (report only): one row per bed clip from its b20 clip-check previews (three-quarter view,
gray workbench, bed proxy drawn as a gray box), frame numbers and the check's numeric result in the row label.

Run: python -B milestone-03-sheet-used.py <out.png>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[5]
Q = ROOT / "runs/qa/ro-swordsman-character-v1/v001/clips"
ROWS = [("AN_RO_LieDown a07", Q / "AN_RO_LieDown/a07-check-b20", [0, 18, 30, 36, 40, 53, 57, 63, 75, 89]),
        ("AN_RO_GetUp a01", Q / "AN_RO_GetUp/a01-check-b20-socketfix", [0, 27, 40, 52, 57, 60, 66, 72, 80, 89]),
        ("AN_RO_Sleep_Loop a04", Q / "AN_RO_Sleep_Loop/a04-check-b20", [0, 45, 90, 135])]
TILE, LABEL, CAPTION = 256, 30, 18
columns = max(len(frames) for _, _, frames in ROWS)
sheet = Image.new("RGB", (TILE * columns, (TILE + LABEL + CAPTION) * len(ROWS)), (24, 24, 28))
draw = ImageDraw.Draw(sheet)
for r, (name, check, frames) in enumerate(ROWS):
    result = json.loads((check / "clip-check.json").read_text(encoding="utf-8"))
    failed = [k for k, ok in result["gates"].items() if not ok]
    top = r * (TILE + LABEL + CAPTION)
    draw.text((6, top + 8), f"{name}  b20  {result['sample_count']} samples  gates {'all pass' if not failed else 'FAIL ' + ','.join(failed)}  "
                            f"min area {result['report_only']['min_triangle_area_ratio']:.4f}", fill=(235, 235, 235))
    for c, frame in enumerate(frames):
        tile = Image.open(check / "preview" / f"f{frame:03d}-three-quarter.png").convert("RGB").resize((TILE, TILE))
        sheet.paste(tile, (c * TILE, top + LABEL))
        draw.text((c * TILE + 6, top + LABEL + TILE + 2), f"frame {frame}", fill=(200, 200, 200))
out = Path(sys.argv[1])
if out.exists():
    raise SystemExit(f"REFUSE_OVERWRITE {out}")
sheet.save(out)
print("CV1_SHEET " + json.dumps({"out": out.as_posix(), "size": sheet.size}))
