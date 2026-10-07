import json, math, shutil, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cv1_transition as tr

JS_MODULE = ROOT / 'tools' / 'runtime-qa' / 'three' / 'src' / 'cv1-transition.js'

CLIPS = {'Idle': {'frames': 120, 'loop': True, 'fps': 60}, 'Walk': {'frames': 60, 'loop': True, 'fps': 60},
         'Cast': {'frames': 90, 'loop': False, 'fps': 60}}


def cut(layer, clip, entry=0, speed=1.0):
    return {'t': 0.0, 'layer': layer, 'clip': clip, 'entry_frame': entry, 'speed': speed}


def total(w):
    return {g: round(sum(v.values()), 12) for g, v in w.items()}


class TransitionTests(unittest.TestCase):
    def test_upper_body_is_spine_01_and_everything_below_it(self):
        parents = {'pelvis': 'root', 'spine_01': 'pelvis', 'spine_02': 'spine_01', 'hand.R': 'spine_02', 'upper_leg.L': 'pelvis', 'root': None}
        self.assertEqual([tr.bone_group(b, parents) for b in ('root', 'pelvis', 'spine_01', 'hand.R', 'upper_leg.L')],
                         ['lower', 'lower', 'upper', 'upper', 'lower'])
        with self.assertRaises(tr.TransitionError):
            tr.bone_group('a', {'a': 'b', 'b': 'a'})

    def test_crossfade_is_linear_and_sums_to_one(self):
        s = tr.validate({'events': [cut('idle', 'Idle'), {'t': 1.0, 'layer': 'walk', 'clip': 'Walk', 'entry_frame': 0, 'speed': 1.0, 'blend_s': 0.2}]}, CLIPS)
        self.assertEqual(tr.weights(s, 0.99)['upper'], {'idle': 1.0})
        mid = tr.weights(s, 1.1)
        self.assertAlmostEqual(mid['upper']['idle'], 0.5)
        self.assertAlmostEqual(mid['lower']['walk'], 0.5)
        self.assertEqual(tr.weights(s, 1.3)['lower'], {'idle': 0.0, 'walk': 1.0})
        for t in (0.0, 1.03, 1.17, 2.0):
            self.assertEqual(total(tr.weights(s, t)), {'upper': 1.0, 'lower': 1.0})

    def test_an_interrupted_fade_continues_from_the_current_weights(self):
        s = tr.validate({'events': [cut('idle', 'Idle'), {'t': 1.0, 'layer': 'walk', 'clip': 'Walk', 'entry_frame': 0, 'speed': 1.0, 'blend_s': 0.4},
                                    {'t': 1.2, 'layer': 'idle', 'blend_s': 0.4}]}, CLIPS)
        before, at = tr.weights(s, 1.2 - 1e-9)['upper'], tr.weights(s, 1.2)['upper']
        self.assertAlmostEqual(before['walk'], at['walk'], places=6)
        self.assertAlmostEqual(at['idle'], 0.5)
        self.assertAlmostEqual(tr.weights(s, 1.4)['upper']['idle'], 0.75)
        self.assertEqual(tr.weights(s, 1.6)['upper'], {'walk': 0.0, 'idle': 1.0})

    def test_an_upper_body_layer_leaves_the_legs_alone(self):
        s = tr.validate({'events': [cut('walk', 'Walk'), {'t': 1.0, 'layer': 'cast', 'clip': 'Cast', 'entry_frame': 0, 'speed': 1.0, 'blend_s': 0.2, 'mask': 'upper'},
                                    {'t': 2.0, 'layer': 'walk', 'blend_s': 0.2, 'mask': 'upper'}]}, CLIPS)
        w = tr.weights(s, 1.1)
        self.assertAlmostEqual(w['upper']['cast'], 0.5)
        self.assertEqual(w['lower'], {'walk': 1.0})
        self.assertAlmostEqual(tr.weights(s, 2.1)['upper']['walk'], 0.5)
        self.assertEqual(tr.weights(s, 2.5)['upper'], {'cast': 0.0, 'walk': 1.0})
        with self.assertRaisesRegex(tr.TransitionError, 'FIRST_EVENT_IS_A_CUT'):
            tr.validate({'events': [dict(cut('walk', 'Walk'), mask='upper')]}, CLIPS)

    def test_layer_frames_wrap_loops_and_hold_the_end_of_others(self):
        s = tr.validate({'events': [cut('idle', 'Idle', entry=100, speed=0.5), {'t': 1.0, 'layer': 'cast', 'clip': 'Cast', 'entry_frame': 80, 'speed': 1.5, 'blend_s': 0.1}]}, CLIPS)
        self.assertAlmostEqual(tr.layer_frame(s, CLIPS, 'idle', 1.0), 10.0)  # 100 + 30, wrapped at 120
        self.assertIsNone(tr.layer_frame(s, CLIPS, 'cast', 0.5))
        self.assertAlmostEqual(tr.layer_frame(s, CLIPS, 'cast', 1.05), 84.5)
        self.assertEqual(tr.layer_frame(s, CLIPS, 'cast', 3.0), 89.0)

    def test_states_follow_their_bone_group(self):
        w = {'upper': {'a': 0.25, 'b': 0.75}, 'lower': {'a': 1.0, 'b': 0.0}}
        states = tr.blend_states(w, {'a': {'grasp.R': 1.0, 'lying': 1.0}, 'b': {'grasp.R': 0.0, 'lying': 0.0}})
        self.assertEqual(states, {'grasp.R': 0.25, 'lying': 1.0})
        over = {'upper': {'a': 0.7499999999999998, 'b': 0.2500000000000003}, 'lower': {'a': 1.0}}  # weights summing to 1 + ulp
        self.assertEqual(tr.blend_states(over, {'a': {'grasp.R': 1.0}, 'b': {'grasp.R': 1.0}})['grasp.R'], 1.0)

    def test_slerp_matches_three_js_slerp_flat(self):
        half = math.sqrt(0.5)
        q90 = (0.0, 0.0, half, half)  # 90 deg about z, (x, y, z, w)
        mid = tr.slerp_flat((0.0, 0.0, 0.0, 1.0), q90, 0.5)
        self.assertAlmostEqual(mid[2], math.sin(math.radians(22.5)))
        self.assertAlmostEqual(mid[3], math.cos(math.radians(22.5)))
        flipped = tr.slerp_flat((0.0, 0.0, 0.0, 1.0), tuple(-c for c in q90), 0.5)  # shortest path
        self.assertAlmostEqual(abs(flipped[3]), math.cos(math.radians(22.5)))
        near = tr.slerp_flat((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.01, math.sqrt(1 - 1e-4)), 0.3)  # lerp + normalize branch
        self.assertAlmostEqual(sum(c * c for c in near), 1.0)
        self.assertEqual(tr.slerp_flat(q90, q90, 0.7), q90)

    def test_mixer_accumulates_like_property_mixer(self):
        q0, q1 = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5))
        self.assertEqual(tr.mix([(q1, 1.0)], q0, 'quaternion'), q1)
        self.assertEqual(tr.mix([(q0, 0.5), (q1, 0.5)], q0, 'quaternion'), tr.slerp_flat(q0, q1, 0.5))
        self.assertEqual(tr.mix([(q1, 0.4)], q0, 'quaternion'), tr.slerp_flat(q1, q0, 0.6))  # under 1: mixed with the original
        self.assertEqual(tr.mix([(q1, 0.0)], q0, 'quaternion'), q0)
        self.assertEqual(tr.mix([((0.0, 0.0, 1.0), 0.25), ((0.0, 0.0, 3.0), 0.75)], (0.0, 0.0, 0.0), 'vector'), (0.0, 0.0, 2.5))

    def test_the_120_fps_grid_holds_the_60_and_30_fps_samples(self):
        fine = set(round(t, 9) for t in tr.sample_times(0.5, 0.9, 120))
        for fps in (60, 30):
            self.assertTrue(set(round(t, 9) for t in tr.sample_times(0.5, 0.9, fps)) <= fine)
        self.assertEqual(tr.sample_times(0.5, 0.5 + 0.1, 30)[0], 0.5)
        self.assertEqual(len(tr.sample_times(0.5, 0.9, 120)), 49)

    def test_validation_names_the_problem(self):
        with self.assertRaisesRegex(tr.TransitionError, 'UNKNOWN_CLIP'):
            tr.validate({'events': [cut('x', 'Nope')]}, CLIPS)
        with self.assertRaisesRegex(tr.TransitionError, 'BLEND'):
            tr.validate({'events': [cut('idle', 'Idle'), {'t': 1.0, 'layer': 'walk', 'clip': 'Walk', 'entry_frame': 0, 'speed': 1.0}]}, CLIPS)
        with self.assertRaisesRegex(tr.TransitionError, 'EVENT_TIMES_NOT_ASCENDING'):
            tr.validate({'events': [cut('idle', 'Idle'), {'t': -1.0, 'layer': 'walk', 'clip': 'Walk', 'entry_frame': 0, 'speed': 1.0, 'blend_s': 0.1}]}, CLIPS)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_javascript_twin_matches_python(self):
        scenarios = [
            {'events': [cut('idle', 'Idle', entry=100, speed=1.5), {'t': 0.5, 'layer': 'walk', 'clip': 'Walk', 'entry_frame': 7, 'speed': 0.5, 'blend_s': 0.4},
                        {'t': 0.7, 'layer': 'idle', 'blend_s': 0.1}, {'t': 0.75, 'layer': 'cast', 'clip': 'Cast', 'entry_frame': 85, 'speed': 1.0, 'blend_s': 0.2}]},
            {'events': [cut('walk', 'Walk'), {'t': 1.0, 'layer': 'cast', 'clip': 'Cast', 'entry_frame': 0, 'speed': 1.0, 'blend_s': 0.2, 'mask': 'upper'},
                        {'t': 2.4, 'layer': 'walk', 'blend_s': 0.2, 'mask': 'upper'}]}]
        times = [0.0, 0.5, 0.6, 0.7, 0.72, 0.75, 0.8, 0.9, 1.05, 1.2, 2.45, 3.0]
        states = {'idle': {'grasp.R': 1.0, 'lying': 0.0}, 'walk': {'grasp.R': 1.0, 'lying': 0.25}, 'cast': {'grasp.R': 0.5, 'lying': 1.0}}
        script = ("import {weights, layerFrame, blendStates, sampleTimes, boneGroup} from %s;"
                  "const i = JSON.parse(await new Promise(r => {let s=''; process.stdin.on('data', d => s += d).on('end', () => r(s));}));"
                  "const out = i.scenarios.map((s) => i.times.map((t) => { const w = weights(s, t);"
                  " const frames = Object.fromEntries([...new Set(s.events.map((e) => e.layer))].map((l) => [l, layerFrame(s, i.clips, l, t)]));"
                  " return {w, frames, states: blendStates(w, i.states)}; }));"
                  "console.log(JSON.stringify({out, samples: sampleTimes(0.5, 0.9, 120), groups: ['spine_01', 'hand.R', 'pelvis'].map((b) => boneGroup(b, i.parents))}));"
                  ) % json.dumps(JS_MODULE.as_uri())
        parents = {'pelvis': None, 'spine_01': 'pelvis', 'hand.R': 'spine_01'}
        done = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True, timeout=60,
                              input=json.dumps({'scenarios': scenarios, 'times': times, 'clips': CLIPS, 'states': states, 'parents': parents}))
        self.assertEqual(done.returncode, 0, done.stderr)
        js = json.loads(done.stdout)
        for s, rows in zip(scenarios, js['out']):
            for t, row in zip(times, rows):
                w = tr.weights(s, t)
                for g in tr.GROUPS:
                    self.assertEqual(set(w[g]), set(row['w'][g]))
                    for layer in w[g]:
                        self.assertAlmostEqual(w[g][layer], row['w'][g][layer], places=12)
                for layer, frame in row['frames'].items():
                    expected = tr.layer_frame(s, CLIPS, layer, t)
                    self.assertTrue(frame is None if expected is None else abs(frame - expected) < 1e-9, (t, layer, frame, expected))
                for key, value in tr.blend_states(w, states).items():
                    self.assertAlmostEqual(value, row['states'][key], places=12)
        self.assertEqual([round(t, 12) for t in js['samples']], [round(t, 12) for t in tr.sample_times(0.5, 0.9, 120)])
        self.assertEqual(js['groups'], [tr.bone_group(b, parents) for b in ('spine_01', 'hand.R', 'pelvis')])


if __name__ == '__main__':
    unittest.main()
