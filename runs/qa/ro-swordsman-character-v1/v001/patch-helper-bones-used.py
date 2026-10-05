"""Add helper-bone rules to the corrective rule evaluators (Python and JavaScript) with tests.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-helper-bones-used.py
A helper bone (pauldron, coat panel) turns by a share of one or more sibling bones' rotations. The share is applied in
the shared parent's frame, so it does not depend on the two bones' rolls. Helpers are evaluated after the mixer and
before the morph rules, and they are owned by the evaluator: a clip must not key them.
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
    ('''def validate_rules(rules: dict) -> None:''', '''def _mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def _share(q, t):
    """Slerp from identity toward q by t along the shortest path."""
    w, x, y, z = _unit(q)
    if w < 0:
        w, x, y, z = -w, -x, -y, -z
    half = math.acos(min(1.0, w))
    s = math.sin(half)
    if s < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    k = math.sin(t * half) / s
    return (math.cos(t * half), x * k, y * k, z * k)


def helper_rotations(rules: dict, pose_rel: dict, rest_local: dict, parents: dict) -> dict:
    """Rest-relative local rotations of the helper bones.

    rest_local: bone -> rest rotation relative to its parent (wxyz); parents: bone -> parent name.
    Each source's rotation is moved into the shared parent frame, scaled by its share and applied to the helper.
    """
    out = {}
    for helper in rules.get("helpers", []):
        bone = helper["bone"]
        if bone not in rest_local:
            raise RuleError("MISSING_BONE:" + bone)
        total = (1.0, 0.0, 0.0, 0.0)
        for follow in helper["follow"]:
            source = follow["source"]
            if source not in pose_rel or source not in rest_local:
                raise RuleError("MISSING_BONE:" + source)
            if parents.get(source) != parents.get(bone):
                raise RuleError("HELPER_NOT_SIBLING:" + bone)
            rest = _unit(rest_local[source])
            in_parent = _mul(_mul(rest, _unit(pose_rel[source])), _conj(rest))
            total = _mul(_share(in_parent, float(follow["share"])), total)
        rest = _unit(rest_local[bone])
        out[bone] = _unit(_mul(_mul(_conj(rest), total), rest))
    return out


def helper_conflicts(rules: dict, animated_bones) -> list:
    """Helper bones that an animation clip also keys."""
    validate_rules(rules)
    return sorted({h["bone"] for h in rules.get("helpers", [])} & set(animated_bones))


def validate_rules(rules: dict) -> None:'''),
    ('''    seen = set()
    for channel in channels:''', '''    helpers = rules.get("helpers", [])
    if not isinstance(helpers, list):
        raise RuleError("RULES_SCHEMA")
    helper_bones = set()
    for helper in helpers:
        follow = helper.get("follow") if isinstance(helper, dict) else None
        if not isinstance(helper.get("bone"), str) or helper["bone"] in helper_bones or helper.get("owner") != "runtime_evaluator" or not isinstance(follow, list) or not follow:
            raise RuleError("INVALID_HELPER")
        if any(not isinstance(f, dict) or not isinstance(f.get("source"), str) or not 0.0 <= float(f.get("share", -1)) <= 1.0 for f in follow):
            raise RuleError("INVALID_HELPER")
        helper_bones.add(helper["bone"])
    if helper_bones & {f["source"] for h in helpers for f in h["follow"]}:
        raise RuleError("HELPER_CHAIN")
    seen = set()
    for channel in channels:'''),
])
patch("tools/runtime-qa/three/src/cv1-pose-rules.js", [
    ('''export function validateRules(rules) {''', '''const mul = (a, b) => [
  a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
  a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
const conj = (q) => [q[0], -q[1], -q[2], -q[3]];

// Slerp from identity toward q by t along the shortest path.
function share(q, t) {
  let [w, x, y, z] = unit(q);
  if (w < 0) [w, x, y, z] = [-w, -x, -y, -z];
  const half = Math.acos(Math.min(1, w)), s = Math.sin(half);
  if (s < 1e-12) return [1, 0, 0, 0];
  const k = Math.sin(t * half) / s;
  return [Math.cos(t * half), x * k, y * k, z * k];
}

// Rest-relative local rotations of the helper bones; restLocal: bone -> rest rotation relative to its parent, parents: bone -> parent name.
export function helperRotations(rules, poseRel, restLocal, parents) {
  const out = {};
  for (const helper of rules.helpers ?? []) {
    if (!(helper.bone in restLocal)) throw new RuleError(`MISSING_BONE:${helper.bone}`);
    let total = [1, 0, 0, 0];
    for (const follow of helper.follow) {
      if (!(follow.source in poseRel) || !(follow.source in restLocal)) throw new RuleError(`MISSING_BONE:${follow.source}`);
      if (parents[follow.source] !== parents[helper.bone]) throw new RuleError(`HELPER_NOT_SIBLING:${helper.bone}`);
      const rest = unit(restLocal[follow.source]);
      total = mul(share(mul(mul(rest, unit(poseRel[follow.source])), conj(rest)), Number(follow.share)), total);
    }
    const rest = unit(restLocal[helper.bone]);
    out[helper.bone] = unit(mul(mul(conj(rest), total), rest));
  }
  return out;
}

// Helper bones that an animation clip also keys.
export function helperConflicts(rules, animatedBones) {
  validateRules(rules);
  const animated = new Set(animatedBones);
  return (rules.helpers ?? []).map((h) => h.bone).filter((bone) => animated.has(bone)).sort();
}

export function validateRules(rules) {'''),
    ('''  const seen = new Set();
  for (const channel of channels) {''', '''  const helpers = rules.helpers ?? [];
  if (!Array.isArray(helpers)) throw new RuleError('RULES_SCHEMA');
  const helperBones = new Set();
  for (const helper of helpers) {
    const valid = helper && typeof helper.bone === 'string' && !helperBones.has(helper.bone) && helper.owner === 'runtime_evaluator' && Array.isArray(helper.follow) && helper.follow.length
      && helper.follow.every((f) => f && typeof f.source === 'string' && Number(f.share) >= 0 && Number(f.share) <= 1);
    if (!valid) throw new RuleError('INVALID_HELPER');
    helperBones.add(helper.bone);
  }
  if (helpers.some((h) => h.follow.some((f) => helperBones.has(f.source)))) throw new RuleError('HELPER_CHAIN');
  const seen = new Set();
  for (const channel of channels) {'''),
])
patch("tests/test_cv1_pose_rules.py", [
    ('''    @unittest.skipUnless(shutil.which('node'), 'node not installed')''', '''    def test_helper_turns_by_its_share_in_the_parent_frame(self):
        rules = sample_rules()
        rules['helpers'] = [{'bone': 'pauldron', 'owner': 'runtime_evaluator', 'follow': [{'source': 'arm', 'share': 0.5}]}]
        rest_arm, rest_pauldron = axis_angle((0, 0, 1), 30), axis_angle((1, 0, 0), -50)
        parents = {'arm': 'clavicle', 'pauldron': 'clavicle'}
        arm = axis_angle((0.2, 1, 0.1), 80)
        out = rules_math.helper_rotations(rules, {'arm': arm}, {'arm': rest_arm, 'pauldron': rest_pauldron}, parents)['pauldron']
        # Same rotation seen from the parent: rest_pauldron * out * rest_pauldron^-1 equals half of rest_arm * arm * rest_arm^-1.
        mul, conj = rules_math._mul, rules_math._conj
        seen = mul(mul(rest_pauldron, out), conj(rest_pauldron))
        expected = rules_math._share(mul(mul(rest_arm, arm), conj(rest_arm)), 0.5)
        self.assertAlmostEqual(abs(sum(a * b for a, b in zip(seen, expected))), 1.0, places=12)
        self.assertAlmostEqual(math.degrees(rules_math.quat_angle(out, (1, 0, 0, 0))), 40.0, places=9)
        with self.assertRaisesRegex(rules_math.RuleError, 'HELPER_NOT_SIBLING'):
            rules_math.helper_rotations(rules, {'arm': arm}, {'arm': rest_arm, 'pauldron': rest_pauldron}, {'arm': 'clavicle', 'pauldron': 'spine'})
        self.assertEqual(rules_math.helper_conflicts(rules, ['arm', 'pauldron']), ['pauldron'])
        rules['helpers'].append({'bone': 'strap', 'owner': 'runtime_evaluator', 'follow': [{'source': 'pauldron', 'share': 0.5}]})
        with self.assertRaisesRegex(rules_math.RuleError, 'HELPER_CHAIN'):
            rules_math.validate_rules(rules)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_helpers_match_python(self):
        rules = sample_rules()
        rules['helpers'] = [{'bone': 'coat', 'owner': 'runtime_evaluator', 'follow': [{'source': 'legL', 'share': 0.3}, {'source': 'legR', 'share': 0.3}]}]
        rest = {'legL': axis_angle((1, 0.2, 0), 170), 'legR': axis_angle((1, -0.2, 0), 170), 'coat': axis_angle((0, 0, 1), 175)}
        parents = {'legL': 'pelvis', 'legR': 'pelvis', 'coat': 'pelvis'}
        pose = {'legL': axis_angle((1, 0, 0.3), 95), 'legR': axis_angle((0.2, 1, 0), -40)}
        script = ("import {helperRotations} from %s;"
                  "const i = JSON.parse(await new Promise(r => {let s=''; process.stdin.on('data', d => s += d).on('end', () => r(s));}));"
                  "console.log(JSON.stringify(helperRotations(i.rules, i.pose, i.rest, i.parents)));") % json.dumps(JS_MODULE.as_uri())
        done = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps({'rules': rules, 'pose': pose, 'rest': rest, 'parents': parents}),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        expected = rules_math.helper_rotations(rules, pose, rest, parents)['coat']
        for a, b in zip(json.loads(done.stdout)['coat'], expected):
            self.assertAlmostEqual(a, b, places=12)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')'''),
])
print("patched")
