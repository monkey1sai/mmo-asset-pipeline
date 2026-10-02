from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location("pipeline", Path(__file__).resolve().parents[1] / "scripts" / "pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def catalog():
    return {"schema_version": 1, "assets": [{
        "id": "test-prop", "project": "shared", "name": "道具", "category": "prop", "priority": 0,
        "demand": "source_backed", "prompt": "One prop", "target_triangles": 1000,
        "texture_px": 1024, "size_m": [1, 1, 1], "pivot": "base", "requires_rig": False,
        "postprocess": ["check pivot"], "sources": [{"path": "C:/repo/source.ts", "line": 1, "head": "a" * 40}]
    }]}


def glb(doc=None):
    if doc is None:
        doc = {"asset": {"version": "2.0"}, "accessors": [{"count": 3}],
               "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}
    payload = json.dumps(doc).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<4sII", b"glTF", 2, len(payload) + 20) + struct.pack("<II", len(payload), 0x4E4F534A) + payload


class PlanningTests(unittest.TestCase):
    def test_catalog_valid(self):
        self.assertEqual(pipeline.validate_catalog(catalog()), [])

    def test_duplicate_rejected(self):
        data = catalog()
        data["assets"].append(deepcopy(data["assets"][0]))
        self.assertTrue(any("duplicate" in e for e in pipeline.validate_catalog(data)))

    def test_unsafe_asset_id_rejected(self):
        for aid in ("../escape", "a..b", "a/b", "A-B"):
            data = catalog()
            data["assets"][0]["id"] = aid
            self.assertTrue(pipeline.validate_catalog(data))

    def test_unbounded_credit_rejected(self):
        for value in ("NaN", "Infinity", "-1", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                pipeline.credit_amount(value)

    def test_plan_reports_demand_gap_without_repeating(self):
        plan = pipeline.make_plan(catalog(), Decimal("205"), Decimal("0.5"), set())
        self.assertEqual(plan["selected_count"], 1)
        self.assertEqual(plan["unallocated_credits"], "204.5")
        self.assertTrue(plan["demand_gap"])

    def test_reserved_and_reuse_excluded(self):
        self.assertEqual(pipeline.make_plan(catalog(), Decimal("1"), Decimal("0.5"), {"test-prop"})["selected_count"], 0)
        data = catalog()
        data["assets"][0]["demand"] = "reuse"
        self.assertEqual(pipeline.make_plan(data, Decimal("1"), Decimal("0.5"), set())["selected_count"], 0)

    def test_unknown_submission_reserved(self):
        runs = [{"operations": [{"operation_id": "unique", "asset_id": "test-prop", "status": "unknown"}]}]
        self.assertEqual(pipeline.reserved_assets(runs), {"test-prop"})

    def test_duplicate_operation_fails_closed(self):
        runs = [{"operations": [{"operation_id": "dup", "asset_id": "one", "status": "submitted"}, {"operation_id": "dup", "asset_id": "two", "status": "submitted"}]}]
        with self.assertRaises(ValueError):
            pipeline.reserved_assets(runs)

    def test_budget_boundary(self):
        plan = pipeline.make_plan(catalog(), Decimal("0.49"), Decimal("0.5"), set())
        self.assertEqual(plan["selected_count"], 0)
        self.assertEqual(plan["estimated_cost"], "0.0")

    def test_nonfinite_dimensions_rejected(self):
        data = catalog()
        data["assets"][0]["size_m"] = [1, float("nan"), 1]
        self.assertTrue(pipeline.validate_catalog(data))

    def test_new_customer_does_not_require_core_edit(self):
        data = catalog()
        data["assets"][0]["project"] = "new-customer"
        self.assertEqual(pipeline.validate_catalog(data), [])
        self.assertEqual(pipeline.make_plan(data, Decimal("1"), Decimal("0.5"), set(), "new-customer")["selected_count"], 1)

    def test_standalone_brief_without_git_history(self):
        data = catalog()
        asset = data["assets"][0]
        asset["project"] = None
        asset["sources"] = [{"kind": "brief", "reference": "requests/my-rock.json#brief"}]
        self.assertEqual(pipeline.validate_catalog(data), [])
        self.assertEqual(pipeline.make_plan(data, Decimal("1"), Decimal("0.5"), set(), "standalone")["selected_count"], 1)

    def test_repo_evidence_still_requires_git_line_and_head(self):
        data = catalog()
        data["assets"][0]["sources"] = [{"kind": "repo", "path": "C:/repo/source.ts", "line": 1}]
        self.assertTrue(pipeline.validate_catalog(data))

    def test_typed_source_needs_traceable_reference(self):
        for source in ({"kind": "brief"}, {"kind": "unknown", "reference": "x"}):
            data = catalog()
            data["assets"][0]["sources"] = [source]
            self.assertTrue(pipeline.validate_catalog(data))

    def test_4k_and_untextured_requests(self):
        for size in (4096, None):
            data = catalog()
            data["assets"][0]["texture_px"] = size
            self.assertEqual(pipeline.validate_catalog(data), [])
        for size in (0, -1, float("inf"), True):
            data = catalog()
            data["assets"][0]["texture_px"] = size
            self.assertTrue(pipeline.validate_catalog(data))

    def test_unknown_customer_filter_is_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, "unknown project"):
            pipeline.make_plan(catalog(), Decimal("1"), Decimal("0.5"), set(), "missing-customer")

    def test_delivery_and_accepted_states_stay_reserved(self):
        for status in ("delivered", "art_accepted", "technical_accepted"):
            runs = [{"operations": [{"operation_id": "one", "asset_id": "test-prop", "status": status}]}]
            reserved = pipeline.reserved_assets(runs)
            self.assertEqual(pipeline.make_plan(catalog(), Decimal("1"), Decimal("0.5"), reserved)["selected_count"], 0)

    def test_pending_completed_and_failed_need_review_before_replanning(self):
        for status in ("pending", "completed", "failed", "cancelled"):
            runs = [{"operations": [{"operation_id": "one", "asset_id": "test-prop", "status": status}]}]
            self.assertEqual(pipeline.reserved_assets(runs), {"test-prop"})

    def test_unknown_or_missing_status_fails_closed(self):
        for status in (None, "unexpected", []):
            runs = [{"operations": [{"operation_id": "one", "asset_id": "test-prop", "status": status}]}]
            with self.assertRaisesRegex(ValueError, "status"):
                pipeline.reserved_assets(runs)


class GlbTests(unittest.TestCase):
    def test_inventory_not_runtime_pass(self):
        report = pipeline.inspect_glb(glb())
        self.assertEqual(report["triangles_per_mesh_copy"], 1)
        self.assertEqual(report["status"], "structural_inventory_only")
        self.assertIn("unity_import", report["not_verified"])

    def test_truncated_and_wrong_magic_rejected(self):
        for data in (b"glTF", b"FAIL" + glb()[4:], glb()[:-1]):
            with self.subTest(data=data[:12]), self.assertRaises(ValueError):
                pipeline.inspect_glb(data)

    def test_empty_model_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.inspect_glb(glb({"asset": {"version": "2.0"}}))

    def test_invalid_accessor_rejected(self):
        doc = {"asset": {"version": "2.0"}, "accessors": [], "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}]}
        with self.assertRaises(ValueError):
            pipeline.inspect_glb(glb(doc))

    def test_buffer_exceeding_bin_rejected(self):
        doc = json.loads(glb()[20:])
        doc["buffers"] = [{"byteLength": 128}]
        with self.assertRaises(ValueError):
            pipeline.inspect_glb(glb(doc))

    def test_external_texture_reported_without_fetch(self):
        doc = json.loads(glb()[20:])
        doc["images"] = [{"uri": "texture.png"}]
        report = pipeline.inspect_glb(glb(doc))
        self.assertEqual(report["external_images"], 1)
        self.assertTrue(report["warnings"])

    def test_outside_workspace_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.workspace_path("../outside.glb")


if __name__ == "__main__":
    unittest.main()
