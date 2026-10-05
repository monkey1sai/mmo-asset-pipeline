import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from supported_weight_solver import solve_supported


class SupportedWeightsTest(unittest.TestCase):
    def test_neighbor_distal_bone_cannot_contaminate_other_digit(self):
        initial=[[1,0,0,0],[1,0,0,0],[0,0,0,1]]
        targets=[[1,0,0,0],[0,1,0,0],[0,0,0,1]]
        graph={0:[(1,1)],1:[(0,1),(2,1)],2:[(1,1)]}
        result,stats=solve_supported(initial,targets,graph,{1},{1:{0,1}}, {},iterations=100)
        self.assertEqual(result[1][2:], [0,0])
        self.assertGreater(result[1][1],0)
        self.assertGreater(stats['maximum_illegal_neighbor_mass_projected'],0)
        self.assertEqual(result[0],initial[0]);self.assertEqual(result[2],initial[2])

    def test_shared_palm_support_is_simultaneous_and_normalized(self):
        initial=[[1,0,0],[0,1,0],[0,0,1]]
        graph={0:[(1,1),(2,1)],1:[(0,1)],2:[(0,1)]}
        result,_=solve_supported(initial,initial,graph,{0},{0:{0,1,2}}, {},iterations=100)
        self.assertGreater(result[0][1],0);self.assertAlmostEqual(result[0][1],result[0][2])
        self.assertAlmostEqual(sum(result[0]),1)

    def test_rigid_cap_is_immutable(self):
        initial=[[1,0],[1,0]];targets=initial
        graph={0:[(1,1)],1:[(0,1)]}
        result,_=solve_supported(initial,targets,graph,{0,1},{0:{0,1},1:{0,1}}, {1:[0,1]},iterations=100)
        self.assertEqual(result[1],[0,1])
