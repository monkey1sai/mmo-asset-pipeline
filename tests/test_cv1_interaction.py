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
    if clip in interaction.BED_CLIPS:
        data['bed'] = {'centre_m': [0.0, 0.6], 'top_z_m': 0.45, 'size_m': [2.0, 0.9], 'yaw_deg': 0}
        initial, switches = interaction.SOCKET_PLAN[clip]
        data['sword_socket'] = {'initial': initial, 'switches': [{'event': e, 'to': to} for e, to in switches],
                                'bed_socket': {'head_m': [-0.4, 0.1, 0.8], 'quaternion_wxyz': [1.0, 0.0, 0.0, 0.0]}}
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

    def test_percent_limits_use_exact_frame_numbers(self):
        lie = dict(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 30]], events=[{'name': 'put_sword_down', 'frame': 30}], stance={'L': [], 'R': []})
        interaction.validate(config(bed=[[63, 89]], **lie))  # 70% of 90 frames is frame 63 (0.7 * 90 = 62.999... in floating point)
        with self.assertRaisesRegex(interaction.InteractionError, 'LIEDOWN_BED'):
            interaction.validate(config(bed=[[64, 89]], **lie))
        self.assertEqual(interaction.share(0.70, 90), 63)

    def test_bed_clips_need_the_request_bed_proxy(self):
        sleep = config(clip='AN_RO_Sleep_Loop', frames=180, grasp=[], stance={'L': [], 'R': []}, bed=[[0, 179]])
        interaction.validate(sleep)
        for change in ({'top_z_m': 0.40}, {'size_m': [2.0, 1.2]}, {'centre_m': [0.0]}):
            broken = dict(sleep, bed=dict(sleep['bed'], **change))
            with self.assertRaisesRegex(interaction.InteractionError, 'BED_PROXY'):
                interaction.validate(broken)
        with self.assertRaisesRegex(interaction.InteractionError, 'BED_PROXY'):
            interaction.validate({k: v for k, v in sleep.items() if k != 'bed'})

    def test_sword_switches_socket_at_the_event_frame(self):
        lie = config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 30]], events=[{'name': 'put_sword_down', 'frame': 30}],
                     stance={'L': [], 'R': []}, bed=[[60, 89]])
        interaction.validate(lie)
        self.assertEqual([interaction.socket_at(lie, t) for t in (0, 29.75, 30, 89)], ['hand', 'hand', 'bed', 'bed'])
        get_up = config(clip='AN_RO_GetUp', frames=90, loop=False, grasp=[[60, 89]], stance={'L': [], 'R': []},
                        events=[{'name': 'pick_sword_up', 'frame': 60}, {'name': 'leave_bed', 'frame': 40}], bed=[[0, 40]])
        interaction.validate(get_up)
        self.assertEqual([interaction.socket_at(get_up, t) for t in (0, 59.5, 60, 89)], ['bed', 'bed', 'hand', 'hand'])
        self.assertEqual(interaction.socket_at(config(), 50), 'hand')
        wrong = dict(lie, sword_socket=dict(lie['sword_socket'], initial='bed'))
        with self.assertRaisesRegex(interaction.InteractionError, 'SWORD_SOCKET_PLAN'):
            interaction.validate(wrong)
        skewed = dict(lie, sword_socket=dict(lie['sword_socket'], bed_socket={'head_m': [0, 0, 0], 'quaternion_wxyz': [1.0, 1.0, 0.0, 0.0]}))
        with self.assertRaisesRegex(interaction.InteractionError, 'BED_SOCKET_TRANSFORM'):
            interaction.validate(skewed)
        # Generic schema: any clip (e.g. a holdout) may declare a bed and sockets without a tool change.
        holdout = dict(config(clip='AN_RO_Holdout_01', frames=60, loop=False, events=[{'name': 'set_down', 'frame': 40}]),
                       bed=lie['bed'], sword_socket={'initial': 'hand', 'switches': [{'event': 'set_down', 'to': 'bed'}], 'bed_socket': lie['sword_socket']['bed_socket']})
        interaction.validate(holdout)
        self.assertEqual(interaction.socket_at(holdout, 45), 'bed')
        with self.assertRaisesRegex(interaction.InteractionError, 'SOCKET_SWITCH_INVALID'):
            interaction.validate(dict(holdout, sword_socket=dict(holdout['sword_socket'], switches=[{'event': 'set_down', 'to': 'hand'}])))
        with self.assertRaisesRegex(interaction.InteractionError, 'BED_SOCKET_NEEDS_BED_PROXY'):
            interaction.validate({k: v for k, v in holdout.items() if k != 'bed'})
        with self.assertRaisesRegex(interaction.InteractionError, 'SOCKET_EVENT_MISSING'):
            interaction.validate(dict(holdout, events=[]))

    def test_socket_event_window_marks_the_frames_around_each_switch(self):
        lie = config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 30]], events=[{'name': 'put_sword_down', 'frame': 30}],
                     stance={'L': [], 'R': []}, bed=[[63, 89]])
        interaction.validate(lie)
        self.assertEqual([interaction.near_socket_event(lie, t, 6) for t in (23.75, 24, 30, 36, 36.25)], [False, True, True, True, False])
        sleep = config(clip='AN_RO_Sleep_Loop', frames=180, grasp=[], stance={'L': [], 'R': []}, bed=[[0, 179]])
        interaction.validate(sleep)
        self.assertFalse(interaction.near_socket_event(sleep, 0, 6))  # a socket without switches has no event
        self.assertFalse(interaction.near_socket_event(config(), 10, 6))  # no sword socket at all

    def test_seated_on_bed_windows_need_the_bed_and_stay_off_the_support_window(self):
        lie = config(clip='AN_RO_LieDown', frames=90, loop=False, grasp=[[0, 30]], events=[{'name': 'put_sword_down', 'frame': 30}],
                     stance={'L': [], 'R': []}, bed=[[63, 89]])
        lie['seated_on_bed'] = {'windows': [[2, 56]]}
        interaction.validate(lie)
        self.assertEqual([interaction.seated_on_bed(lie, t) for t in (1.75, 2, 56, 56.25)], [False, True, True, False])
        for windows in ([[2, 70]], [[2, 64]], [[64, 70]]):
            with self.assertRaisesRegex(interaction.InteractionError, 'SEATED_ON_BED_OVERLAPS_BED_SUPPORT'):
                interaction.validate(dict(lie, seated_on_bed={'windows': windows}))
        # A seated window may end on the frame the bed support starts (and start on the frame it ends): the exemption
        # lasts until the support is established (authorization entry 20), and the support takes over on that frame.
        touching = dict(lie, seated_on_bed={'windows': [[2, 63]]})
        interaction.validate(touching)
        self.assertEqual([interaction.seated_on_bed(touching, t) for t in (62.25, 62.75, 63, 63.25)], [True, True, False, False])
        rising = config(clip='AN_RO_Holdout_01', frames=60, loop=False, grasp=[], stance={'L': [], 'R': []}, bed=[[0, 26]])
        rising['bed'] = {'centre_m': [0.0, 0.6], 'top_z_m': 0.45, 'size_m': [2.0, 0.9], 'yaw_deg': 0}
        rising['seated_on_bed'] = {'windows': [[26, 50]]}
        interaction.validate(rising)
        self.assertEqual([interaction.seated_on_bed(rising, t) for t in (25.75, 26, 26.25, 50, 50.25)], [False, False, True, True, False])
        with self.assertRaisesRegex(interaction.InteractionError, 'SEATED_ON_BED_NEEDS_BED_PROXY'):
            interaction.validate(dict(config(clip='AN_RO_Holdout_01', frames=60, loop=False), seated_on_bed={'windows': [[0, 10]]}))
        self.assertFalse(interaction.seated_on_bed(config(), 5))

    def test_cast_needs_exactly_one_release_event_inside_the_clip(self):
        def cast(events):
            return config(clip='AN_RO_Cast_OpenPalm', frames=90, loop=False, events=events)
        interaction.validate(cast([{'name': 'release', 'frame': 45}]))
        for events in ((), [{'name': 'release', 'frame': 30}, {'name': 'release', 'frame': 50}], [{'name': 'fire', 'frame': 45}]):
            with self.assertRaisesRegex(interaction.InteractionError, 'CAST_ONE_RELEASE_EVENT'):
                interaction.validate(cast(events))
        with self.assertRaisesRegex(interaction.InteractionError, 'EVENT_RANGE'):
            interaction.validate(cast([{'name': 'release', 'frame': 90}]))

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
