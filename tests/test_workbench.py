import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workbench", REPO / "scripts" / "workbench.py")
workbench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workbench)
identity = workbench.identity


def specified(task_type="static_prop"):
    request = workbench.make_draft("unit-rock", "原創灰色岩石，獨立模型", task_type)
    request["status"] = "specified"
    request["spec"]["size_m"] = [1, 1, 1]
    request["spec"]["target_triangles"] = 1500
    request["open_questions"] = []
    return request


class RequestTests(unittest.TestCase):
    def test_intake_preserves_brief_without_claiming_parsed_or_ready(self):
        text = "木城門兩扇可開關"
        request = workbench.make_draft("wood-gate", text, "interactive_prop")
        self.assertEqual(request["brief"], text)
        self.assertEqual(workbench.validate_request(request), [])
        self.assertEqual(request["status"], "draft")
        self.assertTrue(workbench.production_plan(request)["pending"])
        self.assertFalse(workbench.production_plan(request)["paid_submission_authorized_by_this_plan"])

    def test_standalone_has_no_implicit_game_checks(self):
        request = specified()
        checks = {c["id"] for c in workbench.required_checks(request)}
        self.assertNotIn("target_environment", checks)
        self.assertNotIn("rig_mapping", checks)
        self.assertNotIn("animation", checks)

    def test_optional_project_can_be_omitted(self):
        request = specified()
        del request["project"]
        self.assertEqual(workbench.validate_request(request), [])
        self.assertIsNone(workbench.production_plan(request)["project"])

    def test_missing_dimensions_or_geometry_budget_stays_pending(self):
        for field in ("size_m", "target_triangles"):
            with self.subTest(field=field):
                request = specified()
                del request["spec"][field]
                self.assertEqual(workbench.validate_request(request), [])
                self.assertTrue(workbench.production_plan(request)["pending"])
                result = workbench.assess(request, {"checks": {}, "deliverables": []})
                self.assertEqual(result["decision"], "not_ready")

    def test_collinear_axes_rejected(self):
        for up, forward, valid in (("+Y", "+Y", False), ("+Y", "-Y", False), ("+Y", "+Z", True), ("+Z", "+Y", True)):
            request = specified()
            request["spec"].update(up_axis=up, forward_axis=forward)
            self.assertEqual(not workbench.validate_request(request), valid)

    def test_invalid_library_root_fails_clearly(self):
        for index in ([], None):
            with self.assertRaisesRegex(ValueError, "invalid library index"):
                workbench.search_library(index, "rock")

    def test_profile_does_not_force_target_environment(self):
        profile = identity.read_json(REPO / "projects" / "changshan-longdan.json")
        request = workbench.make_draft("gate", "城門", "interactive_prop", profile)
        self.assertEqual(request["project"], profile["id"])
        self.assertEqual(request["delivery"]["scope"], "standalone")
        self.assertNotIn("target_environment", {c["id"] for c in workbench.required_checks(request)})

    def test_character_requires_rig_and_declared_animation_checks(self):
        request = specified("rigged_character")
        request["spec"]["animations"] = ["idle", "walk"]
        checks = {c["id"] for c in workbench.required_checks(request)}
        self.assertTrue({"rig_mapping", "deformation", "animation"} <= checks)
        request["spec"]["requires_rig"] = False
        self.assertTrue(workbench.validate_request(request))

    def test_interactive_template_includes_parts_and_motion(self):
        request = identity.read_json(REPO / "requests" / "examples" / "openable-gate.json")
        self.assertEqual(workbench.validate_request(request), [])
        self.assertEqual(workbench.production_plan(request)["pending"], [])
        self.assertTrue({"separate_parts", "articulation", "clearance"} <= {c["id"] for c in workbench.required_checks(request)})
        request["spec"]["parts"][1]["motion"]["range_deg"] = [100, 0]
        self.assertTrue(workbench.validate_request(request))

    def test_lod_can_be_added_as_explicit_requirement(self):
        request = specified()
        request["additional_checks"] = [{"id": "lod-silhouette", "area": "technical", "description": "LOD 輪廓符合需求"}]
        self.assertIn("lod-silhouette", {c["id"] for c in workbench.required_checks(request)})
        request["additional_checks"][0]["id"] = "art_match"
        self.assertTrue(workbench.validate_request(request))

    def test_target_environment_needs_specific_context(self):
        request = specified()
        request["delivery"] = {"scope": "target_environment", "formats": ["glb"], "target_environment": {"name": "Unity"}}
        self.assertTrue(workbench.validate_request(request))
        request["delivery"]["target_environment"].update(version="example-editor-version", verification_context="test scene")
        self.assertEqual(workbench.validate_request(request), [])
        self.assertIn("target_environment", {c["id"] for c in workbench.required_checks(request)})

    def test_unknown_or_unsafe_inputs_rejected(self):
        for field, value in (("id", "../escape"), ("project", "C:/outside"), ("task_type", []), ("status", {})):
            request = specified()
            request[field] = value
            self.assertTrue(workbench.validate_request(request))

    def test_size_and_texture_are_finite_and_requirement_specific(self):
        request = specified()
        request["spec"]["texture_px"] = 4096
        self.assertEqual(workbench.validate_request(request), [])
        request["spec"]["size_m"][0] = float("nan")
        self.assertTrue(workbench.validate_request(request))

    def test_library_reports_revision_gaps(self):
        index = identity.read_json(REPO / "library" / "index.json")
        matches = workbench.search_library(index, "火盆")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["status"], "needs_revision")
        self.assertEqual(matches[0]["acceptance"]["delivery"], "not_delivered")
        self.assertEqual(workbench.search_library(index, "sword", "changshan-longdan"), [])


class DeprecatedAliasTests(unittest.TestCase):
    """codex/art-quality-loop 的 RO 腳本仍匯入這些名稱；遷移完成前不得移除。"""

    def test_digest_aliases_match_identity(self):
        request = specified()
        request["quality"] = {"schema_version": 1, "status": "draft"}
        self.assertEqual(workbench.request_sha256(request), identity.json_digest(request))
        self.assertEqual(workbench.quality_sha256(request), identity.json_digest(request["quality"]))

    def test_read_json_alias_keeps_legacy_leniency(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text('[{"a": 1}]', encoding="utf-8-sig")
            self.assertEqual(workbench.read_json(path), [{"a": 1}])


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary_parent = (REPO / "tmp").resolve()
        if not temporary_parent.is_relative_to(REPO.resolve()):
            raise ValueError("test temporary directory outside workspace")
        temporary_parent.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="workbench-unit-", dir=temporary_parent)
        self.root = Path(self.temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to(temporary_parent))
        self.addCleanup(self.cleanup_owned_temporary)
        (self.root / "assets" / "processed").mkdir(parents=True)
        (self.root / "runs" / "qa").mkdir(parents=True)
        # 控制邏輯測試使用假檔案及假申報；不是實際模型或視覺驗收。
        (self.root / "assets" / "processed" / "rock.glb").write_bytes(b"unit fixture only")
        (self.root / "runs" / "qa" / "report.md").write_text("mock check evidence", encoding="utf-8")

    def cleanup_owned_temporary(self):
        target = Path(self.temporary.name).resolve()
        if target != self.root or not target.is_relative_to((REPO / "tmp").resolve()):
            raise ValueError("refusing cleanup outside task temporary directory")
        self.temporary.cleanup()

    def artifact(self, path):
        return {"path": path, "sha256": hashlib.sha256((self.root / path).read_bytes()).hexdigest()}

    def evidence(self, request):
        report = self.artifact("runs/qa/report.md")
        return {"request_id": request["id"], "request_sha256": identity.json_digest(request),
                "checks": {c["id"]: {"status": "pass", "method": "unit fixture declaration", "artifacts": [report]} for c in workbench.required_checks(request)},
                "deliverables": [self.artifact("assets/processed/rock.glb")]}

    def test_standalone_can_reach_review_without_claiming_game_delivery(self):
        request = specified()
        result = workbench.assess(request, self.evidence(request), self.root)
        self.assertEqual(result["decision"], "eligible_for_delivery_review")
        self.assertEqual(result["target_environment_claim"], "not_requested")
        self.assertEqual(result["mode"], "evidence_contract_check_only")
        self.assertNotIn("delivered", result)

    def test_specification_drift_invalidates_existing_evidence(self):
        request = specified()
        evidence = self.evidence(request)
        request["style"]["description"] = "紅色岩石"
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_file_drift_invalidates_delivery(self):
        request = specified()
        evidence = self.evidence(request)
        (self.root / "assets" / "processed" / "rock.glb").write_bytes(b"changed")
        self.assertIn("artifact hash mismatch", " ".join(workbench.assess(request, evidence, self.root)["blockers"]))

    def test_skipped_or_failed_check_never_counts_as_pass(self):
        for status in ("not_run", "fail"):
            request = specified()
            evidence = self.evidence(request)
            evidence["checks"]["art_match"]["status"] = status
            self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_pass_without_artifact_proof_is_blocked(self):
        request = specified()
        evidence = self.evidence(request)
        evidence["checks"]["art_match"]["artifacts"] = []
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_scope_upgrade_requires_target_runtime_evidence(self):
        request = specified()
        evidence = self.evidence(request)
        request["delivery"] = {"scope": "target_environment", "formats": ["glb"], "target_environment": {"name": "Unity", "version": "unit version", "verification_context": "unit scene"}}
        evidence["request_sha256"] = identity.json_digest(request)
        self.assertIn("target_environment: not_run", workbench.assess(request, evidence, self.root)["blockers"])

    def test_character_cannot_skip_rig_evidence(self):
        request = specified("rigged_character")
        evidence = self.evidence(request)
        del evidence["checks"]["rig_mapping"]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_outside_or_configuration_artifacts_rejected(self):
        for path in ("../outside.glb", ".git/config", "requests/secret.json", "assets/.env"):
            item = {"path": path, "sha256": "a" * 64}
            self.assertIsNotNone(workbench.check_artifact(item, self.root))

    def test_absolute_or_backslash_artifact_paths_are_not_portable(self):
        # 重新 clone 後仍要能核對，證據內路徑只能是 repo 相對 POSIX。
        for path in (str(self.root / "runs/qa/report.md"), "runs\\qa\\report.md"):
            item = {"path": path, "sha256": self.artifact("runs/qa/report.md")["sha256"]}
            self.assertEqual(workbench.check_artifact(item, self.root), "RECORDED_PATH_INVALID")

    def test_missing_requested_format_is_blocked(self):
        request = specified()
        request["delivery"]["formats"].append("fbx")
        result = workbench.assess(request, self.evidence(request), self.root)
        self.assertIn("missing requested format: fbx", result["blockers"])

    def test_obj_mtl_dependencies_can_be_registered(self):
        request = specified()
        request["delivery"]["formats"] = ["obj"]
        for filename in ("rock.obj", "rock.mtl", "color.png"):
            (self.root / "assets" / "processed" / filename).write_bytes(b"unit dependency")
        evidence = self.evidence(request)
        evidence["deliverables"] = [self.artifact(f"assets/processed/{name}") for name in ("rock.obj", "rock.mtl", "color.png")]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "eligible_for_delivery_review")
        self.assertIsNotNone(workbench.check_artifact({"path": "../outside.mtl", "sha256": "a" * 64}, self.root))

    def test_repository_delivery_package_can_be_checked(self):
        folder = self.root / "deliveries" / "unit-rock" / "v001"
        folder.mkdir(parents=True)
        (folder / "rock.glb").write_bytes(b"unit delivery fixture")
        (folder / "README.md").write_text("unit instructions", encoding="utf-8")
        request = specified()
        evidence = self.evidence(request)
        evidence["deliverables"] = [self.artifact(f"deliveries/unit-rock/v001/{name}") for name in ("rock.glb", "README.md")]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "eligible_for_delivery_review")


if __name__ == "__main__":
    unittest.main()
