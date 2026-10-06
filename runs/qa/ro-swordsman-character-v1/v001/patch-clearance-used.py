"""Finger clearance: classify a touching pair by every finger its six vertices belong to, so web triangles shared by two fingers count."""
from pathlib import Path

path = Path(__file__).resolve().parents[4] / "scripts/cv1_hand_correctives.py"
s = path.read_text(encoding="utf-8")


def patch(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)


patch('''def finger_of(triangle):
    names = [dominant[i] for i in tris[triangle]]
    fingers = {int(n[6]) for n in names if n.startswith("finger")}
    return fingers.pop() if len(fingers) == 1 and all(n.startswith("finger") for n in names) else None
''', '''def fingers_of(pair):
    """The one or two fingers a touching pair belongs to, or None when the palm, thumb or three fingers are involved."""
    names = [dominant[i] for triangle in pair for i in tris[triangle]]
    fingers = sorted({int(n[6]) for n in names if n.startswith("finger")})
    if not all(n.startswith("finger") for n in names) or len(fingers) > 2:
        return None
    return (fingers[0], fingers[-1])
''')
patch('''        between = [(a, b) for a, b in pairs if finger_of(a) and finger_of(b) and finger_of(a) != finger_of(b)]''',
      '''        between = [pair for pair in pairs if fingers_of(pair)]''')
patch('''            low_finger, high_finger = sorted((finger_of(a), finger_of(b)))
            by_key.setdefault((low_finger, high_finger), set()).update(tris[a] + tris[b])''',
      '''            by_key.setdefault(fingers_of((a, b)), set()).update(tris[a] + tris[b])''')
path.write_text(s, encoding="utf-8", newline=chr(10))
print("patched")
