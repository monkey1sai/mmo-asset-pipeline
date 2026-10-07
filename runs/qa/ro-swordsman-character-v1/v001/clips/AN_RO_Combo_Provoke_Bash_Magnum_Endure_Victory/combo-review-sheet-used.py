"""Combo a07 review sheet (report only): twelve clip-check preview instants (three-quarter and right views, gray workbench, no
effects) and six effects-layer previews (Eevee, review camera). Run from the worktree root: python -B .../combo-review-sheet-used.py <out.png>"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
Q = Path("runs/qa/ro-swordsman-character-v1/v001/clips/AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory")
A = Path("assets/processed/ro-swordsman-character-v1/v001/clips/AN_RO_Combo_Provoke_Bash_Magnum_Endure_Victory")
check = json.loads((Q / "a07-check-b20/clip-check.json").read_text(encoding="utf-8"))
frames = [0, 24, 45, 80, 100, 112, 130, 160, 172, 215, 268, 290]
labels = ["Idle start", "provoke beckon", "provoke raise", "bash windup", "windup hold", "bash slash", "pre-guard", "jump (guard)", "magnum impact", "endure guard", "victory raise", "return to Idle"]
fx_frames = [104, 112, 176, 186, 225, 272]
T, CAP = 300, 20
sheet = Image.new("RGB", (T * 6, 28 + (T + CAP) * 5), (24, 24, 28))
d = ImageDraw.Draw(sheet)
failed = [k for k, ok in check["gates"].items() if not ok]
d.text((6, 6), f"AN_RO_Combo a07  b20  {check['sample_count']} samples  gates FAIL {','.join(failed)} (known failures, authorization entry 29)  min area {check['report_only']['min_triangle_area_ratio']:.4f}", fill=(235, 235, 235))
for i, f in enumerate(frames):
    for j, view in enumerate(("three-quarter", "right")):
        r, c = (i // 6) * 2 + j, i % 6
        y = 28 + r * (T + CAP)
        sheet.paste(Image.open(Q / "a07-preview/preview" / f"f{f:03d}-{view}.png").convert("RGB").resize((T, T)), (c * T, y))
        d.text((c * T + 4, y + T + 2), f"f{f} {labels[i]} ({view})", fill=(200, 200, 200))
y = 28 + 4 * (T + CAP)
for c, f in enumerate(fx_frames):
    sheet.paste(Image.open(A / "a07/fx/preview" / f"f{f:03d}-fx.png").convert("RGB").resize((T, T)), (c * T, y))
    d.text((c * T + 4, y + T + 2), f"f{f} effects layer (separate GLB)", fill=(200, 200, 200))
sheet.save(sys.argv[1]); print(sys.argv[1], sheet.size)
