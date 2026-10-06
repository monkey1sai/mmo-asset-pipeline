import contextlib
from copy import deepcopy
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from test_ledger import Workspace

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



class WorkspacePlanTests(unittest.TestCase):
    """plan／validate 經由 Operation ledger 判斷保留與阻擋；合成紀錄，非實際付費操作。"""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.ws = Workspace(Path(directory.name).resolve())
        self.ws.write("catalog/assets.json", catalog())

    def plan(self):
        return pipeline.plan_workspace(self.ws.root, Decimal("1"), Decimal("0.5"))

    def test_unreserved_catalog_asset_is_selected(self):
        self.assertEqual(self.plan()["selected_count"], 1)

    def test_legacy_import_reserves_catalog_asset(self):
        self.ws.legacy("bootstrap-test-prop", "downloaded", catalog_asset_id="test-prop")
        self.assertEqual(self.plan()["selected_count"], 0)

    def test_request_linked_operation_reserves_catalog_asset(self):
        for state in ("downloaded", "failed", "cancelled"):
            with self.subTest(state=state):
                self.ws.hyper3d("op-1", state, self.ws.request("prop-r01", "test-prop"))
                self.assertEqual(self.plan()["selected_count"], 0)

    def test_pending_unknown_or_invalid_operation_stops_planning(self):
        request = self.ws.request("prop-r01")
        for name, write in (("op-pending", lambda: self.ws.hyper3d("op-pending", "pending", request)),
                            ("op-unknown", lambda: self.ws.hyper3d("op-unknown", "unknown", request)),
                            ("garbled", lambda: self.ws.write("runs/hyper3d/operations/garbled.json", "{"))):
            with self.subTest(name=name):
                write()
                with self.assertRaisesRegex(ValueError, f"operation ledger blocks planning: .*{name}"):
                    self.plan()
                (self.ws.root / f"runs/hyper3d/operations/{name}.json").unlink()

    def test_legacy_runs_operations_are_not_a_ledger(self):
        # Q2：runs/*.json 舊格式已匯入帳本；plan 不再讀取，避免兩本帳。
        self.ws.write("runs/2026-10-02-bootstrap.json", {"operations": [{"operation_id": "x", "asset_id": "test-prop", "status": "unknown"}]})
        self.assertEqual(self.plan()["selected_count"], 1)

    def test_validate_cross_checks_catalog_links_and_evidence(self):
        self.assertEqual(pipeline.validate_workspace(self.ws.root), [])
        self.ws.request("orphan-r01", "missing.catalog.asset")
        self.ws.legacy("bootstrap-ghost", "downloaded", catalog_asset_id="ghost.asset")
        self.ws.write("runs/evidence.json", {"proof": "edited"})
        issues = pipeline.validate_workspace(self.ws.root)
        self.assertIn("request orphan-r01: catalog_asset_id not in catalog: missing.catalog.asset", issues)
        self.assertIn("operation bootstrap-ghost: catalog_asset_id not in catalog: ghost.asset", issues)
        self.assertIn("bootstrap-ghost: evidence hash mismatch: runs/evidence.json", issues)


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
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(pipeline.main(["inspect", "../outside.glb"]), 2)
        self.assertIn("PATH_OUTSIDE_WORKSPACE", error.getvalue())


if __name__ == "__main__":
    unittest.main()
