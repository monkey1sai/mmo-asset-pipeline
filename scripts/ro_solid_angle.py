"""Conservative supplemental classification for ambiguous rays on oriented solids."""
import math
import numpy as np


def certify_oriented_closed(points, triangles):
    values=np.asarray(points,dtype=np.float64)
    if not np.all(np.isfinite(values)):raise ValueError('NONFINITE_SOLID')
    keys=[tuple(float(c) for c in p) for p in values]
    # Only exact coincident UV-seam positions; never quantize or move a gap shut.
    canonical={};ids=[]
    for key in keys:
        if key not in canonical:canonical[key]=len(canonical)
        ids.append(canonical[key])
    edges={}
    parent=list(range(len(canonical)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for tri in triangles:
        if len(set(keys[i] for i in tri))!=3:
            raise ValueError('DEGENERATE_SOLID_TRIANGLE')
        a,b,c=values[list(tri)]
        if np.linalg.norm(np.cross(b-a,c-a))<1e-16:raise ValueError('DEGENERATE_SOLID_TRIANGLE')
        for i in tri[1:]:parent[find(ids[i])]=find(ids[tri[0]])
        for a,b in zip(tri,tri[1:]+tri[:1]):
            x,y=keys[a],keys[b];edges.setdefault(tuple(sorted((x,y))),[]).append((x,y))
    if any(len(rows)!=2 or rows[0]!=tuple(reversed(rows[1])) for rows in edges.values()):
        raise ValueError('CLOSED_ORIENTED_SOLID_REQUIRED')
    volumes={};component_faces={}
    for tri in triangles:
        component=find(ids[tri[0]]);a,b,c=values[list(tri)]
        volumes[component]=volumes.get(component,0.)+float(np.dot(a,np.cross(b,c)))/6
        component_faces[component]=component_faces.get(component,0)+1
    if any(not math.isfinite(v) or abs(v)<1e-18 for v in volumes.values()):raise ValueError('ZERO_VOLUME_SOLID')
    if len(set(v>0 for v in volumes.values()))>1:raise ValueError('CONFLICTING_COMPONENT_ORIENTATION')
    return {'canonical_vertices':len(canonical),'duplicate_position_vertices':len(values)-len(canonical),
        'maximum_correspondence_difference_m':0.,'correspondence_tolerance_m':0.,'exact_position_mapping':True,
        'components':[{'faces':component_faces[k],'signed_volume_m3':v} for k,v in volumes.items()]}


def classify_winding(points, triangles, point, nearest_m, tolerance=1e-7):
    if not math.isfinite(nearest_m) or nearest_m<1e-6:
        return None,None
    vertices=np.asarray(points,dtype=np.float64)[np.asarray(triangles,dtype=int)]-np.asarray(point,dtype=np.float64)
    a,b,c=vertices[:,0],vertices[:,1],vertices[:,2]
    la,lb,lc=np.linalg.norm(a,axis=1),np.linalg.norm(b,axis=1),np.linalg.norm(c,axis=1)
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
    winding=float(np.sum(2*np.arctan2(numerator,denominator))/(4*math.pi))
    if not math.isfinite(winding):return None,winding
    if abs(winding)<tolerance:return False,winding
    if abs(abs(winding)-1)<tolerance:return True,winding
    return None,winding
