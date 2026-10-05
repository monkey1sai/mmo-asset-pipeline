import json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cv1_interaction as interaction


def config(clip='AN_RO_Idle_Sword', frames=120, loop=True, grasp=None, stance=None, events=(), bed=None):
    full = [[0, frames - 1]]
    data = {'schema_version': 1, 'clip': clip, 'fps': 60, 'frames': frames, 'loop': loop, 'ramp_frames': 12,
            'states': {'grasp.R': {'windows': full if grasp is None else grasp}, 'grasp.L': {'windows': []}},
            'stance': {'L': full, 'R': full} if stance is None else stance, 'events': [dict(e) for e in events], 'nominal_speed_m_s': 0.0}
    if bed is not None:
        data['bed_support'] = {'windows': bed}
    return data


class InteractionTests(unittest.TestCase):
    def test_state_ramps_outside_the_window_and_is_one_inside(self):
        c = config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 40]], events=[{'name': 'put_sword_down', 'frame': 40}],
                   stance={'L': [], 'R': []}, bed=[[60, 89]])
        interaction.validate(c)
        self.assertEqual(interaction.state_value(c, 'grasp.R', 0), 1.0)
        self.assertEqual(interaction.state_value(c, 'grasp.R', 40), 1.0)
        self.assertAlmostEqual(interaction.state_value(c, 'grasp.R', 46), 0.5)
        self.assertEqual(interaction.state_value(c, 'grasp.R', 52), 0.0)
        self.assertEqual(interaction.state_value(c, 'grasp.L', 10), 0.0)
        with self.assertRaises(interaction.InteractionError):
            interaction.state_value(c, 'grasp.X', 0)

    def test_window_over_a_whole_loop_has_no_seam_ramp(self):
        c = interaction.validate(config())
        self.assertEqual(interaction.state_value(c, 'grasp.R', 0), 1.0)
        self.assertEqual(interaction.state_value(c, 'grasp.R', 119.5), 1.0)

    def test_minimum_coverage_rejects_shortened_windows(self):
        with self.assertRaisesRegex(interaction.InteractionError, 'GRASP_R_MUST_COVER_CLIP'):
            interaction.validate(config(grasp=[[0, 100]]))
        with self.assertRaisesRegex(interaction.InteractionError, 'LIEDOWN_GRASP'):
            interaction.validate(config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 20]], events=[{'name': 'put_sword_down', 'frame': 20}],
                                        stance={'L': [], 'R': []}, bed=[[60, 89]]))
        with self.assertRaisesRegex(interaction.InteractionError, 'STANCE_L_BELOW_40PCT'):
            interaction.validate(config(clip='AN_RO_Walk_Sword', frames=60, stance={'L': [[0, 15]], 'R': [[30, 59]]}))
        walk = config(clip='AN_RO_Walk_Sword', frames=60, stance={'L': [[50, 20]], 'R': [[20, 50]]})
        self.assertAlmostEqual(interaction.coverage(walk['stance']['L'], 60, True), 31 / 60)
        interaction.validate(walk)
        with self.assertRaisesRegex(interaction.InteractionError, 'WRAP_IN_NON_LOOP'):
            interaction.validate(config(clip='AN_RO_GetUp', frames=90, loop=False, grasp=[[60, 89]], stance={'L': [[80, 10]], 'R': []},
                                        events=[{'name': 'pick_sword_up', 'frame': 60}, {'name': 'leave_bed', 'frame': 40}], bed=[[0, 40]]))

    def test_samples_whole_half_and_quarter_frames_near_boundaries(self):
        c = config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 40]], events=[{'name': 'put_sword_down', 'frame': 40}],
                   stance={'L': [], 'R': []}, bed=[[60, 89]])
        times = interaction.sample_times(c)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], 89)
        for t in (10, 10.5, 39.25, 39.75, 40.25, 60.75, 88.5):
            self.assertIn(t, times)
        self.assertNotIn(10.25, times)
        loop_times = interaction.sample_times(interaction.validate(config()))
        self.assertEqual(loop_times[-1], 119.5)

    def test_registry_needs_the_current_sha_and_a_reason_to_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, registry = root / 'idle.json', root / 'registry.json'
            path.write_text(json.dumps(config()), encoding='utf-8')
            with self.assertRaisesRegex(interaction.InteractionError, 'NOT_REGISTERED'):
                interaction.registered(registry, path)
            interaction.register(registry, path, root)
            interaction.registered(registry, path)
            changed = config()
            changed['nominal_speed_m_s'] = 0.1
            path.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(interaction.InteractionError, 'CONFIG_CHANGED'):
                interaction.registered(registry, path)
            with self.assertRaisesRegex(interaction.InteractionError, 'GIVE_FIX_REASON'):
                interaction.register(registry, path, root)
            entry = interaction.register(registry, path, root, reason='fix after failed measurement X')
            self.assertIsNotNone(entry['supersedes'])
            self.assertEqual(len(json.loads(registry.read_text(encoding='utf-8'))['entries']), 2)


if __name__ == '__main__':
    unittest.main()
