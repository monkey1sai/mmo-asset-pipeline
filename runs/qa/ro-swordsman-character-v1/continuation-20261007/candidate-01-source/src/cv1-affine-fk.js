// Pre-IK FK retains the original inverse-bind rest affine instead of re-decomposing it as node TRS.
// This reads bind data only. AnimationMixer, rendered bones, skinning and the comparison formula remain owners
// of their existing data. Relative animation rotation/scale and local translation are applied to the rest affine.
import * as THREE from 'three';

export function prepareAffineFK(model, names) {
  model.root.updateMatrixWorld(true);
  const indices = new Map(model.skeleton.bones.map((bone, i) => [bone, i]));
  const needed = new Set();
  for (const name of names) {
    const bone = model.bones[name];
    if (!bone) throw new Error(`AFFINE_FK_MISSING_BONE ${name}`);
    for (let ancestor = bone; indices.has(ancestor); ancestor = ancestor.parent) needed.add(ancestor);
  }
  const restWorld = new Map(), localRest = new Map(), initial = new Map(), outside = new Map();
  for (const bone of needed) {
    const inverse = model.skeleton.boneInverses[indices.get(bone)];
    if (!inverse.elements.every(Number.isFinite) || Math.abs(inverse.determinant()) < 1e-12) {
      throw new Error(`AFFINE_FK_INVALID_BIND ${bone.name}`);
    }
    restWorld.set(bone, inverse.clone().invert());
  }
  for (const bone of needed) {
    const parentRest = restWorld.get(bone.parent);
    const parentWorld = parentRest ?? bone.parent?.matrixWorld ?? new THREE.Matrix4();
    localRest.set(bone, parentWorld.clone().invert().multiply(restWorld.get(bone)));
    const name = bone.userData.name ?? bone.name;
    const q = model.restLocal[name];
    if (!q || bone.scale.toArray().some((s) => !Number.isFinite(s) || Math.abs(s) < 1e-12)) {
      throw new Error(`AFFINE_FK_INVALID_REST ${name}`);
    }
    initial.set(bone, { position: bone.position.clone(), scale: bone.scale.clone(), rotation: q.clone().normalize() });
    if (!parentRest) outside.set(bone, bone.parent);
  }
  return {
    // Used once to calibrate the frozen sole rest point; callers must not mutate these matrices.
    restWorld,
    evaluate() {
      const posed = new Map();
      function worldOf(bone) {
        if (posed.has(bone)) return posed.get(bone);
        const start = initial.get(bone), rest = localRest.get(bone);
        const rotation = start.rotation.clone().invert().multiply(bone.quaternion).normalize();
        const scale = bone.scale.clone().divide(start.scale);
        const local = rest.clone().multiply(new THREE.Matrix4().compose(new THREE.Vector3(), rotation, scale));
        local.setPosition(new THREE.Vector3().setFromMatrixPosition(rest).add(bone.position).sub(start.position));
        const parent = localRest.has(bone.parent) ? worldOf(bone.parent) : outside.get(bone)?.matrixWorld;
        const world = parent ? parent.clone().multiply(local) : local;
        posed.set(bone, world);
        return world;
      }
      for (const bone of needed) worldOf(bone);
      return posed;
    },
  };
}
