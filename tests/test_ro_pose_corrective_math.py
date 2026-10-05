import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ro_pose_corrective_math import inverse_delta, surface_limited_magnitude


class CorrectiveMathTests(unittest.TestCase):
    def test_inverse_skin_avoids_double_rotation(self):
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],dtype=float)
        skin=.7*rotation+.3*np.eye(3)
        desired=np.array([.001,.002,-.0005])
        rest,condition=inverse_delta(skin,desired)
        np.testing.assert_allclose(skin@rest,desired,atol=1e-12)
        self.assertGreater(np.linalg.norm(skin@desired-desired),.001)

    def test_singular_blend_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNSTABLE_INVERSE_SKIN'):
            inverse_delta(np.diag([1,0,1]),[.001,0,0])

    def test_near_contact_is_not_forced_through_surface(self):
        self.assertEqual(surface_limited_magnitude(.003,.00005,.9),0.)
        self.assertAlmostEqual(surface_limited_magnitude(.003,.0018,.5),.002)
        self.assertEqual(surface_limited_magnitude(.003,.005,-.4),0.)
