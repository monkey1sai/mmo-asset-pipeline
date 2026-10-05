from copy import deepcopy
import unittest

from test_workbench import specified, workbench


class ApiCreationTests(unittest.TestCase):
    def test_only_generation_routes_prepare_api_work(self):
        for route in workbench.ROUTES:
            request = specified()
            request["production"]["route"] = route
            plan = workbench.production_plan(request)
            self.assertEqual("creation_workflow" in plan, route in {"generate", "split_then_generate"})
            self.assertFalse(plan["paid_submission_authorized_by_this_plan"])

    def test_design_preserves_constraints_without_fabricating_payload(self):
        request = specified()
        request["production"]["route"] = "generate"
        request["style"]["must_not_have"] = ["背景、文字"]
        before = deepcopy(request)
        plan = workbench.production_plan(request)
        creation = plan["creation_workflow"]
        job = creation["jobs"][0]
        self.assertEqual(job["design_brief"]["style"], request["style"])
        self.assertIsNone(job["prompt"])
        self.assertIsNone(job["operation_id"])
        self.assertEqual(job["reference_images"], [])
        self.assertFalse(creation["submission_ready"])
        self.assertEqual(request, before)
        job["design_brief"]["style"]["must_not_have"].append("test")
        self.assertEqual(request, before)

    def test_split_keeps_part_pivots_and_whole_asset_budget_separate(self):
        request = specified()
        request["production"]["route"] = "split_then_generate"
        request["spec"]["parts"] = [
            {"id": "frame", "pivot": "bottom", "motion": None},
            {"id": "door", "pivot": "hinge", "motion": {"kind": "rotation", "axis": "+Y", "range_deg": [0, 90]}},
        ]
        jobs = workbench.production_plan(request)["creation_workflow"]["jobs"]
        self.assertEqual([j["subject_id"] for j in jobs], ["frame", "door"])
        self.assertEqual(jobs[1]["design_brief"]["part"]["pivot"], "hinge")
        self.assertEqual(jobs[1]["design_brief"]["whole_asset_spec"]["target_triangles"], 1500)

    def test_missing_parts_stays_pending(self):
        request = specified()
        request["production"]["route"] = "split_then_generate"
        plan = workbench.production_plan(request)
        self.assertTrue(plan["pending"])
        self.assertEqual(plan["creation_workflow"]["jobs"], [])

    def test_api_connection_is_not_credit_or_spending_approval(self):
        request = specified()
        request["production"]["route"] = "generate"
        creation = workbench.production_plan(request)["creation_workflow"]
        self.assertEqual(creation["capability_state"], "requires_current_probe")
        self.assertEqual(creation["authorization_state"], "requires_existing_scope_check")
        self.assertEqual(creation["credit_pool_state"], "requires_monthly_credit_evidence")
        self.assertEqual(creation["unknown_submission_policy"], "reconcile_original_operation_never_resubmit")
        self.assertEqual(creation["website_policy"], "credit_evidence_or_documented_fallback_only")

    def test_large_repair_fallback_does_not_submit_or_reset_budget(self):
        request = specified()
        request["production"]["route"] = "modify"
        before = deepcopy(request)
        plan = workbench.production_plan(request)
        policy = plan["reconstruction_fallback"]
        self.assertFalse(policy["automatic_paid_retry"])
        self.assertFalse(plan["paid_submission_authorized_by_this_plan"])
        self.assertIn("new_phase_requires_user_scope", policy["budget"])
        self.assertNotIn("creation_workflow", plan)
        self.assertEqual(request, before)

    def test_generated_shape_preserves_animation_and_current_adapter_gate(self):
        request = specified()
        request["production"]["route"] = "generate"
        policy = workbench.production_plan(request)["creation_workflow"]["reconstruction_policy"]
        self.assertIn("probe_current_adapter", policy["capabilities"])
        self.assertIn("does_not_supply_verified_rig", policy["animation"])
        self.assertEqual(policy["steps"][0], "preserve_failed_candidate_and_evidence")


if __name__ == "__main__":
    unittest.main()
