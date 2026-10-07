import copy
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'glb_bounds', Path(__file__).resolve().parents[1] / 'tools' / 'glb_bounds.py')
bounds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounds)


def document(nodes=None):
    return {
        'nodes': nodes or [{'name': 'mesh', 'mesh': 0}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'material': 0}]}],
        'accessors': [{'type': 'VEC3', 'componentType': 5126, 'count': 3,
                       'min': [0, 0, 0], 'max': [1, 1, 1]}],
        'materials': [{}],
    }


class GlbBoundsTests(unittest.TestCase):
    def test_flat_output_preserves_local_fields_and_counts(self):
        node = {'name': 'mesh', 'mesh': 0, 'translation': [1, 2, 3], 'scale': [2, 3, 4]}
        result = bounds.node_bounds(document([node]), node)
        self.assertEqual(result, {'node': 'mesh', 'triangles': 1, 'materials': 1,
                                  'translation': [1, 2, 3], 'rotation': [0, 0, 0, 1],
                                  'scale': [2, 3, 4], 'min': [1, 2, 3],
                                  'max': [3, 5, 7], 'size': [2, 3, 4]})

    def test_parent_translation_is_included(self):
        doc = document([{'translation': [10, 0, 0], 'children': [1]},
                        {'mesh': 0, 'translation': [1, 0, 0]}])
        result = bounds.node_bounds(doc, doc['nodes'][1])
        self.assertEqual(result['min'], [11, 0, 0])
        self.assertEqual(result['max'], [12, 1, 1])
        self.assertEqual(result['translation'], [1, 0, 0])

    def test_multilevel_parent_after_child_and_unreferenced_nodes(self):
        doc = document([{'mesh': 0, 'translation': [1, 0, 0]},
                        {'translation': [10, 0, 0], 'children': [0]},
                        {'translation': [100, 0, 0], 'children': [1]},
                        {'mesh': 0, 'translation': [-5, 0, 0]}])
        doc.update({'scene': 0, 'scenes': [{'nodes': [2]}]})
        self.assertEqual(bounds.node_bounds(doc, doc['nodes'][0])['min'], [111, 0, 0])
        self.assertEqual(bounds.node_bounds(doc, doc['nodes'][3])['min'], [-5, 0, 0])

    def test_parent_nonuniform_scale_rotation_and_negative_child_scale(self):
        q = [0, 0, math.sqrt(0.5), math.sqrt(0.5)]
        doc = document([{'translation': [10, 0, 0], 'scale': [2, 3, 1],
                         'rotation': q, 'children': [1]},
                        {'mesh': 0, 'rotation': q, 'scale': [-1, 1, 1],
                         'translation': [1, 0, 0]}])
        # Child: (x,y,z)->(1-y,-x,z); parent: ->(10+3x,2-2y,z).
        result = bounds.node_bounds(doc, doc['nodes'][1])
        self.assertEqual(result['min'], [10, 0, 0])
        self.assertEqual(result['max'], [13, 2, 1])

    def test_no_intermediate_reboxing_in_rotated_chain(self):
        q = [0, 0, math.sin(math.pi / 8), math.cos(math.pi / 8)]
        qi = [0, 0, -q[2], q[3]]
        doc = document([{'rotation': q, 'children': [1]}, {'mesh': 0, 'rotation': qi}])
        result = bounds.node_bounds(doc, doc['nodes'][1])
        self.assertEqual(result['size'], [1, 1, 1])

    def test_invalid_hierarchies_are_rejected(self):
        for nodes in ([{'children': [1]}, {'mesh': 0, 'children': [0]}],
                      [{'children': [2]}, {'children': [2]}, {'mesh': 0}],
                      [{'children': [1, 1]}, {'mesh': 0}],
                      [{'mesh': 0, 'children': [1]}],
                      [{'mesh': 0, 'children': [True]}]):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                bounds.node_transform_chains(document(nodes))

    def test_unsupported_deformation_and_primitive_modes_are_rejected(self):
        base = document()
        mutations = [lambda d: d['nodes'][0].update({'matrix': [1] * 16}),
                     lambda d: d['nodes'][0].update({'skin': 0}),
                     lambda d: d['nodes'][0].update({'weights': [0]}),
                     lambda d: d['meshes'][0].update({'weights': [0]}),
                     lambda d: d['meshes'][0]['primitives'][0].update({'targets': []}),
                     lambda d: d['meshes'][0]['primitives'][0].update({'mode': 1})]
        for mutate in mutations:
            doc = copy.deepcopy(base)
            mutate(doc)
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                bounds.node_bounds(doc, doc['nodes'][0])

    def test_invalid_extrema_transforms_and_counts_are_rejected(self):
        mutations = [lambda d: d['accessors'][0].pop('min'),
                     lambda d: d['accessors'][0].update({'min': [math.nan, 0, 0]}),
                     lambda d: d['accessors'][0].update({'max': [math.inf, 1, 1]}),
                     lambda d: d['accessors'][0].update({'min': [2, 0, 0]}),
                     lambda d: d['accessors'][0].update({'count': 4}),
                     lambda d: d['accessors'][0].update({'componentType': 5123}),
                     lambda d: d['nodes'][0].update({'scale': [1, 1]}),
                     lambda d: d['nodes'][0].update({'translation': [True, 0, 0]}),
                     lambda d: d['nodes'][0].update({'rotation': [0, 0, 0, 2]})]
        for mutate in mutations:
            doc = document()
            mutate(doc)
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                bounds.node_bounds(doc, doc['nodes'][0])


if __name__ == '__main__':
    unittest.main()
