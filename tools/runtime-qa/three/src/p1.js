// Character V1 P1 closed loop: GLB -> Three.js mixer -> final pose -> rule evaluator -> native morph + skin.
// Measures CPU-evaluated vertices against the Blender reference and saves results through serve.py.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { evaluate, driverValues, ownershipConflicts } from './cv1-pose-rules.js';

const ASSETS = '/assets/processed/ro-swordsman-character-v1/p1-closed-loop/';
const QA = '/runs/qa/ro-swordsman-character-v1/p1/';
const FILES = {
  runtime_owner: `${ASSETS}ro_character_p1_runtime_owner.glb`,
  baked_owner: `${ASSETS}ro_character_p1_baked_owner.glb`,
  rules: `${ASSETS}p1-probe-rules.json`,
  reference: `${QA}blender-reference.json`,
  referenceBin: `${QA}blender-reference.f64.bin`,
  phaseStart: `${QA}phase-start.json`,
};
const FOCUS_MESHES = ['SM_RO_glove.R', 'SM_RO_WristLoft.R'];
const $ = (id) => document.getElementById(id);
const hex = (buffer) => [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');

async function fetchBytes(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`FETCH_FAILED ${url} ${response.status}`);
  const buffer = await response.arrayBuffer();
  return { path: url.slice(1), bytes: buffer.byteLength, sha256: hex(await crypto.subtle.digest('SHA-256', buffer)), buffer };
}
const asJson = (file) => JSON.parse(new TextDecoder().decode(file.buffer));
const describe = ({ path, bytes, sha256 }) => ({ path, bytes, sha256 });

async function save(name, body, type) {
  const response = await fetch(`/__save?name=${encodeURIComponent(name)}`, { method: 'POST', headers: { 'X-CV1-Save': '1', 'Content-Type': type }, body });
  if (!response.ok) throw new Error(`SAVE_FAILED ${name} ${response.status}`);
  return response.text();
}

// ---------- scene ----------
const canvas = $('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(960, 960, false);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x77797f);
scene.add(new THREE.HemisphereLight(0xffffff, 0x555560, 1.6));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
keyLight.position.set(-1.5, 2.5, 2.5);
scene.add(keyLight);
const grayMaterial = new THREE.MeshStandardMaterial({ color: 0x9e9e9e, roughness: 0.85, metalness: 0 });
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.05, 20);
const overlay = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: 0xff3355, size: 3, sizeAttenuation: false, depthTest: false }));
overlay.renderOrder = 10;
overlay.visible = false;
scene.add(overlay);

const blenderToThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);

function setCamera(kind, reference) {
  if (kind === 'wrist') {
    const half = reference.camera.ortho_scale / 2;
    Object.assign(camera, { left: -half, right: half, top: half, bottom: -half });
    camera.position.copy(blenderToThree(reference.camera.location));
    camera.up.set(0, 1, 0);
    camera.lookAt(blenderToThree(reference.camera.look_at));
  } else {
    Object.assign(camera, { left: -1.15, right: 1.15, top: 1.15, bottom: -1.15 });
    camera.position.set(-2.4, 1.5, 3.2);
    camera.up.set(0, 1, 0);
    camera.lookAt(0, 0.9, 0);
  }
  camera.updateProjectionMatrix();
}

// ---------- model ----------
async function loadModel(mode, fps) {
  const file = await fetchBytes(FILES[mode]);
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
  // Blender's exporter keeps scene frame numbers: frame f is keyed at f / fps (frame 1 at 1/fps, not 0).
  const timeOfFrame = (frame) => frame / fps;
  const keyTimes = clip.tracks[0].times;
  if (Math.abs(keyTimes[0] - timeOfFrame(1)) > 1e-6 || Math.abs(keyTimes[keyTimes.length - 1] - timeOfFrame(keyTimes.length)) > 1e-6) {
    throw new Error(`UNEXPECTED_CLIP_KEY_TIMES ${keyTimes[0]}..${keyTimes[keyTimes.length - 1]}`);
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
  action.play();
  action.paused = true;
  // Morph channels an animation clip writes: [mesh original name, morph name]
  const animatedMorphChannels = [];
  for (const track of clip.tracks) {
    const match = track.name.match(/^(.*)\.morphTargetInfluences(\[.*\])?$/);
    if (!match) continue;
    const target = root.getObjectByName(match[1]) ?? root.getObjectByProperty('uuid', match[1]);
    if (!target) throw new Error(`UNRESOLVED_MORPH_TRACK ${track.name}`);
    for (const morph of Object.keys(target.morphTargetDictionary ?? {})) animatedMorphChannels.push([target.userData.name ?? target.name, morph]);
  }
  return {
    mode, file: describe(file), root, meshes, bones, skeleton, restLocal, restDisagreementDeg: restDisagreement, mixer, action, blendActions, clip, fps, animatedMorphChannels,
    clipKeyTimes: { first: keyTimes[0], last: keyTimes[keyTimes.length - 1], count: keyTimes.length },
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

// Swap materials per mesh; scene.overrideMaterial would also repaint the reference-point overlay.
function setShading(models, kind) {
  for (const model of Object.values(models)) {
    for (const mesh of Object.values(model.meshes)) {
      mesh.userData.texturedMaterial ??= mesh.material;
      mesh.material = kind === 'gray' ? grayMaterial : mesh.userData.texturedMaterial;
    }
  }
}

function setInfluence(model, mesh, morph, weight) {
  const object = model.meshes[mesh];
  const index = object?.morphTargetDictionary?.[morph];
  if (index === undefined) throw new Error(`MISSING_MORPH_CHANNEL ${mesh}/${morph}`);
  object.morphTargetInfluences[index] = weight;
}

// Evaluator step: runs after the mixer, reads the final pose.
function applyCorrectives(model, rules, state, poseOverride) {
  const pose = poseOverride ?? model.poseRel();
  const weights = evaluate(rules, pose, state);
  for (const { mesh, morph, weight } of weights) setInfluence(model, mesh, morph, weight);
  return { drivers: driverValues(rules, pose, state), morph_weights: Object.fromEntries(weights.map((w) => [`${w.mesh}/${w.morph}`, w.weight])) };
}

function clearCorrectives(model, rules) {
  for (const channel of rules.channels) setInfluence(model, channel.mesh, channel.morph, 0);
}

function currentInfluences(model, rules) {
  return Object.fromEntries(rules.channels.map((c) => [`${c.mesh}/${c.morph}`, model.meshes[c.mesh].morphTargetInfluences[model.meshes[c.mesh].morphTargetDictionary[c.morph]]]));
}

// ---------- measurement ----------
function measure(model, reference, values, block, gate, tier) {
  model.root.updateMatrixWorld(true);
  const v = new THREE.Vector3();
  const perMesh = [];
  let max = 0, sumSquares = 0, count = 0, overGate = 0, overTier = 0, worst = null, coverage = true;
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
      const runtime = [v.x, -v.z, v.y]; // glTF (x, y, z) -> Blender (x, -z, y)
      const ref = [values[base + 3 * id], values[base + 3 * id + 1], values[base + 3 * id + 2]];
      const error = Math.hypot(runtime[0] - ref[0], runtime[1] - ref[1], runtime[2] - ref[2]);
      meshSquares += error * error;
      if (error > gate) overGate++;
      if (error > tier) overTier++;
      if (error > meshMax) meshMax = error;
      if (!worst || error > worst.error_m) worst = { mesh: layout.name, blender_vertex: id, export_vertex: i, error_m: error, runtime, reference: ref };
    }
    const covered = seen.every((flag) => flag === 1);
    coverage = coverage && covered;
    perMesh.push({ mesh: layout.name, export_vertices: ids.count, blender_vertices: layout.vertices, all_blender_vertices_covered: covered, max_error_m: meshMax, rms_error_m: Math.sqrt(meshSquares / ids.count) });
    max = Math.max(max, meshMax);
    sumSquares += meshSquares;
    count += ids.count;
  }
  return { reference_block: block.label, vertices_measured: count, max_error_m: max, rms_error_m: Math.sqrt(sumSquares / count), over_gate: overGate, over_precision_tier: overTier, all_blender_vertices_covered: coverage, worst, per_mesh: perMesh };
}

const maxAbsDifference = (a, b) => Math.max(...Object.keys(b).map((key) => Math.abs((a[key] ?? NaN) - b[key])));

async function capture(name) {
  renderer.render(scene, camera);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  const buffer = await blob.arrayBuffer();
  const path = await save(name, buffer, 'image/png');
  return { path, bytes: buffer.byteLength, sha256: hex(await crypto.subtle.digest('SHA-256', buffer)) };
}

async function runP1(app) {
  const { reference, values, rules, phaseStart, inputs, models } = app;
  const gate = phaseStart.preregistered.wiring_gate_max_error_m, tier = phaseStart.preregistered.precision_tier_m;
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'z').toLowerCase();
  const runtime = models.runtime_owner, baked = models.baked_owner;
  const blockOf = (label) => { const block = reference.blocks.find((b) => b.label === label); if (!block) throw new Error(`MISSING_BLOCK ${label}`); return block; };
  const started = performance.now();

  // 1. runtime owner: mixer -> final pose -> evaluator -> morph + skin
  const runtimeSamples = [];
  let stalePose = null, previousPose = null;
  for (const sample of phaseStart.preregistered.samples) {
    const block = blockOf(`runtime/frame-${sample.frame}`);
    runtime.setFrame(sample.frame);
    if (sample.frame === 61) stalePose = previousPose;
    previousPose = runtime.poseRel();
    const evaluated = applyCorrectives(runtime, rules, { 'grasp.R': sample.grasp });
    runtimeSamples.push({
      frame: sample.frame, half_frame: !Number.isInteger(sample.frame), grasp: sample.grasp, ...evaluated,
      driver_max_abs_difference_vs_blender: maxAbsDifference(evaluated.drivers, block.drivers),
      weight_max_abs_difference_vs_blender: maxAbsDifference(evaluated.morph_weights, block.morph_weights),
      ...measure(runtime, reference, values, block, gate, tier),
    });
  }

  // 2. blend of two paused actions; the evaluator must see the blended pose
  const blendBlock = blockOf('runtime/blend-1-61-0.5');
  runtime.setBlend(1, 61, 0.5);
  const blendEvaluated = applyCorrectives(runtime, rules, { 'grasp.R': blendBlock.grasp });
  const blend = {
    ...blendEvaluated, grasp: blendBlock.grasp,
    driver_max_abs_difference_vs_blender: maxAbsDifference(blendEvaluated.drivers, blendBlock.drivers),
    weight_max_abs_difference_vs_blender: maxAbsDifference(blendEvaluated.morph_weights, blendBlock.morph_weights),
    ...measure(runtime, reference, values, blendBlock, gate, tier),
  };

  // 3. negative controls
  const frame61 = blockOf('runtime/frame-61');
  runtime.setFrame(61);
  clearCorrectives(runtime, rules);
  const nc1 = measure(runtime, reference, values, frame61, gate, tier);
  runtime.setFrame(61);
  const staleEvaluated = applyCorrectives(runtime, rules, { 'grasp.R': 1 }, stalePose);
  const nc2 = measure(runtime, reference, values, frame61, gate, tier);
  const nc3 = ownershipConflicts(rules, baked.animatedMorphChannels);
  let nc4 = { raised: false, message: null };
  try {
    const broken = structuredClone(rules);
    broken.drivers['wrist_progress.R'].bone = 'hand.R_not_in_skeleton';
    evaluate(broken, runtime.poseRel(), { 'grasp.R': 0 });
  } catch (error) {
    nc4 = { raised: true, message: error.message };
  }
  const negativeControls = {
    NC1_evaluator_off_frame_61: { detected: nc1.max_error_m > gate, max_error_m: nc1.max_error_m, over_gate: nc1.over_gate, worst: nc1.worst },
    NC2_stale_pose_frame_61: { detected: nc2.max_error_m > gate, stale_pose_from_frame: 53.5, weights_used: staleEvaluated.morph_weights, max_error_m: nc2.max_error_m, over_gate: nc2.over_gate, worst: nc2.worst },
    NC3_baked_clip_in_runtime_owner_mode: { detected: nc3.length > 0, conflicting_channels: nc3 },
    NC4_missing_bone: { detected: nc4.raised && /^MISSING_BONE:/.test(nc4.message ?? ''), ...nc4 },
  };

  // 4. baked owner: the clip writes the morph weights, evaluator off
  const bakedSamples = [];
  for (const sample of phaseStart.preregistered.samples) {
    const block = blockOf(`baked/frame-${sample.frame}`);
    baked.setFrame(sample.frame);
    const influences = currentInfluences(baked, rules);
    bakedSamples.push({
      frame: sample.frame, half_frame: !Number.isInteger(sample.frame), morph_weights: influences,
      weight_max_abs_difference_vs_blender: maxAbsDifference(influences, block.morph_weights),
      ...measure(baked, reference, values, block, gate, tier),
    });
  }

  // 5. renders from the Blender-matched camera (qualitative)
  const previous = { model: app.active, kind: $('camera').value, shading: $('shading').value, overlay: overlay.visible };
  app.show('runtime_owner');
  setCamera('wrist', reference);
  overlay.visible = false;
  const images = [];
  for (const render of reference.renders) {
    runtime.setFrame(render.frame);
    const evaluated = applyCorrectives(runtime, rules, { 'grasp.R': render.grasp });
    setShading(models, 'gray');
    images.push({ frame: render.frame, grasp: render.grasp, ...evaluated, shading: 'gray', image: await capture(`p1-${stamp}-runtime-wrist-frame-${String(render.frame).padStart(3, '0')}.png`), blender_image: render.image });
  }
  setShading(models, 'textured');
  images.push({ frame: 61, grasp: 1, shading: 'textured', image: await capture(`p1-${stamp}-runtime-wrist-frame-061-textured.png`) });
  app.show(previous.model);
  setCamera(previous.kind, reference);
  setShading(models, previous.shading);
  overlay.visible = previous.overlay;

  const all = [...runtimeSamples, blend, ...bakedSamples];
  const summarise = (rows) => ({ samples: rows.length, max_error_m: Math.max(...rows.map((r) => r.max_error_m)), max_rms_error_m: Math.max(...rows.map((r) => r.rms_error_m)), over_gate: rows.reduce((n, r) => n + r.over_gate, 0), over_precision_tier: rows.reduce((n, r) => n + r.over_precision_tier, 0) });
  const ownership = ownershipConflicts(rules, runtime.animatedMorphChannels);
  const gl = renderer.getContext();
  const debug = gl.getExtension('WEBGL_debug_renderer_info');
  const verdicts = {
    runtime_owner_wiring_gate: runtimeSamples.every((r) => r.max_error_m <= gate),
    blend_wiring_gate: blend.max_error_m <= gate,
    baked_owner_wiring_gate: bakedSamples.every((r) => r.max_error_m <= gate),
    all_blender_vertices_covered: all.every((r) => r.all_blender_vertices_covered),
    runtime_owner_clip_has_no_owned_morph_channel: ownership.length === 0,
    negative_controls_all_detected: Object.values(negativeControls).every((c) => c.detected),
    precision_tier_1um_met: all.every((r) => r.max_error_m <= tier),
  };
  const result = {
    observed_utc: new Date().toISOString(), run: `p1-${stamp}`, phase: 'P1 closed loop, not a candidate',
    runtime: { engine: 'three.js', revision: THREE.REVISION, user_agent: navigator.userAgent, webgl_version: gl.getParameter(gl.VERSION), webgl_renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null },
    inputs, gate_m: gate, precision_tier_m: tier,
    evaluation_order: ['AnimationMixer.update (clip sampling and blending)', 'read final bone local rotations, rest-relative', 'rule evaluator writes morphTargetInfluences', 'updateMatrixWorld', 'engine morph then skin (getVertexPosition on CPU; same order on GPU)'],
    measurement: 'SkinnedMesh.getVertexPosition(i) (morph then skinning) x matrixWorld, converted glTF->Blender axes, compared with the Blender depsgraph position of the same original vertex ID. CPU values; not GPU-frame evidence.',
    name_mapping: 'GLTFLoader sanitises node names (removes "."); original names are read from userData.name for bones and meshes.',
    frame_to_time: { rule: 'time = frame / fps', clip_key_times_s: runtime.clipKeyTimes, note: 'Blender exporter keeps scene frame numbers; times before the first key hold the first pose.' },
    rest_from_inverse_bind_vs_node_default_max_deg: { runtime_owner: runtime.restDisagreementDeg, baked_owner: baked.restDisagreementDeg },
    animated_morph_channels: { runtime_owner: runtime.animatedMorphChannels, baked_owner: baked.animatedMorphChannels },
    verdicts, wiring_gate_pass: Object.entries(verdicts).filter(([key]) => key !== 'precision_tier_1um_met').every(([, value]) => value),
    summary: { runtime_owner_integer_frames: summarise(runtimeSamples.filter((r) => !r.half_frame)), runtime_owner_half_frames: summarise(runtimeSamples.filter((r) => r.half_frame)), blend: summarise([blend]), baked_owner_integer_frames: summarise(bakedSamples.filter((r) => !r.half_frame)), baked_owner_half_frames: summarise(bakedSamples.filter((r) => r.half_frame)) },
    runtime_owner_samples: runtimeSamples, blend_sample: blend, baked_owner_samples: bakedSamples, negative_controls: negativeControls, images,
    measurement_ms: Math.round(performance.now() - started),
  };
  result.saved_as = await save(`p1-${stamp}-runtime-results.json`, JSON.stringify(result, null, 1), 'application/json');
  return result;
}

// ---------- app ----------
async function main() {
  const status = $('status');
  const [referenceFile, binFile, rulesFile, phaseFile] = await Promise.all([fetchBytes(FILES.reference), fetchBytes(FILES.referenceBin), fetchBytes(FILES.rules), fetchBytes(FILES.phaseStart)]);
  const reference = asJson(referenceFile), rules = asJson(rulesFile), phaseStart = asJson(phaseFile);
  const values = new Float64Array(binFile.buffer);
  if (binFile.sha256 !== reference.binary.sha256 || rulesFile.sha256 !== reference.rules.sha256 || phaseFile.sha256 !== reference.phase_start.sha256) throw new Error('REFERENCE_HASH_MISMATCH');
  status.textContent = '載入 GLB…';
  const models = { runtime_owner: await loadModel('runtime_owner', reference.fps), baked_owner: await loadModel('baked_owner', reference.fps) };
  for (const mode of Object.keys(models)) if (models[mode].file.sha256 !== reference.glb[mode].sha256) throw new Error(`GLB_HASH_MISMATCH ${mode}`);
  const harness = {};
  for (const name of ['index.html', 'src/p1.js', 'src/cv1-pose-rules.js']) harness[name] = describe(await fetchBytes(`/tools/runtime-qa/three/${name}`));
  const inputs = { harness, reference: describe(referenceFile), reference_binary: describe(binFile), rules: describe(rulesFile), phase_start: describe(phaseFile), glb: { runtime_owner: models.runtime_owner.file, baked_owner: models.baked_owner.file } };
  const app = {
    reference, values, rules, phaseStart, inputs, models, active: 'runtime_owner', busy: false, playing: false, frame: 1,
    show(mode) {
      for (const [name, model] of Object.entries(models)) { if (name === mode) scene.add(model.root); else scene.remove(model.root); }
      app.active = mode;
    },
  };
  app.show('runtime_owner');
  setCamera('wrist', reference);
  setShading(models, 'gray');

  const weightsBody = $('weights').querySelector('tbody');
  function showWeights(info) {
    const rows = [...Object.entries(info.drivers ?? {}).map(([k, v]) => [`驅動 ${k}`, v]), ...Object.entries(info.morph_weights).map(([k, v]) => [k.split('/')[1], v])];
    weightsBody.replaceChildren(...rows.map(([name, value]) => { const tr = document.createElement('tr'); const a = document.createElement('td'); const b = document.createElement('td'); a.textContent = name; b.textContent = value.toFixed(4); tr.append(a, b); return tr; }));
  }
  function updateOverlay() {
    const prefix = app.active === 'runtime_owner' ? 'runtime' : 'baked';
    const block = reference.blocks.find((b) => b.label === `${prefix}/frame-${app.frame}`);
    overlay.visible = $('overlay').checked && !!block;
    if (!overlay.visible) return;
    const points = [];
    for (const layout of reference.mesh_layout.filter((m) => FOCUS_MESHES.includes(m.name))) {
      const base = block.offset_values + layout.offset_values_in_block;
      for (let i = 0; i < layout.vertices; i++) points.push(values[base + 3 * i], values[base + 3 * i + 2], -values[base + 3 * i + 1]);
    }
    overlay.geometry.dispose();
    overlay.geometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  }
  // One frame: mixer first, then the evaluator on the final pose, then render.
  function update() {
    const model = models[app.active];
    model.setFrame(app.frame);
    if (app.active === 'runtime_owner') {
      if ($('evaluator').checked) showWeights(applyCorrectives(model, rules, { 'grasp.R': Number($('grasp').value) }));
      else { clearCorrectives(model, rules); showWeights({ morph_weights: currentInfluences(model, rules) }); }
    } else {
      showWeights({ morph_weights: currentInfluences(model, rules) });
    }
    $('frameOut').textContent = app.frame.toFixed(1);
    $('graspOut').textContent = Number($('grasp').value).toFixed(2);
    updateOverlay();
    renderer.render(scene, camera);
  }
  let last = performance.now();
  function loop(now) {
    const dt = (now - last) / 1000;
    last = now;
    if (!app.busy) {
      if (app.playing) {
        app.frame += dt * reference.fps * Number($('speed').value);
        if (app.frame > 61) app.frame = 1;
        $('frame').value = app.frame;
      }
      update();
    }
    requestAnimationFrame(loop);
  }
  $('frame').addEventListener('input', () => { app.frame = Number($('frame').value); });
  $('play').addEventListener('click', () => { app.playing = !app.playing; $('play').textContent = app.playing ? '暫停' : '播放'; if (!app.playing) { app.frame = Math.round(app.frame * 2) / 2; $('frame').value = app.frame; } });
  $('mode').addEventListener('change', () => { app.show($('mode').value); $('evaluator').disabled = $('grasp').disabled = app.active !== 'runtime_owner'; });
  $('camera').addEventListener('change', () => setCamera($('camera').value, reference));
  $('shading').addEventListener('change', () => setShading(models, $('shading').value));
  $('run').addEventListener('click', async () => {
    $('run').disabled = true;
    try { await app.run(); } catch (error) { status.textContent = `量測失敗：${error.message}`; status.className = 'bad'; } finally { $('run').disabled = false; }
  });
  app.run = async () => {
    app.busy = true;
    status.className = '';
    status.textContent = '量測中…';
    try {
      const result = await runP1(app);
      app.lastResult = result;
      const s = result.summary;
      const um = (m) => `${(m * 1e6).toFixed(3)} µm`;
      status.className = result.wiring_gate_pass ? 'ok' : 'bad';
      status.textContent = [
        `接線關卡（≤ ${um(result.gate_m)}）：${result.wiring_gate_pass ? '通過' : '未通過'}`,
        `runtime owner 整幀 max ${um(s.runtime_owner_integer_frames.max_error_m)}｜半幀 max ${um(s.runtime_owner_half_frames.max_error_m)}`,
        `混合取樣 max ${um(s.blend.max_error_m)}`,
        `baked owner 整幀 max ${um(s.baked_owner_integer_frames.max_error_m)}｜半幀 max ${um(s.baked_owner_half_frames.max_error_m)}`,
        `反例全部被抓到：${result.verdicts.negative_controls_all_detected ? '是' : '否'}`,
        `1 µm 精度層：${result.verdicts.precision_tier_1um_met ? '達到' : '未達到（僅報告）'}`,
        `已存：${result.saved_as}`,
      ].join('\n');
      return result;
    } finally {
      app.busy = false;
    }
  };
  window.cv1 = app;
  status.textContent = `已載入。three r${THREE.REVISION}；runtime-owner clip 的 morph 軌數 ${models.runtime_owner.animatedMorphChannels.length}，baked-owner ${models.baked_owner.animatedMorphChannels.length}。`;
  requestAnimationFrame(loop);
}

main().catch((error) => { $('status').textContent = `載入失敗：${error.message}`; $('status').className = 'bad'; console.error(error); });
