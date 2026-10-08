from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_motion import validate_export_channels,validate_source_clip


class ExportOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.doc={'nodes':[{'name':'body'},{'name':'secondary'}], 'skins':[{'joints':[0,1]}],
                  'animations':[{'channels':[{'target':{'node':0,'path':'rotation'}}]}]}

    def check(self):return validate_export_channels(self.doc,{'body'},{'secondary'})

    def test_body_only(self):
        self.assertEqual(self.check()['animated_bones'],['body'])

    def test_secondary_channel_rejected(self):
        self.doc['animations'][0]['channels'].append({'target':{'node':1,'path':'rotation'}})
        with self.assertRaisesRegex(ValueError,'EXPORT_UNOWNED_BONE_TRACK'):self.check()

    def test_multiple_and_empty_clips_rejected(self):
        self.doc['animations']*=2
        with self.assertRaisesRegex(ValueError,'EXPORT_CLIP_COUNT'):self.check()
        self.doc['animations']=[{'channels':[]}]
        with self.assertRaisesRegex(ValueError,'EXPORT_CLIP_COUNT'):self.check()

    def test_unknown_and_invalid_target_rejected(self):
        target=self.doc['animations'][0]['channels'][0]['target']
        for node in (-1,2,False,None):
            target['node']=node
            with self.assertRaisesRegex(ValueError,'EXPORT_CHANNEL_TARGET'):self.check()

    def test_duplicate_channel_rejected(self):
        self.doc['animations'][0]['channels']*=2
        with self.assertRaisesRegex(ValueError,'EXPORT_DUPLICATE_CHANNEL'):self.check()

    def test_ambiguous_bone_names_rejected(self):
        self.doc['nodes'].append({'name':'body'})
        with self.assertRaisesRegex(ValueError,'RIG_BONE_AMBIGUOUS'):self.check()

    def test_writer_conflict_and_missing_bone_rejected(self):
        with self.assertRaisesRegex(ValueError,'BONE_WRITER_CONFLICT'):
            validate_export_channels(self.doc,{'body'},{'body'})
        with self.assertRaisesRegex(ValueError,'RIG_BONE_MISSING'):
            validate_export_channels(self.doc,{'missing'},{'secondary'})

    def test_source_clip_count_and_receipt_binding(self):
        self.doc['animations'][0]['name']='clip'
        validate_source_clip(self.doc,['clip'])
        with self.assertRaisesRegex(ValueError,'SOURCE_CLIP_BINDING'):validate_source_clip(self.doc,['other'])
        self.doc['animations']*=2
        with self.assertRaisesRegex(ValueError,'SOURCE_CLIP_COUNT'):validate_source_clip(self.doc,['clip'])
        self.doc['animations']=[]
        with self.assertRaisesRegex(ValueError,'SOURCE_CLIP_COUNT'):validate_source_clip(self.doc,[])
