import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cv1_gait as gait_math

WALK = {'nominal_speed_m_s': 1.4, 'stance': 25 / 60, 'phase_offsets': {'R': 0.0, 'L': 0.5}, 'swing_height_m': 0.07, 'tangent_scale': 0.5,
        'toe_off_pitch_deg': 25, 'landing_pitch_deg': -10,
        'pelvis': {'bob_m': 0.012, 'sway_m': 0.02, 'yaw_deg': 4, 'roll_deg': 2, 'margin_m': 0.003, 'max_drop_m': 0.1}}


class GaitTests(unittest.TestCase):
    def test_stance_foot_moves_back_at_the_nominal_speed_and_stays_flat(self):
        cycle = 1.0
        a, b = gait_math.foot_state(0.1, WALK, cycle), gait_math.foot_state(0.3, WALK, cycle)
        self.assertTrue(a['stance'] and b['stance'])
        self.assertAlmostEqual((a['forward'] - b['forward']) / (0.2 * cycle), 1.4, places=9)
        self.assertEqual((a['lift'], a['pitch']), (0.0, 0.0))

    def test_swing_is_continuous_with_stance_and_returns_to_the_front(self):
        stance = WALK['stance']
        end_stance, start_swing = gait_math.foot_state(stance - 1e-9, WALK, 1.0), gait_math.foot_state(stance + 1e-9, WALK, 1.0)
        self.assertAlmostEqual(end_stance['forward'], start_swing['forward'], places=6)
        self.assertAlmostEqual(start_swing['lift'], 0.0, places=9)
        landing, next_stance = gait_math.foot_state(1 - 1e-9, WALK, 1.0), gait_math.foot_state(0.0, WALK, 1.0)
        self.assertAlmostEqual(landing['forward'], next_stance['forward'], places=6)
        self.assertAlmostEqual(landing['pitch'], 0.0, places=6)
        mid = gait_math.foot_state(stance + (1 - stance) / 2, WALK, 1.0)
        self.assertAlmostEqual(mid['lift'], 0.07, places=9)

    def test_stance_windows_cover_the_flat_frames(self):
        self.assertEqual(gait_math.stance_window(WALK, 'R', 60), [0, 24])
        self.assertEqual(gait_math.stance_window(WALK, 'L', 60), [30, 54])

    def test_pelvis_centre_drops_only_as_far_as_reach_needs(self):
        limit = lambda frame: -0.05 if frame == 10 else 0.0
        heights, centre = gait_math.pelvis_heights(60, WALK, limit)
        bob10 = gait_math.pelvis_motion(10 / 60, WALK)['bob']
        self.assertLessEqual(heights[10], -0.05 + 1e-12)
        self.assertAlmostEqual(centre, -0.05 - 0.012 * bob10 - 0.003, places=12)
        self.assertAlmostEqual(heights[0], heights[60], places=12)
        with self.assertRaisesRegex(ValueError, 'PELVIS_DROP_TOO_LARGE'):
            gait_math.pelvis_heights(60, WALK, lambda f: -0.2)


if __name__ == '__main__':
    unittest.main()
