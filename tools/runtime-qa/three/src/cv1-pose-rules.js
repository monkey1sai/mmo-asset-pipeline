// Character V1 corrective rule evaluation: final joint pose and interaction state -> morph weights.
// Pure math twin of scripts/cv1_pose_rules.py (no engine imports); tests/test_cv1_pose_rules.py checks both agree.
// Quaternions are [w, x, y, z], rest-relative local rotations of the named bone.

const OWNERS = new Set(['runtime_evaluator', 'baked_clip']);

export class RuleError extends Error {}

function unit(q) {
  if (!Array.isArray(q) || q.length !== 4) throw new RuleError('INVALID_QUATERNION');
  const n = Math.hypot(...q.map(Number));
  if (!Number.isFinite(n) || n < 1e-12) throw new RuleError('INVALID_QUATERNION');
  return q.map((c) => Number(c) / n);
}

export function quatAngle(a, b) {
  const ua = unit(a), ub = unit(b);
  const dot = Math.abs(ua[0] * ub[0] + ua[1] * ub[1] + ua[2] * ub[2] + ua[3] * ub[3]);
  return 2 * Math.acos(Math.min(1, dot));
}

export function rotationDifferenceProgress(qRel, qTarget) {
  const span = quatAngle([1, 0, 0, 0], qTarget);
  if (span < 1e-9) throw new RuleError('DEGENERATE_TARGET');
  return Math.min(1, Math.max(0, 1 - quatAngle(qRel, qTarget) / span));
}

export function hat(p, prev, at, next) {
  const open = next === null || next === undefined;
  if (!(prev < at) || (!open && !(at < next))) throw new RuleError('INVALID_HAT');
  if (p <= prev) return 0;
  if (p <= at) return (p - prev) / (at - prev);
  if (open) return 1;
  return Math.max(0, (next - p) / (next - at));
}

const mul = (a, b) => [
  a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
  a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
const conj = (q) => [q[0], -q[1], -q[2], -q[3]];

// Slerp from identity toward q by t along the shortest path.
function share(q, t) {
  let [w, x, y, z] = unit(q);
  if (w < 0) [w, x, y, z] = [-w, -x, -y, -z];
  const half = Math.acos(Math.min(1, w)), s = Math.sin(half);
  if (s < 1e-12) return [1, 0, 0, 0];
  const k = Math.sin(t * half) / s;
  return [Math.cos(t * half), x * k, y * k, z * k];
}

// Remove the twist about the bone's own axis (local +Y) from a rest-relative local rotation.
export function swingOnly(q) {
  const [w, x, y, z] = unit(q);
  const n = Math.hypot(w, y);
  if (n < 1e-12) return [w, x, y, z];
  return mul([w, x, y, z], conj([w / n, 0, y / n, 0]));
}

// The twist part of q about a unit axis (swing-twist decomposition, q = swing * twist).
export function twistAbout(q, axis) {
  const [w, x, y, z] = unit(q);
  const d = x * axis[0] + y * axis[1] + z * axis[2];
  const n = Math.hypot(w, d);
  if (n < 1e-12) return [1, 0, 0, 0];
  return [w / n, (d * axis[0]) / n, (d * axis[1]) / n, (d * axis[2]) / n];
}

function rotate(q, v) {
  return mul(mul(q, [0, v[0], v[1], v[2]]), conj(q)).slice(1);
}

// Rest-relative local rotations of the helper bones; restLocal: bone -> rest rotation relative to its parent, parents: bone -> parent name.
// twist_only keeps just the source's turn about the helper's own axis (its local +Y seen from the parent).
export function helperRotations(rules, poseRel, restLocal, parents) {
  const out = {};
  for (const helper of rules.helpers ?? []) {
    if (!(helper.bone in restLocal)) throw new RuleError(`MISSING_BONE:${helper.bone}`);
    let total = [1, 0, 0, 0];
    for (const follow of helper.follow) {
      if (!(follow.source in poseRel) || !(follow.source in restLocal)) throw new RuleError(`MISSING_BONE:${follow.source}`);
      if (parents[follow.source] !== parents[helper.bone]) throw new RuleError(`HELPER_NOT_SIBLING:${helper.bone}`);
      const rest = unit(restLocal[follow.source]);
      const local = follow.swing_only ? swingOnly(poseRel[follow.source]) : unit(poseRel[follow.source]);
      let inParent = mul(mul(rest, local), conj(rest));
      if (follow.twist_only) inParent = twistAbout(inParent, rotate(unit(restLocal[helper.bone]), [0, 1, 0]));
      total = mul(share(inParent, Number(follow.share)), total);
    }
    const rest = unit(restLocal[helper.bone]);
    out[helper.bone] = unit(mul(mul(conj(rest), total), rest));
  }
  return out;
}

// Helper bones that an animation clip also keys.
export function helperConflicts(rules, animatedBones) {
  validateRules(rules);
  const animated = new Set(animatedBones);
  return (rules.helpers ?? []).map((h) => h.bone).filter((bone) => animated.has(bone)).sort();
}

export function validateRules(rules) {
  if (!rules || rules.schema_version !== 1) throw new RuleError('RULES_SCHEMA');
  const { drivers, channels } = rules;
  if (!drivers || typeof drivers !== 'object' || !Array.isArray(channels) || !channels.length) throw new RuleError('RULES_SCHEMA');
  for (const driver of Object.values(drivers)) {
    if (driver.type === 'rotation_difference') {
      if (typeof driver.bone !== 'string') throw new RuleError('RULES_SCHEMA');
      unit(driver.target_quaternion_wxyz);
    } else if (driver.type === 'state') {
      if (typeof driver.key !== 'string') throw new RuleError('RULES_SCHEMA');
    } else if (driver.type === 'product') {
      // Product of other, non-product drivers: active only when all of them are.
      const simple = (name) => ['rotation_difference', 'state'].includes(drivers[name]?.type);
      if (!Array.isArray(driver.of) || driver.of.length < 2 || !driver.of.every(simple)) throw new RuleError('INVALID_PRODUCT_DRIVER');
    } else {
      throw new RuleError('UNKNOWN_DRIVER_TYPE');
    }
  }
  const helpers = rules.helpers ?? [];
  if (!Array.isArray(helpers)) throw new RuleError('RULES_SCHEMA');
  const helperBones = new Set();
  for (const helper of helpers) {
    const valid = helper && typeof helper.bone === 'string' && !helperBones.has(helper.bone) && helper.owner === 'runtime_evaluator' && Array.isArray(helper.follow) && helper.follow.length
      && helper.follow.every((f) => f && typeof f.source === 'string' && Number(f.share) >= 0 && Number(f.share) <= 1 && ['undefined', 'boolean'].includes(typeof f.swing_only)
        && ['undefined', 'boolean'].includes(typeof f.twist_only) && !(f.swing_only && f.twist_only));
    if (!valid) throw new RuleError('INVALID_HELPER');
    helperBones.add(helper.bone);
  }
  if (helpers.some((h) => h.follow.some((f) => helperBones.has(f.source)))) throw new RuleError('HELPER_CHAIN');
  const seen = new Set();
  for (const channel of channels) {
    const key = `${channel.mesh}\u0000${channel.morph}`;
    if (typeof channel.mesh !== 'string' || !channel.mesh || typeof channel.morph !== 'string' || !channel.morph || seen.has(key)) {
      throw new RuleError('DUPLICATE_OR_INVALID_CHANNEL');
    }
    seen.add(key);
    if (!OWNERS.has(channel.owner) || !(channel.driver in drivers)) throw new RuleError('CHANNEL_OWNER_OR_DRIVER');
    const curve = channel.curve || {};
    if (curve.type === 'hat') hat(0, curve.prev, curve.at, curve.next);
    else if (curve.type !== 'linear') throw new RuleError('UNKNOWN_CURVE_TYPE');
  }
}

export function driverValues(rules, poseRel, state) {
  const out = {};
  for (const [name, driver] of Object.entries(rules.drivers)) {
    if (driver.type === 'rotation_difference') {
      if (!(driver.bone in poseRel)) throw new RuleError(`MISSING_BONE:${driver.bone}`);
      out[name] = rotationDifferenceProgress(poseRel[driver.bone], driver.target_quaternion_wxyz);
    } else if (driver.type === 'state') {
      if (!(driver.key in state)) throw new RuleError(`MISSING_STATE:${driver.key}`);
      const value = Number(state[driver.key]);
      if (!(value >= 0 && value <= 1)) throw new RuleError(`STATE_OUT_OF_RANGE:${driver.key}`);
      out[name] = value;
    }
  }
  for (const [name, driver] of Object.entries(rules.drivers)) {
    if (driver.type === 'product') out[name] = driver.of.reduce((value, factor) => value * out[factor], 1);
  }
  return out;
}

// Returns [{mesh, morph, weight}] for channels owned by the runtime evaluator.
export function evaluate(rules, poseRel, state) {
  validateRules(rules);
  const values = driverValues(rules, poseRel, state);
  return rules.channels
    .filter((channel) => channel.owner === 'runtime_evaluator')
    .map((channel) => {
      const p = values[channel.driver], curve = channel.curve;
      return { mesh: channel.mesh, morph: channel.morph, weight: curve.type === 'linear' ? p : hat(p, curve.prev, curve.at, curve.next) };
    });
}

// Channels written by an animation clip while the rules assign them to the runtime evaluator.
export function ownershipConflicts(rules, animatedChannels) {
  validateRules(rules);
  const animated = new Set(animatedChannels.map(([mesh, morph]) => `${mesh}\u0000${morph}`));
  return rules.channels
    .filter((channel) => channel.owner === 'runtime_evaluator' && animated.has(`${channel.mesh}\u0000${channel.morph}`))
    .map((channel) => [channel.mesh, channel.morph])
    .sort();
}
