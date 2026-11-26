import json
import os
import sys
import tempfile
import unittest

from helpers import REPO, run

S = os.path.join(REPO, "benchmarks", "soroban", "snippets")


class SorobanSnippetSuiteTest(unittest.TestCase):
    def test_cases_are_scrubbed(self):
        for line in open(os.path.join(S, "cases.jsonl"), encoding="utf-8"):
            case = json.loads(line)
            for name, text in case["files"].items():
                low = text.lower()
                self.assertNotIn("vulnerable", low, f"{case['case_id']}:{name}")
                self.assertNotIn("remediated", low, f"{case['case_id']}:{name}")
                self.assertNotIn("#[cfg(test)]\nmod", text, f"{case['case_id']}:{name}")

    def test_make_and_score(self):
        out = tempfile.mkdtemp()
        r = run([sys.executable, os.path.join(S, "make_projects.py"), os.path.join(S, "cases.jsonl"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"projects": 6, "cases": 92})
        manifest = json.load(open(os.path.join(out, "manifest.json")))
        first = manifest["snippets-1"]
        vuln = next(c for c in first if c["expected_detect"])
        clean = next(c for c in first if not c["expected_detect"])
        toml = open(os.path.join(out, "snippets-1", vuln["dir"], "Cargo.toml")).read()
        self.assertRegex(toml, r'name = "case-\d\d"')
        self.assertIn("soroban-sdk", open(os.path.join(out, "snippets-1", "Cargo.toml")).read())
        os.makedirs(os.path.join(out, "snippets-1", ".audit"))
        with open(os.path.join(out, "snippets-1", ".audit", "findings.json"), "w") as f:
            json.dump([{"id": "SOROBAN-001", "locations": [{"file": vuln["dir"] + "src/lib.rs", "line_start": 3}]},
                       {"id": "SOROBAN-002", "locations": [{"file": clean["dir"] + "Cargo.toml", "line_start": 1}]}], f)
        r = run([sys.executable, os.path.join(S, "score_snippets.py"), os.path.join(out, "manifest.json"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        self.assertEqual((res["total"]["detected"], res["total"]["flagged_clean"]), (1, 1))
        self.assertEqual(len(res["missing_projects"]), 5)


if __name__ == "__main__":
    unittest.main()
