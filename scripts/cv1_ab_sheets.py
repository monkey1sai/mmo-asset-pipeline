"""Anonymous A/B review sheets from two joint-range results (same contract motions, same camera rule).

Usage: python -B scripts/cv1_ab_sheets.py <result one> <result two> <new out dir> <seed>
Each row shows one motion: side A typical, A extreme, side B typical, B extreme. Which result is A or B is
drawn per row from the seed and written to key.json, which the reviewer must not be given. Rows carry only
the motion name; no counts, pass marks or file names. A motion one subject could not pose shows a blank pair.
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
first, second, out, seed = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
out.mkdir(parents=True, exist_ok=False)
results = [json.loads(p.read_text(encoding="utf-8")) for p in (first, second)]
rows = [{r["id"]: r for r in result["results"]} for result in results]
order = [r["id"] for r in results[1]["results"]]
rng = random.Random(seed)
SIZE, LABEL, PER_SHEET = 320, 20, 4
key, sheets = {}, []
regions = {}
for motion in order:
    regions.setdefault(rows[1][motion]["region"], []).append(motion)
for region, motions in regions.items():
    for start in range(0, len(motions), PER_SHEET):
        chunk = motions[start:start + PER_SHEET]
        sheet = Image.new("RGB", (SIZE * 4 + 12, (SIZE + LABEL) * len(chunk)), (24, 24, 28))
        draw = ImageDraw.Draw(sheet)
        for line, motion in enumerate(chunk):
            a_is_first = rng.random() < 0.5
            key[motion] = {"A": str(first if a_is_first else second), "B": str(second if a_is_first else first)}
            top = line * (SIZE + LABEL)
            draw.text((6, top + 4), f"{motion}    A: typical, extreme    |    B: typical, extreme", fill=(235, 235, 235))
            for slot, source in enumerate((rows[0] if a_is_first else rows[1], rows[1] if a_is_first else rows[0])):
                row = source.get(motion)
                for column, level in enumerate(("typical", "extreme")):
                    x = (slot * 2 + column) * SIZE + (12 if slot else 0)
                    if row and row["status"] == "measured" and row["levels"][level]["tile"]:
                        sheet.paste(Image.open(ROOT / row["levels"][level]["tile"]).convert("RGB").resize((SIZE, SIZE)), (x, top + LABEL))
                    else:
                        draw.text((x + 8, top + LABEL + SIZE // 2), "could not be posed", fill=(200, 120, 120))
        name = f"ab-{region.replace('.', '-')}-{start // PER_SHEET + 1:02d}.png"
        sheet.save(out / name)
        sheets.append(name)
(out.parent / (out.name + "-key.json")).write_text(json.dumps({"seed": seed, "first": str(first), "second": str(second), "key": key}, indent=1), encoding="utf-8")
print(len(sheets), "sheets")
