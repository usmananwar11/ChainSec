import json
import unittest

from helpers import load, run_py, valid_finding, write_tmp_json


def check(findings, *flags):
    path = write_tmp_json(findings)
    r = run_py("validate-findings.py", path, *flags)
    return r, (json.loads(r.stdout) if r.stdout.strip() else None), path


class ValidateFindingsTest(unittest.TestCase):
    def test_valid(self):
        r, out, _ = check([valid_finding()])
        self.assertEqual((r.returncode, out), (0, []), r.stderr)

    def test_missing_line_on_verified_high(self):
        r, out, _ = check([valid_finding(locations=[{"file": "src/Vault.sol"}])])
        self.assertEqual(r.returncode, 1)
        self.assertEqual([x["rule"] for x in out], ["location"])

    def test_missing_harm(self):
        r, out, _ = check([valid_finding(harm={"who": " ", "loses_what": "funds"})])
        self.assertEqual([x["rule"] for x in out], ["harm"])

    def test_empty_trace(self):
        r, out, _ = check([valid_finding(exploit_trace=[])])
        self.assertEqual([x["rule"] for x in out], ["exploit_trace"])

    def test_rules_skip_candidates_and_low(self):
        r, out, _ = check([valid_finding(status="candidate", exploit_trace=[], harm={}),
                           valid_finding(id="SOL-002", severity="Low", exploit_trace=[])])
        self.assertEqual((r.returncode, out), (0, []))

    def test_schema_error(self):
        r, out, _ = check([valid_finding(severity="Severe")])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(out[0]["rule"], "schema")

    def test_top_level_must_be_array(self):
        r, out, _ = check(valid_finding())
        self.assertEqual(r.returncode, 2)

    def test_downgrade_rewrites_file(self):
        r, out, path = check([valid_finding(exploit_trace=[])], "--downgrade")
        self.assertEqual((r.returncode, out), (0, []), r.stdout)
        f = load(path)[0]
        self.assertEqual((f["status"], f["severity"]), ("downgraded", "Low"))
        self.assertEqual(f["verdict"]["original_severity"], "High")
        self.assertIn("exploit_trace", f["verdict"]["reason"])

    def test_downgrade_keeps_schema_errors(self):
        r, out, _ = check([valid_finding(severity="Severe")], "--downgrade")
        self.assertEqual(r.returncode, 1)

    def test_duplicate_id_reported_once_per_id(self):
        r, out, _ = check([valid_finding(), valid_finding(), valid_finding(),
                           valid_finding(id="SOL-002"), valid_finding(id="SOL-002")])
        self.assertEqual(r.returncode, 1)
        self.assertEqual([(x["id"], x["rule"]) for x in out],
                         [("SOL-001", "duplicate-id"), ("SOL-002", "duplicate-id")])

    def test_downgrade_touches_only_offending_duplicate(self):
        r, out, path = check([valid_finding(), valid_finding(exploit_trace=[])], "--downgrade")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual([x["rule"] for x in out], ["duplicate-id"])
        good, bad = load(path)
        self.assertEqual((good["status"], good["severity"]), ("verified", "High"))
        self.assertNotIn("original_severity", good["verdict"])
        self.assertEqual((bad["status"], bad["severity"]), ("downgraded", "Low"))
        self.assertIn("exploit_trace", bad["verdict"]["reason"])

    def test_schema_only_ignores_hard_rules_and_duplicates(self):
        r, out, _ = check([valid_finding(exploit_trace=[]), valid_finding(harm={})], "--schema-only")
        self.assertEqual((r.returncode, out), (0, []), r.stdout)

    def test_schema_only_reports_schema_errors(self):
        r, out, _ = check([valid_finding(severity="Severe", exploit_trace=[])], "--schema-only")
        self.assertEqual(r.returncode, 1)
        self.assertEqual({x["rule"] for x in out}, {"schema"})

    def test_schema_only_input_error(self):
        r, out, _ = check(valid_finding(), "--schema-only")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out[0]["rule"], "input")


if __name__ == "__main__":
    unittest.main()
