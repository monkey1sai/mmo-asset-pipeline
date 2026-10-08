"""Local static server for the character V1 Three.js QA scene.

Binds 127.0.0.1 only. Serves three whitelisted repo folders read-only and accepts result uploads
from the page into one evidence folder; existing files are never overwritten.
"""
from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
READABLE = ("tools/runtime-qa/three/", "assets/processed/ro-swordsman-character-v1/", "runs/qa/ro-swordsman-character-v1/")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
         ".glb": "model/gltf-binary", ".bin": "application/octet-stream", ".png": "image/png", ".css": "text/css; charset=utf-8"}
SAVE_NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,80}\.(json|png)\Z")
MAX_UPLOAD = 64 * 1024 * 1024


def make_handler(save_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "cv1-runtime-qa"

        def reply(self, status, body=b"", content_type="text/plain; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == "/":
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/tools/runtime-qa/three/index.html")
                self.end_headers()
                return
            relative = path.lstrip("/")
            target = (ROOT / relative).resolve()
            in_readable_folder = any(target.is_relative_to((ROOT / folder).resolve()) for folder in READABLE)
            if not relative.startswith(READABLE) or not target.is_relative_to(ROOT) or not in_readable_folder or not target.is_file() or target.suffix.lower() not in TYPES:
                self.reply(HTTPStatus.NOT_FOUND, b"not found")
                return
            self.reply(HTTPStatus.OK, target.read_bytes(), TYPES[target.suffix.lower()])

        do_HEAD = do_GET

        def do_POST(self):
            url = urlsplit(self.path)
            name = parse_qs(url.query).get("name", [""])[0]
            length = int(self.headers.get("Content-Length", "-1"))
            # The custom header keeps other web pages from posting here without a CORS preflight, which is never granted.
            if url.path != "/__save" or self.headers.get("X-CV1-Save") != "1" or not SAVE_NAME.fullmatch(name) or not 0 < length <= MAX_UPLOAD:
                self.reply(HTTPStatus.BAD_REQUEST, b"rejected")
                return
            target = save_dir / name
            if target.exists():
                self.reply(HTTPStatus.CONFLICT, b"exists")
                return
            save_dir.mkdir(parents=True, exist_ok=True)
            with open(target, "xb") as handle:
                handle.write(self.rfile.read(length))
            self.reply(HTTPStatus.CREATED, target.relative_to(ROOT).as_posix().encode())

        def log_message(self, format, *args):
            print("%s %s" % (self.address_string(), format % args), flush=True)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--save-dir", default="runs/qa/ro-swordsman-character-v1/p1/runtime")
    args = parser.parse_args()
    save_dir = (ROOT / args.save_dir).resolve()
    if not save_dir.is_relative_to(ROOT / "runs" / "qa"):
        raise SystemExit("save-dir must stay under runs/qa")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(save_dir))
    print(f"cv1 runtime QA on http://127.0.0.1:{args.port}/ (uploads -> {save_dir.relative_to(ROOT).as_posix()})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
