import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pipeline", ROOT / "tools/pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.brief = pipeline.load_json(ROOT / "examples/character.json")

    def test_examples_valid_and_plan_does_not_claim_execution(self):
        for file in (ROOT / "examples").glob("*.json"):
            brief = pipeline.load_json(file)
            self.assertEqual(pipeline.check_brief(brief), [])
            plan = pipeline.make_plan(brief)
            self.assertEqual(plan["production_status"], "UNVERIFIED")
            self.assertTrue(all(s["status"] == "NOT_STARTED" for s in plan["stages"]))
            self.assertTrue(all((ROOT / p).is_file() for p in plan["skill_paths"]))

    def test_unknown_body_rig_does_not_silently_fall_back(self):
        self.brief["rig_profile"] = "giant-new-v2"
        self.assertTrue(pipeline.check_brief(self.brief))

    def test_rigid_part_requires_parent(self):
        del self.brief["parts"][2]["parent_bone"]
        self.assertIn("rigid part: valid parent_bone required", pipeline.check_brief(self.brief))

    def test_cloak_cannot_default_to_leg_weight_transfer(self):
        del self.brief["parts"][3]["motion_solution"]
        self.assertTrue(any("secondary part" in e for e in pipeline.check_brief(self.brief)))

    def test_production_brief_requires_design_resolution(self):
        self.brief["delivery_mode"] = "production"
        self.assertTrue(any("production:" in e for e in pipeline.check_brief(self.brief)))

    def test_nonfinite_or_boolean_scale_rejected(self):
        for value in (True, 0, float("inf"), float("nan")):
            with self.subTest(value=value):
                self.brief["scale_meters"] = value
                self.assertTrue(pipeline.check_brief(self.brief))

    def test_duplicate_parts_rejected(self):
        self.brief["parts"].append(copy.deepcopy(self.brief["parts"][0]))
        self.assertTrue(any("duplicate" in e for e in pipeline.check_brief(self.brief)))

    def test_malformed_profile_types_report_error_without_crashing(self):
        self.brief["rig_profile"] = []
        self.brief["budget_profile"] = {}
        self.brief["parts"][2]["parent_bone"] = []
        self.assertTrue(pipeline.check_brief(self.brief))

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.local_path("../outside.json")

    def test_output_wont_overwrite_prior_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            pipeline.write_new(path, {"revision": 1})
            with self.assertRaises(FileExistsError):
                pipeline.write_new(path, {"revision": 2})
            self.assertEqual(pipeline.load_json(path), {"revision": 1})

    def test_vendor_lock_detects_changed_and_unlocked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "vendor/blender-skills"
            base.mkdir(parents=True)
            (base / "LICENSE").write_text("altered", encoding="utf-8")
            (base / "unlocked.py").write_text("extra", encoding="utf-8")
            pipeline.write_new(base / "source-lock.json", {"files": {"LICENSE": "0" * 64}})
            errors = pipeline.verify_vendor(root)
            self.assertTrue(any("missing or changed" in e for e in errors))
            self.assertTrue(any("unlocked file" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
