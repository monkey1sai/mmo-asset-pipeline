const { chromium } = require('C:/Users/IOT/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome', chromiumSandbox: true });
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:8774/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json');
    await page.waitForFunction(() => Boolean(window.cv1p4), null, { timeout: 120000 });
    const data = await page.evaluate(async () => {
      const THREE = await import('/tools/runtime-qa/three/node_modules/three/build/three.module.js');
      const fl = await import('/tools/runtime-qa/three/src/cv1-foot-lock.js');
      const {loadModel} = await import('/tools/runtime-qa/three/src/cv1-runtime.js');
      const api = window.cv1p4, spec = await (await fetch('/' + api.manifest.transitions.path)).json();
      const fresh = await loadModel('/' + api.manifest.clips[api.manifest.base].glb.path, api.manifest.clips[api.manifest.base].fps);
      fresh.root.updateMatrixWorld(true);
      const soleLocal = Object.fromEntries(['L','R'].map(side => {
        const s = api.manifest.foot_lock.sole_rest_world_blender[side];
        return [side, new THREE.Vector3(s[0],s[2],-s[1]).applyMatrix4(fresh.bones[`foot.${side}`].matrixWorld.clone().invert())];
      }));
      const records = [];
      for (const [sid, t] of [['combo-idle-end-b100-s1.0', .55], ['combo-idle-end-b200-s0.5', .6]]) {
        api.setup(spec.scenarios.find(s => s.id === sid));
        const locked = api.evaluateAt(t), fk = api.evaluateAt(t, true, false);
        const v = new THREE.Vector3();
        const point = name => api.model.bones[name].getWorldPosition(v).toArray();
        const inputs = ['L', 'R'].map(side => {
          const [hip, knee, ankle, toe] = api.manifest.foot_lock.legs[side].map(point);
          const foot = api.model.bones[api.manifest.foot_lock.legs[side][2]];
          // Same sole local derivation as the P4 loader: frozen rest-world centroid -> inverse rest foot.
          const bind = api.model.skeleton.boneInverses[api.model.skeleton.bones.indexOf(foot)].clone().invert();
          const s = api.manifest.foot_lock.sole_rest_world_blender[side];
          const sole = soleLocal[side].clone().applyMatrix4(foot.matrixWorld).toArray();
          const target = fl.add(ankle, fl.sub(locked.footTargets[side], sole));
          const args = [hip, knee, ankle, target, fl.sub(toe, ankle), [-1, 0, 0]];
          return { side, inputs: args, output: fl.twoBone(...args), sole };
        });
        const unlocked = Object.fromEntries(['root', 'pelvis', ...['L','R'].flatMap(s => ['upper_leg','lower_leg','foot','toe'].map(n => `${n}.${s}`))].map(name => {
          const bone = api.model.bones[name];
          return [name, { quaternion: bone.quaternion.toArray(), norm: bone.quaternion.length(), position: bone.position.toArray(), scale: bone.scale.toArray(), matrixWorld: bone.matrixWorld.elements,
            restLocal: api.model.restLocal[name]?.toArray(), basis_quaternion: api.model.poseRel()[name],
            restWorldTRS: fresh.bones[name].matrixWorld.elements,
            restWorldInverseBind: api.model.skeleton.boneInverses[api.model.skeleton.bones.indexOf(bone)].clone().invert().elements }];
        }));
        records.push({ scenario: sid, t, inputs, unlocked });
      }
      return records;
    });
    fs.writeFileSync(path.join(__dirname, 'runtime-solver-03.json'), JSON.stringify(data, null, 1), { flag: 'wx' });
    console.log('SOLVER_DIAGNOSTIC_SAVED');
  } finally { await browser.close(); }
})().catch(e => { console.error(e.stack); process.exitCode = 1; });
