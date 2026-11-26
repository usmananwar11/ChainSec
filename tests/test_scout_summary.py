import json
import os
import sys
import tempfile
import unittest

from helpers import CORE, run

SCRIPT = os.path.join(CORE, "chains", "soroban", "recon", "scout-summary.py")


def sarif(*results):
    return {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "scout"}}, "results": list(results)}]}


def result(rule, uri, line, text, level="warning"):
    return {"ruleId": rule, "level": level, "message": {"text": text},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}]}


def summarize(content):
    d = tempfile.mkdtemp()
    src, out = os.path.join(d, "scout.json"), os.path.join(d, "scout.md")
    with open(src, "w") as f:
        f.write(content if isinstance(content, str) else json.dumps(content))
    r = run([sys.executable, SCRIPT, src, out])
    return r, (open(out).read() if r.returncode == 0 else "")


class ScoutSummaryTest(unittest.TestCase):
    def test_table(self):
        r, md = summarize(sarif(result("unsafe-unwrap", "src/lib.rs", 12, "Unsafe usage of `unwrap`\nmore"),
                                result("unprotected-update-current-contract-wasm", "src/lib.rs", 40,
                                       "a | b", level="error")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Results: 2 from 2 detectors", md)
        self.assertIn("| unsafe-unwrap | warning | src/lib.rs:12 | Unsafe usage of `unwrap` |", md)
        self.assertIn("a \\| b", md)
        self.assertNotIn("more", md)

    def test_empty_and_bad_input(self):
        r, md = summarize(sarif())
        self.assertIn("Scout reported nothing.", md)
        r, _ = summarize("not json")
        self.assertEqual(r.returncode, 1)

    def test_missing_input(self):
        r = run([sys.executable, SCRIPT, "/nonexistent/scout.json", os.path.join(tempfile.mkdtemp(), "x.md")])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
