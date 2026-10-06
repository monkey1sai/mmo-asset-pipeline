"""workspace_plan：plan CLI 的機械草稿（prepare spec、evidence 與品質 ledger 骨架）；合成需求，不提交生成。"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from test_ledger import Workspace
from test_workbench import specified, workbench

PREPARE_FIELDS = {"operation_id", "request", "images", "output_directory", "parameters", "authorization"}


class PlanDraftTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.ws = Workspace(Path(directory.name).resolve())

    def request(self, route="generate", **spec):
        request = specified()
        request["production"]["route"] = route
        request["spec"].update(spec)
        self.ws.write(f"requests/{request['id']}.json", request)
        return request

    def plan(self, request):
        return workbench.workspace_plan(request, f"requests/{request['id']}.json", self.ws.root)

    def draft(self, request, index=0):
        return self.plan(request)["creation_workflow"]["jobs"][index]["prepare_spec_draft"]

    def test_generate_draft_fills_only_mechanical_fields(self):
        request = self.request(target_triangles=1500)
        job = self.plan(request)["creation_workflow"]["jobs"][0]
        draft = job["prepare_spec_draft"]
        self.assertEqual(set(draft), PREPARE_FIELDS)
        self.assertEqual(draft["operation_id"], f"{request['id']}-r01")
        self.assertEqual(draft["request"], f"requests/{request['id']}.json")
        self.assertEqual(draft["output_directory"], f"assets/raw/{request['id']}/v001")
        self.assertEqual(draft["parameters"], {"tier": None, "mesh_mode": "Raw", "quality_override": 1500,
                                               "geometry_file_format": "glb", "material": None, "prompt": None})
        self.assertEqual((draft["images"], draft["authorization"]), (None, None))
        self.assertTrue(any("tier" in note for note in job["draft_notes"]))

    def test_numbering_skips_ledger_ids_prepared_plans_and_existing_outputs(self):
        request = self.request()
        rid = request["id"]
        self.ws.hyper3d(f"{rid}-r01", "downloaded", f"requests/{rid}.json")
        self.ws.write(f"runs/hyper3d/plans/{rid}-r02.json", {"prepared": "not submitted"})
        (self.ws.root / f"assets/raw/{rid}/v001").mkdir(parents=True)
        draft = self.draft(request)
        self.assertEqual((draft["operation_id"], draft["output_directory"]), (f"{rid}-r03", f"assets/raw/{rid}/v002"))

    def test_split_route_drafts_one_spec_per_part(self):
        request = self.request("split_then_generate", parts=[{"id": "frame", "pivot": "底面", "motion": None},
                                                             {"id": "door", "pivot": "鉸鏈", "motion": {"kind": "rotation", "axis": "+Y", "range_deg": [0, 90]}}])
        jobs = self.plan(request)["creation_workflow"]["jobs"]
        rid = request["id"]
        self.assertEqual([(j["prepare_spec_draft"]["operation_id"], j["prepare_spec_draft"]["output_directory"]) for j in jobs],
                         [(f"{rid}.frame-r01", f"assets/raw/{rid}/frame/v001"), (f"{rid}.door-r01", f"assets/raw/{rid}/door/v001")])

    def test_format_face_count_and_tapose_derivation(self):
        cases = [(["blend", "fbx"], 100, False, "fbx", 500), (["blend"], 5_000_000, False, None, 1_000_000), (["glb"], None, True, "glb", None)]
        for formats, triangles, rig, fmt, faces in cases:
            with self.subTest(formats=formats):
                request = self.request(target_triangles=triangles, requires_rig=rig)
                request["delivery"]["formats"] = formats
                params = self.draft(request)["parameters"]
                self.assertEqual((params["geometry_file_format"], params["quality_override"], params.get("TAPose")),
                                 (fmt, faces, True if rig else None))

    def test_evidence_skeleton_on_every_route_never_passes(self):
        for route in ("reuse", "review_existing", "modify", "generate"):
            with self.subTest(route=route):
                request = self.request(route)
                plan = self.plan(request)
                skeleton = plan["evidence_skeleton"]
                self.assertEqual(set(skeleton["checks"]), {c["id"] for c in plan["required_checks"]})
                self.assertTrue(all(c == {"status": "not_run", "method": "", "artifacts": []} for c in skeleton["checks"].values()))
                self.assertEqual(skeleton["request_sha256"], plan["request_sha256"])
                self.assertEqual(workbench.assess(request, skeleton, self.ws.root)["decision"], "not_ready")
                self.assertEqual("creation_workflow" in plan, route == "generate")
                self.assertNotIn("quality_ledger_skeleton", plan)

    def test_quality_request_gets_ledger_skeleton_that_stops(self):
        request = self.request()
        request["quality"] = json.loads((Path(__file__).resolve().parents[1] / "templates/quality-contract.json").read_text(encoding="utf-8"))
        plan = self.plan(request)
        ledger = plan["quality_ledger_skeleton"]
        self.assertEqual((ledger["request_sha256"], ledger["protocol_sha256"], ledger["trials"]),
                         (plan["request_sha256"], plan["quality_loop"]["protocol_sha256"], []))
        self.assertEqual((plan["evidence_skeleton"]["quality_ledger"], plan["evidence_skeleton"]["subject_artifacts"]), (None, []))
        self.assertEqual(workbench.compare_quality(request, ledger, self.ws.root)["next_action"], "stop_blocked")

    def test_production_plan_stays_pure(self):
        request = self.request()
        before = deepcopy(request)
        plan = workbench.production_plan(request)
        self.assertNotIn("evidence_skeleton", plan)
        self.assertNotIn("prepare_spec_draft", plan["creation_workflow"]["jobs"][0])
        self.assertEqual(request, before)

    def test_hyper3d_prepare_rejects_unfilled_draft(self):
        from test_hyper3d_api import FakeProvider, api
        request = self.request(target_triangles=1500)
        draft = self.draft(request)
        client = api.Client(self.ws.root, FakeProvider(), self.ws.root / "state")
        with self.assertRaises(api.SafeError):
            client.prepare(draft)
        self.assertFalse((self.ws.root / "runs/hyper3d/plans").exists())


if __name__ == "__main__":
    unittest.main()
