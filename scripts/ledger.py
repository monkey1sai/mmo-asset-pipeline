"""Operation ledger：付費操作的唯一帳本（runs/hyper3d/operations），只讀與判斷。

Hyper3D client 是唯一寫入者；本模組決定哪些操作阻擋離線規劃、保留哪些需求與 catalog 資產。
無法辨識或推導失敗的紀錄一律視為阻擋，不猜測其狀態。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity  # noqa: E402

OPERATIONS = "runs/hyper3d/operations"
PLANS = "runs/hyper3d/plans"
STATES = {"prepared", "pending", "submitted", "processing", "complete", "download_partial", "downloaded", "failed", "cancelled", "unknown"}
BLOCKING = {"pending", "unknown"}
LEGACY_FIELDS = {"schema_version", "source", "operation_id", "state", "request_id", "catalog_asset_id", "task_uuid", "consumed_credits", "evidence", "imported_utc", "note"}


@dataclass(frozen=True)
class Operation:
    operation_id: str
    state: str | None
    source: str
    request_id: str | None = None
    catalog_asset_id: str | None = None
    fingerprint: str | None = None
    evidence: tuple = ()
    problem: str | None = None

    @property
    def blocks_planning(self) -> bool:
        return self.problem is not None or self.state in BLOCKING

    def summary(self) -> dict:
        return {"operation_id": self.operation_id, "state": self.state, "source": self.source,
                "request_id": self.request_id, "catalog_asset_id": self.catalog_asset_id, "problem": self.problem}


class Ledger:
    def __init__(self, root: Path, operations: list[Operation]):
        self.root = root
        self.operations = operations

    def blocking(self) -> list[Operation]:
        return [op for op in self.operations if op.blocks_planning]

    def reserved_requests(self) -> set[str]:
        return {op.request_id for op in self.operations if op.request_id}

    def reserved_catalog_assets(self) -> set[str]:
        return {op.catalog_asset_id for op in self.operations if op.catalog_asset_id}

    def for_request(self, request_id: str) -> list[Operation]:
        return [op for op in self.operations if op.request_id == request_id]

    def verify_evidence(self) -> list[str]:
        """證據雜湊另行核對：證據被合理編輯時回報漂移，但不阻擋規劃。"""
        issues = []
        for op in self.operations:
            for item in op.evidence:
                try:
                    if identity.file_digest(identity.recorded_path(self.root, item["path"])) != item["sha256"]:
                        issues.append(f"{op.operation_id}: evidence hash mismatch: {item['path']}")
                except (OSError, ValueError):
                    issues.append(f"{op.operation_id}: evidence unavailable: {item['path']}")
        return issues


def _optional_id(value: object) -> bool:
    return value is None or identity.is_asset_id(value)


def _legacy(name: str, record: dict) -> Operation:
    evidence = record.get("evidence")
    valid = (set(record) == LEGACY_FIELDS and record["schema_version"] == 1 and record["state"] in STATES
             and _optional_id(record["request_id"]) and _optional_id(record["catalog_asset_id"])
             and isinstance(evidence, list) and evidence
             and all(isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("sha256"), str)
                     and re.fullmatch(r"[a-f0-9]{64}", e["sha256"]) for e in evidence))
    if not valid:
        return Operation(name, record.get("state") if isinstance(record.get("state"), str) else None, "legacy_import", problem="LEGACY_IMPORT_INVALID")
    return Operation(name, record["state"], "legacy_import", record["request_id"], record["catalog_asset_id"],
                     evidence=tuple(record["evidence"]))


def _hyper3d(root: Path, name: str, record: dict) -> Operation:
    state = record.get("state")

    def broken(code: str) -> Operation:
        return Operation(name, state if isinstance(state, str) else None, "hyper3d", fingerprint=record.get("fingerprint"), problem=code)

    if state not in STATES:
        return broken("STATE_INVALID")
    try:
        plan = identity.read_json(identity.recorded_path(root, f"{PLANS}/{name}.json"))
    except FileNotFoundError:
        return broken("PLAN_MISSING")
    except (OSError, ValueError):
        return broken("PLAN_INTEGRITY_INVALID")
    expected = plan.pop("plan_sha256", None)
    request = plan.get("request")
    if expected is None or identity.json_digest(plan) != expected or expected != record.get("plan_sha256") or not isinstance(request, dict):
        return broken("PLAN_INTEGRITY_INVALID")
    try:
        request_data = identity.read_json(identity.recorded_path(root, request.get("path")))
    except FileNotFoundError:
        return broken("REQUEST_MISSING")
    except (OSError, ValueError):
        return broken("REQUEST_INVALID")
    if not identity.is_asset_id(request_data.get("id")):
        return broken("REQUEST_ID_INVALID")
    if not _optional_id(request_data.get("catalog_asset_id")):
        return broken("CATALOG_ASSET_ID_INVALID")
    return Operation(name, state, "hyper3d", request_data["id"], request_data.get("catalog_asset_id"), record.get("fingerprint"))


def load(root: Path) -> Ledger:
    root = Path(root).resolve()
    directory = root / OPERATIONS
    operations = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        name = path.stem
        try:
            record = identity.read_json(path)
        except (OSError, ValueError):
            operations.append(Operation(name, None, "unreadable", problem="RECORD_INVALID"))
            continue
        if record.get("operation_id") != name or not identity.is_asset_id(name):
            operations.append(Operation(name, None, "unreadable", problem="OPERATION_ID_MISMATCH"))
        elif record.get("source") == "legacy_import":
            operations.append(_legacy(name, record))
        else:
            operations.append(_hyper3d(root, name, record))
    return Ledger(root, operations)
