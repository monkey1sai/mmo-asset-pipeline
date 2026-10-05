"""Add a 'product' driver (product of other drivers' values) to the rule evaluators, Python and JavaScript, with tests.

Run once from the repo root: python -B runs/qa/ro-swordsman-character-v1/v001/patch-product-driver-used.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NL = chr(10)


def patch(path, pairs):
    text = (ROOT / path).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, (path, old[:60])
        text = text.replace(old, new)
    (ROOT / path).write_text(text, encoding="utf-8", newline=NL)


patch("scripts/cv1_pose_rules.py", [
    ('''        elif driver.get("type") == "state":
            if not isinstance(driver.get("key"), str):
                raise RuleError("RULES_SCHEMA")
        else:
            raise RuleError("UNKNOWN_DRIVER_TYPE")''',
     '''        elif driver.get("type") == "state":
            if not isinstance(driver.get("key"), str):
                raise RuleError("RULES_SCHEMA")
        elif driver.get("type") == "product":
            # Product of other, non-product drivers: active only when all of them are.
            factors = driver.get("of")
            if not isinstance(factors, list) or len(factors) < 2 or any(drivers.get(name, {}).get("type") not in ("rotation_difference", "state") for name in factors):
                raise RuleError("INVALID_PRODUCT_DRIVER")
        else:
            raise RuleError("UNKNOWN_DRIVER_TYPE")'''),
    ('''        else:
            if driver["key"] not in state:
                raise RuleError("MISSING_STATE:" + driver["key"])
            value = float(state[driver["key"]])
            if not 0.0 <= value <= 1.0:
                raise RuleError("STATE_OUT_OF_RANGE:" + driver["key"])
            out[name] = value
    return out''',
     '''        elif driver["type"] == "state":
            if driver["key"] not in state:
                raise RuleError("MISSING_STATE:" + driver["key"])
            value = float(state[driver["key"]])
            if not 0.0 <= value <= 1.0:
                raise RuleError("STATE_OUT_OF_RANGE:" + driver["key"])
            out[name] = value
    for name, driver in rules["drivers"].items():
        if driver["type"] == "product":
            value = 1.0
            for factor in driver["of"]:
                value *= out[factor]
            out[name] = value
    return out'''),
])
patch("tools/runtime-qa/three/src/cv1-pose-rules.js", [
    ('''    } else if (driver.type === 'state') {
      if (typeof driver.key !== 'string') throw new RuleError('RULES_SCHEMA');
    } else {
      throw new RuleError('UNKNOWN_DRIVER_TYPE');
    }''',
     '''    } else if (driver.type === 'state') {
      if (typeof driver.key !== 'string') throw new RuleError('RULES_SCHEMA');
    } else if (driver.type === 'product') {
      // Product of other, non-product drivers: active only when all of them are.
      const simple = (name) => ['rotation_difference', 'state'].includes(drivers[name]?.type);
      if (!Array.isArray(driver.of) || driver.of.length < 2 || !driver.of.every(simple)) throw new RuleError('INVALID_PRODUCT_DRIVER');
    } else {
      throw new RuleError('UNKNOWN_DRIVER_TYPE');
    }'''),
    ('''    } else {
      if (!(driver.key in state)) throw new RuleError(`MISSING_STATE:${driver.key}`);
      const value = Number(state[driver.key]);
      if (!(value >= 0 && value <= 1)) throw new RuleError(`STATE_OUT_OF_RANGE:${driver.key}`);
      out[name] = value;
    }
  }
  return out;''',
     '''    } else if (driver.type === 'state') {
      if (!(driver.key in state)) throw new RuleError(`MISSING_STATE:${driver.key}`);
      const value = Number(state[driver.key]);
      if (!(value >= 0 && value <= 1)) throw new RuleError(`STATE_OUT_OF_RANGE:${driver.key}`);
      out[name] = value;
    }
  }
  for (const [name, driver] of Object.entries(rules.drivers)) {
    if (driver.type === 'product') out[name] = driver.of.reduce((value, factor) => value * out[factor], 1);
  }
  return out;'''),
])
patch("tests/test_cv1_pose_rules.py", [
    ('''    @unittest.skipUnless(shutil.which('node'), 'node not installed')''',
     '''    def test_product_driver_needs_every_factor_active(self):
        rules = sample_rules()
        rules['drivers']['both'] = {'type': 'product', 'of': ['wrist', 'grasp']}
        rules['channels'].append({'mesh': 'Glove', 'morph': 'Both', 'owner': 'runtime_evaluator', 'driver': 'both', 'curve': {'type': 'linear'}})
        half = axis_angle((0.3, -0.39, 0.87), 66.8)
        self.assertAlmostEqual(rules_math.evaluate(rules, {'hand.R': half}, {'grasp.R': 0.5})[('Glove', 'Both')], 0.25, places=9)
        self.assertEqual(rules_math.evaluate(rules, {'hand.R': half}, {'grasp.R': 0.0})[('Glove', 'Both')], 0.0)
        rules['drivers']['nested'] = {'type': 'product', 'of': ['both', 'grasp']}
        with self.assertRaisesRegex(rules_math.RuleError, 'INVALID_PRODUCT_DRIVER'):
            rules_math.validate_rules(rules)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')'''),
    ('''        done = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps({'rules': sample_rules(), 'cases': cases}),''',
     '''        shared = sample_rules()
        shared['drivers']['both'] = {'type': 'product', 'of': ['wrist', 'grasp']}
        shared['channels'].append({'mesh': 'Glove', 'morph': 'Both', 'owner': 'runtime_evaluator', 'driver': 'both', 'curve': {'type': 'linear'}})
        done = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps({'rules': shared, 'cases': cases}),'''),
    ('''            expected = rules_math.evaluate(sample_rules(), case['pose'], case['state'])''', '''            expected = rules_math.evaluate(shared, case['pose'], case['state'])'''),
])
print("patched")
