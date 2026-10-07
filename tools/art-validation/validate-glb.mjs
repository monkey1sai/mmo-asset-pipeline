#!/usr/bin/env node
/** Local wrapper around the REAL optional Khronos glTF-Validator package.
 * No network, installation, repair, upload or acceptance. stdout is the report.
 * Exit 0 = structural checks completed without errors (warnings may remain).
 * Exit 2 = blocked/validator errors; exit 3 = validator unavailable/not run.
 */
import { createRequire } from 'node:module';
import { readFile, realpath, stat, lstat } from 'node:fs/promises';
import { resolve, relative, sep, isAbsolute, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const require = createRequire(import.meta.url);
const defaultRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const emit = (x, exitCode) => { console.log(JSON.stringify(x, null, 2)); process.exitCode = exitCode; };
function need(ok, code) { if (!ok) throw new Error(code); }

export function packageEntryWithin(root, entry, pathApi = { relative, isAbsolute, sep }) {
  const local = pathApi.relative(root, entry);
  return !!local && !pathApi.isAbsolute(local) && local !== '..' && !local.startsWith(`..${pathApi.sep}`);
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length === 1 && argv[0] === '--help') {
    console.log('node tools/art-validation/validate-glb.mjs --asset assets/.../model.glb [--root REPO]\nRequires an explicitly installed local gltf-validator package. No installation or network is performed.');
    return;
  }
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    need(['--root','--asset'].includes(argv[i]) && argv[i+1] && !options[argv[i]], 'ARGUMENT_INVALID');
    options[argv[i]] = argv[i+1];
  }
  const root = await realpath(options['--root'] || defaultRoot);
  const asset = options['--asset'];
  need(typeof asset === 'string' && /^(assets|deliveries)\//.test(asset) && !/[\\:\x00]/.test(asset)
       && !asset.split('/').some(s => !s || s === '.' || s === '..'), 'ASSET_PATH_SCOPE');
  let target = root;
  for (const part of asset.split('/')) {
    target = resolve(target, part);
    need(!(await lstat(target)).isSymbolicLink(), 'ASSET_SYMLINK_BLOCKED');
  }
  const actual = await realpath(target);
  const r = relative(root, actual);
  need(r && !r.startsWith(`..${sep}`) && r !== '..' && !resolve(actual).startsWith('\\\\'), 'ASSET_OUTSIDE_ROOT');
  need(extname(actual).toLowerCase() === '.glb', 'ONLY_GLB_SUPPORTED');
  const info = await stat(actual);
  need(info.isFile() && info.size > 0 && info.size <= 512 * 1024 * 1024, 'ASSET_SIZE_INVALID');
  const bytes = await readFile(actual);
  need(!bytes.subarray(0,64).toString('utf8').startsWith('version https://git-lfs.github.com/spec/v1'), 'LFS_POINTER_NOT_ASSET');
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  let validator;
  try {
    // Only the explicitly installed dependency beside this wrapper is eligible.
    // Do not execute an ancestor or NODE_PATH package with the same name.
    const modules = resolve(dirname(fileURLToPath(import.meta.url)), 'node_modules');
    const packageRoot = resolve(modules, 'gltf-validator');
    for (const directory of [modules, packageRoot]) {
      need(!(await lstat(directory)).isSymbolicLink(), 'VALIDATOR_SYMLINK_BLOCKED');
    }
    const entry = require.resolve(packageRoot);
    const actualEntry = await realpath(entry);
    need(packageEntryWithin(packageRoot, actualEntry) && packageEntryWithin(packageRoot, entry),
         'VALIDATOR_OUTSIDE_LOCAL_PACKAGE');
    let partPath = packageRoot;
    for (const part of relative(packageRoot, entry).split(sep)) {
      partPath = resolve(partPath, part);
      need(!(await lstat(partPath)).isSymbolicLink(), 'VALIDATOR_SYMLINK_BLOCKED');
    }
    validator = require(actualEntry);
  }
  catch (e) {
    if (!['ENOENT','MODULE_NOT_FOUND'].includes(e.code)) throw e;
    emit({ schema_version: 1, decision:'not_run', reason:'KHRONOS_VALIDATOR_UNAVAILABLE',
           asset, asset_sha256:sha256, art_accepted:false, technical_accepted:false }, 3);
    return;
  }
  need(typeof validator.validateBytes === 'function' && typeof validator.version === 'function', 'VALIDATOR_API_UNSUPPORTED');
  const result = await validator.validateBytes(new Uint8Array(bytes), {
    uri:'candidate.glb', maxIssues:10000,
    externalResourceFunction: () => Promise.reject(new Error('EXTERNAL_RESOURCE_ACCESS_DISABLED'))
  });
  need(result && result.issues && Number.isInteger(result.issues.numErrors), 'VALIDATOR_REPORT_INVALID');
  const issues = result.issues;
  const after = createHash('sha256').update(await readFile(actual)).digest('hex');
  need(after === sha256, 'ASSET_CHANGED_DURING_VALIDATION');
  emit({schema_version:1, decision:issues.truncated ? 'structural_report_incomplete' : (issues.numErrors ? 'structural_fail' : 'structural_checks_completed'),
    validator:'Khronos glTF-Validator', validator_version:validator.version(), asset,
    asset_sha256:sha256, input_bytes:bytes.length, errors:issues.numErrors,
    warnings:issues.numWarnings, infos:issues.numInfos, hints:issues.numHints,
    truncated:!!issues.truncated,
    issue_codes:[...new Set((issues.messages || []).map(m=>m.code))].sort(),
    external_resources:'not_loaded', art_accepted:false, technical_accepted:false,
    limitations:['Structure only; warnings require review.','No rig deformation, visual, animation naturalness, performance or target-engine certification.']
  }, (issues.numErrors || issues.truncated) ? 2 : 0);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(); }
  catch (e) {
    const code = (e instanceof Error && /^[A-Z][A-Z0-9_]+$/.test(e.message)) ? e.message : 'INPUT_OR_VALIDATOR_FAILURE';
    emit({schema_version:1,decision:'blocked',reason:code,art_accepted:false,technical_accepted:false},2);
  }
}
