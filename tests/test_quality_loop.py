"""Synthetic evidence tests; no actual art, render, DCC or paid generation claims."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
import unittest

import test_workbench as fixtures

workbench = fixtures.workbench


class QualityLoopTests(unittest.TestCase):
    setUp = fixtures.EvidenceTests.setUp
    cleanup_owned_temporary = fixtures.EvidenceTests.cleanup_owned_temporary
    artifact = fixtures.EvidenceTests.artifact
    evidence = fixtures.EvidenceTests.evidence

    def request(self):
        request = fixtures.specified()
        request["production"]["max_revisions"] = 3
        (self.root / "runs/qa/reference.png").write_bytes(b"synthetic reference")
        request["quality"] = {
            "schema_version": 1, "status": "frozen",
            "protocol": {"views": ["front", "side", "back"], "lighting": "fixed unit light",
                         "background": "gray", "framing": "same orthographic scale",
                         "tool_version": "unit fixture", "inspection_context": "synthetic only"},
            "reference_artifacts": [self.artifact("runs/qa/reference.png")],
            "dimensions": [{"id": key, "criterion": key, "target": 4,
                            "anchors": [f"{key} level {i}" for i in range(6)]}
                           for key in ("silhouette", "materials")],
            "budget": {"trial_seconds": 120, "total_seconds": 500},
        }
        return request

    def trial(self, request, tid, values, parent=None):
        model = f"assets/processed/{tid}.glb"
        (self.root / model).write_bytes(f"synthetic model {tid}".encode())
        evidence = self.evidence(request)
        evidence["deliverables"] = [self.artifact(model)]
        evidence["subject_artifacts"] = deepcopy(evidence["deliverables"])
        previews = {}
        for view in request["quality"]["protocol"]["views"]:
            path = f"runs/qa/{tid}-{view}.png"
            (self.root / path).write_bytes(f"synthetic {tid} {view}".encode())
            previews[view] = self.artifact(path)
        return {"id": tid, "parent_id": parent, "status": "completed", "elapsed_seconds": 60,
                "hypothesis": "test one scoped form change", "change": "one shape change",
                "protocol_sha256": workbench.quality_sha256(request), "reviewer": "unit fixture",
                "previews": previews, "evidence": evidence,
                "scores": {key: {"value": value, "reason": "synthetic observed difference"}
                           for key, value in zip(("silhouette", "materials"), values)}}

    def ledger(self, request, *trials):
        return {"schema_version": 1, "request_id": request["id"],
                "request_sha256": workbench.request_sha256(request),
                "protocol_sha256": workbench.quality_sha256(request), "trials": list(trials)}

    def comparison(self, request, *trials):
        return workbench.compare_quality(request, self.ledger(request, *trials), self.root)

    def delivery(self, request, ledger, trial):
        path = "runs/qa/quality-ledger.json"
        (self.root / path).write_text(json.dumps(ledger), encoding="utf-8")
        evidence = deepcopy(trial["evidence"])
        evidence["quality_ledger"] = self.artifact(path)
        return evidence

    def test_scoped_gain_kept_but_below_target_not_delivery(self):
        request = self.request()
        baseline = self.trial(request, "base", [2, 2])
        candidate = self.trial(request, "better", [3, 2], "base")
        result = self.comparison(request, baseline, candidate)
        self.assertEqual(result["trials"][1]["decision"], "keep_for_iteration")
        self.assertFalse(result["quality_target_met"])
        self.assertEqual(result["next_action"], "revise_current_best")

    def test_larger_total_cannot_hide_silhouette_regression(self):
        request = self.request()
        baseline = self.trial(request, "base", [3, 2])
        candidate = self.trial(request, "regression", [2, 5], "base")
        candidate["decision"] = "keep"
        result = self.comparison(request, baseline, candidate)
        self.assertEqual(result["trials"][1]["decision"], "discard")
        self.assertEqual(result["best_trial_id"], "base")

    def test_sequence_compares_to_best_not_last_discarded_trial(self):
        request = self.request()
        baseline = self.trial(request, "base", [2, 2])
        better = self.trial(request, "better", [3, 2], "base")
        rejected = self.trial(request, "rejected", [2, 5], "better")
        final = self.trial(request, "final", [4, 4], "better")
        result = self.comparison(request, baseline, better, rejected, final)
        self.assertEqual(result["best_trial_id"], "final")
        self.assertTrue(result["quality_target_met"])
        self.assertEqual(result["candidate_trials_used"], 3)
        final["parent_id"] = "rejected"
        self.assertEqual(self.comparison(request, baseline, better, rejected, final)["next_action"], "stop_blocked")

    def test_failed_attempt_counts_and_is_preserved(self):
        request = self.request()
        request["production"]["max_revisions"] = 1
        baseline = self.trial(request, "base", [2, 2])
        failed = {"id": "failed", "parent_id": "base", "status": "failed", "elapsed_seconds": 30,
                  "protocol_sha256": workbench.quality_sha256(request), "reviewer": "fixture",
                  "hypothesis": "one failed attempt", "change": "shape", "failure_reason": "TEST_FAILURE"}
        result = self.comparison(request, baseline, failed)
        self.assertEqual(result["trials"][1]["decision"], "failed")
        self.assertEqual(result["next_action"], "stop_budget")

    def test_unresolved_operation_stops_subsequent_attempts(self):
        for status in ("pending", "unknown", "blocked"):
            request = self.request()
            baseline = self.trial(request, "base", [2, 2])
            unresolved = {"id": "unresolved", "parent_id": "base", "status": status,
                          "elapsed_seconds": 30, "reviewer": "fixture", "hypothesis": "shape",
                          "change": "shape", "failure_reason": "operation unresolved",
                          "protocol_sha256": workbench.quality_sha256(request)}
            later = self.trial(request, "later", [4, 4], "base")
            result = self.comparison(request, baseline, unresolved, later)
            self.assertFalse(result["quality_target_met"])
            self.assertIn("trial recorded after a required stop", result["trials"][2]["issues"])

    def test_budget_limits_baseline_and_candidates(self):
        for case in ("trial", "total", "count"):
            request = self.request()
            baseline = self.trial(request, "base", [2, 2])
            candidate = self.trial(request, "better", [4, 4], "base")
            if case == "trial":
                candidate["elapsed_seconds"] = 121
            elif case == "total":
                request["quality"]["budget"]["total_seconds"] = 120
                baseline["elapsed_seconds"] = candidate["elapsed_seconds"] = 100
                baseline["protocol_sha256"] = candidate["protocol_sha256"] = workbench.quality_sha256(request)
            else:
                request["production"]["max_revisions"] = 0
            self.assertEqual(self.comparison(request, baseline, candidate)["next_action"], "stop_blocked")

    def test_fixed_protocol_and_specification_drift_block(self):
        request = self.request()
        baseline = self.trial(request, "base", [4, 4])
        ledger = self.ledger(request, baseline)
        request["quality"]["protocol"]["lighting"] = "different dramatic light"
        result = workbench.compare_quality(request, ledger, self.root)
        self.assertFalse(result["quality_target_met"])
        self.assertTrue(result["blockers"])

    def test_missing_view_score_or_subject_binding_blocks(self):
        for case in ("view", "score", "subject"):
            request = self.request()
            baseline = self.trial(request, "base", [4, 4])
            if case == "view":
                del baseline["previews"]["back"]
            elif case == "score":
                del baseline["scores"]["materials"]
            else:
                baseline["evidence"]["subject_artifacts"] = []
            self.assertFalse(self.comparison(request, baseline)["quality_target_met"])

    def test_reference_preview_or_model_drift_blocks(self):
        for path in ("runs/qa/reference.png", "runs/qa/base-back.png", "assets/processed/base.glb"):
            request = self.request()
            baseline = self.trial(request, "base", [4, 4])
            (self.root / path).write_bytes(b"changed fixture")
            self.assertFalse(self.comparison(request, baseline)["quality_target_met"])

    def test_art_target_can_improve_without_claiming_art_acceptance(self):
        request = self.request()
        baseline = self.trial(request, "base", [2, 2])
        candidate = self.trial(request, "better", [4, 4], "base")
        candidate["evidence"]["checks"]["art_match"]["status"] = "fail"
        result = self.comparison(request, baseline, candidate)
        self.assertEqual(result["best_trial_id"], "better")
        self.assertFalse(result["quality_target_met"])

    def test_art_gain_cannot_override_geometry_or_runtime_gate(self):
        for gate in ("geometry_materials", "target_environment"):
            request = self.request()
            if gate == "target_environment":
                request["delivery"] = {"scope": "target_environment", "formats": ["glb"],
                                       "target_environment": {"name": "fixture engine", "version": "1", "verification_context": "unit scene"}}
            baseline = self.trial(request, "base", [2, 2])
            candidate = self.trial(request, "better", [5, 5], "base")
            candidate["evidence"]["checks"][gate]["status"] = "fail"
            self.assertEqual(self.comparison(request, baseline, candidate)["best_trial_id"], "base")

    def test_saturated_or_equal_scores_are_not_improvements(self):
        request = self.request()
        baseline = self.trial(request, "base", [5, 5])
        candidate = self.trial(request, "equal", [5, 5], "base")
        result = self.comparison(request, baseline, candidate)
        self.assertEqual(result["trials"][1]["decision"], "discard")
        self.assertEqual(result["best_trial_id"], "base")

    def test_known_gate_failure_can_be_followed_by_valid_revision(self):
        request = self.request()
        baseline = self.trial(request, "base", [2, 2])
        bad = self.trial(request, "bad", [4, 4], "base")
        bad["evidence"]["checks"]["geometry_materials"]["status"] = "fail"
        fixed = self.trial(request, "fixed", [4, 4], "base")
        result = self.comparison(request, baseline, bad, fixed)
        self.assertEqual(result["trials"][1]["decision"], "discard")
        self.assertIn("geometry_materials", result["trials"][1]["failed_gates"])
        self.assertEqual(result["best_trial_id"], "fixed")
        self.assertTrue(result["quality_target_met"])

    def test_saturated_baseline_gate_repair_can_be_kept_without_visual_gain(self):
        request = self.request()
        baseline = self.trial(request, "base", [5, 5])
        baseline["evidence"]["checks"]["geometry_materials"]["status"] = "fail"
        fixed = self.trial(request, "fixed", [5, 5], "base")
        result = self.comparison(request, baseline, fixed)
        self.assertEqual(result["trials"][1]["decision"], "keep_for_gate_repair")
        self.assertTrue(result["quality_target_met"])
        fixed["scores"]["silhouette"]["value"] = 4
        self.assertEqual(self.comparison(request, baseline, fixed)["best_trial_id"], "base")

    def test_quality_delivery_requires_ledger_and_exact_evaluated_bytes(self):
        request = self.request()
        baseline = self.trial(request, "base", [4, 4])
        ledger = self.ledger(request, baseline)
        self.assertEqual(workbench.assess(request, baseline["evidence"], self.root)["decision"], "not_ready")
        evidence = self.delivery(request, ledger, baseline)
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "eligible_for_delivery_review")
        evidence["deliverables"] = [self.artifact("assets/processed/rock.glb")]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_quality_delivery_allows_copy_of_evaluated_model(self):
        request = self.request()
        baseline = self.trial(request, "base", [4, 4])
        evidence = self.delivery(request, self.ledger(request, baseline), baseline)
        folder = self.root / "deliveries/unit-rock/v001"
        folder.mkdir(parents=True)
        (folder / "rock.glb").write_bytes((self.root / "assets/processed/base.glb").read_bytes())
        evidence["deliverables"] = [self.artifact("deliveries/unit-rock/v001/rock.glb")]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "eligible_for_delivery_review")

    def test_malformed_contracts_and_scores_are_rejected(self):
        for bad in (None, [], {"schema_version": 1}, {"schema_version": True}):
            request = self.request()
            request["quality"] = bad
            self.assertTrue(workbench.validate_request(request))
        for value in (True, float("nan"), "5", 6):
            request = self.request()
            baseline = self.trial(request, "base", [4, 4])
            baseline["scores"]["silhouette"]["value"] = value
            self.assertFalse(self.comparison(request, baseline)["quality_target_met"])

    def test_intake_quality_flag_adds_draft_without_claiming_ready(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = workbench.main(["intake", "--id", "fixture-quality", "--brief", "品質草稿", "--quality"])
        self.assertEqual(code, 0)
        request = json.loads(output.getvalue())
        self.assertEqual(workbench.validate_request(request), [])
        self.assertEqual(request["quality"]["status"], "draft")
        self.assertTrue(workbench.production_plan(request)["pending"])

    def test_draft_quality_and_boolean_schema_never_pass(self):
        request = self.request()
        request["quality"]["status"] = "draft"
        baseline = self.trial(request, "base", [4, 4])
        self.assertFalse(self.comparison(request, baseline)["quality_target_met"])
        request["quality"]["schema_version"] = True
        self.assertTrue(workbench.validate_request(request))

    def test_changed_or_missing_delivery_texture_is_blocked(self):
        request = self.request()
        baseline = self.trial(request, "base", [4, 4])
        texture = "assets/processed/color.png"
        (self.root / texture).write_bytes(b"original unit texture")
        baseline["evidence"]["deliverables"].append(self.artifact(texture))
        baseline["evidence"]["subject_artifacts"] = deepcopy(baseline["evidence"]["deliverables"])
        ledger = self.ledger(request, baseline)
        for case in ("missing", "changed"):
            evidence = self.delivery(request, ledger, baseline)
            evidence["deliverables"] = evidence["deliverables"][:1]
            if case == "changed":
                other = "assets/processed/other.png"
                (self.root / other).write_bytes(b"different unit texture")
                evidence["deliverables"].append(self.artifact(other))
            self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_malformed_delivery_artifact_returns_not_ready(self):
        request = self.request()
        baseline = self.trial(request, "base", [4, 4])
        evidence = self.delivery(request, self.ledger(request, baseline), baseline)
        del evidence["deliverables"][0]["sha256"]
        self.assertEqual(workbench.assess(request, evidence, self.root)["decision"], "not_ready")

    def test_empty_ledger_and_duplicate_trial_never_pass(self):
        request = self.request()
        self.assertFalse(self.comparison(request)["quality_target_met"])
        baseline = self.trial(request, "base", [4, 4])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.comparison(request, baseline, baseline)


if __name__ == "__main__":
    unittest.main()
