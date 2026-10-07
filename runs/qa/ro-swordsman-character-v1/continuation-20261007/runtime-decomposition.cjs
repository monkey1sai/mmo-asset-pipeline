// Diagnostic only: unchanged page and getVertexPosition. No formula/gate edits.
const { chromium } = require('C:/Users/IOT/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const out = __dirname;
async function main() {
  const browser = await chromium.launch({ headless: true, channel: 'chrome', chromiumSandbox: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('http://127.0.0.1:8774/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json');
    await page.waitForFunction(() => /已載入|載入失敗/.test(document.getElementById('status').textContent), null, { timeout: 120000 });
    const status = await page.locator('#status').innerText();
    if (!status.startsWith('已載入')) throw Error(status);
    const data = await page.evaluate(async () => {
      const THREE = await import('/tools/runtime-qa/three/node_modules/three/build/three.module.js');
      const api = window.cv1p4;
      const spec = await (await fetch('/' + api.manifest.transitions.path)).json();
      const records = [];
      for (const [sid, t] of [['combo-idle-end-b100-s1.0', .55], ['combo-idle-end-b200-s0.5', .6]]) {
        api.setup(spec.scenarios.find(s => s.id === sid));
        const pose = api.evaluateAt(t);
        const mesh = api.model.meshes.SM_RO_core;
        const geo = mesh.geometry, ids = geo.getAttribute('_cv1_id');
        const v = new THREE.Vector3(), p = geo.getAttribute('position');
        const morphs = geo.morphAttributes.position;
        const vertices = [];
        for (let i = 0; i < ids.count; i++) {
          const base = [p.getX(i), p.getY(i), p.getZ(i)];
          // Engine base class evaluates morphs before SkinnedMesh applies bone transforms.
          THREE.Mesh.prototype.getVertexPosition.call(mesh, i, v);
          const morphed = v.toArray();
          mesh.getVertexPosition(i, v);
          vertices.push({ id: ids.getX(i), base, morphed, skinned_local: v.toArray() });
        }
        const i = vertices.findIndex(v => v.id === 5297);
        const joints = geo.getAttribute('skinIndex'), weights = geo.getAttribute('skinWeight');
        const skin = [];
        for (let j = 0; j < 4; j++) {
          const index = joints.getComponent(i, j);
          skin.push({ bone: mesh.skeleton.bones[index].userData.name ?? mesh.skeleton.bones[index].name,
            weight: weights.getComponent(i, j), matrix: mesh.skeleton.bones[index].matrixWorld.clone().multiply(mesh.skeleton.boneInverses[index]).elements });
        }
        records.push({ scenario: sid, t, pose, vertices, skin, bindMatrix: mesh.bindMatrix.elements,
          bindMatrixInverse: mesh.bindMatrixInverse.elements, matrixWorld: mesh.matrixWorld.elements,
          relative: geo.morphTargetsRelative,
          shape_keys: Object.entries(mesh.morphTargetDictionary).map(([name, k]) => ({ name, value: mesh.morphTargetInfluences[k], delta_5297: [morphs[k].getX(i), morphs[k].getY(i), morphs[k].getZ(i)] })) });
      }
      return { scope: 'diagnostic_only', three: THREE.REVISION, records };
    });
    fs.writeFileSync(path.join(out, 'runtime-decomposition.json'), JSON.stringify({ ...data, errors, observed_utc: new Date().toISOString() }, null, 1), { flag: 'wx' });
    console.log(JSON.stringify({ stage: 'diagnostic_saved', records: data.records.length, errors }));
    await page.getByRole('button', { name: '執行 P4 量測並存檔', exact: true }).click();
    await page.waitForFunction(() => Boolean(window.cv1p4.lastResult) || document.getElementById('status').textContent.startsWith('量測失敗'), null, { timeout: 240000 });
    const r = await page.evaluate(() => window.cv1p4.lastResult);
    if (!r) throw Error(await page.locator('#status').innerText());
    fs.writeFileSync(path.join(out, 'baseline-runtime-summary.json'), JSON.stringify({ run: r.run, saved_as: r.saved_as, verdicts: r.verdicts, pass: r.pass, blocks: r.closed_loop.length, max_um: Math.max(...r.closed_loop.map(c => c.max_error_m)) * 1e6, errors }, null, 2), { flag: 'wx' });
    await page.screenshot({ path: path.join(out, 'baseline-runtime.png'), fullPage: true });
    console.log(JSON.stringify({ stage: 'baseline', run: r.run, pass: r.pass, verdicts: r.verdicts, blocks: r.closed_loop.length, max_um: Math.max(...r.closed_loop.map(c => c.max_error_m)) * 1e6 }));
  } finally { await browser.close(); }
}
main().catch(e => { console.error(e.stack); process.exitCode = 1; });
