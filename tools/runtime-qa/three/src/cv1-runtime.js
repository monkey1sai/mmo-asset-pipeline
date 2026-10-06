// Shared runtime pieces for character V1 QA pages: load a GLB, play its clip through AnimationMixer,
// evaluate corrective rules on the final pose, and measure CPU-evaluated vertices against a Blender reference.
// p1.js keeps its own copy of these so the P1 evidence stays bound to the code that produced it.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { evaluate, driverValues, helperRotations } from './cv1-pose-rules.js';

const hex = (buffer) => [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');

export async function fetchBytes(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`FETCH_FAILED ${url} ${response.status}`);
  const buffer = await response.arrayBuffer();
  return { path: url.replace(/^\//, ''), bytes: buffer.byteLength, sha256: hex(await crypto.subtle.digest('SHA-256', buffer)), buffer };
}
export const asJson = (file) => JSON.parse(new TextDecoder().decode(file.buffer));
export const describe = ({ path, bytes, sha256 }) => ({ path, bytes, sha256 });

export async function save(name, body, type) {
  const response = await fetch(`/__save?name=${encodeURIComponent(name)}`, { method: 'POST', headers: { 'X-CV1-Save': '1', 'Content-Type': type }, body });
  if (!response.ok) throw new Error(`SAVE_FAILED ${name} ${response.status}`);
  return response.text();
}

export async function sha256Of(buffer) {
  return hex(await crypto.subtle.digest('SHA-256', buffer));
}

// Loads one GLB with one clip whose first key is at t = 0 and keys sit on every integer frame.
export async function loadModel(url, fps) {
  const file = await fetchBytes(url);
  const gltf = await new GLTFLoader().parseAsync(file.buffer, '');
  const root = gltf.scene;
  const meshes = {}, bones = {};
  root.traverse((object) => {
    const name = object.userData.name ?? object.name; // GLTFLoader strips "." from node names; the original stays in userData
    if (object.isSkinnedMesh) meshes[name] = object;
    if (object.isBone) bones[name] = object;
  });
  const skeleton = Object.values(meshes)[0].skeleton;
  const indexOf = new Map(skeleton.bones.map((bone, i) => [bone, i]));
  const bind = skeleton.boneInverses.map((matrix) => matrix.clone().invert());
  const restLocal = {};
  let restDisagreement = 0;
  const p = new THREE.Vector3(), s = new THREE.Vector3();
  for (const [name, bone] of Object.entries(bones)) {
    const i = indexOf.get(bone), parent = indexOf.get(bone.parent);
    if (i === undefined) continue;
    const q = new THREE.Quaternion();
    if (parent === undefined) q.copy(bone.quaternion);
    else bind[parent].clone().invert().multiply(bind[i]).decompose(p, q, s);
    restDisagreement = Math.max(restDisagreement, THREE.MathUtils.radToDeg(q.angleTo(bone.quaternion)));
    restLocal[name] = q;
  }
  if (gltf.animations.length !== 1) throw new Error(`EXPECTED_ONE_CLIP got ${gltf.animations.length}`);
  const clip = gltf.animations[0];
  const times = clip.tracks[0].times;
  const timeOfFrame = (frame) => frame / fps;
  if (Math.abs(times[0]) > 1e-6 || Math.abs(times[times.length - 1] - timeOfFrame(times.length - 1)) > 1e-5) {
    throw new Error(`UNEXPECTED_CLIP_KEY_TIMES ${times[0]}..${times[times.length - 1]}`);
  }
  const mixer = new THREE.AnimationMixer(root);
  const makeAction = (source) => {
    const action = mixer.clipAction(source);
    action.setLoop(THREE.LoopOnce, 1);
    action.clampWhenFinished = true;
    return action;
  };
  const action = makeAction(clip);
  const blendActions = ['blendA', 'blendB'].map((name) => { const copy = clip.clone(); copy.name = name; return makeAction(copy); });
  const parents = {};
  for (const [name, bone] of Object.entries(bones)) parents[name] = bone.parent?.isBone ? (bone.parent.userData.name ?? bone.parent.name) : null;
  const restLocalWxyz = Object.fromEntries(Object.entries(restLocal).map(([name, q]) => [name, [q.w, q.x, q.y, q.z]]));
  const animatedBones = [...new Set(clip.tracks.filter((t) => /\.quaternion$/.test(t.name)).map((t) => {
    const node = root.getObjectByName(t.name.replace(/\.quaternion$/, ''));
    return node ? (node.userData.name ?? node.name) : t.name;
  }))];
  const animatedMorphChannels = [];
  for (const track of clip.tracks) {
    const match = track.name.match(/^(.*)\.morphTargetInfluences(\[.*\])?$/);
    if (!match) continue;
    const target = root.getObjectByName(match[1]) ?? root.getObjectByProperty('uuid', match[1]);
    if (!target) throw new Error(`UNRESOLVED_MORPH_TRACK ${track.name}`);
    for (const morph of Object.keys(target.morphTargetDictionary ?? {})) animatedMorphChannels.push([target.userData.name ?? target.name, morph]);
  }
  return {
    file: describe(file), root, meshes, bones, skeleton, restLocal, restLocalWxyz, parents, restDisagreementDeg: restDisagreement, mixer, clip, fps, animatedMorphChannels, animatedBones,
    clipKeyTimes: { first: times[0], last: times[times.length - 1], count: times.length },
    setFrame(frame) {
      for (const other of blendActions) other.stop();
      action.setEffectiveWeight(1);
      action.play();
      action.paused = true;
      action.time = timeOfFrame(frame);
      mixer.update(0);
    },
    setBlend(frameA, frameB, weightB) {
      action.stop();
      [[frameA, 1 - weightB], [frameB, weightB]].forEach(([frame, weight], i) => {
        const blend = blendActions[i];
        blend.play();
        blend.paused = true;
        blend.time = timeOfFrame(frame);
        blend.setEffectiveWeight(weight);
      });
      mixer.update(0);
    },
    poseRel() {
      const out = {};
      for (const [name, rest] of Object.entries(restLocal)) {
        const q = rest.clone().invert().multiply(bones[name].quaternion);
        out[name] = [q.w, q.x, q.y, q.z];
      }
      return out;
    },
  };
}

export function setInfluence(model, mesh, morph, weight) {
  const object = model.meshes[mesh];
  const index = object?.morphTargetDictionary?.[morph];
  if (index === undefined) throw new Error(`MISSING_MORPH_CHANNEL ${mesh}/${morph}`);
  object.morphTargetInfluences[index] = weight;
}

// Helper bones follow their sources; runs after the mixer, before the morph rules.
export function applyHelpers(model, rules) {
  const rotations = helperRotations(rules, model.poseRel(), model.restLocalWxyz, model.parents);
  for (const [name, [w, x, y, z]] of Object.entries(rotations)) model.bones[name].quaternion.copy(model.restLocal[name]).multiply(new THREE.Quaternion(x, y, z, w));
  return rotations;
}

// Evaluator step: runs after the mixer and reads the final pose. A pose override (negative control) skips the helpers.
export function applyCorrectives(model, rules, state, poseOverride) {
  if (!poseOverride) applyHelpers(model, rules);
  const pose = poseOverride ?? model.poseRel();
  const weights = evaluate(rules, pose, state);
  for (const { mesh, morph, weight } of weights) setInfluence(model, mesh, morph, weight);
  return { drivers: driverValues(rules, pose, state), morph_weights: Object.fromEntries(weights.map((w) => [`${w.mesh}/${w.morph}`, w.weight])) };
}

export function clearCorrectives(model, rules) {
  for (const channel of rules.channels) setInfluence(model, channel.mesh, channel.morph, 0);
}

export function currentInfluences(model, rules) {
  return Object.fromEntries(rules.channels.map((c) => [`${c.mesh}/${c.morph}`, model.meshes[c.mesh].morphTargetInfluences[model.meshes[c.mesh].morphTargetDictionary[c.morph]]]));
}

export const maxAbsDifference = (a, b) => Math.max(0, ...Object.keys(b).map((key) => Math.abs((a[key] ?? NaN) - b[key])));

// World positions after the engine's morph then skin (SkinnedMesh.getVertexPosition), compared per original vertex ID.
export function measure(model, reference, values, block, gate) {
  model.root.updateMatrixWorld(true);
  const v = new THREE.Vector3();
  const perMesh = [];
  let max = 0, sumSquares = 0, count = 0, overGate = 0, worst = null, coverage = true;
  for (const layout of reference.mesh_layout) {
    const mesh = model.meshes[layout.name];
    if (!mesh) throw new Error(`MISSING_MESH ${layout.name}`);
    const ids = mesh.geometry.getAttribute('_cv1_id');
    if (!ids) throw new Error(`MISSING_ID_ATTRIBUTE ${layout.name}`);
    const base = block.offset_values + layout.offset_values_in_block;
    const seen = new Uint8Array(layout.vertices);
    let meshMax = 0, meshSquares = 0;
    for (let i = 0; i < ids.count; i++) {
      const id = Math.round(ids.getX(i));
      if (id < 0 || id >= layout.vertices) throw new Error(`ID_OUT_OF_RANGE ${layout.name} ${id}`);
      seen[id] = 1;
      mesh.getVertexPosition(i, v).applyMatrix4(mesh.matrixWorld);
      const dx = v.x - values[base + 3 * id], dy = -v.z - values[base + 3 * id + 1], dz = v.y - values[base + 3 * id + 2]; // glTF -> Blender axes
      const error = Math.hypot(dx, dy, dz);
      meshSquares += error * error;
      if (error > gate) overGate++;
      if (error > meshMax) meshMax = error;
      if (!worst || error > worst.error_m) worst = { mesh: layout.name, blender_vertex: id, error_m: error };
    }
    const covered = seen.every((flag) => flag === 1);
    coverage = coverage && covered;
    perMesh.push({ mesh: layout.name, export_vertices: ids.count, all_blender_vertices_covered: covered, max_error_m: meshMax, rms_error_m: Math.sqrt(meshSquares / ids.count) });
    max = Math.max(max, meshMax);
    sumSquares += meshSquares;
    count += ids.count;
  }
  return { reference_block: block.label, vertices_measured: count, max_error_m: max, rms_error_m: Math.sqrt(sumSquares / count), over_gate: overGate, all_blender_vertices_covered: coverage, worst, per_mesh: perMesh };
}
