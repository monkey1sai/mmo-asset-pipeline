import unittest,sys
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ro_solid_angle import certify_oriented_closed,classify_winding


class SolidAngleTests(unittest.TestCase):
    points=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
    triangles=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
    def test_closed_solid_inside_outside_and_reversed_orientation(self):
        certify_oriented_closed(self.points,self.triangles)
        self.assertIs(classify_winding(self.points,self.triangles,(.1,.1,.1),.1)[0],True)
        self.assertIs(classify_winding(self.points,self.triangles,(2,2,2),1)[0],False)
        reversed_tri=[tuple(reversed(t)) for t in self.triangles]
        self.assertIs(classify_winding(self.points,reversed_tri,(.1,.1,.1),.1)[0],True)
    def test_open_or_inconsistent_surface_not_certified(self):
        for triangles in [self.triangles[:-1],[tuple(reversed(self.triangles[0]))]+self.triangles[1:]]:
            with self.assertRaisesRegex(ValueError,'CLOSED_ORIENTED_SOLID_REQUIRED'):certify_oriented_closed(self.points,triangles)
    def test_surface_near_or_noninteger_winding_stays_unknown(self):
        self.assertIsNone(classify_winding(self.points,self.triangles,(0,0,0),0)[0])
        self.assertIsNone(classify_winding(self.points,self.triangles[:-1],(.1,.1,.1),.1)[0])
    def test_degenerate_nonfinite_and_small_crack_rejected(self):
        with self.assertRaisesRegex(ValueError,'DEGENERATE'):
            certify_oriented_closed(self.points,[(0,0,1)]+self.triangles)
        invalid=list(self.points);invalid[0]=(float('nan'),0,0)
        with self.assertRaisesRegex(ValueError,'NONFINITE'):certify_oriented_closed(invalid,self.triangles)
        cracked=self.points+[(1e-9,0,0)];tri=[(4,2,1)]+self.triangles[1:]
        with self.assertRaisesRegex(ValueError,'CLOSED_ORIENTED'):certify_oriented_closed(cracked,tri)
    def test_transformation_and_mirror_preserve_classification(self):
        rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],dtype=float)
        for transform in [rotation,np.diag([-1,1,1])]:
            points=np.asarray(self.points)@transform.T+np.array([.3,-.2,.1])
            target=transform@np.array([.1,.1,.1])+np.array([.3,-.2,.1])
            certify_oriented_closed(points,self.triangles)
            self.assertIs(classify_winding(points,self.triangles,target,.1)[0],True)
    def test_opposed_components_rejected(self):
        points=self.points+[(x+2,y,z) for x,y,z in self.points]
        triangles=self.triangles+[tuple(i+4 for i in reversed(t)) for t in self.triangles]
        with self.assertRaisesRegex(ValueError,'CONFLICTING_COMPONENT'):certify_oriented_closed(points,triangles)
