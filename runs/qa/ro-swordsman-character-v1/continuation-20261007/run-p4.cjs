// Exact P4 regression; async dispatch avoids automation click-ack timeout during synchronous measurement.
const { chromium } = require('C:/Users/IOT/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const label = process.argv[2];
if (!/^(baseline|candidate)$/.test(label)) throw Error('EXPECTED_BASELINE_OR_CANDIDATE');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome', chromiumSandbox: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('http://127.0.0.1:8774/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json');
    await page.waitForFunction(() => Boolean(window.cv1p4), null, { timeout: 120000 });
    await page.evaluate(() => { setTimeout(() => document.getElementById('run').click(), 0); return true; });
    console.log('P4_STARTED ' + label);
    await page.waitForFunction(() => Boolean(window.cv1p4.lastResult) || document.getElementById('status').textContent.startsWith('量測失敗'), null, { timeout: 300000 });
    const r = await page.evaluate(() => window.cv1p4.lastResult);
    if (!r) throw Error(await page.locator('#status').innerText());
    const record = { label, run: r.run, saved_as: r.saved_as, verdicts: r.verdicts, pass: r.pass, blocks: r.closed_loop.length, max_um: Math.max(...r.closed_loop.map(c => c.max_error_m)) * 1e6, runtime: r.runtime, errors, mode: 'headless_background_local_harness' };
    fs.writeFileSync(path.join(__dirname, label + '-runtime-summary.json'), JSON.stringify(record, null, 2), { flag: 'wx' });
    await page.screenshot({ path: path.join(__dirname, label + '-runtime.png'), fullPage: true });
    console.log(JSON.stringify(record));
  } finally { await browser.close(); }
})().catch(e => { console.error(e.stack); process.exitCode = 1; });
