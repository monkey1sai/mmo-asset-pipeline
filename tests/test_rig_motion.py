"""Existing retarget regressions split out for the shared rig tool checkpoint."""
import unittest
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_motion import retarget


class RetargetTests(unittest.TestCase):
    def test_parent_rotation_moves_child_pivot_without_changing_length(self):
        base=np.eye(4);child=np.eye(4);child[1,3]=1
        posed=np.eye(4);posed[:2,:2]=[[0,-1],[1,0]]
        result=retarget({'s':base},{'s':posed},{'root':base,'child':child},{'s':'root'},target_parents={'root':None,'child':'root'})
        np.testing.assert_allclose(result['child'][:3,3],[-1,0,0])
        np.testing.assert_allclose(result['child'][:3,:3],posed[:3,:3])

    def test_parent_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError,'PARENT_CYCLE'):
            retarget({'s':np.eye(4)},{'s':np.eye(4)},{'t':np.eye(4)},{'s':'t'},target_parents={'t':'t'})

    def test_rest_identity_and_unmapped_bones_preserved(self):
        s=np.eye(4);t=np.eye(4);t[:3,3]=[1,2,3]
        out=retarget({'s':s},{'s':s},{'t':t,'secondary':s},{'s':'t'})
        np.testing.assert_equal(out['t'],t);np.testing.assert_equal(out['secondary'],s)

    def test_nonidentity_rest_axis_and_in_place(self):
        rest=np.eye(4);rest[:2,:2]=[[0,-1],[1,0]]
        pose=np.eye(4);pose[:3,3]=[3,4,5]
        out=retarget({'s':rest},{'s':pose},{'t':np.eye(4)},{'s':'t'})['t']
        np.testing.assert_allclose(out[:3,:3],rest[:3,:3].T)
        np.testing.assert_equal(out[:3,3],[0,0,0])

    def test_root_motion_scale(self):
        pose=np.eye(4);pose[0,3]=100
        out=retarget({'s':np.eye(4)},{'s':pose},{'t':np.eye(4)},{'s':'t'},root_policy='root_motion',root_target='t',translation_scale=.01)
        self.assertEqual(out['t'][0,3],1)

    def test_reject_scale_collision_and_missing_root(self):
        m=np.eye(4);m[0,0]=2
        with self.assertRaises(ValueError):retarget({'s':np.eye(4)},{'s':m},{'t':np.eye(4)},{'s':'t'})
        with self.assertRaises(ValueError):retarget({}, {}, {}, {'a':'t','b':'t'})
        with self.assertRaises(ValueError):retarget({}, {}, {}, {'s':'t'},root_policy='root_motion')
