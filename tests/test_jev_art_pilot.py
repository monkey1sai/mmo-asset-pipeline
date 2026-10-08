"""本機合成 provider 驗證；不讀憑證、不呼叫 API。"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import identity
import jev_art_pilot as pilot
import workbench


class FakeClient:
    def __init__(self, failure=False):
        self.calls = 0
        self.failure = failure

    def system_one(self, state, questions):
        self.calls += 1
        if self.failure:
            raise RuntimeError("private provider error body must never be recorded")
        answers = {}
        for qid, question in questions.items():
            if question["type"] == "choice":
                selected = "none" if qid == "match_asset" else "static_prop"
                probabilities = {option: float(option == selected) for option in question["criteria"]}
                answers[qid] = {"type": "choice", "choice": selected, "confidence": 1.0, "probabilities": probabilities}
            else:
                answers[qid] = {"type": "score", "score": 0.0, "confidence": 1.0, "probabilities": {str(i): float(i == 0) for i in range(len(question["criteria"]))}}
        return {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 100, "output_tokens": 20}, "unexpected_header": "do not preserve"}


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (pilot.DATASET, "library/index.json", "scripts/jev_art_pilot.py", "scripts/workbench.py", "scripts/identity.py"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, target)
        self.run_id = "unit-jev-pilot"

    def prepare(self):
        with redirect_stdout(io.StringIO()):
            return pilot.prepare(self.root, self.run_id)

    def execute(self, client, limit=1):
        with redirect_stdout(io.StringIO()):
            return pilot.execute(self.root, self.run_id, client, limit)

    def test_dataset_covers_chinese_genres_and_reachable_expected_candidates(self):
        dataset, assets = pilot.load_dataset(self.root)
        self.assertEqual(len(dataset["cases"]), 20)
        self.assertEqual(len({c["genre"] for c in dataset["cases"]}), 12)
        self.assertEqual({c["expected_type"] for c in dataset["cases"]}, set(pilot.TASK_CRITERIA))
        self.assertEqual(sum(not c["acceptable_assets"] for c in dataset["cases"]), 3)
        self.assertEqual(sum(a["provenance_kind"] == "library_metadata_snapshot" for a in assets.values()), 5)

    def test_payload_withholds_labels_paths_and_unapproved_fields(self):
        dataset, assets = pilot.load_dataset(self.root)
        case = dataset["cases"][0]
        assets[case["candidate_ids"][0]]["private_path"] = "PRIVATE_SOURCE"
        payload = pilot.make_payload(case, assets)
        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("expected_type", "acceptable_assets", "label_source", "private_path", "PRIVATE_SOURCE", "files", "qa_report"):
            self.assertNotIn(forbidden, serialized)
        self.assertIn("none", payload["questions"]["match_asset"]["criteria"])
        self.assertEqual(payload["state"]["brief"], case["brief"])
        self.assertEqual(set(pilot.TASK_CRITERIA), set(payload["questions"]["task_type"]["criteria"]))

    def test_prepare_creates_valid_drafts_without_provider_or_evaluation_claim(self):
        report = self.prepare()
        self.assertEqual(report["jev"]["evaluated_cases"], 0)
        self.assertEqual(report["usage"]["actual_charge"], "UNVERIFIED")
        drafts = list((self.root / "requests/examples/jev-pilot").glob("*.json"))
        self.assertEqual(len(drafts), 20)
        for path in drafts:
            request = identity.read_json(path)
            self.assertEqual(workbench.validate_request(request), [])
            self.assertEqual(request["status"], "draft")
            self.assertEqual(request["production"]["route"], "review_existing")
            self.assertTrue(workbench.readiness(request))
        self.assertFalse((pilot.run_path(self.root, self.run_id) / "operations").exists())

    def test_second_prepare_preserves_first_frozen_run(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "RUN_ALREADY_PREPARED"):
            self.prepare()

    def test_input_drift_stops_before_any_provider_call(self):
        self.prepare()
        (self.root / pilot.DATASET).write_text("{}", encoding="utf-8")
        client = FakeClient()
        with self.assertRaisesRegex(ValueError, "FROZEN_INPUT_DRIFT"):
            self.execute(client)
        self.assertEqual(client.calls, 0)

    def test_resume_only_runs_unsubmitted_cases(self):
        self.prepare()
        first = FakeClient()
        self.assertEqual(self.execute(first)["jev"]["evaluated_cases"], 1)
        second = FakeClient()
        self.assertEqual(self.execute(second)["jev"]["evaluated_cases"], 2)
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)
        first_response = pilot.run_path(self.root, self.run_id) / "responses/c01-action-sword.json"
        self.assertNotIn("unexpected_header", identity.read_json(first_response))

    def test_unknown_submission_blocks_retry_and_redacts_provider_error(self):
        self.prepare()
        client = FakeClient(failure=True)
        with self.assertRaisesRegex(ValueError, "PROVIDER_STOPPED_NO_RETRY"):
            self.execute(client)
        operation = pilot.run_path(self.root, self.run_id) / "operations/c01-action-sword.json"
        text = operation.read_text(encoding="utf-8")
        self.assertNotIn("private provider", text)
        self.assertEqual(identity.read_json(operation)["status"], "unknown")
        other = FakeClient()
        with self.assertRaisesRegex(ValueError, "ORIGINAL_OPERATION_UNRESOLVED"):
            self.execute(other)
        self.assertEqual(other.calls, 0)

    def test_request_limit_is_bounded_before_network(self):
        self.prepare()
        client = FakeClient()
        for limit in (0, 21):
            with self.assertRaisesRegex(ValueError, "REQUEST_BUDGET_INVALID"):
                self.execute(client, limit)
        self.assertEqual(client.calls, 0)

    def test_corrupted_response_cannot_be_used_as_evidence(self):
        self.prepare()
        self.execute(FakeClient())
        response = pilot.run_path(self.root, self.run_id) / "responses/c01-action-sword.json"
        response.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RESPONSE_DRIFT"):
            pilot.make_report(self.root, self.run_id)

    def test_invalid_provider_choice_and_probability_are_rejected(self):
        dataset, assets = pilot.load_dataset(self.root)
        payload = pilot.make_payload(dataset["cases"][0], assets)
        valid = FakeClient().system_one(payload["state"], payload["questions"])
        invalid = json.loads(json.dumps(valid))
        invalid["answers"]["task_type"]["choice"] = "execute_paid_generation"
        with self.assertRaisesRegex(ValueError, "CHOICE_INVALID"):
            pilot.validate_response(payload, invalid)
        invalid = json.loads(json.dumps(valid))
        invalid["answers"]["task_type"]["probabilities"]["static_prop"] = float("nan")
        with self.assertRaisesRegex(ValueError, "PROBABILITIES_INVALID"):
            pilot.validate_response(payload, invalid)
        invalid = json.loads(json.dumps(valid))
        invalid["answers"]["fit_0"]["score"] = 3
        with self.assertRaisesRegex(ValueError, "SCORE_INVALID"):
            pilot.validate_response(payload, invalid)

    def test_missing_answer_or_boolean_usage_is_rejected(self):
        dataset, assets = pilot.load_dataset(self.root)
        payload = pilot.make_payload(dataset["cases"][0], assets)
        response = FakeClient().system_one(payload["state"], payload["questions"])
        response["usage"]["input_tokens"] = True
        with self.assertRaisesRegex(ValueError, "USAGE_INVALID"):
            pilot.validate_response(payload, response)
        del response["answers"]["fit_0"]
        with self.assertRaisesRegex(ValueError, "ANSWER_SET_INVALID"):
            pilot.validate_response(payload, response)

    def test_live_requires_explicit_opt_in_before_loading_credentials(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(pilot.main(["live"]), 2)
        self.assertIn("LIVE_REQUIRES_EXECUTE_AND_PROVIDER", output.getvalue())

    def test_redirect_and_unreviewed_provider_source_are_blocked(self):
        request = urllib.request.Request(pilot.ENDPOINT)
        with self.assertRaises(urllib.error.HTTPError):
            pilot.NoRedirect().redirect_request(request, None, 302, "move", {}, "https://other.example")
        provider = self.root / "unknown-provider.py"
        provider.write_text("raise RuntimeError('should never execute')", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "PROVIDER_CLIENT_DRIFT"):
            pilot.load_client(provider, pilot.CLIENT_SHA256)

    def test_unsafe_case_identifier_is_rejected(self):
        dataset = identity.read_json(self.root / pilot.DATASET)
        dataset["cases"][0]["id"] = "../private"
        pilot.write_json(self.root / pilot.DATASET, dataset)
        with self.assertRaisesRegex(ValueError, "CASE_ID_INVALID"):
            pilot.load_dataset(self.root)

    def test_rank_metrics_exclude_no_match_cases_and_allow_alternatives(self):
        rows = [{"acceptable_assets": ["a", "b"], "rank": ["b", "z", "a"]}, {"acceptable_assets": [], "rank": ["z"]}]
        self.assertEqual(pilot.rank_metrics(rows, "rank"), {"evaluated_cases": 1, "top1_correct": 1, "top3_correct": 1, "mrr": 1.0})


if __name__ == "__main__":
    unittest.main()
