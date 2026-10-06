// Character V1 candidate closed loop: QA pose clip -> AnimationMixer -> final pose -> candidate corrective rules
// -> engine morph + skin, measured against the Blender reference and saved through serve.py.
// Usage: candidate.html?manifest=/runs/qa/.../runtime-manifest.json
import * as THREE from 'three';
import { evaluate, ownershipConflicts, helperConflicts } from './cv1-pose-rules.js';
import { fetchBytes, asJson, describe, save, sha256Of, loadModel, applyCorrectives, clearCorrectives, currentInfluences, maxAbsDifference, measure, prepareSocket, applySocket } from './cv1-runtime.js';

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
  if (kind === 'hands') {
    model.root.updateMatrixWorld(true);
    const centre = new THREE.Vector3();
    for (const side of ['R', 'L']) centre.add(new THREE.Vector3().setFromMatrixPosition(model.bones[`hand.${side}`].matrixWorld));
    centre.multiplyScalar(0.5);
    Object.assign(camera, { left: -0.45, right: 0.45, top: 0.45, bottom: -0.45 });
    camera.position.copy(centre).add(new THREE.Vector3(-0.8, 0.5, 2.2));
    camera.lookAt(centre);
  } else {
    Object.assign(camera, { left: -1.15, right: 1.15, top: 1.15, bottom: -1.15 });
    camera.position.set(-2.4, 1.5, 3.2);
    camera.lookAt(0, 0.9, 0);
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

async function run(app) {
  const { manifest, reference, values, rules, inputs, runtime, baked, socket } = app;
  const gate = manifest.gate_m;
  // Mixer, then the sword socket from the events (clips without sockets keep the hand attachment), then the evaluator.
  const play = (frame) => { runtime.setFrame(frame); applySocket(runtime, socket, frame); };
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'z').toLowerCase();
  const started = performance.now();
  const frameBlocks = reference.blocks.filter((b) => b.label.startsWith('all/frame-'));
  const blendBlock = reference.blocks.find((b) => b.label.startsWith('blend/'));

  // 1. runtime owner: mixer -> final pose -> evaluator -> morph + skin
  const runtimeSamples = [];
  const poseByFrame = {};
  for (const block of frameBlocks) {
    play(block.frame);
    poseByFrame[block.frame] = runtime.poseRel();
    const evaluated = applyCorrectives(runtime, rules, block.state);
    runtimeSamples.push({ frame: block.frame, motion: block.motion, level: block.level, state: block.state,
      driver_max_abs_difference_vs_blender: maxAbsDifference(evaluated.drivers, block.drivers),
      weight_max_abs_difference_vs_blender: maxAbsDifference(evaluated.morph_weights, block.morph_weights),
      active_morphs: Object.values(evaluated.morph_weights).filter((w) => w > 1e-6).length,
      ...measure(runtime, reference, values, block, gate) });
  }

  // 2. two paused actions at 0.5 / 0.5: the evaluator must read the blended pose
  runtime.setBlend(blendBlock.frames[0], blendBlock.frames[1], blendBlock.blend);
  applySocket(runtime, socket, blendBlock.frames[0]); // both blended frames share one socket (export picks them so)
  const blendEvaluated = applyCorrectives(runtime, rules, blendBlock.state);
  const blend = { frames: blendBlock.frames, state: blendBlock.state,
    driver_max_abs_difference_vs_blender: maxAbsDifference(blendEvaluated.drivers, blendBlock.drivers),
    weight_max_abs_difference_vs_blender: maxAbsDifference(blendEvaluated.morph_weights, blendBlock.morph_weights),
    ...measure(runtime, reference, values, blendBlock, gate) };

  // 3. negative controls at the frame where the correctives carry the most weight
  const heaviest = frameBlocks.reduce((a, b) => (Object.values(b.morph_weights).reduce((s, w) => s + w, 0) > Object.values(a.morph_weights).reduce((s, w) => s + w, 0) ? b : a));
  // Stale pose: the sampled pose whose corrective weights differ most from the heaviest frame's; in a slow clip the
  // neighbouring sample can be too close to tell apart, which would test nothing.
  const weightDistance = (a, b) => Object.keys(a.morph_weights).reduce((s, k) => s + Math.abs(a.morph_weights[k] - (b.morph_weights[k] ?? 0)), 0);
  const previous = frameBlocks.filter((b) => b !== heaviest).reduce((a, b) => (weightDistance(b, heaviest) > weightDistance(a, heaviest) ? b : a));
  play(heaviest.frame);
  clearCorrectives(runtime, rules);
  const nc1 = measure(runtime, reference, values, heaviest, gate);
  play(heaviest.frame);
  applyCorrectives(runtime, rules, heaviest.state, poseByFrame[previous.frame]);
  let nc2 = measure(runtime, reference, values, heaviest, gate);
  let staleSource = previous.frame;
  if (nc2.max_error_m <= gate && weightDistance(previous, heaviest) < 0.05) {
    // A near-static clip (e.g. a sleep loop) has no sampled pose different enough to test with; the rest pose is then
    // the stale input, so the control still shows that a stale pose would be caught.
    const restPose = Object.fromEntries(Object.keys(runtime.restLocal).map((name) => [name, [1, 0, 0, 0]]));
    play(heaviest.frame);
    applyCorrectives(runtime, rules, heaviest.state, restPose);
    nc2 = measure(runtime, reference, values, heaviest, gate);
    staleSource = `rest (sampled frames differ by ${weightDistance(previous, heaviest).toExponential(2)} total corrective weight)`;
  }
  const nc3 = ownershipConflicts(rules, baked.animatedMorphChannels);
  const stateKey = Object.keys(heaviest.state)[0];
  let nc4 = { raised: false, message: null };
  try {
    const broken = structuredClone(rules);
    const rotationDriver = Object.values(broken.drivers).find((d) => d.type === 'rotation_difference');
    rotationDriver.bone = `${rotationDriver.bone}_not_in_skeleton`;
    evaluate(broken, runtime.poseRel(), heaviest.state);
  } catch (error) {
    nc4 = { raised: true, message: error.message };
  }
  let nc5 = { raised: false, message: null };
  try {
    const missingState = { ...heaviest.state };
    delete missingState[stateKey];
    evaluate(rules, runtime.poseRel(), missingState);
  } catch (error) {
    nc5 = { raised: true, message: error.message };
  }
  const negativeControls = {
    NC1_evaluator_off: { frame: heaviest.frame, motion: heaviest.motion, level: heaviest.level, detected: nc1.max_error_m > gate, max_error_m: nc1.max_error_m, over_gate: nc1.over_gate, worst: nc1.worst },
    NC2_stale_pose: { frame: heaviest.frame, stale_pose_from_frame: staleSource, detected: nc2.max_error_m > gate, max_error_m: nc2.max_error_m, over_gate: nc2.over_gate, worst: nc2.worst },
    NC3_baked_clip_in_runtime_owner_mode: { detected: nc3.length > 0 || helperConflicts(rules, baked.animatedBones).length > 0, conflicting_channels: nc3.length,
      conflicting_helper_bones: helperConflicts(rules, baked.animatedBones).length },
    NC4_missing_bone: { detected: nc4.raised && /^MISSING_BONE:/.test(nc4.message ?? ''), ...nc4 },
    NC5_missing_interaction_state: { detected: nc5.raised && /^MISSING_STATE:/.test(nc5.message ?? ''), ...nc5 },
  };

  // 4. baked owner: the clip writes the morph weights, evaluator off
  const bakedSamples = [];
  // The baked variant holds morph weights on integer frames only; half-frame blocks are runtime-owner samples.
  for (const block of frameBlocks.filter((b) => b.baked_sample !== false)) {
    baked.setFrame(block.frame);
    const influences = currentInfluences(baked, rules);
    bakedSamples.push({ frame: block.frame, weight_max_abs_difference_vs_blender: maxAbsDifference(influences, block.morph_weights), ...measure(baked, reference, values, block, gate) });
  }

  // 5. images (qualitative; CPU numbers above are the measurement)
  scene.remove(baked.root);
  scene.add(runtime.root);
  const images = [];
  for (const [frame, view] of manifest.capture) {
    // Blocks are looked up by frame number: a clip reference samples only some frames.
    const block = frameBlocks.find((b) => b.frame === frame);
    if (!block) throw new Error(`CAPTURE_FRAME_NOT_SAMPLED ${frame}`);
    play(frame);
    applyCorrectives(runtime, rules, block.state);
    setCamera(view, runtime);
    images.push({ frame, view, image: await capture(`${stamp}-frame-${String(frame).padStart(3, '0')}-${view}.png`) });
  }

  const ownership = ownershipConflicts(rules, runtime.animatedMorphChannels);
  const helperOwnership = helperConflicts(rules, runtime.animatedBones);
  const all = [...runtimeSamples, blend, ...bakedSamples];
  const gl = renderer.getContext();
  const debug = gl.getExtension('WEBGL_debug_renderer_info');
  const verdicts = {
    runtime_owner_gate: runtimeSamples.every((r) => r.max_error_m <= gate),
    blend_gate: blend.max_error_m <= gate,
    baked_owner_gate: bakedSamples.every((r) => r.max_error_m <= gate),
    all_blender_vertices_covered: all.every((r) => r.all_blender_vertices_covered),
    rule_weights_match_blender: runtimeSamples.every((r) => r.weight_max_abs_difference_vs_blender <= 1e-4) && blend.weight_max_abs_difference_vs_blender <= 1e-4,
    runtime_owner_clip_has_no_owned_morph_channel: ownership.length === 0,
    runtime_owner_clip_has_no_helper_bone_channel: helperOwnership.length === 0,
    negative_controls_all_detected: Object.values(negativeControls).every((c) => c.detected),
    // With sockets the runtime owns the sword placement: its clip must not animate the sword joint.
    ...(socket ? { runtime_owner_clip_has_no_sword_channel: !runtime.animatedBones.includes('sword') } : {}),
  };
  const result = {
    observed_utc: new Date().toISOString(), run: stamp, check: 'runtime-closed-loop', gate_m: gate, gate_source: manifest.gate_source,
    runtime: { engine: 'three.js', revision: THREE.REVISION, user_agent: navigator.userAgent, webgl_version: gl.getParameter(gl.VERSION), webgl_renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null },
    inputs, evaluation_order: ['AnimationMixer.update', 'sword socket from the clip events (manifest.sword_socket; hand attachment otherwise)', 'helper bones follow their sources (rules.helpers)', 'final bone local rotations, rest-relative', 'rule evaluator writes morphTargetInfluences', 'updateMatrixWorld', 'engine morph then skin'],
    measurement: 'SkinnedMesh.getVertexPosition (morph then skin) x matrixWorld, glTF->Blender axes, against the Blender-evaluated position of the same original vertex ID. CPU values, not GPU-frame evidence.',
    clip_key_times_s: runtime.clipKeyTimes, rest_from_inverse_bind_vs_node_default_max_deg: runtime.restDisagreementDeg,
    verdicts, pass: Object.values(verdicts).every(Boolean),
    summary: { runtime_owner_max_error_m: Math.max(...runtimeSamples.map((r) => r.max_error_m)), blend_max_error_m: blend.max_error_m,
               baked_owner_max_error_m: Math.max(...bakedSamples.map((r) => r.max_error_m)), frames: runtimeSamples.length,
               max_rule_weight_difference: Math.max(...runtimeSamples.map((r) => r.weight_max_abs_difference_vs_blender), blend.weight_max_abs_difference_vs_blender) },
    runtime_owner_samples: runtimeSamples, blend_sample: blend, baked_owner_samples: bakedSamples, negative_controls: negativeControls, images,
    measurement_ms: Math.round(performance.now() - started),
  };
  result.saved_as = await save(`${stamp}-runtime-results.json`, JSON.stringify(result, null, 1), 'application/json');
  return result;
}

async function main() {
  const status = $('status');
  const manifestUrl = new URLSearchParams(location.search).get('manifest');
  if (!manifestUrl) throw new Error('MISSING_MANIFEST_PARAMETER');
  const manifestFile = await fetchBytes(manifestUrl);
  const manifest = asJson(manifestFile);
  const [referenceFile, binFile, rulesFile] = await Promise.all([fetchBytes(`/${manifest.reference.path}`), fetchBytes(`/${manifest.reference_binary.path}`), fetchBytes(`/${manifest.rules.path}`)]);
  for (const [file, expected] of [[referenceFile, manifest.reference], [binFile, manifest.reference_binary], [rulesFile, manifest.rules]]) {
    if (file.sha256 !== expected.sha256) throw new Error(`HASH_MISMATCH ${file.path}`);
  }
  const reference = asJson(referenceFile), rules = asJson(rulesFile);
  const values = new Float64Array(binFile.buffer);
  status.textContent = '載入 GLB…';
  const runtime = await loadModel(`/${manifest.glb.runtime_owner.path}`, reference.fps);
  const baked = await loadModel(`/${manifest.glb.baked_owner.path}`, reference.fps);
  if (runtime.file.sha256 !== manifest.glb.runtime_owner.sha256 || baked.file.sha256 !== manifest.glb.baked_owner.sha256) throw new Error('GLB_HASH_MISMATCH');
  const harness = {};
  for (const name of ['candidate.html', 'src/candidate.js', 'src/cv1-runtime.js', 'src/cv1-pose-rules.js']) harness[name] = describe(await fetchBytes(`/tools/runtime-qa/three/${name}`));
  const inputs = { manifest: describe(manifestFile), harness, reference: describe(referenceFile), reference_binary: describe(binFile), rules: describe(rulesFile),
                   glb: { runtime_owner: runtime.file, baked_owner: baked.file } };
  const frames = reference.blocks.filter((b) => b.label.startsWith('all/frame-'));
  // Before any mixer update: the socket calibration reads the sword joint at rest.
  const socket = prepareSocket(runtime, manifest.sword_socket ?? null);
  const app = { manifest, reference, values, rules, inputs, runtime, baked, socket, busy: false };
  window.cv1 = app;
  scene.add(runtime.root);
  $('frame').max = frames.length - 1;
  setCamera('whole', runtime);

  function show() {
    if (app.busy) return;
    const frame = Number($('frame').value), block = frames[frame];
    runtime.setFrame(frame);
    applySocket(runtime, socket, frame);
    if ($('evaluator').checked) applyCorrectives(runtime, rules, block.state); else clearCorrectives(runtime, rules);
    setCamera($('camera').value, runtime);
    $('frameOut').textContent = frame;
    $('pose').textContent = block.motion ? `${block.motion}（${block.level === 'typical' ? '典型' : '極端'}）  狀態 ${JSON.stringify(block.state)}` : '靜止姿勢';
    renderer.render(scene, camera);
  }
  for (const id of ['frame', 'evaluator', 'camera']) $(id).addEventListener('input', show);
  $('camera').addEventListener('change', show);
  $('run').addEventListener('click', async () => {
    $('run').disabled = true;
    app.busy = true;
    status.className = '';
    status.textContent = '量測中…';
    try {
      const result = await run(app);
      app.lastResult = result;
      const um = (m) => `${(m * 1e6).toFixed(3)} µm`;
      status.className = result.pass ? 'ok' : 'bad';
      status.textContent = [
        `閉環量測（≤ ${um(result.gate_m)}）：${result.pass ? '通過' : '未通過'}`,
        `runtime 求值器 ${result.summary.frames} 幀 max ${um(result.summary.runtime_owner_max_error_m)}`,
        `混合取樣 max ${um(result.summary.blend_max_error_m)}`,
        `烘焙 clip max ${um(result.summary.baked_owner_max_error_m)}`,
        `規則權重與 Blender 最大差 ${result.summary.max_rule_weight_difference.toExponential(2)}`,
        `反例全部被抓到：${result.verdicts.negative_controls_all_detected ? '是' : '否'}`,
        `已存：${result.saved_as}`,
      ].join('\n');
    } catch (error) {
      status.className = 'bad';
      status.textContent = `量測失敗：${error.message}`;
      console.error(error);
    } finally {
      app.busy = false;
      $('run').disabled = false;
      show();
    }
  });
  status.textContent = `已載入 ${frames.length} 幀；修形通道 ${rules.channels.length}；runtime clip 的 morph 軌數 ${runtime.animatedMorphChannels.length}，烘焙 clip ${baked.animatedMorphChannels.length}。`;
  show();
}

main().catch((error) => { $('status').textContent = `載入失敗：${error.message}`; $('status').className = 'bad'; console.error(error); });
