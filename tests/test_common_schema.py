import os
import sys
import unittest

from helpers import CORE, SCRIPTS, load, valid_finding

sys.path.insert(0, SCRIPTS)
from _common import glob_match, matches_any  # noqa: E402
from _schema import validate  # noqa: E402

SCHEMAS = os.path.join(CORE, "engine")


class GlobTest(unittest.TestCase):
    def test_double_star_matches_zero_dirs(self):
        self.assertTrue(glob_match("src/A.sol", "src/**/*.sol"))
        self.assertTrue(glob_match("src/a/b/A.sol", "src/**/*.sol"))

    def test_leading_double_star(self):
        self.assertTrue(glob_match("test/A.sol", "**/test/**"))
        self.assertTrue(glob_match("pkg/test/x/A.sol", "**/test/**"))
        self.assertTrue(glob_match("A.t.sol", "**/*.t.sol"))

    def test_single_star_does_not_cross_dirs(self):
        self.assertFalse(glob_match("src/a/A.sol", "src/*.sol"))

    def test_matches_any(self):
        self.assertTrue(matches_any("lib/x/A.sol", ["src/**", "lib/**"]))
        self.assertFalse(matches_any("x/A.sol", []))


class SchemaEngineTest(unittest.TestCase):
    def test_type_and_required(self):
        s = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        self.assertEqual(validate({"a": 1}, s), [])
        self.assertIn("$: missing required 'a'", validate({}, s))
        self.assertTrue(validate({"a": "x"}, s)[0].startswith("$.a: expected integer"))

    def test_bool_is_not_integer(self):
        self.assertTrue(validate(True, {"type": "integer"}))

    def test_enum_items_minitems_ref(self):
        s = {"$defs": {"sev": {"enum": ["High", "Low"]}},
             "type": "array", "minItems": 1, "items": {"$ref": "#/$defs/sev"}}
        self.assertEqual(validate(["High"], s), [])
        self.assertTrue(validate([], s))
        self.assertTrue(any("not in" in e for e in validate(["Mid"], s)))

    def test_additional_properties(self):
        closed = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
        self.assertIn("$: unexpected property 'b'", validate({"a": 1, "b": 2}, closed))
        typed = {"type": "object", "additionalProperties": {"type": "number"}}
        self.assertEqual(validate({"x": 1.5}, typed), [])
        self.assertTrue(validate({"x": "no"}, typed))


class ProjectSchemasTest(unittest.TestCase):
    def test_valid_finding_passes(self):
        self.assertEqual(validate(valid_finding(), load(os.path.join(SCHEMAS, "finding.schema.json"))), [])

    def test_finding_rejects_unknown_status(self):
        errs = validate(valid_finding(status="TP"), load(os.path.join(SCHEMAS, "finding.schema.json")))
        self.assertTrue(errs)

    def test_minimal_facts_pass(self):
        facts = {"chain": "solidity", "mode": "regex", "units": [], "entry_points": [], "auth_sites": [],
                 "storage_writes": [], "external_calls": [], "value_transfers": [],
                 "counters": {"src/A.sol": {"loc": 10, "external_calls": 1}}}
        self.assertEqual(validate(facts, load(os.path.join(SCHEMAS, "facts.schema.json"))), [])

    def test_pack_schema_requires_chain(self):
        errs = validate({}, load(os.path.join(SCHEMAS, "pack.schema.json")))
        self.assertIn("$: missing required 'chain'", errs)


if __name__ == "__main__":
    unittest.main()
