import copy
import json
import math
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from secondary_motion import ChainSolver, validate_profile
import identity

ROOT=Path(__file__).resolve().parents[1]


class SecondaryTests(unittest.TestCase):
    def setUp(self):
        self.p=identity.read_json(ROOT/'configs/secondary_presets.json')
        self.anchors={'body':np.eye(4)}

    def test_four_presets_reuse_and_rest_lengths(self):
        for c in self.p['chains']:
            p=copy.deepcopy(self.p);p['chains']=[c]
            s=ChainSolver(p);s.advance(0,self.anchors)
            for f in range(240):
                m=np.eye(4);m[0,3]=.15*math.sin(f/24)
                result=s.advance(1/60,{'body':m})
                self.assertEqual(result['constraints_status'],'PASS')
                self.assertTrue(np.isfinite(result['chains'][0]['points']).all())

    def test_writer_conflicts(self):
        for change in ('body','duplicate','anchor'):
            p=copy.deepcopy(self.p)
            if change=='body':p['body_bones'].append('cape_a')
            elif change=='duplicate':p['chains'][1]['bones']=['cape_a']
            else:p['chains'][0]['bones'][0]='body'
            with self.assertRaisesRegex(ValueError,'BONE_WRITER_CONFLICT'):validate_profile(p)

    def test_fixed_step_partition(self):
        a=ChainSolver(self.p);b=ChainSolver(self.p)
        a.advance(0,self.anchors);b.advance(0,self.anchors)
        for _ in range(60):ra=a.advance(1/60,self.anchors)
        for _ in range(120):rb=b.advance(1/120,self.anchors)
        for x,y in zip(ra['chains'],rb['chains']):np.testing.assert_allclose(x['points'],y['points'],atol=1e-12)

    def test_substep_moving_anchor_output_is_attached(self):
        p=copy.deepcopy(self.p);p['chains']=p['chains'][:1]
        s=ChainSolver(p);s.advance(0,self.anchors)
        for i,dt in enumerate([1/240,1/480,1/240,1/60,1/300,1/120]):
            angle=.12*i;m=np.eye(4)
            m[:2,:2]=[[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]]
            m[:3,3]=[.1*(i+1),.02*i,0]
            r=s.advance(dt,{'body':m})
            np.testing.assert_allclose(r['chains'][0]['points'][0],m[:3,3],atol=1e-12)
            self.assertLess(r['max_anchor_error_m'],1e-12)
            self.assertEqual(r['constraints_status'],'PASS')

    def test_substep_output_does_not_integrate_state(self):
        s=ChainSolver(self.p);s.advance(0,self.anchors)
        before={k:[a.copy() for a in v] for k,v in s.states.items()}
        m=np.eye(4);m[0,3]=.1
        r=s.advance(1/240,{'body':m});self.assertEqual(r['steps'],0)
        for k in before:
            for a,b in zip(before[k],s.states[k]):np.testing.assert_array_equal(a,b)

    def test_cross_chain_anchor_dependency_rejected(self):
        p=copy.deepcopy(self.p);p['chains'][1]['anchor_bone']='cape_b'
        with self.assertRaisesRegex(ValueError,'CHAIN_ANCHOR_DEPENDENCY'):ChainSolver(p)

    def test_pause_teleport_respawn_and_large_dt(self):
        s=ChainSolver(self.p);r=s.advance(0,self.anchors)
        self.assertEqual(s.advance(.1,self.anchors,paused=True)['reason'],'paused')
        m=np.eye(4);m[0,3]=3
        r=s.advance(1/60,{'body':m});self.assertEqual(r['reason'],'reset')
        self.assertEqual(r['chains'][0]['points'][0],[3.,0.,0.])
        self.assertEqual(s.advance(.2,{'body':m})['reason'],'reset')
        self.assertEqual(s.advance(0,{'body':m},reset=True)['reason'],'reset')

    def test_invalid_numerics_scale_and_shape(self):
        for value in (float('nan'),-1,True):
            with self.assertRaises(ValueError):ChainSolver(self.p).advance(value,self.anchors)
        m=np.eye(4);m[0,0]=2
        with self.assertRaisesRegex(ValueError,'SCALE'):ChainSolver(self.p).advance(0,{'body':m})
        p=copy.deepcopy(self.p);p['chains'][0]['rest_vectors'][0]=[0,0,0]
        with self.assertRaises(ValueError):ChainSolver(p)

    def test_impossible_collision_reports_fail(self):
        p=copy.deepcopy(self.p);p['chains']=p['chains'][:1]
        p['chains'][0]['colliders']=[{'kind':'sphere','a':[0,0,0],'radius':2}]
        s=ChainSolver(p);s.advance(0,self.anchors)
        self.assertEqual(s.advance(1/60,self.anchors)['constraints_status'],'FAIL')

    def test_capsule_proxy(self):
        from secondary_motion import collider_center
        np.testing.assert_allclose(collider_center(np.array([1.,0,1]),{'kind':'capsule','a':[0,0,0],'b':[0,0,2]}),[0,0,1])

    def test_feasible_collision_deflects_tip(self):
        p=copy.deepcopy(self.p);p['chains']=p['chains'][:1];p['chains'][0]['bones']=['cape_a'];p['chains'][0]['rest_vectors']=[[0,0,-.3]]
        p['chains'][0]['colliders']=[{'kind':'sphere','a':[.05,0,-.3],'radius':.08}]
        s=ChainSolver(p);s.advance(0,self.anchors)
        for _ in range(60):r=s.advance(1/60,self.anchors)
        self.assertEqual(r['constraints_status'],'PASS');self.assertLess(r['chains'][0]['points'][1][0],-.02)

    def test_rigid_plate_segments_remain_collinear(self):
        p=copy.deepcopy(self.p);p['chains']=p['chains'][1:2]
        p['chains'][0]['bones'].append('plate_b');p['chains'][0]['rest_vectors'].append([.15,0,-.25])
        s=ChainSolver(p);s.advance(0,self.anchors)
        for _ in range(30):r=s.advance(1/60,self.anchors)
        pts=np.asarray(r['chains'][0]['points']);np.testing.assert_allclose(np.cross(pts[1]-pts[0],pts[2]-pts[1]),0,atol=1e-12)


class WorkflowTests(unittest.TestCase):
    def test_real_presets_request_binding_and_negative_time(self):
        import motion_workflow
        request=identity.read_json(ROOT/'requests/secondary-fixture-v001.json');profile=identity.read_json(ROOT/'configs/secondary_presets.json')
        trajectory={'samples':[{'time_seconds':0,'anchors':{'body':np.eye(4).tolist()}},{'time_seconds':1/60,'anchors':{'body':np.eye(4).tolist()}}]}
        r=motion_workflow.simulate(request,profile,trajectory)
        self.assertEqual(r['request_sha256'],identity.json_digest(request));self.assertEqual(r['solver_constraints'],'PASS')
        trajectory['samples'][1]['time_seconds']=-1
        with self.assertRaisesRegex(ValueError,'TIME_SEQUENCE'):motion_workflow.simulate(request,profile,trajectory)

    def test_cli_new_version_and_path_boundary(self):
        import motion_workflow
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'requests').mkdir();(root/'configs').mkdir()
            r=identity.read_json(ROOT/'requests/secondary-fixture-v001.json');p=identity.read_json(ROOT/'configs/secondary_presets.json')
            for name,value in [('requests/r.json',r),('configs/p.json',p),('configs/t.json',{'samples':[{'time_seconds':0,'anchors':{'body':np.eye(4).tolist()}}]})]:
                (root/name).write_text(json.dumps(value),encoding='utf-8')
            args=['--request','requests/r.json','--profile','configs/p.json','--trajectory','configs/t.json','--out','runs/qa/demo/result.json']
            with patch.object(motion_workflow,'ROOT',root):
                self.assertEqual(motion_workflow.main(args),0)
                with self.assertRaises(FileExistsError):motion_workflow.main(args)
                with self.assertRaises(identity.IdentityError):motion_workflow.main(args[:-1]+['../escape.json'])


if __name__=='__main__':unittest.main()
