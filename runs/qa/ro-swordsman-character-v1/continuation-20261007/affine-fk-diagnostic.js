// Diagnostic rest-affine FK, read-only with respect to engine bone/bind matrices.
import * as THREE from 'three';
export function prepareAffineFK(model, fresh) {
  fresh.root.updateMatrixWorld(true);
  const restWorld = new Map(model.skeleton.bones.map((b,i) => [b,model.skeleton.boneInverses[i].clone().invert()]));
  const localRest = new Map();
  for (const [bone, world] of restWorld) {
    const parent = restWorld.get(bone.parent);
    localRest.set(bone, parent ? parent.clone().invert().multiply(world) : world.clone());
  }
  const initial = new Map(Object.entries(model.bones).map(([name,bone]) => [bone,{
    p:fresh.bones[name].position.clone(), s:fresh.bones[name].scale.clone(),
    q:model.restLocal[name].clone().normalize()
  }]));
  return {restWorld, evaluate() {
    const posed = new Map();
    function worldOf(bone) {
      if (posed.has(bone)) return posed.get(bone);
      const initialTRS = initial.get(bone), rest = localRest.get(bone);
      const q = initialTRS.q.clone().invert().multiply(bone.quaternion).normalize();
      const scale = bone.scale.clone().divide(initialTRS.s);
      const local = rest.clone().multiply(new THREE.Matrix4().compose(new THREE.Vector3(),q,scale));
      local.setPosition(new THREE.Vector3().setFromMatrixPosition(rest).add(bone.position).sub(initialTRS.p));
      const world = localRest.has(bone.parent) ? worldOf(bone.parent).clone().multiply(local) : local;
      posed.set(bone,world);
      return world;
    }
    for (const bone of restWorld.keys()) worldOf(bone);
    return posed;
  }};
}
