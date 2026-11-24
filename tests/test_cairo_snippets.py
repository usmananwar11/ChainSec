import json
import os
import sys
import tempfile
import unittest

from helpers import REPO, run

S = os.path.join(REPO, "benchmarks", "cairo", "snippets")


class CairoSnippetSuiteTest(unittest.TestCase):
    def test_make_and_score(self):
        out = tempfile.mkdtemp()
        r = run([sys.executable, os.path.join(S, "make_projects.py"), os.path.join(S, "cases.jsonl"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"projects": 6, "cases": 42})
        manifest = json.load(open(os.path.join(out, "manifest.json")))
        first = manifest["snippets-1"]
        vuln = next(c for c in first if c["expected_detect"])
        clean = next(c for c in first if not c["expected_detect"])
        src = open(os.path.join(out, "snippets-1", vuln["file"])).read()
        self.assertIn("starknet::contract", src)
        os.makedirs(os.path.join(out, "snippets-1", ".audit"))
        with open(os.path.join(out, "snippets-1", ".audit", "findings.json"), "w") as f:
            json.dump([{"id": "CAIRO-001", "locations": [{"file": vuln["file"], "line_start": 3}]},
                       {"id": "CAIRO-002", "locations": [{"file": clean["file"], "line_start": 3}]}], f)
        r = run([sys.executable, os.path.join(S, "score_snippets.py"), os.path.join(out, "manifest.json"), out])
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        self.assertEqual((res["total"]["detected"], res["total"]["flagged_clean"]), (1, 1))
        self.assertEqual(len(res["missing_projects"]), 5)


if __name__ == "__main__":
    unittest.main()
