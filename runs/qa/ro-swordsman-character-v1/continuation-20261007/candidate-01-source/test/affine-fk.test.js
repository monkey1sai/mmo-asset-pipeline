import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import { prepareAffineFK } from '../src/cv1-affine-fk.js';

function rig(shear = 0, outside = new THREE.Vector3()) {
  const scene = new THREE.Group();
  scene.position.copy(outside);
  const root = new THREE.Bone(), knee = new THREE.Bone(), foot = new THREE.Bone();
  root.name = 'root'; knee.name = 'knee'; foot.name = 'foot';
  scene.add(root); root.add(knee); knee.add(foot);
  knee.position.y = 1; foot.position.y = 1;
  scene.updateMatrixWorld(true);
  const rest = new THREE.Matrix4().set(1,shear,0,outside.x, 0,1,0,outside.y, 0,0,1,outside.z, 0,0,0,1);
  const worlds = [rest, rest.clone().multiply(new THREE.Matrix4().makeTranslation(0,1,0)), rest.clone().multiply(new THREE.Matrix4().makeTranslation(0,2,0))];
  const skeleton = {bones:[root,knee,foot], boneInverses:worlds.map(m => m.clone().invert())};
  return {root:scene,bones:{root,knee,foot},skeleton,restLocal:{root:new THREE.Quaternion(),knee:new THREE.Quaternion(),foot:new THREE.Quaternion()}};
}
function near(actual, expected) {
  assert.equal(actual.length, expected.length);
  actual.forEach((x,i) => assert.ok(Math.abs(x-expected[i]) < 1e-12, `${i}: ${x} != ${expected[i]}`));
}
const point = (m) => new THREE.Vector3().setFromMatrixPosition(m).toArray();

test('rest shear is retained from binds; source and rendered bone data stay unchanged', () => {
  const model=rig(.25), before=JSON.stringify({bind:model.skeleton.boneInverses.map(m=>m.elements), bones:Object.values(model.bones).map(b=>b.matrixWorld.elements)});
  const fk=prepareAffineFK(model,['foot']);
  const worlds=fk.evaluate();
  near(point(worlds.get(model.bones.knee)),[.25,1,0]);
  near(point(worlds.get(model.bones.foot)),[.5,2,0]);
  assert.equal(JSON.stringify({bind:model.skeleton.boneInverses.map(m=>m.elements), bones:Object.values(model.bones).map(b=>b.matrixWorld.elements)}),before);
});

test('relative animation rotates the full affine chain and carries the outside parent', () => {
  const model=rig(.25,new THREE.Vector3(3,4,5)), fk=prepareAffineFK(model,['foot']);
  model.bones.root.quaternion.setFromAxisAngle(new THREE.Vector3(0,0,1),Math.PI/2);
  model.root.position.x=8;
  model.root.updateMatrixWorld(true);
  near(point(fk.evaluate().get(model.bones.foot)),[6,4,5]);
  // Deterministic reconstruction reads current animation, without accumulating an earlier pose.
  near(point(fk.evaluate().get(model.bones.foot)),[6,4,5]);
  model.bones.root.quaternion.identity();
  near(point(fk.evaluate().get(model.bones.foot)),[8.5,6,5]);
});

test('pure TRS animations retain ordinary FK with translation and scale', () => {
  const model=rig(),fk=prepareAffineFK(model,['foot']);
  model.bones.root.position.set(2,3,4);
  model.bones.root.scale.set(2,3,4);
  model.bones.knee.quaternion.setFromAxisAngle(new THREE.Vector3(0,0,1),Math.PI/3);
  model.bones.knee.position.z=.5;
  model.root.updateMatrixWorld(true);
  near(fk.evaluate().get(model.bones.foot).elements,model.bones.foot.matrixWorld.elements);
});

test('missing bones and singular bind data fail closed', () => {
  assert.throws(()=>prepareAffineFK(rig(),['missing']),/MISSING_BONE/);
  const model=rig(); model.skeleton.boneInverses[1].elements.fill(0);
  assert.throws(()=>prepareAffineFK(model,['foot']),/INVALID_BIND/);
});
