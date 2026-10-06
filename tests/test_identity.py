"""Workspace identity rules shared by workbench, pipeline and the Hyper3D client."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("identity", Path(__file__).resolve().parents[1] / "scripts" / "identity.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class JsonDigestTests(unittest.TestCase):
    def test_key_order_and_whitespace_do_not_change_request_digest(self):
        self.assertEqual(identity.json_digest({"b": 1, "a": "岩"}), identity.json_digest(json.loads('{ "a" : "岩",\n "b" : 1 }')))

    def test_digest_is_sha256_of_compact_sorted_utf8_json(self):
        expected = hashlib.sha256('{"a":"岩","b":[1,2]}'.encode("utf-8")).hexdigest()
        self.assertEqual(identity.json_digest({"b": [1, 2], "a": "岩"}), expected)
        self.assertEqual(identity.canonical_json({"b": [1, 2], "a": "岩"}), '{"a":"岩","b":[1,2]}'.encode("utf-8"))

    def test_non_finite_number_is_identity_error(self):
        with self.assertRaisesRegex(identity.IdentityError, r"\AJSON_NUMBER_INVALID\Z"):
            identity.json_digest({"x": float("nan")})


class AssetIdTests(unittest.TestCase):
    def test_dotted_catalog_ids_are_valid(self):
        for value in ("evoloot.weapon.iron_sword_neutral", "test-001", "a", "a" * 96):
            with self.subTest(value=value):
                self.assertTrue(identity.is_asset_id(value))

    def test_unsafe_or_ambiguous_ids_are_invalid(self):
        for value in ("", "A", "-a", ".a", "a..b", "a.", "a/b", "a\\b", "a:b", "a" * 97, None, 7):
            with self.subTest(value=value):
                self.assertFalse(identity.is_asset_id(value))


class PathTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        (self.root / "runs" / "qa").mkdir(parents=True)

    def test_recorded_path_accepts_repo_relative_posix(self):
        self.assertEqual(identity.recorded_path(self.root, "runs/qa/x.md"), self.root / "runs" / "qa" / "x.md")

    def test_recorded_path_rejects_non_portable_forms(self):
        for value in (str(self.root / "runs"), "runs\\qa\\x.md", "C:x.md", "runs/../runs/qa", "runs/a\x00b", "", ".", None):
            with self.subTest(value=value), self.assertRaisesRegex(identity.IdentityError, r"\A(RECORDED_PATH_INVALID|PATH_OUTSIDE_WORKSPACE)\Z"):
                identity.recorded_path(self.root, value)

    def test_command_path_accepts_absolute_and_backslash_inside_root(self):
        self.assertEqual(identity.command_path(self.root, str(self.root / "runs" / "qa")), self.root / "runs" / "qa")
        self.assertEqual(identity.command_path(self.root, "runs\\qa"), self.root / "runs" / "qa")

    def test_command_path_rejects_outside_root(self):
        for value in ("../outside.json", str(self.root.parent)):
            with self.subTest(value=value), self.assertRaisesRegex(identity.IdentityError, r"\APATH_OUTSIDE_WORKSPACE\Z"):
                identity.command_path(self.root, value)


class FileAndJsonReadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def write(self, text, encoding="utf-8"):
        path = self.root / "x.json"
        path.write_text(text, encoding=encoding)
        return path

    def test_file_digest_matches_bytes(self):
        path = self.root / "m.glb"
        path.write_bytes(b"glTF fixture" * 1000)
        self.assertEqual(identity.file_digest(path), hashlib.sha256(b"glTF fixture" * 1000).hexdigest())

    def test_read_json_accepts_bom_object(self):
        self.assertEqual(identity.read_json(self.write('{"a": 1}', "utf-8-sig")), {"a": 1})

    def test_read_json_rejects_ambiguous_content(self):
        cases = {'[1]': "JSON_OBJECT_REQUIRED", '{"a": NaN}': "JSON_NUMBER_INVALID", '{"a": Infinity}': "JSON_NUMBER_INVALID", '{"a": 1e999}': "JSON_NUMBER_INVALID",
                 '{"a": 1, "a": 2}': "JSON_DUPLICATE_KEY", '{"a": {"b": 1, "b": 1}}': "JSON_DUPLICATE_KEY", '{"a":': "JSON_INVALID"}
        for text, code in cases.items():
            with self.subTest(text=text), self.assertRaisesRegex(identity.IdentityError, rf"\A{code}\Z"):
                identity.read_json(self.write(text))

    def test_identity_error_is_value_error_without_input_echo(self):
        with self.assertRaises(ValueError) as caught:
            identity.read_json(self.write('{"secret-looking-key": 1, "secret-looking-key": 2}'))
        self.assertNotIn("secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
