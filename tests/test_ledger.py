"""Operation ledger: one store, derived request identity, blocking and reservation rules."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import identity  # noqa: E402
import ledger  # noqa: E402


class Workspace:
    """Synthetic records only; no paid operation or real evidence."""

    def __init__(self, root: Path):
        self.root = root

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def request(self, rid, catalog_asset_id=None):
        value = {"id": rid}
        if catalog_asset_id is not None:
            value["catalog_asset_id"] = catalog_asset_id
        self.write(f"requests/{rid}.json", value)
        return f"requests/{rid}.json"

    def hyper3d(self, op, state, request_path, fingerprint="f" * 64):
        plan = {"schema_version": 2, "operation_id": op, "request": {"path": request_path, "request_sha256": "0" * 64}}
        plan["plan_sha256"] = identity.json_digest(plan)
        self.write(f"runs/hyper3d/plans/{op}.json", plan)
        self.write(f"runs/hyper3d/operations/{op}.json", {"schema_version": 2, "operation_id": op, "state": state,
                                                          "plan_sha256": plan["plan_sha256"], "fingerprint": fingerprint})

    def legacy(self, op, state, request_id=None, catalog_asset_id=None, evidence=None):
        proof = self.write("runs/evidence.json", {"proof": True})
        record = {"schema_version": 1, "source": "legacy_import", "operation_id": op, "state": state,
                  "request_id": request_id, "catalog_asset_id": catalog_asset_id, "task_uuid": None, "consumed_credits": None,
                  "evidence": evidence if evidence is not None else [{"path": "runs/evidence.json", "sha256": hashlib.sha256(proof.read_bytes()).hexdigest()}],
                  "imported_utc": "2026-10-06T00:00:00+00:00", "note": "synthetic"}
        self.write(f"runs/hyper3d/operations/{op}.json", record)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.ws = Workspace(Path(directory.name).resolve())

    def load(self):
        return ledger.load(self.ws.root)

    def problems(self):
        return {op.operation_id: op.problem for op in self.load().blocking()}

    def test_empty_workspace_has_no_operations(self):
        loaded = self.load()
        self.assertEqual((loaded.blocking(), loaded.reserved_requests(), loaded.reserved_catalog_assets()), ([], set(), set()))

    def test_hyper3d_record_derives_request_and_catalog_identity(self):
        self.ws.hyper3d("op-1", "downloaded", self.ws.request("rock-r01", "shared.prop.rock"))
        loaded = self.load()
        self.assertEqual(loaded.blocking(), [])
        self.assertEqual(loaded.reserved_requests(), {"rock-r01"})
        self.assertEqual(loaded.reserved_catalog_assets(), {"shared.prop.rock"})
        self.assertEqual([op.operation_id for op in loaded.for_request("rock-r01")], ["op-1"])

    def test_pending_and_unknown_block_planning(self):
        request = self.ws.request("rock-r01")
        self.ws.hyper3d("op-pending", "pending", request)
        self.ws.hyper3d("op-unknown", "unknown", request)
        self.assertEqual(self.problems(), {"op-pending": None, "op-unknown": None})

    def test_failed_and_cancelled_reserve_without_blocking(self):
        self.ws.hyper3d("op-failed", "failed", self.ws.request("a-r01"))
        self.ws.legacy("op-cancelled", "cancelled", catalog_asset_id="shared.prop.b")
        loaded = self.load()
        self.assertEqual(loaded.blocking(), [])
        self.assertEqual(loaded.reserved_requests(), {"a-r01"})
        self.assertEqual(loaded.reserved_catalog_assets(), {"shared.prop.b"})

    def test_broken_derivation_blocks_with_stable_code(self):
        request = self.ws.request("rock-r01")
        self.ws.hyper3d("no-plan", "downloaded", request)
        (self.ws.root / "runs/hyper3d/plans/no-plan.json").unlink()
        self.ws.hyper3d("tampered", "downloaded", request)
        plan = json.loads((self.ws.root / "runs/hyper3d/plans/tampered.json").read_text(encoding="utf-8"))
        plan["request"]["path"] = "requests/other.json"
        self.ws.write("runs/hyper3d/plans/tampered.json", plan)
        self.ws.hyper3d("no-request", "downloaded", "requests/missing.json")
        self.ws.write("requests/bad-catalog.json", {"id": "bad-catalog", "catalog_asset_id": "Not Valid"})
        self.ws.hyper3d("bad-catalog", "downloaded", "requests/bad-catalog.json")
        self.assertEqual(self.problems(), {"no-plan": "PLAN_MISSING", "tampered": "PLAN_INTEGRITY_INVALID",
                                           "no-request": "REQUEST_MISSING", "bad-catalog": "CATALOG_ASSET_ID_INVALID"})

    def test_unknown_vocabulary_or_unreadable_record_blocks(self):
        request = self.ws.request("rock-r01")
        self.ws.hyper3d("completed-spelling", "completed", request)
        self.ws.hyper3d("acceptance-state", "art_accepted", request)
        self.ws.write("runs/hyper3d/operations/garbled.json", "{not json")
        self.ws.hyper3d("renamed", "downloaded", request)
        (self.ws.root / "runs/hyper3d/operations/renamed.json").rename(self.ws.root / "runs/hyper3d/operations/other-name.json")
        self.assertEqual(self.problems(), {"completed-spelling": "STATE_INVALID", "acceptance-state": "STATE_INVALID",
                                           "garbled": "RECORD_INVALID", "other-name": "OPERATION_ID_MISMATCH"})

    def test_lock_and_temporary_files_are_not_records(self):
        self.ws.write("runs/hyper3d/operations/.client.lock", "")
        self.ws.write("runs/hyper3d/operations/op-1.json.tmp", "{")
        self.assertEqual(self.load().blocking(), [])

    def test_legacy_import_uses_explicit_identity(self):
        self.ws.legacy("bootstrap-cl-brazier-v001", "downloaded", catalog_asset_id="cl-brazier")
        self.ws.legacy("legacy-task-94016052", "complete")
        loaded = self.load()
        self.assertEqual(loaded.blocking(), [])
        self.assertEqual(loaded.reserved_catalog_assets(), {"cl-brazier"})
        self.assertEqual(loaded.reserved_requests(), set())

    def test_malformed_legacy_import_blocks(self):
        self.ws.legacy("no-evidence", "downloaded", catalog_asset_id="cl-brazier", evidence=[])
        self.ws.legacy("bad-request", "downloaded", request_id="Bad Id")
        self.assertEqual(self.problems(), {"no-evidence": "LEGACY_IMPORT_INVALID", "bad-request": "LEGACY_IMPORT_INVALID"})

    def test_verify_evidence_reports_hash_drift_without_blocking(self):
        self.ws.legacy("bootstrap-a", "downloaded", catalog_asset_id="cl-brazier")
        self.assertEqual(self.load().verify_evidence(), [])
        self.ws.write("runs/evidence.json", {"proof": "edited"})
        loaded = self.load()
        self.assertEqual(loaded.blocking(), [])
        self.assertEqual(loaded.verify_evidence(), ["bootstrap-a: evidence hash mismatch: runs/evidence.json"])


if __name__ == "__main__":
    unittest.main()
