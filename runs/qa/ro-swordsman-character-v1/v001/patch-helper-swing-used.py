"""Helper bones: optionally follow only the swing of the source (its twist about its own bone axis removed).

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-helper-swing-used.py
The first helper build turned the pauldrons and coat panels with the upper arm's and thigh's axial twist too,
which swung them around the joint (shoulder and hip axial motions gained 300 to 500 intersection pairs).
Bone axis is local +Y in both Blender and the exported glTF bones.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:60])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_pose_rules.py", [
    ('''def helper_rotations(rules: dict, pose_rel: dict, rest_local: dict, parents: dict) -> dict:''', '''def swing_only(q):
    """Remove the twist about the bone's own axis (local +Y) from a rest-relative local rotation."""
    w, x, y, z = _unit(q)
    n = math.sqrt(w * w + y * y)
    if n < 1e-12:
        return (w, x, y, z)
    return _mul((w, x, y, z), _conj((w / n, 0.0, y / n, 0.0)))


def helper_rotations(rules: dict, pose_rel: dict, rest_local: dict, parents: dict) -> dict:'''),
    ('''            rest = _unit(rest_local[source])
            in_parent = _mul(_mul(rest, _unit(pose_rel[source])), _conj(rest))''', '''            rest = _unit(rest_local[source])
            local = swing_only(pose_rel[source]) if follow.get("swing_only") else _unit(pose_rel[source])
            in_parent = _mul(_mul(rest, local), _conj(rest))'''),
    ('''        if any(not isinstance(f, dict) or not isinstance(f.get("source"), str) or not 0.0 <= float(f.get("share", -1)) <= 1.0 for f in follow):''',
     '''        if any(not isinstance(f, dict) or not isinstance(f.get("source"), str) or not 0.0 <= float(f.get("share", -1)) <= 1.0
               or not isinstance(f.get("swing_only", False), bool) for f in follow):'''),
])
patch("tools/runtime-qa/three/src/cv1-pose-rules.js", [
    ('''// Rest-relative local rotations of the helper bones;''', '''// Remove the twist about the bone's own axis (local +Y) from a rest-relative local rotation.
export function swingOnly(q) {
  const [w, x, y, z] = unit(q);
  const n = Math.hypot(w, y);
  if (n < 1e-12) return [w, x, y, z];
  return mul([w, x, y, z], conj([w / n, 0, y / n, 0]));
}

// Rest-relative local rotations of the helper bones;'''),
    ('''      const rest = unit(restLocal[follow.source]);
      total = mul(share(mul(mul(rest, unit(poseRel[follow.source])), conj(rest)), Number(follow.share)), total);''',
     '''      const rest = unit(restLocal[follow.source]);
      const local = follow.swing_only ? swingOnly(poseRel[follow.source]) : unit(poseRel[follow.source]);
      total = mul(share(mul(mul(rest, local), conj(rest)), Number(follow.share)), total);'''),
    ('''      && helper.follow.every((f) => f && typeof f.source === 'string' && Number(f.share) >= 0 && Number(f.share) <= 1);''',
     '''      && helper.follow.every((f) => f && typeof f.source === 'string' && Number(f.share) >= 0 && Number(f.share) <= 1 && ['undefined', 'boolean'].includes(typeof f.swing_only));'''),
])
patch("tests/test_cv1_pose_rules.py", [
    ('''    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_helpers_match_python(self):''', '''    def test_swing_only_ignores_twist_about_the_bone_axis(self):
        twist = axis_angle((0, 1, 0), 70)
        self.assertAlmostEqual(rules_math.quat_angle(rules_math.swing_only(twist), (1, 0, 0, 0)), 0.0, places=12)
        swing = axis_angle((1, 0, 0.4), 50)
        both = rules_math._mul(swing, twist)
        self.assertAlmostEqual(rules_math.quat_angle(rules_math.swing_only(both), swing), 0.0, places=9)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_helpers_match_python(self):'''),
    ('''        rules['helpers'] = [{'bone': 'coat', 'owner': 'runtime_evaluator', 'follow': [{'source': 'legL', 'share': 0.3}, {'source': 'legR', 'share': 0.3}]}]''',
     '''        rules['helpers'] = [{'bone': 'coat', 'owner': 'runtime_evaluator', 'follow': [{'source': 'legL', 'share': 0.3, 'swing_only': True}, {'source': 'legR', 'share': 0.3}]}]'''),
])
print("patched")
