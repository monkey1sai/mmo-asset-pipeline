"""Compose joint-range tiles into review sheets: one row per motion, columns typical | extreme.

Usage: python -B scripts/cv1_contact_sheets.py <joint-range-result.json> [rows_per_sheet]
Sheets are written next to the result under sheets/; existing sheets are not overwritten.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
result_path = Path(sys.argv[1]).resolve()
rows_per_sheet = int(sys.argv[2]) if len(sys.argv) > 2 else 4
result = json.loads(result_path.read_text(encoding="utf-8"))
out = result_path.parent / "sheets"
out.mkdir(exist_ok=False)
LABEL = 22

groups = {}
for row in result["results"]:
    if row["status"] == "measured" and row["levels"]["typical"]["tile"]:
        groups.setdefault(row["region"], []).append(row)
written = []
for region, rows in groups.items():
    for start in range(0, len(rows), rows_per_sheet):
        chunk = rows[start:start + rows_per_sheet]
        tiles = [[Image.open(ROOT / row["levels"][level]["tile"]).convert("RGB") for level in ("typical", "extreme")] for row in chunk]
        size = tiles[0][0].width
        sheet = Image.new("RGB", (size * 2, (size + LABEL) * len(chunk)), (24, 24, 28))
        draw = ImageDraw.Draw(sheet)
        for r, (row, pair) in enumerate(zip(chunk, tiles)):
            top = r * (size + LABEL)
            typical, extreme = row["levels"]["typical"], row["levels"]["extreme"]
            label = lambda r: f"c{r['collapsed_triangles']} hand {r['hand_self_pairs']}+{r['hand_other_new_pairs']} body {r['other_new_pairs']}"
            draw.text((6, top + 5), f"{row['id']}  typical {label(typical)}  |  extreme {label(extreme)}  {'PASS' if row['pass'] else 'FAIL'}", fill=(235, 235, 235))
            for c, tile in enumerate(pair):
                sheet.paste(tile, (c * size, top + LABEL))
        name = f"{region.replace('.', '-')}-{start // rows_per_sheet + 1:02d}.png"
        sheet.save(out / name)
        written.append(name)
print(len(written), "sheets:", " ".join(written))
