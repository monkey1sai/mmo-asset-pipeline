import json
import math
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cv1_foot_lock as fl  # noqa: E402

JS_MODULE = ROOT / 'tools/runtime-qa/three/src/cv1-foot-lock.js'
FORWARD = (0.0, -1.0, 0.0)
CLIPS = {
    'Idle': {'frames': 120, 'loop': True, 'fps': 60, 'nominal_speed_m_s': 0.0, 'stance': {'L': [[0, 119]], 'R': [[0, 119]]}},
    'Walk': {'frames': 60, 'loop': True, 'fps': 60, 'nominal_speed_m_s': 1.4, 'stance': {'L': [[30, 54]], 'R': [[0, 24]]}},
    'Run': {'frames': 40, 'loop': True, 'fps': 60, 'nominal_speed_m_s': 3.5, 'stance': {'L': [[20, 29]], 'R': [[0, 9]]}},
    'GetUp': {'frames': 90, 'loop': False, 'fps': 60, 'nominal_speed_m_s': 0.0, 'stance': {'L': [[58, 73]], 'R': [[58, 73]]}},
}


def cut(layer, clip, entry=0.0, speed=1.0):
    return {'t': 0.0, 'layer': layer, 'clip': clip, 'entry_frame': entry, 'speed': speed}


IDLE_WALK = {'events': [cut('Idle', 'Idle'), {'t': 0.5, 'layer': 'Walk', 'clip': 'Walk', 'entry_frame': 0.0, 'speed': 1.0, 'blend_s': 0.2}]}
WALK_IDLE = {'events': [cut('Walk', 'Walk', entry=-18.0 % 60), {'t': 0.5, 'layer': 'Idle', 'clip': 'Idle', 'entry_frame': 0.0, 'speed': 1.0, 'blend_s': 0.2}]}
WALK_RUN_REPEAT = {'events': [cut('Walk', 'Walk', entry=12.0 - 30.0), {'t': 0.5, 'layer': 'Run', 'clip': 'Run', 'entry_frame': 4.5, 'speed': 1.0, 'blend_s': 0.2},
                              {'t': 0.6, 'layer': 'Walk', 'blend_s': 0.2}, {'t': 0.7, 'layer': 'Run', 'blend_s': 0.2}, {'t': 0.8, 'layer': 'Walk', 'blend_s': 0.2}]}
GETUP_IDLE = {'events': [cut('GetUp', 'GetUp', entry=35.0), {'t': 0.5, 'layer': 'Idle', 'clip': 'Idle', 'entry_frame': 0.0, 'speed': 1.0, 'blend_s': 0.4}]}


class FootLockTests(unittest.TestCase):
    def test_a_planted_foot_locks_for_the_fade_and_releases_as_it_swings(self):
        locks = fl.schedule(IDLE_WALK, CLIPS)
        self.assertEqual(locks['L'], [])  # the Walk left foot swings through the fade
        self.assertEqual(len(locks['R']), 1)
        self.assertEqual(locks['R'][0]['lock'], [0.5, 0.5 + 24 / 60])  # until Walk lifts the right foot at frame 24
        self.assertAlmostEqual(locks['R'][0]['release'][1] - locks['R'][0]['release'][0], fl.RELEASE_S)

    def test_a_foot_that_idle_never_lifts_settles_after_the_fade(self):
        locks = fl.schedule(WALK_IDLE, CLIPS)
        self.assertEqual(locks['L'], [])
        self.assertEqual(locks['R'][0]['lock'], [0.5, 0.7])
        self.assertEqual(locks['R'][0]['settle'], [0.7, 0.7 + fl.SETTLE_S])

    def test_the_lock_holds_while_any_leg_layer_keeps_the_foot_down(self):
        walk_run = {'events': [cut('Walk', 'Walk', entry=12.0 - 30.0), {'t': 0.5, 'layer': 'Run', 'clip': 'Run', 'entry_frame': 4.5, 'speed': 1.0, 'blend_s': 0.2}]}
        locks = fl.schedule(walk_run, CLIPS)['R']
        # Run lifts the foot at 0.575 but Walk still has it down until the fade ends at 0.7: the release waits.
        self.assertEqual(locks, [{'lock': [0.5, 0.7], 'release': [0.7, 0.7 + fl.RELEASE_S]}])

    def test_locks_wait_for_the_previous_release(self):
        for side, locks in fl.schedule(WALK_RUN_REPEAT, CLIPS).items():
            for before, after in zip(locks, locks[1:]):
                self.assertGreaterEqual(after['lock'][0], (before.get('release') or before.get('settle'))[1], side)

    def test_drift_is_the_exact_integral_of_the_blended_speed(self):
        self.assertAlmostEqual(fl.drift(WALK_IDLE, CLIPS, 0.5, 0.7), 1.4 * 0.2 / 2)
        self.assertAlmostEqual(fl.drift(WALK_IDLE, CLIPS, 0.4, 0.6), 1.4 * 0.1 + (1.4 + 0.7) / 2 * 0.1)
        self.assertEqual(fl.drift(WALK_IDLE, CLIPS, 0.9, 0.95), 0.0)

    def test_targets_are_continuous_and_end_on_the_free_foot(self):
        locks = fl.schedule(WALK_IDLE, CLIPS)['R']
        fk = lambda side, t: (0.1, -1.4 * t + 0.7, 0.0) if t < 0.7 else (0.1, -0.28, 0.0)  # noqa: E731
        fwd, up = (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)
        at = lambda t: fl.sole_target(WALK_IDLE, CLIPS, locks, 'R', t, fk, fwd, up)  # noqa: E731
        self.assertEqual(at(0.5), fk('R', 0.5))  # no offset when the lock begins
        for t in (0.7, 1.0):
            a, b = at(t - 1e-9), at(t) if t < 1.0 else fk('R', t)
            self.assertLess(fl.norm(fl.sub(a, b)), 1e-6, t)
        self.assertGreater(at(0.85)[2], 0.0)  # the settle step lifts the foot
        self.assertIsNone(at(1.2))

    def test_two_bone_reaches_the_target_and_keeps_the_bone_lengths(self):
        hip, knee, ankle = (0.0, 0.0, 1.0), (0.0, -0.05, 0.52), (0.0, 0.0, 0.05)
        target = (0.02, 0.12, 0.08)
        knee_turn, hip_turn = fl.two_bone(hip, knee, ankle, target, FORWARD, (-1.0, 0.0, 0.0))
        new_knee = fl.add(hip, fl.rotate(hip_turn, fl.sub(knee, hip)))
        new_ankle = fl.add(new_knee, fl.rotate(fl.qmul(hip_turn, knee_turn), fl.sub(ankle, knee)))
        self.assertLess(fl.norm(fl.sub(new_ankle, target)), 1e-12)
        self.assertAlmostEqual(fl.norm(fl.sub(new_knee, hip)), fl.norm(fl.sub(knee, hip)), places=12)
        same = fl.two_bone(hip, knee, ankle, ankle, FORWARD, (-1.0, 0.0, 0.0))
        for q in same:
            self.assertAlmostEqual(abs(q[0]), 1.0, places=12)

    def test_an_unreachable_target_leaves_the_leg_just_short_of_straight(self):
        hip, knee, ankle = (0.0, 0.0, 1.0), (0.0, -0.05, 0.52), (0.0, 0.0, 0.05)
        knee_turn, hip_turn = fl.two_bone(hip, knee, ankle, (0.0, 0.9, 0.0), FORWARD, (-1.0, 0.0, 0.0))
        new_knee = fl.add(hip, fl.rotate(hip_turn, fl.sub(knee, hip)))
        new_ankle = fl.add(new_knee, fl.rotate(fl.qmul(hip_turn, knee_turn), fl.sub(ankle, knee)))
        reach = fl.norm(fl.sub(knee, hip)) + fl.norm(fl.sub(ankle, knee))
        self.assertAlmostEqual(fl.norm(fl.sub(new_ankle, hip)), reach, places=6)

    def test_a_nearly_straight_leg_bends_towards_the_toes(self):
        # Idle-like leg: 1 cm sideways kink, so the leg plane itself would bend the knee sideways.
        hip, knee, ankle = (0.0, 0.0, 1.0), (0.01, 0.0, 0.5), (0.0, 0.0, 0.0)
        target = (0.0, 0.1, 0.12)
        knee_turn, hip_turn = fl.two_bone(hip, knee, ankle, target, FORWARD, (-1.0, 0.0, 0.0))
        new_knee = fl.add(hip, fl.rotate(hip_turn, fl.sub(knee, hip)))
        new_ankle = fl.add(new_knee, fl.rotate(fl.qmul(hip_turn, knee_turn), fl.sub(ankle, knee)))
        self.assertLess(fl.norm(fl.sub(new_ankle, target)), 1e-9)
        line = fl.sub(target, hip)
        foot_of = fl.add(hip, fl.scale(line, fl.dot(fl.sub(new_knee, hip), line) / fl.dot(line, line)))
        offset = fl.sub(new_knee, foot_of)  # where the knee sits off the hip-ankle line
        self.assertLess(offset[1], -0.05)  # forward (-Y), not sideways
        self.assertLess(abs(offset[0]), 0.5 * abs(offset[1]))

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_twin_matches_python(self):
        scenarios = [IDLE_WALK, WALK_IDLE, WALK_RUN_REPEAT, GETUP_IDLE]
        times = [0.45, 0.5, 0.55, 0.62, 0.7, 0.75, 0.9, 0.95, 1.1]
        script = ("import * as fl from %s;"
                  "const i = JSON.parse(await new Promise(r => {let s=''; process.stdin.on('data', d => s += d).on('end', () => r(s));}));"
                  "const fk = (side, t) => [side === 'L' ? -0.1 : 0.1, -1.1 * t + 0.6, 0.02 * Math.sin(7 * t)];"
                  "const out = i.scenarios.map((s) => { const locks = fl.schedule(s, i.clips);"
                  " return {locks, drift: i.times.map((t) => fl.drift(s, i.clips, 0.3, t)),"
                  " targets: i.times.map((t) => fl.SIDES.map((side) => fl.soleTarget(s, i.clips, locks[side], side, t, fk, [0, -1, 0], [0, 0, 1])))}; });"
                  "const legs = i.legs.map(([h, k, a, t]) => fl.twoBone(h, k, a, t, [0, -1, 0], [-1, 0, 0]));"
                  "console.log(JSON.stringify({out, legs}));") % json.dumps(JS_MODULE.as_uri())
        legs = [[(0.0, 0.0, 1.0), (0.0, -0.05, 0.52), (0.0, 0.0, 0.05), (0.02, 0.12, 0.08)],
                [(0.1, 0.02, 0.95), (0.12, -0.08, 0.5), (0.1, 0.03, 0.06), (0.1, -0.2, 0.06)]]
        done = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True, timeout=60,
                              input=json.dumps({'scenarios': scenarios, 'clips': CLIPS, 'times': times, 'legs': legs}))
        self.assertEqual(done.returncode, 0, done.stderr)
        js = json.loads(done.stdout)

        def fk(side, t):
            return (-0.1 if side == 'L' else 0.1, -1.1 * t + 0.6, 0.02 * math.sin(7 * t))

        for s, row in zip(scenarios, js['out']):
            locks = fl.schedule(s, CLIPS)
            self.assertEqual(json.loads(json.dumps(locks)), row['locks'])
            for t, value in zip(times, row['drift']):
                self.assertAlmostEqual(fl.drift(s, CLIPS, 0.3, t), value, places=12)
            for t, sides in zip(times, row['targets']):
                for side, value in zip(fl.SIDES, sides):
                    expected = fl.sole_target(s, CLIPS, locks[side], side, t, fk, (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
                    if expected is None:
                        self.assertIsNone(value)
                    else:
                        self.assertLess(max(abs(a - b) for a, b in zip(expected, value)), 1e-12)
        for (h, k, a, t), value in zip(legs, js['legs']):
            for q, js_q in zip(fl.two_bone(h, k, a, t, FORWARD, (-1.0, 0.0, 0.0)), value):
                self.assertLess(max(abs(x - y) for x, y in zip(q, js_q)), 1e-12)


if __name__ == '__main__':
    unittest.main()
