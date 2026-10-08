import sys,unittest,json,struct,copy,tempfile,io,contextlib
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cv1_restore_glb_weights import patch_vertices,RestoreError,split_glb
import cv1_restore_glb_weights as module
import workbench,identity


def fixture(edit=None):
    binary=struct.pack('<9f',0,0,0,1,0,0,0,1,0)+bytes([0,0,0,0]*3)+struct.pack('<12f',*([1,0,0,0]*3))
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':12},{'buffer':0,'byteOffset':48,'byteLength':48}],
         'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':3},{'bufferView':1,'componentType':5121,'type':'VEC4','count':3},{'bufferView':2,'componentType':5126,'type':'VEC4','count':3}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0,'JOINTS_0':1,'WEIGHTS_0':2}}]}],
         'nodes':[{'name':'mesh','mesh':0,'skin':0},{'name':'root'},{'name':'cloth'}],'skins':[{'joints':[1,2]}]}
    if edit:edit(doc)
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*(-len(encoded)%4)
    return struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary


class SparseWeightPatchTests(unittest.TestCase):
    def test_preserves_every_nonselected_byte(self):
        blob=fixture();out,report=patch_vertices(blob,'mesh',[{'vertex':1,'weights':{'cloth':.75,'root':.25}}])
        _,start,_=split_glb(blob);allowed=set(range(start+40,start+44))|set(range(start+64,start+80))
        self.assertEqual(len(blob),len(out));self.assertTrue(all(a==b for i,(a,b) in enumerate(zip(blob,out)) if i not in allowed))
        self.assertEqual(struct.unpack_from('<4B',out,start+40),(1,0,0,0))
        self.assertEqual(struct.unpack_from('<4f',out,start+64),(.75,.25,0.,0.))
        self.assertTrue(report['all_other_bytes_identical']);self.assertEqual(report['acceptance'],'NOT_RUN')

    def test_noop_keeps_exact_bytes(self):
        blob=fixture();out,report=patch_vertices(blob,'mesh',[{'vertex':0,'weights':{'root':1}}])
        self.assertEqual(blob,out);self.assertEqual(report['changed_bytes'],0)

    def test_illegal_vertex_and_duplicates(self):
        for value in [-1,3,True,1.5]:
            with self.subTest(value=value),self.assertRaises(RestoreError):patch_vertices(fixture(),'mesh',[{'vertex':value,'weights':{'cloth':1}}])
        with self.assertRaises(RestoreError):patch_vertices(fixture(),'mesh',[{'vertex':0,'weights':{'cloth':1}}]*2)

    def test_invalid_weights(self):
        for weights in [{},{'missing':1},{'root':True},{'root':float('nan')},{'root':float('inf')},{'root':0},{'root':-.1},{'root':.8},{'root':1.1}]:
            with self.subTest(weights=weights),self.assertRaises(RestoreError):patch_vertices(fixture(),'mesh',[{'vertex':0,'weights':weights}])

    def test_empty_and_malformed_rows(self):
        for rows in [[],None,[{'vertex':0}],[{'vertex':0,'weights':{'root':1},'hidden':1}]]:
            with self.assertRaises(RestoreError):patch_vertices(fixture(),'mesh',rows)

    def test_ambiguous_node_bones_and_invalid_skin(self):
        edits=[lambda d:d['nodes'].append({'name':'mesh'}),lambda d:d['nodes'][2].update(name='root'),lambda d:d['nodes'][0].update(skin=-1),lambda d:d['skins'][0].update(joints=[1,True])]
        for edit in edits:
            with self.assertRaises(RestoreError):patch_vertices(fixture(edit),'mesh',[{'vertex':0,'weights':{'root':1}}])

    def test_aliased_views_accessors_and_shared_mesh(self):
        edits=[lambda d:d['bufferViews'][0].update(byteOffset=36),lambda d:d['accessors'].append(copy.deepcopy(d['accessors'][1])),lambda d:d['nodes'].append({'name':'instance','mesh':0,'skin':0})]
        for edit in edits:
            with self.assertRaises(RestoreError):patch_vertices(fixture(edit),'mesh',[{'vertex':0,'weights':{'root':1}}])

    def test_bounds_interleaving_normalized_and_extra_weights(self):
        edits=[lambda d:d['bufferViews'][2].update(byteLength=32),lambda d:d['bufferViews'][1].update(byteStride=8),lambda d:d['accessors'][2].update(normalized=True),lambda d:d['meshes'][0]['primitives'][0]['attributes'].update(WEIGHTS_1=2)]
        for edit in edits:
            with self.assertRaises(RestoreError):patch_vertices(fixture(edit),'mesh',[{'vertex':0,'weights':{'root':1}}])

    def test_multiple_primitive_invalid_attribute_and_length(self):
        edits=[lambda d:d['meshes'][0]['primitives'].append(copy.deepcopy(d['meshes'][0]['primitives'][0])),lambda d:d['meshes'][0]['primitives'][0]['attributes'].update(POSITION=-1)]
        for edit in edits:
            with self.assertRaises(RestoreError):patch_vertices(fixture(edit),'mesh',[{'vertex':0,'weights':{'root':1}}])
        with self.assertRaises(RestoreError):patch_vertices(fixture()+b'1234','mesh',[{'vertex':0,'weights':{'root':1}}])


class SparseWeightCliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'source';self.source.mkdir();(self.source/'mesh.glb').write_bytes(fixture())
        self.request=workbench.make_draft('fixture','local prototype','rigged_character')
        self.assertEqual(workbench.validate_request(self.request),[])
        (self.root/'request.json').write_text(json.dumps(self.request),encoding='utf-8')
        evidence=self.root/'review.md';evidence.write_text('Synthetic scope declaration, not authenticated approval.',encoding='utf-8')
        self.profile={'request_sha256':identity.json_digest(self.request),'source_sha256':identity.file_digest(self.source/'mesh.glb'),
          'mesh':'mesh','changes':[{'vertex':1,'weights':{'cloth':1}}],
          'review':{'status':'local_prototype_accepted','reviewer':'synthetic-not-human-approval','original_vertex_ids':[1],
                    'evidence':{'path':'review.md','sha256':identity.file_digest(evidence)}}}

    def run_cli(self,destination='assets/processed/fixture/v001/out.glb'):
        (self.root/'profile.json').write_text(json.dumps(self.profile),encoding='utf-8')
        args=['--request','request.json','--source-root',str(self.source),'--asset','mesh.glb','--sha256',self.profile['source_sha256'],
              '--profile','profile.json','--out',destination]
        with patch.object(module,'__file__',str(self.root/'scripts/tool.py')),contextlib.redirect_stdout(io.StringIO()):
            return module.patch_main(args)

    def test_new_output_report_and_no_overwrite(self):
        self.assertEqual(self.run_cli(),0)
        out=self.root/'assets/processed/fixture/v001/out.glb';saved=out.read_bytes()
        report=identity.read_json(out.with_suffix('.json'))
        self.assertFalse(report['game_ready']);self.assertEqual(report['review_status'],'DECLARED_NOT_AUTHENTICATED')
        with self.assertRaisesRegex(RestoreError,'OUTPUT_EXISTS'):self.run_cli()
        self.assertEqual(out.read_bytes(),saved)

    def test_report_collision_has_no_partial_glb(self):
        target=self.root/'assets/processed/fixture/v001/out.json';target.parent.mkdir(parents=True);target.write_text('old')
        with self.assertRaisesRegex(RestoreError,'OUTPUT_EXISTS'):self.run_cli()
        self.assertFalse(target.with_suffix('.glb').exists());self.assertEqual(target.read_text(),'old')

    def test_output_scope_and_traversal(self):
        for destination in ['runs/qa/out.glb','../out.glb','assets/processed/out.fbx']:
            with self.assertRaises(ValueError):self.run_cli(destination)
        self.assertFalse((self.root/'assets').exists())

    def test_review_mask_binding_and_drift(self):
        for alter in [lambda p:p.update(request_sha256='0'*64),lambda p:p['review'].update(status='pending'),
                      lambda p:p['review'].update(original_vertex_ids=[0]),lambda p:p['review']['evidence'].update(sha256='0'*64),
                      lambda p:p.update(review=None)]:
            original=copy.deepcopy(self.profile);alter(self.profile)
            with self.assertRaises(ValueError):self.run_cli()
            self.profile=original
        self.assertFalse((self.root/'assets').exists())

    def test_source_drift_and_external_resource_rejected(self):
        source=self.source/'mesh.glb';source.write_bytes(source.read_bytes()+b'x')
        with self.assertRaisesRegex(RestoreError,'SOURCE_DRIFT'):self.run_cli()
        source.write_bytes(fixture(lambda d:d.update(images=[{'uri':'../private.png'}])))
        self.profile['source_sha256']=identity.file_digest(source)
        with self.assertRaisesRegex(ValueError,'EXTERNAL_OR_DATA_URI'):self.run_cli()
        self.assertFalse((self.root/'assets').exists())


if __name__=='__main__':unittest.main()
