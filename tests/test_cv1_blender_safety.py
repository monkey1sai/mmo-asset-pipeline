import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("read_factory_settings", "read_homefile", "save_userpref", "read_factory_userpref")


class BlenderScriptSafetyTests(unittest.TestCase):
    def test_cv1_scripts_never_reset_or_save_blender_user_state(self):
        # wm.read_factory_settings emptied the user's extension wheel cache on 2026-10-05; run with --factory-startup instead.
        offenders = []
        for path in sorted((ROOT / "scripts").glob("cv1_*.py")):
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]
            offenders += [f"{path.name}: {name}" for name in FORBIDDEN if any(name in line for line in lines)]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
