import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from weight_vector_solver import solve_vectors

class WeightVectorTests(unittest.TestCase):
    def test_full_vector_jump_blends_across_middle_bone(self):
        neighbors = {0:[(1,1)],1:[(0,1),(2,1)],2:[(1,1),(3,1)],3:[(2,1)]}
        values, report = solve_vectors([[1,0,0,0],[1,0,0,0],[0,0,1,0],[0,0,1,0]],
            [[1,0,0,0]]*4, neighbors, {1,2}, {}, fidelity=0, iterations=100)
        self.assertAlmostEqual(values[1][2],1/3,places=7)
        self.assertAlmostEqual(values[2][0],1/3,places=7)
        self.assertEqual(values[0],[1,0,0,0])
        self.assertEqual(values[3],[0,0,1,0])
        self.assertLess(report['maximum_normalization_error'],1e-12)

    def test_cap_is_rigid_and_every_component_needs_anchor(self):
        neighbors={0:[(1,1)],1:[(0,1),(2,1)],2:[(1,1)]}
        initial=[[1,0,0,0]]*3
        values,_=solve_vectors(initial,initial,neighbors,{1,2},{2:[0,0,0,1]})
        self.assertEqual(values[2],[0,0,0,1])
        self.assertGreater(values[1][3],0)
        with self.assertRaisesRegex(AssertionError,'Unanchored'):
            solve_vectors(initial,initial,neighbors,{0,1,2},{})

    def test_invalid_negative_or_unnormalized_vector_rejected(self):
        for row in [[1.1,-.1,0,0],[.5,0,0,0],[float('nan'),0,0,0]]:
            with self.assertRaises(AssertionError):
                solve_vectors([row,row],[row,row],{0:[(1,1)],1:[(0,1)]},{1},{})
