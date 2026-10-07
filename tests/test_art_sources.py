"""Synthetic local intake fixtures; NOT real models, licences or service results."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import art_sources as a
import identity


class ArtSourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'repo'; self.root.mkdir()
        self.src=Path(self.tmp.name)/'sources'; self.src.mkdir()
        self.data=b'synthetic test payload; not a real GLB'
        (self.src/'asset.glb').write_bytes(self.data)
        self.request={'id':'sample-request','status':'specified'}
        ev=self.root/'runs/evidence/source-rights.md'; ev.parent.mkdir(parents=True)
        ev.write_text('Synthetic fixture only, not a real rights review.',encoding='utf8')
        self.catalog={'schema_version':1,'research_date':'2026-10-07','providers':[
          {'id':'user-owned','public_raw_policy':'per_asset_review','asset_kinds':['model','motion','material','hdri'],'source_domains':[]},
          {'id':'mixamo','public_raw_policy':'blocked','asset_kinds':['motion'],'source_domains':['mixamo.com']},
          {'id':'poly-haven','public_raw_policy':'cc0_assets_only','asset_kinds':['model','material','hdri'],'source_domains':['polyhaven.com']} ]}
        self.receipt={'schema_version':1,'id':'sample','version':'v001','request':{'id':self.request['id'],'sha256':identity.json_digest(self.request)},
          'provider':'user-owned','asset_kind':'model','source':{'url':'https://example.org/asset','revision':'fixture-1','content_class':'asset'},
          'rights':{'license_id':'fixture-not-a-license','commercial_use':'allowed','public_raw_redistribution':'allowed'},
          'review':{'status':'approved','reviewer':'synthetic-test','reviewed_on':'2026-01-01','evidence':{'path':'runs/evidence/source-rights.md','sha256':identity.file_digest(ev)}},
          'files':[{'path':'asset.glb','sha256':identity.file_digest(self.src/'asset.glb'),'bytes':len(self.data)}],'motion':None}
    def check(self,r=None):
        return a.validate_receipt(r or self.receipt,self.request,self.root,self.src,self.catalog)
    def block(self,code,change):
        r=deepcopy(self.receipt); change(r)
        with self.assertRaisesRegex(a.SourceError,'^'+code+'$'): self.check(r)
    def test_dry_run_no_asset_write(self):
        result=a.import_local(self.receipt,self.request,self.root,self.src,self.catalog)
        self.assertFalse(result['write_performed']); self.assertFalse((self.root/'assets').exists())
        self.assertFalse(result['art_accepted']); self.assertFalse(result['technical_accepted'])
    def test_explicit_apply_copies_identical_bytes_unverified(self):
        result=a.import_local(self.receipt,self.request,self.root,self.src,self.catalog,apply=True)
        out=self.root/result['destination']; self.assertEqual((out/'asset.glb').read_bytes(),self.data)
        self.assertEqual(identity.read_json(out/'source-receipt.json')['status'],'imported_unverified')
        self.assertFalse((self.root/'library').exists()); self.assertFalse((self.root/'.git').exists())
    def test_existing_destination_never_overwritten(self):
        a.import_local(self.receipt,self.request,self.root,self.src,self.catalog,apply=True)
        with self.assertRaisesRegex(a.SourceError,'DESTINATION_ALREADY_EXISTS'): self.check()
    def test_request_changed(self):
        self.request['purpose']='changed'
        with self.assertRaisesRegex(a.SourceError,'REQUEST_HASH_MISMATCH'): self.check()
    def test_request_draft_blocked(self):
        self.request['status']='draft'; self.receipt['request']['sha256']=identity.json_digest(self.request)
        with self.assertRaisesRegex(a.SourceError,'REQUEST_NOT_SPECIFIED'): self.check()
    def test_id_mismatch(self): self.block('REQUEST_ID_MISMATCH',lambda r:r['request'].update(id='other'))
    def test_unknown_provider(self): self.block('PROVIDER_UNKNOWN',lambda r:r.update(provider='nonexistent'))
    def test_unknown_provider_policy_fails_closed(self):
        self.catalog['providers'][0]['public_raw_policy']='typo'
        with self.assertRaisesRegex(a.SourceError,'PUBLIC_RAW_PROVIDER_BLOCKED'): self.check()
    def test_commercial_permission_is_not_raw_permission(self):
        self.block('PUBLIC_RAW_RIGHTS_NOT_APPROVED',lambda r:r['rights'].update(public_raw_redistribution='unknown'))
    def test_noncommercial_blocked(self): self.block('COMMERCIAL_RIGHTS_NOT_APPROVED',lambda r:r['rights'].update(commercial_use='denied'))
    def test_approval_required(self): self.block('LICENSE_REVIEW_REQUIRED',lambda r:r['review'].update(status='not_reviewed'))
    def test_evidence_changed(self):
        (self.root/'runs/evidence/source-rights.md').write_text('changed',encoding='utf8')
        with self.assertRaisesRegex(a.SourceError,'LICENSE_EVIDENCE_MISMATCH'): self.check()
    def test_future_review_blocked(self): self.block('REVIEW_DATE_INVALID',lambda r:r['review'].update(reviewed_on='2999-01-01'))
    def test_bad_dates(self):
        for d in ('2026-99-01',None,[], '20260101'):
            with self.subTest(d=d): self.block('REVIEW_DATE_INVALID',lambda r:r['review'].update(reviewed_on=d))
    def test_no_signed_url_auth_or_query(self):
        for url in ('https://example.org/a?token=secret','https://user:secret@example.org/a','http://example.org/a','https://example.org/a#private'):
            with self.subTest(url=url): self.block('SOURCE_URL_NOT_CANONICAL',lambda r:r['source'].update(url=url))
    def test_no_previews_as_assets(self): self.block('SOURCE_MUST_BE_ASSET_NOT_PREVIEW_OR_CODE',lambda r:r['source'].update(content_class='website_preview'))
    def test_cc0_must_be_asset_with_correct_license(self):
        self.receipt['provider']='poly-haven'; self.receipt['source']['url']='https://polyhaven.com/a/test'
        with self.assertRaisesRegex(a.SourceError,'CC0_LICENSE_REQUIRED'): self.check()
        self.receipt['rights']['license_id']='CC0-1.0'; self.assertEqual(self.check()['file_count'],1)
    def test_source_domain_mismatch(self):
        self.receipt['provider']='poly-haven'
        with self.assertRaisesRegex(a.SourceError,'SOURCE_DOMAIN_MISMATCH'): self.check()
    def test_source_hash_changed(self):
        (self.src/'asset.glb').write_bytes(b'changed')
        with self.assertRaisesRegex(a.SourceError,'SOURCE_FILE_HASH_MISMATCH'): self.check()
    def test_lfs_pointer_is_not_asset(self):
        (self.src/'asset.glb').write_bytes(a.LFS_HEADER+b'\noid sha256:fake\nsize 9\n')
        self.receipt['files'][0].update(sha256=identity.file_digest(self.src/'asset.glb'),bytes=(self.src/'asset.glb').stat().st_size)
        with self.assertRaisesRegex(a.SourceError,'LFS_POINTER_NOT_ASSET'): self.check()
    def test_traversal_windows_reserved_or_absolute_paths(self):
        for name in ('../asset.glb','/asset.glb','C:/asset.glb','dir\\asset.glb','con.glb','foo/../a.glb','a..b.glb'):
            with self.subTest(name=name): self.block('UNSAFE_PORTABLE_PATH',lambda r:r['files'][0].update(path=name))
    def test_scripts_and_archives_blocked(self):
        for name in ('model.py','model.exe','model.zip'):
            with self.subTest(name=name): self.block('SOURCE_FILE_TYPE_NOT_ALLOWED',lambda r:r['files'][0].update(path=name))
    def test_casefold_duplicates(self):
        self.receipt['files'].append({**self.receipt['files'][0],'path':'ASSET.glb'})
        with self.assertRaisesRegex(a.SourceError,'DUPLICATE_PORTABLE_PATH'): self.check()
    def test_symlink_source_blocked(self):
        try: (self.src/'link.glb').symlink_to(self.src/'asset.glb')
        except OSError: self.skipTest('symlink unavailable')
        self.receipt['files'][0]['path']='link.glb'
        with self.assertRaisesRegex(a.SourceError,'SYMLINK_NOT_ALLOWED'): self.check()
    def test_symlink_destination_blocked(self):
        (self.root/'assets').mkdir(); other=Path(self.tmp.name)/'outside'; other.mkdir()
        try: (self.root/'assets/raw').symlink_to(other,target_is_directory=True)
        except OSError: self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(a.SourceError,'SYMLINK_NOT_ALLOWED'): self.check()
    def test_unknown_receipt_keys_rejected(self): self.block('RECEIPT_SCHEMA',lambda r:r.update(api_key='never-log-this'))
    def test_motion_requires_metadata(self): self.block('MOTION_SCHEMA',lambda r:r.update(asset_kind='motion'))
    def test_motion_explicit_policy_is_recorded_not_verified(self):
        self.receipt['asset_kind']='motion'
        self.receipt['motion']={'origin':'mocap','clip_names':['Walk'],'fps':60,'root_motion':'in_place','source_skeleton_fingerprint':'a'*64,'contact_annotation':'needs_authoring'}
        self.assertEqual(self.check()['asset_state'],'source_checked_only')
    def test_motion_invalid_fps_or_root(self):
        self.receipt['asset_kind']='motion'; self.receipt['motion']={'origin':'mocap','clip_names':['Walk'],'fps':float('nan'),'root_motion':'in_place','source_skeleton_fingerprint':'a'*64,'contact_annotation':'needs_authoring'}
        with self.assertRaisesRegex(a.SourceError,'MOTION_FPS_INVALID'): self.check()
        self.receipt['motion']['fps']=60; self.receipt['motion']['root_motion']='automatic'
        with self.assertRaisesRegex(a.SourceError,'ROOT_MOTION_POLICY_REQUIRED'): self.check()
    def test_provider_block_even_when_receipt_claims_permission(self):
        self.receipt.update(provider='mixamo',asset_kind='motion')
        with self.assertRaisesRegex(a.SourceError,'PUBLIC_RAW_PROVIDER_BLOCKED'): self.check()
    def test_source_change_during_copy_rolls_back(self):
        real=tempfile.mkdtemp
        def mutate(*args,**kwargs):
            path=real(*args,**kwargs); (self.src/'asset.glb').write_bytes(b'x'*len(self.data)); return path
        with patch.object(a.tempfile,'mkdtemp',side_effect=mutate):
            with self.assertRaisesRegex(a.SourceError,'SOURCE_CHANGED_DURING_COPY'):
                a.import_local(self.receipt,self.request,self.root,self.src,self.catalog,apply=True)
        parent=self.root/'assets/raw/sample'
        self.assertEqual(list(parent.iterdir()),[])
    def test_existing_import_lock_blocks(self):
        parent=self.root/'assets/raw/sample'; parent.mkdir(parents=True); (parent/'.v001.source-import.lock').write_text('busy')
        with self.assertRaisesRegex(a.SourceError,'IMPORT_LOCK_EXISTS'):
            a.import_local(self.receipt,self.request,self.root,self.src,self.catalog,apply=True)
        self.assertFalse((parent/'v001').exists())
    def test_strict_json_duplicate_and_nonfinite(self):
        p=self.root/'invalid.json'
        for value in ('{"a":1,"a":2}','{"a":NaN}','{"a":1e999}','[]'):
            p.write_text(value,encoding='utf8')
            with self.subTest(value=value), self.assertRaises(identity.IdentityError): identity.read_json(p)
    def test_template_is_not_importable(self):
        t=identity.read_json(Path(__file__).resolve().parents[1]/'templates/art-source-receipt.json')
        with self.assertRaises(a.SourceError): self.check(t)
    def test_repo_catalog_loads(self):
        c=a.read_catalog(Path(__file__).resolve().parents[1]); self.assertGreaterEqual(len(c['providers']),12)
        self.assertTrue(all(p['availability']=='not_probed_this_run' for p in c['providers']))

if __name__=='__main__': unittest.main()
