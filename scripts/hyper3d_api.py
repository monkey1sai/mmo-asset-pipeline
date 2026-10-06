"""Workspace-scoped Hyper3D client using the installed Windows DPAPI provider.

No credentials, subscription keys, or signed URLs are persisted in the repo.
CLI consent flags record existing human authority; they do not grant it.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity  # noqa: E402

PROVIDER = Path.home() / ".codex/tools/hyper3d-api/rodin_api.py"
PROVIDER_SHA256 = "45247a8def85815d03bb296767aec5f79699a518489f2e68bddad3ff39b09e3a"
STATE_ROOT = PROVIDER.parent / "state"
MAX_IMAGE = 20 * 1024 * 1024
MAX_FILE = 1024 * 1024 * 1024
ENUMS = {
    "tier": {"Gen-2.5-Extreme-Low", "Gen-2.5-Low", "Gen-2.5-Medium", "Gen-2.5-High", "Gen-2.5-Extreme-High"},
    "mesh_mode": {"Raw", "Quad"},
    "geometry_file_format": {"glb", "usdz", "fbx", "obj", "stl"},
    "material": {"PBR", "Shaded", "All", "Hybrid", "None"},
    "texture_mode": {"legacy", "extreme-low", "low", "medium", "high", "extreme-high"},
    "quality": {"high", "medium", "low", "extra-low"},
    "is_symmetric": {"symmetric", "balanced", "asymmetric", "unknown"},
}
BOOLS = {"TAPose", "quad_normal", "texture_delight", "preview_render", "uhd_texture"}
PLAN_SCHEMA = 2
ACTIVE = {"pending", "unknown", "submitted", "processing", "complete", "download_partial", "downloaded"}
EXTENSIONS = {".glb", ".gltf", ".bin", ".obj", ".mtl", ".fbx", ".usdz", ".stl", ".png", ".jpg", ".jpeg", ".webp", ".zip"}


class SafeError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    # identity 錯誤在此 seam 轉成 SafeError 代碼；其他例外仍由 main 遮蔽。
    try:
        return identity.read_json(path)
    except identity.IdentityError as exc:
        raise SafeError(str(exc)) from None


# 已棄用：codex/art-quality-loop 的 RO 腳本仍匯入下列名稱；遷移到 identity 後移除。
file_sha = identity.file_digest
canonical = identity.canonical_json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = identity.canonical_json(value) + b"\n"
    if exclusive:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            import os
            os.fsync(stream.fileno())
    else:
        # Public records only. The private state uses one exact authorized file.
        temp = path.with_name(path.name + ".tmp")
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        temp.replace(path)


def load_provider():
    # Importing the supported provider must not create global __pycache__ files.
    sys.dont_write_bytecode = True
    if not PROVIDER.is_file() or identity.file_digest(PROVIDER) != PROVIDER_SHA256:
        raise SafeError("PROVIDER_VERSION_REQUIRES_REVIEW")
    spec = importlib.util.spec_from_file_location("hyper3d_supported_provider", PROVIDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_id(value):
    if not identity.is_asset_id(value):
        raise SafeError("OPERATION_ID_INVALID")
    return value


def number(value, code):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise SafeError(code)
    return value


def parameters(value, image_count):
    if not isinstance(value, dict) or set(value) - (set(ENUMS) | BOOLS | {"quality_override", "seed", "prompt", "image_label"}):
        raise SafeError("PARAMETERS_UNSUPPORTED")
    result = dict(value)
    if "tier" not in result:
        raise SafeError("EXPLICIT_GEN25_TIER_REQUIRED")
    for key, choices in ENUMS.items():
        if key in result and (not isinstance(result[key], str) or result[key] not in choices):
            raise SafeError("PARAMETER_ENUM_INVALID")
    for key in BOOLS:
        if key in result and not isinstance(result[key], bool):
            raise SafeError("PARAMETER_BOOLEAN_INVALID")
    for key in ("quality_override", "seed"):
        if key in result and (isinstance(result[key], bool) or not isinstance(result[key], int)):
            raise SafeError("PARAMETER_INTEGER_REQUIRED")
    if "quality_override" in result:
        maximum = 2000000 if result["tier"] in {"Gen-2.5-High", "Gen-2.5-Extreme-High"} else 1000000
        if result.get("mesh_mode", "Raw") == "Quad":
            maximum = min(maximum, 200000)
        if not 500 <= result["quality_override"] <= maximum:
            raise SafeError("FACE_COUNT_INVALID")
    if "seed" in result and not 0 <= result["seed"] <= 65535:
        raise SafeError("SEED_INVALID")
    prompt = result.get("prompt", "")
    if not isinstance(prompt, str) or len(prompt) > 1024 or "\x00" in prompt or (not image_count and not prompt.strip()):
        raise SafeError("PROMPT_INVALID")
    if "image_label" in result:
        labels = result["image_label"]
        if not isinstance(labels, list) or len(labels) != image_count or not image_count or any(x not in {"F", "FL", "FR", "B", "BL", "BR", "L", "R", "U", "D", "?"} for x in labels):
            raise SafeError("IMAGE_LABEL_INVALID")
    # Public estimate is not a reservation. Actual consumed is service evidence.
    estimate = 0.5 + (0.5 if result["tier"] == "Gen-2.5-Extreme-High" else 0) + (2.0 if result.get("texture_mode") == "extreme-high" else 0)
    return result, estimate


class Client:
    def __init__(self, workspace, provider=None, state_root=None):
        self.root = Path(workspace).resolve(strict=True)
        self.provider = provider
        self.state_root = Path(state_root) if state_root is not None else STATE_ROOT
        self.operations = self.path("runs/hyper3d/operations")
        self.plans = self.path("runs/hyper3d/plans")

    def path(self, relative):
        try:
            return identity.recorded_path(self.root, relative)
        except identity.IdentityError as exc:
            raise SafeError(str(exc)) from None

    def transport(self):
        if self.provider is None:
            self.provider = load_provider()
        return self.provider

    def record_path(self, operation):
        return self.path("runs/hyper3d/operations/" + valid_id(operation) + ".json")

    def private_path(self, operation):
        path = self.state_root / (valid_id(operation) + ".dpapi")
        if self.state_root.resolve() != self.state_root.absolute() or path.is_symlink():
            raise SafeError("PRIVATE_STATE_PATH_UNSAFE")
        return path

    @contextmanager
    def lock(self):
        self.operations.mkdir(parents=True, exist_ok=True)
        path = self.path("runs/hyper3d/operations/.client.lock")
        try:
            with path.open("xb") as stream:
                stream.write(b"exclusive client operation; inspect state before removing stale lock\n")
        except FileExistsError:
            raise SafeError("CLIENT_BUSY_OR_STALE_LOCK_REQUIRES_REVIEW") from None
        try:
            yield
        finally:
            path.unlink()

    def balance(self):
        result = self.transport().balance()
        if result.get("authenticated") is not True:
            raise SafeError("AUTHENTICATION_UNVERIFIED")
        return {"authenticated": True, "balance": number(result.get("balance"), "BALANCE_INVALID"), "observed_utc": now(), "charged": False, "pool_breakdown": "not_returned"}

    def capabilities(self):
        return {"provider_path": str(PROVIDER), "provider_sha256": PROVIDER_SHA256,
                "implemented": ["balance", "image_to_3d", "text_to_3d", "Raw", "Quad", "TAPose", "symmetry", "status", "download"],
                "unavailable_transport": ["bang", "texture_only", "agentic"],
                "runtime_generation_verified": False, "TAPose_supplies_verified_rig": False,
                "credential_provider": "installed Windows DPAPI CurrentUser provider; no key read by CLI",
                "private_state_root": str(self.state_root), "automatic_paid_retry": False}

    def image(self, relative):
        path = self.path(relative)
        if not relative.startswith("assets/") or not path.is_file() or not 0 < path.stat().st_size <= MAX_IMAGE:
            raise SafeError("IMAGE_PATH_OR_SIZE_INVALID")
        data = path.read_bytes()
        suffix = path.suffix.lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix)
        if mime is None or not ((suffix == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n")) or (suffix in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8\xff")) or (suffix == ".webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP")):
            raise SafeError("IMAGE_TYPE_INVALID")
        return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "mime": mime}

    def prepare(self, spec):
        if set(spec) != {"operation_id", "request", "images", "output_directory", "parameters", "authorization"}:
            raise SafeError("SPEC_FIELDS_INVALID")
        operation = valid_id(spec["operation_id"])
        images = spec["images"]
        if not isinstance(images, list) or len(images) > 5 or any(not isinstance(x, str) for x in images) or len(set(images)) != len(images):
            raise SafeError("IMAGE_COUNT_INVALID")
        request = self.path(spec["request"])
        if not spec["request"].startswith("requests/") or not request.is_file():
            raise SafeError("REQUEST_FILE_REQUIRED")
        authorization = spec["authorization"]
        if not isinstance(authorization, dict) or set(authorization) != {"spending_scope", "credit_pool", "no_topup_or_upgrade"} or not isinstance(authorization["spending_scope"], str) or not authorization["spending_scope"].strip() or authorization["credit_pool"] not in {"existing_monthly", "existing_monthly_or_regular"} or authorization["no_topup_or_upgrade"] is not True:
            raise SafeError("EXISTING_SPENDING_SCOPE_REQUIRED")
        output = self.path(spec["output_directory"])
        if not spec["output_directory"].startswith("assets/raw/") or output.exists():
            raise SafeError("NEW_RAW_OUTPUT_REQUIRED")
        params, estimate = parameters(spec["parameters"], len(images))
        request_data = read_json(request)
        plan = {"schema_version": PLAN_SCHEMA, "operation_id": operation, "created_utc": now(),
                "request": {"path": spec["request"], "request_sha256": identity.json_digest(request_data), "quality_sha256": identity.json_digest(request_data.get("quality"))},
                "images": [self.image(x) for x in images], "output_directory": spec["output_directory"],
                "parameters": params, "authorization": dict(authorization), "estimated_credits": estimate,
                "provider_sha256": PROVIDER_SHA256, "private_state_file": str(self.private_path(operation)),
                "submission_ready": False, "required_next_gate": "exact private state file authorization and preflight"}
        plan["fingerprint"] = identity.json_digest({"request": plan["request"], "images": plan["images"], "parameters": params})
        plan["plan_sha256"] = identity.json_digest(plan)
        path = self.path("runs/hyper3d/plans/" + operation + ".json")
        write_json(path, plan, exclusive=True)
        return {"plan": str(path), "operation_id": operation, "estimated_credits": estimate, "private_state_file": plan["private_state_file"], "submission_ready": False}

    def plan(self, operation):
        path = self.path("runs/hyper3d/plans/" + valid_id(operation) + ".json")
        plan = read_json(path)
        expected = plan.pop("plan_sha256")
        if identity.json_digest(plan) != expected or plan["operation_id"] != operation or plan["provider_sha256"] != PROVIDER_SHA256:
            raise SafeError("PLAN_INTEGRITY_INVALID")
        plan["plan_sha256"] = expected
        if plan.get("schema_version") != PLAN_SCHEMA:
            # v1 以檔案 bytes 綁定需求；須重新 prepare 才能以 Request digest 提交。
            raise SafeError("PLAN_SCHEMA_OUTDATED")
        if identity.json_digest(read_json(self.path(plan["request"]["path"]))) != plan["request"]["request_sha256"] or any(self.image(x["path"]) != x for x in plan["images"]):
            raise SafeError("INPUT_CHANGED_AFTER_PREPARATION")
        parameters(plan["parameters"], len(plan["images"]))
        if self.path(plan["output_directory"]).exists():
            raise SafeError("NEW_RAW_OUTPUT_REQUIRED")
        if str(self.private_path(operation)) != plan["private_state_file"]:
            raise SafeError("PRIVATE_STATE_BINDING_INVALID")
        return plan

    def multipart(self, plan):
        boundary = "hyper3d" + uuid.uuid4().hex
        chunks = []
        for key, value in plan["parameters"].items():
            text = json.dumps(value, ensure_ascii=False, allow_nan=False) if not isinstance(value, str) else value
            chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{text}\r\n').encode("utf-8"))
        for index, item in enumerate(plan["images"]):
            path = self.path(item["path"])
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise SafeError("INPUT_CHANGED_AFTER_PREPARATION")
            chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="images"; filename="input_{index}{path.suffix.lower()}"\r\nContent-Type: {item["mime"]}\r\n\r\n').encode("ascii") + data + b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode("ascii"))
        return b"".join(chunks), "multipart/form-data; boundary=" + boundary

    def private_write(self, path, value, exclusive):
        blob = self.transport().protected_bytes(identity.canonical_json(value))
        with path.open("xb" if exclusive else "wb") as stream:
            stream.write(blob)
            stream.flush()
            import os
            os.fsync(stream.fileno())

    def submit(self, operation, spending_authorized=False, authorized_state_file=None):
        plan = self.plan(operation)
        private = self.private_path(operation)
        if not spending_authorized or authorized_state_file != str(private):
            raise SafeError("EXACT_PRIVATE_STATE_AUTHORIZATION_REQUIRED")
        with self.lock():
            record_path = self.record_path(operation)
            if record_path.exists() or private.exists():
                raise SafeError("OPERATION_ALREADY_EXISTS_NEVER_RESUBMIT")
            for path in self.operations.glob("*.json"):
                other = read_json(path)
                if other.get("state") in {"pending", "unknown"}:
                    raise SafeError("UNRESOLVED_OPERATION_NEVER_RESUBMIT")
                if other.get("fingerprint") == plan["fingerprint"] and other.get("state") in ACTIVE:
                    raise SafeError("MATCHING_ACTIVE_OPERATION_NEVER_RESUBMIT")
            if not private.parent.is_dir():
                raise SafeError("PRIVATE_STATE_DIRECTORY_UNAVAILABLE")
            body, content_type = self.multipart(plan)
            if plan["authorization"]["credit_pool"] == "existing_monthly":
                raise SafeError("MONTHLY_POOL_EVIDENCE_UNAVAILABLE")
            before = self.balance()
            if before["balance"] < plan["estimated_credits"]:
                raise SafeError("INSUFFICIENT_EXISTING_BALANCE")
            # First prove DPAPI and reserve the ONE authorized filename before charging.
            marker = {"operation_id": operation, "fingerprint": plan["fingerprint"], "state": "reserved"}
            probe = self.transport().protected_bytes(identity.canonical_json(marker))
            if self.transport().protected_bytes(probe, decrypt=True) != identity.canonical_json(marker):
                raise SafeError("PRIVATE_STATE_PROTECTION_FAILED")
            self.private_write(private, marker, True)
            record = {"schema_version": PLAN_SCHEMA, "operation_id": operation, "fingerprint": plan["fingerprint"],
                      "plan_sha256": plan["plan_sha256"], "state": "pending", "started_utc": now(),
                      "estimated_credits": plan["estimated_credits"], "consumed_credits": None, "cost_state": "unverified",
                      "balance_before": before, "task_uuid": None, "downloads": [],
                      "authorization": {**plan["authorization"], "authorized_private_state_file": str(private)},
                      "envelope": {"destination": "https://api.hyper3d.com/api/v2/rodin", "purpose": "request-bound art generation",
                                   "allowed_operations": ["one generation", "same-task status", "completed result download"],
                                   "data_transmitted": ["prepared image bytes", "validated generation parameters"],
                                   "forbidden_operations": ["topup", "upgrade", "publish", "credentials in public records", "Git mutation"],
                                   "stop_conditions": ["unknown submission", "unexpected account or destination", "file collision"]}}
            write_json(record_path, record, exclusive=True)
            failure_stage = "charged_request"
            try:
                result = self.transport().api("/rodin", body, content_type)
                failure_stage = "response_validation"
                try:
                    record["consumed_credits"] = number(result.get("consumed"), "CONSUMED_INVALID")
                    record["cost_state"] = "service_reported"
                except SafeError:
                    record["cost_state"] = "unverified_missing_or_invalid_consumed"
                if result.get("error"):
                    code = result["error"]
                    if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,80}", code):
                        raise SafeError("GENERATION_RESPONSE_INVALID")
                    record.update(state="failed", error_code=code, finished_utc=now())
                else:
                    task = str(uuid.UUID(result["uuid"]))
                    record.update(task_uuid=task, response_identity_observed_utc=now())
                    # Preserve known public identity and independently validated cost first.
                    failure_stage = "public_identity_save"
                    write_json(record_path, record)
                    subscription = result["jobs"]["subscription_key"]
                    if not isinstance(subscription, str) or not subscription or len(subscription) > 4096:
                        raise SafeError("GENERATION_RESPONSE_INVALID")
                    failure_stage = "private_state_save"
                    self.private_write(private, {**marker, "state": "submitted", "task_uuid": task, "subscription_key": subscription}, False)
                    record.update(state="submitted", submitted_utc=now())
            except Exception:
                # Includes network ambiguity, malformed response, and private state write failure.
                record.update(state="unknown", error_code="SUBMISSION_UNKNOWN_NEVER_RESUBMIT", failure_stage=failure_stage, observed_utc=now())
            write_json(record_path, record)
            try:
                record["balance_after"] = self.balance()
            except Exception:
                record["balance_after"] = {"state": "unverified"}
            write_json(record_path, record)
            return record

    def private_read(self, record):
        path = self.private_path(record["operation_id"])
        if not path.is_file() or path.stat().st_size > 16384:
            raise SafeError("PRIVATE_TASK_STATE_UNAVAILABLE")
        value = json.loads(self.transport().protected_bytes(path.read_bytes(), decrypt=True).decode("utf-8"))
        if value.get("operation_id") != record["operation_id"] or value.get("fingerprint") != record["fingerprint"] or value.get("state") != "submitted" or (record["task_uuid"] and value.get("task_uuid") != record["task_uuid"]):
            raise SafeError("PRIVATE_TASK_STATE_BINDING_INVALID")
        return value

    def status(self, operation):
        with self.lock():
            path = self.record_path(operation)
            record = read_json(path)
            if record["state"] in {"downloaded", "download_partial"}:
                # Generation is already known complete at download entry. Never
                # reset download progress or make a partial attempt retryable.
                return {**record, "status_source": "local_download_record", "live_query": False}
            if record["state"] not in ACTIVE:
                raise SafeError("TASK_STATE_TERMINAL_OR_INVALID")
            checked = record.get("status_checked_utc", record.get("submitted_utc", record["started_utc"]))
            interval = min(30, 5 * 2 ** min(record.get("status_poll_count", 0), 3))
            if (datetime.now(timezone.utc) - datetime.fromisoformat(checked)).total_seconds() < interval:
                raise SafeError("STATUS_BACKOFF_REQUIRED")
            private = self.private_read(record)
            result = self.transport().api("/status", {"subscription_key": private["subscription_key"]})
            jobs = result.get("jobs")
            if result.get("error") or not isinstance(jobs, list) or not jobs or len(jobs) > 100:
                raise SafeError("STATUS_RESPONSE_INVALID")
            states = [x.get("status") for x in jobs if isinstance(x, dict)]
            if len(states) != len(jobs) or any(x not in {"Waiting", "Generating", "Done", "Failed"} for x in states):
                raise SafeError("STATUS_RESPONSE_INVALID")
            state = "failed" if "Failed" in states else "complete" if all(x == "Done" for x in states) else "processing"
            record.update(state=state, task_uuid=private["task_uuid"], status_states=states, status_checked_utc=now(), status_poll_count=record.get("status_poll_count", 0) + 1)
            write_json(path, record)
            return record

    def download(self, operation):
        with self.lock():
            path = self.record_path(operation)
            record = read_json(path)
            if record["state"] != "complete":
                raise SafeError("TASK_NOT_COMPLETE_OR_DOWNLOAD_ALREADY_ATTEMPTED")
            self.private_read(record)
            plan = read_json(self.path("runs/hyper3d/plans/" + valid_id(operation) + ".json"))
            expected = plan.pop("plan_sha256")
            if identity.json_digest(plan) != expected or expected != record["plan_sha256"]:
                raise SafeError("PLAN_INTEGRITY_INVALID")
            output = self.path(plan["output_directory"])
            if output.exists() or not plan["output_directory"].startswith("assets/raw/"):
                raise SafeError("NEW_RAW_OUTPUT_REQUIRED")
            result = self.transport().api("/download", {"task_uuid": record["task_uuid"]})
            entries = result.get("list")
            if result.get("error") or not isinstance(entries, list) or not 1 <= len(entries) <= 20:
                raise SafeError("DOWNLOAD_RESPONSE_INVALID")
            files = []
            for item in entries:
                name = item.get("name") if isinstance(item, dict) else None
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,150}", name) or ".." in name or name.endswith((".", " ")) or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *["COM" + str(i) for i in range(1, 10)], *["LPT" + str(i) for i in range(1, 10)]} or Path(name).suffix.lower() not in EXTENSIONS:
                    raise SafeError("DOWNLOAD_FILENAME_UNSAFE")
                parts, public_ip = self.transport().public_download_url(item.get("url"))
                files.append((name, parts, public_ip))
            if len({x[0].casefold() for x in files}) != len(files):
                raise SafeError("DOWNLOAD_FILENAME_COLLISION")
            output.mkdir(parents=True, exist_ok=False)
            record.update(state="download_partial", download_started_utc=now())
            write_json(path, record)
            total = 0
            try:
                for name, parts, public_ip in files:
                    target = self.path(plan["output_directory"] + "/" + name)
                    partial = target.with_name(target.name + ".part")
                    connection = self.transport().PinnedHTTPS(parts.hostname, public_ip)
                    try:
                        connection.request("GET", urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, "")))
                        response = connection.getresponse()
                        if response.status != 200:
                            raise SafeError("DOWNLOAD_HTTP_STATUS_REJECTED")
                        size = 0
                        h = hashlib.sha256()
                        with partial.open("xb") as stream:
                            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                                size += len(chunk)
                                total += len(chunk)
                                if size > MAX_FILE or total > 2 * MAX_FILE:
                                    raise SafeError("DOWNLOAD_SIZE_EXCEEDED")
                                stream.write(chunk)
                                h.update(chunk)
                            stream.flush()
                            import os
                            os.fsync(stream.fileno())
                        if not size or target.exists():
                            raise SafeError("DOWNLOAD_EMPTY_OR_COLLISION")
                        # Windows rename does not overwrite; workspace lock excludes this client.
                        partial.rename(target)
                        record["downloads"].append({"path": target.relative_to(self.root).as_posix(), "bytes": size, "sha256": h.hexdigest()})
                        write_json(path, record)
                    finally:
                        connection.close()
                record.update(state="downloaded", download_finished_utc=now())
            except Exception:
                record.update(state="download_partial", error_code="DOWNLOAD_INCOMPLETE_PARTIAL_PRESERVED")
            write_json(path, record)
            return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("balance")
    commands.add_parser("capabilities")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--spec", required=True, help="relative public spec inside workspace")
    submit = commands.add_parser("submit")
    submit.add_argument("--operation", required=True)
    submit.add_argument("--spending-authorized", action="store_true")
    submit.add_argument("--authorized-state-file", required=True, help="exact outside-repo file explicitly authorized by user")
    for command in ("status", "download"):
        commands.add_parser(command).add_argument("--operation", required=True)
    args = parser.parse_args(argv)
    try:
        client = Client(args.workspace)
        if args.command == "prepare":
            result = client.prepare(read_json(client.path(args.spec)))
        elif args.command == "submit":
            result = client.submit(args.operation, args.spending_authorized, args.authorized_state_file)
        elif args.command in {"status", "download"}:
            result = getattr(client, args.command)(args.operation)
        else:
            result = getattr(client, args.command)()
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 1 if result.get("state") in {"unknown", "failed", "download_partial"} else 0
    except SafeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except Exception:
        # Provider exceptions and transport traces may contain secrets or signed URLs.
        print(json.dumps({"error": "CLIENT_ERROR_REDACTED"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
