"""Make the fade from the twist carrier to the static carrier a parameter (default 12 mm) so the static part reaches the bracer end."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_v001_assemble.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('parser.add_argument("--toe-blend-mm", type=float)', 'parser.add_argument("--toe-blend-mm", type=float)\nparser.add_argument("--twist-fade-mm", type=float, default=12.0)')
patch("u = min(1.0, max(0.0, (axial + span) / 0.02 + 1.0))", "u = min(1.0, max(0.0, (axial + span) / (args.twist_fade_mm / 1000) + 1.0))")
patch("fading to the static carrier 20 mm further back.", "fading to the static carrier over --twist-fade-mm further back.")
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
