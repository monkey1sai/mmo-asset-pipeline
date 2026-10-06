import contextlib
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse

spec = importlib.util.spec_from_file_location("repo_hyper3d_api", Path(__file__).resolve().parents[1] / "scripts/hyper3d_api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
TASK = "123e4567-e89b-12d3-a456-426614174000"
SECRET = "mock-subscription-DO-NOT-PRINT"
SIGNED = "https://file.hyper3d.com/model.glb?private-signature=DO-NOT-PRINT"


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.response = {"uuid": TASK, "jobs": {"subscription_key": SECRET}, "consumed": 0.5}
        self.status_response = {"jobs": [{"status": "Done"}]}
        self.download_response = {"list": [{"name": "model.glb", "url": SIGNED}]}
        self.http_status = 200
        self.request_headers = []

    def balance(self):
        return {"authenticated": True, "balance": 228.5}

    def protected_bytes(self, value, decrypt=False):
        if decrypt:
            if not value.startswith(b"DPAPI-MOCK:"):
                raise RuntimeError(SECRET)
            return value[len(b"DPAPI-MOCK:"):]
        return b"DPAPI-MOCK:" + value

    def api(self, endpoint, body=None, content_type=None):
        self.calls.append((endpoint, body, content_type))
        if endpoint == "/rodin":
            if isinstance(self.response, Exception):
                raise self.response
            return self.response
        if endpoint == "/status":
            return self.status_response
        if endpoint == "/download":
            return self.download_response
        raise RuntimeError("unexpected endpoint")

    def public_download_url(self, value):
        parts = urllib.parse.urlsplit(value)
        if parts.scheme != "https" or parts.hostname != "file.hyper3d.com" or parts.username:
            raise RuntimeError(SIGNED)
        return parts, "93.184.216.34"

    def PinnedHTTPS(self, host, public_ip):
        provider = self

        class Connection:
            def request(self, method, target, *args, **kwargs):
                provider.request_headers.append(kwargs.get("headers", {}))

            def getresponse(self):
                class Response:
                    status = provider.http_status
                    stream = io.BytesIO(b"glTF model fixture")

                    def read(self, count):
                        return self.stream.read(count)

                return Response()

            def close(self):
                pass

        return Connection()


class Hyper3DApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "workspace"
        self.root.mkdir()
        self.state = Path(self.directory.name) / "private-state"
        self.state.mkdir()
        (self.root / "requests").mkdir()
        (self.root / "requests/character.json").write_text(json.dumps({"id": "character-r01", "quality": {"dimensions": ["form"]}}), encoding="utf-8")
        (self.root / "assets/raw/design").mkdir(parents=True)
        (self.root / "assets/raw/design/pose.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        self.provider = FakeProvider()
        self.client = api.Client(self.root, self.provider, self.state)
        self.spec = {"operation_id": "test-001", "request": "requests/character.json", "images": ["assets/raw/design/pose.png"],
                     "output_directory": "assets/raw/character/v001", "parameters": {"tier": "Gen-2.5-High", "mesh_mode": "Raw", "quality_override": 30000, "geometry_file_format": "glb", "TAPose": True, "is_symmetric": "symmetric", "material": "PBR"},
                     "authorization": {"spending_scope": "user permits demand-driven existing credits", "credit_pool": "existing_monthly_or_regular", "no_topup_or_upgrade": True}}

    def prepare(self):
        return self.client.prepare(self.spec)

    def submit(self):
        return self.client.submit(self.spec["operation_id"], True, str(self.client.private_path(self.spec["operation_id"])))

    def complete(self):
        self.prepare()
        self.submit()
        path = self.client.record_path(self.spec["operation_id"])
        record = api.read_json(path)
        record["submitted_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
        api.write_json(path, record)
        return self.client.status(self.spec["operation_id"])

    def public_text(self):
        return "\n".join(x.read_text(encoding="utf-8") for x in self.root.rglob("*.json"))

    def assert_no_secret(self, value=""):
        self.assertNotIn(SECRET, self.public_text() + value)
        self.assertNotIn("private-signature", self.public_text() + value)

    def test_prepare_is_offline_and_requires_exact_state_authority_before_submit(self):
        result = self.prepare()
        self.assertFalse(result["submission_ready"])
        with self.assertRaisesRegex(api.SafeError, "EXACT_PRIVATE_STATE_AUTHORIZATION_REQUIRED"):
            self.client.submit("test-001", True, None)
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_pending_journal_is_durable_before_charged_call(self):
        self.prepare()
        original = self.provider.api

        def observe(endpoint, body=None, content_type=None):
            self.assertEqual(api.read_json(self.client.record_path("test-001"))["state"], "pending")
            self.assertTrue(self.client.private_path("test-001").is_file())
            return original(endpoint, body, content_type)

        self.provider.api = observe
        record = self.submit()
        self.assertEqual(record["state"], "submitted")
        self.assertEqual(record["consumed_credits"], 0.5)
        self.assert_no_secret()
        with self.assertRaisesRegex(api.SafeError, "OPERATION_ALREADY_EXISTS"):
            self.submit()
        self.assertEqual(len(self.provider.calls), 1)

    def test_timeout_is_unknown_and_same_or_new_id_cannot_resubmit(self):
        self.prepare()
        self.provider.response = TimeoutError(SECRET + SIGNED)
        self.assertEqual(self.submit()["state"], "unknown")
        with self.assertRaises(api.SafeError):
            self.submit()
        self.spec["operation_id"] = "test-002"
        self.prepare()
        with self.assertRaisesRegex(api.SafeError, "UNRESOLVED_OPERATION"):
            self.submit()
        self.assertEqual(len(self.provider.calls), 1)
        self.assert_no_secret()

    def test_unknown_operation_also_blocks_changed_payload_and_request(self):
        self.prepare()
        self.provider.response = TimeoutError(SECRET)
        self.submit()
        self.spec["operation_id"] = "test-002"
        self.spec["parameters"]["seed"] = 42
        self.prepare()
        with self.assertRaisesRegex(api.SafeError, "UNRESOLVED_OPERATION"):
            self.submit()
        self.assertEqual(len(self.provider.calls), 1)

    def test_explicit_failed_response_preserves_reported_cost_without_secret(self):
        self.prepare()
        self.provider.response = {"error": "IMAGE_CONTENT_VIOLATION", "consumed": 0, "message": SECRET}
        result = self.submit()
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["consumed_credits"], 0)
        self.assertEqual(len(self.provider.calls), 1)
        self.assert_no_secret()

    def test_dpapi_failure_or_existing_private_file_means_zero_charged_calls(self):
        self.prepare()
        self.provider.protected_bytes = lambda *a, **k: (_ for _ in ()).throw(OSError(SECRET))
        with self.assertRaises(OSError):
            self.submit()
        self.assertEqual(self.provider.calls, [])
        self.client.private_path("test-001").write_bytes(b"previous-task")
        with self.assertRaisesRegex(api.SafeError, "OPERATION_ALREADY_EXISTS"):
            self.submit()
        self.assertEqual(self.client.private_path("test-001").read_bytes(), b"previous-task")

    def test_post_submission_private_write_failure_stays_unknown(self):
        self.prepare()
        original = self.client.private_write

        def broken(path, value, exclusive):
            if not exclusive:
                raise OSError(SECRET)
            return original(path, value, exclusive)

        self.client.private_write = broken
        result = self.submit()
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["task_uuid"], TASK)
        self.assertEqual(result["consumed_credits"], 0.5)
        self.assertEqual(result["failure_stage"], "private_state_save")
        self.assertEqual(len(self.provider.calls), 1)
        self.assert_no_secret()

    def test_missing_cost_keeps_task_and_private_recovery_with_unverified_cost(self):
        self.prepare()
        del self.provider.response["consumed"]
        result = self.submit()
        self.assertEqual(result["state"], "submitted")
        self.assertEqual(result["task_uuid"], TASK)
        self.assertIsNone(result["consumed_credits"])
        self.assertEqual(result["cost_state"], "unverified_missing_or_invalid_consumed")
        self.assertEqual(self.client.private_read(result)["task_uuid"], TASK)
        self.assert_no_secret()

    def test_changed_input_or_plan_tamper_never_calls_network(self):
        self.prepare()
        image = self.root / self.spec["images"][0]
        image.write_bytes(image.read_bytes() + b"changed")
        with self.assertRaisesRegex(api.SafeError, "INPUT_CHANGED"):
            self.submit()
        self.assertEqual(self.provider.calls, [])
        path = self.root / "runs/hyper3d/plans/test-001.json"
        plan = api.read_json(path)
        plan["parameters"]["quality_override"] = 50000
        api.write_json(path, plan)
        with self.assertRaisesRegex(api.SafeError, "PLAN_INTEGRITY"):
            self.submit()

    def test_plan_binds_the_request_digest_that_workbench_evidence_uses(self):
        from test_workbench import specified, workbench
        request = specified()
        (self.root / "requests/character.json").write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8-sig")
        self.prepare()
        plan = json.loads((self.root / "runs/hyper3d/plans/test-001.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["schema_version"], 2)
        self.assertNotIn("sha256", plan["request"])
        self.assertEqual(plan["request"]["request_sha256"], workbench.production_plan(request)["request_sha256"])

    def test_reformatted_request_is_the_same_request_but_content_change_is_not(self):
        self.prepare()
        path = self.root / self.spec["request"]
        path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=4), encoding="utf-8-sig")
        self.assertEqual(self.submit()["state"], "submitted")
        self.spec["operation_id"] = "test-002"
        self.spec["output_directory"] = "assets/raw/character/v002"
        self.prepare()
        path.write_text(json.dumps({"quality": {"dimensions": ["form", "color"]}}), encoding="utf-8")
        with self.assertRaisesRegex(api.SafeError, "INPUT_CHANGED"):
            self.submit()

    def test_operation_id_follows_asset_id_grammar(self):
        self.spec["operation_id"] = "evoloot.weapon.iron_sword-r01"
        self.assertEqual(self.prepare()["operation_id"], "evoloot.weapon.iron_sword-r01")
        for value in ("bad..id", "trailing.", "Upper"):
            self.spec["operation_id"] = value
            with self.subTest(value=value), self.assertRaisesRegex(api.SafeError, "OPERATION_ID_INVALID"):
                self.prepare()

    def test_v1_plan_is_refused_before_any_charge(self):
        self.prepare()
        path = self.root / "runs/hyper3d/plans/test-001.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        del plan["plan_sha256"]
        plan["schema_version"] = 1
        plan["plan_sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(api.SafeError, "PLAN_SCHEMA_OUTDATED"):
            self.submit()
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_unportable_spec_path_reports_identity_code(self):
        self.spec["request"] = "requests\\character.json"
        with self.assertRaisesRegex(api.SafeError, r"\ARECORDED_PATH_INVALID\Z"):
            self.prepare()

    def test_prepare_requires_ledger_derivable_request_identity(self):
        # Q5：帳本由 plan → 需求檔推導 request_id；無法推導的需求不得產生付費操作。
        path = self.root / self.spec["request"]
        for value, code in (({"quality": {}}, "REQUEST_ID_INVALID"), ({"id": "Bad Id"}, "REQUEST_ID_INVALID"),
                            ({"id": "rock-r01", "catalog_asset_id": "a..b"}, "CATALOG_ASSET_ID_INVALID")):
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(value=value), self.assertRaisesRegex(api.SafeError, code):
                self.prepare()
        self.assertFalse((self.root / "runs/hyper3d/plans").exists())

    def test_invalid_ledger_record_blocks_submit_before_any_charge(self):
        self.prepare()
        (self.root / "runs/hyper3d/operations").mkdir(parents=True, exist_ok=True)
        (self.root / "runs/hyper3d/operations/garbled.json").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(api.SafeError, "UNRESOLVED_OPERATION_NEVER_RESUBMIT"):
            self.submit()
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_legacy_import_records_are_read_only(self):
        operations = self.root / "runs/hyper3d/operations"
        operations.mkdir(parents=True)
        (operations / "bootstrap-old.json").write_text(json.dumps({
            "schema_version": 1, "source": "legacy_import", "operation_id": "bootstrap-old", "state": "complete",
            "request_id": None, "catalog_asset_id": "cl-brazier", "task_uuid": None, "consumed_credits": None,
            "evidence": [{"path": "requests/character.json", "sha256": "0" * 64}], "imported_utc": "x", "note": "x"}), encoding="utf-8")
        for command in (self.client.status, self.client.download):
            with self.subTest(command=command.__name__), self.assertRaisesRegex(api.SafeError, "LEGACY_IMPORT_READ_ONLY"):
                command("bootstrap-old")
        self.assertEqual(self.provider.calls, [])

    def test_legacy_hash_aliases_match_identity(self):
        # codex/art-quality-loop 的 RO 腳本仍匯入 file_sha、sha、canonical。
        path = self.root / self.spec["images"][0]
        self.assertEqual(api.file_sha(path), api.identity.file_digest(path))
        value = {"b": [1], "a": "岩"}
        self.assertEqual(api.canonical(value), api.identity.canonical_json(value))
        self.assertEqual(api.sha(api.canonical(value)), api.identity.json_digest(value))

    def test_parameters_and_cost_are_not_fixed_to_half_credit(self):
        params = {"tier": "Gen-2.5-Extreme-High", "texture_mode": "extreme-high", "mesh_mode": "Quad", "quality_override": 200000}
        self.assertEqual(api.parameters(params, 1)[1], 3.0)
        for params in ({}, {"tier": "Gen-2.5-High", "endpoint": "/bang"}, {"tier": "Gen-2.5-Low", "quality_override": 1000001}, {"tier": "Gen-2.5-High", "mesh_mode": "Quad", "quality_override": 200001}, {"tier": "Gen-2.5-High", "TAPose": "true"}, {"tier": "Gen-2.5-High", "seed": True}, {"tier": "Gen-2.5-High", "quality_override": float("nan")}, {"tier": "Gen-2.5-High", "image_label": ["F", "B"]}):
            with self.subTest(params=params), self.assertRaises(api.SafeError):
                api.parameters(params, 1)
        self.assertEqual(self.provider.calls, [])

    def test_text_only_and_multipart_image_options(self):
        self.spec["images"] = []
        self.spec["parameters"]["prompt"] = "A separate straight sword"
        self.prepare()
        plan = self.client.plan("test-001")
        body, content_type = self.client.multipart(plan)
        self.assertNotIn(b'name="images"', body)
        self.assertIn(b'name="TAPose"\r\n\r\ntrue', body)
        self.assertIn("multipart/form-data", content_type)

    def test_workspace_escape_collision_and_image_type(self):
        for name in ("../outside.png", "C:/outside.png", "assets/../../outside.png", "assets\\outside.png"):
            with self.subTest(name=name), self.assertRaises(api.SafeError):
                self.client.path(name)
        self.spec["output_directory"] = "requests"
        with self.assertRaises(api.SafeError):
            self.prepare()
        self.spec["output_directory"] = "assets/raw/new"
        (self.root / self.spec["images"][0]).write_bytes(b"not an image")
        with self.assertRaisesRegex(api.SafeError, "IMAGE_TYPE"):
            self.prepare()

    def test_monthly_only_balance_is_not_pool_evidence(self):
        self.spec["authorization"]["credit_pool"] = "existing_monthly"
        self.prepare()
        with self.assertRaisesRegex(api.SafeError, "MONTHLY_POOL_EVIDENCE_UNAVAILABLE"):
            self.submit()
        self.assertEqual(self.provider.calls, [])

    def test_status_uses_private_key_and_enforces_backoff_and_terminals(self):
        self.prepare()
        self.submit()
        with self.assertRaisesRegex(api.SafeError, "STATUS_BACKOFF"):
            self.client.status("test-001")
        path = self.client.record_path("test-001")
        record = api.read_json(path)
        record["submitted_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
        api.write_json(path, record)
        self.provider.status_response = {"jobs": [{"status": "Done"}, {"status": "Failed"}]}
        result = self.client.status("test-001")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(self.provider.calls[-1][1], {"subscription_key": SECRET})
        with self.assertRaises(api.SafeError):
            self.client.download("test-001")
        self.assert_no_secret(json.dumps(result))

    def test_download_hashes_and_no_secrets_or_auth_header(self):
        self.assertEqual(self.complete()["state"], "complete")
        result = self.client.download("test-001")
        self.assertEqual(result["state"], "downloaded")
        self.assertEqual(result["downloads"][0]["sha256"], hashlib.sha256(b"glTF model fixture").hexdigest())
        self.assertEqual(self.provider.request_headers, [{}])
        with self.assertRaises(api.SafeError):
            self.client.download("test-001")
        self.assert_no_secret(json.dumps(result))

    def test_status_preserves_download_lifecycle_without_network_or_record_rewrite(self):
        self.complete()
        self.client.download("test-001")
        path = self.client.record_path("test-001")
        for state in ("downloaded", "download_partial"):
            with self.subTest(state=state):
                record = api.read_json(path)
                record["state"] = state
                record["status_checked_utc"] = (datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()
                api.write_json(path, record)
                before = path.read_bytes()
                calls = len(self.provider.calls)
                result = self.client.status("test-001")
                self.assertEqual(result["state"], state)
                self.assertFalse(result["live_query"])
                self.assertEqual(result["status_source"], "local_download_record")
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(len(self.provider.calls), calls)
                self.assertEqual(result["downloads"], record["downloads"])

    def test_download_invalid_names_urls_and_case_collisions_stop_before_files(self):
        self.complete()
        for entries in ([{"name": "../model.glb", "url": SIGNED}], [{"name": "CON.glb", "url": SIGNED}], [{"name": "model.glb", "url": "http://127.0.0.1/secret"}], [{"name": "model.glb", "url": SIGNED}, {"name": "MODEL.glb", "url": SIGNED}]):
            self.provider.download_response = {"list": entries}
            with self.subTest(entries=entries), self.assertRaises(Exception):
                self.client.download("test-001")
            self.assertFalse((self.root / self.spec["output_directory"]).exists())
        self.assert_no_secret()

    def test_redirect_preserves_partial_state_and_never_retries(self):
        self.complete()
        self.provider.http_status = 302
        result = self.client.download("test-001")
        self.assertEqual(result["state"], "download_partial")
        self.assertEqual(self.provider.request_headers, [{}])
        with self.assertRaises(api.SafeError):
            self.client.download("test-001")
        self.assert_no_secret()

    def test_size_limit_preserves_part_and_prior_manifest(self):
        self.complete()
        with patch.object(api, "MAX_FILE", 2):
            result = self.client.download("test-001")
        self.assertEqual(result["state"], "download_partial")
        self.assertTrue((self.root / self.spec["output_directory"] / "model.glb.part").exists())
        self.assertEqual(result["downloads"], [])
        self.assert_no_secret()

    def test_real_service_waiting_generating_states_and_unknown_state(self):
        self.complete()
        path = self.client.record_path("test-001")
        for states, valid in ((["Waiting", "Generating", "Done"], True), (["Unexpected"], False)):
            record = api.read_json(path)
            record["status_checked_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
            api.write_json(path, record)
            self.provider.status_response = {"jobs": [{"status": x} for x in states]}
            if valid:
                self.assertEqual(self.client.status("test-001")["state"], "processing")
            else:
                with self.assertRaisesRegex(api.SafeError, "STATUS_RESPONSE_INVALID"):
                    self.client.status("test-001")

    def test_cli_redacts_provider_exception(self):
        with patch.object(api.Client, "balance", side_effect=RuntimeError(SECRET + SIGNED)):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                result = api.main(["--workspace", str(self.root), "balance"])
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(stream.getvalue()), {"error": "CLIENT_ERROR_REDACTED"})
            self.assert_no_secret(stream.getvalue())

    def test_import_disables_bytecode_before_loading_supported_provider(self):
        with patch.object(api.identity, "file_digest", return_value=api.PROVIDER_SHA256), patch.object(Path, "is_file", return_value=True), patch.object(api.importlib.util, "spec_from_file_location") as factory:
            factory.side_effect = RuntimeError("stop before import")
            with self.assertRaises(RuntimeError):
                api.load_provider()
            self.assertTrue(api.sys.dont_write_bytecode)

    def test_unsupported_interfaces_report_unavailable_without_network(self):
        result = self.client.capabilities()
        self.assertEqual(result["unavailable_transport"], ["bang", "texture_only", "agentic"])
        self.assertFalse(result["runtime_generation_verified"])
        self.assertEqual(self.provider.calls, [])


if __name__ == "__main__":
    unittest.main()
