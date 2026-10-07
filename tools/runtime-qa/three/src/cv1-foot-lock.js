// Character V1 stance-foot lock for transitions (no engine imports). Pure math twin of scripts/cv1_foot_lock.py;
// tests/test_cv1_foot_lock.py checks both agree. User decision A1 (authorization entry 25): while a transition fades, a
// foot that every leg layer has in stance is pinned and carried back by the blended nominal speed; the offset is released
// as the foot swings, or settled with a measurable lift when the remaining layer never lifts it. Vectors are [x, y, z];
// quaternions are [w, x, y, z].
import { layers, layerFrame, weights } from './cv1-transition.js';

export const SIDES = ['L', 'R'];
export const RELEASE_S = 0.12, SETTLE_S = 0.3, SETTLE_LIFT_M = 0.04, SETTLE_LIFT_SHARE = 0.5, HORIZON_S = 2.0, POLE_WEIGHT = 0.2;
const ACTIVE_WEIGHT = 1e-12;

// scripts/cv1_interaction.py covered / is_full
function covered(windows, t, loop) {
  for (const [start, end] of windows) {
    if (start <= end) { if (start <= t && t <= end) return true; }
    else if (loop && (t >= start || t <= end)) return true;
  }
  return false;
}
const isFull = (windows, frames) => windows.some(([start, end]) => start <= end && start <= 0 && end >= frames - 1);
const always = (clip, side) => clip.loop && isFull(clip.stance[side], clip.frames);
export const inStance = (clip, side, frame) => always(clip, side) || covered(clip.stance[side], frame, clip.loop);

function crossings(scenario, clips, layer, side, tEnd) {
  const start = layers(scenario)[layer];
  const clip = clips[start.clip];
  if (always(clip, side)) return [];
  const rate = clip.fps * start.speed, out = [];
  for (const window of clip.stance[side]) {
    for (const edge of window) {
      if (clip.loop) {
        for (let k = Math.ceil((start.entry_frame - edge) / clip.frames); ; k++) {
          const t = start.t + (edge + k * clip.frames - start.entry_frame) / rate;
          if (t > tEnd) break;
          if (t >= start.t) out.push(t);
        }
      } else if (edge <= clip.frames - 1) {
        const t = start.t + (edge - start.entry_frame) / rate;
        if (start.t <= t && t <= tEnd) out.push(t);
      }
    }
  }
  return out;
}

function state(scenario, clips, side, t) {
  const starts = layers(scenario);
  const lookup = Object.fromEntries(Object.entries(clips).map(([short, c]) => [short, { frames: c.frames, loop: c.loop, fps: c.fps }]));
  const active = Object.entries(weights(scenario, t).lower).filter(([, w]) => w > ACTIVE_WEIGHT).map(([layer]) => layer);
  const planted = active.map((layer) => inStance(clips[starts[layer].clip], side, layerFrame(scenario, lookup, layer, t)));
  return [active.length > 0 && planted.every(Boolean), active.length >= 2, planted.some(Boolean)];
}

export function horizon(scenario) {
  const events = scenario.events;
  return Math.max(events[0].t, ...events.slice(1).map((e) => e.t + e.blend_s)) + HORIZON_S;
}

export function schedule(scenario, clips) {
  const events = scenario.events, tEnd = horizon(scenario);
  const base = [...events.map((e) => e.t), ...events.slice(1).map((e) => e.t + e.blend_s), tEnd];
  const out = {};
  for (const side of SIDES) {
    const set = new Set(base);
    for (const layer of Object.keys(layers(scenario))) for (const t of crossings(scenario, clips, layer, side, tEnd)) set.add(t);
    const points = [...set].filter((p) => events[0].t <= p && p <= tEnd).sort((a, b) => a - b);
    const segments = [];
    for (let i = 0; i + 1 < points.length; i++) {
      const [a, b] = [points[i], points[i + 1]];
      if (b - a > 1e-12) segments.push([a, b, ...state(scenario, clips, side, 0.5 * (a + b))]);
    }
    const locks = [];
    let freeFrom = -Infinity;
    for (let i = 0; i < segments.length;) {
      const [a, b, allPlanted, fading] = segments[i];
      if (!(allPlanted && fading && b > freeFrom)) { i++; continue; }
      const tLock = Math.max(a, freeFrom);
      let j = i;
      while (j + 1 < segments.length && segments[j + 1][4]) j++;
      if (j === segments.length - 1) {
        const tOff = Math.max(Math.max(...segments.slice(i, j + 1).filter((s) => s[3]).map((s) => s[1])), tLock);
        locks.push({ lock: [tLock, tOff], settle: [tOff, tOff + SETTLE_S] });
        freeFrom = tOff + SETTLE_S;
      } else {
        const tOff = segments[j][1];
        locks.push({ lock: [tLock, tOff], release: [tOff, tOff + RELEASE_S] });
        freeFrom = tOff + RELEASE_S;
      }
      i = j + 1;
    }
    out[side] = locks;
  }
  return out;
}

export function modeAt(locks, t) {
  for (const entry of locks) {
    if (entry.lock[0] <= t && t < entry.lock[1]) return ['lock', entry];
    const kind = entry.release ? 'release' : 'settle';
    if (entry[kind][0] <= t && t < entry[kind][1]) return [kind, entry];
  }
  return [null, null];
}

export const endTime = (locks) => (locks.length ? Math.max(...locks.map((e) => (e.release ?? e.settle)[1])) : null);

export function neededTimes(locks, t) {
  const [kind, entry] = modeAt(locks, t);
  if (kind === null) return [];
  return kind === 'lock' ? [entry.lock[0]] : [entry.lock[0], entry[kind][0]];
}

export function speedAt(scenario, clips, t) {
  const starts = layers(scenario);
  return Object.entries(weights(scenario, t).lower).reduce((sum, [layer, w]) => sum + w * clips[starts[layer].clip].nominal_speed_m_s * starts[layer].speed, 0);
}

export function drift(scenario, clips, t0, t1) {
  if (t1 <= t0) return 0;
  const events = scenario.events;
  const set = new Set([t0, t1]);
  for (const e of events) if (t0 < e.t && e.t < t1) set.add(e.t);
  for (const e of events.slice(1)) if (t0 < e.t + e.blend_s && e.t + e.blend_s < t1) set.add(e.t + e.blend_s);
  const points = [...set].sort((a, b) => a - b);
  let total = 0;
  for (let i = 0; i + 1 < points.length; i++) total += 0.5 * (speedAt(scenario, clips, points[i]) + speedAt(scenario, clips, points[i + 1])) * (points[i + 1] - points[i]);
  return total;
}

export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a) => Math.sqrt(dot(a, a));
const angle = (a, b) => Math.atan2(norm(cross(a, b)), dot(a, b));
function axisAngle(axis, theta) {
  const s = Math.sin(0.5 * theta) / norm(axis);
  return [Math.cos(0.5 * theta), axis[0] * s, axis[1] * s, axis[2] * s];
}
export const qmul = (a, b) => [a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3], a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
  a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1], a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]];
export const qconj = (q) => [q[0], -q[1], -q[2], -q[3]];
export function rotate(q, v) {
  const w = qmul(qmul(q, [0, v[0], v[1], v[2]]), qconj(q));
  return [w[1], w[2], w[3]];
}
const smooth = (u) => u * u * (3 - 2 * u);

export function soleTarget(scenario, clips, locks, side, t, fkSole, forward, up) {
  const [kind, entry] = modeAt(locks, t);
  if (kind === null) return null;
  const tLock = entry.lock[0];
  const locked = (at) => sub(fkSole(side, tLock), scale(forward, drift(scenario, clips, tLock, at)));
  if (kind === 'lock') return locked(t);
  const [r0, r1] = entry[kind];
  const offset = sub(locked(r0), fkSole(side, r0));
  const u = (t - r0) / (r1 - r0);
  let target = add(fkSole(side, t), scale(offset, 1 - smooth(u)));
  if (kind === 'settle') {
    const horizontal = sub(offset, scale(up, dot(offset, up)));
    target = add(target, scale(up, Math.min(SETTLE_LIFT_M, SETTLE_LIFT_SHARE * norm(horizontal)) * Math.sin(Math.PI * u)));
  }
  return target;
}

const wrap = (phi) => phi - 2 * Math.PI * Math.ceil((phi - Math.PI) / (2 * Math.PI));

export function twoBone(hip, knee, ankle, ankleTarget, pole, fallbackNormal) {
  const l1 = norm(sub(knee, hip)), l2 = norm(sub(ankle, knee));
  const u = sub(hip, knee), w = sub(ankle, knee);
  let reach = norm(sub(ankleTarget, hip));
  reach = Math.min(Math.max(reach, Math.abs(l1 - l2) * (1 + 1e-9)), (l1 + l2) * (1 - 1e-9));
  let hinge = cross(u, w);
  const toward = cross(sub(ankle, hip), pole);
  if (norm(toward) > 1e-12) hinge = add(hinge, scale(toward, POLE_WEIGHT * l1 * l2 / norm(toward)));
  if (norm(hinge) < 1e-12 * l1 * l2) hinge = fallbackNormal;
  const n = scale(hinge, 1 / norm(hinge));
  const wPar = scale(n, dot(w, n));
  const wPerp = sub(w, wPar);
  const across = cross(n, wPerp);
  const c0 = dot(u, wPar), aCos = dot(u, wPerp), bSin = dot(u, across);
  const radius = Math.hypot(aCos, bSin);
  let phi = 0;
  if (radius >= 1e-15) {
    const x = Math.max(-1, Math.min(1, ((dot(u, u) + dot(w, w) - reach * reach) / 2 - c0) / radius));
    const base = Math.atan2(bSin, aCos), spread = Math.acos(x);
    const [p1, p2] = [wrap(base - spread), wrap(base + spread)];
    phi = Math.abs(p2) < Math.abs(p1) ? p2 : p1;
  }
  const kneeTurn = axisAngle(n, phi);
  const a = sub(add(knee, rotate(kneeTurn, w)), hip);
  const b = sub(ankleTarget, hip);
  const axis = cross(a, b);
  const hipTurn = norm(axis) < 1e-12 * norm(a) * norm(b) ? [1, 0, 0, 0] : axisAngle(axis, angle(a, b));
  return [kneeTurn, hipTurn];
}
