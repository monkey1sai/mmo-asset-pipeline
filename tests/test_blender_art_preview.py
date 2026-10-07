"""Offline protocol/GLB preflight tests; no Blender renderer is simulated."""
from pathlib import Path
from copy import deepcopy
import json
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import blender_art_preview as p
import identity


class PreviewPreflightTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.request={'id':'sample','status':'specified'}
        self.protocol=identity.read_json(Path(__file__).resolve().parents[1]/'templates/art-preview-protocol.json')
        self.protocol.update(status='frozen',request={'id':'sample','sha256':identity.json_digest(self.request)})
    def glb(self,doc):
        data=json.dumps(doc).encode('utf8'); data+=b' '*((-len(data))%4)
        path=self.root/'sample.glb'; path.write_bytes(struct.pack('<4sIIII',b'glTF',2,20+len(data),len(data),0x4E4F534A)+data); return path
    def test_valid_frozen_protocol(self): self.assertEqual(p.validate_protocol(self.protocol,self.request),self.protocol)
    def test_template_is_not_frozen(self):
        self.protocol['status']='draft'
        with self.assertRaisesRegex(p.PreviewError,'PROTOCOL_NOT_FROZEN'): p.validate_protocol(self.protocol,self.request)
    def test_request_change_invalidates_protocol(self):
        self.request['purpose']='changed'
        with self.assertRaisesRegex(p.PreviewError,'REQUEST_BINDING_MISMATCH'): p.validate_protocol(self.protocol,self.request)
    def test_nan_scale_invalid(self):
        self.protocol['camera']['orthographic_scale_m']=float('nan')
        with self.assertRaisesRegex(p.PreviewError,'CAMERA_SCALE_INVALID'): p.validate_protocol(self.protocol,self.request)
    def test_duplicate_views_invalid(self):
        self.protocol['camera']['azimuths_deg']=[0,0]
        with self.assertRaisesRegex(p.PreviewError,'CAMERA_VIEWS_INVALID'): p.validate_protocol(self.protocol,self.request)
    def test_render_resolution_budget(self):
        self.protocol['render']['width']=99999
        with self.assertRaisesRegex(p.PreviewError,'RENDER_SIZE_INVALID'): p.validate_protocol(self.protocol,self.request)
    def test_wrong_coordinates_invalid(self):
        self.protocol['coordinate_system']='Y_up'
        with self.assertRaisesRegex(p.PreviewError,'COORDINATE_SYSTEM_REQUIRED'): p.validate_protocol(self.protocol,self.request)
    def test_embedded_glb_uri_screen_only(self):
        self.assertEqual(p.embedded_glb_only(self.glb({'asset':{'version':'2.0'},'buffers':[{'byteLength':0}]}))['asset']['version'],'2.0')
    def test_all_uri_resources_blocked(self):
        for uri in ('../secret.png','https://example.org/texture.png','data:image/png;base64,AA=='):
            with self.subTest(uri=uri),self.assertRaisesRegex(p.PreviewError,'EXTERNAL_OR_DATA_URI_NOT_SUPPORTED'):
                p.embedded_glb_only(self.glb({'asset':{'version':'2.0'},'images':[{'uri':uri}]}))
    def test_unknown_extensions_require_review(self):
        with self.assertRaisesRegex(p.PreviewError,'GLB_EXTENSION_REQUIRES_REVIEW'):
            p.embedded_glb_only(self.glb({'asset':{'version':'2.0'},'extensionsUsed':['EXT_meshopt_compression']}))
    def test_non_glb_or_lfs_pointer_rejected(self):
        path=self.root/'pointer.glb'; path.write_text('version https://git-lfs.github.com/spec/v1')
        with self.assertRaisesRegex(p.PreviewError,'INPUT_NOT_GLB'): p.embedded_glb_only(path)
    def test_required_only_unknown_extension_rejected(self):
        with self.assertRaisesRegex(p.PreviewError,'GLB_EXTENSION_REQUIRES_REVIEW'):
            p.embedded_glb_only(self.glb({'extensionsRequired':['EXT_unreviewed']}))
    def test_undeclared_nested_unknown_extension_rejected(self):
        with self.assertRaisesRegex(p.PreviewError,'GLB_EXTENSION_REQUIRES_REVIEW'):
            p.embedded_glb_only(self.glb({'nodes':[{'extensions':{'EXT_unreviewed':{}}}]}))
    def test_known_extension_must_be_declared(self):
        for doc in ({'extensionsRequired':['KHR_materials_unlit']},
                    {'materials':[{'extensions':{'KHR_materials_unlit':{}}}]}):
            with self.subTest(doc=doc),self.assertRaisesRegex(p.PreviewError,'GLB_EXTENSION_DECLARATION_INVALID'):
                p.embedded_glb_only(self.glb(doc))
    def test_declared_known_extension_allowed(self):
        doc={'extensionsUsed':['KHR_materials_unlit'],'extensionsRequired':['KHR_materials_unlit'],
             'materials':[{'extensions':{'KHR_materials_unlit':{}}}]}
        self.assertEqual(p.embedded_glb_only(self.glb(doc)),doc)
    def test_bad_length_rejected(self):
        path=self.glb({'asset':{'version':'2.0'}}); path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaisesRegex(p.PreviewError,'GLB_HEADER_INVALID'): p.embedded_glb_only(path)
    def test_preview_scope_protects_existing_work(self):
        with self.assertRaisesRegex(p.PreviewError,'PATH_SCOPE'): p.scoped_path(self.root,'README.md',[("runs","qa")],False)
    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(p.PreviewError,'PATH_SCOPE'): p.scoped_path(self.root,'runs/qa/../../secret',[("runs","qa")],False)
    def test_symlink_inside_root_rejected(self):
        (self.root/'assets').mkdir(); (self.root/'assets/sample.glb').write_bytes(b'fixture')
        try: (self.root/'assets/link.glb').symlink_to(self.root/'assets/sample.glb')
        except OSError: self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(p.PreviewError,'SYMLINK_NOT_ALLOWED'): p.scoped_path(self.root,'assets/link.glb',[("assets",)])

if __name__=='__main__': unittest.main()
