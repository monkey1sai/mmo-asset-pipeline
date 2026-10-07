// Task-local runner: uses the existing P4 page without changing its measurement logic.
const { chromium } = require('C:/Users/IOT/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const evidenceDir = path.join(root, 'runs/qa/ro-swordsman-character-v1/v001/p4/runtime');
const url = 'http://localhost:8772/tools/runtime-qa/three/p4.html?manifest=/runs/qa/ro-swordsman-character-v1/v001/p4/run-07/merged/p4-manifest.json';
async function main() {
  const start = new Date().toISOString();
  const browser = await chromium.launch({ headless: true, channel: 'chrome', chromiumSandbox: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (error) => errors.push(String(error)));
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    await page.waitForFunction(() => /已載入|載入失敗/.test(document.getElementById('status').textContent), null, { timeout: 120000 });
    const loaded = await page.locator('#status').innerText();
    console.log(JSON.stringify({ stage: 'loaded', loaded, start }));
    if (!loaded.startsWith('已載入')) throw new Error(loaded);
    const inputCounts = await page.evaluate(() => ({ clips: Object.keys(window.cv1p4.manifest.clips).length, blocks: window.cv1p4.reference.blocks.length, visibility: document.visibilityState }));
    if (inputCounts.blocks !== 118 || inputCounts.clips !== 8) throw new Error('Unexpected run-07 input counts');
    await page.getByRole('button', { name: '執行 P4 量測並存檔', exact: true }).click();
    await page.waitForFunction(() => Boolean(window.cv1p4?.lastResult) || document.getElementById('status').textContent.startsWith('量測失敗'), null, { timeout: 240000 });
    const status = await page.locator('#status').innerText();
    const summary = await page.evaluate(() => {
      const r = window.cv1p4.lastResult;
      if (!r) return null;
      return { run: r.run, saved_as: r.saved_as, pass: r.pass, verdicts: r.verdicts, blocks: r.closed_loop.length,
        max_error_um: Math.max(...r.closed_loop.map(c => c.max_error_m)) * 1e6,
        determinism_comparisons: r.determinism.length,
        determinism_max_m: Math.max(...r.determinism.flatMap(d => [d.play_vs_seek_m, d.pause_resume_vs_seek_m])),
        negative_controls: Object.fromEntries(Object.entries(r.negative_controls).map(([k,v]) => [k,v.detected])),
        runtime: r.runtime, measurement_ms: r.measurement_ms };
    });
    if (!summary) throw new Error(status);
    const screenshot = `${summary.run}-background-browser.png`;
    await page.screenshot({ path: path.join(evidenceDir, screenshot), fullPage: true });
    const record = { schema_version: 1, start_utc: start, end_utc: new Date().toISOString(), mode: 'headless_background',
      user_instruction: '你幫我執行, 但不要用前景, 全螢幕, 打開,', url, input_counts: inputCounts,
      screenshot: `runs/qa/ro-swordsman-character-v1/v001/p4/runtime/${screenshot}`, status, summary, page_errors: errors,
      note: 'Background Chrome CPU/WebGL runtime evidence. No visible pane or foreground interaction. The page cost note mentions a desktop pane; actual execution mode is recorded here.' };
    fs.writeFileSync(path.join(evidenceDir, `${summary.run}-background-execution.json`), JSON.stringify(record, null, 2) + '\n', { flag: 'wx' });
    console.log(JSON.stringify(record));
    if (!summary.pass || errors.length) process.exitCode = 1;
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });
