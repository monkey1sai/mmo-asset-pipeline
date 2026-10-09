"""Local bone-chain reference solver. GLB contains baked keys, never this solver.

Positions and colliders are world metres. Call AFTER body pose/world update;
apply returned rotations only to exclusively-owned secondary bones. This module
does not write a game runtime or infer anatomical masks.
"""
from __future__ import annotations
import math
import numpy as np


def vector(value):
    a = np.asarray(value, dtype=float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError('VECTOR_INVALID')
    return a


def unit(v):
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError('DIRECTION_ZERO')
    return v / n


def number(value, lo, hi):
    if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError('PARAMETER_INVALID')
    return value


def validate_profile(p):
    if p.get('schema_version') != 1 or p.get('coordinate_system') != 'world_meters':
        raise ValueError('PROFILE_SCHEMA')
    number(p['fixed_dt'], 1/240, 1/30)
    number(p['max_frame_dt'], p['fixed_dt'], 1)
    number(p['teleport_m'], .01, 100)
    if type(p['iterations']) is not int or not 2 <= p['iterations'] <= 64:
        raise ValueError('ITERATIONS_INVALID')
    vector(p['gravity']); vector(p['wind'])
    owned = set(); ids = set()
    body = set(p['body_bones'])
    if not p['chains']:
        raise ValueError('CHAINS_REQUIRED')
    for c in p['chains']:
        if c['id'] in ids or c['mode'] not in ('flexible', 'rigid_plate'):
            raise ValueError('CHAIN_ID_OR_MODE')
        ids.add(c['id'])
        if not c['bones'] or len(c['bones']) != len(c['rest_vectors']):
            raise ValueError('CHAIN_LAYOUT')
        for b in c['bones']:
            if b in owned or b in body or b == c['anchor_bone']:
                raise ValueError('BONE_WRITER_CONFLICT')
            owned.add(b)
        for v in c['rest_vectors']:
            number(float(np.linalg.norm(vector(v))), 1e-5, 20)
        number(c['stiffness'], 0, 2000)
        number(c['damping'], 0, 100)
        number(c['max_angle_deg'], 0, 89)
        for collider in c.get('colliders', []):
            if collider['kind'] not in ('sphere', 'capsule'):
                raise ValueError('COLLIDER_KIND')
            vector(collider['a'])
            if collider['kind'] == 'capsule': vector(collider['b'])
            number(collider['radius'], 1e-5, 10)
    if any(c['anchor_bone'] in owned for c in p['chains']):
        raise ValueError('CHAIN_ANCHOR_DEPENDENCY')
    return p


def collider_center(point, c):
    a = vector(c['a'])
    if c['kind'] == 'sphere': return a
    b = vector(c['b']); axis = b-a; length2 = axis @ axis
    return a if length2 < 1e-15 else a + np.clip((point-a) @ axis / length2, 0, 1)*axis


class ChainSolver:
    def __init__(self, profile):
        self.profile = validate_profile(profile)
        self.states = {}; self.accumulator = 0.; self.last_anchors = None
        self.reset_count = 0
        self.solved_anchors = {}

    def reset(self, anchors):
        self.states = {}
        for c in self.profile['chains']:
            matrix = self._anchor(anchors, c['anchor_bone'])
            points = [matrix[:3, 3].copy()]
            for v in c['rest_vectors']: points.append(points[-1] + matrix[:3, :3] @ vector(v))
            x = np.asarray(points)
            self.states[c['id']] = [x, x.copy()]
        self.accumulator = 0.
        self.last_anchors = {k:np.asarray(v).copy() for k,v in anchors.items()}
        self.solved_anchors = {c['anchor_bone']:self._anchor(anchors,c['anchor_bone']).copy()
                               for c in self.profile['chains']}
        self.reset_count += 1

    @staticmethod
    def _anchor(anchors, name):
        m = np.asarray(anchors[name], dtype=float)
        if m.shape != (4,4) or not np.isfinite(m).all() or not np.allclose(m[3], [0,0,0,1]):
            raise ValueError('ANCHOR_MATRIX_INVALID')
        if not np.allclose(m[:3,:3].T @ m[:3,:3], np.eye(3), atol=1e-5) or np.linalg.det(m[:3,:3]) < 0:
            raise ValueError('ANCHOR_SCALE_OR_SHEAR')
        return m

    def advance(self, dt, anchors, *, paused=False, reset=False):
        number(dt, 0, 100)
        for c in self.profile['chains']: self._anchor(anchors, c['anchor_bone'])
        teleported = self.last_anchors is not None and any(
            np.linalg.norm(np.asarray(anchors[k])[:3,3]-v[:3,3]) > self.profile['teleport_m']
            for k,v in self.last_anchors.items())
        if reset or not self.states or teleported or dt > self.profile['max_frame_dt']:
            self.reset(anchors)
        elif paused:
            # Freeze time; caller resets on resume if the body moved while paused.
            return self.result(anchors, 0, 'paused')
        else:
            self.accumulator += dt
            steps = int((self.accumulator+1e-12)/self.profile['fixed_dt'])
            for _ in range(steps): self._step(anchors)
            if steps:
                self.solved_anchors = {c['anchor_bone']:self._anchor(anchors,c['anchor_bone']).copy()
                                       for c in self.profile['chains']}
            self.accumulator -= steps*self.profile['fixed_dt']
            self.last_anchors = {k:np.asarray(v).copy() for k,v in anchors.items()}
            return self.result(anchors, steps, 'stepped')
        return self.result(anchors, 0, 'reset')

    def _step(self, anchors):
        h = self.profile['fixed_dt']
        force = vector(self.profile['gravity'])+vector(self.profile['wind'])
        for c in self.profile['chains']:
            m = self._anchor(anchors, c['anchor_bone']); x, old = self.states[c['id']]
            rest = [m[:3,:3] @ vector(v) for v in c['rest_vectors']]
            before = x.copy(); x[0] = m[:3,3]
            if c['mode'] == 'rigid_plate':
                # One rigid plate may hinge as a whole; do not flex each segment.
                direction = unit(x[-1]-x[0]); total = sum(np.linalg.norm(v) for v in rest)
                tip = x[-1]+(x[-1]-old[-1])*math.exp(-c['damping']*h)
                tip += (force+c['stiffness']*(x[0]+sum(rest)-x[-1]))*h*h
                direction = self._limit(unit(tip-x[0]), unit(sum(rest)), c['max_angle_deg'])
                for i,v in enumerate(rest): x[i+1] = x[i]+direction*np.linalg.norm(v)
            else:
                for i,v in enumerate(rest, 1):
                    target = x[i-1]+v
                    x[i] += (x[i]-old[i])*math.exp(-c['damping']*h)+(force+c['stiffness']*(target-x[i]))*h*h
            for _ in range(self.profile['iterations']):
                for i,v in enumerate(rest, 1):
                    d = x[i]-x[i-1]
                    direction = unit(v) if np.linalg.norm(d) < 1e-12 else unit(d)
                    direction = self._limit(direction, unit(v), c['max_angle_deg'])
                    x[i] = x[i-1]+direction*np.linalg.norm(v)
                    for col in c.get('colliders', []):
                        center = collider_center(x[i], col); delta = x[i]-center
                        if np.linalg.norm(delta) < col['radius']:
                            normal = unit(v) if np.linalg.norm(delta)<1e-12 else unit(delta)
                            x[i] = center+normal*col['radius']
            self.states[c['id']] = [x, before]

    @staticmethod
    def _limit(direction, rest, degrees):
        limit = math.radians(degrees); dot = np.clip(direction @ rest, -1, 1)
        if dot >= math.cos(limit): return direction
        tangent = direction-rest*dot
        if np.linalg.norm(tangent) < 1e-12:
            tangent = np.cross(rest, [1,0,0] if abs(rest[0])<.9 else [0,1,0])
        return rest*math.cos(limit)+unit(tangent)*math.sin(limit)

    def result(self, anchors, steps, reason):
        rows = []; maximum = 0.; penetration = 0.; angle_error = 0.; anchor_error = 0.; rigid_error = 0.
        for c in self.profile['chains']:
            m = self._anchor(anchors,c['anchor_bone'])
            # Attach frame output between fixed simulation steps. Transport a
            # copy, preserving integration state and the fixed-step clock.
            transform = m @ np.linalg.inv(self.solved_anchors[c['anchor_bone']])
            x = self.states[c['id']][0] @ transform[:3,:3].T + transform[:3,3]
            anchor_error=max(anchor_error,float(np.linalg.norm(x[0]-m[:3,3])))
            if c['mode']=='rigid_plate':
                rest_points=np.vstack((np.zeros(3),np.cumsum(c['rest_vectors'],axis=0)))
                rest_distances=np.linalg.norm(rest_points[:,None,:]-rest_points[None,:,:],axis=2)
                actual_distances=np.linalg.norm(x[:,None,:]-x[None,:,:],axis=2)
                rigid_error=max(rigid_error,float(np.max(abs(actual_distances-rest_distances))))
            for i,v in enumerate(c['rest_vectors'], 1):
                d=x[i]-x[i-1]; rest=m[:3,:3] @ vector(v)
                maximum=max(maximum, abs(float(np.linalg.norm(d)-np.linalg.norm(rest))))
                if np.linalg.norm(d)>1e-12:
                    angle=math.degrees(math.acos(float(np.clip(unit(d) @ unit(rest),-1,1))))
                    angle_error=max(angle_error, angle-c['max_angle_deg'])
                for col in c.get('colliders',[]):
                    penetration=max(penetration, col['radius']-float(np.linalg.norm(x[i]-collider_center(x[i],col))))
            rows.append({'id':c['id'],'bones':c['bones'],'points':x.tolist()})
        return {'chains':rows,'steps':steps,'reason':reason,'reset_count':self.reset_count,
                'max_length_error_m':maximum,'max_proxy_penetration_m':penetration,
                'max_angle_error_deg':angle_error,
                'max_anchor_error_m':anchor_error,
                'max_rigid_shape_error_m':rigid_error,
                'constraints_status':'PASS' if maximum<1e-5 and penetration<1e-5 and angle_error<1e-3 and anchor_error<1e-5 and rigid_error<1e-5 else 'FAIL',
                'visual_acceptance':'NOT_RUN','collision_scope':'tip particles versus supplied proxies; not surfaces or continuous collision'}
