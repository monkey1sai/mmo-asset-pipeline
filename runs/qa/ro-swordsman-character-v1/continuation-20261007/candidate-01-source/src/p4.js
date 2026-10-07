// Character V1 P4 QA scene: clip transitions driven by an explicit weight controller (cv1-transition.js, twin of
// scripts/cv1_transition.py), AnimationMixer blending -> stance-foot lock (cv1-foot-lock.js, twin of
// scripts/cv1_foot_lock.py) -> shared sword socket -> helper bones -> corrective rules -> engine morph + skin. Measurements: the Blender transition reference (closed loop), determinism of play / pause-resume
// / seek, loop seams, weight continuity of repeated switches, counterexamples and evaluation cost.
// Usage: p4.html?manifest=/runs/qa/.../p4-manifest.json
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { fetchBytes, asJson, describe, save, sha256Of, loadModel, applyHelpers, applyCorrectives, clearCorrectives, measure, prepareSocket, socketAt } from './cv1-runtime.js';
import { weights as layerWeights, layers as layerStarts, layerFrame, blendStates, boneGroup, GROUPS } from './cv1-transition.js';
import { schedule as footSchedule, neededTimes, soleTarget, twoBone, qmul, qconj, add, sub, SIDES } from './cv1-foot-lock.js';
import { prepareAffineFK } from './cv1-affine-fk.js';

const $ = (id) => document.getElementById(id);
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
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.05, 20);

function setCamera(kind, model) {
  model.root.updateMatrixWorld(true);
  const centre = new THREE.Vector3();
  if (kind === 'hands' || kind === 'feet') {
    const names = kind === 'hands' ? ['hand.R', 'hand.L'] : ['foot.R', 'foot.L'];
    for (const name of names) centre.add(new THREE.Vector3().setFromMatrixPosition(model.bones[name].matrixWorld));
    centre.multiplyScalar(0.5);
    Object.assign(camera, { left: -0.5, right: 0.5, top: 0.5, bottom: -0.5 });
    camera.position.copy(centre).add(new THREE.Vector3(-0.8, 0.5, 2.2));
    camera.lookAt(centre);
  } else if (kind === 'side') {
    // Right side (+X), level with the hips: the character faces +Z, so a planted foot's travel reads left to right.
    Object.assign(camera, { left: -1.2, right: 1.2, top: 1.2, bottom: -1.2 });
    camera.position.set(3.4, 0.85, -0.2);
    camera.lookAt(0, 0.85, -0.2);
  } else {
    Object.assign(camera, { left: -1.4, right: 1.4, top: 1.4, bottom: -1.4 });
    camera.position.set(-2.4, 1.6, 3.4);
    camera.lookAt(0, 0.75, -0.3);
  }
  camera.up.set(0, 1, 0);
  camera.updateProjectionMatrix();
}

async function capture(name) {
  renderer.render(scene, camera);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  const buffer = await blob.arrayBuffer();
  return { path: await save(name, buffer, 'image/png'), bytes: buffer.byteLength, sha256: await sha256Of(buffer) };
}

// ---- clips split by bone group (upper body: spine_01 and below; lower: the rest) ----
function splitClip(clip, model, groupOf) {
  const parts = { upper: [], lower: [] };
  for (const track of clip.tracks) {
    const nodeName = track.name.slice(0, track.name.lastIndexOf('.'));
    const node = model.root.getObjectByName(nodeName);
    const bone = node ? (node.userData.name ?? node.name) : null;
    parts[bone && groupOf[bone] === 'upper' ? 'upper' : 'lower'].push(track);
  }
  return Object.fromEntries(GROUPS.map((g) => [g, new THREE.AnimationClip(`${clip.name}:${g}`, clip.duration, parts[g])]));
}

function statesOf(info, frame, keys) {
  // States are linear between integer frames (ramps break on integer frames), so the per-frame table interpolates exactly.
  const f0 = Math.floor(frame + 1e-9), a = frame - f0;
  const out = {};
  for (const key of keys) {
    const table = info.states_per_frame[key];
    out[key] = table ? (a < 1e-9 ? table[f0] : table[f0] * (1 - a) + table[f0 + 1] * a) : 0;
  }
  return out;
}

async function main() {
  const status = $('status');
  const manifestUrl = new URLSearchParams(location.search).get('manifest');
  if (!manifestUrl) throw new Error('MISSING_MANIFEST_PARAMETER');
  const manifestFile = await fetchBytes(manifestUrl);
  const manifest = asJson(manifestFile);
  const [referenceFile, binFile, rulesFile] = await Promise.all([fetchBytes(`/${manifest.reference.path}`), fetchBytes(`/${manifest.reference_binary.path}`), fetchBytes(`/${manifest.rules.path}`)]);
  const transitionsFile = await fetchBytes(`/${manifest.transitions.path}`);
  for (const [file, expected] of [[referenceFile, manifest.reference], [binFile, manifest.reference_binary], [rulesFile, manifest.rules], [transitionsFile, manifest.transitions]]) {
    if (file.sha256 !== expected.sha256) throw new Error(`HASH_MISMATCH ${file.path}`);
  }
  const reference = asJson(referenceFile), rules = asJson(rulesFile);
  const values = manifest.reference_binary.dtype.startsWith('float32') ? new Float32Array(binFile.buffer) : new Float64Array(binFile.buffer);
  const stateKeys = [...new Set(Object.values(rules.drivers).filter((d) => d.type === 'state').map((d) => d.key))].sort();
  status.textContent = '載入角色與片段 GLB…';
  const baseInfo = manifest.clips[manifest.base];
  const model = await loadModel(`/${baseInfo.glb.path}`, baseInfo.fps);
  if (model.file.sha256 !== baseInfo.glb.sha256) throw new Error('GLB_HASH_MISMATCH base');
  const groupOf = Object.fromEntries(Object.keys(model.bones).map((name) => [name, boneGroup(name, model.parents)]));
  const clipFiles = {}, clips = {};
  for (const [short, info] of Object.entries(manifest.clips)) {
    const file = short === manifest.base ? model.file : await fetchBytes(`/${info.glb.path}`);
    if (file.sha256 !== info.glb.sha256) throw new Error(`GLB_HASH_MISMATCH ${short}`);
    const clip = short === manifest.base ? model.clip : (await new GLTFLoader().parseAsync(file.buffer, '')).animations[0];
    clipFiles[short] = describe(file);
    clips[short] = { full: clip, parts: splitClip(clip, model, groupOf) };
  }
  const lookup = Object.fromEntries(Object.entries(manifest.clips).map(([short, info]) => [short, { frames: info.frames, loop: info.loop, fps: info.fps }]));
  // The bed socket is shared by the bed clips; calibrate once at rest, before any mixer update.
  const socketBlocks = Object.fromEntries(Object.entries(manifest.clips).filter(([, info]) => info.sword_socket).map(([short, info]) => [short, info.sword_socket]));
  const prepared = prepareSocket(model, Object.values(socketBlocks)[0] ?? null);
  // Foot lock: the Blender rest sole point carried rigidly by each foot joint (offset taken at rest, like the socket).
  const toGl = ([x, y, z]) => [x, z, -y];
  // Exported node TRS loses tiny rest shear. Near a straight leg IK amplifies that FK difference.
  // Read the same GLB's original inverse binds for solver FK; never change the binds or the rendered skin path.
  const affineFK = manifest.foot_lock ? prepareAffineFK(model, SIDES.flatMap((side) => manifest.foot_lock.legs[side])) : null;
  const footLock = manifest.foot_lock ? (() => {
    model.root.updateMatrixWorld(true);
    const soleLocal = {};
    for (const side of SIDES) {
      const foot = model.bones[manifest.foot_lock.legs[side][2]];
      soleLocal[side] = new THREE.Vector3(...toGl(manifest.foot_lock.sole_rest_world_blender[side])).applyMatrix4(affineFK.restWorld.get(foot).clone().invert());
    }
    return { soleLocal, legs: manifest.foot_lock.legs, forward: toGl(manifest.foot_lock.forward_blender), up: toGl(manifest.foot_lock.up_blender),
             fallback: toGl(manifest.foot_lock.fallback_normal_blender) };
  })() : null;
  const flClips = Object.fromEntries(Object.entries(manifest.clips).map(([short, info]) => [short, { frames: info.frames, loop: info.loop, fps: info.fps,
    nominal_speed_m_s: info.nominal_speed_m_s, stance: info.stance }]));
  const harness = {};
  for (const name of ['p4.html', 'src/p4.js', 'src/cv1-runtime.js', 'src/cv1-pose-rules.js', 'src/cv1-transition.js', 'src/cv1-foot-lock.js', 'src/cv1-affine-fk.js']) harness[name] = describe(await fetchBytes(`/tools/runtime-qa/three/${name}`));
  const inputs = { manifest: describe(manifestFile), harness, reference: describe(referenceFile), reference_binary: describe(binFile), rules: describe(rulesFile), transitions: describe(transitionsFile), glb: clipFiles };

  // ---- scenario actions: one action per layer and bone group, activated at rest in layer order ----
  let current = null, legRestore = [];
  // The foot lock writes leg joints after the mixer; PropertyMixer only rewrites a joint when its blended value changes,
  // so the lock-free values are put back before every mixer update (bookkeeping, nothing carries into the result).
  function restoreLegs() {
    for (const [bone, q] of legRestore) bone.quaternion.copy(q);
    legRestore = [];
  }
  function setup(def, override) {
    restoreLegs();
    model.mixer.stopAllAction();
    model.mixer.update(0);
    const starts = layerStarts(def);
    const actions = {};
    for (const [layer, start] of Object.entries(starts)) {
      const info = lookup[start.clip];
      actions[layer] = {};
      for (const g of GROUPS) {
        const source = (override?.[start.clip]?.[g]) ?? clips[start.clip].parts[g];
        const clip = source.clone();
        clip.name = `${def.id ?? 'scn'}:${layer}:${g}`;
        const action = model.mixer.clipAction(clip);
        action.setLoop(info.loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
        action.clampWhenFinished = true;
        action.setEffectiveWeight(0);
        action.play();
        action.paused = true;
        actions[layer][g] = action;
      }
    }
    current = { def, starts, actions, locks: footLock && def.events ? footSchedule(def, flClips) : null, fkSoles: new Map() };
    return current;
  }

  function finish(frames, w, evaluator = true) {
    // Shared socket of the layers that drive the hands; a socketed clip has no sword channel.
    const decisions = new Set();
    for (const [layer, frame] of Object.entries(frames)) {
      const clip = current.starts[layer].clip;
      if (frame === null || !(w.upper[layer] > 1e-12) || !socketBlocks[clip]) continue;
      decisions.add(socketAt(socketBlocks[clip], frame));
    }
    if (decisions.size > 1) throw new Error(`TRANSITION_SOCKET_CONFLICT ${[...decisions]}`);
    const socket = decisions.size ? [...decisions][0] : null;
    const sword = model.bones.sword;
    if (socket === 'bed') {
      model.root.updateMatrixWorld(true);
      sword.parent.matrixWorld.clone().invert().multiply(prepared.worldGltf).decompose(sword.position, sword.quaternion, sword.scale);
    } else if (socket === 'hand') {
      sword.position.copy(prepared.handLocal.position); sword.quaternion.copy(prepared.handLocal.quaternion); sword.scale.copy(prepared.handLocal.scale);
    }
    const layerStates = {};
    for (const [layer, frame] of Object.entries(frames)) if (frame !== null) layerStates[layer] = statesOf(manifest.clips[current.starts[layer].clip], frame, stateKeys);
    const blended = blendStates(w, layerStates);
    const state = Object.fromEntries(stateKeys.map((k) => [k, blended[k] ?? 0]));
    // Evaluator off (negative control / toggle): the helpers still follow, only the corrective morphs are cleared.
    const evaluated = evaluator ? applyCorrectives(model, rules, state) : (applyHelpers(model, rules), clearCorrectives(model, rules), null);
    return { socket, state, evaluated };
  }

  // Action times and weights at wall time t, then the mixer (lock-free pose).
  function setLayers(t) {
    const w = layerWeights(current.def, t);
    const frames = {};
    for (const [layer, start] of Object.entries(current.starts)) {
      const frame = layerFrame(current.def, lookup, layer, t);
      frames[layer] = frame;
      for (const g of GROUPS) {
        const action = current.actions[layer][g];
        action.paused = true;
        action.time = frame === null ? 0 : frame / lookup[start.clip].fps;
        action.setEffectiveWeight(frame === null ? 0 : (w[g][layer] ?? 0));
      }
    }
    restoreLegs();
    model.mixer.update(0);
    model.root.updateMatrixWorld(true);
    return { w, frames };
  }
  const v3 = new THREE.Vector3(), q4 = new THREE.Quaternion();
  const worldPoint = (bone) => bone.getWorldPosition(v3).toArray();
  const worldQuat = (bone) => { bone.getWorldQuaternion(q4).normalize(); return [q4.w, q4.x, q4.y, q4.z]; };
  function solePoints(worlds = affineFK.evaluate()) {
    return Object.fromEntries(SIDES.map((side) => [side, footLock.soleLocal[side].clone().applyMatrix4(worlds.get(model.bones[footLock.legs[side][2]])).toArray()]));
  }
  function fkSolesAt(t) {
    if (!current.fkSoles.has(t)) {
      setLayers(t);
      current.fkSoles.set(t, solePoints());
    }
    return current.fkSoles.get(t);
  }
  // Two-bone leg solve for the locked feet of the current lock-free pose; returns {side: [mode, target (glTF world)]}.
  function applyFootLock(t) {
    const worlds = affineFK.evaluate();
    const now = solePoints(worlds);
    const fkPoint = (bone) => new THREE.Vector3().setFromMatrixPosition(worlds.get(bone)).toArray();
    const fk = (side, at) => (at === t ? now[side] : current.fkSoles.get(at)[side]);
    const moved = {}, updates = [];
    for (const side of SIDES) {
      const target = soleTarget(current.def, flClips, current.locks[side], side, t, fk, footLock.forward, footLock.up);
      if (target === null) continue;
      const [thigh, shin, foot, toe] = footLock.legs[side].map((name) => model.bones[name]);
      const ankle = fkPoint(foot);
      const [kneeTurn, hipTurn] = twoBone(fkPoint(thigh), fkPoint(shin), ankle, add(ankle, sub(target, now[side])), sub(fkPoint(toe), ankle), footLock.fallback);
      const newThigh = qmul(hipTurn, worldQuat(thigh)), newShin = qmul(qmul(hipTurn, kneeTurn), worldQuat(shin));
      updates.push([thigh, qmul(qconj(worldQuat(thigh.parent)), newThigh)], [shin, qmul(qconj(newThigh), newShin)], [foot, qmul(qconj(newShin), worldQuat(foot))]);
      moved[side] = target;
    }
    for (const [bone, [w, x, y, z]] of updates) {
      legRestore.push([bone, bone.quaternion.clone()]);
      bone.quaternion.set(x, y, z, w);
    }
    if (updates.length) model.root.updateMatrixWorld(true);
    return moved;
  }

  // Stateless evaluation at wall time t (seek): lock-free soles the lock needs, the pose at t, the lock, the rest.
  function evaluateAt(t, evaluator = true, lock = true) {
    const locking = lock && current.locks !== null;
    if (locking) for (const side of SIDES) for (const at of neededTimes(current.locks[side], t)) if (at !== t) fkSolesAt(at);
    const { w, frames } = setLayers(t);
    const footTargets = locking ? applyFootLock(t) : {};
    return { t, frames, weights: w, footTargets, ...finish(frames, w, evaluator) };
  }

  // Playback as the runtime contract runs it: the controller owns an integer step clock (t = k / fps, never summed),
  // every step evaluates the scene at the clock (action times set from the layer frames, mixer.update(0)), and a pause
  // holds the clock while the steps keep evaluating. Nothing from an earlier step may carry over.
  function playTo(tEnd, fps, pause) {
    const steps = Math.round(tEnd * fps);
    let k = 0, held = 0, result = evaluateAt(0);
    while (k < steps || (pause && held < pause.steps && k / fps >= pause.at)) {
      if (pause && k / fps >= pause.at && held < pause.steps) {
        result = evaluateAt(k / fps);
        held++;
        continue;
      }
      k++;
      result = evaluateAt(k / fps);
    }
    return result;
  }

  // Diagnostic only: the mixer advances the action times itself (timeScale = layer speed), as mixer.update(dt) games do.
  // The summed time lands a hair before or after a key; three.js returns a float32 key raw at an exact key time but
  // normalised by the slerp just before it, so this path is not used by the contract and is reported, not gated.
  function playMixerTime(tEnd, fps, pause) {
    const dt = 1 / fps, steps = Math.round(tEnd * fps);
    const started = new Set();
    let clock = 0, k = 0, held = 0;
    while (k < steps || (pause && held < pause.steps && clock >= pause.at)) {
      const pausing = pause && clock >= pause.at && held < pause.steps;
      if (pausing) {
        for (const parts of Object.values(current.actions)) for (const g of GROUPS) parts[g].paused = true;
        model.mixer.update(dt);
        held++;
        continue;
      }
      const next = (k + 1) / fps;
      const w = layerWeights(current.def, next);
      for (const [layer, start] of Object.entries(current.starts)) {
        const fps0 = lookup[start.clip].fps;
        for (const g of GROUPS) {
          const action = current.actions[layer][g];
          if (start.t <= next + 1e-12) {
            if (!started.has(`${layer}:${g}`)) {
              started.add(`${layer}:${g}`);
              action.time = start.entry_frame / fps0 + (next - start.t) * start.speed - dt * start.speed;
            }
            action.paused = false;
            action.timeScale = start.speed;
            action.setEffectiveWeight(w[g][layer] ?? 0);
          } else {
            action.paused = true;
            action.setEffectiveWeight(0);
          }
        }
      }
      model.mixer.update(dt);
      clock = next;
      k++;
    }
    const w = layerWeights(current.def, clock);
    const frames = {};
    for (const [layer, start] of Object.entries(current.starts)) {
      frames[layer] = start.t <= clock + 1e-12 ? current.actions[layer].lower.time * lookup[start.clip].fps : null;
      for (const g of GROUPS) current.actions[layer][g].paused = true;
    }
    return { t: clock, frames, weights: w, ...finish(frames, w) };
  }

  // Counterexample harness only: the stock three.js scheduling. A layer starts at its first event; each switch calls
  // crossFadeTo from the previous target to the new one (fadeOut from 1, fadeIn from 0, whatever the current weights).
  function playCrossFadeTo(def, tEnd, fps) {
    setup(def);
    const dt = 1 / fps, steps = Math.round(tEnd * fps);
    for (const parts of Object.values(current.actions)) for (const g of GROUPS) parts[g].stop();
    const begun = new Set();
    const begin = (layer, t) => {
      const start = current.starts[layer], fps0 = lookup[start.clip].fps;
      for (const g of GROUPS) {
        const action = current.actions[layer][g];
        action.reset();
        action.setEffectiveWeight(1);
        action.timeScale = start.speed;
        action.time = start.entry_frame / fps0 + (t - start.t) * start.speed;
        action.play();
      }
      begun.add(layer);
    };
    let active = def.events[0].layer;
    begin(active, 0);
    for (let k = 0; k < steps; k++) {
      const clock = k / fps;
      for (const event of def.events.slice(1)) {
        if (Math.abs(event.t - clock) > 1e-9) continue;
        if (!begun.has(event.layer)) begin(event.layer, clock);
        for (const g of GROUPS) {
          const next = current.actions[event.layer][g];
          next.enabled = true;
          next.setEffectiveWeight(1);
          current.actions[active][g].crossFadeTo(next, event.blend_s, false);
        }
        active = event.layer;
      }
      model.mixer.update(dt);
    }
    const w = Object.fromEntries(GROUPS.map((g) => [g, Object.fromEntries(Object.entries(current.actions).map(([layer, parts]) => [layer, parts[g].getEffectiveWeight()]))]));
    const frames = Object.fromEntries(Object.entries(current.actions).map(([layer, parts]) => [layer, begun.has(layer) ? parts.lower.time * lookup[current.starts[layer].clip].fps : null]));
    finish(frames, w);
    return w;
  }

  function positions() {
    model.root.updateMatrixWorld(true);
    const out = [];
    const v = new THREE.Vector3();
    for (const layout of reference.mesh_layout) {
      const mesh = model.meshes[layout.name];
      for (let i = 0; i < mesh.geometry.getAttribute('position').count; i++) out.push(...mesh.getVertexPosition(i, v).applyMatrix4(mesh.matrixWorld).toArray());
    }
    return Float64Array.from(out);
  }
  const maxDiff = (a, b) => a.reduce((m, x, i) => Math.max(m, Math.abs(x - b[i])), 0);
  const evaluateAtFrames = (def, t) => Object.fromEntries(Object.keys(layerStarts(def)).map((layer) => [layer, layerFrame(def, lookup, layer, t)]));
  const webglInfo = () => {
    const gl = renderer.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info');
    return { vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR), renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER) };
  };

  async function run() {
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'z').toLowerCase();
    const started = performance.now();
    const gate = manifest.gate_m;
    const byId = Object.fromEntries(manifest.scenarios.map((s) => [s.id, s]));
    // 1. closed loop against the Blender transition reference
    const closed = [];
    for (const block of reference.blocks) {
      const def = byId[block.scenario];
      if (current?.def !== def) setup(def);
      const result = evaluateAt(block.t);
      // A loop clip's frame is compared around its seam (frame 59.999... and frame 0 of a 60-frame loop are one pose).
      const frameGap = (l, f) => {
        const info = lookup[current.starts[l].clip], d = Math.abs(f - result.frames[l]);
        return info.loop ? Math.min(d, info.frames - d) : d;
      };
      const frameDiff = Math.max(...Object.entries(block.frames).map(([l, f]) => (f === null ? (result.frames[l] === null ? 0 : Infinity) : frameGap(l, f))));
      const weightDiff = Math.max(...GROUPS.flatMap((g) => Object.entries(block.weights[g]).map(([l, w]) => Math.abs(w - (result.weights[g][l] ?? 0)))));
      const morphDiff = Math.max(0, ...Object.entries(block.morph_weights).map(([k, w]) => Math.abs(w - (result.evaluated.morph_weights[k] ?? NaN))));
      // Foot-lock targets: the same feet, the same mode, the same target point (Blender world -> glTF world).
      const blenderTargets = block.foot_targets ?? {};
      const footSides = [...new Set([...Object.keys(blenderTargets), ...Object.keys(result.footTargets)])];
      const footDiff = Math.max(0, ...footSides.map((side) => (blenderTargets[side] && result.footTargets[side]
        ? Math.max(...toGl(blenderTargets[side][1]).map((x, i) => Math.abs(x - result.footTargets[side][i]))) : Infinity)));
      closed.push({ block: block.label, socket: [block.socket, result.socket], frame_max_abs_difference: frameDiff, weight_max_abs_difference: weightDiff,
                    morph_weight_max_abs_difference: morphDiff, foot_lock: { sides: footSides, target_max_abs_difference_m: footDiff },
                    ...measure(model, reference, values, block, gate) });
    }
    // 2. determinism: the same scenario time (on each fps grid, near every reference time and after the last switch)
    //    reached by seek, by play at 30/60/120 fps and by play with a pause held inside the first fade (7 steps)
    const determinism = [];
    for (const def of manifest.scenarios.filter((s) => /^(walk-run-r|repeat-|walk-castupper-walk-r|idle-liedown-p60|sleep-getup)/.test(s.id))) {
      const fade = def.events[1], last = def.events[def.events.length - 1];
      const targets = [...def.reference_times, last.t + last.blend_s / 2];
      for (const fps of manifest.eval_fps) {
        const pauseAt = Math.round((fade.t + fade.blend_s / 2) * fps) / fps;
        for (const target of targets) {
          const t = Math.round(target * fps) / fps;
          setup(def);
          evaluateAt(t);
          const seek = positions();
          setup(def);
          const played = playTo(t, fps);
          const a = positions();
          setup(def);
          const paused = playTo(t, fps, { at: Math.min(pauseAt, t), steps: 7 });
          const b = positions();
          // Diagnostic: the mixer-advanced time path has no foot lock, so it is compared with a lock-free seek.
          setup(def);
          evaluateAt(t, true, false);
          const seekFree = positions();
          setup(def);
          playMixerTime(t, fps);
          const c = positions();
          determinism.push({ scenario: def.id, t, fps, pause_at: Math.min(pauseAt, t), play_vs_seek_m: maxDiff(a, seek), pause_resume_vs_seek_m: maxDiff(b, seek),
                             diagnostic_mixer_time_advance_vs_lock_free_seek_m: maxDiff(c, seekFree), frames: { seek: evaluateAtFrames(def, t), play: played.frames, pause_resume: paused.frames } });
        }
      }
    }
    // 3. loop seams: each loop clip's closing key against its first key (bones and every measured vertex)
    const seams = [];
    for (const [short, info] of Object.entries(manifest.clips).filter(([, i]) => i.loop)) {
      const def = { id: `seam-${short}`, events: [{ t: 0, layer: short, clip: short, entry_frame: 0, speed: 1 }] };
      setup(def);
      const ends = [];
      for (const frame of [info.frames, 0]) {
        for (const g of GROUPS) {
          const action = current.actions[short][g];
          action.setLoop(THREE.LoopOnce, 1);
          action.time = frame / info.fps;
          action.setEffectiveWeight(1);
        }
        model.mixer.update(0);
        finish({ [short]: frame % info.frames }, { upper: { [short]: 1 }, lower: { [short]: 1 } });
        ends.push({ pose: model.poseRel(), points: positions() });
      }
      const angle = Math.max(...Object.keys(ends[0].pose).map((name) => {
        const [a, b] = [ends[0].pose[name], ends[1].pose[name]];
        const dot = Math.min(1, Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]));
        return THREE.MathUtils.radToDeg(2 * Math.acos(dot));
      }));
      const move = maxDiff(ends[0].points, ends[1].points);
      seams.push({ clip: short, max_bone_deg: angle, max_point_m: move, pass: angle <= manifest.loop_seam.deg && move <= manifest.loop_seam.m });
    }
    // 4. repeated switch: weights continuous through interrupted fades (step change <= dt / blend)
    const repeated = [];
    for (const def of manifest.scenarios.filter((s) => s.id.startsWith('repeat-'))) {
      const dt = 1 / 120;
      let worst = 0;
      for (let t = 0; t <= def.sample_window[1] + 1e-9; t += dt) {
        const a = layerWeights(def, t), b = layerWeights(def, t + dt);
        for (const g of GROUPS) for (const l of new Set([...Object.keys(a[g]), ...Object.keys(b[g])])) worst = Math.max(worst, Math.abs((a[g][l] ?? 0) - (b[g][l] ?? 0)));
      }
      repeated.push({ scenario: def.id, max_weight_step: worst, bound: dt / def.blend_s, pass: worst <= dt / def.blend_s + 1e-9 });
    }
    // 5. counterexamples on disposable copies: a missing bone mapping and the required correctives switched off
    const heaviest = reference.blocks.reduce((a, b) => (Object.values(b.morph_weights).reduce((s, w) => s + w, 0) > Object.values(a.morph_weights).reduce((s, w) => s + w, 0) ? b : a));
    const def = byId[heaviest.scenario];
    setup(def);
    evaluateAt(heaviest.t, false);
    const nc1 = measure(model, reference, values, heaviest, gate);
    // The broken mapping hits the layer that carries most of the upper body at that sample.
    const brokenLayer = Object.entries(heaviest.weights.upper).sort((a, b) => b[1] - a[1])[0][0];
    const brokenClip = current.starts[brokenLayer].clip;
    const without = (part) => { const copy = part.clone(); copy.tracks = copy.tracks.filter((t) => !/^lower_armR\./.test(t.name)); return copy; };
    setup(def, { [brokenClip]: { upper: without(clips[brokenClip].parts.upper), lower: clips[brokenClip].parts.lower } });
    evaluateAt(heaviest.t);
    const nc2 = measure(model, reference, values, heaviest, gate);
    // The foot lock switched off at the locked reference sample where the lock moves the foot the most (the legs must
    // then miss the reference).
    let nc3 = null, lockedBlock = null;
    for (const block of reference.blocks.filter((b) => Object.values(b.foot_targets ?? {}).some(([mode]) => mode === 'lock'))) {
      setup(byId[block.scenario]);
      evaluateAt(block.t, true, false);
      const m = measure(model, reference, values, block, gate);
      if (!nc3 || m.max_error_m > nc3.max_error_m) [nc3, lockedBlock] = [m, block];
    }
    // Stock three.js scheduling (crossFadeTo) on the repeated switch: each interrupt restarts the fades at weight 0 / 1,
    // so the pose depends on the switch history; played to each reference time and compared with the stateless seek.
    // Both sides without the foot lock, so only the weight scheduling differs.
    const repeatDef = manifest.scenarios.find((s) => s.id === 'repeat-walk-run');
    const stateful = [];
    for (const tEnd of repeatDef ? [0.65, 0.75, 0.85] : []) {
      setup(repeatDef);
      evaluateAt(tEnd, true, false);
      const seek = positions();
      const weightsAt = playCrossFadeTo(repeatDef, tEnd, 60);
      stateful.push({ t: tEnd, crossfade_vs_seek_m: maxDiff(positions(), seek), crossfade_weights: weightsAt, controller_weights: layerWeights(repeatDef, tEnd) });
    }
    const negative = {
      NC_correctives_off: { block: heaviest.label, expected_failing_gate: 'closed_loop', detected: nc1.max_error_m > gate, max_error_m: nc1.max_error_m, worst: nc1.worst },
      NC_missing_bone_mapping: { block: heaviest.label, clip: brokenClip, removed_tracks: 'lower_arm.R', expected_failing_gate: 'closed_loop', detected: nc2.max_error_m > gate, max_error_m: nc2.max_error_m, worst: nc2.worst },
      ...(repeatDef ? { NC_stateful_crossfade: { scenario: repeatDef.id, expected_failing_gate: 'determinism', detected: stateful.some((r) => r.crossfade_vs_seek_m > manifest.determinism_gate_m),
                                                 samples: stateful } } : {}),
      ...(nc3 ? { NC_foot_lock_off: { block: lockedBlock.label, expected_failing_gate: 'closed_loop', detected: nc3.max_error_m > gate, max_error_m: nc3.max_error_m, worst: nc3.worst } } : {}),
    };
    // 6. evaluation cost on this machine (CPU: mixer + socket + helpers + correctives; GPU submit: one render)
    setup(byId[manifest.scenarios[0].id]);
    const costs = [], renders = [];
    for (let i = 0; i < 120; i++) {
      const t0 = performance.now();
      evaluateAt(0.5 + (i % 24) / 120);
      costs.push(performance.now() - t0);
      const t1 = performance.now();
      renderer.render(scene, camera);
      renders.push(performance.now() - t1);
    }
    const stats = (xs) => { const s = [...xs].sort((a, b) => a - b); return { mean_ms: xs.reduce((a, b) => a + b, 0) / xs.length, p95_ms: s[Math.floor(0.95 * (s.length - 1))], max_ms: s[s.length - 1] }; };
    // 7. images
    const images = [];
    for (const block of [reference.blocks[0], heaviest]) {
      setup(byId[block.scenario]);
      evaluateAt(block.t);
      setCamera('whole', model);
      images.push(await capture(`${stamp}-p4-${block.scenario}-${String(block.t).replace('.', 'p')}.png`));
    }
    const verdicts = {
      closed_loop_gate: closed.every((r) => r.max_error_m <= gate && r.all_blender_vertices_covered),
      closed_loop_frames_weights_match: closed.every((r) => r.frame_max_abs_difference <= 1e-6 && r.weight_max_abs_difference <= 1e-9 && r.morph_weight_max_abs_difference <= 1e-4),
      foot_lock_targets_match: closed.every((r) => r.foot_lock.target_max_abs_difference_m <= gate),
      sockets_match: closed.every((r) => r.socket[0] === r.socket[1]),
      determinism: determinism.every((r) => r.play_vs_seek_m <= manifest.determinism_gate_m && r.pause_resume_vs_seek_m <= manifest.determinism_gate_m),
      loop_seams: seams.every((r) => r.pass),
      repeated_switch_continuous: repeated.every((r) => r.pass),
      negative_controls_detected: Object.values(negative).every((r) => r.detected),
    };
    const result = {
      observed_utc: new Date().toISOString(), run: stamp, check: 'p4-runtime', gate_m: gate, gate_source: manifest.gate_source, inputs,
      runtime: { three: THREE.REVISION, user_agent: navigator.userAgent, hardware_concurrency: navigator.hardwareConcurrency, device_memory_gb: navigator.deviceMemory ?? null, webgl: webglInfo() },
      evaluation_order: ['explicit layer weights (cv1-transition.js)', 'AnimationMixer accumulation', 'inverse-bind rest affine FK (cv1-affine-fk.js; bind data read-only)', 'stance-foot lock (cv1-foot-lock.js)', 'shared sword socket', 'helper bones (rules.helpers)', 'corrective rules -> morphTargetInfluences', 'engine morph then skin'],
      closed_loop: closed, determinism, loop_seams: seams, repeated_switch: repeated, negative_controls: negative,
      cost: { evaluate: stats(costs), render_960: stats(renders), note: 'This machine in the desktop browser pane; test condition, not a performance promise.' },
      images, verdicts, pass: Object.values(verdicts).every(Boolean), measurement_ms: performance.now() - started,
    };
    result.saved_as = await save(`${stamp}-p4-results.json`, JSON.stringify(result, null, 1), 'application/json');
    return result;
  }

  // ---- interactive scene ----
  // The operable scene offers every scenario of the matrix (all blends and speeds); measurements use the manifest's.
  const all = asJson(transitionsFile).scenarios;
  for (const s of all) $('scenario').add(new Option(`${s.pair}  ${s.id}`, s.id));
  scene.add(model.root);
  let playing = null;
  function show() {
    const def = all.find((s) => s.id === $('scenario').value);
    if (current?.def !== def) {
      setup(def);
      $('time').min = 0;
      $('time').max = def.sample_window[1] + 0.3;
    }
    const t = Number($('time').value);
    const r = evaluateAt(t, $('evaluator').checked, $('footlock').checked);
    setCamera($('camera').value, model);
    $('timeOut').textContent = `${t.toFixed(3)} s`;
    const locked = Object.keys(r.footTargets).join('、') || '無';
    $('pose').textContent = `權重 ${JSON.stringify(r.weights)}\n幀 ${JSON.stringify(Object.fromEntries(Object.entries(r.frames).map(([k, v]) => [k, v === null ? null : +v.toFixed(2)])))}\n狀態 ${JSON.stringify(r.state)}  socket ${r.socket}  腳鎖定 ${locked}`;
    renderer.render(scene, camera);
  }
  for (const id of ['scenario', 'time', 'evaluator', 'footlock', 'camera']) $(id).addEventListener('input', show);
  $('camera').addEventListener('change', show);
  $('play').addEventListener('click', () => {
    if (playing) { clearInterval(playing); playing = null; $('play').textContent = '播放'; return; }
    $('play').textContent = '暫停';
    playing = setInterval(() => {
      const next = Number($('time').value) + 1 / Number($('fps').value);
      $('time').value = next > Number($('time').max) ? 0 : next;
      show();
    }, 1000 / Number($('fps').value));
  });
  $('run').addEventListener('click', async () => {
    $('run').disabled = true;
    status.className = '';
    status.textContent = '量測中…';
    try {
      const r = await run();
      window.cv1p4.lastResult = r;
      status.className = r.pass ? 'ok' : 'bad';
      const um = (m) => `${(m * 1e6).toFixed(3)} µm`;
      status.textContent = [
        `P4 runtime：${r.pass ? '通過' : '未通過'}`,
        `閉環 ${r.closed_loop.length} 點 max ${um(Math.max(...r.closed_loop.map((c) => c.max_error_m)))}（≤ ${um(r.gate_m)}）`,
        `確定性 max ${Math.max(...r.determinism.flatMap((d) => [d.play_vs_seek_m, d.pause_resume_vs_seek_m])).toExponential(2)} m`,
        `loop 接縫 ${r.loop_seams.map((s) => `${s.clip} ${s.max_bone_deg.toFixed(3)}°`).join('、')}`,
        `反例：${Object.entries(r.negative_controls).map(([k, v]) => `${k}=${v.detected ? '抓到' : '漏掉'}`).join('、')}`,
        `求值 ${r.cost.evaluate.mean_ms.toFixed(2)} ms（p95 ${r.cost.evaluate.p95_ms.toFixed(2)}）`,
        `已存：${r.saved_as}`,
      ].join('\n');
    } catch (error) {
      status.className = 'bad';
      status.textContent = `量測失敗：${error.message}`;
      console.error(error);
    } finally {
      $('run').disabled = false;
      current = null;
      show();
    }
  });
  window.cv1p4 = { manifest, reference, model, clips, setup, evaluateAt, playTo, positions };
  status.textContent = `已載入 ${Object.keys(clips).length} 個片段、${all.length} 個轉場情境、${reference.blocks.length} 個參考點。`;
  show();
}

main().catch((error) => { $('status').textContent = `載入失敗：${error.message}`; $('status').className = 'bad'; console.error(error); });
