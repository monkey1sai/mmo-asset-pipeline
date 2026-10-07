// Character V1 transition timeline: layer weights, layer clip frames and blended interaction states from the wall time and
// an event list (no engine imports). Pure math twin of scripts/cv1_transition.py; tests/test_cv1_transition.py checks
// both agree. Each later event fades one layer to full weight over blend_s seconds while every other layer keeps the
// share it had at the event time scaled by (1 - a); an event masked to "upper" acts on spine_01 and the bones below it.
// The weights depend only on the time and the events, so playing, pausing, resuming or seeking reach the same pose.

export const GROUPS = ['upper', 'lower'];
export const UPPER_ROOT = 'spine_01';
const STATE_GROUP = { 'grasp.R': 'upper', 'grasp.L': 'upper' };

export class TransitionError extends Error {}

export function boneGroup(name, parents) {
  const seen = new Set();
  let node = name;
  while (node !== null && node !== undefined) {
    if (node === UPPER_ROOT) return 'upper';
    if (seen.has(node)) throw new TransitionError(`PARENT_CYCLE ${name}`);
    seen.add(node);
    node = parents[node];
  }
  return 'lower';
}

export function layers(scenario) {
  const out = {};
  for (const event of scenario.events) if (!(event.layer in out)) out[event.layer] = event;
  return out;
}

export function layerFrame(scenario, clips, layer, t) {
  const start = layers(scenario)[layer];
  if (t < start.t) return null;
  const clip = clips[start.clip];
  const frame = start.entry_frame + (t - start.t) * clip.fps * start.speed;
  if (clip.loop) return ((frame % clip.frames) + clip.frames) % clip.frames;
  return Math.min(Math.max(frame, 0), clip.frames - 1);
}

function weightsUpTo(events, k, t) {
  if (k === 0) return Object.fromEntries(GROUPS.map((g) => [g, { [events[0].layer]: 1 }]));
  const event = events[k];
  if (t < event.t) return weightsUpTo(events, k - 1, t);
  const a = Math.min(1, (t - event.t) / event.blend_s);
  const frozen = weightsUpTo(events, k - 1, event.t);
  const now = weightsUpTo(events, k - 1, t);
  const out = {};
  for (const g of GROUPS) {
    if (event.mask === 'upper' && g === 'lower') { out[g] = now[g]; continue; }
    const w = {};
    for (const [layer, value] of Object.entries(frozen[g])) if (layer !== event.layer) w[layer] = value * (1 - a);
    w[event.layer] = (frozen[g][event.layer] ?? 0) * (1 - a) + a;
    out[g] = w;
  }
  return out;
}

export function weights(scenario, t) {
  return weightsUpTo(scenario.events, scenario.events.length - 1, t);
}

export function blendStates(groupWeights, layerStates) {
  const keys = [...new Set(Object.values(layerStates).flatMap((states) => Object.keys(states)))].sort();
  const out = {};
  for (const key of keys) {
    const w = groupWeights[STATE_GROUP[key] ?? 'lower'];
    // A convex mix of values in [0, 1]; the clamp only removes the rounding of weights that sum to 1 + ulp.
    out[key] = Math.min(1, Math.max(0, Object.entries(layerStates).reduce((sum, [layer, states]) => sum + (w[layer] ?? 0) * (states[key] ?? 0), 0)));
  }
  return out;
}

export function sampleTimes(tFrom, tTo, fps) {
  const round9 = (x) => Math.round(x * 1e9) / 1e9;
  const first = Math.ceil(round9(tFrom * fps)), last = Math.floor(round9(tTo * fps));
  const out = [];
  for (let k = first; k <= last; k++) out.push(k / fps);
  return out;
}
