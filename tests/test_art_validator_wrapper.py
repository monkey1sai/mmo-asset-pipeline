"""Wrapper syntax, scope and missing-dependency checks; no fake official validator."""
from pathlib import Path
import os
import json
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('node'),'Node not installed')
class ValidatorWrapperTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        (self.root/'tools/art-validation').mkdir(parents=True); (self.root/'assets/raw').mkdir(parents=True)
        self.script=self.root/'tools/art-validation/validate-glb.mjs'
        shutil.copyfile(ROOT/'tools/art-validation/validate-glb.mjs',self.script)
    def run_script(self,*args):
        return subprocess.run(['node',str(self.script),*args],capture_output=True,text=True,timeout=20)
    def test_node_syntax(self):
        r=subprocess.run(['node','--check',str(self.script)],capture_output=True,text=True,timeout=20); self.assertEqual(r.returncode,0,r.stderr)
    def test_help(self):
        r=self.run_script('--help'); self.assertEqual(r.returncode,0); self.assertIn('No installation or network',r.stdout)
    def test_missing_real_validator_is_not_run(self):
        (self.root/'assets/raw/sample.glb').write_bytes(b'synthetic payload; not a geometry validation test')
        r=self.run_script('--asset','assets/raw/sample.glb')
        result=json.loads(r.stdout); self.assertEqual(r.returncode,3,result); self.assertEqual(result['decision'],'not_run')
        self.assertFalse(result['technical_accepted']); self.assertFalse(result['art_accepted'])
    def test_outside_asset_scope_blocked(self):
        r=self.run_script('--asset','../../secret.glb'); self.assertEqual(r.returncode,2)
        self.assertEqual(json.loads(r.stdout)['reason'],'ASSET_PATH_SCOPE')
    def test_lfs_pointer_rejected_before_validator(self):
        (self.root/'assets/raw/pointer.glb').write_text('version https://git-lfs.github.com/spec/v1\n')
        r=self.run_script('--asset','assets/raw/pointer.glb'); self.assertEqual(r.returncode,2)
        self.assertEqual(json.loads(r.stdout)['reason'],'LFS_POINTER_NOT_ASSET')
    def test_ancestor_package_is_not_executed(self):
        foreign=self.root/'node_modules/gltf-validator'
        foreign.mkdir(parents=True)
        (foreign/'index.js').write_text('throw new Error("ANCESTOR_PACKAGE_EXECUTED");')
        (self.root/'assets/raw/sample.glb').write_bytes(b'synthetic missing-dependency input')
        r=self.run_script('--asset','assets/raw/sample.glb')
        self.assertEqual(r.returncode,3,r.stdout)
        self.assertEqual(json.loads(r.stdout)['reason'],'KHRONOS_VALIDATOR_UNAVAILABLE')
        self.assertNotIn('ANCESTOR_PACKAGE_EXECUTED',r.stderr)
    def test_node_path_package_is_not_executed(self):
        foreign=self.root/'external_modules/gltf-validator'
        foreign.mkdir(parents=True)
        (foreign/'index.js').write_text('throw new Error("NODE_PATH_PACKAGE_EXECUTED");')
        (self.root/'assets/raw/sample.glb').write_bytes(b'synthetic missing-dependency input')
        r=subprocess.run(['node',str(self.script),'--asset','assets/raw/sample.glb'],
                         env={**os.environ,'NODE_PATH':str(foreign.parent)},capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,3,r.stdout)
        self.assertEqual(json.loads(r.stdout)['reason'],'KHRONOS_VALIDATOR_UNAVAILABLE')
        self.assertNotIn('NODE_PATH_PACKAGE_EXECUTED',r.stderr)
    def test_error_output_does_not_echo_input(self):
        r=self.run_script('--private-secret','DO_NOT_ECHO'); self.assertEqual(r.returncode,2); self.assertNotIn('DO_NOT_ECHO',r.stdout)
    def test_windows_cross_drive_and_sibling_package_entries_rejected(self):
        source=('import {packageEntryWithin} from '+json.dumps(self.script.as_uri())+';'
                'import {win32} from "node:path";'
                'const root="C:/repo/tools/art-validation/node_modules/gltf-validator";'
                'console.log(JSON.stringify(['
                'packageEntryWithin(root,root+"/index.js",win32),'
                'packageEntryWithin(root,"D:/outside/index.js",win32),'
                'packageEntryWithin(root,root+"-other/index.js",win32),'
                'packageEntryWithin(root,root+"/../outside/index.js",win32)]));')
        r=subprocess.run(['node','--input-type=module','-e',source],capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout),[True,False,False,False])

if __name__=='__main__': unittest.main()
