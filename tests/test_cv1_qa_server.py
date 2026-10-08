"""Exercise the local QA handler without binding a port or reading repo data."""
from http import HTTPStatus
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "tools/runtime-qa/three/serve.py"
SPEC = importlib.util.spec_from_file_location("cv1_qa_server", SOURCE)
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class StaticReadBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ("tools/runtime-qa/three/index.html", "assets/processed/ro-swordsman-character-v1/model.glb",
                     "runs/qa/ro-swordsman-character-v1/result.json", ".codex/private.json",
                     "tools/runtime-qa/three/private.txt"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fixture")

    def request(self, path, method="GET"):
        handler = object.__new__(SERVER.make_handler(self.root / "runs/qa/result"))
        handler.path = path
        handler.command = method
        replies = []
        handler.reply = lambda status, body=b"", content_type=None: replies.append((status, body))
        with patch.object(SERVER, "ROOT", self.root):
            (handler.do_HEAD if method == "HEAD" else handler.do_GET)()
        self.assertEqual(len(replies), 1)
        return replies[0]

    def test_valid_files_in_each_whitelisted_folder_remain_readable(self):
        for path in ("/tools/runtime-qa/three/index.html", "/assets/processed/ro-swordsman-character-v1/model.glb",
                     "/runs/qa/ro-swordsman-character-v1/result.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path), (HTTPStatus.OK, b"fixture"))

    def test_traversal_cannot_read_other_repo_json(self):
        for path in ("/tools/runtime-qa/three/../../../.codex/private.json",
                     "/tools/runtime-qa/three/%2e%2e/%2e%2e/%2e%2e/.codex/private.json",
                     "/tools/runtime-qa/three/..%5c..%5c..%5c.codex%5cprivate.json",
                     "/assets/processed/ro-swordsman-character-v1/../../../.codex/private.json",
                     "/runs/qa/ro-swordsman-character-v1/../../../.codex/private.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], HTTPStatus.NOT_FOUND)

    def test_head_has_the_same_traversal_boundary(self):
        self.assertEqual(self.request("/tools/runtime-qa/three/../../../.codex/private.json", "HEAD")[0], HTTPStatus.NOT_FOUND)

    def test_unlisted_folder_suffix_and_missing_file_stay_rejected(self):
        for path in ("/.codex/private.json", "/tools/runtime-qa/three/private.txt", "/tools/runtime-qa/three/missing.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
