import json, math, shutil, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cv1_pose_rules as rules_math

JS_MODULE = ROOT / 'tools/runtime-qa/three/src/cv1-pose-rules.js'


def axis_angle(axis, degrees):
    n = math.sqrt(sum(c * c for c in axis))
    half = math.radians(degrees) / 2
    return [math.cos(half)] + [c / n * math.sin(half) for c in axis]


TARGET = axis_angle((0.3, -0.39, 0.87), 133.6)


def sample_rules():
    hats = [('K25', 0.0, 0.25, 0.5), ('K50', 0.25, 0.5, 0.75), ('K75', 0.5, 0.75, 1.0), ('K100', 0.75, 1.0, None)]
    return {
        'schema_version': 1,
        'drivers': {'wrist': {'type': 'rotation_difference', 'bone': 'hand.R', 'target_quaternion_wxyz': TARGET},
                    'grasp': {'type': 'state', 'key': 'grasp.R'}},
        'channels': [{'mesh': 'Loft', 'morph': name, 'owner': 'runtime_evaluator', 'driver': 'wrist',
                      'curve': {'type': 'hat', 'prev': prev, 'at': at, 'next': nxt}} for name, prev, at, nxt in hats]
        + [{'mesh': 'Glove', 'morph': 'Grip', 'owner': 'runtime_evaluator', 'driver': 'grasp', 'curve': {'type': 'linear'}}],
    }


class PoseRuleTests(unittest.TestCase):
    def test_progress_follows_authored_axis_and_clamps(self):
        for fraction in (0.0, 0.125, 0.5, 1.0):
            pose = axis_angle((0.3, -0.39, 0.87), 133.6 * fraction)
            self.assertAlmostEqual(rules_math.rotation_difference_progress(pose, TARGET), fraction, places=9)
        self.assertEqual(rules_math.rotation_difference_progress(axis_angle((0.3, -0.39, 0.87), -40), TARGET), 0.0)

    def test_off_axis_rotation_of_equal_size_scores_lower(self):
        off_axis = rules_math.rotation_difference_progress(axis_angle((1, 0, 0), 66.8), TARGET)
        self.assertLess(off_axis, 0.5)

    def test_quaternion_sign_does_not_change_weights(self):
        pose = axis_angle((0.3, -0.39, 0.87), 50)
        flipped = [-c for c in pose]
        self.assertEqual(rules_math.evaluate(sample_rules(), {'hand.R': pose}, {'grasp.R': 0.2}),
                         rules_math.evaluate(sample_rules(), {'hand.R': flipped}, {'grasp.R': 0.2}))

    def test_inbetween_weights_at_stops_and_between(self):
        def weights(fraction):
            out = rules_math.evaluate(sample_rules(), {'hand.R': axis_angle((0.3, -0.39, 0.87), 133.6 * fraction)}, {'grasp.R': 0.0})
            return [round(out[('Loft', k)], 9) for k in ('K25', 'K50', 'K75', 'K100')]
        self.assertEqual(weights(0.0), [0, 0, 0, 0])
        self.assertEqual(weights(0.25), [1, 0, 0, 0])
        self.assertEqual(weights(0.375), [0.5, 0.5, 0, 0])
        self.assertEqual(weights(1.0), [0, 0, 0, 1])

    def test_contact_channel_follows_state_not_pose(self):
        closed = axis_angle((0.3, -0.39, 0.87), 133.6)
        self.assertEqual(rules_math.evaluate(sample_rules(), {'hand.R': closed}, {'grasp.R': 0.0})[('Glove', 'Grip')], 0.0)
        self.assertEqual(rules_math.evaluate(sample_rules(), {'hand.R': [1, 0, 0, 0]}, {'grasp.R': 1.0})[('Glove', 'Grip')], 1.0)

    def test_missing_bone_or_state_raises_instead_of_zero(self):
        with self.assertRaisesRegex(rules_math.RuleError, 'MISSING_BONE:hand.R'):
            rules_math.evaluate(sample_rules(), {}, {'grasp.R': 0.0})
        with self.assertRaisesRegex(rules_math.RuleError, 'MISSING_STATE:grasp.R'):
            rules_math.evaluate(sample_rules(), {'hand.R': [1, 0, 0, 0]}, {})
        with self.assertRaisesRegex(rules_math.RuleError, 'STATE_OUT_OF_RANGE'):
            rules_math.evaluate(sample_rules(), {'hand.R': [1, 0, 0, 0]}, {'grasp.R': 1.5})

    def test_duplicate_channel_and_unknown_owner_are_rejected(self):
        duplicate = sample_rules()
        duplicate['channels'].append(dict(duplicate['channels'][0]))
        with self.assertRaisesRegex(rules_math.RuleError, 'DUPLICATE_OR_INVALID_CHANNEL'):
            rules_math.validate_rules(duplicate)
        both = sample_rules()
        both['channels'][0]['owner'] = 'clip_and_evaluator'
        with self.assertRaisesRegex(rules_math.RuleError, 'CHANNEL_OWNER_OR_DRIVER'):
            rules_math.validate_rules(both)

    def test_ownership_conflict_lists_channels_a_clip_also_writes(self):
        self.assertEqual(rules_math.ownership_conflicts(sample_rules(), [('Body', 'Other')]), [])
        self.assertEqual(rules_math.ownership_conflicts(sample_rules(), [('Glove', 'Grip'), ('Loft', 'K50')]), [('Glove', 'Grip'), ('Loft', 'K50')])
        baked = sample_rules()
        for channel in baked['channels']:
            channel['owner'] = 'baked_clip'
        self.assertEqual(rules_math.ownership_conflicts(baked, [('Glove', 'Grip')]), [])
        self.assertEqual(rules_math.evaluate(baked, {'hand.R': [1, 0, 0, 0]}, {'grasp.R': 1.0}), {})

    def test_product_driver_needs_every_factor_active(self):
        rules = sample_rules()
        rules['drivers']['both'] = {'type': 'product', 'of': ['wrist', 'grasp']}
        rules['channels'].append({'mesh': 'Glove', 'morph': 'Both', 'owner': 'runtime_evaluator', 'driver': 'both', 'curve': {'type': 'linear'}})
        half = axis_angle((0.3, -0.39, 0.87), 66.8)
        self.assertAlmostEqual(rules_math.evaluate(rules, {'hand.R': half}, {'grasp.R': 0.5})[('Glove', 'Both')], 0.25, places=9)
        self.assertEqual(rules_math.evaluate(rules, {'hand.R': half}, {'grasp.R': 0.0})[('Glove', 'Both')], 0.0)
        rules['drivers']['nested'] = {'type': 'product', 'of': ['both', 'grasp']}
        with self.assertRaisesRegex(rules_math.RuleError, 'INVALID_PRODUCT_DRIVER'):
            rules_math.validate_rules(rules)

    def test_helper_turns_by_its_share_in_the_parent_frame(self):
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

    def test_swing_only_ignores_twist_about_the_bone_axis(self):
        twist = axis_angle((0, 1, 0), 70)
        self.assertAlmostEqual(rules_math.quat_angle(rules_math.swing_only(twist), (1, 0, 0, 0)), 0.0, places=12)
        swing = axis_angle((1, 0, 0.4), 50)
        both = rules_math._mul(swing, twist)
        self.assertAlmostEqual(rules_math.quat_angle(rules_math.swing_only(both), swing), 0.0, places=9)

    def test_twist_only_follows_the_turn_about_the_helper_axis_and_ignores_the_bend(self):
        mul, conj = rules_math._mul, rules_math._conj
        rest_hand, rest_twist = axis_angle((0.3, 0, 1), 20), axis_angle((1, 0, 0.2), 155)
        axis = rules_math._rotate(rest_twist, (0, 1, 0))
        bend_axis = (axis[1], -axis[0], 0.0)  # perpendicular to the twist axis
        seen_from_parent = mul(axis_angle(bend_axis, 35), axis_angle(axis, 60))
        hand = mul(mul(conj(rest_hand), seen_from_parent), rest_hand)
        rules = sample_rules()
        rules['helpers'] = [{'bone': 'twist', 'owner': 'runtime_evaluator', 'follow': [{'source': 'hand', 'share': 0.5, 'twist_only': True}]}]
        out = rules_math.helper_rotations(rules, {'hand': hand}, {'hand': rest_hand, 'twist': rest_twist}, {'hand': 'forearm', 'twist': 'forearm'})['twist']
        self.assertAlmostEqual(math.degrees(rules_math.quat_angle(out, axis_angle((0, 1, 0), 30))), 0.0, places=8)
        bend_only = mul(mul(conj(rest_hand), axis_angle(bend_axis, 35)), rest_hand)
        out = rules_math.helper_rotations(rules, {'hand': bend_only}, {'hand': rest_hand, 'twist': rest_twist}, {'hand': 'forearm', 'twist': 'forearm'})['twist']
        self.assertAlmostEqual(math.degrees(rules_math.quat_angle(out, (1, 0, 0, 0))), 0.0, places=8)
        rules['helpers'][0]['follow'][0]['swing_only'] = True
        with self.assertRaisesRegex(rules_math.RuleError, 'INVALID_HELPER'):
            rules_math.validate_rules(rules)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_twist_only_matches_python(self):
        rules = sample_rules()
        rules['helpers'] = [{'bone': 'twist', 'owner': 'runtime_evaluator', 'follow': [{'source': 'hand', 'share': 0.5, 'twist_only': True}]}]
        rest = {'hand': axis_angle((0.3, 0, 1), 20), 'twist': axis_angle((1, 0, 0.2), 155)}
        parents = {'hand': 'forearm', 'twist': 'forearm'}
        pose = {'hand': axis_angle((0.4, 1, -0.3), 75)}
        script = ("import {helperRotations} from %s;"
                  "const i = JSON.parse(await new Promise(r => {let s=''; process.stdin.on('data', d => s += d).on('end', () => r(s));}));"
                  "console.log(JSON.stringify(helperRotations(i.rules, i.pose, i.rest, i.parents)));") % json.dumps(JS_MODULE.as_uri())
        done = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps({'rules': rules, 'pose': pose, 'rest': rest, 'parents': parents}),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        expected = rules_math.helper_rotations(rules, pose, rest, parents)['twist']
        for a, b in zip(json.loads(done.stdout)['twist'], expected):
            self.assertAlmostEqual(a, b, places=12)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_helpers_match_python(self):
        rules = sample_rules()
        rules['helpers'] = [{'bone': 'coat', 'owner': 'runtime_evaluator', 'follow': [{'source': 'legL', 'share': 0.3, 'swing_only': True}, {'source': 'legR', 'share': 0.3}]}]
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

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_evaluator_matches_python(self):
        cases = [{'pose': {'hand.R': axis_angle(axis, degrees)}, 'state': {'grasp.R': grasp}}
                 for axis, degrees, grasp in [((0.3, -0.39, 0.87), 0, 0), ((0.3, -0.39, 0.87), 17.3, 0.35), ((0.3, -0.39, 0.87), 83.5, 1),
                                              ((0.3, -0.39, 0.87), 133.6, 0.5), ((0.3, -0.39, 0.87), 160, 0.1), ((1, 0.2, -0.4), 70, 0.9), ((0, 1, 0), -25, 0)]]
        script = ("import {evaluate, ownershipConflicts} from %s;"
                  "const input = JSON.parse(await new Promise(r => {let s=''; process.stdin.on('data', d => s += d).on('end', () => r(s));}));"
                  "let missing = null; try { evaluate(input.rules, {}, {'grasp.R': 0}); } catch (e) { missing = e.message; }"
                  "console.log(JSON.stringify({weights: input.cases.map(c => evaluate(input.rules, c.pose, c.state)), missing,"
                  " conflicts: ownershipConflicts(input.rules, [['Glove', 'Grip'], ['Body', 'Other']])}));") % json.dumps(JS_MODULE.as_uri())
        shared = sample_rules()
        shared['drivers']['both'] = {'type': 'product', 'of': ['wrist', 'grasp']}
        shared['channels'].append({'mesh': 'Glove', 'morph': 'Both', 'owner': 'runtime_evaluator', 'driver': 'both', 'curve': {'type': 'linear'}})
        done = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps({'rules': shared, 'cases': cases}),
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        output = json.loads(done.stdout)
        self.assertEqual(output['missing'], 'MISSING_BONE:hand.R')
        self.assertEqual(output['conflicts'], [['Glove', 'Grip']])
        for case, rows in zip(cases, output['weights']):
            expected = rules_math.evaluate(shared, case['pose'], case['state'])
            self.assertEqual({(row['mesh'], row['morph']) for row in rows}, set(expected))
            for row in rows:
                self.assertAlmostEqual(row['weight'], expected[(row['mesh'], row['morph'])], places=12)


if __name__ == '__main__':
    unittest.main()
