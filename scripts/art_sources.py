"""Local-only, fail-closed source intake; reuses this repository's identity.py.

No network, paid jobs, subprocesses, extraction, retargeting, Git or automatic
acceptance. `check` is read-only. `import-local --apply` copies only explicitly
listed, hash-bound files into a NEW assets/raw version in this public repository.
A reviewed receipt records a human licensing decision; this code is not a legal
rights detector and does not prove that the declarations are truthful.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity

ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r"[0-9a-f]{64}\Z")
SAFE_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
RESERVED = {"con", "prn", "aux", "nul"} | {f"{s}{i}" for s in ("com", "lpt") for i in range(1, 10)}
EXTENSIONS = {".glb", ".gltf", ".bin", ".fbx", ".bvh", ".obj", ".mtl", ".blend", ".usd", ".usdc", ".usda", ".png", ".jpg", ".jpeg", ".webp", ".tga", ".tif", ".tiff", ".exr", ".hdr"}
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"
KINDS = {"model", "material", "motion", "hdri"}


class SourceError(ValueError):
    """Stable code only; never echo paths, URLs, or user-supplied contents."""


def need(condition: bool, code: str) -> None:
    if not condition:
        raise SourceError(code)


def fields(value: object, keys: set[str], code: str) -> dict:
    need(isinstance(value, dict) and set(value) == keys, code)
    return value


def sha_ok(value: object) -> bool:
    return isinstance(value, str) and bool(HEX.fullmatch(value))


def text(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= 1024 and not any(ord(c) < 32 for c in value)


def safe_relative(value: object) -> str:
    need(isinstance(value, str) and bool(value), "RELATIVE_PATH_REQUIRED")
    parts = value.split("/")
    need(all(SAFE_PART.fullmatch(p) and ".." not in p and not p.endswith(".")
             and p.split(".")[0].lower() not in RESERVED for p in parts), "UNSAFE_PORTABLE_PATH")
    need(not value.startswith("/") and "\\" not in value and ":" not in value, "UNSAFE_PORTABLE_PATH")
    return value


def no_symlinks(root: Path, relative: str) -> Path:
    # Do not accept symlinks even if they resolve back inside the workspace.
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        need(not path.is_symlink(), "SYMLINK_NOT_ALLOWED")
        if hasattr(path, "is_junction"):
            need(not path.is_junction(), "JUNCTION_NOT_ALLOWED")
    return identity.recorded_path(root, relative)


def clean_url(value: object) -> bool:
    if not text(value) or any(c.isspace() for c in value):
        return False
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
                and not u.query and not u.fragment and u.port in (None, 443))
    except ValueError:
        return False


def read_catalog(root: Path) -> dict:
    result = identity.read_json(root / "tools/art-sources/catalog.json")
    need(type(result.get("schema_version")) is int and result["schema_version"] == 1 and isinstance(result.get("providers"), list), "CATALOG_INVALID")
    providers = result["providers"]
    need(all(isinstance(p, dict) and identity.is_asset_id(p.get("id")) for p in providers), "CATALOG_INVALID")
    need(len({p["id"] for p in providers}) == len(providers), "CATALOG_DUPLICATE_ID")
    need(all(p.get("public_raw_policy") in {"cc0_assets_only", "per_asset_review", "blocked", "reference_only"}
             and isinstance(p.get("asset_kinds"), list) and all(k in KINDS for k in p["asset_kinds"])
             and isinstance(p.get("source_domains"), list) and all(isinstance(d, str) and re.fullmatch(r"[a-z0-9.-]+", d) for d in p["source_domains"])
             for p in providers), "CATALOG_POLICY_INVALID")
    return result


def validate_receipt(receipt: dict, request: dict, root: Path, source_root: Path, catalog: dict) -> dict:
    fields(receipt, {"schema_version", "id", "version", "request", "provider", "asset_kind", "source", "rights", "review", "files", "motion"}, "RECEIPT_SCHEMA")
    need(type(receipt["schema_version"]) is int and receipt["schema_version"] == 1, "RECEIPT_VERSION")
    need(identity.is_asset_id(receipt["id"]) and receipt["id"].split(".")[0] not in RESERVED, "ASSET_ID_INVALID")
    need(isinstance(receipt["version"], str) and re.fullmatch(r"v[0-9]{3,6}", receipt["version"]) is not None, "ASSET_VERSION_INVALID")
    binding = fields(receipt["request"], {"id", "sha256"}, "REQUEST_BINDING_SCHEMA")
    need(binding["id"] == request.get("id") and identity.is_asset_id(binding["id"]), "REQUEST_ID_MISMATCH")
    need(sha_ok(binding["sha256"]) and binding["sha256"] == identity.json_digest(request), "REQUEST_HASH_MISMATCH")
    # Full request validity and delivery QA remain the responsibility of workbench.py.
    need(request.get("status") == "specified", "REQUEST_NOT_SPECIFIED")
    need(isinstance(receipt["asset_kind"], str) and receipt["asset_kind"] in KINDS, "ASSET_KIND_INVALID")
    provider = next((p for p in catalog["providers"] if p["id"] == receipt["provider"]), None)
    need(provider is not None, "PROVIDER_UNKNOWN")
    need(receipt["asset_kind"] in provider.get("asset_kinds", []), "PROVIDER_KIND_MISMATCH")
    need(provider.get("public_raw_policy") in {"cc0_assets_only", "per_asset_review"}, "PUBLIC_RAW_PROVIDER_BLOCKED")

    source = fields(receipt["source"], {"url", "revision", "content_class"}, "SOURCE_SCHEMA")
    need(clean_url(source["url"]), "SOURCE_URL_NOT_CANONICAL")
    need(text(source["revision"]), "SOURCE_REVISION_REQUIRED")
    need(source["content_class"] == "asset", "SOURCE_MUST_BE_ASSET_NOT_PREVIEW_OR_CODE")
    host = urlsplit(source["url"]).hostname.lower()
    domains = provider.get("source_domains", [])
    need(not domains or any(host == d or host.endswith("." + d) for d in domains), "SOURCE_DOMAIN_MISMATCH")
    rights = fields(receipt["rights"], {"license_id", "commercial_use", "public_raw_redistribution"}, "RIGHTS_SCHEMA")
    need(text(rights["license_id"]), "LICENSE_ID_REQUIRED")
    need(rights["commercial_use"] == "allowed", "COMMERCIAL_RIGHTS_NOT_APPROVED")
    need(rights["public_raw_redistribution"] == "allowed", "PUBLIC_RAW_RIGHTS_NOT_APPROVED")
    if provider.get("public_raw_policy") == "cc0_assets_only":
        need(rights["license_id"] == "CC0-1.0", "CC0_LICENSE_REQUIRED")

    review = fields(receipt["review"], {"status", "reviewer", "reviewed_on", "evidence"}, "REVIEW_SCHEMA")
    need(review["status"] == "approved" and text(review["reviewer"]), "LICENSE_REVIEW_REQUIRED")
    try:
        d = date.fromisoformat(review["reviewed_on"])
        need(d.isoformat() == review["reviewed_on"] and d <= date.today(), "REVIEW_DATE_INVALID")
    except (ValueError, TypeError):
        raise SourceError("REVIEW_DATE_INVALID") from None
    ev = fields(review["evidence"], {"path", "sha256"}, "LICENSE_EVIDENCE_SCHEMA")
    relative = safe_relative(ev["path"])
    need(relative.startswith("runs/evidence/") and Path(relative).suffix.lower() in {".md", ".txt", ".json"}, "LICENSE_EVIDENCE_SCOPE")
    p = no_symlinks(root, relative)
    need(p.is_file() and sha_ok(ev["sha256"]) and identity.file_digest(p) == ev["sha256"], "LICENSE_EVIDENCE_MISMATCH")

    motion = receipt["motion"]
    if receipt["asset_kind"] == "motion":
        fields(motion, {"origin", "clip_names", "fps", "root_motion", "source_skeleton_fingerprint", "contact_annotation"}, "MOTION_SCHEMA")
        need(motion["origin"] in {"mocap", "authored", "procedural"}, "MOTION_ORIGIN_REQUIRED")
        names = motion["clip_names"]
        need(isinstance(names, list) and bool(names) and all(text(x) for x in names) and len(set(names)) == len(names), "CLIP_NAMES_INVALID")
        need(type(motion["fps"]) in (int, float) and math.isfinite(motion["fps"]) and 0 < motion["fps"] <= 1000, "MOTION_FPS_INVALID")
        need(motion["root_motion"] in {"in_place", "root_motion"}, "ROOT_MOTION_POLICY_REQUIRED")
        need(sha_ok(motion["source_skeleton_fingerprint"]), "SOURCE_SKELETON_FINGERPRINT_REQUIRED")
        need(motion["contact_annotation"] in {"present_unverified", "needs_authoring"}, "CONTACT_ANNOTATION_REQUIRED")
    else:
        need(motion is None, "NON_MOTION_METADATA_CONFLICT")

    files = receipt["files"]
    need(isinstance(files, list) and 0 < len(files) <= 256, "SOURCE_FILES_REQUIRED")
    seen: set[str] = set()
    sources = []
    need(source_root.is_dir() and not source_root.is_symlink(), "SOURCE_ROOT_INVALID")
    for item in files:
        fields(item, {"path", "sha256", "bytes"}, "SOURCE_FILE_SCHEMA")
        relative = safe_relative(item["path"])
        need(relative.casefold() not in seen, "DUPLICATE_PORTABLE_PATH")
        seen.add(relative.casefold())
        need(Path(relative).suffix.lower() in EXTENSIONS, "SOURCE_FILE_TYPE_NOT_ALLOWED")
        need(sha_ok(item["sha256"]) and type(item["bytes"]) is int and 0 < item["bytes"] <= 4 * 1024**3, "SOURCE_FILE_DESCRIPTOR_INVALID")
        path = no_symlinks(source_root, relative)
        need(path.is_file(), "SOURCE_FILE_MISSING")
        with path.open("rb") as f:
            need(not f.read(64).startswith(LFS_HEADER), "LFS_POINTER_NOT_ASSET")
        need(path.stat().st_size == item["bytes"] and identity.file_digest(path) == item["sha256"], "SOURCE_FILE_HASH_MISMATCH")
        sources.append(path)
    # Refuse ambiguous parent-file conflicts before making any destination.
    need(not any(a + "/" in b + "/" and b.startswith(a + "/") for a in seen for b in seen if a != b), "SOURCE_PATH_CONFLICT")
    dest_rel = f"assets/raw/{receipt['id']}/{receipt['version']}"
    destination = no_symlinks(root, dest_rel)
    need(not destination.exists(), "DESTINATION_ALREADY_EXISTS")
    need(not source_root.resolve().is_relative_to(destination), "SOURCE_INSIDE_DESTINATION")
    return {"decision": "ready_for_local_import", "destination": dest_rel,
            "receipt_sha256": identity.json_digest(receipt), "request_sha256": binding["sha256"],
            "file_count": len(sources), "bytes": sum(x["bytes"] for x in files),
            "asset_state": "source_checked_only", "technical_accepted": False, "art_accepted": False,
            "required_next_actions": ["dcc_inspection", "dependency_completeness", "applicable_workbench_checks", "fixed_condition_visual_review"]}


def import_local(receipt: dict, request: dict, root: Path, source_root: Path, catalog: dict, *, apply: bool = False) -> dict:
    result = validate_receipt(receipt, request, root, source_root, catalog)
    if not apply:
        return {**result, "write_performed": False}
    destination = no_symlinks(root, result["destination"])
    # The per-version reservation prevents cooperating importers from racing.
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.parent / ("." + receipt["version"] + ".source-import.lock")
    try:
        handle = lock.open("xb")
    except FileExistsError:
        raise SourceError("IMPORT_LOCK_EXISTS") from None
    temporary = None
    try:
        with handle:
            handle.write(b"local-source-import; do not remove while active\n")
        # Re-check everything after acquiring the reservation.
        validate_receipt(receipt, request, root, source_root, catalog)
        temporary = Path(tempfile.mkdtemp(prefix=".source-import-", dir=destination.parent))
        for item in receipt["files"]:
            source = no_symlinks(source_root, item["path"])
            target = temporary / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            count = 0
            with source.open("rb") as src, target.open("xb") as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    count += len(chunk)
                    need(count <= item["bytes"], "SOURCE_CHANGED_DURING_COPY")
                    digest.update(chunk)
                    dst.write(chunk)
            need(count == item["bytes"] and digest.hexdigest() == item["sha256"], "SOURCE_CHANGED_DURING_COPY")
        saved = {"receipt": receipt, "intake": result,
                 "status": "imported_unverified", "public_repository": True,
                 "note": "Import is not DCC, artistic, retargeting, runtime, or delivery acceptance."}
        (temporary / "source-receipt.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        need(not destination.exists(), "DESTINATION_ALREADY_EXISTS")
        temporary.rename(destination)
        temporary = None
        return {**result, "decision": "imported_unverified", "write_performed": True}
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)
        lock.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    cat = sub.add_parser("catalog")
    cat.add_argument("--kind", choices=sorted(KINDS))
    for command in ("check", "import-local"):
        p = sub.add_parser(command)
        p.add_argument("--request", required=True)
        p.add_argument("--receipt", required=True)
        p.add_argument("--source-root", required=True, type=Path, help="Explicitly authorized directory containing only the listed inputs; never uploaded")
        if command == "import-local":
            p.add_argument("--apply", action="store_true", help="Create a new raw version; otherwise read-only")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        catalog = read_catalog(root)
        if args.command == "catalog":
            result = {"research_date": catalog["research_date"], "availability": "not_probed",
                      "providers": [p for p in catalog["providers"] if args.kind is None or args.kind in p.get("asset_kinds", [])]}
        else:
            request_path = identity.command_path(root, args.request)
            receipt_path = identity.command_path(root, args.receipt)
            need(request_path.relative_to(root).parts[0] == "requests" and request_path.suffix == ".json", "REQUEST_PATH_SCOPE")
            need(receipt_path.relative_to(root).parts[:2] in {("runs", "evidence"), ("requests", "source-receipts")} and receipt_path.suffix == ".json", "RECEIPT_PATH_SCOPE")
            need(not args.source_root.is_symlink(), "SOURCE_ROOT_INVALID")
            result = import_local(identity.read_json(receipt_path), identity.read_json(request_path), root,
                                  args.source_root.resolve(), catalog, apply=getattr(args, "apply", False))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (SourceError, identity.IdentityError) as exc:
        print(json.dumps({"decision": "blocked", "error": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError, TypeError, KeyError):
        print('{"decision":"blocked","error":"INPUT_OR_IO_INVALID"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
