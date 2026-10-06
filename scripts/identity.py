"""Workspace identity：如何命名（Asset ID）、定位（Recorded／Command path）及認定同一份內容（digest）。

錯誤訊息只含穩定代碼，不回顯輸入值，避免路徑或內容外洩到 log。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

ASSET_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}\Z")


class IdentityError(ValueError):
    pass


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except ValueError:
        raise IdentityError("JSON_NUMBER_INVALID") from None


def json_digest(value: object) -> str:
    """Request digest 即 json_digest(request)：鍵序、空白與 BOM 不影響結果。"""
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_asset_id(value: object) -> bool:
    # Windows 會去掉檔名結尾的點，因此 "a." 與 "a" 可能落到同一檔案。
    return isinstance(value, str) and bool(ASSET_ID.fullmatch(value)) and ".." not in value and not value.endswith(".")


def recorded_path(root: Path, value: object) -> Path:
    """JSON 紀錄內的路徑：必須是可攜的 repo 相對 POSIX 路徑。"""
    if not isinstance(value, str) or not value or "\x00" in value or Path(value).is_absolute() or ".." in Path(value).parts or "\\" in value or ":" in value:
        raise IdentityError("RECORDED_PATH_INVALID")
    root = root.resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root) or path == root:
        raise IdentityError("PATH_OUTSIDE_WORKSPACE")
    return path


def command_path(root: Path, value: str) -> Path:
    """人在 shell 輸入的命令列參數：可為絕對路徑或使用反斜線，但必須留在 root 內。"""
    root = root.resolve()
    path = Path(value)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not path.is_relative_to(root):
        raise IdentityError("PATH_OUTSIDE_WORKSPACE")
    return path


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise IdentityError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise IdentityError("JSON_NUMBER_INVALID")


def _finite_float(text: str) -> float:
    # 1e999 等溢位字面值會被解析成 inf，必須與 Infinity 一樣拒絕。
    value = float(text)
    if not math.isfinite(value):
        raise IdentityError("JSON_NUMBER_INVALID")
    return value


def read_json(path: Path) -> dict:
    """讀進來的內容必須與 digest 代表的內容一致：拒絕重複鍵與非有限數值。"""
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object, parse_constant=_reject_constant, parse_float=_finite_float)
    except IdentityError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise IdentityError("JSON_INVALID") from None
    if not isinstance(value, dict):
        raise IdentityError("JSON_OBJECT_REQUIRED")
    return value
